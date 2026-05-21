"""tmQMg-L CSV client: fetch ligand metadata from raw.githubusercontent.com,
cache locally, and look up by SMILES.

tmQMg-L is the ligand-centric cut of tmQMg — crystallographically observed
ligands extracted from CSD-derived transition-metal complexes. Each ligand
has: SMILES (with explicit-H, lowercase-aromatic conventions), stoichiometry,
occurrence count, and a map of donor-atom indices per source-TMC subgraph.
Repo: github.com/hkneiding/tmQMg-L.

Schema as of v74k (May 2025), `ligands_misc_info.csv`:

  delimiter:  ;   (semicolon, not comma)
  columns:    Unnamed: 0, name, stoichiometry, occurrence,
              parent_metal_occurrences, metal_bond_node_idx_groups,
              smiles, smiles_metal_bond_node_idx_groups,
              weisfeiler_lehman_graph_hash, stable_occurrence

The SMILES column uses **bracketed metal-binding atoms** (e.g., `[N]`, `[C]`,
`[As]`) to mark donor atoms. To match against a "vanilla" SMILES (PubChem or
hand-authored), this client canonicalizes both sides with RDKit when
available — the brackets normalize away. Without RDKit, only exact-string
matches succeed (rare).

Denticity is derived from `metal_bond_node_idx_groups`: a Python-literal dict
whose values are lists of donor-atom-index lists. The denticity is the length
of any non-empty inner list. (Most ligands bind consistently across the TMCs
they appear in.)

Formal charge and InChIKey are NOT in this CSV — they live in
`ligands_fingerprints.csv` (charge) and would need RDKit to compute InChIKey.
This client returns `charge: None` for now.
"""
from __future__ import annotations

import ast
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import requests

# Some tmQMg-L fields (e.g. `parent_metal_occurrences`) hold long lists of
# CSD codes that exceed Python's default csv field limit. Raise it.
csv.field_size_limit(sys.maxsize)

# ----------------------------------------------------------------------------
# Sources
# ----------------------------------------------------------------------------

_RAW_URL_FMT = (
    "https://raw.githubusercontent.com/hkneiding/tmQMg-L/{sha}/{path}"
)
_MISC_INFO_PATH = "ligands_misc_info.csv"
_USER_AGENT = "chemstructure-database-creation/1.0 (+research skill)"

# ----------------------------------------------------------------------------
# RDKit (soft optional)
# ----------------------------------------------------------------------------

try:
    from rdkit import Chem
    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")
    _RDKIT = True
except ImportError:                              # pragma: no cover
    _RDKIT = False


def _canonicalize_smiles(smi: str | None) -> str | None:
    """Canonicalize via RDKit, preserving stereo. Returns None if RDKit
    can't parse the SMILES.

    The tmQMg-L SMILES use bracketed metal-binding atoms (e.g., `[N]`).
    RDKit parses these correctly, and the canonical form normalizes them
    against a regular SMILES of the same molecule.
    """
    if not smi or not _RDKIT:
        return None
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)


def _canonicalize_smiles_no_stereo(smi: str | None) -> str | None:
    """Canonicalize and drop stereo + isotopes. tmQMg-L SMILES usually
    have no stereo annotations (donor atoms are marked, stereo isn't), so
    PubChem hits with isomeric SMILES (e.g., 1,5-cyclooctadiene as
    `C1/C=C\\CC/C=C\\C1`) miss the verbatim canonical match. The
    no-stereo form bridges the gap.
    """
    if not smi or not _RDKIT:
        return None
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True, isomericSmiles=False)


# ----------------------------------------------------------------------------
# Denticity derivation
# ----------------------------------------------------------------------------

def _derive_denticity(donor_groups_field: str | None) -> int | None:
    """Parse the `metal_bond_node_idx_groups` field and return the most common
    denticity across observations.

    The field is a Python-literal dict: `{'CSD-CODE-subgraph-N': [[i0, i1, ...]], ...}`.
    Each inner list is one binding mode; its length is the denticity for that
    observation. Returns the modal denticity (or None if the field is empty
    or unparseable).
    """
    if not donor_groups_field:
        return None
    try:
        parsed = ast.literal_eval(donor_groups_field)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    counts: Counter[int] = Counter()
    for groups in parsed.values():
        if not isinstance(groups, list):
            continue
        for group in groups:
            if isinstance(group, list):
                counts[len(group)] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


