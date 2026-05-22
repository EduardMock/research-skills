# Organometallic and Catalyst SMILES

Writing SMILES for catalysts, NHCs, phosphines and TM complexes has more traps than organic molecules. This reference covers the idioms that work for molSimplify (`mol3D.from_smiles`, `startgen_pythonic`, `-lig` flag) and survive an RDKit round-trip.

## NHC carbenes

**Rule: the carbene carbon is `[C]` — divalent, no H, no charge.** Writing plain `C` adds two implicit Hs and silently gives a CH₂.

### IMes (1,3-dimesitylimidazol-2-ylidene)

```
Cc1cc(C)c(N2C=CN(c3c(C)cc(C)cc3C)[C]2)c(C)c1
```

Walk-through:
- `Cc1cc(C)c(...)c(C)c1` — outer mesityl on one ring N
- `N2C=CN(Ar')[C]2` — imidazol-2-ylidene core (N−C=C−N with the carbene `[C]` closing the ring)
- `c3c(C)cc(C)cc3C` — inner mesityl on the other ring N

### IPr (1,3-bis(2,6-diisopropylphenyl)imidazol-2-ylidene)

```
CC(C)c1cccc(C(C)C)c1N1C=CN(c2c(C(C)C)cccc2C(C)C)[C]1
```

### SIMes, SIPr (saturated analogues)

Replace the imidazole `C=C` with `CC`:
```
Cc1cc(C)c(N2CCN(c3c(C)cc(C)cc3C)[C]2)c(C)c1      # SIMes
CC(C)c1cccc(C(C)C)c1N1CCN(c2c(C(C)C)cccc2C(C)C)[C]1  # SIPr
```

### CAAC (cyclic alkyl amino carbene, Bertrand)

CAACs have one N and one sp³ quaternary C flanking the carbene. Example CAAC (1-(2,6-diisopropylphenyl)-3,3-dimethyl-4-(2,4,6-trimethylphenyl)-pyrrolidin-2-ylidene):
```
CC(C)c1cccc(C(C)C)c1N1C(c2c(C)cc(C)cc2C)C(C)(C)[C]1
```

Encoding pattern: `ArN1-C(R1)(R2)-CR3R4-[C]1` where `[C]` is the carbene.

### Verification for NHCs

```python
mol = Chem.MolFromSmiles(smi)
carbene_c = [a for a in mol.GetAtoms() if a.GetSymbol() == 'C' and a.GetTotalNumHs() == 0 and a.GetDegree() == 2 and a.GetFormalCharge() == 0]
assert len(carbene_c) == 1, "expected exactly one divalent carbene C"
```

## Phosphines and phosphites

| Ligand | SMILES |
|---|---|
| PMe₃ | `P(C)(C)C` |
| PPh₃ | `P(c1ccccc1)(c1ccccc1)c1ccccc1` |
| PCy₃ | `P(C1CCCCC1)(C1CCCCC1)C1CCCCC1` |
| P(OMe)₃ | `P(OC)(OC)OC` |
| PtBu₃ | `P(C(C)(C)C)(C(C)(C)C)C(C)(C)C` |
| DPPE (1,2-bis(diphenylphosphino)ethane) | `P(c1ccccc1)(c1ccccc1)CCP(c2ccccc2)c2ccccc2` |
| BINAP core | `c1ccc2c(c1)ccc1ccccc12` (just the binaphthyl — add PPh₂ groups at the 2,2′ positions) |

Phosphines are trivalent in the neutral SMILES — implicit lone pair. Works with `mol3D.from_smiles` for docking.

## Metal centres

| Metal/ion | SMILES |
|---|---|
| Ni(0) | `[Ni]` |
| Ni(II) | `[Ni+2]` |
| Pd(0) | `[Pd]` |
| Pd(II) | `[Pd+2]` |
| Pt(II) | `[Pt+2]` |
| Ru(II) | `[Ru+2]` |
| Fe(II) | `[Fe+2]` |
| Fe(III) | `[Fe+3]` |
| Rh(I) | `[Rh+]` |
| Ir(I) / (III) | `[Ir+]` / `[Ir+3]` |
| Cu(I) / (II) | `[Cu+]` / `[Cu+2]` |
| Au(I) / (III) | `[Au+]` / `[Au+3]` |

