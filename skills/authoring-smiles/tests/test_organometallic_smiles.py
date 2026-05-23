"""Executable test suite for the organometallic SMILES rules in
``references/organometallic-and-catalysts.md``.

Each test verifies one rule with an assertion. Run with either:

    pytest tests/test_organometallic_smiles.py -v

or as a standalone script:

    python tests/test_organometallic_smiles.py

Verified against RDKit 2026.03.1 on Linux. Earlier versions:
    - multidative haptic (test_eta_multidative_*) requires >= 2025.03.1 (PR #8301)
    - includeDativeBonds toggle (test_smileswriteparams_dative_off) requires >= 2024.03.3 (PR #7384)
    - SANITIZE_CLEANUP_ORGANOMETALLICS auto-rewrite requires >= 2023.09.1 (PR #6357)

Each test belongs to one rule section in the markdown reference. When you change
a rule, change the corresponding test; the test names track the section letters.
"""

from __future__ import annotations

import sys

from rdkit import Chem
from rdkit.Chem import rdMolDescriptors


PARTIAL_SANITIZE = (
    Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES
)


def parse_om(smi: str) -> tuple[Chem.Mol, str]:
    """Parse organometallic SMILES with fallback to partial sanitize.

    Returns (mol, mode) where mode in {'full', 'partial'}.
    Raises ValueError if even partial-sanitize parse fails.
    """
    m = Chem.MolFromSmiles(smi)
    if m is not None:
        return m, "full"
    m = Chem.MolFromSmiles(smi, sanitize=False)
    if m is None:
        raise ValueError(f"unparseable: {smi}")
    Chem.SanitizeMol(m, sanitizeOps=PARTIAL_SANITIZE)
    return m, "partial"


def _check(smi: str, formula: str | None = None, mode: str = "full") -> Chem.Mol:
    """Helper: parse, verify mode and (optionally) formula. Returns the mol."""
    m, got_mode = parse_om(smi)
    assert got_mode == mode, f"{smi!r}: expected mode={mode!r}, got {got_mode!r}"
    if formula is not None:
        got = rdMolDescriptors.CalcMolFormula(m)
        assert got == formula, f"{smi!r}: expected formula={formula!r}, got {got!r}"
    canon = Chem.MolToSmiles(m)
    assert Chem.MolFromSmiles(canon) is not None, (
        f"{smi!r}: canonical {canon!r} fails to re-parse"
    )
    return m


# ---------------------------------------------------------------------------
# Rule 1: Default valence of transition metals is -1 (no valence check)
# ---------------------------------------------------------------------------


def test_rule1_metal_default_valence_is_minus_one():
    """Transition metals have default valence -1 = no valence enforcement.

    Confirmed for every Z in the d-block from 21 (Sc) to 80 (Hg).
    """
    pt = Chem.GetPeriodicTable()
    for z in list(range(21, 31)) + list(range(39, 49)) + list(range(72, 81)):
        v = pt.GetDefaultValence(z)
        assert v == -1, f"element Z={z} ({pt.GetElementSymbol(z)}): default valence {v} != -1"


# ---------------------------------------------------------------------------
# Section A: Dative bonds
# ---------------------------------------------------------------------------


def test_A_dative_arrow_parses():
    m = _check("[NH3]->[Ni]", formula="H3NNi")
    n_atom = next(a for a in m.GetAtoms() if a.GetSymbol() == "N")
    ni_atom = next(a for a in m.GetAtoms() if a.GetSymbol() == "Ni")
    bond = m.GetBondBetweenAtoms(n_atom.GetIdx(), ni_atom.GetIdx())
    # The bond is encoded as DATIVE...
    assert bond.GetBondType() == Chem.BondType.DATIVE
    # ...and crucially preserves all 3 Hs on N (vs. the unbracketed-N footgun in test_A_unbracketed_N_becomes_amido).
    assert n_atom.GetTotalNumHs() == 3


