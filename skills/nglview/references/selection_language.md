# NGLView Selection Language Reference

Complete reference for the NGL selection syntax used in NGLView for targeting atoms in small molecules, catalysts, and complexes.

## Overview

NGLView uses NGL's powerful selection language to specify which atoms to visualize or manipulate. For small molecule chemistry, the most common selections involve elements (metals, carbons), molecule names, atom indices, and distance-based selections around reactive centers.

## Basic Syntax

### Selection Format

```python
view.add_representation(repr_type, selection='<selection_expression>')
```

**Examples**:
```python
view.add_cartoon(selection='protein')
view.add_licorice(selection='50-60')
view.add_surface(selection=':A and protein')
```

## Keyword Selectors

### Molecule Type Keywords

```python
# Proteins
view.add_cartoon(selection='protein')

# Nucleic acids (DNA/RNA)
view.add_cartoon(selection='nucleic')

# Ions
view.add_spacefill(selection='ion')

# Water molecules
view.add_point(selection='water')

# Ligands (HETATM records)
view.add_ball_and_stick(selection='ligand')

# Hetero atoms (non-standard residues)
view.add_licorice(selection='hetero')

# Small molecules
view.add_ball_and_stick(selection='small')

# Polymers
view.add_cartoon(selection='polymer')
```

### Common Combinations

```python
# Protein without water
view.add_cartoon(selection='protein and not water')

# All hetero except water
view.add_licorice(selection='hetero and not water')

# Nucleic and protein
view.add_cartoon(selection='nucleic or protein')
```

## Residue Selection

### By Residue Number

```python
# Single residue
view.add_licorice(selection='50')

# Residue range
view.add_licorice(selection='50-60')
view.add_licorice(selection='1-100')

# Multiple ranges (space-separated)
view.add_licorice(selection='10-20 50-60 90-100')

# Negative residue numbers
view.add_licorice(selection='-5--1')  # Residues -5 to -1

# Insertion codes
view.add_licorice(selection='27A-27E')
```

### By Residue Name (Three-Letter Code)

```python
# Single residue type
view.add_licorice(selection='ALA')  # All alanines

# Multiple residue types
view.add_licorice(selection='GLU or ASP')  # Acidic residues
view.add_licorice(selection='LYS or ARG')  # Basic residues

# Aromatic residues
view.add_licorice(selection='PHE or TYR or TRP')

# Hydrophobic residues
view.add_licorice(selection='ALA or VAL or LEU or ILE or MET or PHE or TRP or PRO')
```

### Common Residue Groups

```python
# Charged residues
charged = 'GLU or ASP or LYS or ARG or HIS'
view.add_licorice(selection=charged)

# Polar residues
polar = 'SER or THR or ASN or GLN or TYR or CYS'
view.add_licorice(selection=polar)

# Aromatic residues
aromatic = 'PHE or TYR or TRP or HIS'
view.add_licorice(selection=aromatic)

# Small residues
small = 'GLY or ALA or SER'
view.add_licorice(selection=small)
```

## Chain Selection

### By Chain Identifier

```python
# Single chain
view.add_cartoon(selection=':A')

# Multiple chains
view.add_cartoon(selection=':A or :B')

# All except specific chain
view.add_cartoon(selection='not :C')

# Chain with residue range
view.add_cartoon(selection=':A and 1-50')
```

### Chain Combinations

```python
# Different representations for different chains
view.add_cartoon(selection=':A', color='blue')
view.add_cartoon(selection=':B', color='red')

# Interface between chains
view.add_licorice(selection='(:A and 10 within :B) or (:B and 10 within :A)')
```

## Atom Selection

### By Atom Name

```python
# C-alpha atoms
view.add_spacefill(selection='.CA')

# Backbone atoms
view.add_licorice(selection='.N or .CA or .C or .O')

# Specific atom names
view.add_spacefill(selection='.CB')  # Beta carbons

# Multiple atom types
view.add_licorice(selection='.N or .O')  # Nitrogen and oxygen
```

