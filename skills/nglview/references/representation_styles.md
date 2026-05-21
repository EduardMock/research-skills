# NGLView Representation Styles Reference

Complete visual reference for all representation types available in NGLView for small molecule, catalyst, and complex visualization.

## Overview

NGLView provides 22+ representation types for visualizing molecular structures. For small molecules, catalysts, and organometallic complexes, the most commonly used representations are **ball-and-stick**, **licorice**, **spacefill**, and **line**. This reference covers all available types with emphasis on chemical applications.

## Representation Types

### 1. Cartoon

**Description**: Secondary structure ribbons for proteins and nucleic acids

**Best For**:
- Protein secondary structure visualization
- Overall protein fold
- Domain organization
- Helix, sheet, and coil regions

**Usage**:
```python
view.add_cartoon(
    selection='protein',
    color='secondary structure',
    radius=0.5,
    opacity=1.0
)
```

**Parameters**:
- `radius` (float): Thickness of cartoon (default: auto)
- `tension` (float): Smoothness (default: auto)
- `capped` (bool): Cap ends (default: True)
- `smoothSheet` (bool): Smooth beta sheets (default: False)

**Color Schemes**: Works well with 'secondary structure', 'residueindex', 'chainindex'

**Example Applications**:
- Protein structure overview
- Multi-domain proteins
- Protein-protein interfaces
- Conformational changes

---

### 2. Licorice

**Description**: Stick bonds with atom spheres at junctions

**Best For**:
- Small molecules
- Active site residues
- Ligands
- Detailed atomic interactions

**Usage**:
```python
view.add_licorice(
    selection='not hydrogen',
    color='element',
    radius=0.3,
    opacity=1.0
)
```

**Parameters**:
- `radius` (float): Stick/sphere radius (default: 0.3)
- `scale` (float): Scaling factor (default: 1.0)
- `aspectRatio` (float): Bond aspect ratio (default: 1.5)

**Color Schemes**: Works well with 'element', 'residueindex'

**Example Applications**:
- Ligand binding sites
- Substrate binding
- Cofactor visualization
- Catalytic residues
- Hydrogen bonding networks

---

### 3. Ball and Stick

**Description**: Classic molecular model with spheres (atoms) and cylinders (bonds)

**Best For**:
- Small molecules
- Ligands
- Chemical structures
- Traditional molecular models

**Usage**:
```python
view.add_ball_and_stick(
    selection='ligand',
    color='element',
    sphereDetail=2,
    cylinderHeight=0.5
)
```

**Parameters**:
- `sphereDetail` (int): Sphere quality (default: 2)
- `cylinderHeight` (float): Bond height (default: 0.5)
- `radiusScale` (float): Atom size scaling (default: 0.3)

**Color Schemes**: Works well with 'element', 'random'

**Example Applications**:
- Drug molecules
- Small molecule ligands
- Chemical education
- Conformer analysis

---

### 4. Spacefill (CPK)

**Description**: Van der Waals spheres representing atomic radii

**Best For**:
- Molecular surface representation
- Steric effects
- Packing analysis
- Volume visualization

**Usage**:
```python
view.add_spacefill(
    selection='protein',
    radius=1.0,
    color='element',
    opacity=0.7
)
```

**Parameters**:
- `radius` (float): Sphere radius multiplier (default: 1.0)
- `detail` (int): Sphere tessellation (default: 2)
- `scale` (float): Scaling factor (default: 1.0)

**Color Schemes**: Works well with 'element', 'hydrophobicity', 'random'

**Example Applications**:
- Protein cavities
- Binding pockets
- Steric clashes
- Molecular volume
- Surface complementarity

---

### 5. Surface

**Description**: Molecular surface (solvent accessible or solvent excluded)

**Best For**:
- Overall molecular shape
- Binding interfaces
- Electrostatic potential
- Hydrophobicity mapping

**Usage**:
```python
view.add_surface(
    selection='protein',
    opacity=0.3,
    color='hydrophobicity',
    surfaceType='vws'  # van der Waals surface
)
```

