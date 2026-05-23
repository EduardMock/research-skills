#!/usr/bin/env python3
"""RxnScribe wrapper: scheme image → structured reaction JSON.

CLI:
    python extract_reactions.py scheme.png
    python extract_reactions.py 'schemes/*.png' -o out/
    python extract_reactions.py scheme.png --device cuda
    python extract_reactions.py scheme.png --render-to overlay.png

Python:
    import extract_reactions as r
    model = r.load_model(device="cpu")              # reuse across many images
    result = r.predict(model, "scheme.png")
    results = r.predict_batch(model, "schemes/*.png")
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any

HF_REPO_ID = "yujieq/RxnScribe"
HF_CKPT = "pix2seq_reaction_full.ckpt"


def _validate_smiles(smiles: str | None) -> tuple[bool, str | None, str | None]:
    """Return (parses, canonical_smiles_or_None, rdkit_error_or_None)."""
    if not smiles:
        return (False, None, "empty SMILES")
    try:
        from rdkit import Chem
        from rdkit import RDLogger
        RDLogger.DisableLog("rdApp.*")
    except ImportError:
        return (True, None, "rdkit not installed; skipped validation")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return (False, None, "MolFromSmiles returned None")
    return (True, Chem.MolToSmiles(mol), None)


def _resolve_ckpt(ckpt_path: str | None) -> str:
    """Use provided path or fetch from HF Hub (cached after first call)."""
    if ckpt_path:
        p = Path(ckpt_path).expanduser().resolve()
        if not p.is_file():
            raise FileNotFoundError(f"checkpoint not found: {p}")
        return str(p)
    from huggingface_hub import hf_hub_download
    return hf_hub_download(HF_REPO_ID, HF_CKPT)


def load_model(ckpt_path: str | None = None, device: str = "cpu") -> Any:
    """Load and return a RxnScribe instance. Expensive (~5–15 s on CPU); reuse it."""
    import torch
    from rxnscribe import RxnScribe
    ckpt = _resolve_ckpt(ckpt_path)
    return RxnScribe(ckpt, device=torch.device(device))


def _enrich(role_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add RDKit-canonicalised SMILES + parses flag to molecule items in place."""
    out = []
    for item in role_items:
        new = dict(item)
        if "smiles" in new and isinstance(new["smiles"], str):
            parses, canonical, err = _validate_smiles(new["smiles"])
            new["canonical_smiles"] = canonical
            new["parses"] = parses
            new["rdkit_error"] = err
        out.append(new)
    return out


def predict(
    model: Any,
    image_path: str | os.PathLike,
    molscribe: bool = True,
    ocr: bool = True,
) -> dict[str, Any]:
    """Run RxnScribe on a single scheme image and return a normalised dict."""
    image_path = str(Path(image_path).resolve())
    if not Path(image_path).is_file():
        raise FileNotFoundError(image_path)
    raw_reactions = model.predict_image_file(
        image_path, molscribe=molscribe, ocr=ocr
    )
    # raw_reactions is a list of dicts with keys reactants / conditions / products.
    normalised: list[dict[str, Any]] = []
    for rxn in raw_reactions:
        normalised.append({
            "reactants": _enrich(rxn.get("reactants", [])),
            "conditions": list(rxn.get("conditions", [])),  # text, not molecules
            "products": _enrich(rxn.get("products", [])),
        })
    return {
        "image": image_path,
        "device": str(getattr(model, "device", "?")),
        "n_reactions": len(normalised),
        "reactions": normalised,
    }


def predict_batch(
    model: Any,
    pattern: str,
    molscribe: bool = True,
    ocr: bool = True,
) -> list[dict[str, Any]]:
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"glob matched no files: {pattern!r}")
    return [predict(model, p, molscribe=molscribe, ocr=ocr) for p in paths]


def parse_conditions(text: str) -> dict[str, Any]:
    """Stub: parse a RxnScribe conditions string into structured fields.

    RxnScribe returns conditions as raw OCR (e.g. 'Pd(PPh3)4, K2CO3, DMF, 80 °C, 12 h').
    Extend this with regexes or an LLM call (e.g. claude-haiku) for catalyst/solvent/T/t/yield.
    Returns at minimum {'raw': text}.
    """
    return {"raw": text}


def render_overlay(image_path: str | os.PathLike, result: dict[str, Any], out_path: str | os.PathLike) -> None:
    """Draw RxnScribe's bounding boxes onto a copy of the image for visual QA."""
    from PIL import Image, ImageDraw

    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    palette = {"reactants": (220, 50, 50), "conditions": (50, 180, 50), "products": (50, 90, 220)}
    for rxn in result["reactions"]:
        for role, color in palette.items():
            for item in rxn.get(role, []):
                bbox = item.get("bbox")
                if not bbox or len(bbox) != 4:
                    continue
                draw.rectangle(bbox, outline=color, width=3)
                label = item.get("canonical_smiles") or item.get("smiles") or item.get("text") or role[:-1]
                draw.text((bbox[0] + 2, bbox[1] + 2), str(label)[:40], fill=color)
    img.save(out_path)


def _main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("input", help="scheme image path or glob (e.g. 'schemes/*.png')")
    p.add_argument("-o", "--out", default=None, help="output directory; default = stdout JSON")
    p.add_argument("--ckpt", default=None, help="path to RxnScribe checkpoint (default: fetch from HF Hub)")
    p.add_argument("--device", default="cpu", choices=("cpu", "cuda"))
    p.add_argument("--render-to", default=None, help="(single-image mode only) write a bbox-overlay PNG here")
    args = p.parse_args()

    is_glob = any(ch in args.input for ch in "*?[")

    model = load_model(ckpt_path=args.ckpt, device=args.device)

    if is_glob:
        results = predict_batch(model, args.input)
    else:
        results = [predict(model, args.input)]
        if args.render_to:
            render_overlay(args.input, results[0], args.render_to)
            print(f"wrote overlay → {args.render_to}", file=sys.stderr)

    if args.out:
        outdir = Path(args.out)
        outdir.mkdir(parents=True, exist_ok=True)
        for r in results:
            stem = Path(r["image"]).stem
            (outdir / f"{stem}.json").write_text(json.dumps(r, indent=2))
        print(f"wrote {len(results)} JSON file(s) to {outdir}", file=sys.stderr)
    else:
        json.dump(results if is_glob else results[0], sys.stdout, indent=2)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(_main())
