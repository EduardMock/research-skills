# Worked Examples — Paper to SMILES

Three detailed walkthroughs showing the full thought process from a paper description to a final verified SMILES. Load when you want a model for how to reason through an unfamiliar structure.

---

## Example 1: IMes (an NHC ligand)

**Paper description:** 1,3-bis(2,4,6-trimethylphenyl)imidazol-2-ylidene. Two mesityl groups on N1 and N3 of an imidazol-2-ylidene. The ring has N1−C2(carbene)−N3−C4=C5 (closing back to N1).

### Step 1: identify the scaffold

- Core = imidazol-2-ylidene (5-membered ring: N, [C] carbene, N, C=C)
- Two substituents = mesityl = 2,4,6-trimethylphenyl

### Step 2: build the mesityl fragment

Mesityl = benzene with Me at positions 2, 4, 6 (1,3,5-substitution counting from the attachment).

Start at position 1 (attachment to the rest of the molecule):
- Position 1: `c1` (attached externally)
- Position 2: `c(C)` (Me)
- Position 3: `c`
- Position 4: `c(C)` (Me)
- Position 5: `c`
- Position 6: `c1C` (Me, closes ring)

Mesityl fragment: `c1c(C)cc(C)cc1C` — the attaching carbon is the first `c`.

Alternatively, using a 2,4,6-pattern where the external atom attaches at the last `c`: `Cc1cc(C)cc(C)c1`. Both valid — pick whichever reads better in context.

### Step 3: build the imidazol-2-ylidene ring

Atoms: N1 − C2(carbene) − N3 − C4 = C5 − (back to N1)

With one mesityl (Ar) on each N:
- `N(Ar)` for N1
- `[C]` for C2 carbene — **divalent, not `C`**
- `N(Ar')` for N3
- `C=C` for C4=C5
- Close ring back to N1

Ring as SMILES: `N1([C]N(Ar')C=C1)Ar` — but this isn't the cleanest traversal. Better: start on the imidazole ring and walk around.

