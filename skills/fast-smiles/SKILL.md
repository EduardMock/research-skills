---
name: fast-smiles
description: Use when performing targeted edits on an existing SMILES from a natural-language instruction — add/remove/replace/relocate a group, remove a protecting group, functionalize a ring atom, change a bond, flip stereo. Maps NL instructions to the right RDKit tool (RWMol, reaction SMARTS, ReplaceSubstructs), covers atom-targeting vocabulary, and enforces a verification ritual. For authoring from scratch use authoring-smiles; for parsing/descriptors/similarity use rdkit; for real reaction-outcome prediction this skill does not apply.
---

# Fast SMILES Edits

## Overview

Input: a SMILES + an NL instruction (`"add OH alpha to the ketone"`, `"remove the Boc group"`, `"move the benzyl group to the alpha carbon"`). Output: an edited SMILES, verified.

**Three editing strategies, one verification ritual.** The skill's value is knowing which strategy fits the instruction, and enforcing the verification loop so silent misinterpretations don't leak into downstream pipelines.

## When to use

- "Add OH to the carbon alpha to the carbonyl"
- "Remove the Boc / TBS / Bn protecting group"
- "Move the benzyl from the quaternary C to the alpha C"
- "Replace methyl with CF₃"
- "Flip the stereo at the alpha carbon"
- "Change this C-C single bond to a double bond"
- "Add a hydroxyl to the pyrone ring carbon alpha to the ring oxygen"

## When NOT to use

- **Authoring from scratch** → `authoring-smiles`
- **Parsing / descriptors / similarity / substructure search** → `rdkit`
- **Real reaction-outcome prediction** → this is *pattern-level* editing, not chemistry. If the user wants an *actual* product of a real reaction, route to a reaction predictor (AiZynthFinder, ASKCOS, or quantum-chemistry workflow)

## Decision table — which tool for which edit

