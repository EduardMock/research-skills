# test/co2-mech/compounds.py
"""Hard-coded chemistry data for the Fan, Chen & Lin 2012 Chem. Commun. feature
article "Theoretical studies of reactions of carbon dioxide mediated and
catalysed by transition metal complexes" (Chem. Commun., 2012, 48, 10808).

This is a broad theoretical *review*. The overwhelming majority of its 38
Schemes are GENERIC model cartoons — bare [M] / [Ni] / [Pd] / [Ru] metal
placeholders with model L = PH3 / PMe3 ligands and R-group substituents — that
depict OTHER groups' DFT model systems, not discrete catalogable compounds.
Per the skill's inclusion criteria those placeholder cartoons are excluded.

Catalogued (discrete, bold-numbered or named-and-used species):
  * Scheme 5 : Pd2 allyl-bridged dinuclear complexes 1 -> 2 (L = PMe3,
               bridging ligand = 2-methylallyl). The review's own DFT study.
  * Scheme 19 / eqn 4 : niobium-nitride catalytic cycle 1Nb -> 2Nb -> 3Nb
               -> 4Nb (L = amide N(tBu)Ar, Ar = 3,5-dimethylphenyl).
  * eqn 14 / eqn 15 : Ni(COD)2 / phosphine catalysed [2+2+2] of silylated
               diynes with CO2 -> bicyclic 2-pyrones (discrete drawn structures).
  * Named catalyst protagonists actually charged in eqns 14/15: Ni(COD)2,
               COD (free ligand), P(n-Oct)3, 2-(2-pyridylethyl)dibutylphosphine.
  * CO2 : the protagonist substrate appearing in every numbered transformation.
"""
from __future__ import annotations
from typing import Any

PAPER_COMPOUND_TABLE: list[dict[str, Any]] = [
    # --- universal substrate ---
    {"paper_id": "CO2", "role": "CO2",
     "name": "carbon dioxide",
     "fallback_smiles": "O=C=O"},

    # --- Scheme 5: allyl-bridged dinuclear Pd(I) complexes (L = PMe3,
    #     bridging ligand = 2-methylallyl). 1 + CO2 -> 2 (one bridging allyl
    #     converted to a bridging carboxylate). ---
    {"paper_id": "1", "role": "catalyst",
     "name": "bis(mu-2-methylallyl) bis(trimethylphosphine) dipalladium "
             "(Scheme 5 reactant)",
     "fallback_smiles": "CP(C)(C)[Pd]1[Pd](P(C)(C)C)CC(C)=C1"},
    {"paper_id": "2", "role": "product",
     "name": "(mu-2-methylallyl)(mu-2-methylallylcarboxylato) "
             "bis(trimethylphosphine) dipalladium (Scheme 5 product)",
     "fallback_smiles": "CP(C)(C)[Pd]1[Pd](P(C)(C)C)OC(=O)CC(C)=C1.C=C(C)C"},

    # --- Scheme 19 / eqn 4: niobium-nitride cycle. Amide ligand = N(tBu)Ar,
    #     Ar = 3,5-dimethylphenyl. Three amides per Nb. ---
    {"paper_id": "1Nb", "role": "catalyst",
     "name": "anionic niobium nitride [NNb(N(tBu)Ar)3]- (Ar = 3,5-xylyl)",
     "fallback_smiles": "N#[Nb](N(C(C)(C)C)c1cc(C)cc(C)c1)(N(C(C)(C)C)c1cc(C)cc(C)c1)N(C(C)(C)C)c1cc(C)cc(C)c1"},
    {"paper_id": "2Nb", "role": "intermediate",
     "name": "niobium carbamate [O2C-N=Nb(N(tBu)Ar)3]- from CO2 insertion",
     "fallback_smiles": "[O-]C(=O)N=[Nb](N(C(C)(C)C)c1cc(C)cc(C)c1)(N(C(C)(C)C)c1cc(C)cc(C)c1)N(C(C)(C)C)c1cc(C)cc(C)c1"},
    {"paper_id": "3Nb", "role": "intermediate",
     "name": "niobium isocyanate acetate [OCN-Nb(OC(O)Me)(N(tBu)Ar)3]",
     "fallback_smiles": "O=C=N[Nb](OC(C)=O)(N(C(C)(C)C)c1cc(C)cc(C)c1)(N(C(C)(C)C)c1cc(C)cc(C)c1)N(C(C)(C)C)c1cc(C)cc(C)c1"},
    {"paper_id": "4Nb", "role": "intermediate",
     "name": "niobium isocyanate [OCN-Nb(N(tBu)Ar)3]",
     "fallback_smiles": "O=C=N[Nb](N(C(C)(C)C)c1cc(C)cc(C)c1)(N(C(C)(C)C)c1cc(C)cc(C)c1)N(C(C)(C)C)c1cc(C)cc(C)c1"},

    # --- eqn 14: hepta-1,6-diyne (H / SiMe3 termini) + CO2 --Ni(COD)2/P(n-Oct)3-->
    #     cyclopenta-fused 2-pyrone with SiMe3 alpha to the carbonyl.
    #     Atom balance: C10H16Si + CO2 -> C11H16O2Si (exact). ---
    {"paper_id": "14s", "role": "diyne",
     "name": "1-(trimethylsilyl)hepta-1,6-diyne (eqn 14 substrate)",
     "fallback_smiles": "C#CCCCC#C[Si](C)(C)C"},
    {"paper_id": "14p", "role": "pyrone",
     "name": "4-(trimethylsilyl)-6,7-dihydro-5H-cyclopenta[c]pyran-3(?)-one "
             "(eqn 14 product; SiMe3 alpha to C=O)",
     "fallback_smiles": "O=C1OC=C2CCCC2=C1[Si](C)(C)C"},

    # --- eqn 15: octa-diyne (Et / SiMe3 termini, (CH2)4 tether) + CO2
    #     --Ni(COD)2/2-PyCH2CH2PBu2--> cyclohexane-fused 2-pyrone with Et alpha
    #     to C=O and SiMe3 alpha to ring O (opposite regiochem to eqn 14).
    #     Atom balance: C13H22Si + CO2 -> C14H22O2Si (exact). ---
    {"paper_id": "15s", "role": "diyne",
     "name": "1-(trimethylsilyl)-8-... ethyl-substituted octa-1,7-diyne "
             "(eqn 15 substrate)",
     "fallback_smiles": "CCC#CCCCCC#C[Si](C)(C)C"},
    {"paper_id": "15p", "role": "pyrone",
     "name": "4-ethyl-1-(trimethylsilyl)-5,6,7,8-tetrahydroisochromen-3-one "
             "(eqn 15 product; Et alpha to C=O, SiMe3 alpha to ring O)",
     "fallback_smiles": "O=C1OC(=C2CCCCC2=C1CC)[Si](C)(C)C"},

    # --- named catalyst protagonists charged in eqns 14/15 ---
    {"paper_id": "Ni(COD)2", "role": "catalyst_precursor",
     "name": "bis(1,5-cyclooctadiene)nickel(0)",
     "fallback_smiles": "[Ni].C1CC=CCCC=C1.C1CC=CCCC=C1"},
    {"paper_id": "COD", "role": "ligand",
     "name": "1,5-cyclooctadiene (free ligand of Ni(COD)2)",
     "fallback_smiles": "C1CC=CCCC=C1"},
    {"paper_id": "P(n-Oct)3", "role": "ligand",
     "name": "tri-n-octylphosphine (eqn 14 ligand)",
     "fallback_smiles": "CCCCCCCCP(CCCCCCCC)CCCCCCCC"},
    {"paper_id": "2-PyCH2CH2PBu2", "role": "ligand",
     "name": "2-(2-(dibutylphosphino)ethyl)pyridine (eqn 15 ligand)",
     "fallback_smiles": "CCCCP(CCCC)CCc1ccccn1"},
]

