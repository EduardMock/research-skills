# Metal Coordination Visualization Reference

Complete guide for visualizing metal coordination complexes, highlighting ligands, and displaying coordination bonds in NGLView.

## Overview

This reference provides techniques for visualizing organometallic catalysts and coordination complexes with emphasis on:
- Identifying and highlighting the central metal ion
- Displaying coordinating atoms within distance cutoffs
- Showing coordination bonds as dotted/dashed lines
- Highlighting different ligand types with distinct colors
- Creating publication-quality coordination sphere visualizations

## Basic Metal Center Identification

### Finding Metal Atoms

```python
import nglview as nv

# Load complex
view = nv.NGLWidget()
comp = view.add_component('catalyst.pdb')
view.clear_representations()

# Common transition metals used in catalysis
metals = '_Pd or _Pt or _Ru or _Rh or _Ir or _Fe or _Co or _Ni or _Cu or _Zn'

# Highlight metal center with spacefill
view.clear_representations()
view.add_spacefill(selection=metals, color='orange', radius=1.5)
view.add_licorice(selection='not hydrogen', color='element')
view.center(selection=metals)
```

### Metal-Specific Selections

```python
# Palladium complexes
view.add_spacefill(selection='_Pd', color='orange', radius=1.5)

# Platinum complexes
view.add_spacefill(selection='_Pt', color='silver', radius=1.5)

# Iron complexes
view.add_spacefill(selection='_Fe', color='brown', radius=1.5)

# Ruthenium complexes
view.add_spacefill(selection='_Ru', color='cyan', radius=1.5)

# Rhodium complexes
view.add_spacefill(selection='_Rh', color='pink', radius=1.5)

# Iridium complexes
view.add_spacefill(selection='_Ir', color='lightblue', radius=1.5)

# Copper complexes
view.add_spacefill(selection='_Cu', color='tan', radius=1.5)
```

## Coordination Sphere Visualization

### Basic Coordination Shell (First Shell)

Display atoms directly coordinated to the metal center:

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('catalyst.pdb')
view.clear_representations()

# Metal center
view.add_spacefill(selection='_Pd', color='orange', radius=1.5)

# First coordination shell (within 2.5 Å of Pd)
view.add_licorice(selection='2.5 within _Pd', color='element', radius=0.3)

# Rest of molecule (faded)
view.add_line(selection='not (2.5 within _Pd)', color='grey', opacity=0.3)

# Center on metal
view.center(selection='_Pd')
```

### Common Coordination Distances

Different metals have different typical coordination distances:

```python
# Palladium(II) - square planar: 2.0-2.3 Å
coord_shell_pd = '2.3 within _Pd'

# Platinum(II) - square planar: 2.0-2.3 Å
coord_shell_pt = '2.3 within _Pt'

# Ruthenium(II) - octahedral: 1.9-2.2 Å
coord_shell_ru = '2.2 within _Ru'

# Iron(II/III) - octahedral: 1.9-2.3 Å
coord_shell_fe = '2.3 within _Fe'

# Copper(II) - square planar/distorted: 1.9-2.5 Å
coord_shell_cu = '2.5 within _Cu'

# Zinc(II) - tetrahedral: 1.9-2.1 Å
coord_shell_zn = '2.1 within _Zn'
```

### Multi-Shell Coordination Sphere

Show first and second coordination shells:

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('catalyst.pdb')
view.clear_representations()

# Metal center (largest)
view.add_spacefill(selection='_Pd', color='orange', radius=1.8)

# First coordination shell (within 2.5 Å) - thick sticks
view.add_licorice(
    selection='2.5 within _Pd and not _Pd',
    color='element',
    radius=0.35
)

# Second coordination shell (2.5-5.0 Å) - thin sticks
view.add_licorice(
    selection='5.0 within _Pd and not 2.5 within _Pd',
    color='element',
    radius=0.2,
    opacity=0.7
)

# Distant atoms (faded lines)
view.add_line(
    selection='not 5.0 within _Pd',
    color='lightgrey',
    opacity=0.3
)

view.center(selection='_Pd')
```

## Displaying Coordination Bonds as Dotted Lines

