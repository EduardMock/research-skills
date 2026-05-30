"""Extract embedded images from a paper PDF using ``pdfimages -all``.

Units: lengths in pixels (px), file sizes in bytes (B).

The output is the raw image dump as poppler delivers it (PNG / JPG / JB2 /
…), plus a small ``figs.json`` catalog that downstream subagents read to
decide which figure is the **energy diagram** they need to trace.

Pipeline position. This sits UPSTREAM of ``compounds.py`` — the figures are
how a human (or the planner subagent) finds out which species the paper
discusses, what the mechanism scheme looks like, and what the free-energy
profile says. There is therefore NO ``--require-compounds`` guard here.

Workflow contract::

    extract-figs paper.pdf  →  out/figs/fig-NNN.{png,jpg,...} + figs.json
                            ↓
              energy-diagram analyzer subagent
                            ↓
              mechanism_from_diagram.json
              { "diagram_figure": "...",
                "pathways_by_color": {
                  "blue":  {"label": "1a",
                            "sequence": ["Ni(L1)2", "INT1-1a", "TS1-1a", ...],
                            "rate_limiting_ts": "TS3-1a",
                            "most_stable_int": "INT5-1a"},
                  "red":   {...}, ...
                }
              }
                            ↓
              feeds the planner that writes mechanism.json for the SI pipeline.

The analyzer's job is described in SKILL.md § ``extract-figs``. The principle
is *follow the colored lines* — one colour, one pathway. The labels along
the line are the mechanism for that pathway.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from . import _log


class FigEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    filename: str
    fmt: str          # "png" | "jpg" | "jb2" | "tif" | ...
    size_bytes: int
    md5: str
    width_px: int | None = None    # filled when PIL/Pillow can read the file
    height_px: int | None = None


class FigCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid")
    units: dict[str, str] = Field(
        default_factory=lambda: {"width": "px", "height": "px", "size": "B"},
        alias="_units",
    )
    source_pdf: str
    n_figures: int
    # Top N candidate filenames for the analyzer subagent — narrows 2000+
    # tiny embedded rasters down to the few that are plausibly the energy
    # diagram / mechanism scheme / structure overview. Heuristic:
    # png/jpg only, width≥400 px, sorted by size_bytes descending.
    top_candidates: list[str]
    figures: list[FigEntry]


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _dims_or_none(path: Path) -> tuple[int | None, int | None]:
    """Return (width, height) in px, or (None, None) if PIL can't read it.

    pdfimages can emit JBIG2 (.jb2) and CCITT (.ccitt) blobs that PIL won't
    open — we leave dims as None rather than crashing.
    """
    try:
        from PIL import Image  # type: ignore
        with Image.open(path) as im:
            return im.width, im.height
    except Exception:                                    # pragma: no cover
        return None, None


def decide_needs_crop(n_candidates: int, n_captions: int) -> bool:
    """Decide whether caption-anchored cropping is needed after `pdfimages -all`.

    Policy: try `pdfimages -all` FIRST; only rasterize pages and crop when the
    embedded images can't be the figures. The signal is a count comparison:

      * ``n_captions == 0`` — nothing to anchor a crop to; trust whatever
        pdfimages produced. → no crop.
      * ``n_candidates >= n_captions`` — there are at least as many figure-grade
        embedded rasters as there are Figure/Scheme captions, so pdfimages very
        likely already extracted the figures. → no crop.
      * otherwise — the figures are vector art (e.g. an energy diagram drawn in
        paths, not an embedded raster); pdfimages missed them. → crop.

    This is why ni-zhang (8 vector figures, ~1 incidental embedded jpg) crops,
    while a paper whose figures are embedded photos/rasters does not.
    """
    if n_captions == 0:
        return False
    return n_candidates < n_captions


def run_pdfimages(pdf: Path, out_dir: Path, prefix: str = "fig") -> None:
    """Invoke ``pdfimages -all <pdf> <out_dir>/<prefix>``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    # `-all` writes each image in its native format (jpg / png / jbig2 / …)
    # rather than forcing PPM. pdfimages numbers files <prefix>-000.<ext>.
    subprocess.run(
        ["pdfimages", "-all", str(pdf), str(out_dir / prefix)],
        check=True,
    )


