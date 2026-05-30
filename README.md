# research-skills

Agent skills for scientific computing, computational chemistry, and molecular workflows. Compatible with [Claude Code](https://claude.com/claude-code), [Gemini CLI](https://github.com/google-gemini/gemini-cli), [Copilot CLI](https://github.com/github/copilot-cli), and any tool that consumes the [agent skills spec](https://agentskills.io/specification).

## Install

Install one skill:

```bash
npx skills add EduardMock/research-skills@fast-smiles
```

Install all skills in this repo:

```bash
npx skills add EduardMock/research-skills
```

Browse the wider skills ecosystem at [skills.sh](https://skills.sh/).

## Available skills

| Skill | What it does |
|---|---|
| [`chem-code-kickstart`](skills/chem-code-kickstart/SKILL.md) | Scaffold a comp-chem research repo: tight `CLAUDE.md` (goals, agent-coding principles adapted from the [`clax`](https://github.com/smsharma/clax) lessons, coding style, naming, project structure, docs/specs location) plus minimal `src/`, `tests/` with `--fast` mode, `env.yml`, `pyproject.toml`, `.gitignore`. Enforces brevity; hands off to `superpowers:brainstorming` to pick the next skill. |
| [`fast-smiles`](skills/fast-smiles/SKILL.md) | Targeted edits on an existing SMILES from a natural-language instruction. Maps NL → RDKit (`RWMol`, reaction SMARTS, `ReplaceSubstructs`) and enforces a verification ritual so silent misinterpretations don't leak downstream. |
| [`nglview`](skills/nglview/SKILL.md) | Interactive 3D molecular visualization in Jupyter — small molecules, catalysts, organometallics, QM/MM trajectories. Reads Amber, Gromacs, CHARMM, OpenMM; representations tuned for small molecules (ball-stick, licorice, spacefill). |
| [`g-xtb`](skills/g-xtb/SKILL.md) | Fast semi-empirical QM (energies, geometry opt, Hessians, gaps, charges, bond orders) on any element Z=1–103. Approximates ωB97M-V/def2-TZVPPD without DFT-grade compute. Includes a dependency-free Python wrapper. |
| [`mol-image-to-smiles`](skills/mol-image-to-smiles/SKILL.md) | OCSR for a cropped single-molecule image → SMILES. Wraps DECIMER (local, TensorFlow) with optional MolNextR fallback (HuggingFace). RDKit-validates the output. Honest about the organometallic / Markush / stereo limits. |
| [`reaction-data-extraction`](skills/reaction-data-extraction/SKILL.md) | Reaction-scheme image → structured JSON of reactants, products, and conditions with per-molecule SMILES and bounding boxes. Wraps RxnScribe (Coley group, MIT — pix2seq, USPTO-trained). |
| [`paper-fetch-smiles`](skills/paper-fetch-smiles/SKILL.md) | Entry point for converting a chemistry paper into machine-readable data. Hand-authors `compounds.py` (ground truth) → `compounds.png`, and orchestrates the pipeline below. Enforces complete coverage of numbered species + named protagonists; routes authoring through `authoring-smiles`. |
| [`chem-db-lookup`](skills/chem-db-lookup/SKILL.md) | Deterministic lookups against chemically-relevant public databases: PubChem (name/SMILES → canonical data), tmQMg-L (ligands), CSD→COD (crystal structure → CIF → discrete-molecule `.xyz` via openbabel). Ephemeral cache — nothing left in the project. Resolves `compounds.py` → `compounds.json`. |
| [`paper-figure-extract`](skills/paper-figure-extract/SKILL.md) | Figures & schemes out of a paper PDF: caption-anchored, column-aware crops of `Figure N` energy diagrams and region-only `Scheme N` reaction crops + JSON catalogs, fed to analyzer subagents that read the chemistry. |
| [`si-xyz-extract`](skills/si-xyz-extract/SKILL.md) | Computational SI PDF → per-structure `.xyz` (each self-describing `charge=N multiplicity=M` on line 2 — hard rule, no silent neutral-singlet fallback) + parsed DFT `table.json`. Feeds `g-xtb`. |
| [`reaction-mechanism-graph`](skills/reaction-mechanism-graph/SKILL.md) | Joins `structures/*.xyz` + `table.json` + `compounds.json` (+ `mechanism.json`) into `index.json`, verifying every catalytic step by per-element, charge, and electron-parity mass balance. |

## License

MIT — see [LICENSE](LICENSE).
