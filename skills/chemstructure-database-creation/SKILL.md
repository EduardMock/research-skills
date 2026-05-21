---
name: chemstructure-database-creation
description: Use when building a JSON compound database from a list of molecule names/SMILES — typically the post-extraction stage of a paper-conversion pipeline. Resolves each query against PubChem (PUG REST → IUPAC, canonical SMILES, InChI, InChIKey, MW, CID) and optionally matches ligand SMILES against the tmQMg-L crystallographic ligand set (denticity, formal charge, donor atoms, DFT descriptors). Standalone — calls live HTTP APIs, caches on disk, no clone required. Trigger on phrases like "build compound database", "resolve compound names", "look up on PubChem", "enrich paper compound table", "match against tmQMg-L", "canonicalize SMILES", "compound catalog from paper", or any pipeline that needs a normalized .json catalog with canonical identifiers per compound. Bias toward triggering — anywhere a name → enriched-record resolution is needed, this is the skill.
---

# Chem-Structure Database Creation

## Purpose

This skill is a **stand-alone compound-resolution stage** for a paper-conversion pipeline (or any workflow that produces a list of compound names and needs them canonicalized). It:

1. **Fetches** structural data from public APIs:
   - **PubChem** PUG REST (no API key, ~5 req/s): IUPAC name, canonical SMILES, isomeric SMILES, InChI, InChIKey, MW, CID.
   - **tmQMg-L** raw CSVs on GitHub: crystallographically observed ligands with denticity, formal charge, metal-coordinating-atom indices, and DFT descriptors.
2. **Matches** queries across sources by name → SMILES → InChIKey, with a sensible fallback chain.
3. **Reviews** each record (RDKit-based, soft-optional): canonicalize SMILES, sanity-check valence, flag inconsistencies between PubChem and any caller-supplied fallback SMILES.
4. **Emits** a uniform JSON compound database with a documented schema.

Hard dependencies: Python 3.8+ and `requests`. Soft-optional: `rdkit` (for the review step), `pandas` (not used — stdlib `csv` is enough).

## When to trigger

Primary:
- Paper-extraction stage emits `[{paper_id, role, name, fallback_smiles?}, ...]` and you need canonical identifiers per row.
- You have a free-form list of compound names/SMILES and want a normalized `.json` catalog.
- You have ligand SMILES and want to know whether it appears in tmQMg-L (crystallographically observed → real geometry + DFT descriptors).
- A downstream step needs InChIKey-keyed records (for joins with property databases, dedup, etc.).

Secondary:
- Interactive PubChem lookups during analysis.
- Building a local cache so re-runs are offline.

Do NOT use for:
- Hand-authoring SMILES from a figure → use `authoring-smiles`.
- Editing existing SMILES via NL instruction → use `fast-smiles`.
- Generic RDKit operations (fingerprints, descriptors not on PubChem) → use `rdkit`.

## Pipeline shape

```
            ┌──────────────────────────────────┐
paper  →    │  upstream extraction agent       │   ← out of scope
            │  yields: [{paper_id, role,       │
            │           name, fallback_smiles}]│
            └──────────────┬───────────────────┘
                           ▼
            ┌──────────────────────────────────┐
            │  THIS SKILL                      │
            │  scripts/cli.py build ...        │
            │  └─ pubchem_client.fetch()       │
            │  └─ tmqmg_l_client.match()       │
            │  └─ review.review_record()       │
            └──────────────┬───────────────────┘
                           ▼
                  compounds.json
                  (canonical schema)
```

## Record schemas

### Input — one row

Minimum fields: `paper_id`, `name`. Everything else optional. `fallback_smiles` is strongly recommended (PubChem misses on organometallics, NHCs, paper-internal codes — fallback keeps the record useful instead of `null`).

```json
{
  "paper_id": "Ni(COD)2",
  "role": "catalyst_precursor",
  "name": "bis(1,5-cyclooctadiene)nickel(0)",
  "fallback_smiles": "C1CC=CCCC=C1.C1CC=CCCC=C1.[Ni]"
}
```