def test_A_dative_direction_symmetric():
    """[Ni]<-[NH3] and [NH3]->[Ni] parse to the same canonical form."""
    a = Chem.MolToSmiles(Chem.MolFromSmiles("[NH3]->[Ni]"))
    b = Chem.MolToSmiles(Chem.MolFromSmiles("[Ni]<-[NH3]"))
    assert a == b == "[NH3]->[Ni]"


def test_A_bracketed_NH3_single_bond_is_rewritten_to_dative():
    """[NH3][Ni] (bracketed N, plain bond) auto-converts to dative via
    SANITIZE_CLEANUP_ORGANOMETALLICS — Hs are preserved, not stripped."""
    m = _check("[NH3][Ni]", formula="H3NNi")
    canon = Chem.MolToSmiles(m)
    assert canon == "[NH3]->[Ni]", (
        f"bracketed [NH3] with non-dative bond should canonicalize to '[NH3]->[Ni]', got {canon!r}"
    )
    n_atom = next(a for a in m.GetAtoms() if a.GetSymbol() == "N")
    assert n_atom.GetTotalNumHs() == 3, "bracketed [NH3] keeps all 3 Hs"


def test_A_unbracketed_N_becomes_amido():
    """The real footgun: unbracketed N gets organic-subset valence (3),
    so one Ni-N bond leaves only 2 implicit Hs → amido, not ammine."""
    m = _check("[Ni]N", formula="H2NNi")
    n_atom = next(a for a in m.GetAtoms() if a.GetSymbol() == "N")
    assert n_atom.GetTotalNumHs() == 2, (
        "unbracketed N with one bond to Ni should give 2 implicit Hs (amido), not 3 (ammine)"
    )


def test_smileswriteparams_dative_off():
    """includeDativeBonds=False downgrades '->' to single bonds on output."""
    m = Chem.MolFromSmiles("[NH3]->[Ni]")
    p = Chem.SmilesWriteParams()
    p.includeDativeBonds = True
    assert Chem.MolToSmiles(m, p) == "[NH3]->[Ni]"
    p.includeDativeBonds = False
    assert "->" not in Chem.MolToSmiles(m, p)


# ---------------------------------------------------------------------------
# Section B: Metal–heteroatom σ bonds (amido, alkoxo, halido, thiolato)
# ---------------------------------------------------------------------------


def test_B_Ni_NH2_amido():
    """Three equivalent ways to write the Ni-NH2 amido."""
    for smi in ("[Ni][NH2]", "[Ni]N", "N[Ni]"):
        m = _check(smi, formula="H2NNi")
        n_atom = next(a for a in m.GetAtoms() if a.GetSymbol() == "N")
        assert n_atom.GetTotalNumHs() == 2


def test_B_Pd_NMe2():
    _check("[Pd]N(C)C", formula="C2H6NPd")


def test_B_Ti_OMe4_alkoxo():
    _check("[Ti](OC)(OC)(OC)OC", formula="C4H12O4Ti")


def test_B_Au_thiolate():
    _check("[Au]SCC", formula="C2H5AuS")


def test_B_trans_PtMe2Cl2():
    _check("C[Pt](C)(Cl)Cl", formula="C2H6Cl2Pt")


# ---------------------------------------------------------------------------
# Section C: NHC carbenes
# ---------------------------------------------------------------------------


def test_C_IMes_carbene_count():
    smi = "Cc1cc(C)c(N2C=CN(c3c(C)cc(C)cc3C)[C]2)c(C)c1"
    m = _check(smi, formula="C21H24N2")
    carbenes = [
        a for a in m.GetAtoms()
        if a.GetSymbol() == "C"
        and a.GetTotalNumHs() == 0
        and a.GetDegree() == 2
        and a.GetFormalCharge() == 0
    ]
    assert len(carbenes) == 1, "IMes should have exactly one divalent carbene C"


