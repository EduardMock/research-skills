---
name: chem-code-kickstart
description: Use when starting a new computational-chemistry project or adding a CLAUDE.md to an existing one. Produces a tight CLAUDE.md (project goals, agent-coding principles adapted from the clax / Anthropic C-compiler lessons, coding style, naming, project structure, docs/specs location) plus a minimal repo scaffold (src/, tests/ with --fast mode, env.yml for project-local micromamba, pyproject.toml, .gitignore, docs/specs/, docs/progress.md). Enforces brevity — every line earns its place. After scaffolding, hands off to superpowers:brainstorming to surface which other research-skills (rdkit, g-xtb, paper-fetch-smiles, jupyter-notebook, monicamd, …) are relevant for this project. Triggers — "kickstart this project", "set up a chemistry project", "init this repo as a comp-chem study", "create CLAUDE.md for this study", "scaffold a new chemistry project".
---

# chem-code-kickstart

## Overview

Single-shot scaffold for a computational-chemistry research repo. Output: one tight `CLAUDE.md` + a minimal directory tree. State lives in the generated files, not in the skill. After the scaffold, the agent must hand off to `superpowers:brainstorming` to decide which other research-skills to bring in.

## When to use

- "Kickstart this project"
- "Set up a chemistry project for X"
- "Init this repo as a comp-chem study"
- "Create CLAUDE.md for this study"
- "Scaffold a new chemistry project"

## When NOT to use

- The cwd already has a `CLAUDE.md` you intend to keep — only modify if the user explicitly asks.
- Picking which other skills to use (`rdkit`, `g-xtb`, `paper-fetch-smiles`, …) — that is the brainstorming follow-up, not this skill.
- Per-skill setup for a single calculation — invoke that skill itself.

## Steps

### 1. Detect cwd state

Read `pwd`, `ls`, `git status`. Classify:

| State | Signals | Action |
|---|---|---|
| Empty / near-empty | no `*.py`, no `CLAUDE.md`, no `pyproject.toml` | Full scaffold |
| Has code, no CLAUDE.md | Python files or `pyproject.toml`, no `CLAUDE.md` | Retrofit — never touch existing `src/` |
| Has CLAUDE.md | `CLAUDE.md` present | Ask before any change. Default: skip. |

### 2. Project Q&A

1. **Project goal** — 1–2 sentences. What is this trying to learn or produce?
2. **Package name** — defaults to cwd basename, `snake_case`.
3. **Replicating a reference?** Y/N. Yes when the project reimplements a method, reproduces published results, or benchmarks against a known-good source (DFT/CCSD(T) data, experimental measurements, a higher-level method, a paper). If yes, follow up:
   - What is the oracle? (e.g. `DFT/wB97X-D/def2-TZVPP`, `Janet 2024 benchmark set`)
   - What is it used for *in this project*? One sentence — e.g. "validating xTB rankings against DFT for the top 20 catalysts".
   - Where will reference data live? (e.g. `data/ref/`)
4. **Investigating specific systems?** Y/N. Yes when the project studies named chemical entities — catalysts, complexes, target proteins, reactions. If yes, collect each as `(name, identifier, description)`. `identifier` is a SMILES, an InChI, or a path under `data/`.
5. **Notebooks central?** Y/N. The `notebooks/` directory is always created; this answer only affects one line in `CLAUDE.md` and the post-handoff skill suggestions.

Replicate and investigate are not exclusive — a project that screens specific catalysts *and* validates against DFT benchmarks gets both appendices.

Capture as `{{PROJECT_NAME}}`, `{{PROJECT_GOAL}}`, `{{PKG}}`, `{{ORACLE}}`, `{{ORACLE_PURPOSE}}`, `{{REF_DATA_PATH}}`, `{{SYSTEMS_TABLE}}`, `{{SYSTEMS_LIST}}`, `{{DATE}}`.

`{{SYSTEMS_TABLE}}` renders one row per system in Markdown:
```
| ni_catalyst_a | `CC(=O)O[Ni](OC(C)=O)` | Ni(II) acetate baseline |
| ni_catalyst_b | `data/proteins/2abc.pdb` | apo binding pocket |
```

`{{SYSTEMS_LIST}}` renders the same data as Python tuples for `conftest.py`:
```
    ("ni_catalyst_a", "CC(=O)O[Ni](OC(C)=O)", "Ni(II) acetate baseline"),
    ("ni_catalyst_b", "data/proteins/2abc.pdb", "apo binding pocket"),
```

### 3. Materialize files

For each template in `templates/`, substitute placeholders and `Write` the result. Apply the **overwrite rules** in step 4. Always-created files:

```
CLAUDE.md
docs/progress.md
docs/specs/.gitkeep
src/{{PKG}}/__init__.py
src/{{PKG}}/typeshed.py
tests/__init__.py
tests/conftest.py
notebooks/.gitkeep
scripts/.gitkeep
data/.gitkeep
outputs/.gitkeep
env.yml
pyproject.toml
.gitignore
```

