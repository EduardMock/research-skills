"""CLI for the reaction-mechanism-graph skill.

Subcommands (each delegates to the module's own argparse — run with --help):

    build-index  — join structures/*.xyz + table.json + compounds.json
                   (+ optional mechanism.json) into index.json, with per-step
                   mass-balance verification (per-element, charge, electron
                   parity vs multiplicity parity).
"""
from __future__ import annotations

import sys

_USAGE = "usage: python -m scripts.cli build-index [--help] ..."


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE, file=sys.stderr)
        return 0 if argv else 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "build-index":
        from . import si_index
        return si_index.main(rest)
    print(f"unknown subcommand {cmd!r}\n{_USAGE}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
