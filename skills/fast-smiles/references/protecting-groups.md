# Protecting-Group SMARTS Library

Ready-to-use reaction SMARTS for installing and removing common protecting groups. Each entry:

- **Structure** — the PG as attached to the substrate
- **Remove** — reaction SMARTS that strips the PG, leaving H on the anchor atom
- **Install** — reaction SMARTS that adds the PG to a free X-H (amine, alcohol, acid, …)
- **Verification** — expected formula delta (heavy atoms)

Use with `AllChem.ReactionFromSmarts(...)` + `RunReactants((mol,))`. See `edit-recipes.md` recipe #4.

## Amine protecting groups

### Boc (tert-butoxycarbonyl)

```
Structure:    R-NH-C(=O)-O-C(CH3)3
Remove:       [*:1][N:2]C(=O)OC(C)(C)C>>[*:1][NH:2]
Install:      [*:1][NH:2]>>[*:1][N:2]C(=O)OC(C)(C)C
Δ (remove):   −7 heavy atoms (5 C + 2 O removed; net −C₅H₈O₂)
```

```python
# Example: deprotect N-Boc-piperidine
from rdkit.Chem import AllChem
rxn = AllChem.ReactionFromSmarts("[*:1][N:2]C(=O)OC(C)(C)C>>[*:1][NH:2]")
rxn.RunReactants((Chem.MolFromSmiles("CC(C)(C)OC(=O)N1CCCCC1"),))[0][0]
# → piperidine
```

### Cbz / Z (benzyloxycarbonyl)

```
Structure:    R-NH-C(=O)-O-CH2-C6H5
Remove:       [*:1][N:2]C(=O)OCc1ccccc1>>[*:1][NH:2]
Install:      [*:1][NH:2]>>[*:1][N:2]C(=O)OCc1ccccc1
Δ (remove):   −9 heavy atoms (−C₈H₇O₂)
```

### Fmoc (9-fluorenylmethyloxycarbonyl)

```
Structure:    R-NH-C(=O)-O-CH2-C9H9
Remove:       [*:1][N:2]C(=O)OCC3c4ccccc4-c4ccccc43>>[*:1][NH:2]
Install:      [*:1][NH:2]>>[*:1][N:2]C(=O)OCC3c4ccccc4-c4ccccc43
Δ (remove):   −17 heavy atoms
```

### Acetyl (Ac) — on amines or alcohols

```
Structure (amide):  R-NH-C(=O)-CH3
Remove:       [*:1][N:2]C(=O)C>>[*:1][NH:2]
Install:      [*:1][NH:2]>>[*:1][N:2]C(=O)C
Δ (remove):   −3 heavy atoms (−C₂H₂O)
```

### Trifluoroacetyl (TFA)

```
Structure:    R-NH-C(=O)-CF3
Remove:       [*:1][N:2]C(=O)C(F)(F)F>>[*:1][NH:2]
Δ (remove):   −6 heavy atoms (2 C + 1 O + 3 F)
```

## Alcohol protecting groups (silyl ethers)

### TMS (trimethylsilyl)

```
Structure:    R-O-Si(CH3)3
Remove:       [*:1][O:2][Si](C)(C)C>>[*:1][OH:2]
Install:      [*:1][OH:2]>>[*:1][O:2][Si](C)(C)C
Δ (remove):   −4 heavy atoms
```

### TES (triethylsilyl)

```
Remove:       [*:1][O:2][Si](CC)(CC)CC>>[*:1][OH:2]
Δ (remove):   −7 heavy atoms
```

### TBS / TBDMS (tert-butyldimethylsilyl)

```
Structure:    R-O-Si(CH3)2-C(CH3)3
Remove:       [*:1][O:2][Si](C)(C)C(C)(C)C>>[*:1][OH:2]
Install:      [*:1][OH:2]>>[*:1][O:2][Si](C)(C)C(C)(C)C
Δ (remove):   −7 heavy atoms (−C₆H₁₄Si)
```

### TBDPS (tert-butyldiphenylsilyl)

```
Remove:       [*:1][O:2][Si](c1ccccc1)(c1ccccc1)C(C)(C)C>>[*:1][OH:2]
Δ (remove):   −17 heavy atoms
```

### TIPS (triisopropylsilyl)

```
Remove:       [*:1][O:2][Si](C(C)C)(C(C)C)C(C)C>>[*:1][OH:2]
Δ (remove):   −10 heavy atoms
```

## Alcohol protecting groups (ethers and esters)

### Benzyl ether (Bn)

```
Structure:    R-O-CH2-C6H5
Remove:       [*:1][O:2]Cc1ccccc1>>[*:1][OH:2]
Install:      [*:1][OH:2]>>[*:1][O:2]Cc1ccccc1
Δ (remove):   −7 heavy atoms (−C₇H₇, leaves H)
```

### PMB / MPM (p-methoxybenzyl)

```
Structure:    R-O-CH2-C6H4-OMe
Remove:       [*:1][O:2]Cc1ccc(OC)cc1>>[*:1][OH:2]
Δ (remove):   −9 heavy atoms
```

