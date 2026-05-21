# Edit Recipes — NL → RDKit Code

Copy-adapt cookbook. Every recipe is a complete function; the NL pattern it targets is in the docstring. All recipes end with canonical SMILES output after sanitization.

## Preamble for every recipe

```python
from rdkit import Chem
from rdkit.Chem import AllChem, Draw, rdMolDescriptors

def _finalize(rwmol):
    """Sanitize + canonical SMILES."""
    mol = rwmol.GetMol() if isinstance(rwmol, Chem.RWMol) else rwmol
    Chem.SanitizeMol(mol)
    return Chem.MolToSmiles(mol)
```

## 1 — Add a single atom (OH, F, Cl, …) at a SMARTS-matched atom

```python
def add_atom_at(smi: str, target_smarts: str, atom_symbol: str, bond=Chem.BondType.SINGLE) -> str:
    """
    Add a single atom (e.g., 'O' for OH, 'F' for fluorine) at the first atom
    matching target_smarts. Target atom must have at least one implicit H.

    Example:
      "Add OH to the alpha carbon of the ketone"
      add_atom_at("c1ccc(CC(=O)C)cc1", "[CX4;H2]C(=O)", "O")
      → 'CC(=O)C(O)c1ccccc1'
    """
    rw = Chem.RWMol(Chem.MolFromSmiles(smi))
    patt = Chem.MolFromSmarts(target_smarts)
    matches = rw.GetSubstructMatches(patt)
    if not matches:
        raise ValueError(f"no match for {target_smarts} in {smi}")
    if len(matches) > 1:
        print(f"warning: {len(matches)} matches for {target_smarts}; using first at atoms {matches[0]}")
    target_idx = matches[0][0]
    target = rw.GetAtomWithIdx(target_idx)
    if target.GetTotalNumHs() == 0:
        raise ValueError(f"atom {target_idx} ({target.GetSymbol()}) has no H — can't add substituent")
    new_idx = rw.AddAtom(Chem.Atom(atom_symbol))
    rw.AddBond(target_idx, new_idx, bond)
    return _finalize(rw)
```

## 2 — Add a multi-atom group (CF₃, Me, Ph, CN) at a matched atom

```python
def add_group_at(smi: str, target_smarts: str, group_smi: str) -> str:
    """
    Attach a group (given as SMILES) to the first matched atom.

    Example:
      "Replace H on the alpha C with CF3"
      add_group_at("CC(=O)C", "[CH3]", "C(F)(F)F")
      → 'O=C(C)CC(F)(F)F' (alpha-CF3 acetone)
    """
    mol = Chem.MolFromSmiles(smi)
    patt = Chem.MolFromSmarts(target_smarts)
    matches = mol.GetSubstructMatches(patt)
    if not matches:
        raise ValueError(f"no match for {target_smarts}")
    target_idx = matches[0][0]

    group = Chem.MolFromSmiles(group_smi)
    combined = Chem.CombineMols(mol, group)
    rw = Chem.RWMol(combined)
    # the group's first atom sits at mol.GetNumAtoms()
    group_attach_idx = mol.GetNumAtoms()
    rw.AddBond(target_idx, group_attach_idx, Chem.BondType.SINGLE)
    # the matched atom loses one implicit H automatically when we add a bond + sanitize
    return _finalize(rw)
```

## 3 — Remove a single leaf atom (H is implicit; halogens, OH, NH₂, …)

