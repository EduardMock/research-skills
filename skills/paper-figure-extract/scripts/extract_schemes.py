"""Extract reaction/catalytic-cycle SCHEMES from a paper PDF, region-only.

Where ``extract-figs --caption-anchored`` is tuned for **energy diagrams**
(``Figure N``, ΔG-vs-reaction-coordinate plots), this subcommand is tuned for
**reaction schemes** (``Scheme N``) — the catalytic cycles, insertion modes
and stoichiometric reactions a CO2/TM mechanism paper draws. The marker that
says "there is a reaction here" is the word ``Scheme`` (vs ``Figure``).

Two hard design rules, per the skill owner:

1. **Never rasterize whole pages.** Unlike ``extract-figs``, this script never
   writes ``page-NN.png``. For each ``Scheme N`` caption it renders ONLY that
   scheme's bounding box, via ``pdftoppm -x -y -W -H`` (region crop at the
   PDF level). No full-page raster is ever produced or deleted.
2. **The product is reactions, not just pictures.** Each ``scheme-N.png`` crop
   is paired with a row in ``schemes.json`` whose ``reactions`` list is filled
   by the analyzer subagent (see SKILL.md). One scheme → one catalytic cycle →
   its ordered list of elementary reaction steps.

Pipeline::

    extract-schemes paper.pdf
        ├─ pdftotext -bbox-layout → find every `Scheme N` caption
        ├─ figure_bboxes(): region above each caption (the drawing)
        ├─ pdftoppm -x -y -W -H : render ONLY that region → scheme-N.png
        └─ schemes.json : {scheme, page, crop, caption, reactions: []}
                            ↓
              scheme-reaction analyzer subagent (per SKILL.md)
                            ↓
              schemes.json with reactions[] filled:
              { "scheme": 5, "is_catalytic_cycle": true,
                "reactions": [
                  {"step": 1, "from": ["1", "CO2"], "to": ["A"],
                   "kind": "CO2_coordination", "note": "η²(C,O), path b"},
                  ...] }

``reactions[]`` is deliberately the SAME vocabulary the SI ``mechanism.json``
uses (``from`` / ``to`` species labels), so a cycle traced off a scheme can be
promoted into ``mechanism.json`` once SI .xyz labels exist.

Units: PDF points (pt, 1/72 inch) for all bboxes; pixels on the crops
(``px = pt * dpi / 72``).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import _log
from .caption_crop import (
    FigureBox,
    _find_text_blocks,
    _sanitize_xml,
    figure_bboxes,
    find_captions,
)


def _bbox_xml(pdf: Path) -> str:
    """``pdftotext -bbox-layout`` output, sanitized of XML-illegal control chars."""
    out = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf), "-"],
        check=True, capture_output=True, text=True,
    ).stdout
    return _sanitize_xml(out)


def _column_clip(box: FigureBox, caption: Any) -> FigureBox:
    """Narrow a box's x-extent to the caption's column in a 2-column layout.

    ``figure_bboxes`` widens x to the whole page content area (5–95 %), which
    in a two-column journal drags the neighbouring text column into the crop.
    A scheme caption is centred under its drawing, so the caption's centre-x
    tells us which column the scheme lives in: clip x to that half-page. Full
    page-width schemes (caption centre near the spine) are left full-width.
    """
    page_w, _ = box.page_size_pts
    x0, y0, x1, y1 = box.bbox_pts
    cx0, _, cx1, _ = caption.bbox_pts
    cap_center = 0.5 * (cx0 + cx1)
    margin = page_w * 0.04
    mid = 0.5 * page_w
    # If the caption sits clearly in one half, clip to that half. "Clearly"
    # means its centre is >10 % of page width away from the spine.
    if cap_center < mid - 0.10 * page_w:          # left column
        x1 = min(x1, mid + margin)
        x0 = max(x0, margin)
    elif cap_center > mid + 0.10 * page_w:         # right column
        x0 = max(x0, mid - margin)
        x1 = min(x1, page_w - margin)
    return FigureBox(page=box.page, kind=box.kind, number=box.number,
                     bbox_pts=(x0, y0, x1, y1), page_size_pts=box.page_size_pts)


def render_scheme_regions(
    boxes: list[FigureBox],
    pdf: Path,
    *,
    dpi: int,
    out_dir: Path,
) -> list[Path]:
    """Render ONLY each scheme's bbox with ``pdftoppm -x -y -W -H``.

    No full page is ever rasterized. pdftoppm takes the crop window in PIXELS
    at the target DPI (``px = pt * dpi / 72``) and ``-f/-l`` to pin the page.
    Writes ``scheme-<N>.png`` (overwrites). Returns crop paths in scheme order.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    scale = dpi / 72.0
    written: list[Path] = []
    for box in boxes:
        x0, y0, x1, y1 = box.bbox_pts
        x_px = int(round(x0 * scale))
        y_px = int(round(y0 * scale))
        w_px = int(round((x1 - x0) * scale))
        h_px = int(round((y1 - y0) * scale))
        if w_px <= 0 or h_px <= 0:
            continue
        stem = out_dir / f"scheme-{box.number}"
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi),
             "-f", str(box.page), "-l", str(box.page),
             "-x", str(x_px), "-y", str(y_px),
             "-W", str(w_px), "-H", str(h_px),
             str(pdf), str(stem)],
            check=True,
        )
        # pdftoppm appends the page number: scheme-N-<page>.png. Normalize to
        # scheme-N.png so the catalog filename is stable and page-agnostic.
        produced = sorted(out_dir.glob(f"scheme-{box.number}-*.png"))
        final = out_dir / f"scheme-{box.number}.png"
        if produced:
            produced[0].replace(final)
            for extra in produced[1:]:
                extra.unlink()
            written.append(final)
        elif final.exists():
            written.append(final)
    return written


