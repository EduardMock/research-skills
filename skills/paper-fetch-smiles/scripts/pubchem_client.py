"""PubChem PUG REST client with on-disk JSON cache.

Pure `requests` (no `pubchempy` dependency). Caches one big JSON dict keyed
by ``"{query_type}:{query}"`` so re-runs are free.

The public entry point is :func:`pubchem_fetch`.

Rate-limit handling: PubChem's documented sustainable rate is ~5 req/s for
PUG REST. The client throttles to ``rate_limit`` req/s and retries on HTTP
429 with exponential backoff.
"""
from __future__ import annotations

import json
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests

# ----------------------------------------------------------------------------
# Defaults
# ----------------------------------------------------------------------------

_PUG_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"
# As of 2025, PubChem's PUG REST returns SMILES under `SMILES` (preferred,
# isomeric where known) and `ConnectivitySMILES` (canonical, no stereo).
# Older deployments may still expose `CanonicalSMILES` / `IsomericSMILES`.
# Requesting all four — the parser handles whichever come back.
_DEFAULT_PROPS = (
    "IUPACName,SMILES,ConnectivitySMILES,CanonicalSMILES,IsomericSMILES,"
    "InChI,InChIKey,MolecularWeight"
)
_DEFAULT_TIMEOUT_S = 20.0
_DEFAULT_RATE_LIMIT_RPS = 4.0
_USER_AGENT = "chemstructure-database-creation/1.0 (+research skill)"

# The shape every record conforms to. Missing values are ``None``.
_EMPTY_RECORD: dict[str, Any] = {
    "query": None,
    "query_type": None,
    "name": None,
    "iupac": None,
    "smiles": None,
    "canonical_smiles": None,
    "isomeric_smiles": None,
    "inchi": None,
    "inchikey": None,
    "cid": None,
    "mw": None,
    "fallback_smiles": None,
    "source": "unresolved",
}


# ----------------------------------------------------------------------------
# Cache I/O
# ----------------------------------------------------------------------------