**Parameters**:
- `surfaceType` (str): 'vws', 'sas', 'ms', 'ses', 'av' (default: 'vws')
- `probeRadius` (float): Probe size for SAS (default: 1.4)
- `smooth` (int): Smoothing iterations (default: 0)
- `scaleFactor` (float): Vertex density (default: 2.0)

**Surface Types**:
- `'vws'`: van der Waals surface
- `'sas'`: Solvent accessible surface
- `'ms'`: Molecular surface
- `'ses'`: Solvent excluded surface
- `'av'`: Accessible volume surface

**Color Schemes**: Works well with 'hydrophobicity', 'electrostatic', 'uniform'

**Example Applications**:
- Protein-protein interfaces
- Binding grooves
- Electrostatic potential visualization
- Hydrophobic patches
- Druggability assessment

---

### 6. Ribbon

**Description**: Smooth ribbon through backbone atoms

**Best For**:
- Smooth protein backbone trace
- Secondary structure
- Continuous path representation

**Usage**:
```python
view.add_ribbon(
    selection='protein',
    color='spectrum',
    radius=0.5
)
```

**Parameters**:
- `radius` (float): Ribbon thickness (default: auto)
- `tension` (float): Smoothness (default: auto)
- `smoothSheet` (bool): Sheet smoothing (default: True)

**Color Schemes**: Works well with 'residueindex', 'chainindex', 'secondary structure'

**Example Applications**:
- Smooth protein representation
- Trajectory visualization
- Conformational transitions

---

### 7. Tube

**Description**: Cylindrical tube along backbone

**Best For**:
- Simple backbone representation
- Polymer chains
- Smooth trajectories

**Usage**:
```python
view.add_tube(
    selection='protein',
    radius=0.5,
    color='residueindex'
)
```

**Parameters**:
- `radius` (float): Tube radius (default: 0.5)
- `tension` (float): Smoothness (default: auto)
- `radiusScale` (float): Radius scaling (default: 1.0)

**Color Schemes**: Works well with 'residueindex', 'spectrum'

**Example Applications**:
- Polymer visualization
- Trajectory paths
- Simple protein representation

---

### 8. Trace

**Description**: C-alpha trace for proteins

**Best For**:
- Protein backbone
- Simplified protein view
- Large complexes

**Usage**:
```python
view.add_trace(
    selection='protein',
    color='chainindex',
    radius=0.3
)
```

**Parameters**:
- `radius` (float): Trace radius (default: 0.3)

**Color Schemes**: Works well with 'chainindex', 'residueindex'

**Example Applications**:
- Large protein complexes
- Multi-chain assemblies
- Backbone-only view
- Trajectory overview

---

### 9. Rope

**Description**: Rope-like representation

**Best For**:
- Smooth chain representation
- Artistic visualization
- Path tracing

**Usage**:
```python
view.add_rope(
    selection='protein',
    color='spectrum',
    radius=0.5
)
```

**Parameters**:
- `radius` (float): Rope radius (default: 0.5)

**Color Schemes**: Works well with 'spectrum', 'chainindex'

**Example Applications**:
- Visual presentations
- Chain topology
- Smooth paths

---

### 10. Backbone

**Description**: Simple backbone bonds

**Best For**:
- Protein backbone connectivity
- Simple topology
- Minimal representation

**Usage**:
```python
view.add_backbone(
    selection='protein',
    color='chainindex',
    linewidth=2
)
```

**Parameters**:
- `linewidth` (int): Line thickness (default: 2)

**Color Schemes**: Works well with 'chainindex', 'secondary structure'

**Example Applications**:
- Backbone connectivity
- Simple protein sketches
- Combined with other representations

---

### 11. Point

**Description**: Point cloud representation

**Best For**:
- Large systems
- Fast rendering
- Point-based visualization

**Usage**:
```python
view.add_point(
    selection='protein',
    pointSize=2,
    color='element'
)
```

**Parameters**:
- `pointSize` (float): Point size (default: 1.0)
- `sizeAttenuation` (bool): Distance-based sizing (default: True)

