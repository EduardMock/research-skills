# research-skills

Agent skills for scientific computing, research, and computational chemistry. Each skill lives in `skills/<name>/` with a `SKILL.md` and any references/templates/hooks/tests next to it. The skills are designed to be shared with other researchers and scientists therfore it has to be reproducible and well documented. 

## Adding a skill

1. Create `skills/<name>/SKILL.md` (frontmatter `name`, `description` — trigger phrases drive activation).
2. Symlink it into local Claude Code so it's discoverable in this checkout when user asks for it:
   ```bash
   ln -s ../../skills/<name> .claude/skills/<name>
   ```
   `.claude/` is gitignored — every clone/worktree does this once after pulling.
3. Add a row to the table in `README.md`.

## Skill conventions

- Description is trigger-heavy: list positive triggers and a "When NOT to use" section.
- Templates / references / scripts live next to `SKILL.md` (see `skills/fast-smiles/references/`, `skills/chem-code-kickstart/templates/`).
- Brevity — every line earns its place.
- Parse any structured content (JSON, YAML, API responses, file formats) through Pydantic models to guarantee data integrity — never hand-roll dict access on untrusted input.