# ----------------------------------------------------------------------------
# CSV reading
# ----------------------------------------------------------------------------

def _read_misc_csv(csv_path: Path) -> list[dict[str, Any]]:
    """Read the CSV with semicolon delimiter and cast known numerics."""
    rows: list[dict[str, Any]] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for raw in reader:
            row: dict[str, Any] = {
                k: (v if v != "" else None) for k, v in raw.items()
            }
            for k in ("occurrence", "stable_occurrence"):
                v = row.get(k)
                if v is not None:
                    try:
                        row[k] = int(v)
                    except (TypeError, ValueError):
                        pass
            rows.append(row)
    return rows


def _build_index(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, str]]:
    """Build SMILES → ligand_id index. Two flavors of key:

    - ``smiles``: the verbatim SMILES from the CSV (includes `[N]` markers).
    - ``canonical_smiles``: RDKit-canonical form (if RDKit available).

    A lookup with a vanilla SMILES from PubChem will hit the canonical form.
    """
    by_smiles: dict[str, str] = {}
    by_canon: dict[str, str] = {}
    by_canon_no_stereo: dict[str, str] = {}
    for row in rows:
        lid = row.get("name")
        smi = row.get("smiles")
        if not lid or not smi:
            continue
        by_smiles.setdefault(smi, lid)
        canon = _canonicalize_smiles(smi)
        if canon:
            by_canon.setdefault(canon, lid)
        canon_ns = _canonicalize_smiles_no_stereo(smi)
        if canon_ns:
            by_canon_no_stereo.setdefault(canon_ns, lid)
    return {
        "smiles": by_smiles,
        "canonical_smiles": by_canon,
        "canonical_smiles_no_stereo": by_canon_no_stereo,
    }


# ----------------------------------------------------------------------------
# Client
# ----------------------------------------------------------------------------

