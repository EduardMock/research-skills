"""Thin Python wrapper around the statically-linked g-xTB binary.

Binary resolution order:

1. ``$GXTB_BIN`` env var (absolute path to the g-xTB-enabled xtb)
2. ``xtb`` on ``PATH``

Design rules (see SKILL.md for rationale):

- Every call runs in its own temp dir → no file collisions between parallel jobs.
- Energy comes from the Turbomole-format ``energy`` file (written by --grad),
  not from stdout regex. The file is stable; stdout formatting is not.
- ``xtbout.json`` is advertised in ``--help`` but is NOT actually written by
  this 6.7.1-gxtb build, so we avoid it entirely.
- Returns a plain dataclass; callers never see xtb-internal filenames.
- ``keep=True`` preserves the workdir for debugging.
"""
from __future__ import annotations

import dataclasses as _dc
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

__all__ = ["run", "Result", "GXTB_BIN"]

GXTB_BIN = os.environ.get("GXTB_BIN") or shutil.which("xtb") or "xtb"


@_dc.dataclass
class Result:
    """Parsed output of one g-xTB run. All energies in Hartree, gap in eV."""
    energy: float                               # total energy (Eh)
    gap_ev: float | None                        # HOMO–LUMO gap
    natoms: int
    elements: list[str]                         # symbols in input order
    coords: list[tuple[float, float, float]]    # Å; input geom for SP, optimised for --opt
    charges: list[float] | None                 # atomic Mulliken-like charges
    wbo: list[tuple[int, int, float]] | None    # 1-indexed Wiberg bond orders
    gradient: list[tuple[float, float, float]] | None  # Eh/Bohr, only with grad=True
    converged: bool
    workdir: Path                               # kept only if keep=True, else deleted
    stdout: str
    stderr: str


# -- file parsers -----------------------------------------------------------

def _parse_tm_energy(path: Path) -> float:
    """Turbomole '$energy ... $end' block — last 'cycle' wins."""
    txt = path.read_text().splitlines()
    last = None
    for line in txt:
        parts = line.split()
        if len(parts) >= 2 and parts[0].lstrip("-").replace(".", "", 1).isdigit():
            try:
                int(parts[0])                   # cycle index
                last = float(parts[1])          # total energy
            except ValueError:
                continue
    if last is None:
        raise RuntimeError(f"no energy found in {path}")
    return last


def _parse_tm_gradient(path: Path, natoms: int) -> list[tuple[float, float, float]]:
    """Turbomole '$grad' block. Gradient rows follow the atom-coord rows."""
    lines = path.read_text().splitlines()
    # Skip header + coord block (natoms lines) → gradient is the next natoms lines.
    i = 0
    while i < len(lines) and not lines[i].strip().startswith("cycle"):
        i += 1
    grad_start = i + 1 + natoms
    grad = []
    for row in lines[grad_start:grad_start + natoms]:
        # Turbomole uses "D" for scientific notation in some builds
        parts = row.replace("D", "E").split()
        grad.append((float(parts[0]), float(parts[1]), float(parts[2])))
    return grad


def _parse_xyz(path: Path) -> tuple[list[str], list[tuple[float, float, float]]]:
    lines = path.read_text().splitlines()
    n = int(lines[0])
    elts, coords = [], []
    for row in lines[2:2 + n]:
        p = row.split()
        elts.append(p[0])
        coords.append((float(p[1]), float(p[2]), float(p[3])))
    return elts, coords


def _parse_charges(path: Path) -> list[float]:
    return [float(x) for x in path.read_text().split()]


def _parse_wbo(path: Path) -> list[tuple[int, int, float]]:
    out = []
    for row in path.read_text().splitlines():
        p = row.split()
        if len(p) >= 3:
            out.append((int(p[0]), int(p[1]), float(p[2])))
    return out


_GAP_RE = re.compile(r"HOMO-LUMO gap\s+(-?\d+\.\d+)\s+eV")


# -- main entry point -------------------------------------------------------

