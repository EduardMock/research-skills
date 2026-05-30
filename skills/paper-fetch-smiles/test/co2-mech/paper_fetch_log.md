# paper-fetch-smiles log — Fan 2012

Generated 2026-05-30T11:41:56+00:00

## REVIEW — needs human attention

- [ ] inclusion scope: this is a broad theoretical *review*; 38 Schemes are mostly GENERIC [M]/[Ni]/[Pd]/[Ru] model cartoons (model L = PH3/PMe3, R placeholders) depicting OTHER groups' DFT systems. Only Scheme 5 (Pd2 `1`/`2`), Scheme 19/eqn 4 (`1Nb`-`4Nb`) and eqns 14/15 (silyl diynes + bicyclic pyrones) carry discrete bold-numbered structures. A reviewer who wants every model cartoon catalogued would disagree with this scope.  _(compounds.py author)_
- [ ] `1`/`2` (Scheme 5) bridging-allyl connectivity to the two Pd centres is drawn as μ-allyl; the fallback SMILES embeds the allyl/carboxylate in the Pd2 ring as a faithful-but-simplified 2D representation, not a μ-η3 hapticity-correct structure.  _(compounds.py author)_
- [ ] `1Nb`/`2Nb` are anionic ([NNb(NR2)3]- / Na+ salt); fallback SMILES drawn as the neutral/anion core without the explicit Na+ counter-cation. Charge handling for these rows is approximate.  _(compounds.py author)_
- [ ] PubChem name resolution: COD, P(n-Oct)3, 2-PyCH2CH2PBu2 and the four silyl diyne/pyrone structures did not hit PubChem by generated name — carried through as fallback (n_unresolved=0, all have valid flat SMILES).  _(scripts/cli.py build)_

## VERIFIED — reviewer-confirmed
- extract-schemes: located 38 schemes (numbers [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38]), rendered 38 region crops (no full pages). reactions[] pending analyzer.  _(scripts/extract_schemes.py)_
- compounds.py: 15 rows authored; all 15 fallback_smiles parse with RDKit (sanitize=False) and are flat (no /, \\, @). All 7 metal-bearing rows (`1`,`2`,`1Nb`-`4Nb`,`Ni(COD)2`) have EXPECTED_ELECTRONIC_STRUCTURE coverage (9 EES keys incl. in-situ Ni(0)/nickelacycle resting states).  _(compounds.py author)_
- eqn 14 atom balance: substrate C10H16Si + CO2 -> product C11H16O2Si (exact). Regiochem: SiMe3 placed alpha to C=O per paper text "the silyl group ... is attached to the carbon atom that is bonded to the carbonyl unit". Alternative (SiMe3 alpha to ring-O) enumerated and rejected.  _(educt->product reasoning)_
- eqn 15 atom balance: substrate C13H22Si + CO2 -> product C14H22O2Si (exact). Regiochem OPPOSITE to eqn 14 per paper ("does not have the same regioselectivity"): Et alpha to C=O, SiMe3 alpha to ring-O; matches the drawn eqn-15 product.  _(educt->product reasoning)_
- compounds.png: visually checked all 15 cells against the paper drawings (Scheme 5, Scheme 19, eqns 14/15) — bicyclic pyrone ring sizes (cyclopenta for 14p, cyclohexa for 15p), SiMe3/Et positions, Pd2 and Nb cores all match. No [unparseable] placeholders.  _(render verification ritual)_
- PubChem resolved: CO2 (CID 280, MW 44.009), Ni(COD)2 (CID 6433264, MW 275.05). expected_electronic_structure carried through to compounds.json (9 keys).  _(scripts/cli.py build)_
