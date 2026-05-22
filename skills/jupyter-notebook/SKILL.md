---
name: jupyter-notebook
description: Guidelines for creating, structuring, and executing Jupyter notebooks in this project. Auto-triggers whenever notebooks are mentioned.
triggers:
  - notebook
  - jupyter
  - .ipynb
---

# Jupyter Notebook Guidelines

**Auto-trigger:** Apply these rules any time a notebook is mentioned, created, or modified.

---

## Execution

Always run notebooks via nbconvert with the project environment:

```bash
micromamba run -n specified_enviorment jupyter nbconvert --to notebook --execute --inplace notebooks/my_notebook.ipynb
```

To also export HTML output:

```bash
micromamba run -n specified_enviorment jupyter nbconvert --to html --execute notebooks/my_notebook.ipynb
```

Never run notebooks interactively without `%autoreload` active (see below).

---

## Notebook Scope

One notebook = one focused unit:

- A single algorithm/component demo
- One analysis pipeline end-to-end
- One workflow (data → training → evaluation)
- One experiment comparison

**Never mix** unrelated components. Fast re-execution must always be feasible.

---

## Required Cell 1: Autoreload + Imports

Always start every notebook with:

```python
%load_ext autoreload
%autoreload 2

# stdlib
import warnings

# third-party
import numpy as np
import matplotlib.pyplot as plt

# local
from mypackage.module import Component
```

`%autoreload 2` ensures code changes in `src/` are picked up without kernel restart.

---

## Required Cell 2: Theory Block (Markdown)

Every notebook must have a theory/background markdown cell near the top explaining:

- What this notebook demonstrates
- The mathematical formulation (LaTeX symbols)
- Symbol table

**Template:**

```markdown
## Background

This notebook demonstrates **[topic]**.

### Problem Setup

Given [...], we want to compute [...].

### Method

$$
\mathcal{L} = \mathbb{E}_{x \sim p} \left[ \| f_\theta(x) - q(x) \|^2 \right]
$$

### Symbol Reference

| Symbol     | Meaning                      |
| ---------- | ---------------------------- |
| $x$        | molecular configuration      |
| $q(x)$     | committor function           |
| $f_\theta$ | neural network approximation |
| $p$        | equilibrium distribution     |
```

---

## Figures

Always call `plt.show()`. Always include a commented `plt.savefig()` below it:

```python
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(x, y)
ax.set_xlabel("$x$")
ax.set_ylabel("$q(x)$")
ax.set_title("Committor estimate")
plt.tight_layout()
plt.show()
# plt.savefig("figures/committor_estimate.pdf", dpi=300, bbox_inches="tight")
```

After every figure, embed a wrapped caption directly on the figure using `fig.text`.
Width scales with column count (~80 chars per column):

```python
import textwrap
import numpy as np

n_cols = axes.shape[1] if hasattr(axes, "shape") and axes.ndim > 1 else len(np.atleast_1d(axes))
caption_width = 80 * n_cols
caption = textwrap.fill(
    "Figure 1. Estimated committor function q(x) along the reaction coordinate x. "
    "The dashed line marks the transition state at q(x) = 0.5. "
    "$\\Omega[X] = \\sum_i \\omega(x_i)$ corrects the bias of the non-uniform shooting-point selector.",
    width=caption_width,
)
fig.text(0.5, -0.02, caption, ha="center", va="top", fontsize=10)
plt.tight_layout()
plt.show()
# plt.savefig("figures/committor_estimate.pdf", dpi=300, bbox_inches="tight")
```

Rules:

- Use object-oriented API (`fig, ax = plt.subplots()`), not `plt.plot()` directly.
- Always `plt.tight_layout()` before show.
- savefig path goes to `figures/` subdirectory.
- Format: `.pdf` for publications, `.png` for quick checks.
- Caption: use LaTeX math strings (`$\\Omega$`, `$\\sum_i$`) — no Unicode escapes.
- Caption must name what is shown, reference key symbols, and state what the reader should observe.

---

## Additional Guidelines

### Cell Organization

Structure cells in this order:

1. Autoreload + imports
2. Theory markdown
3. Configuration / hyperparameters (one cell, all tunable values)
4. Data loading
5. Model / component setup
6. Experiments / analysis
7. Results / figures
8. Summary markdown (what was shown, key takeaways)

### Configuration Cell

Collect all tunable parameters in a single config cell near the top:

```python
# --- Config ---
N_STEPS = 1000
BETA = 1.0
DT = 0.01
SEED = 42
# --------------
```

### Markdown between sections

Use short markdown headers to separate sections. Makes notebooks scannable.

### Avoid

- Cells longer than ~30 lines — split into functions or helper cells.
- Hardcoded paths — use `pathlib.Path` relative to repo root.
- Side effects in import cells (no training, no file writes).
- Storing large outputs in the notebook — clear outputs before committing.

### Clearing outputs before git commit

```bash
micromamba run -n comlearn jupyter nbconvert --ClearOutputPreprocessor.enabled=True --to notebook --inplace notebooks/my_notebook.ipynb
```

Or use `nbstripout` as a git hook (recommended for the repo).

### Reproducibility

Set seeds at the top of the experiment section:

```python
import torch
import numpy as np
torch.manual_seed(SEED)
np.random.seed(SEED)
```