class TmQMgLClient:
    """Cached client for tmQMg-L ligand lookups.

    First call downloads ``ligands_misc_info.csv`` (~19 MB) to ``cache_dir``
    and builds a SMILES index. Subsequent calls are local.

    Parameters
    ----------
    cache_dir : str or Path
        Parent directory for the cache. A ``tmQMg-L/`` subdir is created
        inside.
    sha : str
        Git ref to pin tmQMg-L to. Defaults to ``"main"``. Use a real commit
        SHA for reproducibility.
    auto_fetch : bool
        If True (default), download on first use. If False, raise instead.
    timeout : float
        HTTP timeout per request (seconds).
    """

    def __init__(
        self,
        cache_dir: str | Path = ".tmqml_cache",
        *,
        sha: str = "main",
        auto_fetch: bool = True,
        timeout: float = 120.0,
    ) -> None:
        self.cache_dir = Path(cache_dir) / "tmQMg-L"
        self.sha = sha
        self.auto_fetch = auto_fetch
        self.timeout = timeout
        self._rows: list[dict[str, Any]] | None = None
        self._index: dict[str, dict[str, str]] | None = None
        self._row_by_id: dict[str, dict[str, Any]] | None = None

    # -- public --------------------------------------------------------------

    def ensure_loaded(self) -> None:
        """Download (if needed) and build the lookup index in memory."""
        if self._index is not None:
            return
        csv_path = self.cache_dir / _MISC_INFO_PATH
        if not csv_path.exists():
            if not self.auto_fetch:
                raise FileNotFoundError(
                    f"{csv_path} not found and auto_fetch=False"
                )
            self._download_csv(csv_path)

        index_path = self.cache_dir / "index.json"
        if (
            index_path.exists()
            and index_path.stat().st_mtime >= csv_path.stat().st_mtime
        ):
            try:
                self._index = json.loads(index_path.read_text())
                # rows still need to be loaded on first projection
                return
            except (json.JSONDecodeError, OSError):
                pass

        rows = _read_misc_csv(csv_path)
        self._rows = rows
        self._row_by_id = {row["name"]: row for row in rows if row.get("name")}
        self._index = _build_index(rows)
        index_path.write_text(json.dumps(self._index, indent=2))

    def match_by_smiles(self, smiles: str | None) -> dict[str, Any] | None:
        """Look up a ligand by SMILES. Returns a projected record (with
        derived denticity) or None.

        Tries verbatim match first, then canonicalizes via RDKit (if installed)
        and re-checks against the canonical-SMILES index.
        """
        if not smiles:
            return None
        self.ensure_loaded()
        assert self._index is not None
        lid = self._index["smiles"].get(smiles)
        if lid is None:
            canon = _canonicalize_smiles(smiles)
            if canon:
                lid = self._index["canonical_smiles"].get(canon)
        if lid is None:
            # Fallback: drop stereo. PubChem may return an isomeric form for
            # a molecule whose tmQMg-L entry has no stereo annotations.
            canon_ns = _canonicalize_smiles_no_stereo(smiles)
            if canon_ns:
                lid = self._index.get("canonical_smiles_no_stereo", {}).get(canon_ns)
        if lid is None:
            return None
        return self._row_for(lid)

    def match_by_inchikey(self, inchikey: str | None) -> dict[str, Any] | None:
        """The misc-info CSV does not contain InChIKey. Returns None.

        Kept for API parity with the SMILES path; future versions could
        compute InChIKey via RDKit and rebuild the index.
        """
        return None

    # -- internals -----------------------------------------------------------

    def _download_csv(self, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        url = _RAW_URL_FMT.format(sha=self.sha, path=_MISC_INFO_PATH)
        print(f"[tmqmg_l] downloading {url} → {dst}", file=sys.stderr)
        with requests.get(
            url,
            stream=True,
            headers={"User-Agent": _USER_AGENT},
            timeout=self.timeout,
        ) as r:
            r.raise_for_status()
            tmp = dst.with_suffix(dst.suffix + ".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        f.write(chunk)
            tmp.replace(dst)

    def _row_for(self, ligand_id: str) -> dict[str, Any] | None:
        if self._row_by_id is None:
            rows = _read_misc_csv(self.cache_dir / _MISC_INFO_PATH)
            self._rows = rows
            self._row_by_id = {r["name"]: r for r in rows if r.get("name")}
        row = self._row_by_id.get(ligand_id)
        if row is None:
            return None
        return self._project_row(row)

    @staticmethod
    def _project_row(row: dict[str, Any]) -> dict[str, Any]:
        """Return a stable, documented subset of the tmQMg-L row.

        - ``ligand_id``: tmQMg-L's `name` column.
        - ``smiles``: verbatim from the CSV (with `[N]`-style donor markers).
        - ``canonical_smiles``: RDKit-canonical (None if RDKit absent).
        - ``denticity``: derived from `metal_bond_node_idx_groups` (modal).
        - ``stoichiometry``, ``occurrence``, ``stable_occurrence``: passthrough.
        - ``charge``: None — not in this CSV (see `ligands_fingerprints.csv`).
        - ``extras``: free-form passthrough of everything else.
        """
        smi = row.get("smiles")
        out: dict[str, Any] = {
            "ligand_id": row.get("name"),
            "smiles": smi,
            "canonical_smiles": _canonicalize_smiles(smi),
            "denticity": _derive_denticity(row.get("metal_bond_node_idx_groups")),
            "charge": None,                   # not in misc_info; in fingerprints CSV
            "stoichiometry": row.get("stoichiometry"),
            "occurrence": row.get("occurrence"),
            "stable_occurrence": row.get("stable_occurrence"),
        }
        # Pass through unprojected columns under `extras` so the schema can
        # evolve without us guessing. Exclude the bulky CSD-code lists
        # (`parent_metal_occurrences`, `smiles_metal_bond_node_idx_groups`) —
        # they balloon the output for no downstream benefit. Keep the
        # Weisfeiler-Lehman graph hash (small, useful for dedup).
        promoted = {"name", "smiles", "stoichiometry", "occurrence",
                    "stable_occurrence", "metal_bond_node_idx_groups"}
        bulky = {"parent_metal_occurrences",
                 "smiles_metal_bond_node_idx_groups"}
        extras = {
            k: v for k, v in row.items()
            if k not in promoted and k not in bulky
        }
        if extras:
            out["extras"] = extras
        return out


__all__ = ["TmQMgLClient"]
