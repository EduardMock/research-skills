# Organometallic SMILES — Literature and Library Landscape

Curated reading and tool list for handling organometallic compounds in cheminformatics, with focus on what works in RDKit. Compiled May 2026.

## TL;DR for picking a representation

| Use case | Recommended encoding | Reference |
|---|---|---|
| Stock catalyst lookup | PubChem CID → canonical SMILES | pubchem-api skill |
| Bench-author for paper/figure | Dative `->` for L-type + single for X-type | Rasmussen 2025 |
| ML featurization (no exotic bonds) | Ionic disconnect, dummy-atom for haptic | tmQMg-L (Kneiding 2024) |
| Catalogue OM ligands programmatically | tmQMg-L's CSV + nested-list hapticity | tmQMg-L (Kneiding 2024) |
| Build 3D structures from scratch | molSimplify / Architector / MACE | see Building Toolkits |
| Cross-toolkit interop (Open Babel, OE) | Disable dative on write; ionic Cp form | RDKit `SmilesWriteParams.includeDativeBonds=False` |
| InChI generation on TMC | Convert datives → haptic first | RDKit `DativeBondsToHaptic` |

## Standards papers

### SMILES extensions

- **OpenSMILES specification v1.0** (Craig A. James, ed.) — §3.9.6 defines `->` / `<-` arrow bonds. The de-facto standard for dative-bond SMILES.
  http://opensmiles.org/opensmiles.html

