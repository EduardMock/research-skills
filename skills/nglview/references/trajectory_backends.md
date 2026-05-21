# NGLView Trajectory Backends Reference

Complete guide to loading QM/MM, ab initio MD, and classical MD trajectories of small molecules, catalysts, and complexes using NGLView's multiple backend support.

## Overview

NGLView supports trajectories from QM/MM engines, ab initio MD packages, and classical MD engines through Python trajectory analysis libraries (backends). Each backend provides an adapter that converts trajectory data to NGLView format.

## Format Support Matrix

| Engine/Package | Simulation Type | Formats | Extensions | Recommended Backend | Alternative Backends |
|----------------|-----------------|---------|------------|---------------------|---------------------|
| **Amber (QM/MM)** | QM/MM, semiempirical | Binary NetCDF, ASCII | .nc, .ncdf, .mdcrd, .trr | PyTraj | MDTraj, MDAnalysis, ParmEd |
| **Gromacs** | Classical MD | XTC, TRR, GRO | .xtc, .trr, .gro | MDTraj, Simpletraj | MDAnalysis |
| **CHARMM** | Classical MD | DCD, PSF | .dcd, .psf | MDTraj | MDAnalysis |
| **NAMD** | Classical MD, QM/MM | DCD | .dcd, .psf | MDTraj | MDAnalysis |
| **OpenMM** | Classical MD | DCD, PDB, HDF5 | .dcd, .pdb, .h5 | MDTraj, ASE | MDAnalysis |
| **CP2K** | AIMD, BOMD | XYZ, PDB | .xyz, .pdb | MDAnalysis | custom |
| **ORCA** | IRC, NEB, AIMD | XYZ | .xyz | custom parsing | MDAnalysis |
| **Gaussian** | IRC, scan | Log files | .log | custom parsing | - |
| **ADF** | Reaction coordinates | XYZ, KF | .xyz | custom parsing | - |

## Backend Details

### 1. MDTraj (Recommended for Multi-Format Support)

**Supported Formats**: Amber, Gromacs, CHARMM, NAMD, OpenMM, TINKER, MOL2, SDF, and many more

**Installation:**
```bash
conda install -c conda-forge mdtraj
```

**Basic Usage:**
```python
import mdtraj as md
import nglview as nv

# Load trajectory
traj = md.load('trajectory.xtc', top='topology.gro')

# Create view
view = nv.NGLWidget()
comp = view.add_trajectory(traj)
view.clear_representations()
view
```

**Advanced Usage:**
```python
# Load with stride (every Nth frame)
traj = md.load('trajectory.xtc', top='topology.gro', stride=10)

# Load frame slice
traj = md.load('trajectory.xtc', top='topology.gro', frame=slice(0, 1000, 5))

# Load multiple files
traj = md.load(['traj1.xtc', 'traj2.xtc'], top='topology.gro')

# Atom selection before visualization
protein = traj.atom_slice(traj.topology.select('protein'))
view = nv.NGLWidget()
comp = view.add_trajectory(protein)
view.clear_representations()
```

**Key Features:**
- Unit conversion: Converts nm to Å automatically
- Fast I/O for most formats
- Rich topology information
- Extensive analysis capabilities

**Code Pattern (from nglview/adaptor.py:323-351):**
```python
class MDTrajTrajectory(Trajectory, Structure):
    def get_coordinates(self, index):
        return 10 * self.trajectory.xyz[index]  # nm to Angstrom

    @property
    def n_frames(self):
        return self.trajectory.n_frames
```

---

### 2. PyTraj (Recommended for Amber)

**Supported Formats**: All Amber trajectory formats (NetCDF, ASCII, Restart, TRR)

**Installation:**
```bash
conda install -c ambermd pytraj
```

**Basic Usage:**
```python
import pytraj as pt
import nglview as nv

# Load Amber trajectory
traj = pt.load('trajectory.nc', top='system.prmtop')

# Create view
view = nv.NGLWidget()
comp = view.add_trajectory(traj)
view.clear_representations()
view
```