NGLView can display distance constraints as dotted/dashed lines between atoms.

### Method 1: Using Distance Representation

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('catalyst.pdb')
view.clear_representations()

# Show molecule structure
view.add_licorice(selection='all', color='element', radius=0.2)

# Metal center highlighted
view.add_spacefill(selection='_Pd', color='orange', radius=1.5)

# Add distance lines from metal to coordinating atoms
# This shows dotted lines between Pd and atoms within 2.5 Å
view.add_distance(
    atom_pair=[
        ['_Pd', '2.5 within _Pd and not _Pd']
    ],
    color='blue',
    label_visible=False
)

view.center(selection='_Pd')
```

### Method 2: Programmatic Distance Addition

For more control, add individual distance constraints:

```python
import nglview as nv
import MDAnalysis as mda
import numpy as np

# Load with MDAnalysis to get coordinates
u = mda.Universe('catalyst.pdb')
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# Show structure
view.add_licorice(selection='all', color='element', radius=0.2)
view.add_spacefill(selection='_Pd', color='orange', radius=1.5)

# Find metal and coordinating atoms
metal_atoms = u.select_atoms('name Pd')
coord_atoms = u.select_atoms('around 2.5 name Pd and not name Pd')

# Add dotted lines for each coordination bond
for metal in metal_atoms:
    metal_idx = metal.index
    for coord in coord_atoms:
        coord_idx = coord.index

        # Calculate distance
        dist = np.linalg.norm(metal.position - coord.position)

        if dist < 2.5:  # Within coordination distance
            # Add distance representation (dotted line)
            view.add_distance(
                atom_pair=[[metal_idx], [coord_idx]],
                label_visible=True,
                label_color='blue',
                color='blue',
                opacity=0.7
            )

view.center(selection='_Pd')
```

### Method 3: Contact Representation

Display coordination sphere as contact surface:

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('catalyst.pdb')
view.clear_representations()

# Molecule
view.add_licorice(selection='all', color='element', radius=0.2)

# Metal center
view.add_spacefill(selection='_Pd', color='orange', radius=1.5)

# Show contacts between metal and coordinating atoms
view.add_contact(
    selection='_Pd',
    color='blue',
    maxDistance=2.5,  # Coordination distance cutoff
    linewidth=2
)

view.center(selection='_Pd')
```

## Ligand-Specific Highlighting

### Highlighting Different Ligand Types

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('catalyst.pdb')
view.clear_representations()

# Metal center
view.add_spacefill(selection='_Pd', color='orange', radius=1.5)

# Phosphine ligands (P-containing)
view.add_licorice(
    selection='_P or (bonded _P)',
    color='purple',
    radius=0.35
)

# Nitrogen-donor ligands
view.add_licorice(
    selection='_N or (bonded _N)',
    color='blue',
    radius=0.35
)

# Halide ligands
view.add_spacefill(
    selection='_Cl or _Br or _I',
    color='green',
    radius=1.2
)

# Carbon monoxide (CO) ligands
view.add_ball_and_stick(
    selection='_C and (bonded _O) and 2.5 within _Pd',
    color='red',
    sphereDetail=3
)

# Rest of structure (faded)
view.add_line(
    selection='not (2.5 within _Pd)',
    color='lightgrey',
    opacity=0.3
)

view.center(selection='_Pd')
```

### Ligand Type Identification by Residue Name

For structured input files with residue names:

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('complex.pdb')
view.clear_representations()

# Metal center
view.add_spacefill(selection='_Ru', color='cyan', radius=1.5)

# PPh3 ligand (triphenylphosphine)
view.add_licorice(
    selection='resname PPH3',
    color='purple',
    radius=0.35
)

# Bipyridine ligand
view.add_licorice(
    selection='resname BPY',
    color='blue',
    radius=0.35
)

# Chloride ligands
view.add_spacefill(
    selection='resname CL',
    color='green',
    radius=1.2
)

# Coordination bonds
view.add_contact(
    selection='_Ru',
    color='orange',
    maxDistance=2.3,
    linewidth=3
)

view.center(selection='_Ru')
```

### Color-Coding by Donor Atom Type

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('catalyst.pdb')
view.clear_representations()

