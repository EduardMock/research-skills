# Atom Targeting — NL → SMARTS

When a user says "the alpha carbon of the ketone" or "the carbon in the pyrone ring adjacent to the oxygen," convert the phrase to SMARTS, match it, and edit.

## Key SMARTS primitives

| Primitive | Meaning |
|---|---|
| `[C]` | aliphatic carbon |
| `[c]` | aromatic carbon |
| `[#6]` | any carbon (aliph or arom) |
| `[CX4]` | sp³ carbon (4 connections) |
| `[CX3]` | sp² carbon (3 connections) |
| `[CX2]` | sp carbon |
| `[CH0]` / `[CH1]` / `[CH2]` / `[CH3]` | carbon with 0/1/2/3 implicit H |
| `[R]` / `[R0]` | in a ring / not in a ring |
| `[r6]` | in a 6-membered ring |
| `[!R]` | not in a ring |
| `[C;H2]` | combined filters — sp3 carbon with 2 H |
| `[$(X)]` | recursive SMARTS — atom that is itself matchable by pattern X |

## Position relative to a functional group

### Alpha, beta, gamma to a carbonyl

"Alpha" = directly bonded. "Beta" = one atom away. "Gamma" = two atoms away.

| Phrase | SMARTS for the target atom (first atom in match) |
|---|---|
| alpha to ketone | `[CX4;!$(C=O)][CX3](=O)[#6]` |
| alpha to aldehyde | `[CX4;!$(C=O)][CX3H1](=O)` |
| alpha to carboxylic acid | `[CX4;!$(C=O)][CX3](=O)[OX2H1]` |
| alpha to ester (acyl side) | `[CX4;!$(C=O)][CX3](=O)O[CX4]` |
| alpha to ester (alkyl side, i.e. the alcohol C) | `[CX4][OX2]C(=O)[#6]` |
| alpha to amide (N side) | `[CX4][NX3]C(=O)[#6]` |
| beta to ketone | `[CX4][CX4][CX3](=O)[#6]` |

### Alpha to a ring heteroatom

| Phrase | SMARTS |
|---|---|
| alpha to ring O (any ring) | `[#6;R][O;R]` |
| alpha to ring N (any ring) | `[#6;R][N;R]` |
| alpha to ring S | `[#6;R][S;R]` |
| alpha to pyranone O | `[c,C;r6][o;r6]` (in a 6-ring with aromatic O) |

### Benzylic and allylic

| Phrase | SMARTS |
|---|---|
| benzylic C (sp3 C next to aromatic) | `[CX4][c]` |
| allylic C (sp3 C next to C=C) | `[CX4][CX3]=[CX3]` |
| propargylic C (sp3 C next to C≡C) | `[CX4][CX2]#[CX2]` |
| homobenzylic (one C removed) | `[CX4][CX4][c]` |

## Ring-specific targets

| Phrase | SMARTS |
|---|---|
| any atom in a 5-ring | `[*;r5]` |
| any atom in a 6-ring | `[*;r6]` |
| any aromatic atom | `[a]` |
| bridgehead (in ≥2 rings) | `[x2]` where `x` denotes ring-atom count |
| benzene ring C | `[cH1]` in `c1ccccc1` subpattern |
| pyridine N | `[n;r6]` (aromatic N in 6-ring) |
| pyridine alpha-C (ortho to N) | `[c;r6][n;r6]` |
| indole N-H | `[nH]` in `c1ccc2[nH]ccc2c1` |
| 2H-pyran-2-one (pyrone) ring atom | use `HasSubstructMatch(Chem.MolFromSmarts("O=c1occcc1"))` then list ring atoms |

### Targeting by role within a specific ring

Pattern: match the *whole ring* with SMARTS, then intersect with an atom-role pattern.

```python
from rdkit import Chem

mol = Chem.MolFromSmiles("O=c1occc2c1CCCC2")  # a fused pyrone
ring_patt = Chem.MolFromSmarts("O=c1occ[c,C][c,C]1")  # the pyran-2-one
ring_atoms = set(mol.GetSubstructMatch(ring_patt))

# "the ring C alpha to the ring O"
role_patt = Chem.MolFromSmarts("[c;r6][o;r6]")
role_matches = mol.GetSubstructMatches(role_patt)
target = next((m[0] for m in role_matches if m[0] in ring_atoms), None)
# target = atom idx for the ring C directly bonded to the ring oxygen
```

