# MDAnalysis Selection Language Reference

Complete reference for MDAnalysis atom selection syntax for use with NGLView trajectory visualization and analysis.

## Overview

MDAnalysis provides a powerful selection language for querying atoms in molecular systems. This reference is essential when working with NGLView trajectories loaded via `view.add_trajectory(u)`, as selections are used for:
- Highlighting specific regions
- Calculating distances and coordination spheres
- Extracting subsets for visualization
- Defining representations

**Official Documentation**: https://docs.mdanalysis.org/1.1.0/documentation_pages/selections.html

## Basic Selection Keywords

### Macromolecular Selections

```python
# Protein-related (less common for small molecule catalysis)
protein              # All protein atoms
backbone             # Protein backbone atoms (N, CA, C)
nucleic              # All nucleic acid atoms
nucleicbackbone      # Nucleic acid backbone

# For small molecule/catalyst work, use element and name selections instead
```

### Atom Properties

```python
# By atom name
name CA              # Alpha carbons
name H*              # All hydrogens (wildcard)
name "C1'"           # Atom named C1' (quotes for special chars)

# By element (most useful for catalysts)
type C               # Carbon atoms (if type is element)
name Pd              # Palladium atoms
name Pt              # Platinum atoms
name Fe              # Iron atoms

# By residue
resname LIG          # Residue named LIG
resname MOL          # Residue named MOL
resname CAT          # Catalyst residue
resid 1:10           # Residues 1 through 10
resid 5              # Residue number 5
resnum 100           # Canonical residue number 100

# By segment
segid A              # Segment A
segid SYST           # Segment SYST
```

### Specific Atom Selection

```python
# Select single atom: atom <segid> <resid> <name>
atom SYST 1 Pd       # Pd atom in segment SYST, residue 1

# By index
bynum 1:100          # Atoms 1-100 (1-based indexing)
index 0:99           # Atoms 0-99 (0-based indexing)
```

## Pattern Matching (Wildcards)

MDAnalysis supports glob-style wildcards for flexible selections:

```python
# ? matches single character
name C?              # C1, C2, CA, CB, etc.
name H?              # H1, H2, HA, HB, etc.

# * matches multiple characters
name C*              # All atoms starting with C
resname GL*          # GLU, GLY, GLN, etc.
name *A              # All atoms ending with A

# [seq] matches any character in sequence
name C[123]          # C1, C2, or C3
name H[AB]           # HA or HB

# [!seq] matches characters NOT in sequence
name C[!12]          # Carbon atoms NOT named C1 or C2
```

### Examples for Small Molecules

```python
# All hydrogens
name H*

# All carbons (various naming conventions)
name C or name C*

# Metal centers
name Pd or name Pt or name Ru or name Fe

# Phosphorus atoms (phosphine ligands)
name P or name P*

# Coordinating nitrogen atoms
name N and name N[123]
```

## Boolean Operators

Combine selections with logical operators:

```python
# NOT - negation
not name H*                          # Non-hydrogen atoms
not resname SOL                      # Exclude solvent

# AND - intersection
name C and resname LIG               # Carbons in ligand
protein and not name H*              # Heavy atoms in protein

# OR - union
name Pd or name Pt                   # Palladium or platinum
resname LIG or resname CAT           # Multiple residues

# Parentheses for grouping
(name H* or name D*) and resname LIG # Hydrogens/deuteriums in ligand
```

### Complex Boolean Examples

```python
# Non-hydrogen heavy atoms
not name H*

# Exclude water and ions
not (resname WAT or resname SOL or resname NA or resname CL)

# Metal centers excluding specific elements
(name Fe or name Ru or name Os) and not resname HEM

# Aromatic carbons (by naming convention)
name C* and (resname PHE or resname TYR or resname TRP)
```

## Geometric Selections

Distance-based selections are crucial for coordination sphere analysis:

### Around Selection

Select atoms within a distance of a selection:

```python
# around <distance> <selection>
around 5.0 name Pd                   # Atoms within 5 Å of Pd
around 3.0 resname LIG               # Atoms within 3 Å of ligand
around 2.5 (name Pd or name Pt)      # Within 2.5 Å of any metal

# Coordination sphere
around 2.3 name Pd and not name Pd   # First coordination shell (exclude metal)
```