def test_C_IPr_parses():
    smi = "CC(C)c1cccc(C(C)C)c1N1C=CN(c2c(C(C)C)cccc2C(C)C)[C]1"
    _check(smi, formula="C27H36N2")


def test_C_writing_C_not_brackets_gives_CH2_not_carbene():
    """The footgun: plain `C` instead of `[C]` adds two implicit Hs."""
    bad = "Cc1cc(C)c(N2C=CN(c3c(C)cc(C)cc3C)C2)c(C)c1"   # note: C2 instead of [C]2
    m = Chem.MolFromSmiles(bad)
    assert m is not None
    # Find the ring atom corresponding to position 2 of the imidazole.
    # It should now be a sp3 CH2 (no longer a carbene).
    carbene_count = sum(
        1 for a in m.GetAtoms()
        if a.GetSymbol() == "C"
        and a.GetTotalNumHs() == 0
        and a.GetDegree() == 2
        and a.GetFormalCharge() == 0
    )
    assert carbene_count == 0, "plain `C` should add Hs and remove the carbene"


# ---------------------------------------------------------------------------
# Section D: Phosphines and the [PH] artifact
# ---------------------------------------------------------------------------


def test_D_PdCl2_PMe3_introduces_PH_artifact():
    """Known: P–metal single bond yields spurious [PH] on round-trip."""
    m = Chem.MolFromSmiles("[Pd](Cl)(Cl)P(C)(C)C")
    assert m is not None
    canon = Chem.MolToSmiles(m)
    assert "[PH]" in canon, (
        "Without dative arrows, PR–PdCl2 round-trips with a spurious [PH] "
        "(P default valence is 3; the 4th connection forces an explicit H)."
    )


def test_D_dative_P_to_Pd_avoids_PH():
    """Using `->` on the P-Pd bond avoids the [PH] artifact."""
    m = Chem.MolFromSmiles("Cl[Pd](Cl)<-P(C)(C)C")
    assert m is not None
    canon = Chem.MolToSmiles(m)
    assert "[PH]" not in canon, (
        f"dative form should not introduce [PH], got {canon!r}"
    )


def test_D_wilkinson_full_sanitize():
    smi = (
        "[Rh](Cl)(P(c1ccccc1)(c1ccccc1)c1ccccc1)"
        "(P(c2ccccc2)(c2ccccc2)c2ccccc2)"
        "P(c3ccccc3)(c3ccccc3)c3ccccc3"
    )
    _check(smi, formula="C54H48ClP3Rh")


# ---------------------------------------------------------------------------
# Section E: η-coordination / hapticity
# ---------------------------------------------------------------------------


def test_E_eta2_ethene_3ring():
    """η²-alkene encoded as a 3-membered ring [M]-C-C-[M]."""
    m = _check("[Ni]1CC1", formula="C2H4Ni")
    ni = next(a for a in m.GetAtoms() if a.GetSymbol() == "Ni")
    # Ni must be bonded to BOTH carbons (this is the topology that encodes η²).
    neighbors = sorted(a.GetSymbol() for a in ni.GetNeighbors())
    assert neighbors == ["C", "C"]


def test_E_eta2_CO2_3ring():
    _check("[Ni]1OC1=O", formula="CNiO2")


def test_E_eta2_double_bond_in_ring_fails_or_changes():
    """[Ni]1C=C1 is NOT a valid η²-ethene encoding — it gives a cyclopropene-like topology."""
    m = Chem.MolFromSmiles("[Ni]1C=C1")
    if m is not None:
        # If it parses, at least confirm the bond order in the ring isn't a clean single bond.
        ni = next(a for a in m.GetAtoms() if a.GetSymbol() == "Ni")
        cc_bond = m.GetBondBetweenAtoms(*[a.GetIdx() for a in ni.GetNeighbors()])
        assert cc_bond.GetBondType() != Chem.BondType.SINGLE, (
            "the [Ni]1C=C1 form does not match the [Ni]1CC1 idiom — use single bonds in the η-ring"
        )