# Electronic structure for every transition-metal-bearing species in the table
# plus the in-situ Ni(0)-phosphine adducts of the [2+2+2] cycle (eqns 14/15,
# Scheme 38), which are not table rows but live here per the skill contract.
EXPECTED_ELECTRONIC_STRUCTURE: dict[str, dict[str, Any]] = {
    # Scheme 5 dinuclear Pd(I)-Pd(I), each Pd d9, Pd-Pd bond -> overall singlet.
    "Pd2_bis_allyl_1": {
        "oxidation_state": 1, "d_count": 9,
        "geometry_class": "dinuclear_allyl_bridged",
        "spin_state": "closed_shell_singlet"},
    "Pd2_allyl_carboxylate_2": {
        "oxidation_state": 1, "d_count": 9,
        "geometry_class": "dinuclear_allyl_carboxylate_bridged",
        "spin_state": "closed_shell_singlet"},

    # Scheme 19 niobium cycle. 1Nb anionic Nb nitride is d0 Nb(V).
    "Nb_nitride_1Nb": {
        "oxidation_state": 5, "d_count": 0,
        "geometry_class": "tetrahedral", "spin_state": "closed_shell_singlet"},
    "Nb_carbamate_2Nb": {
        "oxidation_state": 5, "d_count": 0,
        "geometry_class": "tetrahedral", "spin_state": "closed_shell_singlet"},
    "Nb_isocyanate_acetate_3Nb": {
        "oxidation_state": 5, "d_count": 0,
        "geometry_class": "trigonal_bipyramidal",
        "spin_state": "closed_shell_singlet"},
    "Nb_isocyanate_4Nb": {
        "oxidation_state": 5, "d_count": 0,
        "geometry_class": "tetrahedral", "spin_state": "closed_shell_singlet"},

    # eqns 14/15 [2+2+2]: Ni(COD)2 precursor + in-situ Ni(0)-phosphine /
    # nickelacycle resting states drawn in Scheme 38.
    "Ni(COD)2": {
        "oxidation_state": 0, "d_count": 10,
        "geometry_class": "tetrahedral", "spin_state": "closed_shell_singlet"},
    "Ni(0)_L_eta2_diyne": {
        "oxidation_state": 0, "d_count": 10,
        "geometry_class": "trigonal_planar",
        "spin_state": "closed_shell_singlet"},
    "nickelacycle_oxa": {
        "oxidation_state": 2, "d_count": 8,
        "geometry_class": "square_planar",
        "spin_state": "closed_shell_singlet"},
}
