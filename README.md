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
| [`fast-smiles`](skills/fast-smiles/SKILL.md) | Targeted edits on an existing SMILES from a natural-language instruction. Maps NL → RDKit (`RWMol`, reaction SMARTS, `ReplaceSubstructs`) and enforces a verification ritual so silent misinterpretations don't leak downstream. |
| [`nglview`](skills/nglview/SKILL.md) | Interactive 3D molecular visualization in Jupyter — small molecules, catalysts, organometallics, QM/MM trajectories. Reads Amber, Gromacs, CHARMM, OpenMM; representations tuned for small molecules (ball-stick, licorice, spacefill). |
| [`g-xtb`](skills/g-xtb/SKILL.md) | Fast semi-empirical QM (energies, geometry opt, Hessians, gaps, charges, bond orders) on any element Z=1–103. Approximates ωB97M-V/def2-TZVPPD without DFT-grade compute. Includes a dependency-free Python wrapper. |

## License

MIT — see [LICENSE](LICENSE). Note: `nglview` is reused from K-Dense Inc. under MIT (preserved in its frontmatter `metadata.skill-author`).