Pick a canonical traversal: N1 → C2 → N3 → C4 → C5 → N1. Written with ring-close digit `2` (we'll use `1` for the outer mesityl):
- N1: `N2(Ar)`
- C2: `[C]2` — this would close the ring, but we haven't visited N3/C4/C5 yet

So instead walk: N1 → C5 → C4 → N3 → C2 → close to N1:
- `N2(Ar)C=CN(Ar')[C]2`

where the ring closure `2` goes from N1 (opened) to C2 (closed).

### Step 4: compose

Put it all together — outer mesityl on N1, inner mesityl on N3:

```
Cc1cc(C)c(N2C=CN(c3c(C)cc(C)cc3C)[C]2)c(C)c1
```

Breakdown of the final string:
- `Cc1cc(C)c(...)c(C)c1` — outer mesityl attached at position 1 to the imidazole N
- `N2C=CN(...)[C]2` — imidazol-2-ylidene ring (ring digit 2)
- Inside the inner `N(...)`: `c3c(C)cc(C)cc3C` — second mesityl (ring digit 3)

### Step 5: verify

```python
from rdkit import Chem
from rdkit.Chem import Draw, rdMolDescriptors

smi = "Cc1cc(C)c(N2C=CN(c3c(C)cc(C)cc3C)[C]2)c(C)c1"
mol = Chem.MolFromSmiles(smi)
assert mol is not None
print(rdMolDescriptors.CalcMolFormula(mol))   # expect C21H24N2
# Verify the carbene
carbene = [a for a in mol.GetAtoms()
           if a.GetSymbol() == 'C' and a.GetTotalNumHs() == 0
           and a.GetDegree() == 2 and a.GetFormalCharge() == 0]
assert len(carbene) == 1
Draw.MolToImage(mol, size=(500, 400))
```

---

## Example 2: Ethyl (E)-cinnamate — and why the (E) is dropped

**Paper description:** ethyl ester of (E)-cinnamic acid. Structure: PhCH=CH-C(=O)-OEt, E geometry at the C=C.

The paper draws an (E) double bond, but **we do not encode it.** Stereo markers (`/`, `\`, `@`) break downstream structure handling, so the output is a flat skeleton — the (E) geometry is recovered by the 3D build, not carried in the string.

### Step 1: scaffold

Three pieces: phenyl − vinyl − ester (CO₂Et).

### Step 2: choose starting atom

Two natural starts:
- From the phenyl: reads as "phenyl, vinyl, ester"
- From the ester: reads as "ethyl ester of cinnamic acid"

Either works. Let's write from the ester end (reads as "ethyl ester of cinnamic acid"), which places the phenyl at the end of the string.

### Step 3: traversal

Monosubstituted benzene has no positional distinction — `Xc1ccccc1` and `c1ccc(X)cc1` both describe phenyl-X. Both parse to the same molecule. Pick whichever traversal reads better for the surrounding context.

### Step 4: the double bond — plain `C=C`, no slashes

The C=C is written as a bare double bond. Do **not** add `/C=C/` (E) or `/C=C\` (Z) — geometry is omitted by policy.

### Step 5: compose

```
CCOC(=O)C=Cc1ccccc1
```

Reads naturally: ethyl-O-carbonyl-vinyl-phenyl.

### Step 6: verify

```python
smi = "CCOC(=O)C=Cc1ccccc1"
mol = Chem.MolFromSmiles(smi)
print(rdMolDescriptors.CalcMolFormula(mol))            # C11H12O2
# Guard: the SMILES must be flat — no stereo markers
assert "/" not in smi and "\\" not in smi and "@" not in smi
print(Chem.MolToSmiles(mol, isomericSmiles=False))     # flat canonical form
```

---

## Example 3: 2,6-Diisopropylaniline

**Paper description:** aniline (aminobenzene) with isopropyl groups at positions 2 and 6 (both ortho to the amine).

### Step 1: scaffold

Benzene + NH₂ + 2 × iPr at the ortho positions to NH₂.

### Step 2: starting atom

Standard convention: start at the NH₂-bearing carbon (position 1).

### Step 3: traversal around the ring

Positions: 1 (C-NH₂), 2 (C-iPr), 3, 4, 5, 6 (C-iPr).

Walk around in one direction:
- Pos 1: `Nc1` — N attached, open ring
- Pos 2: `c(C(C)C)` — iPr branch
- Pos 3: `c`
- Pos 4: `c`
- Pos 5: `c`
- Pos 6: `c1C(C)C` — iPr substituent, close ring

Combined: `Nc1c(C(C)C)cccc1C(C)C`

### Step 4: check the count

Six ring atoms: `c1`, `c(C(C)C)`, `c`, `c`, `c`, `c1` → yes, six. ✓
Substituents: NH₂ at pos 1, iPr at pos 2 and pos 6. ✓ (symmetric 2,6-pattern — the molecule has C₂ᵥ symmetry.)

### Step 5: verify

```python
smi = "Nc1c(C(C)C)cccc1C(C)C"
mol = Chem.MolFromSmiles(smi)
print(rdMolDescriptors.CalcMolFormula(mol))   # C12H19N
print(Chem.MolToSmiles(mol))                    # canonical form
```

---

## Pattern summary across all three

| Step | What you do | Why |
|---|---|---|
| 1 | Decompose into scaffold pieces (rings, chains, functional groups) | Reduces the problem to fragments you already know |
| 2 | Choose the starting atom by readability convention | Different chemists should still produce similar strings |
| 3 | Traverse each ring in one direction, emit `c` or `c(X)` | Mechanical, error-resistant |
| 4 | Add stereochemistry last | Easy to verify on a complete skeleton |
| 5 | Parse + visualize + canonicalize | Evidence that intent matches reality |

Any SMILES you author goes through steps 1→5. Skipping step 5 is the most common cause of subtle errors shipped to downstream pipelines.