- **"SMILES all around: structure-to-SMILES conversion for transition metal complexes."** Rasmussen, Strandgaard, Seumer, et al. (Jensen group, Copenhagen). *J. Cheminform.* 17:63 (2025). DOI: [10.1186/s13321-025-01008-1](https://doi.org/10.1186/s13321-025-01008-1)
  *The* current conventions paper for RDKit-style OM SMILES. Recommendations: (i) every M–L bond as a dative with electrons on the ligand; (ii) non-zwitterionic carbene form for NHCs; (iii) cleaning heuristic for spurious haptic neighbours from XYZ→SMILES inference. Generated parsable SMILES for 227,124 CSD complexes. Notes RDKit's unreliable metal-centred stereo in 2024.03.3.

- **RDKit Discussion #3618** — "Improving the RDKit's support for organometallics" (Greg Landrum, opened Dec 2020). The community roadmap thread.
  https://github.com/rdkit/rdkit/discussions/3618

### InChI

- **"The IUPAC International Chemical Identifier (InChI)."** Goodman, Pletnev, Thiessen, Bolton, Heller. *J. Cheminform.* 13:40 (2021). DOI: [10.1186/s13321-021-00517-z](https://doi.org/10.1186/s13321-021-00517-z)
  Documents InChI 1.06; explicitly flags organometallics as "not described by the current version" with extensions planned.

- **"Making the InChI FAIR and sustainable while moving to inorganics."** Blanke, Brammer, Baljozovic, Khan, Lange, Bänsch, Tovee, Schatzschneider, Hartshorn, Herres-Pawlis. *Faraday Discuss.* 256, 503–519 (2025). DOI: [10.1039/D4FD00145A](https://doi.org/10.1039/D4FD00145A)
  Introduces the InChI 1.07 / FAIR-InChI inorganic extension: a decision tree using coordination number and electronegativity to decide which M–L bonds to keep vs. disconnect. FeCl₂ becomes ionic; [FeCl₄]²⁻ kept intact. The most consequential standards advance for OM identification.

### CML / MOL/SDF

- **CML "Chemical Markup Language for Computational Chemistry."** Phadungsukanan et al. *J. Cheminform.* 4:15 (2012). DOI: [10.1186/1758-2946-4-15](https://doi.org/10.1186/1758-2946-4-15)
  Background only — `bondType="hbond"` covers dative bonds, no recent OM-specific update.

- **MDL/Dassault BIOVIA CTAB spec** — V3000 supports `BOND CFG` type 9 (coordination/dative) and arbitrary atom valence. No native hapticity.

## Database papers

- **tmQM.** Balcells & Skjelstad. "tmQM Dataset — Quantum Geometries and Properties of 86k Transition Metal Complexes." *J. Chem. Inf. Model.* 60(12): 6135-6146 (2020). DOI: [10.1021/acs.jcim.0c01041](https://doi.org/10.1021/acs.jcim.0c01041)
  86k TMC structures + DFT properties; SMILES via Open Babel (acknowledged lossy).

- **tmQMg.** Kneiding et al. "Deep learning metal complex properties with natural quantum graphs." *Digital Discovery* 2, 996 (2023). DOI: [10.1039/D2DD00129B](https://doi.org/10.1039/D2DD00129B)
  Replaces SMILES with **natural quantum graphs (NatQG)** from NBO analysis — explicit admission that SMILES is inadequate for TMC electronic structure.

- **tmQMg-L.** Kneiding, Nova, Balcells. "Directional multiobjective optimization of metal complexes at the billion-system scale." *Nat. Comput. Sci.* 4, 263 (2024). DOI: [10.1038/s43588-024-00616-5](https://doi.org/10.1038/s43588-024-00616-5)
  30,466 ligands extracted from tmQMg. CSV columns: SMILES, NBO formal charge, donor-atom indices, DFT descriptors. **Hapticity encoded by nested lists** in `metal_bond_node_idx_groups`: indices in the same sublist = haptic group.

- **ReaLigands.** Taylor, Nandy, et al. (Kulik group). "ReaLigands: A Ligand Library Cultivated from Experiment and Intended for Molecular Computational Catalyst Design." *JCIM* 63(22), 7188 (2023). DOI: [10.1021/acs.jcim.3c01310](https://doi.org/10.1021/acs.jcim.3c01310)
  Companion library to molSimplify.

- **MOSAEC** (algorithm). White et al. "High Structural Error Rates in 'Computation-Ready' MOF Databases Discovered by Checking Metal Oxidation States." *JACS* (2025). DOI: [10.1021/jacs.5c04914](https://doi.org/10.1021/jacs.5c04914)
  Finds ≥40% structural-error rates in popular MOF databases via metal-oxidation-state consistency. **Cite this whenever a downstream pipeline ingests a "computation-ready" OM/MOF database without revalidation.**

- **MOSAEC-DB.** Vargas et al. *Chem. Sci.* (2025). DOI: [10.1039/D4SC07438F](https://doi.org/10.1039/D4SC07438F)
  Cleaned MOF database produced by the algorithm above.

- **CSD survey.** Taylor & Wood. "A Million Crystal Structures: The Whole Is Greater than the Sum of Its Parts." *Chem. Rev.* 119(16), 9427 (2019). DOI: [10.1021/acs.chemrev.9b00155](https://doi.org/10.1021/acs.chemrev.9b00155)
  General CSD context; no separate OM subset paper since.

## Workflow papers — RDKit on metals

- **Computational Discovery of Transition-Metal Complexes.** Nandy, Duan, Taylor, Liu, Steeves, Kulik. *Chem. Rev.* 121(16), 9927 (2021). DOI: [10.1021/acs.chemrev.1c00347](https://doi.org/10.1021/acs.chemrev.1c00347)
  Canonical review; catalogues representation choices and trade-offs.

- **molSimplify 2.0.** Terrones, Duan, Nandy, Kulik. *JCIM* 66(5), 2753 (2026). DOI: [10.1021/acs.jcim.5c02733](https://doi.org/10.1021/acs.jcim.5c02733)
  Eliminates steric clashes, supports higher-denticity ligands, ML-predicted coordinating-atom identities.

- **molSimplify v1.** Ioannidis, Gani, Kulik. *J. Comput. Chem.* 37(22), 2106 (2016). DOI: [10.1002/jcc.24437](https://doi.org/10.1002/jcc.24437)
  Original release; XYZ templates + ligand SMILES, no native dative-bond syntax.

- **Architector.** Taylor, Burrill, Janssen, Batista, Perez, Yang (LANL). "Architector for high-throughput cross-periodic table 3D complex building." *Nat. Commun.* 14, 2786 (2023). DOI: [10.1038/s41467-023-38169-2](https://doi.org/10.1038/s41467-023-38169-2)
  Input: metal + coordination number + ligand SMILES + explicit donor-atom indices (passed as Python dicts, not in-SMILES).

- **MACE.** Chernyshov & Pidko (TU Delft). "MACE: Automated Assessment of Stereochemistry of Transition Metal Complexes." *JCTC* 20(5), 2313 (2024). DOI: [10.1021/acs.jctc.3c01313](https://doi.org/10.1021/acs.jctc.3c01313)
  Pólya stereoisomer enumeration, decision trees for chirality-at-metal in CN 4–9. Explicitly notes "lack of support for π-bonding and polyhaptic ligands."

- **OBeLiX.** Kalikadien, van der Lem, Valsecchi, Lefort, Pidko. "Unveiling the impact of ligand configurations and structural fluxionality on virtual screening of TMCs." *Digital Discovery* (2025). DOI: [10.1039/D5DD00093A](https://doi.org/10.1039/D5DD00093A)
  Wraps MACE + ChemSpaX + CREST + Morfeus + cclib. Uses ligand SMILES → 3D stereoisomers; demoed on 87 bisphosphines (Ir, Ru, Mn).

- **Molassembler.** Sobez & Reiher. *JCIM* 60(8), 3884 (2020). DOI: [10.1021/acs.jcim.0c00503](https://doi.org/10.1021/acs.jcim.0c00503)
  Custom connectivity model (not SMILES) for inorganic/OM molecule construction.

## Catalysis ML/screening — SMILES conventions in practice

- **DENOPTIM.** Foscato, Venkatraman, Jensen. *JCIM* 59(10), 4077 (2019). DOI: [10.1021/acs.jcim.9b00516](https://doi.org/10.1021/acs.jcim.9b00516)
  Goes "beyond valence-rules representations"; uses fragment-graph model with custom attachment-point notation because SMILES can't natively express transition-state-like fragments or hapticity.

- **Automated de novo design of olefin metathesis catalysts.** Foscato, Jensen et al. *JCIM* 64(4), 1185 (2024). DOI: [10.1021/acs.jcim.3c01649](https://doi.org/10.1021/acs.jcim.3c01649)

- **Tartarus benchmark.** Nigam, Pollice, Tom, Jorner et al. *NeurIPS D&B* (2023). arXiv: [2209.12487](https://arxiv.org/abs/2209.12487)
  Reaction-substrate task is the closest to homogeneous catalysis, but **no Tartarus task involves a transition-metal centre.**

## Library landscape (active 2025–2026)

### Data libraries
| Project | Repo | What | Status |
|---|---|---|---|
| tmQMg | [uiocompcat/tmQMg](https://github.com/uiocompcat/tmQMg) | 74,547 CSD complexes + xyz + NBO graphs | active (Sept 2024 release) |
| tmQMg-L | [uiocompcat/tmQMg-L](https://github.com/uiocompcat/tmQMg-L) | 35,466 ligands + SMILES + donor indices | active (March 2025) |
| xyz2mol_tm | [jensengroup/xyz2mol_tm](https://github.com/jensengroup/xyz2mol_tm) | XYZ → RDKit SMILES with dative arrows | active |
| ReaLigands | (within molSimplify) | Curated ligand library | active |
| MOSAEC-DB | [uowoolab/MOSAEC](https://github.com/uowoolab/MOSAEC) | Cleaned MOF database | research-tool maintenance |

### Building toolkits
| Project | Repo | RDKit-based? | Status |
|---|---|---|---|
| molSimplify | [hjkgrp/molSimplify](https://github.com/hjkgrp/molSimplify) | OpenBabel-based | very active (v2.0.0 May 2026) |
| Architector | [lanl/Architector](https://github.com/lanl/Architector) | OpenBabel | slowing (last release July 2023) |
| MACE | [EPiCs-group/epic-mace](https://github.com/EPiCs-group/epic-mace) | **RDKit** (pinned 2020.09) | moderate |
| OBeLiX | [EPiCs-group/obelix](https://github.com/EPiCs-group/obelix) | RDKit | WIP |
| MetalloGen | [kyunghoonlee777/MetalloGen](https://github.com/kyunghoonlee777/MetalloGen) | uses m-SMILES syntax | early-stage |
| stk | [lukasturcani/stk](https://github.com/lukasturcani/stk) | **RDKit** + dative arrows | very active (5,313 commits) |

### Descriptors
| Project | Repo | What | Status |
|---|---|---|---|
| Morfeus | [digital-chemistry-laboratory/morfeus](https://github.com/digital-chemistry-laboratory/morfeus) | %Vbur, bite angle, Sterimol, xTB electronic | very active (Nov 2025) |
| DBSTEP | [patonlab/DBSTEP](https://github.com/patonlab/DBSTEP) | Sterimol, %Vbur, 3D-grid steric | quietly maintained |

### Format conversion
| Project | Repo | What |
|---|---|---|
| OpenBabel | [openbabel/openbabel](https://github.com/openbabel/openbabel) | Workhorse converter; permissive on metals |
| RDKit | [rdkit/rdkit](https://github.com/rdkit/rdkit) | First-class `->`/`<-` dative since 2018.09 |
| chemcoord | [mcocdawc/chemcoord](https://github.com/mcocdawc/chemcoord) | Z-matrix ↔ Cartesian |

## RDKit version timeline for OM features

| Release | What changed | PR |
|---|---|---|
| 2018.09 | `->`/`<-` dative bonds in SMILES + `BondType.DATIVE` | — |
| 2023.09.1 | `SANITIZE_CLEANUP_ORGANOMETALLICS` (0x400) reinstated as default; MOL V2000 bond type 9 = dative on read | #6357, #6566 |
| 2024.03.3 | `SmilesWriteParams.includeDativeBonds` (default True; toggle False for legacy tools) | #7384 |
| 2025.03.1 | Carbon hypervalence fix → η³-propene and η⁶-benzene multidative SMILES work; bracket-and-explicit-H on metal neighbours for lossless round-trip | #8301, #8318 |
| 2025.03.2 | ZOB CXSMILES `Z:` tag for zero-order bonds | #8454 |
| 2025.09.1/.2 | Hydrides-on-metal preserved through sanitization | #8874 |
| 2025.09.6 | `FindRingFamilies(includeDativeBonds=, includeHydrogenBonds=)` | — |
| 2026.03.1 | Current stable | — |

## Open RDKit issues to know about

- **#5736** "Hybridization wrong for dative-bound atoms" — closed *not planned*. Phosphines/NHCs report SP3D. Don't rely on hybridization for dative donors.
- **#7577** "Cu²⁺ radical count non-deterministic" — closed *not planned*. Mol-block representation alters inferred radical count.
- **#6853** "`MolToInchi` crashes on `BondType.DATIVE`" — open. Convert datives first with `DativeBondsToHaptic`.
- **#7655, #7659** Dative can erase double-bond stereo and R/S on metal in edge cases.
- **#7788** AlCl₃ isoelectronic model regression.

## Useful external resources

- Cookbook: [Organometallics with Dative Bonds (RDKitCB_19)](https://www.rdkit.org/docs/Cookbook.html)
- Jensen UGM 2024 talk: ["Dealing with organometallic molecules in RDKit"](https://speakerdeck.com/jhjensen/dealing-with-organometallic-molecules-in-rdkit) — catalyzed the recent round of fixes
- RDKit UGM repos: [2024](https://github.com/rdkit/UGM_2024), [2025](https://github.com/rdkit/UGM_2025)

## Cross-cutting observations

1. **The community has converged on OpenSMILES dative bonds + RDKit** as the practical encoding, despite RDKit's known weaknesses on metal stereo and polyhapticity (Rasmussen 2025).
2. **Hapticity has no clean SMILES solution.** Every workflow paper either (a) sidesteps it via external donor-atom indices (Architector, MACE, OBeLiX) or (b) admits the limitation (Rasmussen 2025, Chernyshov 2024).
3. **InChI 1.07** (Blanke 2025) is the most consequential standards advance of 2023–2026 and should make OM CSD searches finally tractable.
4. **Database error rates matter** — White 2025's 40%+ figure for MOF DBs is the cautionary reference whenever ingesting "computation-ready" OM data.