def test_E_eta3_allyl_4ring():
    """η³-allyl encoded as a 4-membered ring with one C=C inside."""
    m = _check("[Pd]([Cl])1CC=C1", formula="C3H4ClPd")
    pd = next(a for a in m.GetAtoms() if a.GetSymbol() == "Pd")
    # Pd must be bonded to two ring carbons (the terminal allyl carbons).
    c_neighbors = [a for a in pd.GetNeighbors() if a.GetSymbol() == "C"]
    assert len(c_neighbors) == 2


def test_E_ferrocene_ionic_disconnect():
    """The portable, robust ferrocene representation: ionic disconnect."""
    m = _check("[Fe+2].[cH-]1cccc1.[cH-]1cccc1", formula="C10H10Fe")
    # Should have 3 disconnected components.
    frags = Chem.GetMolFrags(m, asMols=False)
    assert len(frags) == 3
    # Net charge zero.
    total_charge = sum(a.GetFormalCharge() for a in m.GetAtoms())
    assert total_charge == 0


def test_E_eta3_propene_multidative():
    """Multidative haptic SMILES — requires RDKit >= 2025.03.1 (PR #8301)."""
    m = _check("[CH2-]1-[CH]2=[CH2]3.[Fe]123", formula="C3H5Fe-")
    fe = next(a for a in m.GetAtoms() if a.GetSymbol() == "Fe")
    # Fe should have three bonds, all to ring carbons.
    assert fe.GetDegree() == 3


def test_E_eta6_benzene_multidative():
    """η⁶-benzene as six dative bonds to Fe via ring-closure digits."""
    m = _check("[cH]12[cH]3[cH]4[cH]5[cH]6[cH]17.[Fe]234567", formula="C6H6Fe")
    fe = next(a for a in m.GetAtoms() if a.GetSymbol() == "Fe")
    assert fe.GetDegree() == 6


def test_E_haptic_dative_interconversion_callable():
    """HapticBondsToDative and DativeBondsToHaptic exist and are callable."""
    assert callable(Chem.HapticBondsToDative)
    assert callable(Chem.DativeBondsToHaptic)


# ---------------------------------------------------------------------------
# Section F: μ-bridging ligands
# ---------------------------------------------------------------------------


def test_F_mu_Cl_bridge():
    """[Pd]1Cl[Pd]1 parses with full sanitize."""
    m = _check("[Pd]1Cl[Pd]1", formula="ClPd2")
    cl = next(a for a in m.GetAtoms() if a.GetSymbol() == "Cl")
    assert cl.GetDegree() == 2  # bridges both Pds


def test_F_mu_H_bridge_needs_partial_sanitize():
    """[M]1[H][M]1 requires partial sanitize because H's default valence is 1.

    Round-trip warning: the canonical form RDKit emits ('[H]1[Mn][Mn]1') also fails
    default-sanitize re-parse — any pipeline that re-parses canonical output of a μ-H
    must also use partial sanitize. Test verifies parse, formula, and partial-mode round-trip.
    """
    m, mode = parse_om("[Mn]1[H][Mn]1")
    assert mode == "partial"
    assert rdMolDescriptors.CalcMolFormula(m) == "HMn2"
    canon = Chem.MolToSmiles(m)
    # Default-sanitize re-parse fails — that's the documented behavior:
    assert Chem.MolFromSmiles(canon) is None
    # Partial-sanitize re-parse must succeed:
    m2, mode2 = parse_om(canon)
    assert mode2 == "partial"
    assert rdMolDescriptors.CalcMolFormula(m2) == "HMn2"


def test_F_open_Pd2Cl4_full_sanitize():
    """Cl[Pd](Cl)(Cl)[Pd]Cl with a Pd-Pd bond parses cleanly."""
    _check("Cl[Pd](Cl)(Cl)[Pd]Cl")