def _load_cache(cache_path: Path) -> dict[str, dict[str, Any]]:
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_cache(cache_path: Path, cache: dict[str, dict[str, Any]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(cache_path.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, indent=2, sort_keys=True))
    tmp.replace(cache_path)


# ----------------------------------------------------------------------------
# HTTP
# ----------------------------------------------------------------------------

class _Throttler:
    """Trivial token-bucket-ish throttle. One instance per session."""

    def __init__(self, rps: float) -> None:
        self.min_interval = 1.0 / rps if rps > 0 else 0.0
        self._next_ok = 0.0

    def wait(self) -> None:
        if self.min_interval <= 0:
            return
        now = time.monotonic()
        if now < self._next_ok:
            time.sleep(self._next_ok - now)
        self._next_ok = time.monotonic() + self.min_interval


def _get(url: str, throttle: _Throttler, *, timeout: float, max_retries: int = 4
         ) -> requests.Response | None:
    """GET with throttle and 429-aware exponential backoff. Returns None on
    final failure (caller writes a fallback record)."""
    backoff = 1.0
    for attempt in range(max_retries):
        throttle.wait()
        try:
            r = requests.get(url, headers={"User-Agent": _USER_AGENT},
                             timeout=timeout)
        except requests.RequestException:
            time.sleep(backoff)
            backoff *= 2
            continue
        if r.status_code == 200:
            return r
        if r.status_code == 404:
            return r            # not-found is a legitimate result, not a retry
        if r.status_code in (429, 503):
            # respect Retry-After if present
            ra = r.headers.get("Retry-After")
            sleep_for = float(ra) if ra and ra.isdigit() else backoff
            time.sleep(sleep_for)
            backoff *= 2
            continue
        # Other 4xx: treat as unresolvable; don't hammer the server.
        return r
    return None


# ----------------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------------

def _parse_properties_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """PubChem returns {"PropertyTable": {"Properties": [ {...}, ... ]}}.
    Take the first hit (PubChem returns its preferred match first)."""
    try:
        rows = payload["PropertyTable"]["Properties"]
    except (KeyError, TypeError):
        return None
    if not rows:
        return None
    row = rows[0]
    mw_raw = row.get("MolecularWeight")
    try:
        mw = float(mw_raw) if mw_raw is not None else None
    except (TypeError, ValueError):
        mw = None
    # New (2025) keys: `SMILES` (preferred), `ConnectivitySMILES` (no stereo).
    # Legacy keys: `IsomericSMILES`, `CanonicalSMILES`. Either may appear
    # depending on the PubChem deployment we hit.
    smi_pref = row.get("SMILES") or row.get("IsomericSMILES")
    smi_canon = (
        row.get("ConnectivitySMILES")
        or row.get("CanonicalSMILES")
        or smi_pref
    )
    return {
        "cid": row.get("CID"),
        "iupac": row.get("IUPACName"),
        "canonical_smiles": smi_canon,
        "isomeric_smiles": smi_pref if smi_pref != smi_canon else None,
        # `smiles` is the "preferred" form — isomeric if known, else canonical.
        "smiles": smi_pref or smi_canon,
        "inchi": row.get("InChI"),
        "inchikey": row.get("InChIKey"),
        "mw": mw,
    }


# ----------------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------------

def pubchem_fetch(
    query: str,
    *,
    query_type: str = "name",
    fallback_smiles: str | None = None,
    cache_path: Path | str | None = None,
    force: bool = False,
    rate_limit: float = _DEFAULT_RATE_LIMIT_RPS,
    timeout: float = _DEFAULT_TIMEOUT_S,
    throttle: _Throttler | None = None,
) -> dict[str, Any]:
    """Resolve ``query`` against PubChem and return a normalized record.

    Parameters
    ----------
    query : str
        The lookup string.
    query_type : {"name", "smiles", "inchi", "inchikey", "cid"}
        PubChem PUG REST namespace. Defaults to "name".
    fallback_smiles : str, optional
        SMILES to write into ``smiles`` (and mark ``source: "fallback"``) when
        PubChem can't resolve the query. Strongly recommended for
        organometallics, NHCs, and paper-internal codes.
    cache_path : Path or str, optional
        On-disk JSON cache. Defaults to ``./pubchem_cache.json``.
    force : bool
        If True, bypass cache and re-fetch.
    rate_limit : float
        PubChem requests per second. Default 4.
    timeout : float
        Per-request HTTP timeout (seconds).
    throttle : _Throttler, optional
        Reuse a throttler across many calls (the CLI does this). When omitted,
        each call uses a fresh throttler.

    Returns
    -------
    dict
        A record matching the schema in ``references/schema.md``. ``source``
        is one of ``"pubchem"``, ``"cache"``, ``"fallback"``, ``"unresolved"``.
    """
    if cache_path is None:
        cache_path = Path("pubchem_cache.json")
    cache_path = Path(cache_path)
    cache = _load_cache(cache_path)

    cache_key = f"{query_type}:{query}"
    if not force and cache_key in cache:
        hit = dict(cache[cache_key])
        # When the caller passes a fallback_smiles that improves on a previously
        # cached fallback, refresh — but a pubchem hit is always trusted.
        if hit.get("source") == "fallback" and fallback_smiles and hit.get("smiles") != fallback_smiles:
            pass                  # fall through to refetch
        else:
            hit.setdefault("source", "cache")
            return hit

    # Build the URL.
    encoded = urllib.parse.quote(query, safe="")
    url = f"{_PUG_BASE}/{query_type}/{encoded}/property/{_DEFAULT_PROPS}/JSON"

    throttle = throttle or _Throttler(rate_limit)
    response = _get(url, throttle, timeout=timeout)

    record = dict(_EMPTY_RECORD)
    record["query"] = query
    record["query_type"] = query_type
    record["name"] = query if query_type == "name" else None
    record["fallback_smiles"] = fallback_smiles

    parsed: dict[str, Any] | None = None
    if response is not None and response.status_code == 200:
        try:
            parsed = _parse_properties_payload(response.json())
        except ValueError:
            parsed = None

    if parsed is not None:
        record.update(parsed)
        record["source"] = "pubchem"
    elif fallback_smiles is not None:
        record["smiles"] = fallback_smiles
        record["canonical_smiles"] = fallback_smiles
        record["source"] = "fallback"
    else:
        record["source"] = "unresolved"

    cache[cache_key] = record
    _save_cache(cache_path, cache)
    return record


def make_throttler(rate_limit: float = _DEFAULT_RATE_LIMIT_RPS) -> _Throttler:
    """Factory so callers can share a throttler across many fetches."""
    return _Throttler(rate_limit)


__all__ = ["pubchem_fetch", "make_throttler"]
