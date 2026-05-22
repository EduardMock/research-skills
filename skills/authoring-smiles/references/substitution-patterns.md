# Substitution Pattern Idioms

Quick-lookup reference for turning substitution patterns from synthesis papers into readable SMILES. Start here when a paper shows a substituted aromatic core.

## Aromatic numbering convention in SMILES

When you write `c1ccccc1`, the six ring atoms appear in order:

```
position:  1  2  3  4  5  6
SMILES:    c1 c  c  c  c  c1
```

Position 1 is the one bearing the attachment to the rest of the molecule (the first `c` after a substituent, or the first ring atom in the string). Traverse in one direction and emit `c` (unsubstituted) or `c(R)` (substituted) at each position.

## Benzene substitution patterns

X, Y, Z are substituent SMILES fragments (e.g. `C`, `C(C)C`, `OC`, `[N+](=O)[O-]`). The first position is conventionally the one attached to the rest of the molecule (or the first substituent if standalone).

| Pattern | Skeleton | Notes |
|---|---|---|
| Mono (1) | `Xc1ccccc1` | Start at substituted carbon |
| 1,2 / ortho (2 subs) | `Xc1ccccc1Y` | Compact; fine for 2 subs |
| 1,2 / ortho (>2 subs) | `Xc1cccc(W)c1Y` | Use when more substituents follow |
| 1,3 / meta | `Xc1cccc(Y)c1` | Two positions apart |
| 1,4 / para | `Xc1ccc(Y)cc1` | Three positions apart |
| 2,6- (common on aniline/phenol X) | `Xc1c(Y)cccc1Z` | X usually NH₂/OH; Y,Z bulky ortho |
| 1,2,3- | `Xc1cccc(Z)c1Y` | |
| 1,3,5- / symmetrical | `Xc1cc(Y)cc(Z)c1` | Mesityl family, triazine cores |
| 2,4,6- (mesityl Y=Me) | `Cc1cc(C)cc(C)c1X` | Expands to the Mes fragment |
| 2,6- then 4 (Y=iPr, Z=Me) | `Cc1cc(C(C)C)c(X)c(C(C)C)c1` | "super-Mes" style |
| 1,2,4,5- | `Xc1cc(Y)c(Z)cc1W` | |
| 3,5-di-tert-butyl-4-Y (BHT-like) | `Xc1cc(C(C)(C)C)c(Y)c(C(C)(C)C)c1` | X at pos 1, Y at para; BHT itself: X=`C` (Me), Y=`O` (OH) |
| 2,6-di-tert-butyl-4-methylphenol (BHT) | `Oc1c(C(C)(C)C)cc(C)cc1C(C)(C)C` | phenol with two tBu ortho, Me para |
| Phenol with ortho substituents (2-X, 6-Y) | `Oc1c(X)cccc1Y` | phenol OH at pos 1; X, Y ortho |
| Phenol with 2,4,6 triple-subst | `Oc1c(X)cc(Z)cc1Y` | e.g. 2,4,6-trichlorophenol: `Oc1c(Cl)cc(Cl)cc1Cl` |

## Fused bicyclic aromatics

| System | SMILES |
|---|---|
| Naphthalene | `c1ccc2ccccc2c1` |
| Indole | `c1ccc2[nH]ccc2c1` |
| Quinoline | `c1ccc2ncccc2c1` |
| Benzimidazole | `c1ccc2[nH]cnc2c1` |
| Benzofuran | `c1ccc2occc2c1` |
| Benzothiophene | `c1ccc2sccc2c1` |

## Heteroaromatic five-membered rings

| Ring | SMILES | Substituted at N (if applicable) |
|---|---|---|
| Furan | `c1ccoc1` | — |
| Thiophene | `c1ccsc1` | — |
| Pyrrole | `c1cc[nH]c1` | N-Me: `Cn1cccc1` |
| Imidazole | `c1cnc[nH]1` | 1-Me: `Cn1ccnc1` |
| Oxazole | `c1ocnc1` | — |
| Thiazole | `c1scnc1` | — |
| Triazole (1,2,3-) | `c1cnn[nH]1` | 1-Me: `Cn1ccnn1` |

## Six-membered N-heterocycles

| Ring | SMILES |
|---|---|
| Pyridine | `c1ccncc1` |
| Pyrimidine | `c1cncnc1` |
| Pyrazine | `c1cnccn1` |
| Pyridazine | `c1ccnnc1` |
| Triazine (1,3,5-) | `c1ncncn1` |

## Common substituent fragments

Memorize these — they appear in nearly every ligand paper. Attach each at its leftmost atom.

