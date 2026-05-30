"""Generalized per-structure XYZ extractor for supporting-info PDFs.

Units (HARD, encoded on every written .xyz):

    x, y, z       : Å        (angstrom — the XYZ standard)
    charge        : e        (elementary charge, signed integer)
    multiplicity  : (dimensionless, 2S+1)  — singlet=1, doublet=2, triplet=3, …

Built from ``extract_si_xyz.py`` (Zhang 2024 Inorganics SI). Every written
``.xyz`` self-describes its charge, multiplicity, and length unit in the
line-2 comment:

    24
    charge=0 multiplicity=1 units=angstrom  name=INT3-1a  (from <paper> SI)
    C  0.0000  0.0000  0.0000
    ...

This is the HARD rule for the skill (see ``SKILL.md`` § "`.xyz` files —
must self-describe charge and multiplicity"). ``multiplicity = 2S+1``
(singlet=1, doublet=2, triplet=3, …), NOT the unpaired-electron count S.

If a label has neither an entry in ``--cm-json`` nor a CLI default, the script
DOES NOT write the .xyz — it logs a REVIEW item to ``paper_fetch_log.md`` and
moves on. No silent neutral-singlet fallback.

CLI knobs (all paper-specific quirks live here, not in code):

  --banner             text that marks the start of the coordinate section.
                       Default: "coordinates of all stationary points".
  --page-marker-regex  lines matching this are dropped (page numbers in the
                       coord section). Default: ``^S\\d+$``.
  --cm-json            JSON file: ``{"<label>": {"charge": int,
                       "multiplicity": int}, ...}``.
  --default-charge,
  --default-multiplicity  used for labels missing from --cm-json. If neither
                          flag is supplied AND a label isn't in --cm-json,
                          the structure is skipped + REVIEW-logged.
  --si-pdf, --out-dir, --log  IO paths.

Filename sanitization: ``(``, ``)``, ``=``, spaces dropped; ASCII ``'`` and
Unicode ``’`` (U+2019) both collapse to ``p`` (conformer primes).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import _log

XYZ_LINE = re.compile(
    r"^([A-Z][a-z]?)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$"
)


class SiAtom(BaseModel):
    model_config = ConfigDict(extra="forbid")
    element: str = Field(min_length=1, max_length=2)
    x: float
    y: float
    z: float

    @model_validator(mode="after")
    def _element_capitalisation(self) -> "SiAtom":
        # Allow "C", "Ca", "Mg", but not "ca" or "CA". `"".islower()` is False,
        # so handle the single-letter case explicitly.
        rest = self.element[1:]
        if not (self.element[0].isupper() and (rest == "" or rest.islower())):
            raise ValueError(f"bad element capitalisation: {self.element!r}")
        return self


class SiStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    atoms: list[SiAtom]
    charge: int
    multiplicity: int = Field(ge=1)  # 2S+1 ≥ 1

    @model_validator(mode="after")
    def _nonempty(self) -> "SiStructure":
        if not self.atoms:
            raise ValueError(f"structure {self.name!r} has zero atoms")
        return self

    def to_xyz_text(self, source_note: str = "") -> str:
        head = (
            f"charge={self.charge} multiplicity={self.multiplicity} "
            f"units=angstrom"
        )
        comment = f"{head}  name={self.name}"
        if source_note:
            comment += f"  ({source_note})"
        lines = [str(len(self.atoms)), comment]
        for a in self.atoms:
            lines.append(
                f"{a.element:<2s}  {a.x:>14.8f}  {a.y:>14.8f}  {a.z:>14.8f}"
            )
        return "\n".join(lines) + "\n"


def sanitize(label: str) -> str:
    """Map a paper label to a filesystem-safe stem.

    Collapses ASCII ``'`` and Unicode ``’`` to ``p`` (both are used as
    conformer prime marks in the wild).
    """
    return (label.replace("(", "")
                 .replace(")", "")
                 .replace("=", "")
                 .replace(" ", "")
                 .replace("'", "p")
                 .replace("’", "p"))


def pdftotext_raw(pdf: Path) -> str:
    out = subprocess.run(
        ["pdftotext", "-raw", str(pdf), "-"],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.replace("\x0c", "\n")


def parse(
    text: str,
    *,
    banner: str,
    page_marker_re: re.Pattern[str],
) -> list[tuple[str, list[SiAtom]]]:
    """Walk the coord section text and return ``[(name, atoms), ...]``."""
    lines = text.splitlines()
    start = next(
        (i for i, l in enumerate(lines) if banner.lower() in l.lower()),
        None,
    )
    if start is None:
        raise RuntimeError(f"banner {banner!r} not found in SI text")

    results: list[tuple[str, list[SiAtom]]] = []
    current_name: str | None = None
    current_atoms: list[SiAtom] = []

    for raw in lines[start + 1:]:
        line = raw.strip()
        if not line or page_marker_re.match(line):
            continue
        m = XYZ_LINE.match(line)
        if m:
            if current_name is None:
                continue   # stray atoms before the first label — ignore
            current_atoms.append(SiAtom(
                element=m.group(1),
                x=float(m.group(2)),
                y=float(m.group(3)),
                z=float(m.group(4)),
            ))
        else:
            if current_name is not None and current_atoms:
                results.append((current_name, current_atoms))
            current_name = line
            current_atoms = []
    if current_name is not None and current_atoms:
        results.append((current_name, current_atoms))
    return results


def _load_cm_map(path: Path | None) -> dict[str, dict[str, int]]:
    if path is None:
        return {}
    data: Any = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"--cm-json must be a JSON object: {path}")
    out: dict[str, dict[str, int]] = {}
    for k, v in data.items():
        if not isinstance(v, dict) or "charge" not in v or "multiplicity" not in v:
            raise ValueError(
                f"--cm-json[{k!r}] must have keys 'charge' and 'multiplicity'"
            )
        out[k] = {"charge": int(v["charge"]), "multiplicity": int(v["multiplicity"])}
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--si-pdf", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--banner", default="coordinates of all stationary points")
    p.add_argument("--page-marker-regex", default=r"^S\d+$")
    p.add_argument("--cm-json", type=Path, default=None,
                   help='{"<label>": {"charge": int, "multiplicity": int}}')
    p.add_argument("--default-charge", type=int, default=None)
    p.add_argument("--default-multiplicity", type=int, default=None)
    p.add_argument("--log", type=Path, default=None)
    p.add_argument("--paper-name", default="(unknown paper)")
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args(argv)

    if not args.si_pdf.exists():
        print(f"ERROR: SI PDF not found: {args.si_pdf}", file=sys.stderr)
        return 2

    cm_map = _load_cm_map(args.cm_json)
    page_marker_re = re.compile(args.page_marker_regex)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for stale in args.out_dir.glob("*.xyz"):
        stale.unlink()

    raw_structs = parse(
        pdftotext_raw(args.si_pdf),
        banner=args.banner,
        page_marker_re=page_marker_re,
    )

    seen: set[str] = set()
    n_written = 0
    n_skipped_dup = 0
    n_skipped_no_cm = 0

    for name, atoms in raw_structs:
        stem = sanitize(name)
        if stem in seen:
            n_skipped_dup += 1
            if args.verbose:
                print(f"  duplicate suppressed: {name}", file=sys.stderr)
            continue
        seen.add(stem)

        cm = cm_map.get(name)
        # Try the sanitised stem too — planner output may use either form.
        if cm is None:
            cm = cm_map.get(stem)
        if cm is None and args.default_charge is not None \
                     and args.default_multiplicity is not None:
            cm = {"charge": args.default_charge,
                  "multiplicity": args.default_multiplicity}
        if cm is None:
            n_skipped_no_cm += 1
            if args.log:
                _log.append(
                    args.log,
                    "REVIEW",
                    f"si_xyz: skipping `{name}` — no entry in --cm-json and "
                    "no --default-charge/--default-multiplicity supplied",
                    paper_name=args.paper_name,
                    source="scripts/si_xyz.py",
                )
            continue

        struct = SiStructure(
            name=name, atoms=atoms,
            charge=cm["charge"], multiplicity=cm["multiplicity"],
        )
        path = args.out_dir / f"{stem}.xyz"
        path.write_text(struct.to_xyz_text(
            source_note=f"extracted from {args.paper_name} SI"
        ))
        n_written += 1
        if args.verbose:
            print(f"  wrote {path.name} ({len(atoms)} atoms, "
                  f"chrg={struct.charge} mult={struct.multiplicity})",
                  file=sys.stderr)

    print(
        f"si_xyz: wrote {n_written} structures into {args.out_dir} "
        f"({n_skipped_dup} duplicates, {n_skipped_no_cm} skipped "
        f"for missing charge/multiplicity — see log)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