# Metal center
view.add_spacefill(selection='_Fe', color='brown', radius=1.5)

# Coordination sphere with color by donor atom
coord_sphere = '2.3 within _Fe and not _Fe'

# Phosphorus donors (purple)
view.add_ball_and_stick(
    selection=f'{coord_sphere} and _P',
    color='purple',
    aspectRatio=3.0
)

# Nitrogen donors (blue)
view.add_ball_and_stick(
    selection=f'{coord_sphere} and _N',
    color='blue',
    aspectRatio=3.0
)

# Oxygen donors (red)
view.add_ball_and_stick(
    selection=f'{coord_sphere} and _O',
    color='red',
    aspectRatio=3.0
)

# Carbon donors (grey)
view.add_ball_and_stick(
    selection=f'{coord_sphere} and _C',
    color='grey',
    aspectRatio=3.0
)

# Ligand backbones (thin)
view.add_licorice(
    selection=f'{coord_sphere}',
    color='element',
    radius=0.15
)

# Coordination bonds
view.add_distance(
    atom_pair=[['_Fe', coord_sphere]],
    color='orange',
    label_visible=False,
    linewidth=2
)

view.center(selection='_Fe')
```

## Complete Coordination Complex Examples

### Example 1: Square Planar Pd(II) Complex

```python
import nglview as nv

# Load Pd(II) catalyst with bidentate ligands
view = nv.NGLWidget()
comp = view.add_component('pd_catalyst.pdb')
view.clear_representations()

# Palladium center (orange sphere)
view.add_spacefill(
    selection='_Pd',
    color='orange',
    radius=1.8
)

# First coordination shell (within 2.3 Å)
coord_atoms = '2.3 within _Pd and not _Pd'

# Highlight N-donors (blue)
view.add_ball_and_stick(
    selection=f'{coord_atoms} and _N',
    color='blue',
    aspectRatio=3.5
)

# Highlight P-donors (purple)
view.add_ball_and_stick(
    selection=f'{coord_atoms} and _P',
    color='purple',
    aspectRatio=3.5
)

# Ligand scaffolds (element colors, thin)
view.add_licorice(
    selection='3.0 within _Pd',
    color='element',
    radius=0.18
)

# Coordination bonds (dotted orange lines)
view.add_contact(
    selection='_Pd',
    color='orange',
    maxDistance=2.3,
    linewidth=3
)

# Outer structure (very faded)
view.add_line(
    selection='not 3.0 within _Pd',
    color='lightgrey',
    opacity=0.2
)

# Center and adjust camera
view.center(selection='_Pd')
view.camera = 'orthographic'
view.background = 'white'

view
```

### Example 2: Octahedral Ru(II) Complex

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('ru_complex.pdb')
view.clear_representations()

# Ruthenium center (cyan sphere)
view.add_spacefill(
    selection='_Ru',
    color='cyan',
    radius=1.8
)

# Coordination sphere (within 2.2 Å)
coord_sphere = '2.2 within _Ru and not _Ru'

# Bipyridine ligands (blue sticks)
view.add_licorice(
    selection='2.5 within _Ru and (_C or _N or _H)',
    color='blue',
    radius=0.3
)

# Coordinating N atoms (blue balls)
view.add_ball_and_stick(
    selection=f'{coord_sphere} and _N',
    color='darkblue',
    aspectRatio=4.0
)

# Chloride ligands (green spheres)
view.add_spacefill(
    selection=f'{coord_sphere} and _Cl',
    color='green',
    radius=1.3
)

# Coordination bonds (dashed cyan lines)
view.add_contact(
    selection='_Ru',
    color='cyan',
    maxDistance=2.2,
    linewidth=3
)

# Labels for coordinating atoms
view.add_label(
    selection=coord_sphere,
    label_type='atomname',
    color='black',
    backgroundColor='white',
    backgroundOpacity=0.7,
    radius=1.5
)

# Camera settings for publication
view.center(selection='_Ru')
view.camera = 'orthographic'
view.background = 'white'

view
```

### Example 3: Multi-Metal Cluster

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('iron_cluster.pdb')
view.clear_representations()