### Spherical Selections

```python
# sphzone <radius> <selection>
# Spherical zone centered on selection
sphzone 5.0 name Pd                  # Sphere of 5 Å around Pd

# sphlayer <inner> <outer> <selection>
# Spherical shell between two radii
sphlayer 2.5 5.0 name Pd             # Shell from 2.5 to 5.0 Å around Pd
sphlayer 2.3 4.0 name Ru             # Second coordination shell
```

### Cylindrical Selections

```python
# cyzone <radius> <zMax> <zMin> <selection>
# Cylindrical zone along z-axis
cyzone 5.0 10.0 -10.0 name Pd        # Cylinder radius 5 Å, height -10 to 10 Å

# cylayer <inner> <outer> <zMax> <zMin> <selection>
# Cylindrical shell
cylayer 3.0 6.0 10.0 -10.0 name Pd   # Shell from 3-6 Å radius
```

### Point-Based Selection

Select atoms near specific coordinates:

```python
# point <x> <y> <z> <distance>
point 10.0 5.0 0.0 3.0               # Atoms within 3 Å of (10, 5, 0)
```

### Property-Based Geometric Selections

```python
# prop [abs] <property> <operator> <value>
# property: x, y, z
# operator: <, >, <=, >=, ==, !=

prop x < 10.0                        # x-coordinate less than 10
prop abs z > 5.0                     # |z| > 5
prop y >= 0.0 and prop y <= 10.0     # y between 0 and 10
```

## Same Property Selections

Select atoms sharing properties with another selection:

```python
# same <property> as <selection>

# Available properties:
# - name, type, resname, resid, segid
# - mass, charge, radius, bfactor
# - resnum, residue, segment, fragment
# - x, y, z

same resname as name Pd              # All atoms in Pd-containing residue
same residue as name Pd              # Same as byres
same segid as resname LIG            # All atoms in ligand's segment
same fragment as name Pd             # All atoms in same fragment

# Useful for highlighting related atoms
same resname as (around 2.5 name Pd) # Residues in coordination sphere
```

## By-Residue Selections

Expand selection to include entire residues:

```python
# byres <selection>
byres name Pd                        # All atoms in Pd-containing residue
byres (around 5.0 name Pd)          # All residues within 5 Å
byres (name C1 or name C2)          # Residues containing C1 or C2
```

## Connectivity Selections

Select bonded atoms (requires bond information):

```python
# bonded <selection>
bonded name Pd                       # Atoms bonded to Pd
bonded (name C1)                     # Atoms bonded to C1

# Combined with other selections
bonded name P and not name H*        # Heavy atoms bonded to phosphorus
```

## Preexisting Group References

Reference previously defined AtomGroups:

```python
# In Python code:
import MDAnalysis as mda

u = mda.Universe('system.pdb')

# Define a group
metals = u.select_atoms('name Pd or name Pt or name Ru')

# Reference in later selections using 'group'
coord_sphere = u.select_atoms('around 2.5 group metals')
```

## Dynamic (Updating) Selections

For trajectory analysis, create selections that update each frame:

```python
import MDAnalysis as mda

u = mda.Universe('system.pdb', 'trajectory.xtc')

# Static selection (evaluated once)
metal = u.select_atoms('name Pd')

# Dynamic selection (re-evaluated each frame)
coord_atoms = u.select_atoms('around 2.5 name Pd', updating=True)

# Iterate through trajectory
for ts in u.trajectory:
    print(f"Frame {ts.frame}: {len(coord_atoms)} coordinating atoms")
```

## NGLView Integration Examples

### Example 1: Highlight Metal Coordination Sphere

```python
import MDAnalysis as mda
import nglview as nv

u = mda.Universe('catalyst.pdb')
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# Use MDAnalysis selection syntax in NGLView
view.add_spacefill(selection='name Pd', color='orange', radius=1.5)
view.add_licorice(selection='around 2.5 name Pd and not name Pd',
                  color='element', radius=0.35)
view.add_line(selection='not around 2.5 name Pd', color='grey', opacity=0.3)

view.center(selection='name Pd')
view
```

### Example 2: Multi-Shell Coordination

