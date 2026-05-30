"""Caption-anchored figure cropping.

Units: PDF points (1/72 inch) for bbox; pixels (at the chosen DPI) on the
output crops. Conversion: ``px = pt * dpi / 72``.

Pipeline:
    1. ``find_captions(bbox_xml)`` → list[CaptionAnchor]
       Walks the ``pdftotext -bbox-layout`` XHTML; returns every line whose
       first word is "Figure" or "Scheme" followed by a "N." token.
       Coordinates are PDF points with origin top-left.

    2. ``figure_bboxes(captions)`` → list[FigureBox]
       For each caption, the figure spans from the bottom of the previous
       caption on the same page (or the page top) down to the bottom of the
       current caption's block. Left/right are the caption's own column.

    3. ``crop_page_rasters(boxes, raster_dir, dpi, out_dir)`` → list[Path]
       Convert pt→px, open ``page-NN.png``, crop, save ``fig-<kind>-N.png``.

The whole module deliberately produces ONE crop per caption — no
multi-fragment dumps — so the downstream authoring step (compounds.py /
mechanism.json) stays small.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


_NUM_RE = re.compile(r"^(?P<n>\d+)\.?$")
_SECTION_NUM_RE = re.compile(r"^\d+(\.\d+)+\.?$")    # "2.4.1." / "6.4.2." etc.

# Control chars illegal in XML 1.0 (everything below 0x20 except tab/LF/CR).
# pdftotext -bbox-layout occasionally copies a raw control byte (e.g. 0x02
# from a ligature/superscript glyph) straight into a <word>, which makes
# ElementTree reject the whole document with "not well-formed (invalid
# token)". Strip them before parsing.
_BAD_XML_CHARS_RE = re.compile(
    "[" + "".join(chr(c) for c in range(0x20) if c not in (0x09, 0x0A, 0x0D)) + "]"
)


def _sanitize_xml(xml: str) -> str:
    """Drop XML-1.0-illegal control characters so ElementTree can parse."""
    return _BAD_XML_CHARS_RE.sub("", xml)


@dataclass(frozen=True)
class CaptionAnchor:
    page: int                # 1-based, matching pdftoppm filenames
    kind: str                # "Figure" or "Scheme"
    number: int
    text: str                # first ~120 chars after the anchor word
    bbox_pts: tuple[float, float, float, float]
    page_size_pts: tuple[float, float]


@dataclass(frozen=True)
class FigureBox:
    page: int
    kind: str
    number: int
    bbox_pts: tuple[float, float, float, float]
    page_size_pts: tuple[float, float]


def _ns_tag(root: ET.Element, name: str) -> str:
    if root.tag.startswith("{"):
        ns = root.tag[: root.tag.index("}") + 1]
        return f"{ns}{name}"
    return name


def _next_block_starts_on_page(
    page_blocks: list[tuple[float, float, float, float]],
    after_y: float,
) -> float | None:
    """Return yMin of the block whose yMin > ``after_y`` but is closest to it.

    Used to clip a caption's yMax when pdftotext's block bboxes vertically
    overlap (the next block starts inside the caption block's bbox).
    """
    next_ymin: float | None = None
    for (_, ymin, _, _) in page_blocks:
        if ymin > after_y:
            if next_ymin is None or ymin < next_ymin:
                next_ymin = ymin
    return next_ymin


def find_captions(bbox_xml: str) -> list[CaptionAnchor]:
    """Parse bbox-layout XHTML and return caption anchors in page order.

    Captions are detected per WORD, not per line — pdftotext's
    ``-bbox-layout`` splits a single visual line into multiple ``<line>``
    elements whenever the font (e.g. bold→regular at the caption number)
    changes mid-line, so a naive "first two words of first line" check
    misses every caption whose number is set in a different style than
    the body. Instead:

      1. Find every ``<word>`` whose text is exactly ``Figure`` or
         ``Scheme`` and that lives at the block's left edge (xMin within
         5 pt of the block's xMin AND within ~10 pt of the block-top y).
         That filter excludes inline references like "see Figure 4" because
         those sit mid-line, mid-block.
      2. Look at the next few words in the block (in reading order) for
         a token that matches ``\\d+\\.?``. That's the figure number.
      3. The caption block is the block that the anchor word belongs to;
         the caption bbox is the block bbox.

    De-duplicate by ``(page, kind, number)`` keeping the first hit.
    """
    root = ET.fromstring(bbox_xml)
    t = lambda n: _ns_tag(root, n)

    captions: list[CaptionAnchor] = []
    seen: set[tuple[int, str, int]] = set()
    for page_idx, page in enumerate(root.iter(t("page")), start=1):
        page_w = float(page.attrib["width"])
        page_h = float(page.attrib["height"])
        # Pre-collect every block bbox on the page so we can clip caption
        # bboxes against following blocks that overlap them vertically.
        all_page_blocks = [
            (float(b.attrib["xMin"]), float(b.attrib["yMin"]),
             float(b.attrib["xMax"]), float(b.attrib["yMax"]))
            for b in page.iter(t("block"))
        ]
        for block in page.iter(t("block")):
            block_xmin = float(block.attrib["xMin"])
            block_ymin = float(block.attrib["yMin"])
            block_xmax = float(block.attrib["xMax"])
            block_ymax = float(block.attrib["yMax"])
            # Collect every word in the block in reading order (line then word).
            words_in_block: list[tuple[str, float, float]] = []
            for line in block.iter(t("line")):
                for w in line.iter(t("word")):
                    txt = (w.text or "").strip()
                    if not txt:
                        continue
                    wxmin = float(w.attrib["xMin"])
                    wymin = float(w.attrib["yMin"])
                    words_in_block.append((txt, wxmin, wymin))
            if not words_in_block:
                continue
            for i, (txt, wx, wy) in enumerate(words_in_block):
                if txt not in ("Figure", "Scheme"):
                    continue
                # Caption-position filter: the anchor word lives at the
                # block's left edge AND near the block's top — anything
                # else is an inline reference inside running text.
                if wx > block_xmin + 5.0:
                    continue
                if wy > block_ymin + 12.0:
                    continue
                # Look ahead up to 4 words for the figure number.
                number: int | None = None
                for j in range(i + 1, min(i + 5, len(words_in_block))):
                    nxt = words_in_block[j][0]
                    m = _NUM_RE.match(nxt)
                    if m:
                        number = int(m.group("n"))
                        break
                if number is None:
                    continue
                key = (page_idx, txt, number)
                if key in seen:
                    continue
                seen.add(key)
                # Caption text preview (first ~120 chars).
                preview = " ".join(w[0] for w in words_in_block)[:120]
                # Compute caption yMax from the LINES of the caption, not
                # the block's bbox. pdftotext's block bbox often includes a
                # few points of padding below the last text line, and the
                # NEXT block (e.g. a section heading "2.4.2. Oxidative
                # Coupling...") can start INSIDE that padding region.
                # Crop based on the actual last-line yMax.
                line_ymaxes = [float(line.attrib["yMax"])
                               for line in block.iter(t("line"))]
                caption_ymax = max(line_ymaxes) if line_ymaxes else block_ymax
                # Also stop at the first line whose first word looks like a
                # section number ("N.N." / "N.N.N.") — defence in depth in
                # case a section heading got grouped into the caption block.
                for line in block.iter(t("line")):
                    line_ymin = float(line.attrib["yMin"])
                    if line_ymin <= block_ymin + 1.0:
                        continue
                    first_word = next(iter(line.iter(t("word"))), None)
                    if first_word is None:
                        continue
                    first_txt = (first_word.text or "").strip()
                    if _SECTION_NUM_RE.match(first_txt):
                        caption_ymax = min(caption_ymax, line_ymin - 1.0)
                        break
                # Finally, clip caption_ymax to the next block's yMin if it
                # starts INSIDE the caption block's bbox (pdftotext overlap).
                next_ymin = _next_block_starts_on_page(
                    all_page_blocks, after_y=block_ymin + 1.0,
                )
                if next_ymin is not None and next_ymin < caption_ymax:
                    caption_ymax = next_ymin - 1.0
                captions.append(CaptionAnchor(
                    page=page_idx, kind=txt, number=number,
                    text=preview,
                    bbox_pts=(block_xmin, block_ymin, block_xmax, caption_ymax),
                    page_size_pts=(page_w, page_h),
                ))
                break   # one caption per block is plenty
    return captions


def _find_text_blocks(bbox_xml: str) -> dict[int, list[tuple[float, float, float, float]]]:
    """Return ``{page_idx: [(xMin, yMin, xMax, yMax), ...]}`` for every text block."""
    root = ET.fromstring(bbox_xml)
    t = lambda n: _ns_tag(root, n)
    out: dict[int, list[tuple[float, float, float, float]]] = {}
    for page_idx, page in enumerate(root.iter(t("page")), start=1):
        boxes = []
        for block in page.iter(t("block")):
            boxes.append((
                float(block.attrib["xMin"]),
                float(block.attrib["yMin"]),
                float(block.attrib["xMax"]),
                float(block.attrib["yMax"]),
            ))
        out[page_idx] = boxes
    return out


def figure_bboxes(
    captions: list[CaptionAnchor],
    *,
    page_text_blocks: dict[int, list[tuple[float, float, float, float]]] | None = None,
) -> list[FigureBox]:
    """Compute the figure bbox above each caption.

    Bounds:
      * x: the caption's own xMin .. xMax (caption usually spans the figure's
        horizontal extent; multi-column layouts use the caption's column).
      * y top: the bottom of the **last text block above the caption on the
        same page**, if ``page_text_blocks`` is provided; otherwise the
        bottom of the previous caption on the same page, or page top.
        This naturally trims body text above the figure — the body
        paragraph that precedes the figure ends at its block.yMax, and the
        figure starts in the whitespace below.
      * y bottom: the caption block's yMax (i.e. the bottom of the caption
        text — the crop includes the caption).

    If `page_text_blocks` is omitted (back-compat / unit tests), falls back
    to the previous-caption-bottom or page-top heuristic.
    """
    ordered = sorted(captions, key=lambda c: (c.page, c.bbox_pts[1]))
    prev_bottom_on_page: dict[int, float] = {}
    out: list[FigureBox] = []
    for c in ordered:
        cap_xmin, cap_ymin, cap_xmax, cap_ymax = c.bbox_pts
        page_w, page_h = c.page_size_pts
        # Default top: previous caption bottom on this page, or 0.
        top_y = prev_bottom_on_page.get(c.page, 0.0)
        if page_text_blocks is not None:
            # Find the LAST text block on this page that ends ABOVE the caption.
            blocks_above = [
                b for b in page_text_blocks.get(c.page, [])
                if b[3] < cap_ymin and b[3] > top_y
            ]
            if blocks_above:
                top_y = max(b[3] for b in blocks_above)
        top_y = max(0.0, top_y + 2.0)
        if cap_ymin - top_y < 80.0:
            top_y = max(0.0, cap_ymin - 250.0)
        # X EXTENT: figures often spill outside the caption's text-column
        # xMin / xMax (left labels, right legends). Use the page's content
        # area instead — ~5% margin on each side captures everything.
        x_left = page_w * 0.05
        x_right = page_w * 0.95
        out.append(FigureBox(
            page=c.page, kind=c.kind, number=c.number,
            bbox_pts=(x_left, top_y, x_right, cap_ymax),
            page_size_pts=c.page_size_pts,
        ))
        prev_bottom_on_page[c.page] = cap_ymax
    return out


def column_aware_bboxes(
    captions: list[CaptionAnchor],
    *,
    page_text_blocks: dict[int, list[tuple[float, float, float, float]]] | None = None,
    wide_caption_frac: float = 0.40,
) -> list[FigureBox]:
    """Like ``figure_bboxes`` but x-clips single-column figures to their column.

    Journals lay figures out one of two ways, and the caption width is a clean
    discriminator (verified on two fixtures):

      * **Full-width figure** — caption spans most of the page (ni-zhang: caption
        is 66 % of page width). The drawing fills both columns; keep the
        page-content x-extent (5–95 %), same as ``figure_bboxes``.
      * **Single-column figure / scheme** — caption is narrow and sits in one
        column (co2-mech: "Scheme 5" caption is 5 % of page, centred at 71 %).
        The drawing lives in that one column; clip x to the column so the
        neighbouring text column is not dragged into the crop.

    The split: if a caption's width ≥ ``wide_caption_frac`` of the page → full
    width. Otherwise the caption's centre-x picks the column (left/right half)
    and x is clipped to that half (plus a small margin). This avoids the failure
    mode of a blind midpoint split, which halves full-width figures.

    y-bounds are computed exactly as in ``figure_bboxes`` (delegated), so this is
    purely an x-extent refinement.
    """
    base = figure_bboxes(captions, page_text_blocks=page_text_blocks)
    cap_by_key = {(c.page, c.kind, c.number): c for c in captions}
    out: list[FigureBox] = []
    for box in base:
        cap = cap_by_key.get((box.page, box.kind, box.number))
        x0, y0, x1, y1 = box.bbox_pts
        page_w, _ = box.page_size_pts
        if cap is not None:
            cx0, _, cx1, _ = cap.bbox_pts
            cap_frac = (cx1 - cx0) / page_w
            if cap_frac < wide_caption_frac:
                # Narrow caption → single-column figure. Clip to its column.
                cap_center = 0.5 * (cx0 + cx1)
                mid = 0.5 * page_w
                margin = page_w * 0.04
                if cap_center < mid - 0.10 * page_w:        # left column
                    x0 = max(x0, margin)
                    x1 = min(x1, mid + margin)
                elif cap_center > mid + 0.10 * page_w:      # right column
                    x0 = max(x0, mid - margin)
                    x1 = min(x1, page_w - margin)
                # caption near the spine → ambiguous; leave full-width.
        out.append(FigureBox(
            page=box.page, kind=box.kind, number=box.number,
            bbox_pts=(x0, y0, x1, y1), page_size_pts=box.page_size_pts,
        ))
    return out


def crop_page_rasters(
    boxes: list[FigureBox],
    raster_dir: Path,
    *,
    dpi: int,
    out_dir: Path,
) -> list[Path]:
    """Crop ``page-NN.png`` rasters to each figure's pixel bbox.

    Filenames: ``fig-<kind>-<number>.png`` (overwrites existing). Returns
    the list of crop paths in caption order.
    """
    from PIL import Image
    out_dir.mkdir(parents=True, exist_ok=True)
    scale = dpi / 72.0
    written: list[Path] = []
    cache: dict[int, "Image.Image"] = {}
    for box in boxes:
        page = box.page
        candidates = [
            raster_dir / f"page-{page:02d}.png",
            raster_dir / f"page-{page}.png",
        ]
        src = next((p for p in candidates if p.exists()), None)
        if src is None:
            continue
        if page not in cache:
            cache[page] = Image.open(src)
        im = cache[page]
        x0, y0, x1, y1 = (int(round(v * scale)) for v in box.bbox_pts)
        x0 = max(0, x0); y0 = max(0, y0)
        x1 = min(im.width, x1); y1 = min(im.height, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        crop = im.crop((x0, y0, x1, y1))
        out_path = out_dir / f"fig-{box.kind}-{box.number}.png"
        crop.save(out_path)
        written.append(out_path)
    return written