**Color Schemes**: Works well with 'element', 'random'

**Example Applications**:
- Large molecular systems
- Density visualization
- Fast preview rendering

---

### 12. Line

**Description**: Simple line bonds

**Best For**:
- Wireframe models
- Chemical structures
- Minimal rendering

**Usage**:
```python
view.add_line(
    selection='ligand',
    linewidth=2,
    color='element'
)
```

**Parameters**:
- `linewidth` (int): Line thickness (default: 2)

**Color Schemes**: Works well with 'element', 'uniform'

**Example Applications**:
- Chemical diagrams
- Simple molecular structures
- Overlays with other representations

---

### 13. Hyperball

**Description**: Solvent-excluded surface using hyperballs

**Best For**:
- Smooth molecular surfaces
- Artistic visualization
- High-quality rendering

**Usage**:
```python
view.add_hyperball(
    selection='protein',
    color='element',
    shrink=0.1
)
```

**Parameters**:
- `shrink` (float): Shrinking factor (default: 0.1)

**Color Schemes**: Works well with 'element', 'residueindex'

**Example Applications**:
- Publication figures
- High-quality surfaces
- Artistic molecular views

---

### 14. Label

**Description**: Text labels for atoms/residues

**Best For**:
- Atom/residue identification
- Numbering
- Annotations

**Usage**:
```python
view.add_label(
    selection='.CA',
    label_type='residue',  # 'atom', 'residue', 'text'
    color='black',
    fontSize=14
)
```

**Parameters**:
- `label_type` (str): 'atom', 'residue', 'text' (default: 'residue')
- `fontSize` (int): Label size (default: 14)
- `fontFamily` (str): Font (default: 'sans-serif')
- `fontWeight` (str): 'normal', 'bold' (default: 'normal')

**Color Schemes**: Usually uniform colors for readability

**Example Applications**:
- Residue numbering
- Atom identification
- Active site labeling
- Custom annotations

---

### 15. Distance

**Description**: Distance measurements between atom pairs

**Best For**:
- Bond length measurement
- Distance constraints
- Interaction distances

**Usage**:
```python
view.add_distance(
    atom_pair=[[0, 10], [5, 15]],  # List of [atom1, atom2] pairs
    color='black',
    labelSize=2.0
)
```

**Parameters**:
- `atom_pair` (list): List of atom index pairs
- `labelSize` (float): Label scaling (default: 2.0)
- `labelColor` (str): Label color (default: 'black')

**Color Schemes**: Typically uniform colors

**Example Applications**:
- Hydrogen bond distances
- Salt bridge measurements
- Constraint validation
- Interaction analysis

---

### 16. Contact

**Description**: Inter-molecular contacts

**Best For**:
- Protein-protein interfaces
- Protein-ligand contacts
- Interaction networks

**Usage**:
```python
view.add_contact(
    selection='protein',
    maxDistance=5.0,
    color='grey'
)
```

**Parameters**:
- `maxDistance` (float): Contact cutoff in Å (default: 4.0)
- `filterSele` (str): Filter contacts (default: None)

**Color Schemes**: Uniform colors work best

**Example Applications**:
- Interface analysis
- Binding site contacts
- Molecular recognition
- Crystal packing

---

### 17. Unitcell

**Description**: Crystallographic unit cell

**Best For**:
- Crystal structures
- Lattice visualization
- Symmetry

**Usage**:
```python
view.add_unitcell(
    radius=0.1,
    color='black'
)
```

**Parameters**:
- `radius` (float): Line radius (default: 0.1)

**Color Schemes**: Uniform colors (typically black or white)

**Example Applications**:
- X-ray crystal structures
- Lattice parameters
- Crystal symmetry
- Space group visualization

---

### 18. Slice

**Description**: Molecular slice/cross-section

**Best For**:
- Internal structure
- Cavity analysis
- Cross-sections

**Usage**:
```python
view.add_slice(
    selection='protein',
    color='element',
    position=[0, 0, 0],
    normal=[0, 1, 0]
)
```