**Advanced Usage:**
```python
# Load restart file
traj = pt.load('restart.rst7', top='system.prmtop')

# Load with frame stride
traj = pt.iterload('trajectory.nc', top='system.prmtop', frame_slice=(0, 1000, 10))

# Multiple trajectories
traj_list = [pt.load('traj1.nc', 'top.prmtop'),
             pt.load('traj2.nc', 'top.prmtop')]
view = nv.NGLWidget()
comp = view.add_trajectory(traj_list)
view.clear_representations()

# Atom selection
protein_indices = traj.top.select('@CA')  # C-alpha atoms
protein_traj = traj[protein_indices]
view = nv.NGLWidget()
comp = view.add_trajectory(protein_traj)
view.clear_representations()
```

**Key Features:**
- Native Amber support (fastest for Amber)
- Coordinates already in Ångströms
- Direct cpptraj integration
- Efficient memory usage

**Code Pattern (from nglview/adaptor.py:354-382):**
```python
class PyTrajTrajectory(Trajectory, Structure):
    def get_coordinates(self, index):
        return self.trajectory[index].xyz  # Already in Angstroms

    @property
    def n_frames(self):
        return self.trajectory.n_frames
```

---

### 3. MDAnalysis (Best for Complex Selections)

**Supported Formats**: Gromacs, Amber, CHARMM, NAMD, LAMMPS, DL_POLY, and 40+ other formats

**Installation:**
```bash
conda install -c conda-forge MDAnalysis
```

**Basic Usage:**
```python
from MDAnalysis import Universe
import nglview as nv

# Create Universe
u = Universe('topology.gro', 'trajectory.xtc')

# Visualize entire system
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# Or visualize selection
protein = u.select_atoms('protein')
view = nv.NGLWidget()
comp = view.add_trajectory(protein)
view.clear_representations()
view
```

**Advanced Usage:**
```python
# Multiple trajectory files
u = Universe('topology.psf', ['traj1.dcd', 'traj2.dcd'])

# Complex selections
binding_site = u.select_atoms('protein and around 5 resname LIG')
view = nv.NGLWidget()
comp = view.add_trajectory(binding_site)
view.clear_representations()

# Trajectory transformations before viewing
from MDAnalysis.transformations import fit_rot_trans

# Align trajectory
mobile = u.select_atoms('protein and name CA')
ref = Universe('reference.pdb').select_atoms('protein and name CA')
transform = fit_rot_trans(mobile, ref)
u.trajectory.add_transformations(transform)

view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# Frame iteration
for ts in u.trajectory[0:100:10]:  # Frames 0-100, step 10
    # Process each frame
    pass
```

**Key Features:**
- Most extensive format support
- Powerful selection language
- On-the-fly transformations
- Supports both Universe and AtomGroup

**Code Pattern (from nglview/adaptor.py:426-475):**
```python
class MDAnalysisTrajectory(Trajectory, Structure):
    def get_coordinates(self, index):
        self.atomgroup.universe.trajectory[index]
        xyz = self.atomgroup.atoms.positions
        return xyz

    @property
    def n_frames(self):
        return self.atomgroup.universe.trajectory.n_frames
```

---

### 4. ParmEd (Amber Structures and Trajectories)

**Supported Formats**: Amber (PrmTop, Inpcrd, RST7), PDB, MOL2, and others

**Installation:**
```bash
conda install -c conda-forge parmed
```

**Basic Usage:**
```python
import parmed as pmd
import nglview as nv

# Load Amber system
structure = pmd.load_file('system.prmtop', 'trajectory.nc')

# Visualize
view = nv.NGLWidget()
comp = view.add_trajectory(structure)
view.clear_representations()
view
```

**Advanced Usage:**
```python
# Load structure only
parm = pmd.load_file('system.prmtop')
coords = pmd.load_file('trajectory.rst7')
parm.coordinates = coords.coordinates

# Multi-model PDB output
traj = pmd.load_file('system.prmtop', 'trajectory.nc')
adapter = nv.ParmEdTrajectory(traj)
adapter.only_save_1st_model = False  # Save all frames as models
pdb_string = adapter.get_structure_string()

# Structure manipulation
parm = pmd.load_file('system.prmtop')
parm.strip('@H*')  # Remove hydrogens
parm.coordinates = some_coords
view = nv.NGLWidget()
comp = view.add_trajectory(parm)
view.clear_representations()
```