### Trityl (Tr, triphenylmethyl)

```
Structure:    R-O-C(C6H5)3
Remove:       [*:1][O:2]C(c1ccccc1)(c1ccccc1)c1ccccc1>>[*:1][OH:2]
Δ (remove):   −19 heavy atoms
```

### Acetate (Ac, on an alcohol)

```
Structure:    R-O-C(=O)-CH3
Remove:       [*:1][O:2]C(=O)C>>[*:1][OH:2]
Install:      [*:1][OH:2]>>[*:1][O:2]C(=O)C
Δ (remove):   −3 heavy atoms
```

### Benzoate (Bz)

```
Structure:    R-O-C(=O)-C6H5
Remove:       [*:1][O:2]C(=O)c1ccccc1>>[*:1][OH:2]
Δ (remove):   −8 heavy atoms
```

### Pivaloate (Piv)

```
Structure:    R-O-C(=O)-C(CH3)3
Remove:       [*:1][O:2]C(=O)C(C)(C)C>>[*:1][OH:2]
Δ (remove):   −6 heavy atoms
```

## Acetal-based alcohol protecting groups

### THP (tetrahydropyranyl)

```
Structure:    R-O-[tetrahydropyran at 2-position]
Remove:       [*:1][O:2]C1OCCCC1>>[*:1][OH:2]
Install:      [*:1][OH:2]>>[*:1][O:2]C1OCCCC1
Δ (remove):   −6 heavy atoms
```

### MOM (methoxymethyl)

```
Structure:    R-O-CH2-O-CH3
Remove:       [*:1][O:2]COC>>[*:1][OH:2]
Δ (remove):   −3 heavy atoms
```

### MEM (2-methoxyethoxymethyl)

```
Structure:    R-O-CH2-O-CH2-CH2-O-CH3
Remove:       [*:1][O:2]COCCOC>>[*:1][OH:2]
Δ (remove):   −6 heavy atoms
```

### BOM (benzyloxymethyl)

```
Structure:    R-O-CH2-O-CH2-C6H5
Remove:       [*:1][O:2]COCc1ccccc1>>[*:1][OH:2]
Δ (remove):   −9 heavy atoms
```

### SEM (2-(trimethylsilyl)ethoxymethyl)

```
Structure:    R-O-CH2-O-CH2-CH2-Si(CH3)3
Remove:       [*:1][O:2]COCC[Si](C)(C)C>>[*:1][OH:2]
Δ (remove):   −8 heavy atoms
```

## Carboxylic acid protecting groups

### Methyl ester

```
Structure:    R-C(=O)-O-CH3
Remove:       [*:1]C(=O)[O:2]C>>[*:1]C(=O)[OH:2]
Install:      [*:1]C(=O)[OH:2]>>[*:1]C(=O)[O:2]C
Δ (remove):   −1 heavy atom (−CH₂)
```

### Ethyl ester

```
Remove:       [*:1]C(=O)[O:2]CC>>[*:1]C(=O)[OH:2]
Δ (remove):   −2 heavy atoms
```

### tert-Butyl ester

```
Remove:       [*:1]C(=O)[O:2]C(C)(C)C>>[*:1]C(=O)[OH:2]
Δ (remove):   −4 heavy atoms
```

### Benzyl ester

```
Remove:       [*:1]C(=O)[O:2]Cc1ccccc1>>[*:1]C(=O)[OH:2]
Δ (remove):   −7 heavy atoms
```

## Sulfonate protecting groups (for alcohols/amines)

### Tosyl (Ts, p-toluenesulfonyl) — on N or O

```
Structure:    R-X-S(=O)(=O)-C6H4-CH3
Remove:       [*:1][N,O:2]S(=O)(=O)c1ccc(C)cc1>>[*:1][NH,OH:2]
Δ (remove):   −10 heavy atoms (1 S + 2 O + 7 C)
```

### Mesyl (Ms, methanesulfonyl)

```
Structure:    R-X-S(=O)(=O)-CH3
Remove:       [*:1][N,O:2]S(=O)(=O)C>>[*:1][NH,OH:2]
Δ (remove):   −4 heavy atoms
```

### Nosyl (Ns, nitrobenzenesulfonyl)

```
Remove:       [*:1][N,O:2]S(=O)(=O)c1ccc([N+](=O)[O-])cc1>>[*:1][NH,OH:2]
Δ (remove):   −12 heavy atoms
```

## Unified deprotection helper

