#!/usr/bin/env python3
"""DECIMER (+ MolNextR fallback) wrapper with RDKit validation.

CLI:
    python mol_image_to_smiles.py mol.png
    python mol_image_to_smiles.py 'figs/*.png' -o out/
    python mol_image_to_smiles.py mol.png --engine molnextr

Python:
    import mol_image_to_smiles as m
    r = m.predict("mol.png")            # auto: DECIMER, fall back to MolNextR on parse fail
    rs = m.predict_batch("figs/*.png")  # list[dict]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Any

# Imported lazily so a user with only one engine installed can still use the other.
_decimer_predict = None
_molnextr = None


def _decimer() -> Any:
    global _decimer_predict
    if _decimer_predict is None:
        from DECIMER import predict_SMILES  # uppercase import, lowercase pip pkg
        _decimer_predict = predict_SMILES
    return _decimer_predict


def _validate_smiles(smiles: str) -> tuple[bool, str | None, str | None]:
    """Return (parses, canonical_smiles_or_None, rdkit_error_or_None)."""
    try:
        from rdkit import Chem
        from rdkit import RDLogger
        RDLogger.DisableLog("rdApp.*")  # silence noisy valence warnings
    except ImportError:
        # rdkit not available — accept any non-empty string as "unverified".
        return (bool(smiles), None, "rdkit not installed; skipped validation")
    if not smiles:
        return (False, None, "empty SMILES")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return (False, None, "MolFromSmiles returned None")
    return (True, Chem.MolToSmiles(mol), None)


def _run_decimer(image_path: str) -> dict[str, Any]:
    raw = _decimer()(image_path)
    parses, canonical, err = _validate_smiles(raw)
    return {
        "engine": "decimer",
        "raw_smiles": raw,
        "canonical_smiles": canonical,
        "parses": parses,
        "rdkit_error": err,
    }


def _run_molnextr(image_path: str) -> dict[str, Any]:
    """Optional fallback via HuggingFace inference. Lazy-import so it isn't required."""
    try:
        from huggingface_hub import InferenceClient
    except ImportError as e:
        return {
            "engine": "molnextr",
            "raw_smiles": None,
            "canonical_smiles": None,
            "parses": False,
            "rdkit_error": f"huggingface_hub not installed ({e})",
        }
    client = InferenceClient(model="MolecularAI/MolNextR")
    with open(image_path, "rb") as f:
        raw = client.image_to_text(f.read()).strip()
    parses, canonical, err = _validate_smiles(raw)
    return {
        "engine": "molnextr",
        "raw_smiles": raw,
        "canonical_smiles": canonical,
        "parses": parses,
        "rdkit_error": err,
    }


def predict(
    image_path: str | os.PathLike,
    engine: str = "auto",
) -> dict[str, Any]:
    """Predict SMILES for one image.

    engine = "decimer" | "molnextr" | "auto" (DECIMER first, MolNextR on parse failure)
    """
    image_path = str(Path(image_path).resolve())
    if not Path(image_path).is_file():
        raise FileNotFoundError(image_path)
    warnings: list[str] = []

    if engine == "decimer":
        result = _run_decimer(image_path)
    elif engine == "molnextr":
        result = _run_molnextr(image_path)
    elif engine == "auto":
        result = _run_decimer(image_path)
        if not result["parses"]:
            warnings.append(f"DECIMER output did not parse ({result['rdkit_error']}); falling back to MolNextR")
            result = _run_molnextr(image_path)
    else:
        raise ValueError(f"unknown engine: {engine!r}")

    return {
        "image": image_path,
        "warnings": warnings,
        **result,
    }


def predict_batch(
    pattern: str,
    engine: str = "auto",
) -> list[dict[str, Any]]:
    paths = sorted(glob.glob(pattern))
    if not paths:
        raise FileNotFoundError(f"glob matched no files: {pattern!r}")
    out: list[dict[str, Any]] = []
    for p in paths:
        try:
            out.append(predict(p, engine=engine))
        except Exception as e:
            out.append({
                "image": str(Path(p).resolve()),
                "engine": engine,
                "raw_smiles": None,
                "canonical_smiles": None,
                "parses": False,
                "rdkit_error": f"{type(e).__name__}: {e}",
                "warnings": [],
            })
    return out


def _main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("input", help="image path or glob (e.g. 'figs/*.png')")
    p.add_argument("-o", "--out", default=None, help="output directory; default = stdout JSON")
    p.add_argument("-e", "--engine", default="auto", choices=("auto", "decimer", "molnextr"))
    args = p.parse_args()

    is_glob = any(ch in args.input for ch in "*?[")
    if is_glob:
        results = predict_batch(args.input, engine=args.engine)
    else:
        results = [predict(args.input, engine=args.engine)]

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
