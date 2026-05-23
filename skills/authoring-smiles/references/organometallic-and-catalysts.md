# Organometallic and Catalyst SMILES

Writing SMILES for catalysts, NHCs, phosphines, amido/alkoxo complexes, η-complexes and TM intermediates has more traps than organic molecules. This reference codifies the patterns that work with **RDKit 2024.03+** (datives) and **2025.03+** (multidative haptic SMILES), and that round-trip through `mol3D.from_smiles` for molSimplify.

For the modern dative-bond API and the multidative/haptic interconversion functions, see also the upstream paper *Rasmussen, Strandgaard, Seumer, et al., "SMILES all around: structure-to-SMILES conversion for transition metal complexes", J. Cheminform. 17:63 (2025)* — currently the single most explicit conventions paper for RDKit-style OM SMILES. See `references/literature.md` for the full reading list and library landscape.

## The four foundational rules

1. **Default valence of a transition metal in RDKit is `-1`** — i.e. *no valence check*. All valence-rule conflicts live on the **ligand atom**, not the metal. So when authoring fails with "Explicit valence for atom #N is greater than permitted", the offending atom is almost never the metal itself.

2. **Use `->`/`<-` (OpenSMILES dative) for every L-type donor** (neutral lone-pair donor: amine, phosphine, NHC carbene, CO, ether, sulfide, η-arene). Use a normal single `-` bond for every X-type donor (anionic: halide, alkyl, aryl, amido, alkoxo, hydride). This is the convention chosen by Rasmussen 2025, used by stk, MACE, xyz2mol_tm.

3. **NHC carbenes are `[C]`** (divalent, no H, no charge). Writing `C` adds two implicit Hs and silently gives a CH₂.

4. **Aromatic donors stay lowercase even when bound to a metal.** `n1ccccc1[Ni]` not `N1=CC=CC=C1[Ni]`.

## A. Dative bonds — the modern RDKit-native syntax

