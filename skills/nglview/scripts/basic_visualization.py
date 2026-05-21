#!/usr/bin/env python3
"""
Basic NGLView Visualization Template

Load and visualize molecular structures and trajectories for small molecules,
catalysts, and complexes.

Usage:
    # Single structure file
    python basic_visualization.py catalyst.pdb

    # Trajectory with topology
    python basic_visualization.py --traj reaction.xtc --top catalyst.gro

    # XYZ file from QM calculation
    python basic_visualization.py reaction_path.xyz

    # Custom representation
    python basic_visualization.py complex.pdb --repr ball_and_stick --color element

Dependencies:
    - nglview
    - mdtraj or pytraj or MDAnalysis (for trajectories)
    - jupyter notebook or jupyterlab

Example:
    >>> import nglview as nv
    >>> view = nv.NGLWidget()
    >>> comp = view.add_component('catalyst.pdb')
    >>> view.clear_representations()
    >>> view.add_ball_and_stick(selection='all')
    >>> view
"""

import argparse
import sys
from pathlib import Path


def detect_backend(traj_file, top_file=None):
    """
    Detect appropriate backend based on file extensions.

    Returns:
        str: Backend name ('mdtraj', 'pytraj', 'mdanalysis', or 'file')
    """
    traj_ext = Path(traj_file).suffix.lower()

    # Gromacs formats - prefer MDTraj or Simpletraj
    if traj_ext in ['.xtc', '.trr', '.gro']:
        return 'mdtraj'

    # Amber formats - prefer PyTraj
    elif traj_ext in ['.nc', '.netcdf', '.rst7']:
        return 'pytraj'

    # CHARMM/NAMD DCD - prefer MDTraj
    elif traj_ext == '.dcd':
        return 'mdtraj'

    # XYZ files from QM - use MDTraj
    elif traj_ext == '.xyz':
        return 'mdtraj'

    # PDB files - direct loading
    elif traj_ext == '.pdb':
        return 'file'

    # Default to MDTraj (most versatile)
    else:
        return 'mdtraj'


def load_structure(structure_file, backend='file'):
    """
    Load a single structure file.

    Args:
        structure_file (str): Path to structure file
        backend (str): Loading method ('file' or backend library)

    Returns:
        nglview widget
    """
    import nglview as nv

    if backend == 'file':
        view = nv.NGLWidget()
        comp = view.add_component(structure_file)
        view.clear_representations()
    else:
        # Use trajectory loading even for single structure
        view = load_trajectory(structure_file, None, backend)

    return view


def load_trajectory(traj_file, top_file=None, backend='mdtraj'):
    """
    Load a trajectory with specified backend.

    Args:
        traj_file (str): Path to trajectory file
        top_file (str): Path to topology file (required for some formats)
        backend (str): Backend library to use

    Returns:
        nglview widget
    """
    import nglview as nv

    if backend == 'mdtraj':
        try:
            import mdtraj as md
            if top_file:
                traj = md.load(traj_file, top=top_file)
            else:
                traj = md.load(traj_file)
            view = nv.NGLWidget()
            comp = view.add_trajectory(traj)
            view.clear_representations()
            return view
        except ImportError:
            print("Error: mdtraj not installed. Install with: pip install mdtraj")
            sys.exit(1)

    elif backend == 'pytraj':
        try:
            import pytraj as pt
            if top_file:
                traj = pt.load(traj_file, top=top_file)
            else:
                traj = pt.load(traj_file)
            view = nv.NGLWidget()
            comp = view.add_trajectory(traj)
            view.clear_representations()
            return view
        except ImportError:
            print("Error: pytraj not installed. Install with: conda install pytraj -c ambermd")
            sys.exit(1)

    elif backend == 'mdanalysis':
        try:
            from MDAnalysis import Universe
            if top_file:
                u = Universe(top_file, traj_file)
            else:
                u = Universe(traj_file)
            view = nv.NGLWidget()
            comp = view.add_trajectory(u)
            view.clear_representations()
            return view
        except ImportError:
            print("Error: MDAnalysis not installed. Install with: pip install MDAnalysis")
            sys.exit(1)

    else:
        print(f"Error: Unknown backend '{backend}'")
        sys.exit(1)


