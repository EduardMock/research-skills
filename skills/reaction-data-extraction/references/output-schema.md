# RxnScribe output schema (post-wrapper)

The wrapper (`scripts/extract_reactions.py::predict`) calls `RxnScribe.predict_image_file(image, molscribe=True, ocr=True)` and normalises the result.

## Top-level dict

```jsonc
{
  "image": "/abs/path/to/scheme.png",   // str
  "device": "cpu",                       // "cpu" | "cuda"
  "n_reactions": 2,                      // int, len(reactions)
  "reactions": [ /* per-reaction objects, see below */ ]
}
```

## Per-reaction object

```jsonc
{
  "reactants":  [ /* molecule items */ ],
  "conditions": [ /* condition (text) items */ ],
  "products":   [ /* molecule items */ ]
}
```

A multi-step linear scheme produces multiple per-reaction objects, one per arrow.

## Molecule item (reactants / products)

Direct from RxnScribe + MolScribe, plus three RDKit-validated fields added by the wrapper:

```jsonc
{
  // --- from RxnScribe ---
  "category":     "Mol",                 // string label
  "category_id":  1,                     // 1 = reactant, 3 = product (RxnScribe convention)
  "bbox":         [x1, y1, x2, y2],      // pixels, top-left origin
  "smiles":       "c1ccc(Br)cc1",        // MolScribe's raw output (may be invalid)
  "molfile":      "...",                 // MDL molfile string

  // --- added by wrapper ---
  "canonical_smiles": "Brc1ccccc1",      // RDKit canonicalised; null if !parses
  "parses":           true,              // bool — RDKit could parse `smiles`
  "rdkit_error":      null               // str or null
}
```

**Always branch on `parses`** before using `canonical_smiles` downstream — MolScribe sometimes emits syntactically valid SMILES that fail full RDKit sanitisation (most often on organometallics and unusual valences).

## Condition item

Conditions are raw OCR — *not* parsed into catalyst/solvent/T/t/yield. Wrapper does **not** enrich these:

```jsonc
{
  "category":    "Text",
  "category_id": 2,
  "bbox":        [x1, y1, x2, y2],
  "text":        "Pd(PPh3)4, K2CO3, DMF, 80 °C, 12 h"
}
```

To extract structured fields, post-process the `text` string. Two reasonable approaches:

1. **Regex set** for common patterns:
   ```python
   import re
   T   = re.search(r"(\d+\s*°\s*C|rt|reflux)", text)
   t   = re.search(r"(\d+(?:\.\d+)?)\s*(h|hr|hour|min)s?", text)
   yld = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
   ```
2. **LLM call** (e.g. `claude-haiku-4-5`) with a strict JSON schema — robust to footnote prose, abbreviations, and unusual unit notation. Slower but generalises across paper styles.

Either way, store the parsed fields *alongside* the raw `text` rather than replacing it — the raw OCR is the ground truth.

## Full example payload

A two-step linear scheme (Pd-catalysed coupling → ester hydrolysis):

```json
{
  "image": "/data/papers/jacs_2024_si_p12_scheme1.png",
  "device": "cpu",
  "n_reactions": 2,
  "reactions": [
    {
      "reactants": [
        {"category": "Mol", "category_id": 1, "bbox": [12, 84, 180, 220],
         "smiles": "Brc1ccc(C(=O)OC)cc1", "molfile": "...",
         "canonical_smiles": "COC(=O)c1ccc(Br)cc1", "parses": true, "rdkit_error": null},
        {"category": "Mol", "category_id": 1, "bbox": [220, 84, 360, 220],
         "smiles": "OB(O)c1ccccc1", "molfile": "...",
         "canonical_smiles": "OB(O)c1ccccc1", "parses": true, "rdkit_error": null}
      ],
      "conditions": [
        {"category": "Text", "category_id": 2, "bbox": [380, 130, 540, 170],
         "text": "Pd(PPh3)4 (5 mol%), K2CO3, DMF, 80 °C, 12 h"}
      ],
      "products": [
        {"category": "Mol", "category_id": 3, "bbox": [560, 84, 740, 220],
         "smiles": "COC(=O)c1ccc(-c2ccccc2)cc1", "molfile": "...",
         "canonical_smiles": "COC(=O)c1ccc-c2ccccc2cc1", "parses": true, "rdkit_error": null}
      ]
    },
    {
      "reactants": [
        {"category": "Mol", "category_id": 1, "bbox": [760, 84, 940, 220],
         "smiles": "COC(=O)c1ccc(-c2ccccc2)cc1", "molfile": "...",
         "canonical_smiles": "COC(=O)c1ccc-c2ccccc2cc1", "parses": true, "rdkit_error": null}
      ],
      "conditions": [
        {"category": "Text", "category_id": 2, "bbox": [960, 130, 1080, 170],
         "text": "NaOH (aq), MeOH, rt, 4 h, 92%"}
      ],
      "products": [
        {"category": "Mol", "category_id": 3, "bbox": [1100, 84, 1280, 220],
         "smiles": "OC(=O)c1ccc(-c2ccccc2)cc1", "molfile": "...",
         "canonical_smiles": "OC(=O)c1ccc-c2ccccc2cc1", "parses": true, "rdkit_error": null}
      ]
    }
  ]
}
```

## Category ID reference

| `category_id` | Meaning |
|---|---|
| 1 | Reactant (molecule) |
| 2 | Condition (text) |
| 3 | Product (molecule) |

Anything outside {1, 2, 3} is a wrapper bug or a RxnScribe API change — file an issue.
