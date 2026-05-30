"""Crystal-structure fetcher: CSD-preferred, COD-fallback, CIF → discrete .xyz.

Two sources, tried in order:

1. **CSD (Cambridge Structural Database)** — via the CCDC ``ccdc`` Python API.
   Only available when ``ccdc`` is importable AND a valid CCDC licence is
   present on the host. Non-reproducible for anyone without a licence, so it is
   strictly opportunistic: any import / licence / lookup failure falls through
   to COD with a logged note. Look up by refcode (e.g. ``ABEBUF``) or formula.

2. **COD (Crystallography Open Database)** — open REST, no licence, fully
   reproducible. Fetch a CIF directly by COD-ID, or search by formula / free
   text (DOI, name) and take the top hit.

Whichever source wins, the CIF is converted to ``.xyz`` with **openbabel**,
perceiving bonds and splitting the packing into discrete molecules
(``obabel in.cif -O out.xyz --separate``) — one ``.xyz`` per unique molecule,
which is what a QM step (g-xTB) actually wants. The source ``.cif`` is kept
alongside.

Untrusted external payloads (COD search JSON) are parsed through Pydantic
models, never hand-rolled dict access.

Crystal ``.xyz`` are *experimental* geometries: they do NOT carry the
``charge=/multiplicity=`` line-2 contract that the ``si-xyz-extract`` skill
enforces for DFT inputs. Charge/multiplicity are undefined for a packed
structure; downstream code must supply them explicitly if it needs them.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, ConfigDict, Field

_COD_CIF_FMT = "https://www.crystallography.net/cod/{cod_id}.cif"
_COD_SEARCH = "https://www.crystallography.net/cod/result"
_USER_AGENT = "chem-db-lookup/1.0 (+research skill)"
_TIMEOUT_S = 60.0


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CodSearchEntry(BaseModel):
    """One row of a COD ``result?format=json`` response. COD returns many more
    columns than we use; ``extra='ignore'`` keeps the model forward-compatible."""

    model_config = ConfigDict(extra="ignore")

    file: str                                   # the COD-ID
    formula: str | None = None
    chemname: str | None = None
    doi: str | None = None


class CrystalHit(BaseModel):
    """Result of a successful crystal fetch + conversion."""

    model_config = ConfigDict(extra="forbid")

    source: str                                 # "CSD" | "COD"
    identifier: str                             # refcode or COD-ID
    formula: str | None = None
    cif: str                                    # path to the saved .cif
    xyz: list[str] = Field(default_factory=list)  # one path per discrete molecule
    n_molecules: int = 0
    note: str | None = None


# ---------------------------------------------------------------------------
# openbabel CIF -> xyz
# ---------------------------------------------------------------------------

def _require_obabel() -> str:
    exe = shutil.which("obabel")
    if exe is None:
        raise RuntimeError(
            "openbabel ('obabel') not found on PATH. Install it into the "
            "chem-db-lookup env (conda-forge::openbabel)."
        )
    return exe


def _obabel(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run([_require_obabel(), *args], capture_output=True, text=True)


def _xyz_formula(xyz_path: Path) -> str | None:
    """Hill-ish formula key (sorted element:count) for deduping symmetry copies."""
    lines = xyz_path.read_text().splitlines()
    if len(lines) < 3:
        return None
    from collections import Counter
    els: Counter[str] = Counter()
    for ln in lines[2:]:
        parts = ln.split()
        if parts:
            els[parts[0]] += 1
    if not els:
        return None
    return " ".join(f"{el}{n}" for el, n in sorted(els.items()))


def cif_to_xyz(cif_path: Path, out_stem: Path) -> list[Path]:
    """Convert a CIF to discrete-molecule .xyz via openbabel — one file per
    *unique* molecule.

    A CIF stores only the asymmetric unit + symmetry operators. So this runs
    **two passes** (they cannot be combined: openbabel 3.x drops the cell when
    ``--separate`` shares an invocation with ``--fillUC`` — "Cannot fill unit
    cell without a unit cell!"):

    1. ``--fillUC keepconnect`` — apply symmetry operators to build the full
       unit cell, keeping bonded atoms together.
    2. ``--separate -m`` — split the cell into one file per connected fragment.

    The filled cell contains Z symmetry-equivalent copies (and any co-crystal
    solvent/ions), so the fragments are then **deduped by element formula**,
    keeping one representative per unique molecule.

    LIMITATION: openbabel does not unwrap molecules across periodic boundaries,
    so a molecule straddling a cell edge can come out fragmented (you'll see
    small spurious formulas). Always sanity-check the returned atom counts /
    formulas against what you expect. If ``--fillUC`` fails (CIF has no usable
    cell), it falls back to separating the asymmetric unit as-is.

    Returns the written unique .xyz paths (``<stem>.xyz``, ``<stem>2.xyz``, …).
    """
    out_xyz = out_stem.with_suffix(".xyz")
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    filled = out_stem.with_name(out_stem.name + "_filled.cif")

    pass1 = _obabel([str(cif_path), "-O", str(filled), "--fillUC", "keepconnect"])
    source = filled if (pass1.returncode == 0 and filled.exists()
                        and filled.stat().st_size > 0) else cif_path

    written: list[Path] = []
    with tempfile.TemporaryDirectory(dir=str(out_stem.parent)) as td:
        frag_tmpl = Path(td) / "frag.xyz"
        pass2 = _obabel([str(source), "-O", str(frag_tmpl), "--separate", "-m"])
        if filled.exists():
            filled.unlink()
        if pass2.returncode != 0:
            raise RuntimeError(
                f"obabel failed on {cif_path.name}: {pass2.stderr.strip()}"
            )
        frags = sorted(Path(td).glob("frag*.xyz"),
                       key=lambda p: int("".join(c for c in p.stem if c.isdigit()) or 0))
        seen: set[str] = set()
        for fp in frags:
            if fp.stat().st_size == 0:
                continue
            key = _xyz_formula(fp)
            if key is None or key in seen:
                continue
            seen.add(key)
            dst = out_xyz if not written else \
                out_stem.with_name(f"{out_stem.name}{len(written) + 1}.xyz")
            dst.write_text(fp.read_text())
            written.append(dst)

    if not written:
        raise RuntimeError(
            f"obabel produced no non-empty .xyz from {cif_path.name}"
        )
    return written


# ---------------------------------------------------------------------------
# COD (open, reproducible)
# ---------------------------------------------------------------------------

def _cod_download_cif(cod_id: str, dst: Path, *, timeout: float = _TIMEOUT_S) -> None:
    url = _COD_CIF_FMT.format(cod_id=urllib.parse.quote(str(cod_id), safe=""))
    r = requests.get(url, headers={"User-Agent": _USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    if "data_" not in r.text:                   # CIFs start with a data_ block
        raise RuntimeError(f"COD {cod_id}: response is not a CIF")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(r.text)


def _cod_search(*, formula: str | None = None, text: str | None = None,
                timeout: float = _TIMEOUT_S) -> list[CodSearchEntry]:
    """Query the COD REST search and return validated entries (may be empty)."""
    params: dict[str, str] = {"format": "json"}
    if formula:
        params["formula"] = formula            # Hill formula, e.g. "C6 H6"
    if text:
        params["text"] = text
    r = requests.get(_COD_SEARCH, params=params,
                     headers={"User-Agent": _USER_AGENT}, timeout=timeout)
    r.raise_for_status()
    try:
        payload = r.json()
    except ValueError:
        return []
    if not isinstance(payload, list):
        return []
    entries: list[CodSearchEntry] = []
    for row in payload:
        if isinstance(row, dict) and row.get("file"):
            entries.append(CodSearchEntry.model_validate(row))
    return entries


def fetch_from_cod(out_dir: Path, *, cod_id: str | None = None,
                   formula: str | None = None, text: str | None = None,
                   timeout: float = _TIMEOUT_S) -> CrystalHit:
    """Fetch a CIF from COD (direct id or top search hit) and convert to .xyz."""
    note = None
    if cod_id is None:
        hits = _cod_search(formula=formula, text=text, timeout=timeout)
        if not hits:
            raise RuntimeError(
                f"COD search returned no hits (formula={formula!r}, text={text!r})"
            )
        cod_id = hits[0].file
        if len(hits) > 1:
            note = f"COD search had {len(hits)} hits; took top ({cod_id})"
    cif_path = out_dir / f"COD-{cod_id}.cif"
    _cod_download_cif(cod_id, cif_path, timeout=timeout)
    xyz = cif_to_xyz(cif_path, out_dir / f"COD-{cod_id}")
    return CrystalHit(source="COD", identifier=str(cod_id),
                      formula=formula, cif=str(cif_path),
                      xyz=[str(p) for p in xyz], n_molecules=len(xyz), note=note)


# ---------------------------------------------------------------------------
# CSD (opportunistic, licence-gated)
# ---------------------------------------------------------------------------

def _csd_available() -> bool:
    """True only if the CCDC toolkit imports AND a licence is usable."""
    try:
        from ccdc.io import EntryReader  # noqa: F401
    except Exception:
        return False
    try:
        from ccdc.io import EntryReader
        EntryReader("CSD")                      # opening the DB needs a licence
        return True
    except Exception:
        return False


def fetch_from_csd(out_dir: Path, *, refcode: str | None = None,
                   formula: str | None = None) -> CrystalHit:
    """Fetch a CIF from the CSD via the CCDC API. Raises if unavailable so the
    caller can fall back to COD."""
    from ccdc.io import EntryReader  # type: ignore

    reader = EntryReader("CSD")
    entry = None
    if refcode:
        entry = reader.entry(refcode)
    else:
        raise RuntimeError("CSD lookup needs a refcode (formula search not wired)")
    if entry is None:
        raise RuntimeError(f"CSD: no entry for refcode {refcode!r}")
    cif_path = out_dir / f"CSD-{entry.identifier}.cif"
    cif_path.parent.mkdir(parents=True, exist_ok=True)
    cif_path.write_text(entry.crystal.to_string(format="cif"))
    xyz = cif_to_xyz(cif_path, out_dir / f"CSD-{entry.identifier}")
    return CrystalHit(source="CSD", identifier=entry.identifier,
                      formula=formula, cif=str(cif_path),
                      xyz=[str(p) for p in xyz], n_molecules=len(xyz))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fetch_crystal(out_dir: Path, *, refcode: str | None = None,
                  cod_id: str | None = None, formula: str | None = None,
                  text: str | None = None, prefer_csd: bool = True,
                  timeout: float = _TIMEOUT_S) -> CrystalHit:
    """Fetch a crystal structure, CSD-preferred then COD-fallback.

    Provide a CSD ``refcode`` and/or a COD ``cod_id`` / ``formula`` / ``text``.
    Returns a :class:`CrystalHit`. Raises only if BOTH sources fail.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csd_note = None

    if prefer_csd and refcode:
        if _csd_available():
            try:
                return fetch_from_csd(out_dir, refcode=refcode, formula=formula)
            except Exception as e:               # licence/lookup hiccup → COD
                csd_note = f"CSD failed ({e}); fell back to COD"
        else:
            csd_note = "CSD unavailable (no ccdc/licence); used COD"

    # COD fallback. If only a refcode was given, it can't drive COD — surface it.
    if cod_id is None and not formula and not text:
        if refcode and not text:
            text = refcode                       # last resort: text-search the refcode
        if cod_id is None and not formula and not text:
            raise RuntimeError(
                "No COD-usable key. Provide --cod-id, --formula, or --text "
                "(CSD refcode-only lookup needs a licensed ccdc install)."
            )
    hit = fetch_from_cod(out_dir, cod_id=cod_id, formula=formula, text=text,
                         timeout=timeout)
    if csd_note:
        hit = hit.model_copy(update={
            "note": "; ".join(x for x in (csd_note, hit.note) if x)
        })
    return hit


__all__ = ["fetch_crystal", "fetch_from_cod", "fetch_from_csd",
           "cif_to_xyz", "CrystalHit", "CodSearchEntry"]
