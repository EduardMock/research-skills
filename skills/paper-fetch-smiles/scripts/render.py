"""Render a compounds.json file to a labeled 2D-structure grid image.

Accepts either the simple input shape (a JSON list of compound rows) or the
enriched output shape (``{"metadata": {...}, "compounds": [...]}``).

For each record, picks the best SMILES available in this priority order:

    canonical_smiles -> isomeric_smiles -> smiles -> fallback_smiles

Records whose SMILES cannot be parsed by RDKit (typical for some
organometallics / nickelacycles with bare ``[Ni]`` etc.) are rendered as a
labeled placeholder rather than dropped, so the grid keeps the paper's
numbering intact.

Hard dependency: ``rdkit``. (Unlike the rest of this skill, rendering needs
RDKit — there's no graceful-degrade path that produces a useful image.)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rdkit import Chem
from rdkit.Chem import AllChem, Draw

_SMILES_KEYS = ("canonical_smiles", "isomeric_smiles", "smiles", "fallback_smiles")


def _pick_smiles(rec: dict[str, Any]) -> str | None:
    for k in _SMILES_KEYS:
        v = rec.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return None


def _label(rec: dict[str, Any]) -> str:
    paper_id = rec.get("paper_id") or ""
    role = rec.get("role") or ""
    if paper_id and role:
        return f"{paper_id} ({role})"
    return paper_id or role or rec.get("name") or ""


def _load(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("compounds"), list):
        return data["compounds"]
    raise ValueError(
        f"{path}: expected a JSON list or {{'compounds': [...]}} dict"
    )


def render(
    input_path: str | Path,
    output_path: str | Path,
    *,
    mols_per_row: int = 4,
    sub_img_size: tuple[int, int] = (300, 300),
) -> Path:
    """Read ``input_path`` (compounds.json) and write a grid image to
    ``output_path`` (compounds.png).

    Returns the resolved output path.
    """
    in_p = Path(input_path)
    out_p = Path(output_path)
    rows = _load(in_p)

    mols: list[Chem.Mol] = []
    legends: list[str] = []
    for rec in rows:
        smi = _pick_smiles(rec)
        label = _label(rec)
        mol = Chem.MolFromSmiles(smi) if smi else None
        if mol is None:
            # Placeholder: a single carbon atom keeps the grid cell sized;
            # the legend tells the reader what couldn't be rendered.
            mol = Chem.MolFromSmiles("[*]")
            legends.append(f"{label}\n[unparseable]")
        else:
            AllChem.Compute2DCoords(mol)
            legends.append(label)
        mols.append(mol)

    img = Draw.MolsToGridImage(
        mols,
        molsPerRow=mols_per_row,
        subImgSize=sub_img_size,
        legends=legends,
        useSVG=False,
    )
    out_p.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_p))
    return out_p


__all__ = ["render"]