**Key Features:**
- Direct Amber file support
- Structure editing capabilities
- Converts to PDB for visualization
- Pre-caches all coordinates

**Code Pattern (from nglview/adaptor.py:404-423):**
```python
class ParmEdTrajectory(Trajectory, ParmEdStructure):
    def __init__(self, trajectory):
        self._xyz = trajectory.get_coordinates()  # Cache all coords

    def get_coordinates(self, index):
        return self._xyz[index]
```

---

### 5. Simpletraj (Fast Gromacs I/O)

**Supported Formats**: Gromacs XTC and TRR

**Installation:**
```bash
pip install simpletraj
```

**Basic Usage:**
```python
import nglview as nv

# Create SimpletrajTrajectory adapter
traj = nv.SimpletrajTrajectory('trajectory.xtc', 'topology.gro')

# Visualize
view = nv.NGLWidget(traj)
view
```

**Advanced Usage:**
```python
# Access trajectory cache
from simpletraj import trajectory

cache = trajectory.TrajectoryCache()
traj_obj = cache.get('/absolute/path/to/trajectory.xtc')

n_frames = traj_obj.numframes
frame_data = traj_obj.get_frame(0)
coords = frame_data['coords']
```

**Key Features:**
- Very fast XTC reading (C++ backend)
- Minimal memory footprint
- Trajectory caching
- Best for large Gromacs XTC files

**Code Pattern (from nglview/adaptor.py:279-320):**
```python
class SimpletrajTrajectory(Trajectory, Structure):
    def __init__(self, path, structure_path):
        self.traj_cache = simpletraj.trajectory.TrajectoryCache()

    def get_coordinates(self, index):
        traj = self.traj_cache.get(os.path.abspath(self.path))
        frame = traj.get_frame(index)
        return frame["coords"]
```

---

### 6. HTMD (High-Throughput MD)

**Supported Formats**: Multiple formats via HTMD Molecule class

**Installation:**
```bash
conda install -c acellera htmd
```

**Basic Usage:**
```python
from htmd import Molecule
import nglview as nv

# Load with HTMD
mol = Molecule('structure.pdb')
mol.read('trajectory.xtc')

# Optional: filter atoms
mol.filter('protein')

# Visualize
view = nv.NGLWidget()
comp = view.add_trajectory(mol)
view.clear_representations()
view
```

**Advanced Usage:**
```python
# Multiple simulations
mol = Molecule('system.psf')
mol.read(['sim1/traj.dcd', 'sim2/traj.dcd'])

# HTMD selections
mol.filter('protein and within 5 of resname LIG')

# Access frames
n_frames = mol.numFrames
coords_frame_0 = mol.coords[:, :, 0]  # Shape: (n_atoms, 3, n_frames)

view = nv.NGLWidget()
comp = view.add_trajectory(mol)
view.clear_representations()
```

**Key Features:**
- Integrated with HTMD analysis tools
- Supports adaptive sampling workflows
- Multi-simulation handling
- 3D coordinate array: (atoms, coords, frames)

**Code Pattern (from nglview/adaptor.py:478-508):**
```python
class HTMDTrajectory(Trajectory):
    def get_coordinates(self, index):
        return np.squeeze(self.mol.coords[:, :, index])

    @property
    def n_frames(self):
        return self.mol.numFrames
```

---

### 7. Schrodinger (Desmond Trajectories)

**Supported Formats**: Schrodinger Maestro and Desmond formats

**Installation:**
Requires Schrodinger installation and license.

**Basic Usage:**
```python
from schrodinger.structure import StructureReader
import nglview as nv

# Load structure
structures = StructureReader('system.mae')
view = nv.NGLWidget()
comp = view.add_trajectory(structures[0])
view.clear_representations()
```