**Parameters**:
- `position` (list): Slice position [x, y, z]
- `normal` (list): Slice normal vector [x, y, z]

**Color Schemes**: Works with any color scheme

**Example Applications**:
- Internal cavities
- Membrane cross-sections
- Channel visualization
- Cavity analysis

---

### 19. Axes

**Description**: Coordinate axes

**Best For**:
- Orientation reference
- Coordinate system
- Principal axes

**Usage**:
```python
view.add_axes(
    radius=0.1,
    length=10.0
)
```

**Parameters**:
- `radius` (float): Axis radius (default: 0.1)
- `length` (float): Axis length (default: determined by structure)

**Color Schemes**: X=red, Y=green, Z=blue (standard)

**Example Applications**:
- Orientation reference
- Principal component axes
- Molecular alignment

---

### 20. Helixorient

**Description**: Helix orientation vectors

**Best For**:
- Alpha helix orientation
- Helix packing
- Membrane protein topology

**Usage**:
```python
view.add_helixorient(
    selection='protein',
    radius=0.3,
    color='red'
)
```

**Parameters**:
- `radius` (float): Vector radius (default: 0.3)

**Color Schemes**: Uniform colors

**Example Applications**:
- Helix bundle analysis
- Membrane protein orientation
- Helix-helix packing

---

### 21. Rocket

**Description**: Rocket representation (directional)

**Best For**:
- Directional information
- Trajectory direction
- Chain directionality

**Usage**:
```python
view.add_rocket(
    selection='protein',
    color='chainindex',
    radius=0.5
)
```

**Parameters**:
- `radius` (float): Rocket radius (default: 0.5)

**Color Schemes**: Works with any scheme

**Example Applications**:
- Chain direction
- N-to-C terminus visualization
- Directionality indication

---

### 22. Base (Simplified Base)

**Description**: Nucleic acid base representation

**Best For**:
- DNA/RNA bases
- Base pairing
- Nucleic acid structure

**Usage**:
```python
view.add_base(
    selection='nucleic',
    color='element'
)
```

**Parameters**:
Standard representation parameters

**Color Schemes**: Works with 'element', 'residueindex'

**Example Applications**:
- DNA/RNA visualization
- Base stacking
- Nucleic acid secondary structure

---

## Common Representation Combinations for Small Molecules

### Organometallic Catalyst
```python
view.clear_representations()

# Metal center as large sphere
view.add_spacefill(selection='_Pd or _Pt or _Ru', radius=1.5, color='orange')

# Ligands as ball and stick
view.add_ball_and_stick(selection='not (_Pd or _Pt or _Ru) and not _H', color='element')

# Show coordination sphere
view.add_line(selection='3 within (_Pd or _Pt or _Ru)', linewidth=3)
```

### Catalyst-Substrate Complex
```python
view.clear_representations()

# Catalyst as ball and stick
view.add_ball_and_stick(selection='resname CAT', color='element')

# Substrate/reactant as licorice with different color
view.add_licorice(selection='resname SUB', color='cyan')

# Metal highlighted
view.add_spacefill(selection='_Fe or _Ru or _Pd', radius=1.5, color='red')

# Transparent surface to show steric environment
view.add_surface(selection='resname CAT', opacity=0.2)
```

### Drug Molecule with Solvent
```python
view.clear_representations()

# Drug molecule as ball and stick
view.add_ball_and_stick(selection='resname DRG', color='element')

# Water molecules as small points
view.add_point(selection='water', pointSize=1, color='red', opacity=0.3)

# Ions as spacefill
view.add_spacefill(selection='ion', radius=1.0)
```

### Conformer Comparison Style
```python
view.clear_representations()

# Single conformer - publication quality
view.add_ball_and_stick(
    selection='not hydrogen',
    color='element',
    sphereDetail=3,
    radiusScale=0.25
)

view.background = 'white'
view.camera = 'orthographic'
```