```python
import MDAnalysis as mda
import nglview as nv

u = mda.Universe('catalyst.pdb')
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# Metal center
view.add_spacefill(selection='name Ru', color='cyan', radius=1.5)

# First coordination shell (0-2.3 Å)
view.add_licorice(selection='around 2.3 name Ru and not name Ru',
                  color='element', radius=0.35)

# Second coordination shell (2.3-4.5 Å)
view.add_licorice(
    selection='around 4.5 name Ru and not around 2.3 name Ru',
    color='element', radius=0.2, opacity=0.6
)

# Distant atoms
view.add_line(selection='not around 4.5 name Ru',
              color='lightgrey', opacity=0.2)

view.center(selection='name Ru')
view
```

### Example 3: Ligand-Specific Highlighting

```python
import MDAnalysis as mda
import nglview as nv

u = mda.Universe('complex.pdb')
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# Metal center
view.add_spacefill(selection='name Pd', color='orange', radius=1.5)

# Phosphine ligands (P and bonded atoms)
view.add_licorice(selection='name P* or bonded name P*',
                  color='purple', radius=0.35)

# Nitrogen donors
view.add_ball_and_stick(selection='name N* and around 2.5 name Pd',
                        color='blue', aspectRatio=3.0)

# Halides
view.add_spacefill(selection='name Cl or name Br or name I',
                   color='green', radius=1.2)

view.center(selection='name Pd')
view
```

### Example 4: Exclude Solvent and Ions

```python
import MDAnalysis as mda
import nglview as nv

u = mda.Universe('solvated_system.pdb')
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# Define system without solvent
system = 'not (resname WAT or resname SOL or resname HOH or resname TIP3)'

# Catalyst without solvent
view.add_ball_and_stick(selection=f'{system} and resname CAT',
                        color='element')

# Show nearby water (within 5 Å)
view.add_line(selection='resname WAT and around 5.0 resname CAT',
              color='cyan', opacity=0.3)

view.center(selection='resname CAT')
view
```

### Example 5: Dynamic Coordination Analysis

```python
import MDAnalysis as mda
import nglview as nv
import numpy as np

u = mda.Universe('catalyst.pdb', 'dynamics.xtc')

# Create dynamic selection
metal = u.select_atoms('name Pd')
coord_atoms = u.select_atoms('around 2.5 name Pd and not name Pd',
                             updating=True)

# Analyze coordination number over trajectory
coord_numbers = []
for ts in u.trajectory:
    coord_numbers.append(len(coord_atoms))

print(f"Average coordination number: {np.mean(coord_numbers):.1f}")
print(f"Range: {np.min(coord_numbers)} - {np.max(coord_numbers)}")

# Visualize
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()
view.add_spacefill(selection='name Pd', color='orange', radius=1.5)
view.add_licorice(selection='around 2.5 name Pd', color='element')
view
```

## Common Selection Patterns for Catalysts

### Metal Centers

```python
# Single metal
'name Pd'
'name Pt'
'name Ru'
'name Fe'

# Multiple metals
'name Pd or name Pt'
'name Fe or name Co or name Ni'

# Metal with specific residue
'name Pd and resname CAT'
```

### Coordination Spheres

```python
# First coordination shell
'around 2.3 name Pd and not name Pd'  # Pd(II)
'around 2.2 name Ru and not name Ru'  # Ru(II)
'around 2.3 name Fe and not name Fe'  # Fe(II/III)

# Multiple shells
'around 4.0 name Pd'                  # Within 4 Å
'sphlayer 2.3 4.5 name Pd'           # Shell 2.3-4.5 Å
```

### Ligand Types

```python
# Phosphine ligands
'name P or name P*'
'name P* or bonded name P*'
'resname PPH3 or resname DPPB'

# Nitrogen-donor ligands
'name N and around 2.5 name Pd'
'resname BPY or resname PHEN'

# Carbon monoxide ligands
'name C and bonded name O and around 2.5 name Ru'

# Halide ligands
'name Cl or name Br or name I'
'(name Cl or name Br or name I) and around 2.5 name Pd'
```

### Non-Hydrogen Heavy Atoms