### Output — one resolved compound

Every field present (unknowns become `null`, never missing). See `references/schema.md` for the full table with types.

```json
{
  "paper_id": "Ni(COD)2",
  "role": "catalyst_precursor",
  "query": "bis(1,5-cyclooctadiene)nickel(0)",
  "name": "bis(1,5-cyclooctadiene)nickel(0)",
  "iupac": "bis((1Z,5Z)-cycloocta-1,5-diene);nickel",
  "smiles": "C1CC=CCCC=C1.C1CC=CCCC=C1.[Ni]",
  "canonical_smiles": "C1CC=CCCC=C1.C1CC=CCCC=C1.[Ni]",
  "isomeric_smiles": null,
  "inchi": "InChI=1S/2C8H12.Ni/...",
  "inchikey": "JRTIUDXYIUKIIE-KZUMESAESA-N",
  "cid": 12519307,
  "mw": 275.05,
  "fallback_smiles": "C1CC=CCCC=C1.C1CC=CCCC=C1.[Ni]",
  "source": "pubchem",
  "tmqml": null,
  "review": {"smiles_ok": true, "differs_from_fallback": false, "notes": []}
}
```

`source` ∈ `{"pubchem", "cache", "fallback", "unresolved"}`.
`tmqml` is `null` unless tmQMg-L matching was requested AND succeeded; on hit it carries `{ligand_id, smiles, denticity, charge, n_heavy_atoms, ...}`.

### Output — full database

```json
{
  "metadata": {
    "generated_at": "2026-05-21T10:23:45+00:00",
    "n_compounds": 27,
    "sources_used": ["pubchem", "tmqml"],
    "tmqml_sha": "main",
    "cache_dir": ".compound_cache"
  },
  "compounds": [ /* one record per row */ ]
}
```

## Workflows

### A) Headline: paper-extracted list → compounds.json

```bash
python -m scripts.cli build \
  --input  paper_compounds.json \
  --output compounds.json \
  --cache-dir .compound_cache \
  --match-tmqml \
  --review
```

What happens:
1. Parse input JSON (list of `{paper_id, name, fallback_smiles?, ...}`).
2. For each row, `pubchem_client.fetch(name)` — cached on disk.
3. If `--match-tmqml`: `tmqmg_l_client.match_by_smiles(record["smiles"] or fallback_smiles)`. tmQMg-L CSV is downloaded once and indexed by canonical SMILES + InChIKey.
4. If `--review`: `review.review_record()` canonicalizes SMILES (RDKit), flags `differs_from_fallback`, and records valence/charge issues in `review.notes`.
5. Write `{metadata, compounds: [...]}` to `--output`.

The cache dir is the single source of truth across runs. Delete it for a clean re-fetch; commit it for a reproducible snapshot.

### B) One-off PubChem lookup

```python
from scripts.pubchem_client import pubchem_fetch
rec = pubchem_fetch("1,3-bis(2,6-diisopropylphenyl)imidazol-2-ylidene")
print(rec["smiles"], rec["inchikey"])
```

Cache file defaults to `./pubchem_cache.json`; pass `cache_path=` to override.

### C) Is this ligand in tmQMg-L?

```python
from scripts.tmqmg_l_client import TmQMgLClient
client = TmQMgLClient(cache_dir=".tmqml_cache")
hit = client.match_by_smiles("c1ccncc1")          # pyridine
# {"ligand_id": "L1234", "denticity": 1, "charge": 0, ...} or None
```

First call downloads `ligands_misc_info.csv` (~19 MB) from raw.githubusercontent.com into the cache dir. Subsequent calls are local.

### D) Library mode (no CLI)

```python
from scripts.compound_db import build_compound_db

with open("paper_compounds.json") as f:
    rows = json.load(f)

db = build_compound_db(
    rows,
    cache_dir=".compound_cache",
    match_tmqml=True,
    review=True,
)
# db == {"metadata": {...}, "compounds": [...]}
```

