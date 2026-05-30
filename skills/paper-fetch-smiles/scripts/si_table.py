"""Generalized DFT-table parser for supporting-info PDFs.

Units (defaults — override via ``--columns`` notation if a paper differs):

    E, G, CGFE, ETHF, GTHF : Hartree (atomic units of energy, Eh)
    Ifreq                  : cm⁻¹   (one imaginary frequency, signed; TS only)

The script does not enforce these — they are documentation. If a paper reports
energies in kcal/mol or kJ/mol, name the column accordingly (e.g.
``--columns "E_kcal,G_kcal,...,Ifreq?"``) and downstream consumers can branch.

Built from ``parse_table_s1.py`` (Zhang 2024 Inorganics SI). The Zhang-specific
knobs are now CLI flags:

  --banner        text that marks the end of the table region (case-insensitive;
                  default: "coordinates of all stationary points"). Parsing
                  stops at the first line containing this banner.
  --columns       comma-separated column names. A trailing ``?`` marks the
                  column as optional (only present on some rows). Default:
                  "E,G,CGFE,ETHF,GTHF,Ifreq?".
  --label-regex   regex matching the row's label (first whitespace-delimited
                  token). Default allows alnum + ``()-=`` plus the ASCII and
                  Unicode apostrophes used for conformer primes.
  --si-pdf, --out, --log  IO paths.

Output JSON shape:

    {
      "_units": {"E": "Hartree", ..., "Ifreq": "cm^-1"},
      "rows": {"<label>": {"<col1>": float, ..., "<colN>": float | null}, ...}
    }

The ``null`` only appears for optional columns when the row didn't carry that
value. Lines that look table-shaped but fail to parse end up in
``paper_fetch_log.md`` under REVIEW.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import _log


class SiTableConfig(BaseModel):
    """Knobs for one paper's SI table parse."""
    model_config = ConfigDict(extra="forbid")

    banner: str = "coordinates of all stationary points"
    columns: list[str] = Field(
        default_factory=lambda: ["E", "G", "CGFE", "ETHF", "GTHF", "Ifreq?"]
    )
    label_regex: str = r"[A-Za-z0-9()\-=’']+"

    @field_validator("columns")
    @classmethod
    def _at_least_one(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("columns must be non-empty")
        return v

    @property
    def required_columns(self) -> list[str]:
        return [c.rstrip("?") for c in self.columns if not c.endswith("?")]

    @property
    def optional_columns(self) -> list[str]:
        return [c.rstrip("?") for c in self.columns if c.endswith("?")]

    @property
    def column_names(self) -> list[str]:
        return [c.rstrip("?") for c in self.columns]


class SiTableRow(BaseModel):
    """A single resolved row. ``extra='allow'`` lets dynamic columns flow through."""
    model_config = ConfigDict(extra="allow")

    label: str


def _build_row_regex(cfg: SiTableConfig) -> re.Pattern[str]:
    """Compile the row regex for the configured column layout."""
    parts = [rf"^(?P<label>{cfg.label_regex})"]
    for col in cfg.required_columns:
        parts.append(rf"\s+(?P<{col}>-?\d+\.\d+)")
    for col in cfg.optional_columns:
        parts.append(rf"(?:\s+(?P<{col}>-?\d+\.\d+))?")
    parts.append(r"\s*$")
    return re.compile("".join(parts))


def pdftotext_raw(pdf: Path) -> str:
    """Run ``pdftotext -raw`` and normalise form-feed page breaks to newlines."""
    out = subprocess.run(
        ["pdftotext", "-raw", str(pdf), "-"],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.replace("\x0c", "\n")


def parse(
    text: str,
    cfg: SiTableConfig,
    *,
    log_path: Path | None = None,
    log_source: str = "scripts/si_table.py",
    paper_name: str = "(unknown paper)",
) -> dict[str, dict[str, Any]]:
    """Parse all table rows from raw SI text until ``cfg.banner`` is hit."""
    row_re = _build_row_regex(cfg)
    banner_lower = cfg.banner.lower()
    rows: dict[str, dict[str, Any]] = {}
    suspicious = 0

    for line in text.splitlines():
        if banner_lower in line.lower():
            break
        s = line.strip()
        m = row_re.match(s)
        if not m:
            # Heuristic: a line with the right shape (≥ N floats) but that the
            # regex rejected is worth flagging.
            if s and len(re.findall(r"-?\d+\.\d+", s)) >= len(cfg.required_columns):
                suspicious += 1
                if log_path and suspicious <= 10:  # cap log noise
                    _log.append(
                        log_path,
                        "REVIEW",
                        f"si_table: line shape-matched the column count but failed "
                        f"the row regex: `{s[:120]}`",
                        paper_name=paper_name,
                        source=log_source,
                    )
            continue
        d = m.groupdict()
        label = d.pop("label")
        row: dict[str, Any] = {}
        for col in cfg.column_names:
            v = d.get(col)
            row[col] = float(v) if v is not None else None
        if label in rows:
            if log_path:
                _log.append(
                    log_path,
                    "REVIEW",
                    f"si_table: duplicate row for label `{label}` — keeping first",
                    paper_name=paper_name,
                    source=log_source,
                )
            continue
        # Validate the row through the pydantic model (extra='allow' keeps cols).
        SiTableRow(label=label, **row)
        rows[label] = row
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--si-pdf", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--banner", default="coordinates of all stationary points")
    p.add_argument(
        "--columns",
        default="E,G,CGFE,ETHF,GTHF,Ifreq?",
        help='Comma-separated column names. Trailing "?" marks an optional col.',
    )
    p.add_argument("--label-regex", default=r"[A-Za-z0-9()\-=’']+")
    p.add_argument("--units",
                   default="E=Hartree,G=Hartree,CGFE=Hartree,ETHF=Hartree,"
                           "GTHF=Hartree,Ifreq=cm^-1",
                   help='Comma-separated "<col>=<unit>" pairs documenting '
                        'each column. Stored in the output under "_units".')
    p.add_argument("--log", type=Path, default=None,
                   help="paper_fetch_log.md path (REVIEW items will be appended)")
    p.add_argument("--paper-name", default="(unknown paper)")
    args = p.parse_args(argv)

    if not args.si_pdf.exists():
        print(f"ERROR: SI PDF not found: {args.si_pdf}", file=sys.stderr)
        return 2

    cfg = SiTableConfig(
        banner=args.banner,
        columns=[c.strip() for c in args.columns.split(",") if c.strip()],
        label_regex=args.label_regex,
    )
    text = pdftotext_raw(args.si_pdf)
    rows = parse(
        text, cfg,
        log_path=args.log,
        paper_name=args.paper_name,
    )

    units: dict[str, str] = {}
    for tok in args.units.split(","):
        tok = tok.strip()
        if not tok:
            continue
        if "=" not in tok:
            raise SystemExit(f"--units item must be col=unit: {tok!r}")
        k, v = tok.split("=", 1)
        units[k.strip()] = v.strip()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({"_units": units, "rows": rows}, indent=2))
    n_with_optional = sum(
        1 for r in rows.values()
        for c in cfg.optional_columns if r.get(c) is not None
    )
    print(
        f"si_table: parsed {len(rows)} rows ({n_with_optional} with optional "
        f"column values) → {args.out}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
