"""Optional RDKit-based review pass for resolved compound records.

Goals:

- Confirm SMILES parses, canonicalize it.
- Flag when PubChem's preferred SMILES differs in connectivity from a
  caller-supplied ``fallback_smiles`` (legitimate when PubChem prefers a
  charged form — but worth surfacing).
- Record valence/sanitization issues without raising.

If RDKit is not installed, the function returns a minimal review with
``rdkit_available: false`` and ``smiles_ok: null``. Downstream consumers
should treat ``null`` as "unknown", not "bad".
"""
from __future__ import annotations

from typing import Any

try:
    from rdkit import Chem
    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")             # quiet RDKit's chatty warnings
    _RDKIT = True
except ImportError:                              # pragma: no cover
    _RDKIT = False


def _connectivity_hash(smiles: str | None) -> str | None:
    """Heavy-atom, charge-stripped connectivity hash for diff'ing SMILES.

    Two SMILES with the same skeleton (e.g., the imidazolium ylide vs. the
    neutral NHC) hash to the same value here, so we don't false-flag those.
    """
    if not _RDKIT or not smiles:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    # Neutralize formal charges
    rw = Chem.RWMol(mol)
    for atom in rw.GetAtoms():
        atom.SetFormalCharge(0)
    try:
        Chem.SanitizeMol(rw)
    except (Chem.AtomValenceException, Chem.KekulizeException,
            Chem.AtomKekulizeException):
        # leave it as-is; we just want a connectivity signature
        pass
    try:
        return Chem.MolToSmiles(rw, canonical=True, isomericSmiles=False)
    except Exception:
        # MolToSmiles can still raise on broken aromaticity even after we
        # swallowed the sanitize failure. Fall back to the raw input as
        # the signature — best we can do without crashing.
        return smiles


def review_record(record: dict[str, Any]) -> dict[str, Any]:
    """Annotate ``record`` with a ``review`` block.

    The record is mutated in place AND returned for chaining.
    """
    review: dict[str, Any] = {
        "rdkit_available": _RDKIT,
        "smiles_ok": None,
        "differs_from_fallback": False,
        "notes": [],
    }
    record["review"] = review

    smiles = record.get("smiles")
    fallback = record.get("fallback_smiles")

    if not _RDKIT:
        return record

    if not smiles:
        review["smiles_ok"] = False
        review["notes"].append("no_smiles")
        return record

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        review["smiles_ok"] = False
        review["notes"].append("smiles_unparseable")
    else:
        review["smiles_ok"] = True
        # Always write the RDKit-canonical form back into canonical_smiles.
        record["canonical_smiles"] = Chem.MolToSmiles(mol, canonical=True)

    if smiles and fallback:
        h_smiles = _connectivity_hash(smiles)
        h_fall = _connectivity_hash(fallback)
        if h_smiles is not None and h_fall is not None and h_smiles != h_fall:
            review["differs_from_fallback"] = True
            review["notes"].append("connectivity_differs_from_fallback")

    return record


__all__ = ["review_record"]
