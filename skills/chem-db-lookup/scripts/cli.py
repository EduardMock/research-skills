"""Command-line entry point for the chem-db-lookup skill.

Chemically-relevant external database lookups, clients-only (deterministic,
reproducible). Subcommands:

    build    — bulk-resolve an input JSON list into a normalized compound DB
               (PubChem + optional tmQMg-L ligand match + optional RDKit review).
    lookup   — one-off PubChem (+ optional tmQMg-L) lookup, prints JSON.
    crystal  — fetch a crystal structure (CSD-preferred, COD-fallback) and
               convert the CIF to discrete-molecule .xyz via openbabel.

Cache policy: per-query caches (PubChem responses) live in a temp dir that is
deleted when the command exits — nothing is left in the project tree. The large
tmQMg-L reference dataset is cached once under ~/.cache/chem-db-lookup and
reused across runs.

Exit codes:
    0  success
    1  input parse error / malformed CLI args
    2  all rows unresolved (build only) / crystal fetch failed
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from .compound_db import build_compound_db, _default_dataset_cache
from .pubchem_client import pubchem_fetch
from .tmqmg_l_client import TmQMgLClient


def _cmd_build(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"input not found: {input_path}", file=sys.stderr)
        return 1
    try:
        payload = json.loads(input_path.read_text())
    except json.JSONDecodeError as e:
        print(f"input is not valid JSON: {e}", file=sys.stderr)
        return 1
    ees: dict[str, Any] = {}
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("compounds"), list):
        # {"compounds": [...], "expected_electronic_structure": {...}}
        rows = payload["compounds"]
        if isinstance(payload.get("expected_electronic_structure"), dict):
            ees = payload["expected_electronic_structure"]
    else:
        print(
            "input must be a JSON list of rows or {compounds: [...], "
            "expected_electronic_structure: {...}} dict",
            file=sys.stderr,
        )
        return 1

    # Ephemeral per-query cache: a temp dir deleted on exit. The tmQMg-L
    # dataset persists under ~/.cache/chem-db-lookup (handled in build_compound_db).
    with tempfile.TemporaryDirectory(prefix="chem-db-lookup-") as tmp:
        db = build_compound_db(
            rows,
            cache_dir=tmp,
            match_tmqml=args.match_tmqml,
            review=args.review,
            tmqml_sha=args.tmqml_sha,
            rate_limit=args.rate_limit,
            force_refetch=args.force_refetch,
            expected_electronic_structure=ees,
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
    query = args.query if args.query is not None else args.smiles
    qtype = "smiles" if (args.query is None and args.smiles is not None) else args.query_type
    if query is None:
        print("lookup requires --query or --smiles", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="chem-db-lookup-") as tmp:
        result = pubchem_fetch(
            query,
            query_type=qtype,
            cache_path=Path(tmp) / "pubchem_cache.json",
            rate_limit=args.rate_limit,
        )
        if args.match_tmqml:
            client = TmQMgLClient(cache_dir=_default_dataset_cache(), sha=args.tmqml_sha)
            result["tmqml"] = (
                client.match_by_smiles(result.get("smiles"))
                or client.match_by_smiles(result.get("canonical_smiles"))
                or client.match_by_inchikey(result.get("inchikey"))
            )

    print(json.dumps(result, indent=2, sort_keys=False))
    return 0


def _cmd_crystal(args: argparse.Namespace) -> int:
    from . import crystal_client                # lazy: pulls requests/openbabel only here
    try:
        hit = crystal_client.fetch_crystal(
            Path(args.out_dir),
            refcode=args.refcode,
            cod_id=args.cod_id,
            formula=args.formula,
            text=args.text,
            prefer_csd=not args.no_csd,
        )
    except Exception as e:
        print(f"crystal fetch failed: {e}", file=sys.stderr)
        return 2
    print(json.dumps(hit.model_dump(), indent=2))
    print(
        f"[{hit.source}] {hit.identifier}: {hit.n_molecules} molecule(s) → "
        f"{hit.cif}" + (f"  ({hit.note})" if hit.note else ""),
        file=sys.stderr,
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="chem-db-lookup",
        description=(
            "Resolve compounds/ligands/crystal structures against chemically "
            "relevant public databases (PubChem, tmQMg-L, CSD/COD)."
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pb = sub.add_parser("build", help="bulk-resolve an input JSON file")
    pb.add_argument("--input", required=True, help="path to input JSON list")
    pb.add_argument("--output", required=True, help="path to write compounds.json")
    pb.add_argument("--match-tmqml", action="store_true",
                    help="enable tmQMg-L ligand-matching pass")
    pb.add_argument("--review", action="store_true",
                    help="enable RDKit review pass (degrades if RDKit absent)")
    pb.add_argument("--tmqml-sha", default="main",
                    help="tmQMg-L git ref to pin (default: main)")
    pb.add_argument("--force-refetch", action="store_true",
                    help="bypass the (ephemeral) PubChem cache")
    pb.add_argument("--rate-limit", type=float, default=4.0,
                    help="PubChem requests/sec (default 4)")
    pb.set_defaults(func=_cmd_build)

    pl = sub.add_parser("lookup", help="one-off lookup, prints JSON to stdout")
    pl.add_argument("--query", help="lookup string (defaults to a name query)")
    pl.add_argument("--query-type", default="name",
                    choices=("name", "smiles", "inchi", "inchikey", "cid"))
    pl.add_argument("--smiles", help="shortcut for --query X --query-type smiles")
    pl.add_argument("--match-tmqml", action="store_true")
    pl.add_argument("--tmqml-sha", default="main")
    pl.add_argument("--rate-limit", type=float, default=4.0)
    pl.set_defaults(func=_cmd_lookup)

    pc = sub.add_parser(
        "crystal",
        help="fetch a crystal structure (CSD→COD) and convert CIF to .xyz",
    )
    pc.add_argument("--out-dir", required=True, help="directory for .cif + .xyz")
    pc.add_argument("--refcode", default=None,
                    help="CSD refcode (used only if a licensed ccdc is present)")
    pc.add_argument("--cod-id", default=None, help="COD-ID for a direct CIF fetch")
    pc.add_argument("--formula", default=None,
                    help='Hill formula for COD search, e.g. "C6 H6"')
    pc.add_argument("--text", default=None,
                    help="free-text COD search (DOI, name)")
    pc.add_argument("--no-csd", action="store_true",
                    help="skip the CSD attempt, go straight to COD")
    pc.set_defaults(func=_cmd_crystal)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
