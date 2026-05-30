---
name: si-xyz-extract
description: Use when a computational chemistry paper ships a Supporting-Information PDF with DFT-optimized geometries and an energy table, and you need them as machine-readable files — per-structure .xyz (each self-describing charge & multiplicity) and a parsed energy table.json. Triggers: "extract the DFT structures from the SI", "pull the optimized geometries into xyz", "parse the SI energy table", "get xyz files for g-xTB from this SI PDF". For converting a whole paper use paper-fetch-smiles; to join structures+energies into a mechanism graph use reaction-mechanism-graph.
---

# si-xyz-extract

Turn a computational SI PDF into `structures/*.xyz` (one per stationary point)
and `table.json` (DFT energies keyed by SI label). Deterministic `pdftotext`
parsing — an LLM only decides knobs (banner, columns, charge/multiplicity map)
and verifies output. Part of the `paper-fetch-smiles` pipeline; usable alone.

## When NOT to use

- Converting an entire paper into a compound catalog → `paper-fetch-smiles`.
- Joining the extracted structures/energies into a catalytic-cycle graph with mass balance → `reaction-mechanism-graph` (`build-index`).
- Crystal-structure geometries (experimental, not DFT) → `chem-db-lookup` `crystal`.

## The `.xyz` HARD rule — every `.xyz` self-describes charge and multiplicity

This is the core discipline of the skill. Every `.xyz` embeds `charge` and
`multiplicity` in the line-2 comment, **first**, before any free text:

```
41
charge=0 multiplicity=1  name=Ni(COD)2  (Zhang 2024 Inorganics SI)
Ni      0.00008700     -0.00019300      0.00015700
...
```

- Line 1: atom count. Line 2: `charge=<int> multiplicity=<int>` MUST come first.
- `multiplicity = 2S+1` (singlet=1, doublet=2, triplet=3) — **not** the unpaired-electron count `S`.
- A bare comment ("optimised geometry", "from CID 12345") is **not enough**.

**If charge or multiplicity is unknown for a label, do NOT write the file.** Log a
REVIEW item to `paper_fetch_log.md` and skip. `extract-xyz` enforces this — there
is **no silent neutral-singlet fallback**.

**Why it's a hard rule, not a convenience:** a charged or open-shell species
silently written as neutral singlet makes g-xTB build the SCF for the wrong number
of electrons — on a metal the SCF diverges or (worse) converges to a clean-looking
but meaningless number, silently poisoning every downstream relative energy. A
*skipped* structure the user knows is missing beats a *wrong* one they don't.

**Red flags — STOP:**
- About to write an `.xyz` whose line 2 lacks `charge=N multiplicity=M`. Fix the source; never emit it.
- About to default charge=0 / multiplicity=1 for a structure whose c/m you couldn't find. The correct move is REVIEW-log + skip.
- "It's probably neutral closed-shell" — that's a guess turned into a fabricated input. Don't.

## Commands

Both accept `--log paper_fetch_log.md` and `--paper-name "<First Author Year>"`.
All paper-specific knobs are CLI flags — no per-paper config files. Run `--help`
for the full flag set.

```bash
# DFT energy table → table.json. Columns default "E,G,CGFE,ETHF,GTHF,Ifreq?"
# (trailing `?` = optional col). --banner stops parsing at the coord section.
micromamba run -n paper-fetch-smiles python -m scripts.cli extract-table \
  --si-pdf si.pdf --out table.json --columns "E,G,CGFE,ETHF,GTHF,Ifreq?" \
  --log paper_fetch_log.md --paper-name "<First Author Year>"

# Per-structure .xyz. --cm-json is {"<label>": {"charge": int, "multiplicity": int}}
# (planner-authored); --default-charge/-multiplicity cover the rest. Labels with
# neither are SKIPPED + REVIEW-logged (HARD rule).
micromamba run -n paper-fetch-smiles python -m scripts.cli extract-xyz \
  --si-pdf si.pdf --out-dir structures --cm-json cm.json \
  --default-charge 0 --default-multiplicity 1 \
  --log paper_fetch_log.md --paper-name "<First Author Year>"
```

## Subagent contracts

**Planner (≤ 5 min)** — reads the SI, decides knobs, writes a starter log:

> Read the SI PDF at <path>. Identify (a) the banner phrase that starts the coordinate section; (b) the DFT table's column schema with units (Hartree / cm⁻¹ / kcal·mol⁻¹); (c) the structure-label regex; (d) the charge and multiplicity for **every** structure name → `cm.json`. For anything ambiguous, append a REVIEW item to `paper_fetch_log.md`. Hard cap: 5 min.

**Reviewer (≤ 5 min)** — verifies against the SI PDF:

> Sample 3 random `.xyz` from `structures/` — verify atom count, first/last atom element+coords, and the line-2 `charge=N multiplicity=M` against the SI. Sample 3 random `table.json` rows — verify floats against the SI Table. Append VERIFIED / REVIEW to `paper_fetch_log.md`. **Write VERY SHORT notes** — one line each: VERIFIED = `<label>: <what> = <value> — matches SI p.SN`; REVIEW = `<area>: <one-line problem>`. Terse and greppable. Hard cap: 5 min.

## `paper_fetch_log.md` contract

Append-only; nothing is ever deleted, only checked off. REVIEW items get a
checkbox + script source; VERIFIED items get the specific evidence checked.

```markdown
## REVIEW — needs human attention
- [ ] si_table: duplicate row for label `INT7-4e` — keeping first  _(scripts/si_table.py)_
- [ ] si_xyz: skipping `INT3-1e` — no entry in --cm-json and no defaults  _(scripts/si_xyz.py)_

## VERIFIED — reviewer-confirmed
- INT3-1a: 47 atoms, charge=0 multiplicity=1, first atom Ni 0.000 0.000 0.000 — matches SI page S7.
```

## Cross-check before reporting done

- `structures/*.xyz` count vs `table.json` row count (minus legitimate SI duplicates — captured in REVIEW).
- Every `.xyz` line 2 matches `charge=-?\d+ multiplicity=\d+` (grep it).
- `paper_fetch_log.md` exists; nothing skipped silently.

## Env

`paper-fetch-smiles` env (Pydantic) + system `pdftotext` (poppler, `/usr/bin`).
`_log.py` provides the shared `paper_fetch_log.md` contract.

## Related skills

- `paper-fetch-smiles` — orchestrator; runs this after the compound catalog when an SI PDF exists.
- `reaction-mechanism-graph` — consumes `structures/*.xyz` + `table.json` into `index.json` with mass balance.
- `g-xtb` — consumes these `.xyz` directly: line-2 `charge=N multiplicity=M` maps to `xtb --chrg N --uhf (multiplicity−1)`.
