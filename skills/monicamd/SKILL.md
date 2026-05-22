---
name: mol_monicamd
description: MD trajectory analysis toolkit for geometric and electrostatic features. JSON-controlled workflow for collective variables, PCA/LDA dimensionality reduction, z-matrix (internal) coordinates, ESP point-charge embedding, and QM-ready geometry grid generation. Use for analyzing MD simulations, extracting reaction coordinates, and preparing QM/MM calculations.
license: MIT
metadata:
    skill-author: ru93qon (F.Kiss@campus.lmu.de)
---

# MonicaMD — MD Simulation Analysis Toolkit

## Overview

MonicaMD (**Mo**lecules and **I**nternal **C**luster **A**nalysis of **MD** simulations) is a Python toolkit for analyzing geometric and electrostatic features of any MD simulation. It supports:

- **Collective variable extraction** from MD trajectories (bonds, angles, dihedrals, normal vectors, projections)
- **PCA and LDA** dimensionality reduction to find essential/reactive coordinates
- **Z-matrix (internal) coordinates** for rotation/translation-invariant analysis
- **ESP embedding** — embed a molecule in a point-charge field for QM/MM workflows
- **Grid generation** — apply PCA/LDA components back to real-space geometries for PES sampling
- **JSON-controlled pipeline** — reproducible, checkpoint-restartable workflows

---

## Installation

```bash
git clone https://github.com/NullPointner/MonicaMD.git
cd MonicaMD
conda env create -f mmd.yml
conda activate mmd
pip install .
```

**Key dependencies:** MDAnalysis ≥ 2.2, NumPy ≥ 1.2, SciPy ≥ 1.9, Pandas ≥ 1.4, ParmEd ≥ 3.4

---

## Usage Patterns

### 1. CLI

```bash
MonicaMD.py input.json
# Override any ToDo flag:
MonicaMD.py input.json -reduce_Dim true
```

### 2. Python API

```python
from monicamd import MonicaMD as mmd

Input = mmd.read_json("input.json")
output = mmd.pseudo_main(Input, basename="my_run")
# Access results:
df = output["Outputs"]["dim_reduced"]
```

---

## Input File Structure

```json
{
    "ToDos": {
        "create_universe": true,
        "gen_params": true,
        "iterate_tr": true,
        "reduce_Dim": true
    },
    "Controls": {
        "geo": "md.gro",
        "top": "topol.top",
        "trj": "md.xtc",
        "md_path": "./",
        "selections": ["resname LIG"],
        "subselections": [["resname LIG"]],
        "featuretypes": ["internal"],
        "Do_PCA": true,
        "target_dims": 2,
        "data_preprocessing": "internal_normalisation",
        "write_csv": true,
        "write_tr": true
    }
}
```

---

## Core ToDos Reference

| ToDo | Purpose |
|---|---|
| `create_universe` | Load MD files (gro/xtc/top) via MDAnalysis |
| `gen_params` | Auto-generate featurespace from selection + featuretypes |
| `iterate_tr` | Extract features from every trajectory frame → CSV |
| `reduce_Dim` | Run PCA or LDA on extracted features |
| `apply_components` | Project components → XYZ geometries (grid for QM) |
| `project_data` | Project new data onto existing PCA/LDA subspace |
| `ESP_embedding` | Embed molecule in point charges reproducing ESP |
| `gen_pairs` | Generate atom-pair permutations for custom CVs |
| `find_pairs` | Filter pairs by distance or bond criteria |
| `gen_zmat` | Auto-generate z-matrix connectivity for a selection |
| `read_xyz` | Read XYZ reference structure for alignment/PCA origin |
| `read_chk` | Restore state from a previous run checkpoint |
| `xyz2internal` | Convert XYZ file to internal z-matrix coordinates |
| `check_non_linearity` | Flag linear atom triples that break z-matrix |

---

## Key Controls

### File paths
```json
"md_path": "./",         // prefix for all MD files
"geo": "*.gro",          // structure file (glob ok)
"trj": "*.xtc",          // trajectory file
"top": "*.top",          // topology file
"xyz_in": "ref.xyz",     // external XYZ reference
"chk_file": "out_run.json"  // checkpoint to restore
```

### Atom selections (MDAnalysis syntax)
```json
"selections": ["resname JZ4"],
"subselections": [["resname JZ4"]],   // nested: one list per selection
"ignore_H": false,
"massweight": true
```

### Feature types
```json
"featuretypes": ["xyz"]       // Cartesian
"featuretypes": ["internal"]  // Z-matrix bonds/angles/dihedrals
"featuretypes": ["ESP"]       // Atom-centered electrostatic potential
"featuretypes": ["ESF"]       // Electrostatic field
"featuretypes": ["vel"]       // Velocities
```

### Dimensionality reduction
```json
"Do_PCA": true,
"Do_LDA": true,
"target_dims": 2,
"data_preprocessing": "unit_std_deviation",   // standardize
"data_preprocessing": "internal_normalisation", // normalize bonds 0–1
"Dataset_labels": "labels.csv",   // required for LDA
"LDA_bad_data_label": 0           // label value to exclude
```

### Coordinate alignment
```json
"center_xyz_orientation": true,   // align frames to reference
"center_param": "eckart",         // Eckart conditions
"int_as_xyz": true                // output internal coords as XYZ
```

### Grid generation (apply_components)
```json
"apply_components_control": [
    {"Component": 0, "start": -1.0, "stop": 1.0, "steps": 19},
    {"Component": 1, "start": -0.8, "stop": 0.8, "steps": 19}
],
"apply_components_suffix": ".xyz",
"apply_components_prefix": "grid_"
```

### ESP embedding
```json
"exclude_charges": "resname SOL NA CL",
"embedding_sphere_points": 1000,
"shell_type": "sas",
"add_links": false
```