# All iron atoms (brown spheres)
view.add_spacefill(
    selection='_Fe',
    color='brown',
    radius=1.5
)

# Bridging sulfur atoms (yellow)
view.add_spacefill(
    selection='_S and (3.0 within _Fe)',
    color='yellow',
    radius=1.3
)

# Terminal ligands color-coded
# CO ligands (red)
view.add_ball_and_stick(
    selection='(_C and bonded _O) and 2.5 within _Fe',
    color='red',
    aspectRatio=3.0
)

# Cysteine S-donors (yellow)
view.add_ball_and_stick(
    selection='_S and 2.3 within _Fe and not (bonded _Fe)',
    color='orange',
    aspectRatio=3.0
)

# Coordination bonds from each Fe
view.add_contact(
    selection='_Fe',
    color='brown',
    maxDistance=2.5,
    linewidth=2
)

# Protein scaffold (light grey cartoon)
view.add_cartoon(
    selection='protein',
    color='lightgrey',
    opacity=0.3
)

# Center on cluster
view.center(selection='_Fe')
view.camera = 'orthographic'
view.background = 'white'

view
```

### Example 4: Grubbs Catalyst (Ru Metathesis)

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('grubbs_catalyst.pdb')
view.clear_representations()

# Ruthenium center (large cyan sphere)
view.add_spacefill(
    selection='_Ru',
    color='cyan',
    radius=2.0
)

# Carbene carbon (red ball)
view.add_ball_and_stick(
    selection='_C and (bonded _Ru) and (bonded _C and bonded _C)',
    color='red',
    aspectRatio=4.0
)

# NHC ligand (green sticks)
view.add_licorice(
    selection='(_N or _C or _H) and 4.0 within _Ru and not _Ru',
    color='green',
    radius=0.3
)

# Phosphine ligand (purple sticks)
view.add_licorice(
    selection='_P or (bonded _P)',
    color='purple',
    radius=0.3
)

# Chloride ligands (green spheres)
view.add_spacefill(
    selection='_Cl and 2.5 within _Ru',
    color='darkgreen',
    radius=1.4
)

# Coordination bonds
view.add_contact(
    selection='_Ru',
    color='orange',
    maxDistance=2.3,
    linewidth=3
)

# Camera
view.center(selection='_Ru')
view.camera = 'perspective'
view.background = 'white'

view
```

## Advanced Techniques

### Distance Labels on Coordination Bonds

Show exact distances for coordination bonds:

```python
import nglview as nv
import MDAnalysis as mda

u = mda.Universe('catalyst.pdb')
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# Structure
view.add_licorice(selection='all', color='element', radius=0.2)
view.add_spacefill(selection='_Pd', color='orange', radius=1.5)

# Get metal and coordinating atoms
metal = u.select_atoms('name Pd')[0]
coord_atoms = u.select_atoms('around 2.5 name Pd and not name Pd')

# Add labeled distance for each coordination bond
for atom in coord_atoms:
    view.add_distance(
        atom_pair=[[metal.index], [atom.index]],
        label_visible=True,
        label_color='blue',
        color='blue',
        label_size=1.5,
        label_format='%.2f Å'
    )

view.center(selection='_Pd')
```

### Coordination Number Display

Automatically count and display coordination number:

```python
import nglview as nv
import MDAnalysis as mda

u = mda.Universe('catalyst.pdb')
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# Visualization
view.add_licorice(selection='all', color='element', radius=0.25)
view.add_spacefill(selection='_Pd', color='orange', radius=1.6)

# Calculate coordination number
metal = u.select_atoms('name Pd')
coord_atoms = u.select_atoms('around 2.5 name Pd and not name Pd')
coord_number = len(coord_atoms)

print(f"Coordination number: {coord_number}")

# Add label to metal showing coordination number
view.add_label(
    selection='_Pd',
    label_type='text',
    label_text=f'CN = {coord_number}',
    color='black',
    backgroundColor='yellow',
    backgroundOpacity=0.8,
    radius=2.5
)

view.center(selection='_Pd')
```

### Multi-Panel Comparison of Coordination Modes

Compare different coordination geometries side-by-side:

