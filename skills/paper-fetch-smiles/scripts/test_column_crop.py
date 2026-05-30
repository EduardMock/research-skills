"""Regression test for column-aware caption cropping.

Oracle: test/ni-zhang/figs_truth/gt_1..8.png are hand-verified full-width crops
of the 8 figures in the ni-zhang paper (single-column / full-width figures, wide
captions spanning the figure). Column-aware mode must NOT clip these — it must
still capture each figure full-width, matching the gt content.

Contrast: test/co2-mech schemes have narrow centred captions (5% of page) in a
two-column layout — those SHOULD be clipped to the caption's column.

The discriminator under test: a wide caption (spans most of the page) means a
full-width figure → don't clip; a narrow caption means a single-column figure →
clip x to that column.

Run:  micromamba run -n paper-fetch-smiles python -m scripts.test_column_crop
Exit 0 = all pass. Prints one line per case + a final PASS/FAIL summary.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image

from .caption_crop import (
    _find_text_blocks,
    _sanitize_xml,
    column_aware_bboxes,
    find_captions,
)

HERE = Path(__file__).resolve().parent.parent
NI_ZHANG_PDF = HERE / "test/ni-zhang/inorganics-12-00039.pdf"
NI_ZHANG_GT = HERE / "test/ni-zhang/figs_truth"
CO2_PDF = HERE / ("test/co2-mech/Fan et al. - 2012 - Theoretical studies of "
                  "reactions of carbon dioxide mediated and catalysed by "
                  "transition metal comple.pdf")


def _bbox_xml(pdf: Path) -> str:
    out = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf), "-"],
        check=True, capture_output=True, text=True,
    ).stdout
    return _sanitize_xml(out)


def _boxes_for(pdf: Path):
    xml = _bbox_xml(pdf)
    caps = find_captions(xml)
    blocks = _find_text_blocks(xml)
    return column_aware_bboxes(caps, page_text_blocks=blocks), {c.number: c for c in caps}


def test_ni_zhang_full_width_not_clipped() -> list[str]:
    """Each of the 8 ni-zhang figures must stay full-width (≥90% of page x-span).

    Width oracle: the gt_N.png crops are 1090-1475 px wide at the gt DPI; the key
    invariant is that column-aware mode keeps the figure FULL-WIDTH rather than
    halving it. We assert the box x-span is ≥ 88% of the page width — a midpoint
    column split would drop it to ~50%.
    """
    fails: list[str] = []
    boxes, _ = _boxes_for(NI_ZHANG_PDF)
    fig_boxes = [b for b in boxes if b.kind == "Figure"]
    n_gt = len(list(NI_ZHANG_GT.glob("gt_*.png")))
    if len(fig_boxes) != n_gt:
        fails.append(f"ni-zhang: expected {n_gt} Figure boxes, got {len(fig_boxes)}")
    for b in fig_boxes:
        x0, _, x1, _ = b.bbox_pts
        pw, _ = b.page_size_pts
        span_frac = (x1 - x0) / pw
        if span_frac < 0.88:
            fails.append(
                f"ni-zhang Figure {b.number}: x-span {span_frac*100:.0f}% < 88% "
                "(full-width figure got clipped)"
            )
    return fails


def test_co2_scheme_clipped_to_column() -> list[str]:
    """The two-column co2-mech schemes must be clipped to a single column (<60%)."""
    fails: list[str] = []
    boxes, caps = _boxes_for(CO2_PDF)
    # Scheme 5 (right column) and Scheme 4 (left column) are clear two-column cases.
    for n in (4, 5):
        b = next((b for b in boxes if b.number == n), None)
        if b is None:
            fails.append(f"co2-mech Scheme {n}: no box produced")
            continue
        x0, _, x1, _ = b.bbox_pts
        pw, _ = b.page_size_pts
        span_frac = (x1 - x0) / pw
        if span_frac > 0.60:
            fails.append(
                f"co2-mech Scheme {n}: x-span {span_frac*100:.0f}% > 60% "
                "(two-column scheme not clipped to its column)"
            )
    return fails


def test_decide_needs_crop() -> list[str]:
    """pdfimages-first: only fall back to cropping when embedded images are too
    few to be the figures.

    - ni-zhang: ~1-2 figure-grade embedded rasters but 8 Figure captions →
      embedded images are NOT the figures (they're vector) → MUST crop.
    - a paper whose figures ARE embedded rasters: candidates ≥ captions → DON'T
      crop (pdfimages already did the job).
    - no captions located → nothing to anchor → trust pdfimages, DON'T crop.
    """
    from .extract_figs import decide_needs_crop
    fails: list[str] = []
    cases = [
        ("vector figures (ni-zhang-like)", dict(n_candidates=1, n_captions=8), True),
        ("embedded figures suffice", dict(n_candidates=10, n_captions=8), False),
        ("exactly enough", dict(n_candidates=8, n_captions=8), False),
        ("no captions found", dict(n_candidates=0, n_captions=0), False),
    ]
    for label, kwargs, expected in cases:
        got = decide_needs_crop(**kwargs)
        if got != expected:
            fails.append(f"decide_needs_crop({kwargs}) = {got}, expected {expected} [{label}]")
    return fails


def main() -> int:
    all_fails: list[str] = []
    for name, fn in [
        ("ni-zhang full-width not clipped", test_ni_zhang_full_width_not_clipped),
        ("co2-mech scheme clipped to column", test_co2_scheme_clipped_to_column),
        ("pdfimages-first crop decision", test_decide_needs_crop),
    ]:
        fails = fn()
        status = "PASS" if not fails else "FAIL"
        print(f"[{status}] {name}" + (f" — {len(fails)} issue(s)" if fails else ""))
        for f in fails:
            print(f"    - {f}")
        all_fails += fails
    print(f"\n{'PASS' if not all_fails else 'FAIL'}: "
          f"{2 - len({f.split(':')[0] for f in all_fails})}/2 cases clean"
          if all_fails else "\nPASS: 2/2 cases clean")
    return 0 if not all_fails else 1


if __name__ == "__main__":
    raise SystemExit(main())
