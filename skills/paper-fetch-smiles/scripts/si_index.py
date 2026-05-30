"""Generalized index builder: joins ``structures/*.xyz`` ↔ table.json ↔ compounds.json
plus optional mechanism-graph annotation and mass-balance verification.

Units carried through (per the upstream scripts that wrote each input):

    .xyz coords          : Å         (from ``si_xyz.py``)
    .xyz charge          : e
    .xyz multiplicity    : 2S+1
    table energies       : Hartree   (from ``si_table.py``; the column units
                                       follow whatever the SI prints, see the
                                       --columns flag on si_table)
    table imag. freq.    : cm⁻¹
    atom counts (graph)  : per element, integer

These are surfaced on the output ``index.json`` under the top-level
``_units`` block so downstream notebooks can inspect them without having
to read the producing script.

Built from ``build_index.py`` (Zhang 2024 Inorganics SI). The paper-specific
``desanitize_candidates`` and ``classify`` of the original are replaced by:

  * **Auto label aliases** — every ``paper_id`` in ``compounds.json`` is
    sanitised the same way ``si_xyz.sanitize`` sanitises an SI label, giving a
    deterministic stem→paper_id map. Most papers need no manual aliasing.
  * **CLI aliases** for the residual mismatches (e.g., Zhang's
    ``TS6-1f`` ↔ ``TS5-1f`` SI typesetting bug). ``--aliases "A=B,C=D"``.
  * **Paper-agnostic classification**: ``kind`` is derived from the
    imag-frequency column (`Ifreq`) in ``table.json`` and the label prefix
    (``TS``, ``INT``). Anything finer (ligand_class, pathway, …) lives in
    ``compounds.py`` and rides through via the matched compound's fields.
  * **Optional mechanism graph** (``--mechanism mechanism.json``) — adds
    per-entry ``pathways``, ``next_steps``, ``prev_steps``, ``spin_partners``
    and runs per-step mass-balance / charge-balance / electron-parity checks.
    See ``scripts/mechanism.py`` for the schema and balance invariants.

Output ``index.json``:

    {
      "_units": {"xyz.coords": "angstrom", "xyz.charge": "e",
                 "xyz.multiplicity": "2S+1",
                 "table.E": "Hartree", "table.Ifreq": "cm^-1", ...},
      "metadata": {n_structures, n_with_table, n_with_smiles, n_minima, n_ts,
                   n_pathways, n_mechanism_steps, n_mass_balance_failures},
      "structures": [
        {"paper_id": "TS3-1a", "filename": "TS3-1a.xyz",
         "kind": "ts" | "intermediate" | "discrete",
         "energies": {...} | null,
         "smiles": "..." | null, "smiles_source": "pubchem" | "fallback" | null,
         "compound_match": true | false,
         "pathways": [...], "next_steps": [...], "prev_steps": [...],
         "spin_partners": [...]},
        ...
      ]
    }
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from . import _log
from .mechanism import (
    MechanismInput, atom_summary, derive_neighbours, load_mechanism,
    mass_balance_check,
)
from .si_xyz import sanitize


class IndexEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    paper_id: str
    filename: str
    kind: str  # "ts" | "intermediate" | "discrete"
    energies: dict[str, Any] | None = None
    smiles: str | None = None
    smiles_source: str | None = None
    compound_match: bool = False
    # Mechanism-graph annotations (empty unless --mechanism is supplied).
    pathways: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    prev_steps: list[str] = Field(default_factory=list)
    spin_partners: list[str] = Field(default_factory=list)


class IndexMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n_structures: int
    n_with_table: int
    n_with_smiles: int
    n_minima: int
    n_transition_states: int
    n_pathways: int = 0
    n_mechanism_steps: int = 0
    n_mass_balance_failures: int = 0   # real chemistry imbalances
    n_mass_balance_unresolved: int = 0  # label-lookup misses (CLI alias problem)


class IndexDB(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # Tagged with the unit of every numeric field reachable from this DB.
    # Populated from the upstream table's _units (energies + freq) plus a
    # fixed set for what si_index carries itself.
    units: dict[str, str] = Field(default_factory=dict, alias="_units")
    metadata: IndexMetadata
    structures: list[IndexEntry]


def _parse_aliases(spec: str | None) -> dict[str, str]:
    if not spec:
        return {}
    out: dict[str, str] = {}
    for item in spec.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"--aliases item must be A=B, got: {item!r}")
        k, v = item.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _classify(label: str, energies: dict[str, Any] | None) -> str:
    """Paper-agnostic: TS iff Ifreq present, else INT* → intermediate, else discrete."""
    if energies is not None and energies.get("Ifreq") is not None:
        return "ts"
    if label.startswith("TS"):
        return "ts"
    if label.startswith("INT"):
        return "intermediate"
    return "discrete"


def build(
    struct_dir: Path,
    table: dict[str, dict[str, Any]],
    compounds_json: dict[str, Any],
    *,
    extra_aliases: dict[str, str],
    log_path: Path | None,
    paper_name: str,
    mechanism: MechanismInput | None = None,
    table_units: dict[str, str] | None = None,
) -> IndexDB:
    # Auto-alias: sanitised paper_id (and original) → original paper_id.
    cmpd_by_id = {c["paper_id"]: c for c in compounds_json["compounds"]
                  if c.get("paper_id")}
    cmpd_alias = {sanitize(pid): pid for pid in cmpd_by_id}
    # Table labels → sanitised → original.
    table_alias = {sanitize(lab): lab for lab in table}

    entries: list[IndexEntry] = []
    for path in sorted(struct_dir.glob("*.xyz")):
        stem = path.stem

        # Look up the table row. Apply CLI alias first, then sanitised match.
        table_label = extra_aliases.get(stem) or table_alias.get(stem) or stem
        energies = table.get(table_label)
        if energies is None and log_path:
            _log.append(
                log_path,
                "REVIEW",
                f"si_index: structure `{path.name}` has no table row "
                f"(tried `{table_label}`)",
                paper_name=paper_name,
                source="scripts/si_index.py",
            )

        # Look up the compound entry.
        cmpd_id = extra_aliases.get(stem) or cmpd_alias.get(stem) or stem
        cmpd = cmpd_by_id.get(cmpd_id)
        if cmpd is None and log_path and not stem.startswith(("TS", "INT")):
            _log.append(
                log_path,
                "REVIEW",
                f"si_index: discrete structure `{path.name}` has no compounds.json "
                f"row (tried `{cmpd_id}`)",
                paper_name=paper_name,
                source="scripts/si_index.py",
            )

        # paper_id = whichever name we actually matched, else stem.
        label = table_label if energies is not None else (
            cmpd_id if cmpd is not None else stem
        )
        entries.append(IndexEntry(
            paper_id=label,
            filename=path.name,
            kind=_classify(label, energies),
            energies=energies,
            smiles=(cmpd.get("isomeric_smiles") or cmpd.get("canonical_smiles")
                    if cmpd else None),
            smiles_source=(cmpd.get("source") if cmpd else None),
            compound_match=cmpd is not None,
        ))

    # Mechanism overlay: per-entry neighbours + mass-balance per step.
    n_pathways = 0
    n_mechanism_steps = 0
    n_mass_balance_failures = 0
    n_mass_balance_unresolved = 0
    if mechanism is not None:
        neighbours = derive_neighbours(mechanism)
        # Index entries by paper_id for the merge.
        by_id: dict[str, IndexEntry] = {e.paper_id: e for e in entries}
        # Also accept stem matches keyed by the actual .xyz filename — this is
        # the canonical identity of each structure and survives --aliases (which
        # rewrites paper_id for table-lookup but never the filename).
        from pathlib import Path as _Path
        by_stem: dict[str, IndexEntry] = {
            _Path(e.filename).stem: e for e in entries
        }
        for label, info in neighbours.items():
            ent = by_id.get(label) or by_stem.get(sanitize(label))
            if ent is None:
                if log_path:
                    _log.append(
                        log_path,
                        "REVIEW",
                        f"si_index: mechanism references unknown label `{label}` "
                        "— no index entry / .xyz / compounds.json row found",
                        paper_name=paper_name,
                        source="scripts/si_index.py",
                    )
                continue
            ent.pathways = info["pathways"]
            ent.next_steps = info["next_steps"]
            ent.prev_steps = info["prev_steps"]
            ent.spin_partners = info["spin_partners"]

        # Mass balance: build atom summaries from .xyz files + the join/leave
        # participants. The mechanism may reference small molecules (CO2,
        # COD, L1=PMe3, ...) whose .xyz lives in the same structures dir.
        summaries = {}
        for path in struct_dir.glob("*.xyz"):
            try:
                s = atom_summary(path)
            except ValueError as e:
                if log_path:
                    _log.append(
                        log_path, "REVIEW",
                        f"si_index: can't read atom summary for `{path.name}`: {e}",
                        paper_name=paper_name,
                        source="scripts/si_index.py",
                    )
                continue
            # Index by both verbatim stem and any matching paper_id.
            summaries[s.label] = s
        # Also let mechanism labels resolve through stem-sanitisation.
        by_sanitised = {sanitize(k): v for k, v in summaries.items()}
        # Merge in entries' canonical paper_ids → summary.
        for label, sumr in list(by_sanitised.items()):
            summaries.setdefault(label, sumr)
        for pw in mechanism.mechanism_sequence:
            n_pathways += 1
            for step in pw.steps:
                n_mechanism_steps += 1
                # Resolve each label to a summary via sanitised lookup if the
                # verbatim label isn't directly present.
                step_summaries: dict[str, "object"] = {}
                for lab in [step.from_, step.to, *step.join, *step.leave]:
                    s = summaries.get(lab) or by_sanitised.get(sanitize(lab))
                    if s is not None:
                        step_summaries[lab] = s
                imbalances, unresolved = mass_balance_check(step, step_summaries)
                n_mass_balance_failures += len(imbalances)
                n_mass_balance_unresolved += len(unresolved)
                if log_path:
                    for msg in imbalances:
                        _log.append(
                            log_path, "REVIEW",
                            f"si_index/mass-balance [pathway {pw.pathway}]: {msg}",
                            paper_name=paper_name,
                            source="scripts/si_index.py",
                        )
                    for msg in unresolved:
                        _log.append(
                            log_path, "REVIEW",
                            f"si_index/mass-balance-unresolved [pathway {pw.pathway}]: "
                            f"{msg} (likely an aliasing issue — fix with --aliases)",
                            paper_name=paper_name,
                            source="scripts/si_index.py",
                        )

    # Assemble units: upstream table columns + the .xyz / graph conventions we
    # carry ourselves. The xyz fields are documented on every .xyz line 2 too.
    units: dict[str, str] = {
        "xyz.coords": "angstrom",
        "xyz.charge": "e",
        "xyz.multiplicity": "2S+1",
    }
    for col, u in (table_units or {}).items():
        units[f"table.{col}"] = u
    return IndexDB(
        _units=units,
        metadata=IndexMetadata(
            n_structures=len(entries),
            n_with_table=sum(1 for e in entries if e.energies is not None),
            n_with_smiles=sum(1 for e in entries if e.smiles is not None),
            n_minima=sum(1 for e in entries
                         if e.energies is not None
                         and e.energies.get("Ifreq") is None),
            n_transition_states=sum(1 for e in entries
                                     if e.energies is not None
                                     and e.energies.get("Ifreq") is not None),
            n_pathways=n_pathways,
            n_mechanism_steps=n_mechanism_steps,
            n_mass_balance_failures=n_mass_balance_failures,
            n_mass_balance_unresolved=n_mass_balance_unresolved,
        ),
        structures=entries,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--structures", type=Path, required=True,
                   help="directory of .xyz files")
    p.add_argument("--table", type=Path, required=True,
                   help="table.json from `extract-table`")
    p.add_argument("--compounds", type=Path, required=True,
                   help="compounds.json from `build`")
    p.add_argument("--aliases", default=None,
                   help='CSV: "stem=label,stem=label,..." for residual aliases')
    p.add_argument("--mechanism", type=Path, default=None,
                   help="mechanism.json with mechanism_sequence + spin_pairs "
                        "(see scripts/mechanism.py for schema)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--log", type=Path, default=None)
    p.add_argument("--paper-name", default="(unknown paper)")
    args = p.parse_args(argv)

    if not args.structures.is_dir():
        print(f"ERROR: --structures not a directory: {args.structures}",
              file=sys.stderr)
        return 2

    table_raw = json.loads(args.table.read_text())
    # Accept both the new wrapped shape ({"_units": ..., "rows": {...}}) and
    # the legacy bare-dict shape — caller chooses, downstream behaviour the same.
    if isinstance(table_raw, dict) and "rows" in table_raw and isinstance(
        table_raw["rows"], dict
    ):
        table_units = table_raw.get("_units", {})
        table = table_raw["rows"]
    else:
        table_units = {}
        table = table_raw
    compounds = json.loads(args.compounds.read_text())
    aliases = _parse_aliases(args.aliases)
    mechanism = load_mechanism(args.mechanism) if args.mechanism else None

    db = build(
        args.structures, table, compounds,
        extra_aliases=aliases,
        log_path=args.log,
        paper_name=args.paper_name,
        mechanism=mechanism,
        table_units=table_units,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # by_alias=True so the field serialises as the JSON key "_units".
    args.out.write_text(db.model_dump_json(indent=2, by_alias=True))
    md = db.metadata
    mech_tail = ""
    if mechanism is not None:
        mech_tail = (
            f", {md.n_pathways} pathways, {md.n_mechanism_steps} mech. steps, "
            f"{md.n_mass_balance_failures} imbalances, "
            f"{md.n_mass_balance_unresolved} unresolved labels"
        )
    print(
        f"si_index: wrote {args.out} — {md.n_structures} structures "
        f"({md.n_with_table} with table, {md.n_with_smiles} with SMILES, "
        f"{md.n_minima} minima, {md.n_transition_states} TS{mech_tail})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
