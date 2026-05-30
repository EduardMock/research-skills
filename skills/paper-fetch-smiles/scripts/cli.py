"""Command-line entry point for the paper-fetch-smiles skill.

Subcommands:

    build           — bulk-resolve an input JSON list into a compound DB.
    lookup          — one-off PubChem (and optional tmQMg-L) lookup.
    render          — draw a 2D-structure grid image from compounds.json.
    extract-figs    — `pdfimages -all paper.pdf out/figs/` + figs.json catalog
                       (upstream of compounds.py — feeds the energy-diagram
                       analyzer subagent that traces colored lines into
                       mechanism_from_diagram.json).
    extract-table   — parse a DFT energy table out of an SI PDF.
    extract-xyz     — extract per-structure .xyz files from an SI PDF
                       (each .xyz carries `charge=N multiplicity=M` on line 2).
    build-index     — join structures/ + table.json + compounds.json (+ optional
                       mechanism.json with mass-balance verification) into
                       index.json.

Designed to be invoked from a paper-conversion pipeline.

Exit codes:
    0  success
    1  input parse error / malformed CLI args
    2  all rows unresolved (build only) / required input missing (SI cmds)
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
        payload = json.loads(input_path.read_text())
    except json.JSONDecodeError as e:
        print(f"input is not valid JSON: {e}", file=sys.stderr)
        return 1
    ees: dict[str, Any] = {}
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("compounds"), list):
        # Ground-truth shape: {"compounds": [...], "expected_electronic_structure": {...}}
        # In-place re-runs (input == output path) also land here.
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

    db = build_compound_db(
        rows,
        cache_dir=args.cache_dir,
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


def _require_compounds(path_str: str | None) -> int:
    """HARD ordering guard for the SI subcommands.

    SI extraction (table / xyz / index) must NOT run before the main paper
    pipeline has produced `compounds.json`. The skill's invariant is:

        compounds.py (hand-authored)
          → scripts/cli.py build → compounds.json
          → scripts/cli.py render → compounds.png
          → (only now) SI subcommands consume compounds.json for label
            resolution + downstream cross-checks.

    Returns 0 if the check passes (or was opted out), 2 with a stderr error
    otherwise. The callers translate that into their own exit codes.
    """
    if path_str is None:
        return 0
    from pathlib import Path as _Path
    import json as _json
    p = _Path(path_str)
    if not p.exists():
        print(
            f"ERROR: --require-compounds points to {p}, which does not exist.\n"
            "       Run the main paper pipeline first:\n"
            "         1. Hand-author compounds.py\n"
            "         2. scripts/cli.py build → compounds.json\n"
            "         3. scripts/cli.py render → compounds.png\n"
            "       Then re-run this SI subcommand.",
            file=sys.stderr,
        )
        return 2
    try:
        data = _json.loads(p.read_text())
    except _json.JSONDecodeError as e:
        print(f"ERROR: --require-compounds file is not valid JSON ({p}): {e}",
              file=sys.stderr)
        return 2
    cmpds = data.get("compounds") if isinstance(data, dict) else None
    if not isinstance(cmpds, list) or len(cmpds) == 0:
        print(
            f"ERROR: --require-compounds file {p} has no `compounds` list "
            "or the list is empty.\n"
            "       SI extraction requires a non-empty compounds.json — finish "
            "the main paper pipeline (compounds.py → build) first.",
            file=sys.stderr,
        )
        return 2
    return 0


def _cmd_extract_figs(args: argparse.Namespace) -> int:
    from . import extract_figs
    argv = [
        "--paper-pdf", str(args.paper_pdf),
        "--out-dir", str(args.out_dir),
        "--prefix", args.prefix,
        "--min-width-px", str(args.min_width_px),
        "--min-size-bytes", str(args.min_size_bytes),
        "--page-dpi", str(args.page_dpi),
    ]
    if args.keep_ccitt:
        argv += ["--keep-ccitt"]
    if args.rasterize_pages:
        argv += ["--rasterize-pages"]
    if args.pages:
        argv += ["--pages", args.pages]
    if args.caption_anchored:
        argv += ["--caption-anchored"]
    if args.keep_page_rasters:
        argv += ["--keep-page-rasters"]
    if args.column_aware:
        argv += ["--column-aware"]
    if args.auto:
        argv += ["--auto"]
    if args.log:
        argv += ["--log", str(args.log)]
    if args.paper_name:
        argv += ["--paper-name", args.paper_name]
    return extract_figs.main(argv)


def _cmd_extract_schemes(args: argparse.Namespace) -> int:
    from . import extract_schemes
    argv = [
        "--paper-pdf", str(args.paper_pdf),
        "--out-dir", str(args.out_dir),
        "--page-dpi", str(args.page_dpi),
    ]
    if args.numbers:
        argv += ["--numbers", args.numbers]
    if args.catalog_only:
        argv += ["--catalog-only"]
    if not args.column_aware:
        argv += ["--no-column-aware"]
    if args.log:
        argv += ["--log", str(args.log)]
    if args.paper_name:
        argv += ["--paper-name", args.paper_name]
    return extract_schemes.main(argv)


def _cmd_extract_table(args: argparse.Namespace) -> int:
    rc = _require_compounds(args.require_compounds)
    if rc:
        return rc
    from . import si_table  # local import to avoid pulling pydantic for `build`
    return si_table.main([
        "--si-pdf", str(args.si_pdf),
        "--out", str(args.output),
        "--banner", args.banner,
        "--columns", args.columns,
        "--label-regex", args.label_regex,
        *(["--log", str(args.log)] if args.log else []),
        *(["--paper-name", args.paper_name] if args.paper_name else []),
    ])


def _cmd_extract_xyz(args: argparse.Namespace) -> int:
    rc = _require_compounds(args.require_compounds)
    if rc:
        return rc
    from . import si_xyz
    argv = [
        "--si-pdf", str(args.si_pdf),
        "--out-dir", str(args.out_dir),
        "--banner", args.banner,
        "--page-marker-regex", args.page_marker_regex,
    ]
    if args.cm_json:
        argv += ["--cm-json", str(args.cm_json)]
    if args.default_charge is not None:
        argv += ["--default-charge", str(args.default_charge)]
    if args.default_multiplicity is not None:
        argv += ["--default-multiplicity", str(args.default_multiplicity)]
    if args.log:
        argv += ["--log", str(args.log)]
    if args.paper_name:
        argv += ["--paper-name", args.paper_name]
    if args.verbose:
        argv += ["--verbose"]
    return si_xyz.main(argv)


def _cmd_build_index(args: argparse.Namespace) -> int:
    # build-index has a real --compounds dependency, so the ordering guard
    # is mandatory here (not opt-in like the other two).
    rc = _require_compounds(args.compounds)
    if rc:
        return rc
    from . import si_index
    argv = [
        "--structures", str(args.structures),
        "--table", str(args.table),
        "--compounds", str(args.compounds),
        "--out", str(args.output),
    ]
    if args.aliases:
        argv += ["--aliases", args.aliases]
    if args.mechanism:
        argv += ["--mechanism", str(args.mechanism)]
    if args.log:
        argv += ["--log", str(args.log)]
    if args.paper_name:
        argv += ["--paper-name", args.paper_name]
    return si_index.main(argv)


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

    # Figure extraction (upstream of compounds.py) ---------------------------
    pf = sub.add_parser(
        "extract-figs",
        help="run `pdfimages -all` and catalog the output",
    )
    pf.add_argument("--paper-pdf", required=True,
                    help="path to the main paper PDF")
    pf.add_argument("--out-dir", required=True,
                    help="directory for extracted images + figs.json")
    pf.add_argument("--prefix", default="fig",
                    help="filename prefix for pdfimages output (default: fig)")
    pf.add_argument("--min-width-px", type=int, default=100,
                    help="delete images narrower than this from disk + "
                         "catalog (default 100; 0 = keep everything)")
    pf.add_argument("--min-size-bytes", type=int, default=2048,
                    help="delete files smaller than this (default 2048 = 2 KB; "
                         "0 = keep everything)")
    pf.add_argument("--keep-ccitt", action="store_true",
                    help="keep .ccitt / .params sidecars (default: delete)")
    pf.add_argument("--rasterize-pages", action="store_true",
                    help="also run pdftoppm to write page-1.png, page-2.png, "
                         "… — needed when the energy diagram is vector art")
    pf.add_argument("--pages", default=None,
                    help='page range "N-M" for --rasterize-pages')
    pf.add_argument("--page-dpi", type=int, default=150)
    pf.add_argument("--caption-anchored", action="store_true",
                    help="caption-anchored figure cropping — recommended for "
                         "energy diagrams. Requires --rasterize-pages.")
    pf.add_argument("--keep-page-rasters", action="store_true",
                    help="keep full page-NN.png after cropping")
    pf.add_argument("--column-aware", action="store_true",
                    help="clip single-column figures to their column (detected "
                         "from caption width); leave full-width figures unclipped")
    pf.add_argument("--auto", action="store_true",
                    help="pdfimages-first: only crop when embedded images are too "
                         "few to be the figures (logs the decision)")
    pf.add_argument("--log", default=None)
    pf.add_argument("--paper-name", default=None)
    pf.set_defaults(func=_cmd_extract_figs)

    # SI extraction subcommands ---------------------------------------------
    pt = sub.add_parser("extract-table",
                        help="parse a DFT energy table out of an SI PDF")
    pt.add_argument("--si-pdf", required=True)
    pt.add_argument("--output", required=True, help="table.json output path")
    pt.add_argument("--banner",
                    default="coordinates of all stationary points",
                    help="banner text that ends the table region")
    pt.add_argument("--columns",
                    default="E,G,CGFE,ETHF,GTHF,Ifreq?",
                    help='Comma-separated columns. Trailing "?" = optional col.')
    pt.add_argument("--label-regex", default=r"[A-Za-z0-9()\-=’']+")
    pt.add_argument("--require-compounds", default=None,
                    help="path to compounds.json — refuse to run if it does "
                         "not exist or has an empty `compounds` list. The "
                         "workflow REQUIRES this flag on every SI subcommand.")
    pt.add_argument("--log", default=None,
                    help="paper_fetch_log.md path (REVIEW items will be appended)")
    pt.add_argument("--paper-name", default=None)
    pt.set_defaults(func=_cmd_extract_table)

    px = sub.add_parser("extract-xyz",
                        help="extract .xyz files (charge+multiplicity in line 2)")
    px.add_argument("--si-pdf", required=True)
    px.add_argument("--out-dir", required=True)
    px.add_argument("--banner",
                    default="coordinates of all stationary points")
    px.add_argument("--page-marker-regex", default=r"^S\d+$")
    px.add_argument("--cm-json", default=None,
                    help='{"<label>": {"charge": int, "multiplicity": int}}')
    px.add_argument("--default-charge", type=int, default=None)
    px.add_argument("--default-multiplicity", type=int, default=None)
    px.add_argument("--require-compounds", default=None,
                    help="path to compounds.json — refuse to run if it does "
                         "not exist or has an empty `compounds` list. The "
                         "workflow REQUIRES this flag on every SI subcommand.")
    px.add_argument("--log", default=None)
    px.add_argument("--paper-name", default=None)
    px.add_argument("--verbose", "-v", action="store_true")
    px.set_defaults(func=_cmd_extract_xyz)

    pi = sub.add_parser("build-index",
                        help="join structures + table + compounds (+ mechanism)")
    pi.add_argument("--structures", required=True, help="directory of .xyz files")
    pi.add_argument("--table", required=True, help="table.json from extract-table")
    pi.add_argument("--compounds", required=True,
                    help="compounds.json from build")
    pi.add_argument("--aliases", default=None,
                    help='CSV: "stem=label,stem=label,..."')
    pi.add_argument("--mechanism", default=None,
                    help="mechanism.json (sequence + spin pairs + mass balance)")
    pi.add_argument("--output", required=True, help="index.json output path")
    pi.add_argument("--log", default=None)
    pi.add_argument("--paper-name", default=None)
    pi.set_defaults(func=_cmd_build_index)

    ps = sub.add_parser(
        "extract-schemes",
        help="render reaction/catalytic-cycle `Scheme N` regions (no full pages) "
             "+ schemes.json with a reactions[] stub per cycle",
    )
    ps.add_argument("--paper-pdf", type=Path, required=True)
    ps.add_argument("--out-dir", type=Path, required=True)
    ps.add_argument("--page-dpi", type=int, default=150)
    ps.add_argument("--numbers", default=None,
                    help='only these schemes, e.g. "5,15,19-22"')
    ps.add_argument("--catalog-only", action="store_true",
                    help="locate + write schemes.json but render no crops")
    ps.add_argument("--column-aware", action=argparse.BooleanOptionalAction,
                    default=True,
                    help="clip single-column schemes to their column (ON by "
                         "default; use --no-column-aware to render full page width)")
    ps.add_argument("--log", type=Path, default=None)
    ps.add_argument("--paper-name", default=None)
    ps.set_defaults(func=_cmd_extract_schemes)

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