**Advanced Usage with Trajectory:**
```python
from schrodinger.application.desmond.packages import topo, traj
import nglview as nv

# Load CMS and trajectory
_, model = topo.read_cms('desmond_output.cms')
traj_obj = traj.read_traj('desmond_output.dtr')

# Create adapter
mol_traj = nv.SchrodingerTrajectory(model, traj_obj)

# Or use class method
mol_traj = nv.SchrodingerTrajectory.from_files(
    'desmond_output.cms',
    'desmond_output.dtr'
)

view = nv.NGLWidget(mol_traj)
view
```

**Key Features:**
- Native Desmond support
- Integrates with Schrodinger tools
- Converts to ParmEd internally for PDB export

**Code Pattern (from nglview/adaptor.py:568-606):**
```python
class SchrodingerTrajectory(SchrodingerStructure, Trajectory):
    def get_coordinates(self, index):
        return self._traj[index].pos()

    @classmethod
    def from_files(cls, cms_fname, traj_fname):
        from schrodinger.application.desmond.packages import topo, traj
        _, model = topo.read_cms(cms_fname)
        traj = traj.read_traj(traj_fname)
        return cls(model, traj)
```

---

### 8. ASE (Atomic Simulation Environment)

**Supported Formats**: ASE trajectory format (used by OpenMM, GPAW, etc.)

**Installation:**
```bash
conda install -c conda-forge ase
```

**Basic Usage:**
```python
from ase.io.trajectory import Trajectory
import nglview as nv

# Load ASE trajectory
traj = Trajectory('trajectory.traj')

# Visualize
view = nv.NGLWidget()
comp = view.add_trajectory(traj)
view.clear_representations()
view
```

**Advanced Usage:**
```python
# Access individual frames (ASE Atoms objects)
atoms_frame_0 = traj[0]
positions = atoms_frame_0.get_positions()

# Slice trajectory
traj_subset = traj[0:100:10]

# OpenMM via ASE
# (Requires saving OpenMM to ASE format first)
from ase import Atoms
import numpy as np

# Save OpenMM frames as ASE trajectory
# Then load and visualize
traj = Trajectory('openmm_via_ase.traj')
view = nv.NGLWidget()
comp = view.add_trajectory(traj)
view.clear_representations()
```

**Key Features:**
- Integration with ASE ecosystem
- Good for quantum chemistry packages
- Simple trajectory format

**Code Pattern (from nglview/adaptor.py:511-540):**
```python
class ASETrajectory(Trajectory, Structure):
    def get_coordinates(self, index):
        return self.trajectory[index].positions

    @property
    def n_frames(self):
        return len(self.trajectory)
```

---

### 9. ProDy (Protein Dynamics)

**Supported Formats**: PDB, DCD, various ensemble formats

**Installation:**
```bash
conda install -c conda-forge prody
```

**Basic Usage:**
```python
import prody as pd
import nglview as nv

# Load structure
structure = pd.parsePDB('structure.pdb')
view = nv.NGLWidget()
comp = view.add_trajectory(structure)
view.clear_representations()

# Load ensemble (multiple conformers)
ensemble = pd.parsePDB('nmr_structure.pdb')  # NMR ensemble
view = nv.NGLWidget()
comp = view.add_trajectory(ensemble)
view.clear_representations()
```

**Advanced Usage:**
```python
# Load DCD trajectory
structure = pd.parsePDB('structure.pdb')
dcd = pd.parseDCD('trajectory.dcd')
structure.addCoordset(dcd)

# Create trajectory view
traj = nv.ProdyTrajectory(structure)
view = nv.NGLWidget(traj)

# Access conformers
n_conformers = structure.numConfs()
coords_conf_0 = structure.getConformation(0).getCoords()
```

**Key Features:**
- Protein-focused analysis tools
- NMR ensemble support
- ANM/GNM normal mode analysis integration

**Code Pattern (from nglview/adaptor.py:265-276):**
```python
class ProdyTrajectory(Trajectory, ProdyStructure):
    @property
    def n_frames(self):
        return self._obj.numConfs()

    def get_coordinates(self, index):
        return self._obj.getConformation(index).getCoords()
```

---

## Usage Patterns

### Direct Adapter Creation vs Convenience Functions

