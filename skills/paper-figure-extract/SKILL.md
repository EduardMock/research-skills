---
name: paper-figure-extract
description: Use when you need machine-readable figures or reaction schemes out of a chemistry paper PDF — a free-energy/mechanism diagram (Figure N) cropped for an analyzer to read colored curves, or a catalytic-cycle/reaction scheme (Scheme N) cropped region-only. Triggers: "extract the figures from this paper", "crop Figure N / Scheme N", "get the energy diagram out of this PDF", "pull the catalytic cycle scheme", "trace the mechanism from the free-energy profile". For the whole paper→catalog flow use paper-fetch-smiles; for clean A+B→C reaction schemes use reaction-data-extraction (RxnScribe).
---

# paper-figure-extract

Get figures and schemes out of a paper PDF as cropped images + a JSON catalog,
then hand them to an analyzer subagent that reads the chemistry. Two commands:
`extract-figs` (Figure N — energy diagrams) and `extract-schemes` (Scheme N —
reactions). Part of the `paper-fetch-smiles` conversion pipeline; usable alone.

## When NOT to use

- Converting an entire paper into a compound catalog → `paper-fetch-smiles` (it calls this skill).
- Clean `A + B → C` reaction schemes you want parsed to SMILES → `reaction-data-extraction` (RxnScribe). `extract-figs` is tuned for energy *diagrams*, `extract-schemes` for catalytic *cycles*.

## extract-figs — energy/mechanism diagrams (Figure N)

Many catalytic-cycle papers draw the mechanism only as a **free-energy diagram** —
colored curves over a reaction coordinate, labels along the curves. The order of
labels along each colored line IS the mechanism for that pathway; the highest
peak per line is the rate-limiting TS.

**Try `pdfimages` FIRST; crop only as a fallback.** Embedded-raster extraction is
cheap and lossless. Only rasterize whole pages and crop when the figures are
*vector art* `pdfimages` can't see (energy diagrams usually are). `--auto` decides
for you: runs `pdfimages -all`, and if there are fewer figure-grade embedded
images than `Figure`/`Scheme` captions, falls back to `--rasterize-pages
--caption-anchored --column-aware`; else keeps the `pdfimages` output. Prefer `--auto`.

```bash
micromamba run -n paper-fetch-smiles python -m scripts.cli extract-figs \
  --paper-pdf <paper>.pdf  --out-dir figs  --auto \
  --log paper_fetch_log.md  --paper-name "<First Author Year>"
```

Three passes (override `--auto` only if needed), each opt-in:

| Pass | Flag | Produces | Fails when |
|---|---|---|---|
| `pdfimages -all` | always on | every embedded raster, pruned by `--min-width-px` (100) + `--min-size-bytes` (2 KB) | figures are vector |
| `pdftoppm -png` | `--rasterize-pages [--pages N-M] [--page-dpi 150]` | one PNG per page; captures vector art | verbose (text + caption + figure) |
| caption crop | `--caption-anchored [--column-aware] [--keep-page-rasters]` | one `fig-Figure-N.png` per caption via `pdftotext -bbox-layout` | caption's first word "Figure"/"Scheme" isn't leftmost in its block (centred captions) |

The bbox XML is **sanitized of XML-1.0-illegal control bytes** (e.g. a raw `0x02`
from a superscript glyph) before parsing — without this, `ElementTree` aborts the
whole document and every caption is lost (this bit Fan 2012: 38 schemes, 0 recovered).