def run(
    geom: str | Path,
    *,
    opt: bool = False,
    hess: bool = False,
    chrg: int = 0,
    uhf: int | None = None,
    acc: float | None = None,
    extra: list[str] | None = None,
    keep: bool = False,
    xtb_bin: str = GXTB_BIN,
) -> Result:
    """Run g-xTB on a geometry.

    ``geom`` can be a path to any format xtb accepts (.xyz, coord, .sdf, .mol,
    .pdb, POSCAR) OR a raw xyz string (detected via a newline in the first 1 KB).

    ``opt=True`` runs geometry optimisation; coords in the Result are the
    optimised structure. Otherwise coords match the input.

    ``hess=True`` implies --ohess (opt + Hessian) when combined with opt=True,
    else --hess alone. A tighter --acc is applied automatically for hess runs.

    ``extra`` is for flags not covered above, e.g. ``["--molden"]`` or
    ``["--gbe", "toluene"]``.
    """
    work = Path(tempfile.mkdtemp(prefix="gxtb_"))
    try:
        # 1. Stage the geometry file inside work/
        geom_path = Path(geom) if not ("\n" in str(geom)[:1024]) else None
        if geom_path and geom_path.exists():
            staged = work / geom_path.name
            shutil.copy(geom_path, staged)
        else:
            staged = work / "in.xyz"
            staged.write_text(str(geom))

        # 2. Build command; always request --grad so 'energy' file exists.
        cmd = [xtb_bin, staged.name, "--gxtb", "--chrg", str(chrg), "--grad"]
        if uhf is not None:
            cmd += ["--uhf", str(uhf)]
        if opt and hess:
            cmd += ["--ohess"]
            acc = acc if acc is not None else 0.05
        elif opt:
            cmd += ["--opt"]
        elif hess:
            cmd += ["--hess"]
            acc = acc if acc is not None else 0.05
        if acc is not None:
            cmd += ["--acc", str(acc)]
        if extra:
            cmd += list(extra)

        proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
        # xtb writes "normal termination of xtb" to STDERR (not stdout) and
        # returns 0 even on SCF/opt failure — check for the banner to be sure.
        if proc.returncode != 0 or "normal termination" not in proc.stderr:
            raise RuntimeError(
                f"g-xTB failed (exit {proc.returncode}) running: {' '.join(cmd)}\n"
                f"--- stderr tail ---\n{proc.stderr[-1500:]}\n"
                f"--- stdout tail ---\n{proc.stdout[-1500:]}"
            )

        # 3. Parse outputs
        energy = _parse_tm_energy(work / "energy")
        gap = None
        m = _GAP_RE.search(proc.stdout)
        if m:
            gap = float(m.group(1))

        # Geometry: optimised xyz if --opt, else the input geom
        geom_for_result = work / "xtbopt.xyz" if opt and (work / "xtbopt.xyz").exists() else staged
        # POSCAR / .mol inputs won't round-trip through _parse_xyz. We standardise on
        # xtb's output xyz (written to xtbopt.xyz when --opt; for SP we write our own).
        if not (opt and (work / "xtbopt.xyz").exists()):
            # For SP, write a minimal canonical xyz from the input so the Result is clean.
            if staged.suffix.lower() != ".xyz":
                # Let xtb dump a coord→xyz conversion by re-reading; cheap fallback:
                raise NotImplementedError(
                    "Non-xyz inputs for singlepoints not parsed back — pass .xyz or set opt=True"
                )
        elements, coords = _parse_xyz(geom_for_result)

        natoms = len(elements)
        charges = _parse_charges(work / "charges") if (work / "charges").exists() else None
        wbo = _parse_wbo(work / "wbo") if (work / "wbo").exists() else None
        gradient = _parse_tm_gradient(work / "gradient", natoms) if (work / "gradient").exists() else None

        return Result(
            energy=energy, gap_ev=gap, natoms=natoms,
            elements=elements, coords=coords,
            charges=charges, wbo=wbo, gradient=gradient,
            converged=True, workdir=work,
            stdout=proc.stdout, stderr=proc.stderr,
        )
    finally:
        if not keep and work.exists():
            shutil.rmtree(work)


# -- molSimplify bridge -----------------------------------------------------

def run_mol3D(mol, **kwargs):
    """Convenience: feed a ``molSimplify.Classes.mol3D.mol3D`` instance."""
    import tempfile as _t
    from molSimplify.Classes.mol3D import mol3D as _mol3D

    with _t.NamedTemporaryFile("w", suffix=".xyz", delete=False) as f:
        mol.writexyz(f.name)
        path = f.name
    result = run(path, **kwargs)

    out = _mol3D()
    # Reconstruct an xyz file from parsed coords and read it back — avoids
    # depending on where xtb wrote xtbopt.xyz after the workdir is cleaned.
    with _t.NamedTemporaryFile("w", suffix=".xyz", delete=False) as f:
        f.write(f"{result.natoms}\ng-xTB result E={result.energy:.8f} Eh\n")
        for sym, (x, y, z) in zip(result.elements, result.coords):
            f.write(f"{sym:<2s} {x:14.8f} {y:14.8f} {z:14.8f}\n")
        out_path = f.name
    out.readfromxyz(out_path)
    return out, result


if __name__ == "__main__":
    # Self-check: run on H2O and NH4+, print a one-line summary each.
    import os, sys
    os.chdir(tempfile.mkdtemp(prefix="gxtb_demo_"))

    h2o = "3\nwater\nO 0.0 0.0 0.11779\nH 0.0 0.75545 -0.47116\nH 0.0 -0.75545 -0.47116\n"
    r = run(h2o)
    print(f"H2O  SP : E={r.energy:.6f} Eh  gap={r.gap_ev:.2f} eV  q(O)={r.charges[0]:+.3f}  |grad|={sum(sum(g*g for g in row) for row in r.gradient)**0.5:.6f}")

    r = run(h2o, opt=True)
    print(f"H2O  opt: E={r.energy:.6f} Eh  O-H = {((r.coords[0][0]-r.coords[1][0])**2+(r.coords[0][1]-r.coords[1][1])**2+(r.coords[0][2]-r.coords[1][2])**2)**0.5:.4f} Å")

    nh4 = "5\nNH4+\nN 0 0 0\nH 0.583 0.583 0.583\nH -0.583 -0.583 0.583\nH -0.583 0.583 -0.583\nH 0.583 -0.583 -0.583\n"
    r = run(nh4, chrg=1)
    print(f"NH4+ SP : E={r.energy:.6f} Eh  gap={r.gap_ev:.2f} eV  sum(q)={sum(r.charges):+.3f} (should be +1)")
    sys.exit(0)