### By Element

```python
# Carbon atoms
view.add_spacefill(selection='_C')

# Nitrogen atoms
view.add_spacefill(selection='_N')

# Oxygen atoms
view.add_spacefill(selection='_O')

# Sulfur atoms
view.add_spacefill(selection='_S')

# Metals
view.add_spacefill(selection='_FE or _ZN or _MG')
```

### Atom Properties

```python
# Hydrogen atoms
view.add_line(selection='hydrogen')

# Non-hydrogen atoms
view.add_licorice(selection='not hydrogen')

# Heavy atoms (non-hydrogen)
view.add_spacefill(selection='not hydrogen')

# Backbone atoms
view.add_licorice(selection='backbone')

# Sidechain atoms
view.add_licorice(selection='sidechain')
```

## Boolean Operations

### AND

```python
# Protein in chain A
view.add_cartoon(selection='protein and :A')

# Residues 50-60 in chain A
view.add_licorice(selection='50-60 and :A')

# C-alpha atoms of protein
view.add_spacefill(selection='protein and .CA')

# Aromatic residues in binding site
view.add_licorice(selection='(PHE or TYR or TRP) and 50-75')
```

### OR

```python
# Multiple chains
view.add_cartoon(selection=':A or :B or :C')

# Multiple residues
view.add_licorice(selection='50 or 55 or 60')

# Multiple residue types
view.add_licorice(selection='GLU or ASP or LYS or ARG')
```

### NOT

```python
# Protein without water
view.add_cartoon(selection='protein and not water')

# All except chain A
view.add_cartoon(selection='not :A')

# Heavy atoms (no hydrogens)
view.add_licorice(selection='not hydrogen')

# Hetero atoms except water
view.add_licorice(selection='hetero and not water')
```

### Complex Boolean Expressions

```python
# Use parentheses for grouping
view.add_licorice(
    selection='(protein and :A) or (ligand and :B)'
)

# Multiple conditions
view.add_licorice(
    selection='protein and not (water or ion) and :A'
)

# Aromatic residues in active site
view.add_licorice(
    selection='(PHE or TYR or TRP) and 50-75 and :A'
)
```

## Distance-Based Selection

### Within Distance

```python
# Atoms within 5 Å of ligand
view.add_licorice(selection='5 within ligand')

# Protein residues within 10 Å of residue 50
view.add_licorice(selection='protein and 10 within 50')

# Water within 3 Å of protein
view.add_point(selection='water and 3 within protein')

# Binding site (within distance of ligand)
view.add_licorice(selection='protein and 4 within ligand')

# Interface residues
view.add_licorice(selection=':A and 5 within :B')
```

### Specific Distance Examples

```python
# First shell (direct contacts, < 4 Å)
view.add_licorice(selection='protein and 4 within ligand')

# Second shell (4-8 Å)
view.add_licorice(
    selection='protein and 8 within ligand and not 4 within ligand'
)

# Long-range contacts (5-10 Å)
view.add_line(selection='10 within ligand and not 5 within ligand')

# Solvation shell around protein
view.add_point(selection='water and 3.5 within protein')
```

## Model Selection

```python
# Specific model (NMR structures, trajectories)
view.add_cartoon(selection='/0')  # Model 0

# Multiple models
view.add_cartoon(selection='/0 or /1')

# All models
view.add_cartoon(selection='*')  # Default
```

## Alternate Location Selection

```python
# Specific alternate location
view.add_licorice(selection='%A')  # Alt loc A

# Multiple alternate locations
view.add_licorice(selection='%A or %B')
```

## Special Selections

### Backbone and Sidechain

```python
# Backbone atoms
view.add_licorice(selection='backbone')
view.add_licorice(selection='.N or .CA or .C or .O')  # Equivalent

# Sidechain atoms
view.add_licorice(selection='sidechain')

# Sidechains of specific residues
view.add_licorice(selection='sidechain and 50-60')
```