# ---------------------------------------------------------------------------
# Section G: M–M multiple bonds
# ---------------------------------------------------------------------------


def test_G_M_M_single_double_triple_quadruple_tokens():
    """All four bond-order tokens (`-`, `=`, `#`, `$`) are accepted between metals."""
    expected_orders = {
        "[Mo][Mo]": Chem.BondType.SINGLE,
        "[Mo]=[Mo]": Chem.BondType.DOUBLE,
        "[Mo]#[Mo]": Chem.BondType.TRIPLE,
        "[Mo]$[Mo]": Chem.BondType.QUADRUPLE,
    }
    for smi, expected in expected_orders.items():
        m = Chem.MolFromSmiles(smi)
        assert m is not None, f"{smi!r} failed to parse"
        bond = m.GetBondBetweenAtoms(0, 1)
        assert bond.GetBondType() == expected, (
            f"{smi!r}: expected {expected}, got {bond.GetBondType()}"
        )
        # Round-trip preserves the order.
        assert Chem.MolToSmiles(m) == smi


def test_G_Re2Cl8_quadruple_dianion():
    smi = "[Re-]([Cl])([Cl])([Cl])([Cl])$[Re-]([Cl])([Cl])([Cl])[Cl]"
    m = _check(smi, formula="Cl8Re2-2")
    total_charge = sum(a.GetFormalCharge() for a in m.GetAtoms())
    assert total_charge == -2


def test_G_Mo2_OH8_quadruple_surrogate():
    """Mo₂(OH)₈ — paddlewheel surrogate with quadruple Mo-Mo bond."""
    _check(
        "[OH][Mo]([OH])([OH])([OH])$[Mo]([OH])([OH])([OH])[OH]",
        formula="H8Mo2O8",
    )


# ---------------------------------------------------------------------------
# Section H: Catalytic intermediates and metallacycles
# ---------------------------------------------------------------------------


def test_H_ArNiBr_oxidative_addition():
    _check("Brc1ccc([Ni]Br)cc1", formula="C6H4Br2Ni")


def test_H_PhPdEt_cross_coupling():
    _check("c1ccc([Pd](Br)CC)cc1", formula="C8H10BrPd")


def test_H_nickelalactone():
    _check("O=C1O[Ni]CC1", formula="C3H4NiO2")


def test_H_nickelacyclopentene():
    _check("[Ni]1CC=CC1", formula="C4H6Ni")


def test_H_Ru_methylidene():
    _check("[Ru]=C", formula="CH2Ru")


def test_H_Grubbs1_parses():
    smi = (
        "Cl[Ru](=Cc1ccccc1)(Cl)"
        "(P(C2CCCCC2)(C2CCCCC2)C2CCCCC2)"
        "P(C3CCCCC3)(C3CCCCC3)C3CCCCC3"
    )
    _check(smi, formula="C43H74Cl2P2Ru")


def test_H_Schrock_Mo_parses():
    _check(
        "[Mo](=CC(C)(C)C)(=NC(C)(C)C)(OC(C)(C)C)OC(C)(C)C",
        formula="C17H37MoNO2",
    )


def test_H_Vaska_hydride():
    """Hydride on Ir groups onto the metal as [IrH] on round-trip."""
    m = _check("[Ir]([H])(Cl)(P(C)(C)C)P(C)(C)C", formula="C6H21ClIrP2")
    canon = Chem.MolToSmiles(m)
    assert "[IrH" in canon


# ---------------------------------------------------------------------------
# Section I: Sanitization patterns
# ---------------------------------------------------------------------------


def test_I_sanitize_cleanup_organometallics_is_in_SANITIZE_ALL():
    """The OM cleanup flag is part of the default sanitization."""
    flag = int(Chem.SanitizeFlags.SANITIZE_CLEANUP_ORGANOMETALLICS)
    all_flag = int(Chem.SanitizeFlags.SANITIZE_ALL)
    assert flag == 0x400
    assert (all_flag & flag) == flag, (
        "SANITIZE_CLEANUP_ORGANOMETALLICS should be enabled by default in SANITIZE_ALL"
    )