```python
def remove_leaf(smi: str, leaf_smarts: str) -> str:
    """
    Remove an atom that has exactly one heavy-atom neighbour, matched via SMARTS.
    Useful for: 'remove the hydroxyl', 'remove the fluorine', 'remove the methyl'.

    Example:
      "Remove the hydroxyl" from PhCH(OH)CH3 (1-phenylethanol)
      remove_leaf("c1ccc(C(O)C)cc1", "[OX2H1]")
      → 'CCc1ccccc1' (ethylbenzene)
    """
    rw = Chem.RWMol(Chem.MolFromSmiles(smi))
    patt = Chem.MolFromSmarts(leaf_smarts)
    matches = rw.GetSubstructMatches(patt)
    if not matches:
        raise ValueError(f"no match for {leaf_smarts}")
    leaf_idx = matches[0][0]
    leaf = rw.GetAtomWithIdx(leaf_idx)
    if leaf.GetDegree() != 1:
        raise ValueError(f"atom {leaf_idx} has degree {leaf.GetDegree()}; not a leaf")
    rw.RemoveAtom(leaf_idx)
    return _finalize(rw)
```

For groups larger than one atom (CH₃, Ph, CO₂Me, …) use `remove_group_via_reaction` below.

## 4 — Remove a multi-atom group via reaction SMARTS

```python
def remove_group_via_reaction(smi: str, rxn_smarts: str) -> str:
    """
    Generic removal via a reaction SMARTS of the form:
        [*:1][GROUP_ATOMS] >> [*:1][H]
    The '[*:1]' anchors the atom that stays; the group atoms after it are deleted
    and replaced with H on the anchor.

    Example:
      "Remove the methyl ester, leave the free acid"
      remove_group_via_reaction(
          "CC(=O)OC",
          "[C:1](=O)OC>>[C:1](=O)O"
      )
      → 'CC(=O)O' (acetic acid)
    """
    rxn = AllChem.ReactionFromSmarts(rxn_smarts)
    mol = Chem.MolFromSmiles(smi)
    products = rxn.RunReactants((mol,))
    if not products:
        raise ValueError(f"reaction didn't match in {smi}")
    prod = products[0][0]
    Chem.SanitizeMol(prod)
    return Chem.MolToSmiles(prod)
```

## 5 — Replace group X with group Y

```python
def replace_group(smi: str, old_smarts: str, new_smi: str) -> str:
    """
    Swap a matched substructure for a new one. Uses ReplaceSubstructs.

    Example:
      "Replace the methyl with CF3"
      replace_group("CC(=O)Nc1ccccc1", "[CH3]C(=O)", "C(F)(F)FC(=O)")
      → trifluoroacetanilide
    """
    mol = Chem.MolFromSmiles(smi)
    patt = Chem.MolFromSmarts(old_smarts)
    repl = Chem.MolFromSmiles(new_smi)
    new_mols = Chem.ReplaceSubstructs(mol, patt, repl, replaceAll=False)
    if not new_mols:
        raise ValueError(f"no substructure match for {old_smarts}")
    prod = new_mols[0]
    Chem.SanitizeMol(prod)
    return Chem.MolToSmiles(prod)
```

**Note:** `ReplaceSubstructs` loses atom mapping — the replacement attaches at the first atom of `repl`. For fine control over which atom of the replacement anchors, use a reaction SMARTS with explicit mapping numbers.

## 6 — Relocate a group from atom A to atom B