def build_catalog(
    boxes: list[FigureBox],
    captions_by_number: dict[int, Any],
    crops: set[int],
    *,
    source_pdf: Path,
) -> dict[str, Any]:
    """Assemble schemes.json — one row per scheme, reactions[] left for the analyzer."""
    schemes = []
    for box in boxes:
        cap = captions_by_number.get(box.number)
        schemes.append({
            "scheme": box.number,
            "page": box.page,
            "crop": f"scheme-{box.number}.png" if box.number in crops else None,
            "caption": (cap.text if cap else "").strip(),
            # Filled by the analyzer subagent. is_catalytic_cycle distinguishes a
            # closed cycle (Scheme 5/15/19/25/32) from a one-shot reaction or a
            # coordination-mode cartoon (Scheme 1).
            "is_catalytic_cycle": None,
            "reactions": [],
        })
    return {
        "_units": {"bbox": "pt", "crop": "px"},
        "_schema": {
            "reactions[]": {
                "step": "1-based order along the cycle",
                "from": "list of reactant species labels (paper's vocabulary)",
                "to": "list of product species labels",
                "kind": "elementary-step class, e.g. CO2_coordination / "
                        "oxidative_coupling / insertion / beta_H_elimination / "
                        "reductive_elimination / ligand_exchange / metathesis",
                "note": "free text — barrier, regiochem, path label, spin",
            }
        },
        "source_pdf": str(source_pdf),
        "n_schemes": len(schemes),
        "schemes": schemes,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--paper-pdf", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True,
                   help="directory for scheme-N.png crops + schemes.json")
    p.add_argument("--page-dpi", type=int, default=150,
                   help="render DPI for the region crops (default 150)")
    p.add_argument("--numbers", default=None,
                   help='only these schemes, e.g. "5,15,19-22". Default: all.')
    p.add_argument("--catalog-only", action="store_true",
                   help="write schemes.json but render no crops (locate only).")
    p.add_argument("--column-aware", action=argparse.BooleanOptionalAction,
                   default=True,
                   help="clip single-column schemes to their column (ON by "
                        "default; --no-column-aware renders the full page width).")
    p.add_argument("--log", type=Path, default=None)
    p.add_argument("--paper-name", default="(unknown paper)")
    args = p.parse_args(argv)

    if not args.paper_pdf.exists():
        print(f"ERROR: paper PDF not found: {args.paper_pdf}", file=sys.stderr)
        return 2

    xml = _bbox_xml(args.paper_pdf)
    captions = [c for c in find_captions(xml) if c.kind == "Scheme"]
    if args.numbers:
        wanted = _parse_numbers(args.numbers)
        captions = [c for c in captions if c.number in wanted]
    if not captions:
        if args.log:
            _log.append(
                args.log, "REVIEW",
                f"extract-schemes: no `Scheme N` captions found in {args.paper_pdf} "
                "— captions may be centred or rasterized (pdftotext can't anchor). ",
                paper_name=args.paper_name, source="scripts/extract_schemes.py",
            )
        print("extract-schemes: 0 Scheme captions found", file=sys.stderr)
        return 1

    blocks = _find_text_blocks(xml)
    captions_by_number = {c.number: c for c in captions}
    boxes = figure_bboxes(captions, page_text_blocks=blocks)
    if args.column_aware:
        boxes = [_column_clip(b, captions_by_number[b.number]) for b in boxes]

    crops: set[int] = set()
    if not args.catalog_only:
        written = render_scheme_regions(
            boxes, args.paper_pdf, dpi=args.page_dpi, out_dir=args.out_dir,
        )
        crops = {int(p.stem.split("-")[1]) for p in written}

    catalog = build_catalog(
        boxes, captions_by_number, crops, source_pdf=args.paper_pdf,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    cat_path = args.out_dir / "schemes.json"
    cat_path.write_text(json.dumps(catalog, indent=2))

    if args.log:
        _log.append(
            args.log, "VERIFIED",
            f"extract-schemes: located {catalog['n_schemes']} schemes "
            f"(numbers {sorted(c.number for c in captions)}), rendered "
            f"{len(crops)} region crops (no full pages). reactions[] pending analyzer.",
            paper_name=args.paper_name, source="scripts/extract_schemes.py",
        )
    print(
        f"extract-schemes: {catalog['n_schemes']} schemes catalogued, "
        f"{len(crops)} region crops → {args.out_dir} (schemes.json written)",
        file=sys.stderr,
    )
    return 0


def _parse_numbers(spec: str) -> set[int]:
    """Parse "5,15,19-22" → {5,15,19,20,21,22}."""
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