def run_pdftoppm(
    pdf: Path, out_dir: Path,
    *,
    prefix: str = "page",
    dpi: int = 150,
    page_range: str | None = None,
) -> None:
    """Rasterize PDF pages to PNG via ``pdftoppm``.

    Use this when ``pdfimages`` misses an energy diagram (or scheme) drawn as
    vector art rather than an embedded raster. Output files: ``<prefix>-1.png``,
    ``<prefix>-2.png``, ... in ``out_dir``. The page-range syntax follows
    pdftoppm's ``-f N -l M``; pass ``"5-12"`` to render only those pages.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = ["pdftoppm", "-png", "-r", str(dpi)]
    if page_range:
        try:
            first, last = page_range.split("-", 1)
            cmd += ["-f", first.strip(), "-l", last.strip()]
        except ValueError:
            raise SystemExit(
                f"--pages must look like 'N-M', got: {page_range!r}"
            )
    cmd += [str(pdf), str(out_dir / prefix)]
    subprocess.run(cmd, check=True)


def prune(
    out_dir: Path,
    *,
    min_width_px: int,
    min_size_bytes: int,
    keep_ccitt: bool,
) -> dict[str, int]:
    """Delete uninteresting outputs from ``out_dir``.

    Removes:
      - .ccitt / .params sidecars (useless without a CCITT decoder) unless
        ``keep_ccitt=True``
      - images narrower than ``min_width_px`` (atom sprites, ligature glyphs)
      - images smaller than ``min_size_bytes`` (raster fragments)

    Returns ``{"removed_sidecars": int, "removed_tiny": int, "kept": int}``.
    A width of None (PIL couldn't read the file) is NOT used as a removal
    reason — those are kept and let the analyzer subagent decide.
    """
    removed_sidecars = 0
    removed_tiny = 0
    kept = 0
    for path in list(out_dir.iterdir()):
        if not path.is_file() or path.name == "figs.json":
            continue
        suf = path.suffix.lower()
        if not keep_ccitt and suf in (".ccitt", ".params"):
            path.unlink()
            removed_sidecars += 1
            continue
        size = path.stat().st_size
        if size < min_size_bytes:
            path.unlink()
            removed_tiny += 1
            continue
        w, _ = _dims_or_none(path)
        if w is not None and w < min_width_px:
            path.unlink()
            removed_tiny += 1
            continue
        kept += 1
    return {"removed_sidecars": removed_sidecars,
            "removed_tiny": removed_tiny, "kept": kept}


def catalog(
    out_dir: Path,
    source_pdf: Path,
    *,
    top_n: int = 10,
    min_width_px: int = 400,
) -> FigCatalog:
    figs: list[FigEntry] = []
    for path in sorted(out_dir.iterdir()):
        if not path.is_file() or path.name == "figs.json":
            continue
        # pdfimages drops sidecars like ``fig-001.params`` next to .ccitt
        # blobs; they're metadata, not images — skip them.
        if path.suffix.lower() in (".params", ".ccitt"):
            continue
        # Drop a leading dot (".png" → "png"), tolerate uppercase.
        ext = path.suffix.lstrip(".").lower()
        w, h = _dims_or_none(path)
        figs.append(FigEntry(
            filename=path.name,
            fmt=ext or "unknown",
            size_bytes=path.stat().st_size,
            md5=_md5(path),
            width_px=w, height_px=h,
        ))

    # Top-candidate heuristic: png/jpg, wide enough to be a real figure, then
    # take the N largest by file size. This collapses 2000+ embedded raster
    # bits down to a short shortlist the analyzer subagent can actually read.
    candidates = [
        f for f in figs
        if f.fmt in ("png", "jpg", "jpeg", "tif", "tiff")
        and (f.width_px or 0) >= min_width_px
    ]
    candidates.sort(key=lambda f: f.size_bytes, reverse=True)
    top = [f.filename for f in candidates[:top_n]]

    return FigCatalog(
        source_pdf=str(source_pdf),
        n_figures=len(figs),
        top_candidates=top,
        figures=figs,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--paper-pdf", type=Path, required=True,
                   help="path to the main paper PDF")
    p.add_argument("--out-dir", type=Path, required=True,
                   help="directory to write extracted images and figs.json")
    p.add_argument("--prefix", default="fig",
                   help="filename prefix for pdfimages output (default: 'fig')")
    p.add_argument("--min-width-px", type=int, default=100,
                   help="delete images narrower than this from disk + catalog "
                        "(default 100 — atom sprites and glyph fragments). "
                        "Set to 0 to keep everything pdfimages emits.")
    p.add_argument("--min-size-bytes", type=int, default=2048,
                   help="delete files smaller than this (default 2048 = 2 KB). "
                        "Set to 0 to keep everything.")
    p.add_argument("--keep-ccitt", action="store_true",
                   help=".ccitt and .params pdfimages sidecars are deleted by "
                        "default (useless without a CCITT decoder). Set this "
                        "to keep them.")
    p.add_argument("--rasterize-pages", action="store_true",
                   help="ALSO run `pdftoppm -png -r <dpi>` on the paper, "
                        "writing page-1.png, page-2.png, …. Use this when the "
                        "energy diagram is drawn as vector art (pdfimages won't "
                        "see it). Page rasters bypass the --min-* filter so the "
                        "analyzer can find the diagram.")
    p.add_argument("--pages", default=None,
                   help='only rasterize pages "N-M" (forwarded to pdftoppm '
                        "-f/-l). Default: all pages. Has no effect without "
                        "--rasterize-pages.")
    p.add_argument("--page-dpi", type=int, default=150,
                   help="DPI for --rasterize-pages (default 150)")
    p.add_argument("--caption-anchored", action="store_true",
                   help="after --rasterize-pages, find every `Figure N.` / "
                        "`Scheme N.` caption via `pdftotext -bbox-layout` and "
                        "crop the page raster to the region above (and "
                        "including) that caption. Writes one PNG per caption: "
                        "fig-Figure-N.png / fig-Scheme-N.png. Replaces the "
                        "failed density-based crop heuristic.")
    p.add_argument("--keep-page-rasters", action="store_true",
                   help="with --caption-anchored, also keep the full "
                        "page-NN.png after cropping (default: delete).")
    p.add_argument("--column-aware", action="store_true",
                   help="with --caption-anchored, detect single-column vs "
                        "full-width figures from caption width and clip x to the "
                        "caption's column for single-column figures (avoids "
                        "dragging the neighbouring text column into a two-column "
                        "scheme crop). Full-width figures are left unclipped.")
    p.add_argument("--auto", action="store_true",
                   help="pdfimages-FIRST: run `pdfimages -all`, and only fall "
                        "back to rasterize-pages + caption-anchored (column-aware) "
                        "cropping when the embedded images are too few to be the "
                        "figures (fewer figure-grade rasters than Figure/Scheme "
                        "captions). Logs the decision. Skips cropping entirely when "
                        "pdfimages already did the job.")
    p.add_argument("--log", type=Path, default=None)
    p.add_argument("--paper-name", default="(unknown paper)")
    args = p.parse_args(argv)

    if not args.paper_pdf.exists():
        print(f"ERROR: paper PDF not found: {args.paper_pdf}", file=sys.stderr)
        return 2

    run_pdfimages(args.paper_pdf, args.out_dir, prefix=args.prefix)
    prune_stats = prune(
        args.out_dir,
        min_width_px=args.min_width_px,
        min_size_bytes=args.min_size_bytes,
        keep_ccitt=args.keep_ccitt,
    )
    # --auto: try pdfimages first; decide whether cropping is even needed.
    if args.auto:
        from .caption_crop import find_captions, _sanitize_xml
        prelim = catalog(args.out_dir, source_pdf=args.paper_pdf)
        xml0 = _sanitize_xml(subprocess.run(
            ["pdftotext", "-bbox-layout", str(args.paper_pdf), "-"],
            check=True, capture_output=True, text=True,
        ).stdout)
        n_captions = len(find_captions(xml0))
        n_candidates = len(prelim.top_candidates)
        needs_crop = decide_needs_crop(n_candidates, n_captions)
        if needs_crop:
            args.rasterize_pages = True
            args.caption_anchored = True
            args.column_aware = True
            decision = (f"pdfimages -all gave {n_candidates} figure-grade images "
                        f"< {n_captions} captions → cropping (figures look vector)")
        else:
            decision = (f"pdfimages -all gave {n_candidates} figure-grade images "
                        f">= {n_captions} captions → kept pdfimages output, no cropping")
        print(f"extract-figs[--auto]: {decision}", file=sys.stderr)
        if args.log:
            _log.append(args.log, "VERIFIED", f"extract-figs auto: {decision}",
                        paper_name=args.paper_name, source="scripts/extract_figs.py")

    n_crops = 0
    if args.rasterize_pages:
        # Run AFTER prune — page rasters are uniformly large and shouldn't be
        # caught by the dim/size filter, but also shouldn't get wiped if the
        # user invoked extract-figs twice with different thresholds.
        run_pdftoppm(
            args.paper_pdf, args.out_dir,
            prefix="page", dpi=args.page_dpi, page_range=args.pages,
        )
        if args.caption_anchored:
            from .caption_crop import (
                find_captions, figure_bboxes, column_aware_bboxes,
                _find_text_blocks, _sanitize_xml, crop_page_rasters,
            )
            xml = _sanitize_xml(subprocess.run(
                ["pdftotext", "-bbox-layout", str(args.paper_pdf), "-"],
                check=True, capture_output=True, text=True,
            ).stdout)
            captions = find_captions(xml)
            blocks = _find_text_blocks(xml)
            if args.column_aware:
                boxes = column_aware_bboxes(captions, page_text_blocks=blocks)
            else:
                boxes = figure_bboxes(captions, page_text_blocks=blocks)
            written = crop_page_rasters(
                boxes, args.out_dir, dpi=args.page_dpi, out_dir=args.out_dir,
            )
            n_crops = len(written)
            if not args.keep_page_rasters:
                for p in args.out_dir.glob("page-*.png"):
                    p.unlink()
    elif args.caption_anchored:
        print(
            "WARNING: --caption-anchored has no effect without --rasterize-pages",
            file=sys.stderr,
        )
    cat = catalog(args.out_dir, source_pdf=args.paper_pdf)
    cat_path = args.out_dir / "figs.json"
    cat_path.write_text(cat.model_dump_json(indent=2, by_alias=True))

    # Sanity-log a REVIEW if pdfimages dumped suspiciously few files.
    if cat.n_figures == 0 and args.log:
        _log.append(
            args.log, "REVIEW",
            f"extract-figs: pdfimages returned 0 images for {args.paper_pdf} — "
            "the PDF may have rendered figures as vector art (text/paths) rather "
            "than embedded raster images. Try `pdftoppm` or `pdftocairo -svg`.",
            paper_name=args.paper_name,
            source="scripts/extract_figs.py",
        )

    print(
        f"extract-figs: wrote {cat.n_figures} images + {cat_path.name} "
        f"into {args.out_dir} (pruned {prune_stats['removed_tiny']} tiny + "
        f"{prune_stats['removed_sidecars']} sidecars; "
        f"{len(cat.top_candidates)} top candidates)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