Since RDKit 2018.09, `->` and `<-` are first-class SMILES tokens. The arrow points **donor → acceptor** (electrons flow from the donor's lone pair into the metal). Direction is symmetric: `[NH3]->[Ni]` and `[Ni]<-[NH3]` parse to the same molecule and canonicalize to donor-first form.

```python
from rdkit import Chem
m = Chem.MolFromSmiles('[NH3]->[Ni]')
# Bond type is Chem.BondType.DATIVE (verify via GetBondBetweenAtoms(...).GetBondType()).
# Ni's explicit valence count == 1 (RDKit's valence model counts datives just like other bonds).
# N keeps all 3 Hs because they are explicit inside the bracket.
```

**Why this matters:** RDKit's accounting still counts dative bonds toward the acceptor's *explicit valence number* — what dative actually buys you is preservation of **hydrogen counts** and **formal charges**:

| Input | Canonical output | Formula | What happened |
|---|---|---|---|
| `[NH3]->[Ni]` | `[NH3]->[Ni]` | H₃NNi | explicit ammine, all 3 Hs kept |
| `[NH3][Ni]` | `[NH3]->[Ni]` | H₃NNi | `cleanupOrganometallics` auto-rewrites to dative; 3 Hs kept |
| `[Ni]N` (organic N) | `[NH2][Ni]` | H₂NNi | **amido**: organic-subset N gets 2 implicit Hs, not 3 |
| `[Ni][NH2]` | `[NH2][Ni]` | H₂NNi | **amido**: 2 Hs explicit, stays as single bond |

So the **footgun is the unbracketed N**, not the missing dative arrow — outside brackets, organic-subset valence (3) gives you an amido instead of an ammine. Inside brackets `[NH3]` you get an ammine either way (RDKit's cleanup rescues a non-dative encoding). Always **bracket the donor** for unambiguous intent: `[NH3]` for ammine, `[NH2]` for amido.

### Controlling round-trip with `SmilesWriteParams`

`includeDativeBonds` is True by default since PR #7384 (2024.03.3). Toggle it off only when writing for legacy tools that choke on `->`:

```python
m = Chem.MolFromSmiles('[NH3]->[Ni]')
p = Chem.SmilesWriteParams()
p.includeDativeBonds = False
Chem.MolToSmiles(m, p)   # '[NH3][Ni]'  — datives downgraded to single bonds
```

### Donor type cheatsheet

| Donor class | Examples | Bond | Notes |
|---|---|---|---|
| L (neutral 2-e donor) | NR₃, PR₃, NHC `[C]`, CO, R₂O, R₂S, py | `->` | Use dative |
| X (anionic 1-e donor) | Cl⁻, OR⁻, NR₂⁻, R⁻, H⁻ | `-` | Use single |
| LX hybrid (η-allyl, Cp⁻) | allyl, Cp⁻ | mixed | See section E |

## B. Metal–heteroatom σ bonds (amido, alkoxo, halido, thiolato)

X-type ligands use a plain single bond. The ligand atom carries its conventional organic-subset valence; the metal does not.

| Motif | SMILES | Canonical form | Formula |
|---|---|---|---|
| Ni–NH₂ amido | `[Ni][NH2]` | `[NH2][Ni]` | H₂NNi |
| Ni–NH₂ (let RDKit fill H) | `[Ni]N` | `[NH2][Ni]` | H₂NNi |
| Pd–NMe₂ amido | `[Pd]N(C)C` | `C[N](C)[Pd]` | C₂H₆NPd |
| Ti(OMe)₄ alkoxo | `[Ti](OC)(OC)(OC)OC` | `C[O][Ti]([O]C)([O]C)[O]C` | C₄H₁₂O₄Ti |
| Au(I) thiolate | `[Au]SCC` | `CC[S][Au]` | C₂H₅AuS |
| PtMe₂Cl₂ (trans) | `C[Pt](C)(Cl)Cl` | `[CH3][Pt]([CH3])([Cl])[Cl]` | C₂H₆Cl₂Pt |

**Rule:** the ligand atom (N, O, S) inside brackets keeps the H count you give it. Outside brackets it gets organic-subset valence and RDKit fills the missing Hs. **For amido, write `[Ni][NH2]` to be explicit.** Conversely, write `[NH3]->[Ni]` (or even `[NH3][Ni]` — `cleanupOrganometallics` will dative-ify it) for ammine: outside brackets, plain `N[Ni]` gives amido.

**Bracket migration on round-trip:** after parsing `[Pd]N(C)C`, RDKit writes `C[N](C)[Pd]` — the `N` becomes bracketed (`[N]`) because it has zero implicit H and PR #8318 (2025.03.1) now brackets every metal-bound atom for lossless round-trip. The molecule is unchanged; only the string form differs.

## C. NHC carbenes

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
Cc1cc(C)c(N2CCN(c3c(C)cc(C)cc3C)[C]2)c(C)c1                # SIMes
CC(C)c1cccc(C(C)C)c1N1CCN(c2c(C(C)C)cccc2C(C)C)[C]1        # SIPr
```

### CAAC (cyclic alkyl amino carbene, Bertrand)

```
CC(C)c1cccc(C(C)C)c1N1C(c2c(C)cc(C)cc2C)C(C)(C)[C]1
```

Pattern: `ArN1-C(R1)(R2)-CR3R4-[C]1` where `[C]` is the carbene.

### Verification

```python
mol = Chem.MolFromSmiles(smi)
carbene_c = [a for a in mol.GetAtoms()
             if a.GetSymbol() == 'C' and a.GetTotalNumHs() == 0
             and a.GetDegree() == 2 and a.GetFormalCharge() == 0]
assert len(carbene_c) == 1
```

### NHC bound to a metal — use the dative arrow

```
# IMes->Pd(Cl)2  (donor is the carbene C)
Cc1cc(C)c(N2C=CN(c3c(C)cc(C)cc3C)[C]2->[Pd](Cl)Cl)c(C)c1
```

## D. Phosphines, phosphites — and the `[PH]` artifact

Free phosphines parse cleanly:

| Ligand | SMILES |
|---|---|
| PMe₃ | `P(C)(C)C` |
| PPh₃ | `P(c1ccccc1)(c1ccccc1)c1ccccc1` |
| PCy₃ | `P(C1CCCCC1)(C1CCCCC1)C1CCCCC1` |
| P(OMe)₃ | `P(OC)(OC)OC` |
| PtBu₃ | `P(C(C)(C)C)(C(C)(C)C)C(C)(C)C` |
| DPPE | `P(c1ccccc1)(c1ccccc1)CCP(c2ccccc2)c2ccccc2` |

**Known artifact (RDKit 2026.03.1, still present): when a P–M single bond appears, the round-trip introduces `[PH]`.** Example:

```python
m = Chem.MolFromSmiles('[Pd](Cl)(Cl)P(C)(C)C')
Chem.MolToSmiles(m)
# 'C[PH](C)(C)[Pd]([Cl])[Cl]'   — note the spurious [PH]
```

This is because P's default valence is 3; with three C-bonds + one Pd-bond it's tetravalent, and RDKit's PVI model adds an explicit H to "fix" what it thinks is hypervalence. The structure is **chemically correct** (the `[PH]` is a parser artifact, not a real proton) — but if you need a clean form:

- **Authoring fix:** write the P→M bond as dative: `[P](C)(C)(C)->[Pd](Cl)Cl` → canonical `C[P](C)(C)->[Pd]([Cl])[Cl]` (no `[PH]`)
- **Post-parse fix:** `Chem.RemoveHs(mol)` after parsing
- **Downstream:** for molSimplify, `[PH]` is harmless because `mol3D` re-infers coordination

### Wilkinson's catalyst — both styles

```
# Non-dative (gets [PH] on round-trip):
[Rh](Cl)(P(c1ccccc1)(c1ccccc1)c1ccccc1)(P(c2ccccc2)(c2ccccc2)c2ccccc2)P(c3ccccc3)(c3ccccc3)c3ccccc3

# Dative (clean):
Cl[Rh](<-P(c1ccccc1)(c1ccccc1)c1ccccc1)(<-P(c2ccccc2)(c2ccccc2)c2ccccc2)<-P(c3ccccc3)(c3ccccc3)c3ccccc3
```

## E. η-coordination / hapticity

There are now **three** ways to encode hapticity in RDKit. Pick by downstream needs.

### η² alkene — the 3-membered-ring idiom

```python
'[Ni]1CC1'        # η²-ethene-Ni — round-trips as '[CH2]1[CH2][Ni]1'
'[Ni]1OC1=O'      # η²-CO₂-Ni
'[Ni]1CC1c1ccccc1' # η²-styrene-Ni
```

**Important:** keep the ring C–C bond as a **single** bond (`[Ni]1CC1`). Writing `[Ni]1C=C1` parses as cyclopropene-like with a metal and confuses aromaticity perception. The graph topology (Ni bonded to both olefinic carbons) is what encodes the η². The C=C bond order is implicit — if you need to query with SMARTS, use `[#28]1[#6][#6]1`.

### η³ allyl — the 4-membered ring with one C=C

```python
'[Pd]([Cl])1CC=C1'   # η³-allyl-Pd-Cl, round-trips as '[Cl][Pd]1[CH]=C[CH2]1'
```

Two C–Pd edges flank a C=C, encoding the π-allyl topology. The central-C trick (`[Pd]C(=C)C`) parses but loses the metal–terminal-carbon bonds.

### η⁵ Cp, η⁶ arene — ionic disconnect (recommended)

The robust, RDKit-portable representation is **separated components** with charge balance:

```python
'[Fe+2].[cH-]1cccc1.[cH-]1cccc1'      # ferrocene
'[Fe+2].[cH-]1cccc1.Cc1c(C)c(C)c(C)[c-]1C'  # FeCp*Cp (mixed)
```

The metal is one component, each Cp is an anion component. Hapticity is implicit (chemist reads it; software doesn't). This survives ChemDraw, Open Babel, and OEChem round-trips.

### Multidative haptic SMILES (RDKit ≥ 2025.03.1, native)

Since PR #8301, RDKit accepts ring-closure notation where multiple ligand atoms close to the same metal — letting hapticity stay graph-explicit:

```python
'[CH2-]1-[CH]2=[CH2]3.[Fe]123'                  # η³-propene-Fe
'[cH]12[cH]3[cH]4[cH]5[cH]6[cH]17.[Fe]234567'   # η⁶-benzene-Fe
```

The disconnect `.` separates ligand and metal as components, but the ring digits 1-7 create dative bonds across the disconnect. RDKit round-trips both with `->` arrows.

### Hapticity API — `HapticBondsToDative` / `DativeBondsToHaptic`

For programmatic interconversion between haptic dummy-atom centroids (used in MOL/SDF) and dative-bond representations:

```python
from rdkit import Chem
# dummy-atom centroid → multiple datives
m_dative = Chem.HapticBondsToDative(m_haptic)
# multiple datives → dummy-atom centroid
m_haptic = Chem.DativeBondsToHaptic(m_dative)
```

Both live in `rdkit.Chem.rdmolops`, hardened by PR #6253 (2023).

### Decision tree for hapticity

```
Need RDKit-only graph fidelity?                      -> multidative (2025.03+)
Need ChemDraw/Open Babel/OEChem portability?         -> ionic disconnect
Need clean ML featurization (no exotic bond types)?  -> ionic disconnect
Need to recover hapticity from a CIF/MOL?            -> HapticBondsToDative
Just need a quick η² alkene?                         -> 3-membered ring
Just need a quick η³ allyl?                          -> 4-membered ring with one C=C
```

## F. μ-bridging ligands

| Motif | SMILES | Notes |
|---|---|---|
| μ-Cl bridge | `[Pd]1Cl[Pd]1` | Round-trips as `[Cl]1[Pd][Pd]<-1` with auto-dative |
| Open Pd₂Cl₄ | `Cl[Pd](Cl)(Cl)[Pd]Cl` | No bridge, just two square-planar Pd |
| μ-H bridge | `[Mn]1[H][Mn]1` | **Needs partial sanitize** (H explicit valence = 2 fails default) |
| μ-CO (Fe₂(CO)₉-ish) | `[Fe]1([C-]#[O+])([C-]#[O+])([C-]#[O+])C(=O)[Fe]1([C-]#[O+])([C-]#[O+])[C-]#[O+]` | Full sanitize OK |

**Rule for μ-H:** RDKit's default sanitization forbids hydrogen valence > 1. Use the partial-sanitize helper from §I for `[M]1[H][M]1` patterns. **Round-trip warning:** the canonical form RDKit emits (`[H]1[Mn][Mn]1`) also fails the default sanitize check, so any pipeline that re-parses canonical output must do so with partial sanitize too. If you need a single canonical SMILES that survives default re-parse, accept the loss of bridge topology and write `[M][H]` with H terminal on one metal.

## G. M–M multiple bonds — `$` is the quadruple-bond token

RDKit accepts all four bond orders between metals, including the rare `$`:

| Bond order | Token | Example | Round-trip |
|---|---|---|---|
| single | `-` (or implicit) | `[Mn](...)[Mn](...)`  Mn₂(CO)₁₀ | clean |
| double | `=` | `[Mo]=[Mo]` | `[Mo]=[Mo]` |
| triple | `#` | `[Mo]#[Mo]` | `[Mo]#[Mo]` |
| quadruple | `$` | `[Mo]$[Mo]` | `[Mo]$[Mo]` |

Re₂Cl₈²⁻ (quadruple bond):
```
[Re-]([Cl])([Cl])([Cl])([Cl])$[Re-]([Cl])([Cl])([Cl])[Cl]
```

Mn₂(CO)₁₀ (M–M single):
```
[Mn]([C-]#[O+])([C-]#[O+])([C-]#[O+])([C-]#[O+])([C-]#[O+])[Mn]([C-]#[O+])([C-]#[O+])([C-]#[O+])([C-]#[O+])[C-]#[O+]
```

Mo₂(OH)₈ (test surrogate for paddlewheel without bridging carboxylates):
```
[OH][Mo]([OH])([OH])([OH])$[Mo]([OH])([OH])([OH])[OH]
```
For the genuine Mo₂(OAc)₄ paddlewheel, use bridging carboxylates and place `$` between the two Mo atoms.

## H. Catalytic intermediates and metallacycles

| Motif | SMILES | Comment |
|---|---|---|
| Ar–Ni(II)–Br (oxidative addition) | `Brc1ccc([Ni]Br)cc1` | C₆H₄Br₂Ni |
| Ph–Pd(II)–Et (cross-coupling) | `c1ccc([Pd](Br)CC)cc1` | Pd explicit valence 3 |
| Nickelalactone (Ni/CO₂/C₂H₄) | `O=C1O[Ni]CC1` | 5-membered: Ni–O–C(=O)–CH₂–CH₂ |
| Nickelacyclopentene | `[Ni]1CC=CC1` | 5-membered metallacycle |
| Ru=CH₂ methylidene | `[Ru]=C` | Round-trip `[CH2]=[Ru]` |
| Ir(H)(Cl) (Vaska-style) | `[Ir]([H])(Cl)(P(C)(C)C)P(C)(C)C` | H groups onto Ir as `[IrH]` |

### Grubbs-1 (Cl₂(PCy₃)₂Ru=CHPh)

```
Cl[Ru](=Cc1ccccc1)(Cl)(P(C2CCCCC2)(C2CCCCC2)C2CCCCC2)P(C3CCCCC3)(C3CCCCC3)C3CCCCC3
```
C₄₃H₇₄Cl₂P₂Ru — parses with full sanitize; gets `[PH]` on round-trip (see §D).

### Schrock molybdenum alkylidene

```
[Mo](=CC(C)(C)C)(=NC(C)(C)C)(OC(C)(C)C)OC(C)(C)C
```
The =NR imido and =CR alkylidene both ride double bonds off Mo. Round-trips cleanly.

### Recommendation
Prefer the **pubchem-api** skill for stock catalysts (Grubbs 1st gen CID 11571518, Grubbs 2nd CID 11647888, Hoveyda-Grubbs 2nd CID 11320810). Hand-author only when you need a variant not on PubChem.

## I. Sanitization patterns

Default `Chem.MolFromSmiles(smi)` runs `SANITIZE_ALL` which since RDKit 2023.09.1 includes `SANITIZE_CLEANUP_ORGANOMETALLICS` (flag `0x400`, PR #6357). This step walks each hypervalent atom bonded to a metal and downgrades the single bond → dative.

When that's not enough — e.g. μ-H bridges, neutral CO with dative arrows, η⁵ Cp via single bonds — use **partial sanitize**:

```python
from rdkit import Chem

PARTIAL_SANITIZE = Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES

def parse_om(smi: str):
    """Parse organometallic SMILES with fallback to partial sanitize.
    Returns (mol, mode) where mode in {'full', 'partial'}."""
    m = Chem.MolFromSmiles(smi)
    if m is not None:
        return m, "full"
    m = Chem.MolFromSmiles(smi, sanitize=False)
    if m is None:
        raise ValueError(f"unparseable: {smi}")
    Chem.SanitizeMol(m, sanitizeOps=PARTIAL_SANITIZE)
    return m, "partial"
```

To **disable** the OM cleanup explicitly (rare — e.g. when you want to inspect raw bond orders before the rewrite):

```python
flags = Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_CLEANUP_ORGANOMETALLICS
```

## J. Metal centres reference

| Metal/ion | SMILES |
|---|---|
| Ni(0) / Ni(II) | `[Ni]` / `[Ni+2]` |
| Pd(0) / Pd(II) | `[Pd]` / `[Pd+2]` |
| Pt(II) | `[Pt+2]` |
| Ru(II) | `[Ru+2]` |
| Fe(II) / Fe(III) | `[Fe+2]` / `[Fe+3]` |
| Rh(I) | `[Rh+]` |
| Ir(I) / Ir(III) | `[Ir+]` / `[Ir+3]` |
| Cu(I) / Cu(II) | `[Cu+]` / `[Cu+2]` |
| Au(I) / Au(III) | `[Au+]` / `[Au+3]` |
| Mo(0) | `[Mo]` |
| Re(III) | `[Re-]` (in Re₂Cl₈²⁻ each Re carries −1 formal charge) |

**Charge convention:** for ML featurization include the formal oxidation state. For molSimplify geometry building, a 0-charge metal with neutral L-type donors often gives the most stable embed.

## K. Common ligand fragments (attach at leftmost atom)

| Fragment | SMILES |
|---|---|
| Cp (cyclopentadienyl anion) | `[cH-]1cccc1` |
| Cp* (pentamethyl-Cp anion) | `Cc1c(C)c(C)c(C)[c-]1C` |
| Acac (enol form) | `CC(=O)CC(C)=O` |
| Acac (anion) | `CC(=O)[CH-]C(C)=O` |
| Salen backbone | `Oc1ccccc1/C=N/CC/N=C/c1ccccc1O` |
| Triphos | `P(CC[P](c1ccccc1)c1ccccc1)(CC[P](c1ccccc1)c1ccccc1)CC[P](c1ccccc1)c1ccccc1` |
| COD (1,5-cyclooctadiene) | `C1CC=CCCC=C1` |
| NBD (norbornadiene) | `C1CC2CC1C=C2` |
| BINAP scaffold | `c1ccc2c(c1)ccc1c2c(P(c2ccccc2)c2ccccc2)ccc1P(c1ccccc1)c1ccccc1` |
| CO (charge-trick, preferred) | `[C-]#[O+]` |
| CO (neutral, needs partial sanitize when M-bound) | `C#O` |

## L. molSimplify-specific conventions

1. **Prefer `from_smiles` with `gen3d=True`** for small organic ligands. For TMCs, build via `startgen_pythonic({'-core': ..., '-lig': ...})` rather than a giant SMILES.

2. **Ligand SMILES in compound tables:** store the **free, un-coordinated ligand's** canonical SMILES. The catalyst itself is assembled via `-lig`/`-ligcon`/`-core`.

3. **Donor atom index** (`-ligcon`): RDKit atom indices match `mol3D` indices after `mol3D.from_smiles`. Identify donors with:
   ```python
   rd = Chem.MolFromSmiles(smi)
   donor_idx = [a.GetIdx() for a in rd.GetAtoms()
                if a.GetSymbol() in {'N', 'P', 'O', 'S'} and a.GetTotalNumHs() == 0]
   # NHCs: carbene `[C]` — match GetSymbol()=='C' and GetTotalNumHs()==0 and GetDegree()==2
   ```

4. **Pydentate fallback:** if you omit `-ligcon`, molSimplify's pydentate GNN predicts coordinating atoms. Trust it for common ligands; verify for unusual donors.

## Troubleshooting checklist

| Symptom | Likely cause | Fix |
|---|---|---|
| `MolFromSmiles` returns `None` for complex | Ligand atom hypervalent under default valence rules | Use dative `->` on L-type donors, or fall back to `parse_om` helper (§I) |
| NHC carbene parsed as `[CH2]` | Wrote `C` instead of `[C]` | Replace with `[C]` inside ring |
| Phosphine round-trips as `[PH]` | P got 4 connections with default valence 3 | Use `[P](...)->[M]` dative or `Chem.RemoveHs` post-parse |
| Amido bond `[Ni]N` writes as `[Ni][NH2]` | Outside brackets, N takes 2 implicit H | Cosmetic only — same molecule. Use `[NH2]` to be explicit. |
| η-complex won't parse | Used `=` inside the η-ring | Use single bonds in the M-containing ring (`[Ni]1CC1` not `[Ni]1C=C1`) |
| Pyridine ring loses aromaticity after metal binding | Wrote Kekulé `N=CC=CC=C` | Use lowercase `n1ccccc1` |
| `mol3D.from_smiles` 3D embedding fails | OpenBabel can't build a conformer | Build free ligand first, coordinate via `-lig` |
| Wrong hapticity in assembled complex | SMILES lacks hapticity info | Use `-ligcon` indices in molSimplify, or multidative encoding (§E) |
| `MolToInchi` crashes on TMC | RDKit issue #6853 (dative bonds unsupported in InChI) | Call `Chem.DativeBondsToHaptic(m)` first, or downgrade datives to single bonds |
| Hybridization wrong (SP3D on dative donor) | RDKit issue #5736 (closed: not planned) | Don't rely on hybridization for dative-bound atoms |
| Hydride explicit valence error on μ-H | Default sanitize forbids H valence > 1 | Use partial-sanitize helper (§I) |

## Verification ritual

Every authored OM SMILES needs three checks:

```python
from rdkit import Chem
from rdkit.Chem import Draw, rdMolDescriptors

mol, mode = parse_om(smi)               # parses (full or partial sanitize)
print("mode:", mode)
print("formula:", rdMolDescriptors.CalcMolFormula(mol))   # matches paper?
canon = Chem.MolToSmiles(mol)
print("canon:", canon)
roundtrip = Chem.MolFromSmiles(canon)
assert roundtrip is not None, "canonical form fails to re-parse"
Draw.MolToImage(mol, size=(400, 400))   # visual check
```

Test suite: see `tests/test_organometallic_smiles.py` for executable checks on every motif in this document.