```python
import nglview as nv
from ipywidgets import HBox

# Load different complexes
view1 = nv.NGLWidget()
comp1 = view1.add_component('square_planar.pdb')
view2 = nv.NGLWidget()
comp2 = view2.add_component('tetrahedral.pdb')
view3 = nv.NGLWidget()
comp3 = view3.add_component('octahedral.pdb')

# Configure each view
for view, metal, color in [(view1, '_Pd', 'orange'),
                            (view2, '_Zn', 'grey'),
                            (view3, '_Fe', 'brown')]:
    view.clear_representations()
    view.add_spacefill(selection=metal, color=color, radius=1.5)
    view.add_licorice(selection='all', color='element', radius=0.2)
    view.add_contact(selection=metal, color=color, maxDistance=2.5, linewidth=3)
    view.center(selection=metal)
    view.camera = 'orthographic'
    view.background = 'white'

# Display side-by-side
HBox([view1, view2, view3])
```

## Publication-Quality Settings

### Settings for Publication Figures

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('catalyst.pdb')
view.clear_representations()

# High-quality rendering settings
view.add_spacefill(selection='_Pd', color='orange', radius=1.8)
view.add_licorice(selection='2.5 within _Pd', color='element', radius=0.3)
view.add_contact(selection='_Pd', color='blue', maxDistance=2.5, linewidth=3)

# Camera and background
view.camera = 'orthographic'  # Better for publication
view.background = 'white'

# Center on active site
view.center(selection='_Pd')

# Render high-resolution image
view.render_image(factor=4, trim=True, transparent=False)

# Download the image
view.download_image(filename='coordination_complex.png')
```

### Color Schemes for Different Publications

```python
# Nature/Science style (white background, soft colors)
view.background = 'white'
view.add_spacefill(selection='_Ru', color='#00CED1', radius=1.5)  # Soft cyan
view.add_licorice(selection='all', color='element', radius=0.25)

# JACS style (white background, bold colors)
view.background = 'white'
view.add_spacefill(selection='_Pd', color='#FF6600', radius=1.6)  # Bold orange
view.add_licorice(selection='all', color='element', radius=0.28)

# Organometallics style (light grey background)
view.background = '#F5F5F5'
view.add_spacefill(selection='_Fe', color='#8B4513', radius=1.5)  # Saddle brown
view.add_licorice(selection='all', color='element', radius=0.25)
```

## Summary Table: Common Metal Coordination Parameters

| Metal | Typical CN | Coord. Distance (Å) | Common Geometry | Display Color |
|-------|-----------|---------------------|-----------------|---------------|
| Pd(II) | 4 | 2.0-2.3 | Square planar | Orange |
| Pt(II) | 4 | 2.0-2.3 | Square planar | Silver |
| Ru(II) | 6 | 1.9-2.2 | Octahedral | Cyan |
| Fe(II/III) | 6 | 1.9-2.3 | Octahedral | Brown |
| Co(II/III) | 6 | 1.9-2.2 | Octahedral | Pink |
| Ni(II) | 4-6 | 1.9-2.2 | Various | Green |
| Cu(II) | 4-5 | 1.9-2.5 | Square planar/pyramidal | Tan |
| Zn(II) | 4 | 1.9-2.1 | Tetrahedral | Grey |
| Rh(I) | 4 | 2.0-2.3 | Square planar | Light pink |
| Ir(I/III) | 4-6 | 2.0-2.3 | Various | Light blue |

## Quick Reference Code

### Minimal Coordination Sphere Display

```python
import nglview as nv

view = nv.NGLWidget()
comp = view.add_component('catalyst.pdb')
view.clear_representations()

# Metal (spacefill)
view.add_spacefill(selection='_Pd', color='orange', radius=1.5)

# Coordination sphere (licorice)
view.add_licorice(selection='2.5 within _Pd', color='element', radius=0.3)

# Coordination bonds (dotted lines)
view.add_contact(selection='_Pd', color='blue', maxDistance=2.5, linewidth=2)

# Center and display
view.center(selection='_Pd')
view
```

This reference provides all the tools needed to create professional visualizations of metal coordination complexes with proper highlighting of ligands, coordination spheres, and coordination bonds.