**`--column-aware`**: caption width discriminates layout — a caption ≥ 40 % of page
width → full-width figure (keep page-content x); narrower → clip x to the caption's
column so the neighbouring text column isn't dragged in. Regression-tested by
`scripts/test_column_crop.py` (ni-zhang's 8 figures stay full-width vs `figs_truth/gt_N.png`;
Fan's two-column schemes clip). Catalog: `figs/figs.json`.

### Energy-diagram analyzer subagent (≤ 5 min)

> Skim every `page-NN.png` / `fig-Figure-N.png`, find energy-diagram pages (axes `ΔG` / kcal·mol⁻¹, "reaction coordinate" on X, INT*/TS* labels along curves). Read the caption (`pdftotext -raw paper.pdf - | grep -i "figure N"`) for diyne/ligand/pathway. For each diagram, for each line **color**, list labels left-to-right + printed ΔG, then the rate-limiting TS (max ΔG among TS) and most-stable INT (min ΔG among INT). Write `mechanism_from_diagram.json` (schema below). Append VERIFIED per diagram + REVIEW per illegible label to `paper_fetch_log.md`. Hard cap: 5 min.

```json
{
  "_units": {"energy": "kcal/mol", "axis_y": "ΔG_THF", "axis_x": "reaction coordinate"},
  "diagrams": [
    {"figure": "page-08.png", "caption_summary": "Figure 4. ...diyne 4 + CO2, L1=PMe3...",
     "diyne": "4", "ligand": "L1=PMe3",
     "pathways_by_color": {
       "black": {"pathway_label": "4c",
                 "sequence": ["Ni(L1)2", "INT1-4c", "TS4-4c", "INT6-4c"],
                 "energies_kcal_mol": [0.0, 12.4, 25.2, 18.0],
                 "rate_limiting_ts": "TS4-4c", "most_stable_int": "INT8-4c"}}}
  ]
}
```

Forks/merges fall out for free: pathways sharing a `sequence` prefix fork off the
same intermediate; sharing a trailing label merge. This file feeds the
`reaction-mechanism-graph` planner as the source of `mechanism_sequence`.

## extract-schemes — reactions / catalytic cycles (Scheme N)

Where `Figure N` is an energy diagram, **`Scheme N` is a reaction**. Two hard differences from `extract-figs`:

- **Region-only rendering — never whole pages.** Each `Scheme N` caption renders ONLY that scheme's bbox via `pdftoppm -x -y -W -H`. No `page-NN.png` is ever produced. X clipped to the caption's column.
- **The product is reactions, not pictures.** Each `scheme-N.png` pairs with a `schemes.json` row whose `reactions[]` (ordered elementary steps) the analyzer fills.

```bash
micromamba run -n paper-fetch-smiles python -m scripts.cli extract-schemes \
  --paper-pdf <paper>.pdf  --out-dir schemes  --numbers "5,15,19-25" \
  --log paper_fetch_log.md  --paper-name "<First Author Year>"
```

`reactions[]` uses the SAME `from`/`to` species-label vocabulary as
`reaction-mechanism-graph`'s `mechanism.json`, so a traced cycle can be promoted
once SI `.xyz` labels exist.

### Scheme-reaction analyzer subagent (≤ 5 min)

> For each `scheme-N.png`, set `is_catalytic_cycle` (closed loop of arrows?). If it depicts reactions, trace arrows in order → `reactions[]`: one entry per arrow with `from`/`to` paper labels (`1`, `A`, `INT1-1a`, `CO2`, `Ni(COD)2`), an elementary-step `kind` (CO2_coordination / oxidative_coupling / insertion / beta_H_elimination / reductive_elimination / ligand_exchange / metathesis), and a `note` (barrier, regiochem, path). Forks/merges = two entries sharing a `from`/`to` label. Read caption + text (`pdftotext -raw paper.pdf - | grep -i "scheme N"`). Append VERIFIED/REVIEW to `paper_fetch_log.md`. Hard cap: 5 min.

## Common mistakes

| Mistake | Fix |
|---|---|
| `pdfimages -all` → thousands of tiny rasters, no figure | Defaults prune <100 px / <2 KB; raise `--min-width-px` (atom sprites are 30–80 px). |
| `pdfimages` returns 0 useful figures (all vector) | Add `--rasterize-pages`. |
| `--caption-anchored` finds 0 captions | "Figure"/"Scheme" must be the leftmost word of its bbox block. Centred/rasterised captions can't anchor — fall back to `--rasterize-pages` alone and let the analyzer find pages by content. |
| Using `extract-figs` on a reaction scheme | Use `extract-schemes` (region-only) or `reaction-data-extraction` for clean A+B→C. |

## Env

Uses the `paper-fetch-smiles` env (Pillow for cropping) plus poppler binaries
(`pdfimages`, `pdftoppm`, `pdftotext`) from the system (`/usr/bin`). `_log.py`
writes the shared append-only `paper_fetch_log.md` (REVIEW/VERIFIED) contract.

## Related skills

- `paper-fetch-smiles` — orchestrator; runs this as the optional pre-step before authoring `compounds.py`.
- `reaction-mechanism-graph` — consumes `mechanism_from_diagram.json` / `schemes.json` `reactions[]` into `mechanism.json`.
- `reaction-data-extraction` — RxnScribe for clean reaction schemes.