| Edit kind | Tool | Why |
|---|---|---|
| Replace one fragment with another (atom-preserving) | `AllChem.ReactionFromSmarts` | Declarative, atom-mapped, reusable |
| Add / remove / rebond individual atoms | `Chem.RWMol` | Imperative, explicit indices |
| Broad substructure swap, mapping not needed | `Chem.ReplaceSubstructs` | One-liner for simple substitutions |
| Stereo flip (`@` ↔ `@@`, `/` ↔ `\`) | String edit, re-parse | No atom renumbering needed |
| Protecting-group removal | SMARTS library in `references/protecting-groups.md` | Pre-validated patterns |

**Rule of thumb:** if the edit has a clean "reactants >> products" description, use a reaction SMARTS. If it requires hand-picking atoms, use `RWMol`. Never edit the SMILES string directly — it breaks on canonicalization, rings, and explicit-H atoms.

## Atom targeting — NL → SMARTS vocabulary

When an instruction names an atom by chemical relationship, convert to SMARTS first, match, then edit.

| NL phrase | SMARTS |
|---|---|
| "alpha to ketone/aldehyde" | `[C;!$(C=O)][CX3](=O)` — sp3 C attached to carbonyl C |
| "alpha to ester" | `[C;!$(C=O)]C(=O)O[C,H]` |
| "beta to carbonyl" | `[C][C;!$(C=O)]C(=O)` |
| "alpha to a ring oxygen" | `[C;R][O;R]` |
| "benzylic C" | `[CX4][c]` (sp3 C next to aromatic) |
| "allylic C" | `[CX4][C]=[C]` |
| "aromatic C ortho to group X" | `c(c[$X])` (where `$X` is the X SMARTS) |
| "carbon in the pyrone ring" | `[c;r6;$([c]1ccc(=O)oc1)]` (carbon in 2H-pyran-2-one) |
| "carbonyl carbon" | `[CX3]=O` |
| "tertiary amine N" | `[NX3;H0;!$(N=*)]` |

See `references/atom-targeting.md` for the full table and examples of disambiguating multiple matches.

## The four-step edit loop

1. **Parse** input SMILES → `mol = Chem.MolFromSmiles(smi)`
2. **Locate** target atom(s) via `mol.GetSubstructMatches(patt)` — if more than one match, disambiguate explicitly
3. **Apply** edit via `RWMol`, `RunReactants`, or `ReplaceSubstructs`
4. **Verify** — parse output, diff canonical SMILES, check formula delta, visualize

Do NOT hand-edit the SMILES string.

## Core recipes (inline, minimal)

### Add a single atom at a matched atom

```python
from rdkit import Chem

def add_substituent(smi, smarts_target, substituent_smi):
    """Add `substituent_smi` at the first atom matching `smarts_target`."""
    mol = Chem.RWMol(Chem.MolFromSmiles(smi))
    patt = Chem.MolFromSmarts(smarts_target)
    matches = mol.GetSubstructMatches(patt)
    assert len(matches) >= 1, f"no match for {smarts_target}"
    target_idx = matches[0][0]

    sub = Chem.MolFromSmiles(substituent_smi)
    combined = Chem.CombineMols(mol, sub)
    rw = Chem.RWMol(combined)
    # the substituent's first atom sits at len(mol.GetAtoms())
    rw.AddBond(target_idx, mol.GetNumAtoms(), Chem.BondType.SINGLE)
    Chem.SanitizeMol(rw)
    return Chem.MolToSmiles(rw)

# "add OH to the alpha C of phenylacetone"
add_substituent("c1ccc(CC(=O)C)cc1", "[CX4;H2]C(=O)", "O")
# → 'CC(=O)C(O)c1ccccc1'
```

### Remove a matched substructure (protecting group)

```python
def remove_pg(smi, pg_smarts_reaction):
    """pg_smarts_reaction is a reaction SMARTS like '[...][N:1]C(=O)OC(C)(C)C>>[...][NH:1]'"""
    from rdkit.Chem import AllChem
    rxn = AllChem.ReactionFromSmarts(pg_smarts_reaction)
    mol = Chem.MolFromSmiles(smi)
    products = rxn.RunReactants((mol,))
    assert products, "no match; PG not present"
    prod = products[0][0]
    Chem.SanitizeMol(prod)
    return Chem.MolToSmiles(prod)

# Boc removal: [*:1]NC(=O)OC(C)(C)C >> [*:1]N
remove_pg("CC(C)(C)OC(=O)N1CCC(c2ccccc2)CC1",
          "[*:1][N:2]C(=O)OC(C)(C)C>>[*:1][NH:2]")
# → 'c1ccc(C2CCNCC2)cc1'
```

Full PG library: `references/protecting-groups.md`.

### Relocate a substituent

```python
def relocate(smi, source_smarts, target_smarts, group_smarts):
    """Remove `group` from atom matching `source_smarts`, re-attach at atom matching `target_smarts`."""
    # Step 1: remove group
    rxn_remove = AllChem.ReactionFromSmarts(f"{source_smarts}({group_smarts})>>[*:1]")
    # ... (detailed in edit-recipes.md)
```

See `references/edit-recipes.md` for the full pattern — relocation is the trickiest edit and has a dedicated walkthrough.

### Flip stereo

```python
def flip_stereo(smi):
    """Flip all @ to @@ and vice versa, plus / to \\."""
    return smi.translate(str.maketrans({'@': '\x00', '/': '\x01'})).replace(
        '\x00@', '@').replace('\x00', '@@').replace('\x01', '\\').replace('\\', '/')
    # In practice: do it atom-by-atom via RWMol — this string trick is only for single-center molecules
```

For multi-stereocenter or atom-specific flips, use `atom.InvertChirality()` on the matched atom via RWMol. See `references/edit-recipes.md`.

## Conventions for ambiguous instructions

Natural-language edits routinely imply things that aren't valence-consistent. Apply these defaults; if even they fail, **stop and ask the user**.

| NL phrase | Meaning |
|---|---|
| "Move group X from A to B" | Remove X from A (A gets H back); bond X to B (B loses an H). If B has no H, flag. |
| "Add group X to atom Y" | Bond X to Y, replacing one H. If Y has no H, flag. |
| "Remove group X" | Delete X's atoms; atom it was bound to gets H back. |
| "Replace X with Y" | Cleave X, attach Y; adjust H on the anchor atom. |
| "Move the X group to be attached to the same carbon as Y" | Same as "move X to the carbon bearing Y". |

**Valence check before acting:**

```python
target_atom = mol.GetAtomWithIdx(target_idx)
if target_atom.GetTotalNumHs() == 0:
    raise ValueError(f"atom {target_idx} ({target_atom.GetSymbol()}) has no H to replace — edit is not valence-consistent")
```

**Never silently reinterpret** a valence-impossible instruction. The baseline failure mode is: the edit "works", but it's not what the user meant.

## Verification ritual (required)

```python
from rdkit import Chem
from rdkit.Chem import Draw, rdMolDescriptors

mol_in  = Chem.MolFromSmiles(smi_in)
mol_out = Chem.MolFromSmiles(smi_out)
assert mol_out is not None, "output failed to parse"

# 1. heavy-atom delta matches the edit
n_in  = mol_in.GetNumHeavyAtoms()
n_out = mol_out.GetNumHeavyAtoms()
print(f"heavy atoms: {n_in} → {n_out} (Δ = {n_out - n_in})")

# 2. formula delta
print(rdMolDescriptors.CalcMolFormula(mol_in), "→",
      rdMolDescriptors.CalcMolFormula(mol_out))

# 3. canonical SMILES
print("canonical:", Chem.MolToSmiles(mol_out))

# 4. side-by-side visual
Draw.MolsToGridImage([mol_in, mol_out], molsPerRow=2,
                     subImgSize=(350, 300),
                     legends=["before", "after"])
```

Expected Δ for common edits:

| Edit | Heavy-atom Δ | Formula Δ |
|---|---|---|
| +OH | +1 | +O |
| +Me | +1 | +CH₂ (implicit H shift) |
| +CF₃ | +4 | +CF₂ (replaces 1 H) |
| Remove Boc | −7 | −C₅H₈O₂ (minus -C(=O)OC(CH₃)₃, gain 1 H) |
| Remove TBS | −6 | −C₆H₁₄Si |

If the formula Δ doesn't match the intended edit, the edit is wrong. Don't ship it.

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Edited SMILES string directly | Works on trivial cases, breaks on rings/canonical indices | Use RWMol or reaction SMARTS |
| Forgot `Chem.SanitizeMol` after RWMol | Valence errors downstream | `Chem.SanitizeMol(mol)` before `MolToSmiles` |
| Multiple SMARTS matches, edited first silently | Wrong position edited | Print `GetSubstructMatches(patt)`; choose explicitly |
| Stereo lost after edit | `@` / `@@` dropped | `Chem.AssignStereochemistry(mol, cleanIt=True, force=True)` |
| Implicit H count wrong | Atom is a radical or wrong degree | `atom.UpdatePropertyCache()` after manual bond changes |
| Ambiguous "move" silently reinterpreted | Plausible but not the intended structure | Valence check first; ask user if impossible |
| PG SMARTS too permissive | Removes the wrong group (e.g., Boc SMARTS hitting a pivaloyl ester) | Use the precise patterns in `references/protecting-groups.md` |

## Red flags — STOP and re-examine

- Instruction implies impossible valence → ask the user
- SMARTS matches > 1 atom, edit applied to first → require explicit choice
- Canonical output SMILES identical to input → edit did nothing
- Formula delta doesn't match the expected edit
- RDKit parse returns `None` after edit → sanitization failed; check explicit H counts

## Reference material

- **references/edit-recipes.md** — cookbook of NL patterns → tested RDKit code. Copy-adapt.
- **references/protecting-groups.md** — SMARTS library for Boc, Cbz, Fmoc, TMS, TBS, TBDPS, TIPS, Bn, PMB, Tr, Ac, Bz, Piv, Ts, Ms, THP, MOM, BOM — install and remove.
- **references/atom-targeting.md** — full NL → SMARTS vocabulary, disambiguation techniques.

## Related skills

- **authoring-smiles** — write SMILES from scratch from a paper figure
- **rdkit** — full RDKit API reference (descriptors, similarity, 3D)
- **datamol** — simpler RDKit wrapper for standard workflows
- **pubchem-api** — fetch existing SMILES for named compounds
