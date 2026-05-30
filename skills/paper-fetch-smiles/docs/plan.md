# SI-extraction extension to paper-fetch-smiles

## Goal

When a supporting-information PDF is part of the paper, the skill must also
extract every per-structure XYZ geometry, the DFT energy table, and a joined
`index.json` that ties XYZ ↔ energies ↔ `compounds.json` rows. Every extracted
`.xyz` must self-describe its charge and multiplicity.

## Architecture

```
SI PDF
  │
  ├── planner subagent (≤5 min)
  │     - reads SI, proposes: banner, columns, label regex, page marker,
  │       per-label {charge, multiplicity}, label aliases
  │     - writes:  si_config.json   (planner output, throwaway)
  │     - writes:  paper_fetch_log.md  (initial REVIEW notes)
  │
  ├── bash extraction  (deterministic, no LLM)
  │     - scripts/cli.py extract-table   → table.json
  │     - scripts/cli.py extract-xyz     → structures/*.xyz  (charge/mult in line 2)
  │     - scripts/cli.py build-index     → index.json
  │     - all three append REVIEW items to paper_fetch_log.md
  │
  └── reviewer subagent (≤5 min)
        - cross-checks ≥3 random structures vs SI PDF (atom count, label,
          first/last atom)
        - cross-checks Table S1 rows for 3 random labels
        - verifies every .xyz has charge=N multiplicity=M on line 2
        - appends VERIFIED / REVIEW items to paper_fetch_log.md
```

The skill drives planner → extract → reviewer in one run.

## New files

```
scripts/
  models.py          # pydantic v2 models (internal validation only)
  si_table.py        # generalized table parser (was parse_table_s1.py)
  si_xyz.py          # generalized XYZ extractor (was extract_si_xyz.py)
  si_index.py        # generalized index builder (was build_index.py)
docs/
  plan.md            # this file
references/
  si_extraction.md   # detailed reference for SI quirks per paper
```

`scripts/cli.py` gains three subcommands: `extract-table`, `extract-xyz`,
`build-index`. Each script is also runnable standalone as
`python -m scripts.si_xxx`.

## Pydantic models (internal only — JSON shape unchanged)

| Model | Used by | Notes |
|---|---|---|
| `SiTableRow` | si_table | dynamic column set; `extra='allow'` so flag-defined columns flow through |
| `SiAtom` | si_xyz | `element: str`, `xyz: tuple[float,float,float]` |
| `SiStructure` | si_xyz | `name`, `atoms: list[SiAtom]`, `charge: int`, `multiplicity: int` |
| `IndexEntry` | si_index | merged record |
| `IndexDB` | si_index | `metadata + structures[]` |
| `PaperCompound` | (Phase 2) | wraps PAPER_COMPOUND_TABLE rows |
| `ResolvedCompound` | (Phase 2) | wraps build_compound_db output rows |

Phase 1 (this branch) introduces the SI models. Phase 2 (separate branch) ports
the existing compound resolver to pydantic. **JSON shapes on disk are
byte-identical to today.**

## `.xyz` file convention (HARD)

Every `.xyz` the skill writes has charge + multiplicity in the line-2 comment:

```
24
charge=0 multiplicity=1   name=INT3-1a  (extracted from Zhang 2024 SI)
C  0.000  0.000  0.000
...
```

- Line 1: atom count (unchanged from XYZ spec).
- Line 2: comment line. MUST start with `charge=<int> multiplicity=<int>`.
  Free text may follow. ASE-style `extxyz` parsers and a regex one-liner both
  read this. `multiplicity` = `2S+1` (singlet=1, doublet=2, triplet=3, …),
  not the unpaired-electron count `S`.
- Lines 3+: `element x y z` in Å.

If charge or multiplicity is unknown for a label, the script does NOT write
the .xyz; it writes a `REVIEW` line in `paper_fetch_log.md` instead. No
silent neutral-singlet default.

## `paper_fetch_log.md` contract

A single markdown file in the paper directory, append-only, with two section
kinds:

```markdown
# paper-fetch-smiles log — <paper>

Generated <ISO timestamp>

## REVIEW — needs human attention

- [ ] **TS6-1f / TS5-1f label mismatch**: coord section uses TS6-1f, Table S1
      uses TS5-1f. Verified same physical structure? (`scripts/si_index.py`,
      aliases input)
- [ ] **INT3-1e: missing charge/multiplicity**: no entry in --cm-json and no
      default supplied. .xyz not written. (`scripts/si_xyz.py`)

## VERIFIED — reviewer-confirmed

- INT3-1a: 47 atoms, charge=0 multiplicity=1, first atom Ni 0.000 0.000 0.000
  — matches SI page S7.
- Table S1 row TS3-1e: E=-1785.100422, Ifreq=-363.66 — matches SI page S2.
```

Every REVIEW item has a checkbox and a reason. Every VERIFIED item has the
specific evidence the reviewer checked.

## Subagent contracts

### Planner (≤5 min)

**Input**: SI PDF path, paper directory.

**Output**:
- `si_config.json`: `{banner, columns, label_regex, page_marker, cm_map,
  aliases, table_label_regex}`
- Initial `paper_fetch_log.md` with REVIEW items for ambiguities

**Tools allowed**: Read (PDF pages), Bash (`pdftotext`, `grep`), Write.

**Prompt skeleton** lives in `references/si_extraction.md`.

### Reviewer (≤5 min)

**Input**: paper directory after extraction.

**Output**: appends to `paper_fetch_log.md` with VERIFIED + new REVIEW items.

**Tools allowed**: Read (PDF + .xyz + JSON), Bash, Edit (paper_fetch_log.md).

**Sampling protocol**: 3 random structures, 3 random Table S1 rows, every .xyz
checked for `charge=N multiplicity=M` on line 2.

## Generalization knobs (all on CLI, no per-paper config files)

| Script | Flags |
|---|---|
| `extract-table` | `--si-pdf`, `--banner`, `--columns "E,G,CGFE,ETHF,GTHF,Ifreq?"`, `--label-regex`, `--out`, `--log` |
| `extract-xyz` | `--si-pdf`, `--banner`, `--page-marker-regex`, `--cm-json`, `--default-charge`, `--default-multiplicity`, `--out-dir`, `--log` |
| `build-index` | `--structures`, `--table`, `--compounds`, `--aliases "A=B,C=D"`, `--out`, `--log` |

`--cm-json` shape: `{"<label>": {"charge": 0, "multiplicity": 1}, ...}`.
A label not in the map AND with no `--default-*` supplied → REVIEW log + skip.

## Out of scope (Phase 2+)

- Full pydantic migration of `compound_db.py` / `pubchem_client.py` /
  `tmqmg_l_client.py` / `render.py` / `review.py`.
- pydantic model export from `compounds.py`.
- Verifying ni-louie / ni-tsuda compounds.json are byte-identical after a
  Phase-2 migration.
