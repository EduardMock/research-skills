---
name: chem-db-lookup
description: Use when you need to resolve a compound, ligand, or crystal structure against a public chemical database — a name/SMILES/InChI/CID to PubChem canonical data, a ligand to tmQMg-L, or a crystal structure (by CSD refcode, COD-ID, formula, or DOI) to a CIF and discrete-molecule .xyz. Triggers: "look up this compound", "resolve these names to SMILES/CIDs", "fetch the crystal structure of X", "get an xyz from the CSD/COD for X", "bulk-resolve compounds.py into compounds.json". For converting a whole paper use paper-fetch-smiles; for writing a SMILES by hand use authoring-smiles.
---

# chem-db-lookup

Clients-only, deterministic lookups against the chemically relevant public
databases. Reproducible (no agent-driven curl improvisation) so the same input
gives the same output, and it leaves **nothing** in your project tree.

## Databases

| Database | What | Keyed by |
|---|---|---|
| **PubChem** | canonical SMILES / InChI / InChIKey / CID / MW | name, SMILES, InChI, InChIKey, CID |
| **tmQMg-L** | crystallographically-observed ligand metadata + denticity | SMILES (RDKit-canonicalised both sides) |
| **CSD → COD** | crystal structure → CIF → discrete-molecule `.xyz` | CSD refcode (licensed), COD-ID, Hill formula, free text/DOI |

## When NOT to use

- Converting an entire paper into a catalog → `paper-fetch-smiles` (it *calls* this skill for the resolution step).
- Authoring a SMILES by hand → `authoring-smiles`. Computing descriptors/similarity → `rdkit`.
- Non-chemistry databases (genomics, materials-beyond-crystals, economics) — out of scope by design.

## Cache policy — NOTHING is left in the project

This is a hard rule, not a preference:

- **Per-query results** (PubChem responses, fetched CIF/xyz when you don't ask to keep them) live in a temp dir that is **deleted when the command exits**. The CLI does this for you (`tempfile.TemporaryDirectory`). Never point a cache at the project dir.
- **Large reference datasets** (tmQMg-L's ~19 MB CSV) cache once under `~/.cache/chem-db-lookup/` — sandbox-writable, out of the project, reused across runs. Never re-downloaded per run, never committed.

**Red flag:** a `.compound_cache/`, `pubchem_cache.json`, or `*.cif` left sitting in the working copy after a lookup → you bypassed the CLI's temp-cache handling. Fix the invocation; don't commit the cache.

## Crystal structures: CSD preferred, COD fallback

`crystal` tries the CSD first (CCDC `ccdc` Python API) **only when** `ccdc`
imports AND a licence is usable; any failure falls through to **COD** (open,
reproducible) with a logged note. Default to COD for anything you intend to
share — the CSD path can't be reproduced without a licence.

**The asymmetric-unit trap (why we don't just `obabel in.cif`):** a CIF stores
only the asymmetric unit + symmetry operators. A naive `obabel in.cif -O out.xyz`
emits that fragment (e.g. half a molecule on a special position). The CLI runs
**two passes** — `--fillUC keepconnect` to expand symmetry into the full cell,
then `--separate -m` to split it into per-molecule files — and **dedupes the
resulting fragments by element formula** so you get one `.xyz` per *unique*
molecule, not Z symmetry copies. (The passes can't be combined: openbabel 3.x
drops the cell when `--separate` shares an invocation with `--fillUC`.)

**Limitation — verify the output.** openbabel does not unwrap molecules across
periodic boundaries, and many X-ray CIFs omit hydrogens. So you may get a
boundary-fragmented molecule or an H-less skeleton. **Always check the returned
atom counts / formulas against what you expect**; for production QM, optimise
the geometry afterwards (e.g. `g-xtb`) rather than trusting the raw crystal xyz.

Crystal `.xyz` are *experimental* geometries: they do **not** carry the
`charge=/multiplicity=` line-2 contract (that's `si-xyz-extract` for DFT inputs).
Charge/spin are undefined for a packed crystal — supply them yourself for QM.

## Quick reference

```bash
# Bulk-resolve compounds.py's dump (or any {compounds:[...]} JSON) → compounds.json
micromamba run -n chem-db-lookup python -m scripts.cli build \
  --input _compounds_input.json --output compounds.json --review --match-tmqml

# One-off
micromamba run -n chem-db-lookup python -m scripts.cli lookup --query "ferrocene"
micromamba run -n chem-db-lookup python -m scripts.cli lookup --smiles "c1ccccc1"

# Crystal → CIF + discrete .xyz (CSD-preferred, COD fallback)
micromamba run -n chem-db-lookup python -m scripts.cli crystal \
  --out-dir ./xtal --refcode FEROCE --formula "C10 H10 Fe"
micromamba run -n chem-db-lookup python -m scripts.cli crystal \
  --out-dir ./xtal --cod-id 2310525        # direct COD fetch, no CSD attempt needed
```

Run any subcommand with `--help` for all flags. `build`/`lookup` exit 2 if every row is unresolved; `crystal` exits 2 if both sources fail.

## Common mistakes

| Mistake | Fix |
|---|---|
| Leaving a cache file in the project | Use the CLI (temp cache auto-deleted); datasets go to `~/.cache/chem-db-lookup`. |
| `obabel in.cif` → half a molecule | Symmetry not expanded. The CLI fills the cell then separates (two passes) + dedupes; still verify atom count/formula. |
| Expecting CSD to work everywhere | CSD needs a licensed `ccdc` install. Without it, pass `--cod-id`/`--formula`/`--text` for COD. |
| Putting `charge=/mult=` on a crystal `.xyz` | Crystal geometries are experimental; c/m are undefined here — that contract belongs to `si-xyz-extract`. |
| Bulk-resolving with a project-local `--cache-dir` | There is no `--cache-dir` flag anymore — caching is automatic and ephemeral. |

## Output: `compounds.json`

`{metadata, expected_electronic_structure, compounds[]}` — byte-stable shape so
downstream (`si-xyz-extract` join, notebooks) needs no changes. Each compound row
carries PubChem fields, the hand-authored `fallback_smiles` (carried through, never
dropped), optional `tmqml` block, and an optional RDKit `review` block.

## Env

`chem-db-lookup` (`pydantic`, `rdkit`, `requests`, `openbabel`), defined at
`/storage/edm/envs/chem-db-lookup.yml`:

```bash
micromamba env create -f /storage/edm/envs/chem-db-lookup.yml
```

The CSD path additionally needs the CCDC `ccdc` package + licence (not in the yml).

## Related skills

- `paper-fetch-smiles` — the orchestrator; hand-authors `compounds.py` then calls this skill's `build` for resolution.
- `authoring-smiles` — write the `fallback_smiles` this skill resolves.
- `g-xtb` — consumes crystal `.xyz` (supply `--chrg`/`--uhf` yourself; crystal c/m are undefined).
- `rdkit` — descriptors / similarity on resolved structures.
