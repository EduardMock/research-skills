---
name: mol-image-to-smiles
description: Use when converting a 2D molecular structure image (PNG/JPG of a single molecule cropped from a paper figure, ChemDraw export, or hand-drawn sketch) into a SMILES string. Primary engine is DECIMER (Steinbeck group, EfficientNet-V2 + transformer, runs locally on CPU/GPU), optional fallback is MolNextR via HuggingFace. Trigger on phrases like "image to SMILES", "OCSR", "recognise this structure", "extract SMILES from figure", "DECIMER", "what molecule is in this picture". Input is ONE cropped molecule per image — for whole journal figures with multiple structures, run DECIMER-Segmentation first. Downstream of segmentation, upstream of `paper-fetch-smiles`.
---

# Mol Image → SMILES (OCSR)

## Environment check (run BEFORE any code execution)

This skill needs a dedicated mamba env **`decimer-env`** — DECIMER pulls in TensorFlow, which doesn't belong in the shared `skill-env`. Run this check first; if it fails, STOP and report the missing piece — do NOT install ad-hoc (per global CLAUDE.md, always update `/storage/edm/envs/decimer-env.yml` first).

```bash
ENV=decimer-env
micromamba env list | awk '{print $1}' | grep -qx "$ENV" \
  || { echo "ERROR: mamba env '$ENV' not available — define /storage/edm/envs/${ENV}.yml and create with: micromamba create -n $ENV -f /storage/edm/envs/${ENV}.yml" >&2; exit 1; }
for pkg in DECIMER rdkit PIL; do
  micromamba run -n "$ENV" python -c "import $pkg" 2>/dev/null \
    || { echo "ERROR: python package '$pkg' not available in env '$ENV' — add to /storage/edm/envs/${ENV}.yml and reinstall." >&2; exit 1; }
done
# Optional fallback engines — only required if you intend to use them:
# micromamba run -n "$ENV" python -c "import huggingface_hub"            # MolNextR fallback
# micromamba run -n "$ENV" python -c "import decimer_segmentation"       # whole-page segmentation
```

## Overview

Optical Chemical Structure Recognition (OCSR): take a raster image of one molecule, return a SMILES string. The skill wraps two production OCSR models:

| Engine | Runtime | When to use |
|---|---|---|
| **DECIMER 2.8** (default) | Local TensorFlow, CPU or GPU | Standard organic structures; no network needed; ~1–3 s per image on CPU |
| **MolNextR** (fallback) | HuggingFace API call | DECIMER returned an unparseable SMILES; complex polycycles; you have network |

**One image = one molecule.** OCSR models do not segment. If your input is a journal figure with several structures, crop first (use `DECIMER-Segmentation`, or do it by hand in a notebook).

This skill is the **automated alternative** to `authoring-smiles` for the case where you already have the image cropped. It feeds compounds straight into the `paper-fetch-smiles` pipeline (`compounds.json` → PubChem enrichment → grid PNG).

## When to use

- A paper figure has been cropped to one structure per PNG; you want SMILES for each
- A reaction-scheme parser (`reaction-data-extraction`) returned a molfile/bbox and you want a clean SMILES
- Quick sanity check during literature reading — "what is this exactly?"
- Building a small compound table from screenshots without retyping
- Validating that a hand-drawn sketch can be machine-read

## When NOT to use

- **Whole page or multi-structure figure** → segment first (`DECIMER-Segmentation`, `pip install decimer-segmentation`)
- **Reaction schemes with arrows and conditions** → `reaction-data-extraction` (calls RxnScribe; uses MolScribe internally for the molecules)
- **Authoring SMILES from a description or your own sketch** → `authoring-smiles`
- **Looking up a known compound by name** → `paper-fetch-smiles` (PubChem)
- **Editing an existing SMILES via NL** → `fast-smiles`

## What it recognises well — and what it does not

DECIMER is trained on ~450M synthetic depictions generated from PubChem SMILES. That training distribution dictates accuracy:

| Class | DECIMER | Notes |
|---|---|---|
| Drug-like organic small molecules | ★★★★★ | Core competency |
| Standard heterocycles, fused aromatics | ★★★★★ | |
| Common abbreviations (Me, Et, Ph, Bn, Boc, OMs, …) | ★★★★ | Expanded in training; spotty for rare groups |
| Stereochemistry (wedge/dash) | ★★ | Often dropped; verify against the figure |
| Hand-drawn structures | ★★★★ | Use the dedicated *hand-drawn model variant* (see below) |
| Markush / R-groups (R₁, [R], wavy bonds) | ✗ | Not in training; returns junk |
| **Organometallics, dative bonds, η-coordination, sandwich complexes** | ✗ | Out of training distribution. Output will be a plausible-looking but wrong organic SMILES. **Verify with `authoring-smiles`.** |
| Polymers `(X)n` | ✗ | Not supported |
| Low-resolution (< ~200 px) or blurred | ✗ | Degrades fast |

**Rule of thumb for this vault's workflow:** DECIMER is reliable for the *organic ligand backbone* (e.g. a free phosphine, an NHC precursor, the diketonate before metalation). It is **not** reliable for the assembled TM complex. Treat DECIMER output on any structure containing a metal centre as a draft to verify.

## Installation

DECIMER pulls in TensorFlow 2.10 and is ~3 GB on disk. Install into a project-local env:

```bash
# Per-project env (works inside Claude's sandbox)
micromamba create -p ./.venv-mm python=3.10 -c conda-forge -y
micromamba activate ./.venv-mm
pip install decimer rdkit pillow
# Optional MolNextR fallback:
pip install huggingface_hub
# Optional: page → cropped molecules
pip install decimer-segmentation
```

First call downloads the trained weights (~0.5 GB) to `~/.data/DECIMER-V2/` and caches them.

## Quick reference

| Task | Command | Notes |
|---|---|---|
| Single image → SMILES (one-liner) | `python -c "from DECIMER import predict_SMILES; print(predict_SMILES('mol.png'))"` | First call is slow (TF init + weight load) |
| Via this skill's wrapper | `python scripts/mol_image_to_smiles.py mol.png` | Validates with RDKit, emits JSON |
| Batch (glob) | `python scripts/mol_image_to_smiles.py 'figs/*.png' -o out/` | One JSON per image |
| Force MolNextR | `python scripts/mol_image_to_smiles.py mol.png --engine molnextr` | Requires HF token if rate-limited |
| Hand-drawn structures | DECIMER-HandDrawn model, separate ckpt (Zenodo 10781330) | Different weights, same `predict_SMILES` API after model swap |
| Page → cropped molecules | `from decimer_segmentation import segment_chemical_structures` | Returns list of PIL images, one per detected molecule |

## Bundled wrapper — `scripts/mol_image_to_smiles.py`

The wrapper provides:

- A clean CLI that emits JSON (so it composes with `jq`, `paper-fetch-smiles`, etc.)
- **RDKit validation** of the returned SMILES (parses? canonical form?). Raw `predict_SMILES` returns invalid SMILES silently — always validate.
- An `auto` mode that tries DECIMER first, falls back to MolNextR on parse failure
- Per-image JSON output schema matching what `paper-fetch-smiles` consumes for the `fallback_smiles` field

```python
# Python API
import sys; sys.path.insert(0, "/path/to/research-skills/skills/mol-image-to-smiles/scripts")
import mol_image_to_smiles as m

result = m.predict("mol.png")                # auto engine, validates with RDKit
result = m.predict("mol.png", engine="molnextr")
results = m.predict_batch("figs/*.png")      # list[dict], one per image
```

Output schema (one image):

```json
{
  "image": "/abs/path/to/mol.png",
  "engine": "decimer",
  "raw_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
  "parses": true,
  "rdkit_error": null,
  "warnings": []
}
```

If DECIMER returns garbage on a TM complex, `parses` will often be `true` (DECIMER outputs syntactically valid SMILES) but the structure is wrong. **Visual verification against the original image is mandatory for any organometallic input** — the script can't catch this for you. Render the output back to PNG with RDKit and eyeball it next to the source crop.

## Composing with the rest of the vault

### Page → compounds.json (the full upstream pipeline)