**Convenience Functions (Recommended):**
```python
# Automatic adapter wrapping
import nglview as nv
import mdtraj as md

traj = md.load('traj.xtc', top='top.gro')
view = nv.NGLWidget()
comp = view.add_trajectory(traj)  # Uses componentwise pattern
view.clear_representations()
```

**Direct Adapter Creation:**
```python
# Manual adapter instantiation
import nglview as nv
import mdtraj as md

traj = md.load('traj.xtc', top='top.gro')
adapter = nv.MDTrajTrajectory(traj)
view = nv.NGLWidget(adapter)
```

**Adding to Existing View:**
```python
# NGLView auto-detects backend
view = nv.NGLWidget()

traj = md.load('traj.xtc', top='top.gro')
view.add_trajectory(traj)  # Auto-wrapped in MDTrajTrajectory
```

### Backend Auto-Detection

NGLView automatically detects the backend based on the module name:

```python
# From nglview/widget.py
package_name = trajectory.__module__.split('.')[0]
if package_name in BACKENDS:
    trajectory = BACKENDS[package_name](trajectory)
```

Registered backends (from nglview/config.py):
```python
BACKENDS = {
    'mdtraj': MDTrajTrajectory,
    'pytraj': PyTrajTrajectory,
    'MDAnalysis': MDAnalysisTrajectory,
    'parmed': ParmEdTrajectory,
    'simpletraj': SimpletrajTrajectory,
    'htmd': HTMDTrajectory,
    'prody': ProdyTrajectory,
    'ase': ASETrajectory,
    'schrodinger': SchrodingerTrajectory,
}
```

### Custom Backend Registration

You can register custom trajectory adapters:

```python
import nglview as nv

@nv.register_backend('mypackage')
class MyTrajectoryAdapter(nv.Trajectory, nv.Structure):
    def __init__(self, trajectory):
        self.trajectory = trajectory
        self.ext = "pdb"
        self.id = str(uuid.uuid4())

    def get_coordinates(self, index):
        # Return (n_atoms, 3) numpy array in Angstroms
        return self.trajectory.get_frame(index)

    @property
    def n_frames(self):
        return len(self.trajectory)

    def get_structure_string(self):
        # Return structure in self.ext format
        return self.trajectory.to_pdb()

# Now NGLView will automatically use MyTrajectoryAdapter
# when it detects objects from 'mypackage'
```

## Performance Comparison

| Backend | Speed (Large XTC) | Memory Usage | Format Support | Best For |
|---------|------------------|--------------|----------------|----------|
| Simpletraj | Excellent | Low | XTC/TRR only | Large Gromacs files |
| MDTraj | Very Good | Medium | Extensive | General purpose |
| PyTraj | Excellent | Low | Amber formats | Amber trajectories |
| MDAnalysis | Good | Medium-High | Most extensive | Complex analysis |
| ParmEd | Good | High (pre-caches) | Amber + PDB | Amber systems |
| HTMD | Good | Medium | Multiple | HTMD workflows |

## Troubleshooting

### Common Issues

**1. Backend Not Found:**
```python
# Error: No module named 'mdtraj'
# Solution: Install the backend
conda install -c conda-forge mdtraj
```

**2. Topology/Trajectory Mismatch:**
```python
# Error: Number of atoms mismatch
# Solution: Ensure topology matches trajectory
traj = md.load('traj.xtc', top='correct_topology.gro')
```

**3. Memory Issues with Large Trajectories:**
```python
# Load with stride
traj = md.load('huge_traj.xtc', top='top.gro', stride=10)

# Or load frame slice
traj = md.load('huge_traj.xtc', top='top.gro', frame=slice(0, 1000))
```

**4. Unit Conversion Issues:**
```python
# MDTraj uses nanometers, NGLView expects Angstroms
# Adapters handle this automatically:
# MDTrajTrajectory: multiplies by 10
# PyTrajTrajectory: already in Angstroms
```

**5. Frame Index Out of Range:**
```python
# Check max frame
print(f"Max frame: {view.max_frame}")

# Valid frame range: 0 to max_frame (inclusive)
view.frame = view.max_frame  # Last frame
```

## Best Practices

1. **Choose backend based on your MD engine** - Use PyTraj for Amber, MDTraj for Gromacs/CHARMM, etc.