This "ring ∩ role" pattern is in `edit-recipes.md` as `functionalize_ring_atom`.

## Position relative to a specified group

The phrase "ortho / meta / para to X" on a benzene ring:

| Phrase | SMARTS |
|---|---|
| aromatic C ortho to NH₂ | `c([NH2])c` — the second `c` matches |
| aromatic C meta to NH₂ | `c([NH2])cc` — the last `c` matches |
| aromatic C para to NH₂ | `c([NH2])ccc` — the last `c` matches |
| aromatic C ortho to a generic group X | `c([$X])c` where `$X` is the X SMARTS |

## Disambiguation when multiple atoms match

SMARTS often matches more than one atom. Strategies:

### 1. Tighten the SMARTS

```python
# too-loose: matches every aromatic C
mol.GetSubstructMatches(Chem.MolFromSmarts("[c]"))

# tighter: aromatic C para to OH
mol.GetSubstructMatches(Chem.MolFromSmarts("c([OH1])ccc"))
# match tuple last atom is the para-C
```

### 2. Filter by a second criterion

```python
matches = mol.GetSubstructMatches(patt)
# keep only matches on ring-containing atoms
ring_matches = [m for m in matches if mol.GetAtomWithIdx(m[0]).IsInRing()]
```

### 3. Ask the user

If there are N valid matches and the instruction doesn't disambiguate:

```python
if len(matches) > 1:
    for i, m in enumerate(matches):
        a = mol.GetAtomWithIdx(m[0])
        print(f"match {i}: atom {m[0]} ({a.GetSymbol()}), ring={a.IsInRing()}, neighbors={[n.GetSymbol() for n in a.GetNeighbors()]}")
    raise ValueError("ambiguous target — specify which match")
```

### 4. Use atom-mapping numbers in a reaction SMARTS

When the edit is complex, a reaction SMARTS with `[C:1]`, `[O:2]` etc. forces explicit atom correspondence and eliminates ambiguity.

## Visualizing what SMARTS matched

Before committing to an edit, always highlight the matched atoms to confirm you've targeted the right position.

```python
from rdkit.Chem import Draw

patt = Chem.MolFromSmarts("[CX4;H2]C(=O)")
matches = mol.GetSubstructMatches(patt)
highlight = [a for m in matches for a in m]  # flatten all matched atoms
Draw.MolToImage(mol, size=(400, 300), highlightAtoms=highlight)
```

If the highlight covers atoms you didn't intend, tighten the SMARTS before editing.

## Common NL phrases and their SMARTS

| Natural language | SMARTS target (first atom in match) |
|---|---|
| the hydroxyl group | `[OX2H1]` |
| the primary amine | `[NX3H2][CX4]` |
| the secondary amine | `[NX3H1]([CX4])[CX4]` |
| the tertiary amine | `[NX3H0]([CX4])([CX4])[CX4]` |
| the aromatic NH | `[nH]` |
| the carbonyl carbon | `[CX3]=O` |
| the quaternary carbon | `[CX4H0]` |
| the tertiary carbon | `[CX4H1]` |
| the secondary carbon | `[CX4H2]` |
| the methyl group | `[CH3]` |
| the methylene (CH₂) | `[CH2]` |
| the vinyl C | `[CX3H1]=[CX3]` |
| the terminal alkyne C-H | `[CX2H1]#[CX2]` |
| the alpha-C of the imidazole | `[c;r5][n;r5][c;r5]` — middle C (between two N) |
| the ring junction (fused bicyclic) | `[*;R2]` — atom in two rings |

## Troubleshooting

| Problem | Likely cause | Fix |
|---|---|---|
| SMARTS returns `None` when parsed | Syntax error (e.g. aromatic `[c]` outside a ring) | Check `Chem.MolFromSmarts` output |
| No matches in an obviously matching molecule | Aromatic vs. aliphatic mismatch | Use `[#6]` for "any C" or explicitly add aromatic variants |
| Too many matches | SMARTS too loose | Add `;R`, `;!R`, `H2`, `X4` qualifiers |
| Match covers wrong atom of the pattern | SMARTS walks atoms in order; "first atom" is the leftmost | Reorder SMARTS or pick a different index in the match tuple |
| Match works on small mol, fails on larger one | Another functional group is being preferred | Use recursive SMARTS `[$(pattern)]` for context |
