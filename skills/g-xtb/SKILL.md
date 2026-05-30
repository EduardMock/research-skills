---
name: g-xtb
description: Use when running fast semi-empirical QM calculations (single-point energies, geometry optimisations, numerical Hessians, HOMO–LUMO gaps, Wiberg bond orders, atomic charges, dipoles) on molecules containing any element up to Z=103 (Lr) — including transition-metal complexes, lanthanides, actinides — without needing DFT-grade compute. Trigger on requests like "compute g-xTB energy of …", "optimise this catalyst with xtb", "xtb single point", "semi-empirical sanity check", or when a DFT step is too slow for a screening loop. g-xTB approximates ωB97M-V/def2-TZVPPD and does not need external parameter files.
---

# g-xTB (Grimme)

## Environment check (run BEFORE any code execution)

This skill needs the `xtb` binary (a modified `xtb 6.7.1`, NOT stock GFN2-xTB). Skill code is launched from mamba env **`g-xtb`** — dedicated because the binary is upstream-specific, not a pip package. Run this check first; if it fails, STOP and report the missing piece — do NOT install ad-hoc (per global CLAUDE.md, always update `/storage/edm/envs/g-xtb.yml` first).

```bash
ENV=g-xtb
micromamba env list | awk '{print $1}' | grep -qx "$ENV" \
  || { echo "ERROR: mamba env '$ENV' not available — define /storage/edm/envs/${ENV}.yml and create with: micromamba create -n $ENV -f /storage/edm/envs/${ENV}.yml" >&2; exit 1; }
# Require the g-xTB-capable xtb binary (either on PATH inside env, or $GXTB_BIN):
if [ -n "${GXTB_BIN:-}" ]; then BIN="$GXTB_BIN"; else BIN=$(micromamba run -n "$ENV" command -v xtb 2>/dev/null); fi
[ -n "$BIN" ] && [ -x "$BIN" ] \
  || { echo "ERROR: 'xtb' binary not available in env '$ENV' and \$GXTB_BIN is unset. Install the g-xTB tarball and set \$GXTB_BIN, or add xtb to /storage/edm/envs/${ENV}.yml." >&2; exit 1; }
"$BIN" --gxtb --help >/dev/null 2>&1 \
  || { echo "ERROR: 'xtb' at $BIN does not support --gxtb (likely stock GFN2-xTB). Replace with the modified g-xTB build from grimme-lab/g-xtb." >&2; exit 1; }
```

## Overview

**g-xTB** is Grimme-lab's general-purpose semi-empirical QM method that approximates **ωB97M-V/def2-TZVPPD** properties across **Z = 1–103**. It is delivered as a modified `xtb 6.7.1` binary interfacing a modified `tblite`. Turn on with the single flag `--gxtb`. No parameter files needed; single-point on water runs in ~0.3 s wall-time.

The upstream project ships statically-linked tarballs — no build step, no `LD_LIBRARY_PATH`, no env activation needed.

## Installation

Download the tarball for your platform from the upstream repo:

```
https://github.com/grimme-lab/g-xtb (tarballs under binaries/)
```

Unpack to a stable location and either:

1. Put the resulting `bin/` on your `PATH` so `xtb` resolves to the g-xTB build, **or**
2. Export `GXTB_BIN=/abs/path/to/xtb-6.7.1/bin/xtb` and let the scripts in this skill pick it up.

The included `scripts/gxtb.py` resolves the binary in this order: `$GXTB_BIN` → `xtb` on `PATH`.

Throughout this skill the bare command is `xtb` for brevity; substitute the absolute path or use `$GXTB_BIN` if your `xtb` on `PATH` is a different build (e.g. stock GFN2-xTB).

## When to use

- Screening thousands of catalysts where DFT is too slow — g-xTB ≈ 0.1–1 s per 3-atom singlepoint, scaling to minutes for TMCs
- Structures containing **transition metals, lanthanides, actinides** — GFN2-xTB degrades for these; g-xTB is the upgrade path
- Getting a *reasonable* starting geometry before handing off to DFT (optimise with `--gxtb --opt`, then single-point with ORCA/TeraChem)
- HOMO/LUMO, dipole, Wiberg bond orders, Mulliken charges as cheap descriptors for ML features
- Numerical Hessian / frequencies on systems GFN2-xTB can't parameterise

**Do NOT use for:**
- Publication-grade thermochemistry (g-xTB is semi-empirical — always verify with DFT)
- Reaction barriers where the TS has unusual bonding (validate against DFT)
- Open-shell systems without checking the unrestricted solution explicitly (see below)
- Excited states — g-xTB is ground-state only

## Quick reference