def setup_representation(view, repr_type='ball_and_stick', color='element', selection='all'):
    """
    Configure visualization representation for small molecules.

    Args:
        view: NGLView widget
        repr_type (str): Representation type
        color (str): Color scheme
        selection (str): Atom selection
    """
    # Clear default representations
    view.clear_representations()

    # Add requested representation
    if repr_type == 'ball_and_stick':
        view.add_ball_and_stick(selection=selection, color=color)
    elif repr_type == 'licorice':
        view.add_licorice(selection=selection, color=color)
    elif repr_type == 'spacefill':
        view.add_spacefill(selection=selection, color=color)
    elif repr_type == 'line':
        view.add_line(selection=selection, color=color)
    else:
        view.add_representation(repr_type, selection=selection, color=color)

    # Center view
    view.center(selection=selection)


def main():
    """Main entry point for basic visualization."""
    parser = argparse.ArgumentParser(
        description='Visualize molecular structures and trajectories with NGLView',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Visualize PDB file
  python basic_visualization.py catalyst.pdb

  # Visualize Gromacs trajectory
  python basic_visualization.py --traj reaction.xtc --top system.gro

  # Visualize with custom representation
  python basic_visualization.py complex.pdb --repr licorice --color element

  # Visualize XYZ from QM calculation
  python basic_visualization.py reaction_coordinate.xyz --repr ball_and_stick
        """
    )

    parser.add_argument('structure', nargs='?', help='Structure file (PDB, XYZ, etc.)')
    parser.add_argument('--traj', help='Trajectory file')
    parser.add_argument('--top', help='Topology file (required for some trajectory formats)')
    parser.add_argument('--repr', default='ball_and_stick',
                       choices=['ball_and_stick', 'licorice', 'spacefill', 'line'],
                       help='Representation type (default: ball_and_stick)')
    parser.add_argument('--color', default='element',
                       help='Color scheme (default: element)')
    parser.add_argument('--selection', default='all',
                       help='Atom selection (default: all)')
    parser.add_argument('--backend', choices=['mdtraj', 'pytraj', 'mdanalysis', 'auto'],
                       default='auto',
                       help='Backend library to use (default: auto-detect)')

    args = parser.parse_args()

    # Check if running in Jupyter
    try:
        get_ipython()  # noqa: F821
        in_jupyter = True
    except NameError:
        in_jupyter = False

    if not in_jupyter:
        print("Warning: This script is designed to run in Jupyter notebooks.")
        print("The visualization will not display in a regular terminal.")
        print("\nTo use this script:")
        print("1. Start Jupyter: jupyter notebook")
        print("2. Create a new notebook")
        print("3. Run: %run basic_visualization.py <your_file>")
        print("\nOr import and use the functions directly in your notebook.")
        sys.exit(0)

    # Determine input file
    if args.traj:
        traj_file = args.traj
        top_file = args.top

        # Auto-detect backend if requested
        if args.backend == 'auto':
            backend = detect_backend(traj_file, top_file)
        else:
            backend = args.backend

        print(f"Loading trajectory: {traj_file}")
        if top_file:
            print(f"Topology: {top_file}")
        print(f"Backend: {backend}")

        view = load_trajectory(traj_file, top_file, backend)

    elif args.structure:
        structure_file = args.structure

        # Auto-detect backend if requested
        if args.backend == 'auto':
            backend = detect_backend(structure_file)
        else:
            backend = args.backend

        print(f"Loading structure: {structure_file}")
        print(f"Backend: {backend}")

        view = load_structure(structure_file, backend)

    else:
        parser.print_help()
        sys.exit(1)

    # Setup representation
    setup_representation(view, args.repr, args.color, args.selection)

    # Print info
    print(f"\nVisualization ready!")
    print(f"Representation: {args.repr}")
    print(f"Color: {args.color}")
    print(f"Selection: {args.selection}")

    if hasattr(view, 'max_frame'):
        print(f"Total frames: {view.max_frame + 1}")

    # Return view for display
    return view


if __name__ == '__main__':
    view = main()
    # Display in Jupyter
    display(view)  # noqa: F821