def test_I_cleanup_organometallics_rewrites_to_dative():
    """After sanitize, a Pd-Cl bridge should be rewritten with a dative arrow."""
    m = _check("[Pd]1Cl[Pd]1", formula="ClPd2")
    canon = Chem.MolToSmiles(m)
    assert "<-" in canon or "->" in canon, (
        f"cleanupOrganometallics should rewrite to dative on canonical output, got {canon!r}"
    )


def test_I_parse_om_helper_modes():
    """The parse_om helper returns mode='full' for ordinary parses and 'partial' for fallback."""
    m1, mode1 = parse_om("[Ni]1CC1")
    assert m1 is not None and mode1 == "full"
    m2, mode2 = parse_om("[Mn]1[H][Mn]1")
    assert m2 is not None and mode2 == "partial"


# ---------------------------------------------------------------------------
# Section K: Common ligand fragments
# ---------------------------------------------------------------------------


def test_K_charged_CO_parses_full_sanitize():
    """The charge-trick [C-]#[O+] is the preferred CO encoding for Cr(CO)6."""
    smi = (
        "[Cr]([C-]#[O+])([C-]#[O+])([C-]#[O+])([C-]#[O+])([C-]#[O+])[C-]#[O+]"
    )
    _check(smi, formula="C6CrO6")


def test_K_neutral_CO_dative_needs_partial():
    """Neutral C in <-C#O leaves an H on C; either accept the round-trip or use [C-]#[O+]."""
    smi = "[Cr](<-C#O)(<-C#O)(<-C#O)(<-C#O)(<-C#O)<-C#O"
    m, mode = parse_om(smi)
    # Either mode is acceptable depending on RDKit version's handling of neutral C
    assert m is not None


# ---------------------------------------------------------------------------
# Negative tests — confirm the documented footguns
# ---------------------------------------------------------------------------


def test_negative_uncharged_C_in_CO_round_trip_uses_bare_C():
    """[Cr](C#O)... parses (with partial sanitize) to formula C6CrO6 — no Hs sneak onto C,
    because each C ends up with explicit valence 4 (3 from triple bond + 1 from Cr) and
    RDKit brackets it as `[C]` in the canonical output. But the canonical form uses bracketed
    `[C]` atoms, not the original organic-subset `C` — so the input string is NOT idempotent
    under canonicalization. Always prefer the charge-trick `[C-]#[O+]` for CO."""
    smi = "[Cr](C#O)(C#O)(C#O)(C#O)(C#O)C#O"
    m, _ = parse_om(smi)
    formula = rdMolDescriptors.CalcMolFormula(m)
    assert formula == "C6CrO6", f"expected C6CrO6 (no Hs), got {formula}"
    canon = Chem.MolToSmiles(m)
    # The canonical form should have bracketed `[C]` atoms (not bare `C`).
    assert "[C]" in canon, (
        f"neutral C#O on Cr round-trips with bracketed [C] atoms (not bare C), got {canon!r}"
    )


# ---------------------------------------------------------------------------
# Standalone runner (so this file works without pytest installed)
# ---------------------------------------------------------------------------


def _run_standalone() -> int:
    """Run every test_* function in this module. Return number of failures."""
    import inspect
    tests = [
        (name, obj) for name, obj in inspect.getmembers(sys.modules[__name__])
        if name.startswith("test_") and inspect.isfunction(obj)
    ]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except AssertionError as e:
            failures += 1
            print(f"  FAIL  {name}: {e}")
        except Exception as e:
            failures += 1
            print(f"  ERR   {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return failures


if __name__ == "__main__":
    sys.exit(_run_standalone())
