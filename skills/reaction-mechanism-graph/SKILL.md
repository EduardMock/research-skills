---
name: reaction-mechanism-graph
description: Use when you have per-structure .xyz geometries (with charge/multiplicity), a DFT energy table, and a catalytic cycle, and you need them joined into one indexed mechanism graph with mass-balance verification of every elementary step. Triggers: "build the mechanism graph", "join the structures, energies and compounds into an index", "mass-balance the catalytic cycle", "build-index for this mechanism", "check every step conserves atoms and charge". For extracting the .xyz/table first use si-xyz-extract; for the compound catalog use paper-fetch-smiles.
---

# reaction-mechanism-graph

Join `structures/*.xyz` ↔ `table.json` ↔ `compounds.json` (+ optional
`mechanism.json`) into `index.json`, annotating every structure with its graph
neighbours and **verifying mass balance for every elementary step**. Final stage
of the `paper-fetch-smiles` pipeline; usable alone once the inputs exist.

## When NOT to use

- Extracting the `.xyz` / energy table from the SI first → `si-xyz-extract`.
- Building the compound catalog → `paper-fetch-smiles`.

## Command

```bash
micromamba run -n paper-fetch-smiles python -m scripts.cli build-index \
  --structures structures --table table.json --compounds compounds.json \
  --output index.json --mechanism mechanism.json \
  --aliases "NiPMe32=Ni(L1)2" \
  --log paper_fetch_log.md --paper-name "<First Author Year>"
```

`--mechanism` is optional; without it you still get the structure↔energy↔compound
join. `--aliases` (CSV `stem=label,...`) handles residual coord-vs-table label
mismatches (e.g. SI files `Ni(L1)2` in the table but `Ni(PMe3)2` in the coords).

## `mechanism.json` — catalytic cycle as data

Annotates every structure with `pathways`, `next_steps`, `prev_steps`,
`spin_partners` AND runs mass-balance verification per step:

```json
{
  "mechanism_sequence": [
    {"pathway": "1a", "steps": [
       {"from": "Ni(COD)2", "to": "Ni(PMe3)2", "join": ["PMe3","PMe3"], "leave": ["COD","COD"]},
       {"from": "Ni(PMe3)2", "to": "INT1-1a", "join": ["1"]},
       {"from": "INT2-1a", "to": "TS1-1a"},
       {"from": "TS1-1a", "to": "INT3-1a"}]},
    {"pathway": "1b", "steps": [
       {"from": "INT2-1a", "to": "TS1-1b"},
       {"from": "TS1-1b", "to": "INT3-1a"}]}
  ],
  "spin_pairs": [["INT5-1f", "INT5-1f-triplet"]]
}
```

**Encode every pathway the paper documents.** Forks/merges are first-class: any
node listed as `from`/`to` in two pathways is automatically a fork (multiple
`next_steps`) or merge (multiple `prev_steps`) — no node-type marker needed.
Partial mechanisms miss bypass routes and off-cycle deactivation. Every label in
`from / to / join / leave / spin_pairs` must match a `.xyz` stem (sanitised
paper_id is the lookup key — kept byte-identical to `si-xyz-extract`'s sanitiser).

## The three mass-balance invariants (per step)

1. **Per-element atom count**: `from.elements + Σ join.elements == to.elements + Σ leave.elements`
2. **Net charge**: same, with `.charge`
3. **Electron parity vs multiplicity parity**: `(ΣZ − charge) mod 2 == (multiplicity − 1) mod 2`, per-step and per-species

Real imbalances → `paper_fetch_log.md` REVIEW with a per-element delta. Lookup
misses are flagged **separately** ("aliasing issue — fix with `--aliases`") and
counted as `n_mass_balance_unresolved`, NOT as chemistry failures.

## A non-zero `n_mass_balance_failures` is a BLOCKER, not a warning

This is the skill's discipline rule. `build-index` succeeding and the `.xyz`
parsing cleanly are *different checks* from mass balance. Even one failure means
an elementary step does not conserve atoms/charge — most often a missing
co-reactant/co-product the paper left implicit (H⁺, H₂O, a lost ligand, solvent,
a counterion), a wrong protonation/charge/multiplicity on a structure, or a
mis-mapped step. Each silently corrupts the reaction energy of that step.

**Do not report the index complete while `n_mass_balance_failures > 0`.** Surface
the failing steps (which steps, the atom/charge delta), give the likely chemical
cause, and either fix it (add the missing species to `join`/`leave`, correct the
c/m, re-map the step) or get the imbalance explicitly accepted. "The extraction
worked" is not "the mechanism is correct."

**Red flags — STOP:**
- About to report done with `index.json.metadata.n_mass_balance_failures > 0`.
- Treating a per-element imbalance as noise — it points at a missing atom in an `.xyz` or a wrong `join`/`leave` term.
- Confusing `n_mass_balance_unresolved` (a label lookup miss — fix with `--aliases`) with a real chemistry failure.

## Cross-check before reporting done

- `index.json.metadata.n_mass_balance_failures == 0` (or every remaining imbalance explicitly explained).
- `n_mass_balance_unresolved == 0` (else fix `--aliases`).
- `paper_fetch_log.md` REVIEW section has no unaddressed mass-balance items.

## Env

`paper-fetch-smiles` env (Pydantic). `_log.py` provides the shared
`paper_fetch_log.md` contract. The `mechanism.py` `_Z` atomic-number table
currently covers up to Hg (Z=80) — heavier elements contribute 0 to the parity
sum, so extend it before trusting parity checks on actinide complexes.

## Related skills

- `si-xyz-extract` — produces the `structures/*.xyz` + `table.json` this joins.
- `paper-fetch-smiles` — orchestrator; produces `compounds.json` and runs this last.
- `paper-figure-extract` — its `mechanism_from_diagram.json` / scheme `reactions[]` seed `mechanism.json`.
- `g-xtb` — recompute a step's species if you suspect a wrong charge/multiplicity behind an imbalance.