**Charge convention:** write the formal oxidation state charge only if you want it to appear in the parsed structure. For neutral metal fragments with bound neutral donors, a 0-charge metal (`[Ni]`) usually works best with molSimplify's geometry-building.

## Dative bonds

SMILES has no native dative notation. Encode a dative bond as a **single bond**. The SMILES specification treats bonds as undirected; RDKit's valence-checking still passes for neutral donor atoms (phosphine P, amine N, carbene `[C]`, sulfide S, N-heterocyclic N, CO C).

```
# [Ni(CO)4]
[Ni](C#O)(C#O)(C#O)C#O

# [PdCl2(PPh3)2]
[Pd](Cl)(Cl)(P(c1ccccc1)(c1ccccc1)c1ccccc1)P(c1ccccc1)(c1ccccc1)c1ccccc1

# Ni(IMes)(CO)3 (simplified)
O=C[Ni](C=O)(C=O)[C]1N(c2c(C)cc(C)cc2C)C=CN1c1c(C)cc(C)cc1C
```

If RDKit complains about valence on the metal, try:
1. Adjusting metal charge to balance donor lone pairs (e.g., `[Ni+2]` with 2 X-type ligands, `[Ni]` with L-type donors only)
2. Setting `sanitize=False` on parsing, then running a partial sanitize

## Aromatic heterocycles coordinating to metals

Keep them lowercase (aromatic) even when bound.

```
# pyridine-Ni
n1ccccc1[Ni]

# 2,2'-bipyridine-Ni
c1ccc(-c2ccccn2)nc1[Ni]  # or use explicit [Ni] bonds to both Ns
```

## η-coordination / hapticity (η² alkene, η⁵ Cp, η⁶ arene)

SMILES cannot directly encode hapticity. Options:

1. **Leave SMILES as the unbound molecule** and let molSimplify (`-lig`, `-ligcon`) handle the coordination geometry. This is the recommended path.
2. For **η² alkene** on a metal, write bonds from both alkene carbons to the metal:
   ```
   # η²-ethene-Ni
   [Ni]1CC1   # three-membered ring with Ni and both C
   ```
3. For **Cp (η⁵-C₅H₅)** on Fe (ferrocene), some toolkits accept:
   ```
   [Fe+2].[cH-]1cccc1.[cH-]1cccc1  # two Cp anions + Fe(II)
   ```
   But this is a component-based encoding — each Cp is written as an anion, and molSimplify interprets coordination afterwards. RDKit parses it but does not infer hapticity.

## Grubbs / Hoveyda-Grubbs / Schrock / Wilkinson

Recommended path: use the **pubchem-api** skill to fetch canonical SMILES (e.g., Grubbs 1st gen CID 11571518, Grubbs 2nd gen CID 11647888, Hoveyda-Grubbs 2nd CID 11320810). Hand-authoring these is error-prone because they involve carbenes, phosphines, and specific M−C bond orders.

If you must author:

**Wilkinson's catalyst — RhCl(PPh₃)₃:**
```
[Rh](Cl)(P(c1ccccc1)(c1ccccc1)c1ccccc1)(P(c2ccccc2)(c2ccccc2)c2ccccc2)P(c3ccccc3)(c3ccccc3)c3ccccc3
```

**Grubbs 1st generation (Cl₂(PCy₃)₂Ru=CHPh):**
```
Cl[Ru](=Cc1ccccc1)(Cl)(P(C2CCCCC2)(C2CCCCC2)C2CCCCC2)P(C3CCCCC3)(C3CCCCC3)C3CCCCC3
```