`build_compound_db` is the single function the upstream pipeline should import. It's small and intentional — its surface area is the API contract for downstream integrators.

## Scripts overview

| Path | Purpose |
|---|---|
| `scripts/pubchem_client.py` | Cached PubChem PUG REST client (pure `requests`). Handles 429 with exponential backoff. |
| `scripts/tmqmg_l_client.py` | tmQMg-L CSV fetcher + SMILES/InChIKey matcher. Downloads on first use; caches locally. |
| `scripts/compound_db.py` | Orchestrator: input list → enriched compound DB. `build_compound_db()` is the public function. |
| `scripts/review.py` | RDKit-based SMILES validation/canonicalization. Degrades gracefully if RDKit absent. |
| `scripts/cli.py` | Entry point for the paper-conversion pipeline (`python -m scripts.cli build ...`). |

Only `requests` is a hard dependency. RDKit is soft-optional. Pandas is not used.

## Caching strategy

| What | Where | Format | Invalidation |
|---|---|---|---|
| PubChem fetches | `<cache_dir>/pubchem_cache.json` | JSON dict, key = `"<query_type>:<query>"` | `force=True` or delete file |
| tmQMg-L CSVs | `<cache_dir>/tmQMg-L/*.csv` | Verbatim from raw.githubusercontent.com | Delete; or change `--tmqml-sha` |
| tmQMg-L lookup index | `<cache_dir>/tmQMg-L/index.json` | `{smiles: ligand_id, inchikey: ligand_id}` | Auto-rebuilt when CSV changes |

All caches are plain JSON/CSV — safe to commit alongside the output DB for reproducibility, or to gitignore for a fresh fetch each run.

## CLI reference

```
python -m scripts.cli build \
  --input  INPUT_JSON \
  --output OUTPUT_JSON \
  [--cache-dir DIR]           default ./.compound_cache
  [--match-tmqml]             enable tmQMg-L matching pass
  [--review]                  enable RDKit review pass
  [--tmqml-sha SHA]           pin tmQMg-L to a commit (default: main)
  [--force-refetch]           bypass PubChem cache
  [--rate-limit N]            PubChem requests/sec (default 4)
```

Exit codes: `0` success, `1` input parse error, `2` all rows unresolved.

A lookup helper is also exposed:

```
python -m scripts.cli lookup --query "pyridine"
python -m scripts.cli lookup --smiles "c1ccncc1" --match-tmqml
```

## Common pitfalls

| Pitfall | What to do |
|---|---|
| PubChem rate-limit (429) | Default 4 req/s with exponential-backoff retry. Lower to 2 for big jobs. |
| Name lookup misses (organometallics, NHCs, paper-internal codes like "1", "22") | Always pass `fallback_smiles`. The resolver writes it under `source: "fallback"` instead of leaving the row null. |
| tmQMg-L SMILES not canonical-matching the query | tmQMg-L stores RDKit-canonical SMILES with explicit metal-binding markers. Canonicalize the query with RDKit first, or rely on the InChIKey path (works without RDKit if PubChem returned an InChIKey). |
| PubChem returns charged form (e.g., NHCs as imidazolium ylides) | This is correct PubChem behavior. The review step records `differs_from_fallback: true` so you know — don't silently overwrite. |
| Air-gapped use | First call needs internet. Prime the cache on a connected machine, then commit `<cache_dir>` and run offline. |
| Schema drift over time | Add fields to the output only; keep existing fields' meaning stable. Document additions in `references/schema.md`. |

## References

- `references/schema.md` — Full JSON record schemas (input + output), with types and nullability.
- `references/pubchem_api.md` — PubChem PUG REST quick reference (endpoints, rate limits, fallbacks).
- `references/tmqmg_l.md` — tmQMg-L dataset background (provenance, file layout, descriptor columns).

## Related skills

- `authoring-smiles` — hand-author fallback SMILES when PubChem misses (organometallics, NHCs).
- `fast-smiles` — edit an existing SMILES via NL instructions.
- `rdkit` — descriptors/fingerprints/similarity beyond what this skill covers.