```python
# All heavy atoms
'not name H*'

# Heavy atoms in coordination sphere
'around 2.5 name Pd and not name H* and not name Pd'

# Heavy atoms in specific region
'not name H* and prop z > 0.0'
```

### Solvent Exclusion

```python
# Exclude water
'not resname WAT'
'not (resname WAT or resname SOL or resname HOH)'

# Exclude water and ions
'not (resname WAT or resname NA or resname CL or resname K)'

# System without solvent
'protein or resname LIG'  # Protein + ligand only
'not resname WAT and not resname NA and not resname CL'
```

## Performance Tips

1. **Avoid Redundant Selections**: Store frequently used selections as AtomGroups
   ```python
   metals = u.select_atoms('name Pd or name Pt')
   # Reuse: coord = u.select_atoms('around 2.5 group metals')
   ```

2. **Use Index Ranges for Large Systems**: More efficient than property-based
   ```python
   # Faster for contiguous ranges
   'index 0:1000'
   # vs
   'resid 1:100'  # (if residues are contiguous)
   ```

3. **Updating Selections**: Only use when necessary (trajectory analysis)
   ```python
   # Static (evaluated once)
   static_sel = u.select_atoms('name CA')

   # Dynamic (re-evaluated each frame)
   dynamic_sel = u.select_atoms('around 5.0 name CA', updating=True)
   ```

4. **Combine Geometric Selections**: More efficient than nested
   ```python
   # Efficient
   'around 5.0 name Pd and not name H*'

   # Less efficient (two passes)
   # sel1 = 'around 5.0 name Pd'
   # sel2 = sel1 + ' and not name H*'
   ```

## Selection Syntax Differences: MDAnalysis vs NGL

When using NGLView with MDAnalysis, be aware of syntax differences:

| Feature | MDAnalysis | NGL (in NGLView) |
|---------|------------|------------------|
| Element | `name Pd` | `_Pd` |
| Distance | `around 2.5 name Pd` | `2.5 within _Pd` |
| Residue | `resname LIG` | `LIG` (for resname) |
| NOT operator | `not` | `not` |
| AND operator | `and` | `and` |
| OR operator | `or` | `or` |

**Important**: When using `view.add_trajectory(u)` with an MDAnalysis Universe, NGLView accepts **MDAnalysis selection syntax** in the `selection` parameter, not NGL syntax. The NGL syntax only applies to structures loaded with `view.add_component('file.pdb')`.

```python
# Correct for MDAnalysis backend
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.add_licorice(selection='around 2.5 name Pd')  # MDAnalysis syntax

# Correct for file backend
view = nv.NGLWidget()
comp = view.add_component('structure.pdb')
view.add_licorice(selection='2.5 within _Pd')  # NGL syntax
```

## Quick Reference Table

| Selection Type | Syntax | Example |
|----------------|--------|---------|
| Element name | `name <name>` | `name Pd` |
| Residue name | `resname <name>` | `resname LIG` |
| Residue ID | `resid <range>` | `resid 1:10` |
| Distance | `around <dist> <sel>` | `around 2.5 name Pd` |
| Spherical shell | `sphlayer <in> <out> <sel>` | `sphlayer 2.5 5.0 name Pd` |
| Wildcard | `*` or `?` | `name C*` |
| Negation | `not <sel>` | `not name H*` |
| Union | `<sel1> or <sel2>` | `name Pd or name Pt` |
| Intersection | `<sel1> and <sel2>` | `name C and resname LIG` |
| Same property | `same <prop> as <sel>` | `same resname as name Pd` |
| By residue | `byres <sel>` | `byres name Pd` |
| Bonded | `bonded <sel>` | `bonded name P` |
| Index (0-based) | `index <range>` | `index 0:99` |
| Index (1-based) | `bynum <range>` | `bynum 1:100` |

## Summary

MDAnalysis selection language provides powerful tools for:
- **Element-based selections** for metal centers and ligands
- **Distance-based selections** for coordination spheres
- **Boolean logic** for complex queries
- **Pattern matching** with wildcards
- **Dynamic selections** for trajectory analysis
- **Direct integration** with NGLView visualization

This selection syntax is essential for analyzing catalyst structures, coordination complexes, and reaction trajectories in computational chemistry and materials science.
