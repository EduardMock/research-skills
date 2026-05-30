"""CLI for the si-xyz-extract skill.

Subcommands (each delegates to the module's own argparse — run with --help):

    extract-table  — parse a DFT energy table out of an SI PDF → table.json.
    extract-xyz    — extract per-structure .xyz from an SI PDF; every .xyz
                     self-describes `charge=N multiplicity=M` on line 2 (HARD
                     rule — no .xyz is written when c/m is unknown).
"""
from __future__ import annotations

import sys

_USAGE = "usage: python -m scripts.cli {extract-table|extract-xyz} [--help] ..."


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(_USAGE, file=sys.stderr)
        return 0 if argv else 1
    cmd, rest = argv[0], argv[1:]
    if cmd == "extract-table":
        from . import si_table
        return si_table.main(rest)
    if cmd == "extract-xyz":
        from . import si_xyz
        return si_xyz.main(rest)
    print(f"unknown subcommand {cmd!r}\n{_USAGE}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
