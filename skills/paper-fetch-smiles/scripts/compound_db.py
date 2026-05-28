"""Orchestrator: input list of paper-extracted compounds → enriched JSON DB.

The public function is :func:`build_compound_db`. It's the API contract for
downstream pipeline integrators — keep its signature stable.

Per-row flow:

  pubchem_client.pubchem_fetch(name, fallback_smiles=...)
    -> dict[str, Any]              # IUPAC, SMILES, InChI, InChIKey, MW, ...
  (optional) tmqmg_l_client.match_by_smiles | match_by_inchikey
    -> dict[str, Any] | None       # ligand_id, denticity, charge, ...
  (optional) review.review_record
    -> mutates record with .review

Input row schema is loose: the only required field is ``name`` (or ``smiles``
when ``query_type='smiles'``). Optional: ``paper_id``, ``role``,
``fallback_smiles``, ``query_type``.
"""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any, Iterable

from .pubchem_client import pubchem_fetch, make_throttler
from .tmqmg_l_client import TmQMgLClient

try:
    from .review import review_record
except ImportError:                              # pragma: no cover
    review_record = None                          # type: ignore


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _resolve_one(
    row: dict[str, Any],
    *,
    pubchem_cache_path: Path,
    rate_limit: float,
    force: bool,
    throttle,
) -> dict[str, Any]:
    """Resolve a single input row against PubChem. Returns the merged record
    (input fields preserved alongside PubChem fields)."""
    query_type = row.get("query_type", "name")
    query = row.get("name") if query_type == "name" else row.get(query_type)
    if not query:
        # No query at all — emit an unresolved record so the row is still in
        # the DB.
        return {
            **row,
            "query": None,
            "query_type": query_type,
            "iupac": None,
            "smiles": row.get("fallback_smiles"),
            "canonical_smiles": row.get("fallback_smiles"),
            "isomeric_smiles": None,
            "inchi": None,
            "inchikey": None,
            "cid": None,
            "mw": None,
            "source": "fallback" if row.get("fallback_smiles") else "unresolved",
            "tmqml": None,
        }

    rec = pubchem_fetch(
        query,
        query_type=query_type,
        fallback_smiles=row.get("fallback_smiles"),
        cache_path=pubchem_cache_path,
        force=force,
        rate_limit=rate_limit,
        throttle=throttle,
    )
    # Merge: input fields win for paper_id / role / name (if caller named the
    # compound differently from how PubChem labels it). PubChem fields fill
    # the rest.
    merged: dict[str, Any] = {
        "paper_id": row.get("paper_id"),
        "role": row.get("role"),
        "query": rec.get("query"),
        "query_type": rec.get("query_type"),
        "name": row.get("name") or rec.get("name"),
        "iupac": rec.get("iupac"),
        "smiles": rec.get("smiles"),
        "canonical_smiles": rec.get("canonical_smiles"),
        "isomeric_smiles": rec.get("isomeric_smiles"),
        "inchi": rec.get("inchi"),
        "inchikey": rec.get("inchikey"),
        "cid": rec.get("cid"),
        "mw": rec.get("mw"),
        "fallback_smiles": row.get("fallback_smiles"),
        "source": rec.get("source", "unresolved"),
        "tmqml": None,
    }
    # Carry through any extra input fields (the pipeline may pass through
    # paper-specific metadata like yield, reaction_id, etc.).
    for k, v in row.items():
        if k not in merged and k not in ("query_type", "fallback_smiles"):
            merged[k] = v
    return merged


def build_compound_db(
    rows: Iterable[dict[str, Any]],
    *,
    cache_dir: str | Path = ".compound_cache",
    match_tmqml: bool = False,
    review: bool = False,
    tmqml_sha: str = "main",
    rate_limit: float = 4.0,
    force_refetch: bool = False,
    expected_electronic_structure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a list of paper-extracted compound rows into a normalized DB.

    Parameters
    ----------
    rows : iterable of dict
        Each row needs at least ``name`` (or whatever ``query_type`` points at).
        Optional: ``paper_id``, ``role``, ``fallback_smiles``, ``query_type``.
    cache_dir : str or Path
        Directory for PubChem and tmQMg-L caches. Created if missing.
    match_tmqml : bool
        Whether to look up each record's SMILES/InChIKey in tmQMg-L.
    review : bool
        Whether to run the RDKit review pass.
    tmqml_sha : str
        Git ref to pin tmQMg-L to.
    rate_limit : float
        PubChem requests per second (shared throttle across all rows).
    force_refetch : bool
        Bypass the PubChem cache.
    expected_electronic_structure : dict, optional
        Hand-authored electronic-structure annotations for metal species
        (oxidation_state, d_count, geometry_class, spin_state). Carried
        through to the output unchanged. Pass ``{}`` for purely organic
        papers — the key is always present in the output.

    Returns
    -------
    dict
        ``{"metadata": {...}, "expected_electronic_structure": {...},
        "compounds": [record, ...]}``.
    """
    cache_dir_p = Path(cache_dir)
    cache_dir_p.mkdir(parents=True, exist_ok=True)
    pubchem_cache_path = cache_dir_p / "pubchem_cache.json"

    throttle = make_throttler(rate_limit)
    tmqml_client: TmQMgLClient | None = None
    if match_tmqml:
        tmqml_client = TmQMgLClient(cache_dir=cache_dir_p, sha=tmqml_sha)

    rows = list(rows)
    compounds: list[dict[str, Any]] = []
    sources_used: set[str] = set()
    for row in rows:
        rec = _resolve_one(
            row,
            pubchem_cache_path=pubchem_cache_path,
            rate_limit=rate_limit,
            force=force_refetch,
            throttle=throttle,
        )
        if tmqml_client is not None:
            hit = (
                tmqml_client.match_by_smiles(rec.get("smiles"))
                or tmqml_client.match_by_smiles(rec.get("canonical_smiles"))
                or tmqml_client.match_by_inchikey(rec.get("inchikey"))
            )
            rec["tmqml"] = hit
            if hit is not None:
                sources_used.add("tmqml")
        if review and review_record is not None:
            review_record(rec)
        compounds.append(rec)
        sources_used.add(rec.get("source") or "unresolved")

    metadata = {
        "generated_at": _now_iso(),
        "n_compounds": len(compounds),
        "n_resolved_pubchem": sum(1 for r in compounds if r["source"] == "pubchem"),
        "n_fallback": sum(1 for r in compounds if r["source"] == "fallback"),
        "n_unresolved": sum(1 for r in compounds if r["source"] == "unresolved"),
        "n_tmqml_matched": sum(1 for r in compounds if r.get("tmqml") is not None),
        "sources_used": sorted(sources_used),
        "tmqml_sha": tmqml_sha if match_tmqml else None,
        "cache_dir": str(cache_dir_p),
        "review_enabled": bool(review),
    }
    ees = expected_electronic_structure if expected_electronic_structure is not None else {}
    return {
        "metadata": metadata,
        "expected_electronic_structure": ees,
        "compounds": compounds,
    }


__all__ = ["build_compound_db"]
