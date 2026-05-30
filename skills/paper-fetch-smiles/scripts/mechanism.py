"""Mechanism graph + spin partners + mass-balance verification.

Units (read from / cross-checked against the participants' .xyz files):

    atom counts   : (dimensionless, integer per element)
    charge        : e        (elementary charge, signed integer)
    multiplicity  : (dimensionless, 2S+1)
    electron Z    : (dimensionless, atomic number)

A paper's catalytic cycle is encoded as a JSON ``mechanism.json`` next to its
``compounds.py`` / ``compounds.json``. Shape::

    {
      "mechanism_sequence": [
        {"pathway": "1a",
         "steps": [
           {"from": "Ni(L1)2",  "to": "INT1-1a", "join": ["1"]},
           {"from": "INT1-1a",  "to": "INT2-1a", "leave": ["L1=PMe3"]},
           {"from": "INT2-1a",  "to": "TS1-1a"},
           ...
         ]},
        {"pathway": "1b", "steps": [...]}
      ],
      "spin_pairs": [
        ["INT5-1f", "INT5-1f-triplet"]
      ]
    }

Each step represents an elementary process from ``from`` → ``to``, with
optional ``join`` (small molecules / fragments adding into the metal sphere)
and ``leave`` (groups departing). All four label sets must match the
``paper_id`` of an entry in ``compounds.json`` **or** the stem of an .xyz file
in the structures dir, so the verifier can look up atom counts and charges.

**Forks** (one species → two products) and **merges** (two species → one)
are first-class. The schema doesn't have an explicit fork node — write the
diverging steps in two pathway entries that share the ``from`` label::

    {"mechanism_sequence": [
       {"pathway": "1a", "steps": [
           {"from": "INT2-1", "to": "TS1-1a"},   ← fork point
           {"from": "TS1-1a", "to": "INT5"}      ← merge point
       ]},
       {"pathway": "1b", "steps": [
           {"from": "INT2-1", "to": "TS1-1b"},   ← same INT2-1
           {"from": "TS1-1b", "to": "INT5"}      ← same INT5
       ]}
    ]}

``derive_neighbours`` accumulates both branches: INT2-1.next_steps becomes
``[TS1-1a, TS1-1b]``; INT2-1.pathways becomes ``[1a, 1b]``; INT5.prev_steps
becomes ``[TS1-1a, TS1-1b]``.

This module exposes:

* :func:`load_mechanism` — read + validate ``mechanism.json``
* :func:`derive_neighbours` — per-label ``{pathways, next_steps, prev_steps,
  spin_partners}`` dict, ready to merge into ``IndexEntry``
* :func:`mass_balance_check` — list of imbalance messages for one step;
  callers append these to ``paper_fetch_log.md``
* :func:`atom_summary` — read an .xyz file and return per-element counts +
  charge + multiplicity (parsed from the line-2 ``charge=N multiplicity=M``
  comment that ``si_xyz`` enforces)

Mass balance covers three invariants per step:
    (1) per-element atom counts:  from + join == to + leave  for every element
    (2) total formal charge:      from + join == to + leave
    (3) total electron parity:    from + join == to + leave  (sum of (Z·count) +
        charge, mod 2 ⇒ multiplicity parity); flagged only when impossible
        rather than just unusual
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- pydantic models ---------------------------------------------------------

class MechanismStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_: str = Field(alias="from")
    to: str
    join: list[str] = Field(default_factory=list)
    leave: list[str] = Field(default_factory=list)
    note: str | None = None


class MechanismPathway(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pathway: str
    steps: list[MechanismStep]

    @field_validator("steps")
    @classmethod
    def _nonempty(cls, v: list[MechanismStep]) -> list[MechanismStep]:
        if not v:
            raise ValueError("pathway must have at least one step")
        return v


class MechanismInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mechanism_sequence: list[MechanismPathway] = Field(default_factory=list)
    spin_pairs: list[list[str]] = Field(default_factory=list)

    @field_validator("spin_pairs")
    @classmethod
    def _at_least_two_each(cls, v: list[list[str]]) -> list[list[str]]:
        for group in v:
            if len(group) < 2:
                raise ValueError(f"spin_pairs group needs ≥2 labels: {group!r}")
        return v


class AtomSummary(BaseModel):
    """What we need from an .xyz to verify a step."""
    model_config = ConfigDict(extra="forbid")
    label: str                # the SI label / stem
    per_element: dict[str, int]
    charge: int
    multiplicity: int


# --- loaders -----------------------------------------------------------------

def load_mechanism(path: Path) -> MechanismInput:
    return MechanismInput.model_validate_json(path.read_text())


# Heavy elements (Z) for parity check. Extend as needed.
_Z = {
    "H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9,
    "Ne": 10, "Na": 11, "Mg": 12, "Al": 13, "Si": 14, "P": 15, "S": 16, "Cl": 17,
    "Ar": 18, "K": 19, "Ca": 20, "Sc": 21, "Ti": 22, "V": 23, "Cr": 24, "Mn": 25,
    "Fe": 26, "Co": 27, "Ni": 28, "Cu": 29, "Zn": 30, "Ga": 31, "Ge": 32, "As": 33,
    "Se": 34, "Br": 35, "Kr": 36, "Rb": 37, "Sr": 38, "Y": 39, "Zr": 40, "Nb": 41,
    "Mo": 42, "Tc": 43, "Ru": 44, "Rh": 45, "Pd": 46, "Ag": 47, "Cd": 48, "In": 49,
    "Sn": 50, "Sb": 51, "Te": 52, "I": 53, "Xe": 54, "Cs": 55, "Ba": 56, "La": 57,
    "Ce": 58, "Pr": 59, "Nd": 60, "Pm": 61, "Sm": 62, "Eu": 63, "Gd": 64, "Tb": 65,
    "Dy": 66, "Ho": 67, "Er": 68, "Tm": 69, "Yb": 70, "Lu": 71, "Hf": 72, "Ta": 73,
    "W": 74, "Re": 75, "Os": 76, "Ir": 77, "Pt": 78, "Au": 79, "Hg": 80,
}


_CM_RE = re.compile(r"charge=(?P<c>-?\d+)\s+multiplicity=(?P<m>\d+)")


def atom_summary(xyz_path: Path) -> AtomSummary:
    """Read an .xyz (with line-2 ``charge=N multiplicity=M`` comment) and summarise.

    Raises ``ValueError`` if the comment line is missing the c/m tokens — the
    skill's contract says every .xyz must self-describe.
    """
    text = xyz_path.read_text()
    lines = text.splitlines()
    if len(lines) < 2:
        raise ValueError(f"{xyz_path}: file too short")
    try:
        n_atoms = int(lines[0].strip())
    except ValueError as e:
        raise ValueError(f"{xyz_path}: line 1 is not an atom count") from e
    m = _CM_RE.search(lines[1])
    if not m:
        raise ValueError(
            f"{xyz_path}: line 2 must contain `charge=N multiplicity=M` "
            f"(skill contract). Got: {lines[1]!r}"
        )
    charge = int(m.group("c"))
    mult = int(m.group("m"))
    per_el: Counter[str] = Counter()
    for line in lines[2:2 + n_atoms]:
        tok = line.split()
        if not tok:
            continue
        per_el[tok[0]] += 1
    if sum(per_el.values()) != n_atoms:
        raise ValueError(
            f"{xyz_path}: declared {n_atoms} atoms but parsed {sum(per_el.values())}"
        )
    return AtomSummary(
        label=xyz_path.stem,
        per_element=dict(per_el),
        charge=charge,
        multiplicity=mult,
    )


# --- derivation: per-label graph view ---------------------------------------

def derive_neighbours(
    mech: MechanismInput,
) -> dict[str, dict[str, Any]]:
    """Return ``{label: {pathways, next_steps, prev_steps, spin_partners}}``."""
    out: dict[str, dict[str, Any]] = {}

    def _slot(label: str) -> dict[str, Any]:
        return out.setdefault(label, {
            "pathways": [], "next_steps": [], "prev_steps": [], "spin_partners": [],
        })

    for pw in mech.mechanism_sequence:
        for step in pw.steps:
            a = _slot(step.from_)
            b = _slot(step.to)
            if pw.pathway not in a["pathways"]:
                a["pathways"].append(pw.pathway)
            if pw.pathway not in b["pathways"]:
                b["pathways"].append(pw.pathway)
            if step.to not in a["next_steps"]:
                a["next_steps"].append(step.to)
            if step.from_ not in b["prev_steps"]:
                b["prev_steps"].append(step.from_)

    for group in mech.spin_pairs:
        for label in group:
            partners = [g for g in group if g != label]
            slot = _slot(label)
            for p in partners:
                if p not in slot["spin_partners"]:
                    slot["spin_partners"].append(p)
    return out


# --- mass balance ------------------------------------------------------------

def _lookup_summaries(
    labels: list[str],
    summaries: dict[str, AtomSummary],
) -> tuple[list[AtomSummary], list[str]]:
    """Return ``(found_summaries, missing_labels)``."""
    found: list[AtomSummary] = []
    missing: list[str] = []
    for l in labels:
        if l in summaries:
            found.append(summaries[l])
        else:
            missing.append(l)
    return found, missing


def mass_balance_check(
    step: MechanismStep,
    summaries: dict[str, AtomSummary],
) -> tuple[list[str], list[str]]:
    """Verify one ``from → to`` step.

    Returns ``(imbalances, unresolved)`` — two lists of single-line messages,
    suitable for REVIEW entries in paper_fetch_log.md.

    * ``imbalances`` — real failures (per-element delta, charge delta, parity
      mismatch). Empty list = balanced as far as we could check.
    * ``unresolved`` — couldn't perform the check because some participants
      lack an atom summary (no .xyz under any name we tried).

    The two are kept separate so the run-metadata can report "X imbalances"
    distinctly from "Y unresolved labels" — the latter is usually a CLI
    aliasing problem, not a chemistry problem.
    """
    imbalances: list[str] = []
    unresolved: list[str] = []

    all_labels = [step.from_, step.to, *step.join, *step.leave]
    _, missing = _lookup_summaries(all_labels, summaries)
    if missing:
        unresolved.append(
            f"{step.from_} → {step.to}: can't verify mass balance — missing "
            f"atom summaries for {missing}"
        )
        return imbalances, unresolved

    from_, to_ = summaries[step.from_], summaries[step.to]
    joiners = [summaries[l] for l in step.join]
    leavers = [summaries[l] for l in step.leave]

    # Per-element balance.
    lhs: Counter[str] = Counter(from_.per_element)
    for j in joiners:
        lhs.update(j.per_element)
    rhs: Counter[str] = Counter(to_.per_element)
    for l in leavers:
        rhs.update(l.per_element)
    if lhs != rhs:
        diff = {el: lhs.get(el, 0) - rhs.get(el, 0)
                for el in set(lhs) | set(rhs)
                if lhs.get(el, 0) != rhs.get(el, 0)}
        imbalances.append(
            f"{step.from_} → {step.to}: per-element imbalance "
            f"(lhs−rhs by element): {diff}"
        )

    # Charge balance.
    q_lhs = from_.charge + sum(j.charge for j in joiners)
    q_rhs = to_.charge + sum(l.charge for l in leavers)
    if q_lhs != q_rhs:
        imbalances.append(
            f"{step.from_} → {step.to}: charge imbalance lhs={q_lhs} rhs={q_rhs}"
        )

    # Electron-parity vs multiplicity-parity.
    # Total electrons = Σ Z·count − total_charge. Parity must match (2S+1−1).
    def _parity(s: AtomSummary) -> int:
        Zsum = sum(_Z.get(el, 0) * n for el, n in s.per_element.items())
        return (Zsum - s.charge) % 2  # 0 = closed-shell parity, 1 = odd
    def _mult_parity(s: AtomSummary) -> int:
        return (s.multiplicity - 1) % 2  # 2S, parity of unpaired electrons
    lhs_par = sum(_parity(s) for s in [from_, *joiners]) % 2
    rhs_par = sum(_parity(s) for s in [to_, *leavers]) % 2
    if lhs_par != rhs_par:
        imbalances.append(
            f"{step.from_} → {step.to}: electron-count parity imbalance "
            f"lhs={lhs_par} rhs={rhs_par} (means odd vs even electron-total)"
        )
    # Multiplicity-parity check is per-species, not per-step (it's a
    # self-consistency check) — flag if a species' declared multiplicity
    # disagrees with electron-count parity.
    for s in [from_, to_, *joiners, *leavers]:
        if _parity(s) != _mult_parity(s):
            imbalances.append(
                f"{s.label}: multiplicity={s.multiplicity} disagrees with "
                f"electron-count parity (charge={s.charge}, "
                f"sumZ={sum(_Z.get(el, 0) * n for el, n in s.per_element.items())})"
            )

    return imbalances, unresolved


__all__ = [
    "MechanismStep", "MechanismPathway", "MechanismInput", "AtomSummary",
    "load_mechanism", "atom_summary", "derive_neighbours", "mass_balance_check",
]