| Name | Fragment | Notes |
|---|---|---|
| Methyl | `C` | |
| Ethyl | `CC` | |
| n-Propyl | `CCC` | |
| i-Propyl | `C(C)C` | |
| n-Butyl | `CCCC` | |
| i-Butyl | `CC(C)C` | |
| s-Butyl | `C(C)CC` | |
| t-Butyl | `C(C)(C)C` | |
| Cyclopropyl | `C1CC1` | |
| Cyclohexyl | `C1CCCCC1` | |
| Phenyl | `c1ccccc1` | |
| Benzyl (CH₂Ph) | `Cc1ccccc1` | |
| Phenethyl | `CCc1ccccc1` | |
| Mesityl (Mes, 2,4,6-Me₃-C₆H₂) | `c1c(C)cc(C)cc1C` | Attach at first `c` |
| 2,6-Diisopropylphenyl (Dipp) | `c1c(C(C)C)cccc1C(C)C` | Attach at first `c` |
| 3,5-bis(trifluoromethyl)phenyl | `c1cc(C(F)(F)F)cc(C(F)(F)F)c1` | Attach at first `c` |
| Pentafluorophenyl (C₆F₅) | `c1(F)c(F)c(F)c(F)c1F` | Attach at first `c` |
| Trimethylsilyl (TMS) | `[Si](C)(C)C` | |
| Triethylsilyl (TES) | `[Si](CC)(CC)CC` | |
| tert-Butyldimethylsilyl (TBS/TBDMS) | `[Si](C)(C)C(C)(C)C` | |
| Trifluoromethyl (-CF₃) | `C(F)(F)F` | |
| Difluoromethyl (-CF₂H) | `C(F)F` | |
| Methoxy (-OMe) | `OC` | |
| Ethoxy (-OEt) | `OCC` | |
| -CO₂Me | `C(=O)OC` | Carbonyl first; ester O after |
| -CO₂Et | `C(=O)OCC` | |
| -C(O)NHR | `C(=O)NR` | |
| -OC(O)Me (acetate ester) | `OC(C)=O` | |
| Nitro (-NO₂) | `[N+](=O)[O-]` | Charge-separated canonical form |
| Cyano (-CN) | `C#N` | |
| Sulfonate (-SO₃⁻) | `S(=O)(=O)[O-]` | |
| Sulfonyl methyl (-SO₂Me) | `S(=O)(=O)C` | |
| Sulfonamide (-SO₂NR₂) | `S(=O)(=O)NR` | |
| Phosphonate (-PO(OEt)₂) | `P(=O)(OCC)OCC` | |
| Azide (-N₃) | `N=[N+]=[N-]` | |
| Amidine (-C(=NR)NR₂) | `C(=NR)NR` | |

## Paper-to-SMILES recipe for a substituted aromatic

1. Locate position 1 in the paper (usually the attachment to the rest of the molecule, or the named substituent in the compound title).
2. Write `c1` for position 1. If the paper names X at position 1, prepend X and start: `Xc1`.
3. Traverse the ring in the direction that lets you emit substituted positions early (simpler subs first).
4. At each ring position emit `c` if unsubstituted, `c(R)` if substituted (`R` = the substituent fragment from the table above).
5. Close with `c1` on the final ring atom. Verify you wrote exactly six ring atoms for a six-membered ring.
6. If you got tangled, rotate the starting atom to the opposite substituted position and retry.

## Double-checking a substitution pattern

Count: for N subs on benzene, you should have exactly `6-N` bare `c` and `N` occurrences of `c(...)` (plus the leading substituted `c` if you started with a substituent attached). Pattern mismatches show up as off-by-one count errors.

## Worked pattern examples

**2,4,6-Trinitrotoluene (TNT)**  
Toluene with -NO₂ at 2, 4, 6.  
`Cc1c([N+](=O)[O-])cc([N+](=O)[O-])cc1[N+](=O)[O-]`

**4-Methylanisole (p-cresol methyl ether)**  
`COc1ccc(C)cc1` — para pattern, OMe first, Me at 4.

**3,5-Lutidine (3,5-dimethylpyridine)**  
`Cc1cnc(C)cc1` ❌ wrong — 3,5 on pyridine.  
`Cc1cc(C)cnc1` ✓ — 3,5-dimethylpyridine.  
(Check by counting ring atoms: 6 = c,c,c,c,n,c. N at position 5 in this traversal; Me at 3 and 1.)

**Sulfanilamide (4-aminobenzenesulfonamide)**  
`Nc1ccc(S(=O)(=O)N)cc1` — NH₂ at 1, SO₂NH₂ para at 4.

**Pyridoxine (Vitamin B6 aromatic core)**  
2-methyl, 3-hydroxy, 4-(CH₂OH), 5-(CH₂OH)-pyridine:  
`Cc1ncc(CO)c(CO)c1O`