### Reactive Center Highlight
```python
view.clear_representations()

# Entire molecule as thin licorice (context)
view.add_licorice(selection='all', color='grey', radius=0.15, opacity=0.5)

# Reactive atoms as ball and stick (highlight)
view.add_ball_and_stick(selection='10-20', color='element')

# Metal center
view.add_spacefill(selection='_Pd', radius=1.5, color='orange')
```

## Color Scheme Reference

### Built-in Color Schemes

1. **element** - CPK coloring by element
   - C: grey, N: blue, O: red, S: yellow, etc.
   - Best for: Chemical accuracy, small molecules

2. **residueindex** - Color by residue number (rainbow)
   - Blue (N-terminus) to red (C-terminus)
   - Best for: Sequence position, trajectory coloring

3. **chainindex** - Color by chain
   - Different color per chain
   - Best for: Multi-chain complexes, interfaces

4. **secondary structure** - Color by secondary structure
   - Helix: magenta, Sheet: yellow, Coil: white/grey
   - Best for: Protein fold visualization

5. **hydrophobicity** - Color by hydrophobicity scale
   - Hydrophobic: orange, Hydrophilic: blue
   - Best for: Surface properties, membrane proteins

6. **random** - Random colors per residue/chain
   - Best for: Distinguishing components

7. **uniform** - Single color
   - Specify with `color='blue'` parameter
   - Best for: Clean publication figures

### Custom Colors

```python
# RGB color
view.add_cartoon(color=[255, 0, 0])  # Red

# Hex color
view.add_surface(color='#FF5733')

# Color name
view.add_licorice(color='cyan')

# Per-residue coloring
import seaborn as sns
colors_hex = sns.color_palette('viridis', n_residues).as_hex()
colors_int = [int(c.replace('#', '0x'), 16) for c in colors_hex]
view._set_color_by_residue(colors_int, component=0)
```

## Parameter Quick Reference

### Common Parameters Across Representations

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `selection` | str | 'all' | Atom selection |
| `color` | str/list | 'element' | Color scheme or color |
| `opacity` | float | 1.0 | Transparency (0-1) |
| `radius` | float | varies | Size/thickness |
| `radiusScale` | float | 1.0 | Scaling multiplier |

### Representation-Specific Parameters

**Cartoon:**
- `aspectRatio`: 5.0
- `capped`: True
- `smoothSheet`: False
- `tension`: auto

**Surface:**
- `surfaceType`: 'vws'
- `probeRadius`: 1.4
- `smooth`: 0
- `scaleFactor`: 2.0

**Label:**
- `fontSize`: 14
- `fontFamily`: 'sans-serif'
- `fontWeight`: 'normal'
- `labelType`: 'residue'

**Point:**
- `pointSize`: 1.0
- `sizeAttenuation`: True

**Distance:**
- `labelSize`: 2.0
- `labelColor`: 'black'

## Best Practices

1. **Layer Representations**: Start with cartoon/surface, add details with licorice/ball-and-stick

2. **Use Transparency**: Set `opacity=0.3` for surfaces to show internal features

3. **Limit Detail**: Don't show hydrogen atoms unless necessary (`selection='not hydrogen'`)

4. **Combine Complementary Types**: Cartoon (overall) + Licorice (detail) + Surface (context)

5. **Color Consistently**: Use same color scheme across related representations

6. **Performance**: Point clouds and lines are fastest for large systems

7. **Publication Quality**: Use surface, cartoon, and ball-and-stick for publication figures

8. **Remove Defaults**: Always call `view.clear_representations()` before custom styling

## Troubleshooting

**Representation Not Visible:**
- Check selection syntax
- Ensure atoms exist in selection
- Try increasing radius
- Check opacity (not set to 0)

**Performance Issues:**
- Use simpler representations (trace, backbone, point)
- Reduce selection size
- Lower detail parameters
- Remove hydrogen atoms

**Overlapping Representations:**
- Order matters - later representations appear on top
- Use transparency to show multiple layers
- Remove representations you don't need

This comprehensive reference covers all representation types and styling options available in NGLView for molecular visualization.
