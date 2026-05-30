"""Command-line entry point for the paper-fetch-smiles skill.

paper-fetch-smiles is the conversion ENTRY POINT: it hand-authors `compounds.py`
and renders the visual check. Resolution (PubChem/tmQMg-L/crystal) lives in the
`chem-db-lookup` skill (`build`/`lookup`); figure, SI, and mechanism extraction
live in `paper-figure-extract`, `si-xyz-extract`, and `reaction-mechanism-graph`.
This CLI therefore exposes only:

    render   — draw a 2D-structure grid image from a compounds.json file.

Exit codes:
    0  success
    1  input parse error / malformed CLI args
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _cmd_render(args: argparse.Namespace) -> int:
    try:
        from .render import render
    except ImportError as e:                     # RDKit missing
        print(f"render needs RDKit: {e}", file=sys.stderr)
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
        prog="paper-fetch-smiles",
        description="Render a compounds.json into a 2D-structure grid PNG.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("render", help="render compounds.json to a grid PNG")
    pr.add_argument("--input", required=True,
                    help="compounds.json (list or {compounds: [...]} dict)")
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
    raise SystemExit(main())
