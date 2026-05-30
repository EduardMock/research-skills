"""CLI for the paper-figure-extract skill.

Subcommands (each delegates to the module's own argparse — run with --help):

    extract-figs     — pdfimages-first figure extraction with optional page
                       rasterize + caption-anchored / column-aware cropping.
    extract-schemes  — region-only crops of `Scheme N` reaction/cycle bboxes
                       (never whole pages) + schemes.json reactions[] stub.
"""
from __future__ import annotations

import sys

_USAGE = "usage: python -m scripts.cli {extract-figs|extract-schemes} [--help] ..."


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE, file=sys.stderr)
        return 0 if argv else 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "extract-figs":
        from . import extract_figs
        return extract_figs.main(rest)
    if cmd == "extract-schemes":
        from . import extract_schemes
        return extract_schemes.main(rest)
    print(f"unknown subcommand {cmd!r}\n{_USAGE}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
