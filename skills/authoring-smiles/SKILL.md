---
name: authoring-smiles
description: Use when writing a SMILES by hand from a paper figure, 2D sketch, or chemical description. Covers construction order, readable-SMILES conventions, substitution-pattern idioms for aromatic cores from synthesis papers, stereochemistry, and organometallic/carbene quirks. For parsing/descriptors/similarity use the rdkit skill; for fetching known compounds use pubchem-api.
---

# Authoring SMILES

## Overview

A valid SMILES is necessary but not sufficient — you want one a reviewer can **read**. This skill codifies the conventions that turn "parses successfully" into "reads like the structure it describes."

**Test of a good SMILES:** a chemist can sketch it on paper from the string alone, without canonicalizing.

## When to use

- Paper figure → SMILES for a compound table
- Sketching a ligand variant by modifying an existing SMILES
- Encoding a catalyst (NHC carbene, metal complex, phosphine) by hand
- Writing substitution patterns from synthesis papers (ortho/meta/para, 2,4,6-trimethyl, 3,5-di-tert-butyl, …)
- Producing SMILES for `mol3D.from_smiles`, `startgen_pythonic`, or `-lig` CLI flags

## When NOT to use

- Looking up a known compound → **pubchem-api**
- Parsing, descriptors, similarity, substructure search → **rdkit**
- Generic molecular manipulation → **datamol**
- Many variants by SMARTS replacement → **rdkit** (`ReplaceSubstructs`)

## The five-rule construction order (do not skip)

1. **Atoms** — element symbols (organic subset B C N O P S F Cl Br I skip brackets if valence is normal)
2. **Bonds** — `-` single (implicit), `=` double, `#` triple, `:` aromatic (implicit with lowercase)
3. **Branches** — parentheses attach to preceding atom
4. **Ring closures** — matching digits; `%10+` for two-digit
5. **Disconnections** — `.` for separate components

Get the skeleton right first. Add stereo and charges last, only if the paper specifies them.

## Picking a starting atom (readability convention)

- **One end of the longest chain** by default
- **Aromatic core with one unique substituent**: start on the ring carbon bearing that substituent (`Xc1ccccc1…`)
- **Catalysts**: start at the metal so the coordination sphere reads first
- **Stereocenters**: use `[C@H]` / `[C@@H]` and order neighbours to match the wedge drawing

The choice is arbitrary — software canonicalizes. Convention exists so humans can read each other's SMILES without launching RDKit.

## Branch ordering

**Smallest branches first, biggest branch unparenthesized at the end.**

- ❌ `C(C(=O)OCC)(F)(F)Br` — deep parens right away
- ✅ `FC(F)(Cl)Br` — tiny branches first, halogens in one glance

**Red flag:** nesting >3 levels of parens means restart from a different atom.

## Stereochemistry — only when the paper specifies it

Don't add stereo by habit. A correct skeleton without stereo is better than a wrong stereo.

- `A/C=C/B` = **E** (both slashes same direction, "flies apart")
- `A/C=C\B` = **Z** (opposite directions)
- `[C@H]` = anticlockwise view from first neighbour; `[C@@H]` = clockwise
- Neighbour order in `[C@H](a)(b)c` = the order you visit from the wedge drawing

## Verification ritual — required after authoring

```python
from rdkit import Chem
from rdkit.Chem import Draw, rdMolDescriptors

mol = Chem.MolFromSmiles(smi)
assert mol is not None, f"syntax error in {smi}"

print(rdMolDescriptors.CalcMolFormula(mol))   # matches paper formula?
Draw.MolToImage(mol, size=(400, 400))          # visual check — matches figure?
print(Chem.MolToSmiles(mol))                   # canonical form for data files
```

For molSimplify: also `mol3D.from_smiles(smi, gen3d=True)` must succeed.

**Never ship to a screening pipeline without the visual check.** Syntax can be valid while the structure is wrong (missing H, wrong regiochemistry, wrong stereo).

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Biggest branch in first parens | Deep nesting | Refactor: small subs first, big chain last |
| Wrong E/Z | Paper E → drawn Z | Same-direction slashes = trans |
| Kekulé instead of aromatic | Extra Hs, wrong sanitization | `c1ccccc1` not `C1=CC=CC=C1` |
| `C` for NHC carbene | RDKit adds 2 H → CH₂ | Use `[C]` |
| Quat centre missing 4th sub | RDKit adds H, degree 3 | Malonate centre is `C(X)(Y)(Z)W` — count 4 |
| Explicit Hs for organic atoms | Verbose, harder to read | Let implicit Hs do the work |
| Ring digit `1` kept open | Parse error or wrong connectivity | After a ring closes, the digit is free to reuse |
| Two-digit ring without `%` | Rejected by parser | Use `%10`, `%11`, … |
| Added stereo paper didn't specify | Introduces wrong stereo | Figure silent → SMILES silent |

## Red flags — STOP and restart

- Parentheses nested >3 levels deep
- Same ring digit appearing 3+ times on an atom
- SMILES >100 chars for a molecule <30 heavy atoms
- You can't read your own SMILES back to the structure without parsing it
- `Chem.MolFromSmiles` returns `None`

## Reference material

Load on demand:

- **references/substitution-patterns.md** — aromatic substitution idioms (ortho/meta/para, 1,3,5-, 2,6-, 2,4,6-), library of common substituent fragments, paper-to-SMILES recipe.
- **references/organometallic-and-catalysts.md** — NHC carbenes (IMes, IPr, SIPr, CAACs), metal centres, dative bonds, molSimplify-specific conventions.
- **references/worked-examples.md** — three paper-to-SMILES walkthroughs (IMes, ethyl E-cinnamate, 2,6-diisopropylaniline) showing the full construction.

## Related skills

- **rdkit** — parsing, descriptors, canonicalization, SMARTS, reactions
- **datamol** — simpler RDKit wrapper
- **pubchem-api** — fetch SMILES for named compounds
- **querying-tmqm-ligands** — crystallographic TMC ligand library
