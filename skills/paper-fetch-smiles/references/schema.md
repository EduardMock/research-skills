# JSON record schemas

The skill's contract with upstream and downstream consumers. Treat as **append-only** — additions OK, never change a field's meaning or drop one without a major version bump.

## Input schema — one row

The input to `python -m scripts.cli build` (or `build_compound_db()`) is a JSON list of these objects.

| Field | Type | Required | Notes |
|---|---|---|---|
| `paper_id` | string | recommended | The identifier used in the paper (e.g., `"1"`, `"Ni(COD)2"`, `"IPr"`). Carried through to the output verbatim. |
| `role` | string | optional | Free-form tag — `"catalyst_precursor"`, `"ligand"`, `"substrate"`, `"product"`, etc. Carried through. |
| `name` | string | required (when `query_type="name"`) | The query passed to PubChem. |
| `fallback_smiles` | string | recommended | Used when PubChem can't resolve `name`. Strongly recommended for organometallics, NHCs, and paper-internal codes. |
| `query_type` | string | optional | One of `"name"` (default), `"smiles"`, `"inchi"`, `"inchikey"`, `"cid"`. Controls which PubChem PUG REST namespace is hit. |
| any other keys | any | optional | Carried through unchanged into the output record. Useful for paper-specific metadata (yield, reaction_id, ...). |

Minimal example:

```json
[
  {"paper_id": "1", "role": "diyne",
   "name": "dimethyl 2,2-di(but-2-yn-1-yl)malonate",
   "fallback_smiles": "CC#CCC(CC#CC)(C(=O)OC)C(=O)OC"}
]
```

## Output schema — top-level

```json
{
  "metadata": { ... },
  "compounds": [ ... ]
}
```

### `metadata`

| Field | Type | Notes |
|---|---|---|
| `generated_at` | ISO 8601 string | UTC timestamp of the build. |
| `n_compounds` | int | Total rows in `compounds`. |
| `n_resolved_pubchem` | int | Rows where `source == "pubchem"`. |
| `n_fallback` | int | Rows where `source == "fallback"`. |
| `n_unresolved` | int | Rows where `source == "unresolved"`. |
| `n_tmqml_matched` | int | Rows with a non-null `tmqml`. |
| `sources_used` | list[string] | Subset of `["pubchem", "cache", "fallback", "unresolved", "tmqml"]`. |
| `tmqml_sha` | string \| null | The tmQMg-L git ref used, or null if matching disabled. |
| `cache_dir` | string | Path to the on-disk cache. |
| `review_enabled` | bool | Whether the RDKit review pass ran. |

### `compounds[i]` — one resolved record

| Field | Type | Nullable | Notes |
|---|---|---|---|
| `paper_id` | string | yes | From input. |
| `role` | string | yes | From input. |
| `query` | string | yes | What was actually sent to PubChem. |
| `query_type` | string | no | `"name"`, `"smiles"`, ... |
| `name` | string | yes | Caller-supplied name (preferred over PubChem's preferred name). |
| `iupac` | string | yes | PubChem's IUPAC name. |
| `smiles` | string | yes | Preferred SMILES (isomeric if PubChem provided one, else canonical). |
| `canonical_smiles` | string | yes | PubChem `CanonicalSMILES` (rewritten by review pass if RDKit available). |
| `isomeric_smiles` | string | yes | PubChem `IsomericSMILES`. |
| `inchi` | string | yes | Full InChI. |
| `inchikey` | string | yes | Full InChIKey (`XXXX-XXXX-X`). |
| `cid` | int | yes | PubChem CID. |
| `mw` | float | yes | Molecular weight (g/mol). |
| `fallback_smiles` | string | yes | Echoed from input. |
| `source` | string | no | `"pubchem"`, `"cache"`, `"fallback"`, or `"unresolved"`. |
| `tmqml` | object \| null | yes | tmQMg-L hit (see below) or null. |
| `review` | object | yes | RDKit review block (see below), only present if review enabled. |
| any extra input keys | any | yes | Carried through. |

### `compounds[i].tmqml` — tmQMg-L hit

```json
{
  "ligand_id": "L1234",
  "smiles": "c1ccncc1",
  "denticity": 1,
  "charge": 0,
  "n_atoms": 11,
  "n_heavy_atoms": 6,
  "metal_bound_to": "Pd",
  "coordinating_atoms": "0",
  "extras": { /* version-specific extra columns */ }
}
```

`extras` is a free-form pass-through of any tmQMg-L columns the projector didn't promote — schema there evolves; we don't pin it.

### `compounds[i].review` — RDKit review block

```json
{
  "rdkit_available": true,
  "smiles_ok": true,
  "differs_from_fallback": false,
  "notes": []
}
```

| Field | Meaning |
|---|---|
| `rdkit_available` | True iff RDKit was importable at runtime. |
| `smiles_ok` | True if `smiles` parsed; False if not; null if RDKit absent. |
| `differs_from_fallback` | True iff PubChem's SMILES and `fallback_smiles` hash to different connectivity skeletons. PubChem often returns a charged form (e.g., NHC → imidazolium ylide) — surfacing this lets the caller decide which to trust. |
| `notes` | Free-form list of strings flagging issues: `"no_smiles"`, `"smiles_unparseable"`, `"connectivity_differs_from_fallback"`, ... |

## Versioning

This schema is unversioned today. Treat any breaking change (renaming a field, changing nullability, removing a field) as a major version bump that requires migration in the upstream pipeline. Additive changes (new fields, new optional metadata) are always fine.