**Known RDKit quirk:** when this parses, the phosphines canonicalize as `[PH]` (implicit H added to satisfy RDKit's P(V) valence model for dative-bond P→Ru). The structure is chemically correct — the `[PH]` is a parser artifact, not a real proton. If you need a clean canonical form without `[PH]`, either (a) strip explicit Hs on P with `Chem.RemoveHs(mol)` after parsing, or (b) use `Chem.MolFromSmiles(smi, sanitize=False)` + partial sanitize. For downstream molSimplify work, the `[PH]` form is harmless because `mol3D` re-infers coordination.

Round-trip with RDKit and visualize before using downstream — metal–ligand bond-order parsing is the most common failure mode.

## molSimplify-specific conventions

1. **Prefer `from_smiles` with `gen3d=True`** for small organic ligands. For TMCs, build the structure via `startgen_pythonic({'-core': ..., '-lig': ...})` rather than a giant SMILES.

2. **Ligand SMILES in compounds tables**: store the free (un-coordinated) ligand's canonical SMILES. The catalyst itself is assembled via `-lig`/`-ligcon`/`-core`.

3. **Donor atom index** (`-ligcon`): RDKit atom indices match `mol3D` indices after `mol3D.from_smiles` (see `exploration_notebook/ni_co2_diyne/01_reference_catalyst_build.ipynb`). Identify donors with:
   ```python
   rd = Chem.MolFromSmiles(smi)
   donor_idx = [a.GetIdx() for a in rd.GetAtoms()
                if a.GetSymbol() in {'N', 'P', 'O', 'S'} and a.GetTotalNumHs() == 0]
   ```
   For NHCs: the carbene `[C]` is always the donor; find it by `GetSymbol()=='C'` and `GetTotalNumHs()==0 and GetDegree()==2`.

4. **Pydentate fallback**: if you omit `-ligcon`, molSimplify's pydentate GNN predicts coordinating atoms. Trust it for common ligands (phosphines, NHCs, pyridines); verify manually for unusual donor patterns.

## Common catalyst-ligand fragments (attach at leftmost atom)

| Fragment | SMILES |
|---|---|
| Cp (cyclopentadienyl anion) | `[cH-]1cccc1` |
| Cp* (pentamethylcyclopentadienyl anion) | `Cc1c(C)c(C)c(C)[c-]1C` |
| Acac (acetylacetonate, enolate form) | `CC(=O)CC(C)=O` (neutral) or `CC(=O)[CH-]C(C)=O` (anion) |
| Salen (backbone, R = -OH with imines) | `Oc1ccccc1/C=N/CC/N=C/c1ccccc1O` |
| Triphos (tripod phosphine) | `P(CC[P](c1ccccc1)c1ccccc1)(CC[P](c1ccccc1)c1ccccc1)CC[P](c1ccccc1)c1ccccc1` |
| COD (1,5-cyclooctadiene) | `C1CC=CCCC=C1` |
| NBD (norbornadiene) | `C1CC2CC1C=C2` |
| BINAP scaffold | `c1ccc2c(c1)ccc1c2c(P(c2ccccc2)c2ccccc2)ccc1P(c1ccccc1)c1ccccc1` |

## Troubleshooting checklist

| Symptom | Cause | Fix |
|---|---|---|
| `MolFromSmiles` returns `None` on a metal complex | RDKit rejected the metal valence | Adjust metal charge; or use `sanitize=False` + `Chem.SanitizeMol(mol, sanitizeOps=...)` |
| NHC carbene is parsed as `[CH2]` | Wrote `C` instead of `[C]` | Replace with `[C]` inside the ring |
| Pyridine ring loses aromaticity after metal binding | Wrote Kekulé `N=CC=CC=C` | Use lowercase `n1ccccc1` |
| `mol3D.from_smiles` 3D embedding fails | openbabel can't build a conformer | Simplify: generate the free ligand first, coordinate via `-lig` afterwards |
| Wrong hapticity in assembled complex | SMILES lacks hapticity info | Don't encode in SMILES — use `-ligcon` indices in molSimplify |
