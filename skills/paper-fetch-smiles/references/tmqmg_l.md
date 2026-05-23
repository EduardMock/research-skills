# tmQMg-L dataset reference

**tmQMg-L** is the ligand-centric cut of the **tmQMg** dataset (which is itself a graph-featurized extension of **tmQM** — Cambridge Structural Database–derived transition-metal complexes with DFT properties). It exposes ~30k unique ligands, each one extracted from a real, crystallographically characterized transition-metal complex, annotated with denticity, charge, donor-atom indices, and DFT descriptors.

| Dataset | Content | Size |
|---|---|---|
| **tmQM** | Mononuclear TMCs from CSD with DFT properties (HOMO, LUMO, gap, dipole, polarizability, charges). | ~86k complexes |
| **tmQMg** | Graph-featurized tmQM. | ~61k complexes |
| **tmQMg-L** | Unique ligands extracted from tmQMg TMCs. | ~30k ligands |

References:
- tmQM: Balcells & Skjelstad, *J. Chem. Inf. Model.* **2020**, 60, 6135.
- tmQMg / tmQMg-L: Kneiding et al., *Dalton Trans.* 2023; repo at `github.com/hkneiding/tmQMg-L` (redirects to `github.com/uiocompcat/tmQMg-L`).

## Why it's useful

- Real geometries, not toy SMILES. Donor atoms are known.
- Comes with DFT descriptors — useful for ranking/screening without recomputation.
- Open source, no CCDC license needed.

## File layout (on GitHub)

| File | Size | Description |
|---|---|---|
| `ligands_misc_info.csv` | ~19 MB | Main metadata: ligand id, SMILES, stoichiometry, occurrence, donor atoms, denticity, charge. **Used by this skill.** |
| `ligands_fingerprints.csv` | ~4 MB | NBO formal charge, per-element atom counts, alt-charge flags. |
| `ligands_descriptors.csv` | ~19 MB | RDKit/steric/electronic descriptors. Rows split into `L*` (stable conformer) vs `L_free` (gas-phase optimized). |
| `xyz/ligand_*.xyz` | 30–90 MB each | Multi-XYZ files; ligand ID in the comment line of each block. |

Raw URL pattern (this skill builds these):

    https://raw.githubusercontent.com/hkneiding/tmQMg-L/{sha}/{path}

Set `sha` to a commit hash for reproducibility; `main` is the default.

## Column-naming caveats

Schemas have evolved across releases (`v60k`, `v74k`). The client tolerates a few variants:

- SMILES column: `smiles` / `SMILES` / `smiles_metal_bound`
- InChIKey column: `inchikey` / `InChIKey` / `inchi_key`
- ID column: `ligand_id` / `id` / `name`

If you're matching against a specific release, pin the SHA and confirm column names in the on-disk CSV.

## Denticity is **observational**, not intrinsic

tmQMg-L's denticity is from the *source TMC*. The same ligand can bind differently in a different complex — e.g., a P,P bidentate observed as monodentate elsewhere. Don't assume the value transfers.

## Releases & sizes

Two tagged releases exist (`v60k`, `v74k`) but neither has uploaded release assets. Either:
- Fetch per-file via the raw URLs above (this skill's approach, light).
- Whole-repo tarball: `https://github.com/hkneiding/tmQMg-L/archive/refs/heads/main.tar.gz` (~190 MB).

## Related ligand datasets

For phosphines specifically, **Kraken** (Gensch et al., *Nat. Comput. Sci.* 2022) ships precomputed steric descriptors (%Vbur, cone angle, TEP) that tmQMg-L doesn't. For NHCs, the analogous dataset is **OSCAR**. This skill currently only knows about tmQMg-L — those would be future additions.