| Task | Command | Key outputs |
|---|---|---|
| Single-point | `xtb s.xyz --gxtb` | stdout energy, `charges`, `wbo` |
| Geometry optimisation | `xtb s.xyz --gxtb --opt` | `xtbopt.xyz`, `xtbopt.log` (trajectory) |
| Numerical Hessian | `xtb s.xyz --gxtb --hess --acc 0.05` | `hessian`, `g98.out`, `vibspectrum` |
| Opt + Hessian | `xtb s.xyz --gxtb --ohess --acc 0.05` | both of the above |
| Molden file | `xtb s.xyz --gxtb --molden` | `molden.input` |
| Gradient to file | `xtb s.xyz --gxtb --grad` | `gradient`, `energy` |
| Charged / open-shell | `xtb s.xyz --gxtb --chrg 1 --uhf 0` | energy depends on charge/spin |
| Solvation (GB) | `xtb s.xyz --gxtb --gbe toluene` | *electrostatic only — unstable for opt* |
| Solvation (COSMO) | `xtb s.xyz --gxtb --cosmo water` | *gradient inconsistent; single-points only* |
| Tight SCF (pre-Hessian) | add `--acc 0.1` or `--acc 0.01` | smaller is tighter |
| Silent / verbose | `--silent`, `--verbose` | |

**Input geometry formats accepted:** xyz (Å), TM `coord` (Bohr), SDF/MOL, PDB, POSCAR.

**Charge / spin alternatives to flags:** drop a `.CHRG` file (one integer) or `.UHF` file (one integer = number of unpaired electrons) in the working directory — `xtb` picks them up automatically.

### ⚠️ Argument-order contract — geometry file FIRST

This `xtb-6.7.1-gxtb` build is stricter than upstream about CLI parsing: **the geometry path must be the first positional argument, before any flags.** Both `--opt [level]` and `--gxtb` are optional-argument flags that will swallow the *next* token as their value — so putting the xyz after them strips the program of an input file and it aborts with `[ERROR] -1- prog_main: No input file given`.

```bash
# ✅ xtb's documented canonical form — geom first
xtb water.xyz --gxtb --opt normal
xtb water.xyz --opt normal --gxtb
xtb water.xyz --gxtb --hess --acc 0.05

# ❌ abort: "No input file given"
xtb --gxtb water.xyz
xtb --opt normal --gxtb water.xyz
```

When scripting subprocess calls from Python, compose the command list as `[xtb_bin, geometry_path, *flags]`, not `[xtb_bin, *flags, geometry_path]`. The in-repo `Scripts/structgen.xtb_opt` used to get this wrong — pinned by a regression test at `tests/test_ff_gxtb.py::test_xtb_opt_geom_file_is_first_positional`.

## Verified reference numbers

Sanity numbers you can reproduce with `scripts/smoke_test.sh`:

| System | Command | Result | Time |
|---|---|---|---|
| H₂O (neutral) | `xtb h2o.xyz --gxtb` | E = **−76.437476 Eh** | 0.3 s |
| H₂O (opt) | `xtb h2o.xyz --gxtb --opt` | converged, `xtbopt.xyz` written | 0.2 s |
| NH₄⁺ (+1) | `xtb nh4.xyz --gxtb --chrg 1` | E = **−56.885 Eh**, HOMO–LUMO = 23.1 eV | 0.1 s |

## Implementation patterns

### Bash wrapper for clean runs

`xtb` writes ~7 files into the **current working directory** (`charges`, `wbo`, `xtbrestart`, `xtbtopo.mol`, `xtbopt.*`, …). Always run in a dedicated subdir so runs don't clobber each other:

```bash
run_gxtb() {
    local xyz="$1"; shift
    local dir; dir=$(mktemp -d -p "$PWD" "gxtb_$(basename "$xyz" .xyz)_XXX")
    cp "$xyz" "$dir/"
    (cd "$dir" && "${GXTB_BIN:-xtb}" "$(basename "$xyz")" --gxtb "$@")
    echo "$dir"
}

out=$(run_gxtb h2o.xyz --opt)
cat "$out/xtbopt.xyz"
```

### Python — prefer the wrapper in `scripts/gxtb.py`

The best entry point is `scripts/gxtb.py` next to this skill — a thin, dependency-free module that:

- runs each call in its own temp dir (no file collisions)
- always passes `--grad` so `energy` (Turbomole format) is machine-readable
- parses `charges`, `wbo`, `gradient`, and (for opts) `xtbopt.xyz` into a `Result` dataclass
- raises with full stderr + stdout tails on any xtb failure (see note on termination banner below)

**Usage:**

```python
import sys; sys.path.insert(0, "/path/to/research-skills/skills/g-xtb/scripts")
import gxtb

# Single-point from a file
r = gxtb.run("my_catalyst.xyz", chrg=0)
print(r.energy, r.gap_ev, r.charges[:3], r.wbo[:3])

# Single-point from a raw xyz string (auto-detected by the newline test)
xyz = "3\nwater\nO 0 0 0.118\nH 0 0.755 -0.471\nH 0 -0.755 -0.471\n"
r = gxtb.run(xyz)

# Optimisation
r = gxtb.run("catalyst.xyz", opt=True, chrg=0)      # r.coords is now optimised
# Opt + numerical Hessian with tight SCF
r = gxtb.run("catalyst.xyz", opt=True, hess=True)   # acc=0.05 set automatically

# Keep the workdir for debugging
r = gxtb.run("catalyst.xyz", keep=True)
print("files in", r.workdir, list(r.workdir.iterdir()))
```