**Conditional appendices — apply each independently:**

| Condition | CLAUDE.md | tests/conftest.py |
|---|---|---|
| Replicating a reference | append `oracle-appendix.md.tmpl` | append `conftest-oracle.py.tmpl` |
| Investigating systems | append `systems-appendix.md.tmpl` | append `conftest-systems.py.tmpl` |
| Both | both appendices, in this order | both appendices, in this order |
| Neither | nothing extra | nothing extra |

If replicating, also create the reference-data directory at `{{REF_DATA_PATH}}` (with a `.gitkeep` if empty) so the path the appendix references actually exists.

### 4. Per-file overwrite rules

| Path | If it exists |
|---|---|
| `CLAUDE.md` | Ask. Never silent-overwrite. |
| `env.yml` | Ask. Offer merge or skip. |
| `pyproject.toml` | Add only missing `[tool.ruff]` / `[tool.pytest.ini_options]` blocks. Don't touch `[project]`. |
| `.gitignore` | Append missing lines only. |
| `docs/progress.md` | Leave alone. |
| `src/{{PKG}}/` populated | Don't touch contents. Only create missing files. |
| Directories | Create if missing. Don't touch existing contents. |
| `.git` absent | Offer `git init`. Don't force. |

### 5. Verify

- No `{{...}}` placeholder leaks through into any written file.
- Each appendix heading appears at most once (`## Oracle pattern`, `## Systems under investigation`) — no accidental double-append.
- `tests/conftest.py` parses as Python (e.g. `python -c "import ast; ast.parse(open('tests/conftest.py').read())"`).
- Report what was created via `git status`.

### 6. Hand off — mandatory final step

End with this message to the agent (paraphrase OK, intent must hold):

> Scaffold complete. **Now invoke `superpowers:brainstorming` and ask the user which other research-skills are relevant for this project.** From the stated goal, suggest a focused subset — e.g. `rdkit` for descriptors/similarity, `g-xtb` for fast semi-empirical QM, `paper-fetch-smiles` for extracting compound tables from PDFs, `mol-image-to-smiles` / `reaction-data-extraction` for figure OCR, `nglview` for 3D visualization, `monicamd` for MD analysis, `jupyter-notebook` for notebook conventions, `authoring-smiles` / `fast-smiles` for SMILES authoring/editing. Don't enumerate all — pick those that fit the stated goal and ask one focused question.

## Brevity rules (apply to every output)

- No prose padding. Every sentence should add what the reader needs to act.
- One-line docstrings on generated stubs; two only if essential.
- Tables instead of paragraphs where the data is comparative.
- Omit a section entirely if it has no content for *this* project.
- Principles get the lines they need to explain *what + why + how to apply* — depth over compression, but no fluff.
- These rules apply to this `SKILL.md` itself.

## Failure modes — surface, don't paper over

- Package name collides with a stdlib name (`os`, `sys`, `json`, `time`, …) → suggest alternative, don't proceed.
- Cwd is inside another project's `src/` → refuse with explanation.
- User-supplied goal is empty after one re-prompt → abort with a clear message.
- A template produces an unsubstituted `{{…}}` placeholder → surface, don't write the file.

## Templates

All templates live in `templates/` next to this file. The placeholder syntax is `{{NAME}}`, matched literally — no regex, no escaping.

| Template | Writes to | Notes |
|---|---|---|
| `CLAUDE.md.tmpl` | `CLAUDE.md` | Core artifact. Append `oracle-appendix.md.tmpl` and/or `systems-appendix.md.tmpl` as the Q&A dictates. |
| `progress.md.tmpl` | `docs/progress.md` | Stub with hint comments. Leave alone if file exists. |
| `env.yml.tmpl` | `env.yml` | Project-local micromamba (`.venv-mm`). |
| `pyproject.toml.tmpl` | `pyproject.toml` | Minimal: `[project]`, `[tool.ruff]`, `[tool.pytest.ini_options]`. |
| `conftest.py.tmpl` | `tests/conftest.py` | `--fast` fixture base. Append oracle/systems blocks below. |
| `conftest-oracle.py.tmpl` | appended to `tests/conftest.py` | When replicating. Adds `REF_DATA` path and `reference` fixture. |
| `conftest-systems.py.tmpl` | appended to `tests/conftest.py` | When investigating. Adds `SYSTEMS` list and parametrised `system` fixture. |
| `gitignore.tmpl` | `.gitignore` | Comp-chem junk + venv + outputs. |
| `typeshed.py.tmpl` | `src/{{PKG}}/typeshed.py` | Empty stub with one example alias commented. |
| `oracle-appendix.md.tmpl` | appended to `CLAUDE.md` | When replicating. Names oracle, purpose, reference-data path; the oracle workflow. |
| `systems-appendix.md.tmpl` | appended to `CLAUDE.md` | When investigating. Table of systems, how to add new ones, sanity-check checklist. |