### Pair finding (for Watson-Crick type CVs)
```json
"pairs_of": ["resname DA and not name *P *T", "resname DT and not name *P *T"],
"find_pair_type": [{"Type": "bond", "Identifier": [{"name": "N1", "subselec": 0}, {"name": "H3", "subselec": 1}]}],
"pair_threshold": [[0, 2.5]],
"unique_pairs": true
```

---

## Custom Collective Variables (Params)

Define arbitrary collective variables using vector algebra:

```json
"Params": {
    "zA": {
        "Type": "normal_vector",
        "Identifier": [
            {"name": "C4", "subselec": 0},
            {"name": "C5", "subselec": 0},
            {"name": "N1", "subselec": 0}
        ]
    },
    "sheer": {
        "Type": "projected_vector_a",
        "Identifier": ["rAT", "yA"]
    },
    "buckle": {
        "Type": "dihedral",
        "Identifier": ["xA", {"Type": "projected_vector_b", "Identifier": ["xT", "zA"]}, "zA"]
    }
}
```

| Type | Description |
|---|---|
| `bond` | Distance between two atoms or named vectors |
| `dihedral` | Dihedral angle from 3 vectors or atoms |
| `normal_vector` | Normal to plane defined by ≥3 atoms |
| `projected_vector_a` | Scalar: component of vector A along B |
| `projected_vector_b` | Vector: projection of B onto plane ⊥ to A |

---

## Output Files

| File | Content |
|---|---|
| `out_<input>.json` | Checkpoint for `read_chk` (full state) |
| `<base>_PCA_combined_mode_N.xyz` | Animation of Nth PCA mode |
| `<base>_PCA_combined_components.csv` | All components + explained variances |
| `<base>_PCA_combined_dim_reduced.csv` | Per-frame projections |
| `<base>_iter_trj.csv` | Feature values per frame |
| `<base>_iter_trj.xyz` | Centered/aligned trajectory |
| `<base>_LDA_combined_dim_reduced.csv` | LDA projections |
| `*.pc` | Point-charge embedding files for QM packages |

---

## Workflow Examples

### Cartesian PCA of a ligand
```json
{
    "ToDos": {"create_universe": true, "read_xyz": true, "gen_params": true, "iterate_tr": true, "reduce_Dim": true},
    "Controls": {
        "featuretypes": ["xyz"], "xyz_in": "ref.xyz",
        "geo": "md.gro", "top": "topol.top", "trj": "md.xtc", "md_path": "../",
        "Do_PCA": true, "massweight": true, "ignore_H": false,
        "selections": ["resname LIG"], "subselections": [["resname LIG"]],
        "center_xyz_orientation": true, "center_param": "eckart",
        "data_preprocessing": "unit_std_deviation",
        "write_csv": true, "write_tr": true, "continue_after_alteration": true
    }
}
```

### Z-matrix PCA (rotation/translation invariant)
Change only these controls vs Cartesian:
```json
"featuretypes": ["internal"],
"data_preprocessing": "internal_normalisation"
```
Remove `center_xyz_orientation` and `center_param` (not needed for internal coords).

### LDA with labeled snapshots
```json
{
    "ToDos": {"create_universe": true, "gen_params": true, "iterate_tr": true, "reduce_Dim": true},
    "Controls": {
        "featuretypes": ["internal"],
        "Do_LDA": true,
        "Dataset_labels": "labels.csv",
        "LDA_bad_data_label": 0,
        "data_preprocessing": "unit_std_deviation"
    }
}
```

### Project new data onto existing subspace
```json
{
    "ToDos": {"read_chk": true, "create_universe": true, "iterate_tr": true, "project_data": true},
    "Controls": {
        "chk_file": "out_previous_run.json",
        "xyz_trj": "new_structures.xyz"
    }
}
```

### Checkpoint / restart
```json
{
    "ToDos": {"read_chk": true, "apply_components": true},
    "Controls": {
        "chk_file": "out_pca_run.json",
        "apply_components_control": [{"Component": 0, "start": -1, "stop": 1, "steps": 19}],
        "apply_components_suffix": ".xyz",
        "int_as_xyz": true
    }
}
```

---

## Scripted Python Usage

```python
from monicamd import MonicaMD as mmd
from monicamd.MonicaMD_utilities import processes

# Build input programmatically
Input = {
    "ToDos": {
        "create_universe": True,
        "gen_pairs": True,
        "find_pairs": True,
        "iterate_tr": True,
    },
    "Controls": {
        "geo": "md.gro", "top": "topol.top", "trj": "md.xtc",
        "pairs_of": ["resname DA and not name *P *T", "resname DT and not name *P *T"],
        "find_pair_type": [{"Type": "bond", "Identifier": [{"name": "N1", "subselec": 0}, {"name": "H3", "subselec": 1}]}],
        "pair_threshold": [(0, 2.5)],
        "Params": { ... },   # define CVs here
        "write_csv": True,
    }
}
output = mmd.pseudo_main(Input, basename="wc_analysis")
```

---

## Tips

- **Typo detection:** MonicaMD uses Levenshtein distance to suggest corrections for misspelled JSON keys — read the output carefully.
- **Checkpointing:** Every run writes `out_<input>.json`. Use `read_chk: true` + `chk_file` to resume or extend a previous run without recomputing features.
- **Internal vs Cartesian:** Internal coordinates (z-matrix) are invariant to rigid-body rotation/translation — no need for alignment. Cartesian coords require `center_xyz_orientation`.
- **`continue_after_alteration`:** Set to `true` in automated pipelines; set to `false` to inspect the auto-filled input before production steps run.
- **No topology file:** For pure XYZ trajectories (no topology), use `xyz_trj` instead of `trj`/`geo`/`top`.