```python
from decimer_segmentation import segment_chemical_structures
import mol_image_to_smiles as m
from PIL import Image
import json

page = Image.open("paper_page_5.png")
crops = segment_chemical_structures(page)            # list[PIL.Image]

records = []
for i, crop in enumerate(crops):
    crop_path = f"crops/crop_{i:03d}.png"
    crop.save(crop_path)
    r = m.predict(crop_path)
    records.append({
        "paper_id": f"P5-{i+1}",
        "role": "unknown",                            # agent fills this in
        "name": "",                                   # agent fills this in
        "fallback_smiles": r["canonical_smiles"] if r["parses"] else None,
        "_provenance": {"engine": r["engine"], "raw": r["raw_smiles"]},
    })

json.dump(records, open("compounds.json", "w"), indent=2)
# Next: hand off to paper-fetch-smiles for PubChem enrichment and grid render.
```

### Verification loop with `authoring-smiles`

For any structure where DECIMER's output is suspicious (any metal centre, any unusual coordination, any stereochemistry that matters):

1. Run `mol_image_to_smiles.py` to get a draft SMILES.
2. Render the draft with RDKit → side-by-side with the source crop.
3. If they disagree, switch to `authoring-smiles` and reconstruct by hand using the construction order rules there. DECIMER's output is at best a starting hint.

## Common mistakes

| Mistake | Fix |
|---|---|
| Feeding a whole journal figure with multiple structures | Segment first with `decimer_segmentation.segment_chemical_structures`. DECIMER returns nonsense on multi-structure inputs. |
| Trusting DECIMER on TM complexes / sandwich compounds / η-coordinated ligands | Don't. Always verify against the figure. The output will *look* valid (parses fine) but encode the wrong connectivity. |
| Assuming stereochemistry is preserved | DECIMER often drops wedges. If stereo matters, edit the result with `fast-smiles` or author by hand with `authoring-smiles`. |
| Using `from decimer import predict_SMILES` (lowercase) | Wrong — the import is `from DECIMER import predict_SMILES` (uppercase package name, lowercase pip package). |
| Calling `predict_SMILES` in a hot loop and paying TF startup every time | Import once at module scope. The TF graph + weights load on first call (~10–20 s); subsequent calls are ~1–3 s on CPU. The bundled wrapper does this correctly. |
| Not validating the returned SMILES | DECIMER can return strings that look like SMILES but fail `Chem.MolFromSmiles`. The bundled wrapper validates; if you call `predict_SMILES` directly, wrap with `Chem.MolFromSmiles(...) is not None`. |
| Using the standard DECIMER model on hand-drawn sketches | Use the DECIMER-HandDrawn variant (Zenodo 10.5281/zenodo.10781330). Standard weights underperform on hand-drawn input. |
| Image too small (< ~200 px on the short edge) | Upscale (PIL `resize` with `BICUBIC`) before passing to DECIMER. |
| Sandbox: no `~/.data/DECIMER-V2/` write access | Set `DECIMER_DATA_DIR` env var to a writable path (e.g. `$PWD/.decimer_cache`), or pre-download weights outside the sandbox. |

## Reported accuracy (independent context)

- **In-distribution test set** (PubChem-derived synthetic depictions): ~96 % Tanimoto = 1.0 match (Rajan et al., *Nat. Commun.* 14:5045, 2023).
- **Out-of-distribution literature figures**: independent benchmarks (Brinkhaus et al., *J. Cheminform.* 2024) report 60–80 % depending on figure style.
- **Organometallics**: no published benchmark — anecdotally near 0 % usable output. Treat as out-of-scope.

## Related

- Upstream DECIMER: <https://github.com/Kohulan/DECIMER-Image_Transformer>
- DECIMER paper: Rajan K. et al., *Nat. Commun.* 14, 5045 (2023). DOI: [10.1038/s41467-023-40782-0](https://doi.org/10.1038/s41467-023-40782-0)
- DECIMER-Segmentation: <https://github.com/Kohulan/DECIMER-Image-Segmentation>
- DECIMER-HandDrawn model: <https://doi.org/10.5281/zenodo.10781330>
- MolNextR (HF): `MolecularAI/MolNextR`
- Sibling skills in this vault: `authoring-smiles` (manual SMILES), `reaction-data-extraction` (whole schemes), `paper-fetch-smiles` (downstream enrichment), `fast-smiles` (NL edits)