### Secondary Structure

```python
# Helices
view.add_cartoon(selection='helix')

# Sheets
view.add_cartoon(selection='sheet')

# Turns
view.add_cartoon(selection='turn')

# Coils
view.add_cartoon(selection='coil')
```

### Atom Index

```python
# Select by atom index
view.add_spacefill(selection='@100')  # Atom index 100

# Multiple atom indices
view.add_spacefill(selection='@10 or @20 or @30')

# Atom range
view.add_spacefill(selection='@10-100')
```

## Selection by List (Python)

For programmatic selection, pass atom indices as a list:

```python
# Select specific atom indices
atom_indices = [10, 25, 50, 75, 100]
view.add_licorice(selection=atom_indices, color='red')

# Select from numpy array
import numpy as np
ca_indices = np.where(atom_names == 'CA')[0]
view.add_spacefill(selection=ca_indices.tolist())

# Dynamic selection based on property
high_bfactor = [i for i, b in enumerate(bfactors) if b > 50]
view.add_spacefill(selection=high_bfactor, color='red')
```

## Practical Examples

### Visualize Binding Site

```python
# Show protein and binding site
view.clear_representations()

# Protein cartoon
view.add_cartoon(selection='protein', color='secondary structure')

# Binding site residues (within 5 Å of ligand)
view.add_licorice(
    selection='protein and 5 within ligand',
    color='element'
)

# Ligand as ball and stick
view.add_ball_and_stick(selection='ligand', color='cyan')

# Center on binding site
view.center(selection='ligand')
```

### Protein-Protein Interface

```python
# Show interface between chain A and B
view.clear_representations()

# Both proteins as cartoon
view.add_cartoon(selection=':A', color='blue')
view.add_cartoon(selection=':B', color='red')

# Interface residues from chain A (within 5 Å of chain B)
view.add_licorice(
    selection=':A and 5 within :B',
    color='blue'
)

# Interface residues from chain B (within 5 Å of chain A)
view.add_licorice(
    selection=':B and 5 within :A',
    color='red'
)

# Center on interface
view.center(selection=':A and 5 within :B')
```

### Active Site with Key Residues

```python
# Catalytic triad (Ser-His-Asp)
view.clear_representations()

# Protein as cartoon
view.add_cartoon(selection='protein', color='grey', opacity=0.3)

# Catalytic triad
view.add_licorice(selection='195 or 57 or 102', color='element')

# Label catalytic residues
view.add_label(selection='195 or 57 or 102', label_type='residue')

# Substrate/ligand
view.add_ball_and_stick(selection='ligand', color='cyan')

# Center on active site
view.center(selection='195 or 57 or 102 or ligand')
```

### Membrane Protein

```python
# Transmembrane protein with lipids
view.clear_representations()

# Protein cartoon
view.add_cartoon(selection='protein', color='hydrophobicity')

# Lipid headgroups
view.add_spacefill(selection='lipid and (.P or .N)', opacity=0.5)

# Lipid tails
view.add_line(selection='lipid and not (.P or .N)')

# Water near protein
view.add_point(selection='water and 3 within protein', pointSize=1)
```

### DNA-Protein Complex

```python
# Transcription factor bound to DNA
view.clear_representations()

# Protein
view.add_cartoon(selection='protein', color='blue')

# DNA backbone
view.add_cartoon(selection='nucleic', color='red')

# DNA bases
view.add_base(selection='nucleic', color='element')

# Protein-DNA interface
view.add_licorice(
    selection='protein and 5 within nucleic',
    color='element'
)

# Center on complex
view.center(selection='all')
```

### Highlighting Mutations