2. **Load large trajectories efficiently** - Use stride or frame slices to reduce memory

3. **Pre-select atoms when possible** - Filter to protein/region of interest before loading

4. **Consider Simpletraj for huge Gromacs files** - Significantly faster I/O

5. **Use MDAnalysis for complex selections** - Best selection language and flexibility

6. **Cache trajectories in memory** - Don't reload the same trajectory multiple times

7. **Match file formats correctly** - Ensure topology format matches trajectory needs

## Code Examples

###Loading Trajectory from Each Engine (Small Molecule Focus)

```python
import nglview as nv

# Amber QM/MM
import pytraj as pt
traj = pt.load('qmmm_prod.nc', top='catalyst.prmtop')
view = nv.NGLWidget()
comp = view.add_trajectory(traj)
view.clear_representations()

# Gromacs (small molecule MD)
import mdtraj as md
traj = md.load('ligand_md.xtc', top='ligand.gro')
view = nv.NGLWidget()
comp = view.add_trajectory(traj)
view.clear_representations()

# NAMD QM/MM
traj = md.load('qmmm.dcd', top='complex.psf')
view = nv.NGLWidget()
comp = view.add_trajectory(traj)
view.clear_representations()

# OpenMM (drug molecule simulation)
traj = md.load('drug_sim.dcd', top='drug.pdb')
view = nv.NGLWidget()
comp = view.add_trajectory(traj)
view.clear_representations()

# CP2K AIMD (catalyst dynamics)
from MDAnalysis import Universe
u = Universe('catalyst.pdb', 'aimd_traj.xyz')
view = nv.NGLWidget()
comp = view.add_trajectory(u)
view.clear_representations()

# ORCA IRC (reaction coordinate)
# Custom parsing required (see below)
```

### Custom Parsing for QM Packages

**⚠️ Important**: XYZ files lack bond connectivity information and will display atoms as disconnected spheres in NGLView. **Always convert XYZ to MOL2 format first** for proper visualization with chemical bonds.

For ORCA, Gaussian, and other QM packages that output XYZ or log files:

```python
import nglview as nv

# IMPORTANT: Convert XYZ to MOL2 first using OpenBabel
# obabel irc_forward.xyz -O irc_forward.mol2

# Load converted MOL2 file with proper bond information
view = nv.NGLWidget()
comp = view.add_component('irc_forward.mol2')

# Style for small molecules
view.clear_representations()
view.add_ball_and_stick(color='element')
view.background = 'white'
view

# For Gaussian log files, extract geometries first
# Use cclib or custom parser to extract to MOL2 (NOT XYZ)
import cclib

parser = cclib.io.ccopen('gaussian.log')
data = parser.parse()

# Extract geometries and create MOL2 with bond information
# Use OpenBabel for conversion or RDKit for bond perception
```

**Automated XYZ to MOL2 Conversion:**

```bash
# Single file conversion
obabel input.xyz -O output.mol2

# Batch conversion of all XYZ files
for f in *.xyz; do obabel "$f" -O "${f%.xyz}.mol2"; done

# Or use the provided script
python ~/.claude/skills/nglview/scripts/xyz_to_mol2.py reaction_path.xyz
```

### Reaction Coordinate Visualization

```python
import nglview as nv

# IRC or NEB trajectory
# IMPORTANT: Convert XYZ to MOL2 first for proper bond visualization
# obabel reaction_path.xyz -O reaction_path.mol2

view = nv.NGLWidget()
comp = view.add_component('reaction_path.mol2')

# Setup for reaction visualization
view.clear_representations()
view.add_ball_and_stick(color='element', sphereDetail=3)
view.background = 'white'
view.camera = 'orthographic'

# Center on reactive center
view.center(selection='all')

# Animate reaction (v4.0+: direct frame control)
# The widget displays play controls automatically
# Or animate programmatically with custom timing:
import time
for frame_num in range(view.max_frame + 1):
    view.frame = frame_num
    time.sleep(0.2)  # 200ms delay to see reaction clearly

view
```

This comprehensive reference covers all supported trajectory backends and their usage patterns for molecular dynamics visualization in NGLView.