```python
def relocate_group(smi: str, source_smarts: str, group_smarts: str, target_smarts: str) -> str:
    """
    Two-step move:
      1. remove group from source atom (gets H back)
      2. attach same group to target atom (loses an H)

    For single-atom leaves (OH, F, Me), prefer chaining recipe #3 (`remove_leaf`)
    + recipe #1 (`add_atom_at`) — simpler and lets you target source and destination
    with narrow SMARTS each.

    This recipe #6 is for multi-atom groups (benzyl, CF3, Ph, acyl, ...).

    Example:
      "Move the benzyl group from the quaternary C to the alpha C of the ketone"
      Input: `CC(=O)C(C)(Cc1ccccc1)CC`  (1-benzyl-1-methyl-2-butanone pattern)
      Source = the quaternary C: `[CX4;H0]`
      Target = the alpha C of C=O: `[CX4;H2,CX4;H3]C(=O)` (methyl or methylene alpha)
      Group = benzyl: `[CH2]c1ccccc1`
    """
    rw = Chem.RWMol(Chem.MolFromSmiles(smi))

    # Step 1: locate source and group
    src_patt = Chem.MolFromSmarts(source_smarts)
    grp_patt = Chem.MolFromSmarts(group_smarts)
    src_matches = rw.GetSubstructMatches(src_patt)
    grp_matches = rw.GetSubstructMatches(grp_patt)
    if not src_matches or not grp_matches:
        raise ValueError("source or group pattern didn't match")

    src_idx = src_matches[0][0]
    # find the group whose first atom is bonded to the source
    chosen_group = None
    for g in grp_matches:
        if rw.GetBondBetweenAtoms(src_idx, g[0]) is not None:
            chosen_group = g
            break
    if chosen_group is None:
        raise ValueError("group is not directly bonded to source atom")

    # Step 2: break the bond source → group_root
    group_root = chosen_group[0]
    rw.RemoveBond(src_idx, group_root)

    # Step 3: locate target atom, bond group_root to it
    tgt_patt = Chem.MolFromSmarts(target_smarts)
    tgt_matches = rw.GetSubstructMatches(tgt_patt)
    # filter out matches that overlap with the group we just detached
    group_atom_set = set(chosen_group)
    tgt_matches = [m for m in tgt_matches if m[0] not in group_atom_set]
    if not tgt_matches:
        raise ValueError("no valid target atom after detaching group")
    tgt_idx = tgt_matches[0][0]

    rw.AddBond(tgt_idx, group_root, Chem.BondType.SINGLE)
    # Sanitize will re-count implicit Hs
    return _finalize(rw)
```

**Valence check before calling:** if `target` has zero implicit H *before* the move, the edit is not valence-consistent — stop and ask the user.

## 7 — Change bond order (single ↔ double ↔ triple)

```python
def change_bond(smi: str, bond_smarts: str, new_order: Chem.BondType) -> str:
    """
    Change the bond between two atoms identified by a 2-atom SMARTS match.

    Example:
      "Change the C-C single bond of ethane to a double bond"
      change_bond("CC", "[CH3][CH3]", Chem.BondType.DOUBLE)  # → ethylene
    """
    rw = Chem.RWMol(Chem.MolFromSmiles(smi))
    patt = Chem.MolFromSmarts(bond_smarts)
    matches = rw.GetSubstructMatches(patt)
    if not matches:
        raise ValueError(f"no match for {bond_smarts}")
    a, b = matches[0][0], matches[0][1]
    bond = rw.GetBondBetweenAtoms(a, b)
    bond.SetBondType(new_order)
    return _finalize(rw)
```

## 8 — Invert stereo at a specific atom

```python
def invert_stereo_at(smi: str, atom_smarts: str) -> str:
    """
    Flip @ ↔ @@ at the first atom matching atom_smarts.

    Example:
      "Flip the stereo of the alpha carbon of alanine"
      invert_stereo_at("N[C@@H](C)C(=O)O", "[C@@H]")
      → 'N[C@H](C)C(=O)O' (D → L alanine)
    """
    rw = Chem.RWMol(Chem.MolFromSmiles(smi))
    patt = Chem.MolFromSmarts(atom_smarts)
    matches = rw.GetSubstructMatches(patt, useChirality=False)
    if not matches:
        raise ValueError(f"no match for {atom_smarts}")
    atom = rw.GetAtomWithIdx(matches[0][0])
    atom.InvertChirality()
    Chem.AssignStereochemistry(rw, cleanIt=True, force=True)
    return _finalize(rw)
```

## 9 — Functionalize a ring atom identified by ring membership