```python
# Show wild-type and mutant positions
view.clear_representations()

# Protein cartoon
view.add_cartoon(selection='protein', color='grey')

# Wild-type residues (in blue)
wild_type_positions = '45 or 67 or 89'
view.add_spacefill(
    selection=wild_type_positions,
    color='blue',
    opacity=0.5
)

# Mutant residues (in red)
mutant_positions = '46 or 68 or 90'
view.add_spacefill(
    selection=mutant_positions,
    color='red',
    opacity=0.5
)

# Show sidechains
view.add_licorice(
    selection=f'{wild_type_positions} or {mutant_positions}',
    color='element'
)
```

## Selection Tips

### 1. Case Sensitivity
- Keywords are **case-insensitive**: `protein`, `PROTEIN`, and `Protein` all work
- Atom names are **case-sensitive**: `.CA` (C-alpha) ≠ `.Ca` (calcium)
- Chain IDs are **case-sensitive**: `:A` ≠ `:a`

### 2. Spaces in Selections
- Spaces separate multiple ranges: `'10-20 50-60'` means residues 10-20 OR 50-60
- Use explicit `or` for clarity: `'10-20 or 50-60'`

### 3. Parentheses for Grouping
- Use parentheses with complex boolean logic
- Example: `'(protein and :A) or (ligand and :B)'`

### 4. Distance Selections
- Units are in Ångströms (Å)
- Distance is measured from any atom in the selection
- Use `within` keyword: `'5 within ligand'`

### 5. Performance
- More specific selections render faster
- Use `'not hydrogen'` to exclude hydrogens for better performance
- Combine keywords when possible: `'protein and :A'` is more efficient than applying post-filters

## Common Pitfalls

### 1. Forgotten Dots for Atom Names
```python
# Wrong
view.add_spacefill(selection='CA')  # Selects residue CA, not C-alpha atoms

# Correct
view.add_spacefill(selection='.CA')  # C-alpha atoms
```

### 2. Missing Quotes
```python
# Wrong
view.add_cartoon(selection=protein)  # Python error

# Correct
view.add_cartoon(selection='protein')
```

### 3. Residue Range with Insertions
```python
# For insertion codes, be explicit
view.add_licorice(selection='27 or 27A or 27B or 28')

# Or use ranges if sequential
view.add_licorice(selection='27-28')  # May not include insertions
```

### 4. Chain Selection Confusion
```python
# Wrong: Selects residues, not chains
view.add_cartoon(selection='A')  # Residue named 'A' (if exists)

# Correct: Colon prefix for chains
view.add_cartoon(selection=':A')
```

### 5. Distance Selection Order
```python
# Order matters with 'within'
# This selects water atoms within 5Å of protein:
view.add_point(selection='water and 5 within protein')

# This selects protein atoms within 5Å of water (different!):
view.add_licorice(selection='protein and 5 within water')
```

## Selection Validation

Test your selections before adding representations:

```python
# Get selection info
selection = 'protein and 5 within ligand'

# This will show how many atoms match
# (implementation depends on backend)
# For MDTraj:
import mdtraj as md
traj = md.load('structure.pdb')
atom_indices = traj.top.select(selection)
print(f"Selected {len(atom_indices)} atoms")
```

## Quick Reference Table

| Selection | Meaning |
|-----------|---------|
| `'protein'` | All protein atoms |
| `'nucleic'` | DNA/RNA atoms |
| `'ligand'` | Hetero atoms (ligands) |
| `'water'` | Water molecules |
| `'ion'` | Ions |
| `'50-60'` | Residues 50 to 60 |
| `':A'` | Chain A |
| `'.CA'` | C-alpha atoms |
| `'_C'` | Carbon atoms |
| `'not hydrogen'` | Heavy atoms |
| `'5 within ligand'` | Within 5Å of ligand |
| `'protein and :A'` | Protein in chain A |
| `'PHE or TYR or TRP'` | Aromatic residues |
| `'protein and not water'` | Protein without water |
| `'backbone'` | Backbone atoms (N,CA,C,O) |
| `'sidechain'` | Sidechain atoms |

This comprehensive reference covers all selection syntax patterns available in NGLView for precise molecular targeting.