**molSimplify bridge (also in the wrapper):**

```python
from molSimplify.Classes.mol3D import mol3D
import gxtb
mol = mol3D(); mol.readfromxyz("catalyst.xyz")
opt_mol, r = gxtb.run_mol3D(mol, opt=True, chrg=0)
print(f"E = {r.energy:.6f} Eh over {opt_mol.natoms} atoms; gap = {r.gap_ev:.2f} eV")
```

### Why not `tblite` / `xtb-python` Python bindings?

g-xTB is only in a **modified fork** of tblite; upstream `tblite` and `xtb-python` do **not** expose `--gxtb`. The subprocess wrapper above is currently the only way to call g-xTB from Python.

## Parsing common outputs

- **Total energy:** last `TOTAL ENERGY ... Eh` line in stdout (regex above).
- **HOMO–LUMO gap:** `HOMO-LUMO gap ... eV` line in stdout.
- **Atomic charges:** `charges` file — one float per line, atom order matches input xyz.
- **Wiberg bond orders:** `wbo` file — three columns `i j bond_order` (1-indexed).
- **Optimisation trajectory:** `xtbopt.log` — concatenated xyz frames with energy in the comment line.
- **Frequencies:** `vibspectrum` (Turbomole format), `g98.out` (Gaussian-format Molden-compatible).
- **Gradient (with `--grad`):** `gradient` file (Turbomole format), separate `energy` file.

## Common mistakes

| Mistake | Fix |
|---|---|
| Trying to build from source | Don't — use the upstream static binary tarball. There is no source build path for the modified `xtb 6.7.1` that exposes `--gxtb`. |
| Looking for a parameter file | There is none for g-xTB. `--gxtb` is self-contained. |
| `--ptb` returns energy=0 | Correct — `--ptb` is a *density*-only method; it intentionally provides no total energy / gradient. Use `--gxtb` for energies. |
| Wrong charge on a TMC → SCF diverges or nonsensical energy | Always set `--chrg` explicitly for charged species; never rely on the default. |
| Open-shell calculation silently run as closed-shell | Supply `--uhf N` **or** drop a `.UHF` file. *Any* `--uhf` / `.UHF` triggers unrestricted, even `--uhf 0`. Use this to force UHF on an even-electron system. |
| Parallel Hessian on macOS crashes during diagonalization | README warning. Not relevant on Linux here. |
| `--cosmo` / `--gbe` used during optimisation | Both are flagged unstable/inconsistent by upstream. Use for single-point solvation corrections only; optimise in gas phase. |
| Running two `xtb` jobs in the same cwd | They share `xtbrestart`, `charges`, `wbo`, … and will clobber each other. Always run in a per-job subdir (see wrapper above). |
| Hessian noisy / lots of imaginary modes | Tighten SCF: add `--acc 0.05` or `--acc 0.01`. The README explicitly recommends this. |
| Tried `dock`, `--lmo`, `$pcem`, `$cube` | Upstream-documented limitations — not supported under `--gxtb`. |
| Checking for `"normal termination"` in stdout | xtb prints that banner to **stderr**, not stdout. A subprocess check on `proc.stdout` will always raise. Check `proc.stderr` (already handled by `scripts/gxtb.py`). |
| **Passing the geometry file after `--opt` or `--gxtb`** (silent fail) | In this 6.7.1-gxtb build those flags consume the next token as their optional value and xtb aborts with `No input file given`. Always put the geometry path first: `[xtb_bin, geom, *flags]`. Details in the "Argument-order contract" box above. |
| Expecting `xtbout.json` from `--json` | `--help` lists `--json` but this 6.7.1-gxtb build silently does **not** write `xtbout.json`. Parse the Turbomole `energy` / `gradient` files written by `--grad` instead. |
| Parsing energy from stdout `TOTAL ENERGY` line | Works, but stdout formatting can vary. Use the Turbomole `energy` file (one float per cycle in column 2) — stable across xtb versions. |

## Integration with molSimplify

Typical screening loop pattern:

```
structgen → mol3D → run_gxtb(opt=True) → optimised mol3D + E(g-xTB)
                                        → decide: promote to DFT or discard
```

- Use as a **geometry pre-optimiser** before DFT: factor 100–1000× faster than B3LYP/def2-TZVP and gives reasonable bonds for TMCs.
- Use as a **cheap descriptor source** (HOMO/LUMO, dipole, charges) that feed into RAC-like features or ML models.
- Drop-in replacement wherever GFN2-xTB was used for heavy elements — g-xTB covers the full periodic table; GFN2 does not.

## Related

- Underlying `xtb` docs (most flags behave identically): https://xtb-docs.readthedocs.io
- Preprint: https://chemrxiv.org/engage/chemrxiv/article-details/685434533ba0887c335fc974
- Upstream repo: https://github.com/grimme-lab/g-xtb (tarballs in `binaries/`)
- `xtb --help` prints the current full flag list for this 6.7.1-gxtb build.
