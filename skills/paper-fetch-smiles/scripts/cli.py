"""Command-line entry point for the paper-fetch-smiles skill.

Three subcommands:

    build    — bulk-resolve an input JSON list into a compound DB.
    lookup   — one-off PubChem (and optional tmQMg-L) lookup, prints JSON.
    render   — draw a 2D-structure grid image from a compounds.json file.

Designed to be invoked from a paper-conversion pipeline.

Exit codes:
    0  success
    1  input parse error / malformed CLI args
    2  all rows unresolved (build only)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .compound_db import build_compound_db
from .pubchem_client import pubchem_fetch
from .tmqmg_l_client import TmQMgLClient


def _cmd_build(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"input not found: {input_path}", file=sys.stderr)
        return 1
    try:
        rows = json.loads(input_path.read_text())
    except json.JSONDecodeError as e:
        print(f"input is not valid JSON: {e}", file=sys.stderr)
        return 1
    if not isinstance(rows, list):
        # Allow {"compounds": [...]} for convenience.
        if isinstance(rows, dict) and isinstance(rows.get("compounds"), list):
            rows = rows["compounds"]
        else:
            print("input must be a JSON list of rows", file=sys.stderr)
            return 1

    db = build_compound_db(
        rows,
        cache_dir=args.cache_dir,
        match_tmqml=args.match_tmqml,
        review=args.review,
        tmqml_sha=args.tmqml_sha,
        rate_limit=args.rate_limit,
        force_refetch=args.force_refetch,
    )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(db, indent=2, sort_keys=False))
    md = db["metadata"]
    print(
        f"wrote {out_path} — {md['n_compounds']} compounds "
        f"({md['n_resolved_pubchem']} pubchem, {md['n_fallback']} fallback, "
        f"{md['n_unresolved']} unresolved, {md['n_tmqml_matched']} tmQMg-L)",
        file=sys.stderr,
    )
    if md["n_compounds"] > 0 and md["n_resolved_pubchem"] + md["n_fallback"] == 0:
        return 2
    return 0


def _cmd_lookup(args: argparse.Namespace) -> int:
    result: dict[str, Any] = {}
    if args.query is not None:
        result = pubchem_fetch(
            args.query,
            query_type=args.query_type,
            cache_path=Path(args.cache_dir) / "pubchem_cache.json",
            rate_limit=args.rate_limit,
        )
    elif args.smiles is not None:
        # SMILES-only lookup goes through PubChem's `smiles` namespace.
        result = pubchem_fetch(
            args.smiles,
            query_type="smiles",
            cache_path=Path(args.cache_dir) / "pubchem_cache.json",
            rate_limit=args.rate_limit,
        )
    else:
        print("lookup requires --query or --smiles", file=sys.stderr)
        return 1

    if args.match_tmqml:
        client = TmQMgLClient(cache_dir=args.cache_dir, sha=args.tmqml_sha)
        result["tmqml"] = (
            client.match_by_smiles(result.get("smiles"))
            or client.match_by_smiles(result.get("canonical_smiles"))
            or client.match_by_inchikey(result.get("inchikey"))
        )

    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    # Lazy import: RDKit is only needed for this subcommand.
    try:
        from .render import render
    except ImportError as e:
        print(f"render requires rdkit: {e}", file=sys.stderr)
        return 1
    in_path = Path(args.input)
    if not in_path.exists():
        print(f"input not found: {in_path}", file=sys.stderr)
        return 1
    out_path = render(
        in_path,
        Path(args.output),
        mols_per_row=args.mols_per_row,
        sub_img_size=(args.sub_img_size, args.sub_img_size),
    )
    print(f"wrote {out_path}", file=sys.stderr)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chemstructure-database-creation",
        description=(
            "Resolve compound names/SMILES against PubChem (+ optional "
            "tmQMg-L) and emit a normalized JSON database."
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("build", help="bulk-resolve an input JSON file")
    pb.add_argument("--input", required=True, help="path to input JSON list")
    pb.add_argument("--output", required=True, help="path to write compounds.json")
    pb.add_argument("--cache-dir", default=".compound_cache")
    pb.add_argument("--match-tmqml", action="store_true",
                    help="enable tmQMg-L matching pass")
    pb.add_argument("--review", action="store_true",
                    help="enable RDKit review pass (degrades if RDKit absent)")
    pb.add_argument("--tmqml-sha", default="main",
                    help="tmQMg-L git ref to pin (default: main)")
    pb.add_argument("--force-refetch", action="store_true",
                    help="bypass PubChem cache")
    pb.add_argument("--rate-limit", type=float, default=4.0,
                    help="PubChem requests/sec (default 4)")
    pb.set_defaults(func=_cmd_build)

    pl = sub.add_parser("lookup", help="one-off lookup, prints JSON to stdout")
    pl.add_argument("--query", help="lookup string (defaults to a name query)")
    pl.add_argument("--query-type", default="name",
                    choices=("name", "smiles", "inchi", "inchikey", "cid"))
    pl.add_argument("--smiles", help="shortcut for --query X --query-type smiles")
    pl.add_argument("--cache-dir", default=".compound_cache")
    pl.add_argument("--match-tmqml", action="store_true")
    pl.add_argument("--tmqml-sha", default="main")
    pl.add_argument("--rate-limit", type=float, default=4.0)
    pl.set_defaults(func=_cmd_lookup)

    pr = sub.add_parser(
        "render", help="render compounds.json to a 2D-structure grid PNG"
    )
    pr.add_argument("--input", required=True,
                    help="compounds.json (either list or {compounds: [...]} dict)")
    pr.add_argument("--output", required=True,
                    help="output image path (e.g. compounds.png)")
    pr.add_argument("--mols-per-row", type=int, default=4)
    pr.add_argument("--sub-img-size", type=int, default=300,
                    help="per-molecule cell size in px (square)")
    pr.set_defaults(func=_cmd_render)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