```python
def functionalize_ring_atom(smi: str, ring_smarts: str, atom_role_smarts: str, group_smi: str) -> str:
    """
    Add `group_smi` to an atom that simultaneously matches `ring_smarts` (the ring as a whole)
    and `atom_role_smarts` (the specific atom within that ring).

    Example:
      "Add OH to the C alpha to the O in the pyrone ring"
      functionalize_ring_atom(
          "O=c1occc2c1CCCC2",
          ring_smarts="O=c1occc[c,C]1",       # the 2H-pyran-2-one ring
          atom_role_smarts="[c;r6][o;r6]",     # ring C adjacent to ring O
          group_smi="O"
      )
      → 'O=c1oc(O)cc2c1CCCC2'
    """
    mol = Chem.MolFromSmiles(smi)
    ring_patt = Chem.MolFromSmarts(ring_smarts)
    role_patt = Chem.MolFromSmarts(atom_role_smarts)

    ring_matches = mol.GetSubstructMatch(ring_patt)
    if not ring_matches:
        raise ValueError("ring pattern didn't match")
    ring_set = set(ring_matches)

    role_matches = mol.GetSubstructMatches(role_patt)
    # take the first role atom that is (a) inside the ring AND (b) has an implicit H
    # available for substitution. The H check prevents silently picking the carbonyl
    # C (which has no H) when the instruction wants a ring C with replaceable H.
    chosen = next(
        (m[0] for m in role_matches
         if m[0] in ring_set
         and mol.GetAtomWithIdx(m[0]).GetTotalNumHs() > 0),
        None
    )
    if chosen is None:
        raise ValueError(
            "no atom satisfies all three conditions: inside ring, matches role, "
            "has an implicit H. Relax the role SMARTS or pick manually."
        )

    # add the group via add_group_at-style logic
    rw = Chem.RWMol(Chem.CombineMols(mol, Chem.MolFromSmiles(group_smi)))
    rw.AddBond(chosen, mol.GetNumAtoms(), Chem.BondType.SINGLE)
    return _finalize(rw)
```

## 10 — Batch apply the same edit to many SMILES

```python
def batch_edit(smiles_list, edit_fn, **kwargs):
    """
    Apply edit_fn to every SMILES; collect (input, output, error) tuples.
    """
    results = []
    for smi in smiles_list:
        try:
            out = edit_fn(smi, **kwargs)
            results.append((smi, out, None))
        except Exception as e:
            results.append((smi, None, str(e)))
    return results

# Example: deprotect a whole library
batch_edit(
    ["CC(C)(C)OC(=O)N1CCC(c2ccccc2)CC1", "CC(C)(C)OC(=O)NCCC"],
    remove_group_via_reaction,
    rxn_smarts="[*:1][N:2]C(=O)OC(C)(C)C>>[*:1][NH:2]"
)
```

## Decision shortcut

```
Is the edit a pattern A → B that applies wherever A occurs?
├── yes → reaction SMARTS (recipe 4, 5)
└── no, it needs atom indices I'll pick explicitly
    ├── simple atom-level ops → RWMol (recipes 1, 3, 7, 8)
    └── multi-atom group ops → RWMol + CombineMols (recipes 2, 6, 9)
```

## Verification scaffold (paste after any edit)

```python
def verify_edit(smi_in, smi_out, expected_formula_delta=None):
    mol_in = Chem.MolFromSmiles(smi_in)
    mol_out = Chem.MolFromSmiles(smi_out)
    assert mol_out is not None, "output failed to parse"
    n_in = mol_in.GetNumHeavyAtoms()
    n_out = mol_out.GetNumHeavyAtoms()
    f_in = rdMolDescriptors.CalcMolFormula(mol_in)
    f_out = rdMolDescriptors.CalcMolFormula(mol_out)
    print(f"{smi_in}  →  {smi_out}")
    print(f"heavy atoms {n_in} → {n_out} (Δ = {n_out - n_in:+d})")
    print(f"formula {f_in} → {f_out}")
    if smi_in == smi_out:
        print("WARNING: no change")
    return mol_in, mol_out
```