```python
from rdkit import Chem
from rdkit.Chem import AllChem

PG_REMOVE = {
    "Boc":   "[*:1][N:2]C(=O)OC(C)(C)C>>[*:1][NH:2]",
    "Cbz":   "[*:1][N:2]C(=O)OCc1ccccc1>>[*:1][NH:2]",
    "Fmoc":  "[*:1][N:2]C(=O)OCC3c4ccccc4-c4ccccc43>>[*:1][NH:2]",
    "Ac-N":  "[*:1][N:2]C(=O)C>>[*:1][NH:2]",
    "TFA":   "[*:1][N:2]C(=O)C(F)(F)F>>[*:1][NH:2]",
    "TMS":   "[*:1][O:2][Si](C)(C)C>>[*:1][OH:2]",
    "TES":   "[*:1][O:2][Si](CC)(CC)CC>>[*:1][OH:2]",
    "TBS":   "[*:1][O:2][Si](C)(C)C(C)(C)C>>[*:1][OH:2]",
    "TBDPS": "[*:1][O:2][Si](c1ccccc1)(c1ccccc1)C(C)(C)C>>[*:1][OH:2]",
    "TIPS":  "[*:1][O:2][Si](C(C)C)(C(C)C)C(C)C>>[*:1][OH:2]",
    "Bn":    "[*:1][O:2]Cc1ccccc1>>[*:1][OH:2]",
    "PMB":   "[*:1][O:2]Cc1ccc(OC)cc1>>[*:1][OH:2]",
    "Tr":    "[*:1][O:2]C(c1ccccc1)(c1ccccc1)c1ccccc1>>[*:1][OH:2]",
    "Ac-O":  "[*:1][O:2]C(=O)C>>[*:1][OH:2]",
    "Bz":    "[*:1][O:2]C(=O)c1ccccc1>>[*:1][OH:2]",
    "Piv":   "[*:1][O:2]C(=O)C(C)(C)C>>[*:1][OH:2]",
    "THP":   "[*:1][O:2]C1OCCCC1>>[*:1][OH:2]",
    "MOM":   "[*:1][O:2]COC>>[*:1][OH:2]",
    "MEM":   "[*:1][O:2]COCCOC>>[*:1][OH:2]",
    "BOM":   "[*:1][O:2]COCc1ccccc1>>[*:1][OH:2]",
    "SEM":   "[*:1][O:2]COCC[Si](C)(C)C>>[*:1][OH:2]",
    "Me-ester":  "[*:1]C(=O)[O:2]C>>[*:1]C(=O)[OH:2]",
    "Et-ester":  "[*:1]C(=O)[O:2]CC>>[*:1]C(=O)[OH:2]",
    "tBu-ester": "[*:1]C(=O)[O:2]C(C)(C)C>>[*:1]C(=O)[OH:2]",
    "Bn-ester":  "[*:1]C(=O)[O:2]Cc1ccccc1>>[*:1]C(=O)[OH:2]",
    "Ts":    "[*:1][N,O:2]S(=O)(=O)c1ccc(C)cc1>>[*:1][NH,OH:2]",
    "Ms":    "[*:1][N,O:2]S(=O)(=O)C>>[*:1][NH,OH:2]",
}

def deprotect(smi, pg_name):
    rxn = AllChem.ReactionFromSmarts(PG_REMOVE[pg_name])
    mol = Chem.MolFromSmiles(smi)
    prods = rxn.RunReactants((mol,))
    if not prods:
        raise ValueError(f"{pg_name} not found in {smi}")
    p = prods[0][0]
    Chem.SanitizeMol(p)
    return Chem.MolToSmiles(p)

# "Remove the Boc group"
deprotect("CC(C)(C)OC(=O)N1CCC(c2ccccc2)CC1", "Boc")
# → 'c1ccc(C2CCNCC2)cc1'
```

## Auto-detect which PG is present

```python
def detect_pgs(smi):
    """Return list of PG names that match the molecule."""
    mol = Chem.MolFromSmiles(smi)
    present = []
    for name, rxn_smarts in PG_REMOVE.items():
        # use the LHS pattern as a substructure query
        lhs_smarts = rxn_smarts.split(">>")[0]
        lhs = Chem.MolFromSmarts(lhs_smarts)
        if lhs and mol.HasSubstructMatch(lhs):
            present.append(name)
    return present

detect_pgs("CC(C)(C)OC(=O)N1CCC(O[Si](C)(C)C(C)(C)C)CC1")
# → ['Boc', 'TBS']
```

## Gotchas

1. **Boc-SMARTS can false-match pivaloyl amides** — the patterns distinguish by the `OC(C)(C)C` (Boc has the oxygen linker; pivaloyl is direct `C(=O)C(C)(C)C`). Check visually if in doubt.

2. **Acetyl on N vs. O are different** — two separate entries (`Ac-N` and `Ac-O`). Using the wrong one will either fail to match or match the wrong atom.

3. **Reaction SMARTS with `[N,O:2]` (SMARTS OR)** may not work in all RDKit versions. If `Ts` or `Ms` removal silently fails, split into two separate rxn SMARTS (one for N, one for O).

4. **Always sanitize after `RunReactants`** — products come out without a full sanitize pass.

5. **Deprotection is not "cleave any C-X bond"** — the reaction SMARTS enforces a specific PG skeleton. If the molecule has a close-but-different group (e.g., a t-butyl carbamate that's actually part of the substrate's backbone), it will still match. Run `detect_pgs` + visualize before ripping.
