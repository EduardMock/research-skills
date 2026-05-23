---
name: reaction-data-extraction
description: Use when extracting structured reaction data (reactants, products, conditions, catalyst, solvent, T, t, yield) from a chemical reaction-scheme IMAGE — a cropped figure from a paper or patent, not a whole PDF. Wraps RxnScribe (Coley group, MIT — pix2seq scheme parser trained on USPTO patent schemes), which delegates molecule recognition to MolScribe and condition text to OCR. Output is JSON with role-typed bounding boxes and per-molecule SMILES. For whole-page PDF input, segment to scheme images first (PyMuPDF, pdf2image, or DECIMER-Segmentation). For single-molecule images use `mol-image-to-smiles`. Trigger on phrases like "extract reaction scheme", "parse reaction figure", "RxnScribe", "reactants and products from scheme", "extract reaction conditions from image".
---

# Reaction Data Extraction (RxnScribe)

## Overview

[RxnScribe](https://github.com/thomas0809/RxnScribe) is a **pix2seq** vision-encoder + autoregressive-decoder model from the Coley group (MIT) that reads a reaction-scheme image and emits a *sequence of role-typed bounding boxes* — reactants (red), conditions (green), products (blue) — for one or more reactions per image. Each molecule box is routed to MolScribe (the OCSR companion model) for SMILES; each condition box is routed to OCR for text.

**Input:** one scheme image (PNG/JPG). Single or multi-step.
**Output:** JSON list of reactions, each with `reactants`, `conditions`, `products` arrays — every item has a `bbox`, a `category`, and either `smiles` + `molfile` (molecules) or `text` (conditions).

This skill is the **automated alternative** to manually transcribing schemes from synthesis papers. It feeds the same `compounds.json` schema that `paper-fetch-smiles` consumes, plus a reaction-level JSON for retrosynthesis / dataset-building workflows.

## When to use

- A paper figure has been cropped to *one reaction scheme per image* and you want structured reaction data
- Building a reaction dataset from patents (USPTO-style schemes are the in-distribution case)
- A multi-step linear scheme — RxnScribe emits one reaction object per step
- You need bounding-box coordinates (e.g. to attribute each role back to a region of the original figure)

## When NOT to use

- **Whole PDF or page**: split it into scheme images first. Useful tools:
  - `pdf2image` or `PyMuPDF` to rasterise pages
  - Manual crop in a notebook for accuracy
  - `decimer-segmentation` only segments single molecules — *not* schemes — so don't use it here
- **Single molecule image** → `mol-image-to-smiles`
- **Reaction-condition tables in the PDF text** (no scheme image): regex-on-Markdown approaches (e.g. MinerU + rule-based parsing) are better suited; RxnScribe doesn't read tables
- **Reaction yield prediction / retrosynthesis**: this skill *extracts* data, it doesn't predict
- **Reactions with metal complexes in the catalyst box**: the box gets *detected* fine, but MolScribe's SMILES for the metal complex will be wrong (same training-data bias as DECIMER — see `mol-image-to-smiles` for details). Treat catalyst SMILES as a draft; verify with `authoring-smiles`.

## Capability table

| Construct | RxnScribe |
|---|---|
| Single reaction | ★★★★★ |
| Multi-step linear schemes | ★★★★ (one object per step) |
| Conditions above/below arrow | ★★★★ |
| Catalyst / solvent / T / t in conditions text | ★★★ (depends on OCR clarity) |
| Yield printed in scheme | ★★★ (only if printed *as part of* the image) |
| Branching / divergent schemes | ★★ |
| USPTO patent style | ★★★★★ (in-distribution) |
| Academic journal styles (decorative arrows, colour, dense layout) | ★★★ |
| **Organometallic catalyst SMILES** | ✗ (MolScribe limitation) |
| Markush / generic schemes | ✗ |
| Mechanism arrows (curly arrows, electron pushing) | ✗ |
| Schemes spanning multiple pages | ✗ |

Reported numbers (Qian et al., *JCIM* 2023, [10.1021/acs.jcim.3c00439](https://doi.org/10.1021/acs.jcim.3c00439)): ≈ 80 % precision/recall for *full reaction* extraction (all roles correct) on the held-out patent test set; component-level (just detecting boxes) is higher. Out-of-distribution academic-figure performance degrades — expect to manually verify.

## Installation

RxnScribe is not on PyPI as of v1.0 — install from source:

```bash
# Per-project env (works inside Claude's sandbox)
micromamba create -p ./.venv-mm python=3.10 -c conda-forge -y
micromamba activate ./.venv-mm

# RxnScribe + deps. The setup.py also pulls in torch, transformers, MolScribe.
git clone https://github.com/thomas0809/RxnScribe.git
cd RxnScribe
pip install -r requirements.txt
pip install .

# RDKit for downstream SMILES validation
pip install rdkit huggingface_hub
```

GPU is optional — pix2seq runs fine on CPU at ~10–20 s per scheme; GPU drops this to ~1 s.

### Model checkpoint

The trained weights are on HuggingFace Hub as `yujieq/RxnScribe`, filename `pix2seq_reaction_full.ckpt` (≈ 350 MB). Download once:

```python
from huggingface_hub import hf_hub_download
ckpt = hf_hub_download("yujieq/RxnScribe", "pix2seq_reaction_full.ckpt")
print(ckpt)   # path under ~/.cache/huggingface/hub/
```

The bundled wrapper does this lazily on first call.

## Quick reference

| Task | Command | Notes |
|---|---|---|
| Single scheme → JSON | `python scripts/extract_reactions.py scheme.png` | Auto-downloads ckpt on first call |
| Batch (glob) | `python scripts/extract_reactions.py 'schemes/*.png' -o out/` | One JSON per scheme |
| Use GPU | `python scripts/extract_reactions.py scheme.png --device cuda` | ~10× faster than CPU |
| Custom checkpoint | `python scripts/extract_reactions.py scheme.png --ckpt /path/to/pix2seq_reaction_full.ckpt` | Skips HF download |
| Render predictions onto the image | `python scripts/extract_reactions.py scheme.png --render-to overlay.png` | Sanity-check the boxes by eye |

## Output schema (one scheme)

```json
{
  "image": "/abs/path/to/scheme.png",
  "device": "cpu",
  "n_reactions": 2,
  "reactions": [
    {
      "reactants": [
        {"category": "Mol", "category_id": 1, "bbox": [x1, y1, x2, y2],
         "smiles": "c1ccc(Br)cc1", "molfile": "..."}
      ],
      "conditions": [
        {"category": "Text", "category_id": 2, "bbox": [...],
         "text": "Pd(PPh3)4, K2CO3, DMF, 80 °C, 12 h"}
      ],
      "products": [
        {"category": "Mol", "category_id": 3, "bbox": [...],
         "smiles": "c1ccc(-c2ccccc2)cc1", "molfile": "..."}
      ]
    },
    { "...": "second step of a two-step scheme" }
  ]
}
```

The wrapper additionally adds for each molecule:

- `canonical_smiles` — RDKit-canonicalised
- `parses` — boolean, RDKit could parse the SMILES
- `rdkit_error` — string or null

**Conditions text is unparsed.** RxnScribe gives you the raw OCR string. For downstream structured fields (`catalyst`, `solvent`, `T`, `t`, `yield`), parse the text yourself — a small LLM call (`claude-haiku-4-5`) or a tuned regex set is the right pattern. The wrapper exposes `parse_conditions(text)` as a stub you can extend.

## Bundled wrapper — `scripts/extract_reactions.py`

```python
# Python API
import sys; sys.path.insert(0, "/path/to/research-skills/skills/reaction-data-extraction/scripts")
import extract_reactions as r

# Load model once (slow), reuse for many images
model = r.load_model(device="cpu")

result = r.predict(model, "scheme.png")          # one image → dict (schema above)
results = r.predict_batch(model, "schemes/*.png")
```

Loading the model is expensive (~5–15 s on CPU including ckpt parse). The wrapper exposes `load_model()` so callers can reuse a single instance across many images instead of paying that cost per-call.

## Composing with the rest of the vault

### Scheme → compounds.json (for `paper-fetch-smiles`)

```python
import extract_reactions as r
import json

model = r.load_model(device="cpu")
result = r.predict(model, "fig2_scheme.png")

records = []
seen = set()
for rxn_idx, rxn in enumerate(result["reactions"], 1):
    for role in ("reactants", "products"):
        for m in rxn[role]:
            if not m.get("parses"):
                continue
            key = m["canonical_smiles"]
            if key in seen:
                continue
            seen.add(key)
            records.append({
                "paper_id": f"S{rxn_idx}-{role[0].upper()}{len(records)+1}",
                "role": "reactant" if role == "reactants" else "product",
                "name": "",                          # agent fills in from paper text
                "fallback_smiles": key,
                "_provenance": {
                    "skill": "reaction-data-extraction",
                    "scheme_image": result["image"],
                    "reaction_index": rxn_idx,
                    "bbox": m["bbox"],
                },
            })

json.dump(records, open("compounds.json", "w"), indent=2)
# Hand off to paper-fetch-smiles for PubChem enrichment + grid render.
```

### Verify catalyst SMILES with `authoring-smiles`

For any scheme involving a metal-catalysed reaction:

1. Run RxnScribe → conditions text contains the catalyst name (e.g. `Pd(PPh3)4`).
2. The catalyst is *usually* not drawn as a structure in the scheme (it's referenced by abbreviation in the conditions box). If it *is* drawn, the SMILES MolScribe returns for the metal complex is unreliable. Cross-check with `authoring-smiles` (organometallic section) before relying on it.
3. For known catalysts referenced by name only, route to `paper-fetch-smiles` for PubChem lookup.

## Common mistakes

| Mistake | Fix |
|---|---|
| Feeding a whole page or PDF directly | RxnScribe expects one *scheme* per image. Pre-crop with `PyMuPDF`/`pdf2image` and manual selection, or train a separate scheme detector. |
| Loading the model per-image inside a loop | Use `load_model()` once and pass the instance into `predict()`. Per-call load is ~5–15 s on CPU. |
| Trusting catalyst SMILES on organometallics | Don't. MolScribe (RxnScribe's molecule backend) is PubChem-trained and falls over on TM complexes. The *scheme* parsing is fine; the *molecule* SMILES isn't. |
| Treating conditions text as structured | It's raw OCR. Parse separately (LLM or regex) before you have catalyst/solvent/T/t fields. |
| Confusing `decimer-segmentation` with scheme detection | `decimer-segmentation` segments individual molecules from pages, not reaction schemes. There is no published off-the-shelf scheme detector — manual crop or hand-rolled YOLO model are the options. |
| Forgetting `molscribe=True, ocr=True` | They default to True in `predict_image_file`, but if you toggle them off you get only bounding boxes — no SMILES, no condition text. |
| Ignoring `parses` flag on output molecules | RxnScribe + MolScribe sometimes emit syntactically valid SMILES that aren't chemically valid. Always check `parses` (RDKit-backed) before using `smiles` downstream. |
| Running on a journal figure with arrow decorations / coloured backgrounds | OOD relative to USPTO training — expect ~50–70 % precision. If quality matters, validate visually with `--render-to`. |
| Multi-page schemes / SI-spanning schemes | Not handled. Manually concatenate steps after extraction. |
| Mechanism diagrams (curly arrows, lone pairs) | Not supported — only product-arrow reaction schemes. |

## Reported scope (verbatim from the paper)

- Trained on **1,378 manually annotated reaction-diagram images**, predominantly from USPTO grants (Qian et al., *JCIM* 2023).
- 5-fold cross-validation during development; 90/10 train/dev split.
- 3 role categories: reactant, condition, product. No separate "catalyst" / "solvent" / "yield" categories — those live inside the condition text.

## Related

- Upstream RxnScribe: <https://github.com/thomas0809/RxnScribe>
- Paper: Qian Y, Guo J, Tu Z, Coley CW, Barzilay R. *RxnScribe: A Sequence Generation Model for Reaction Diagram Parsing.* JCIM 2023. DOI: [10.1021/acs.jcim.3c00439](https://doi.org/10.1021/acs.jcim.3c00439)
- HF demo: <https://huggingface.co/spaces/yujieq/RxnScribe>
- MolScribe (used internally for molecule SMILES): <https://github.com/thomas0809/MolScribe>
- Sibling skills in this vault: `mol-image-to-smiles` (single molecule), `authoring-smiles` (organometallic verification), `paper-fetch-smiles` (downstream enrichment), `fast-smiles` (NL SMILES edits)
- See [references/output-schema.md](references/output-schema.md) for the full per-field schema and example payloads
