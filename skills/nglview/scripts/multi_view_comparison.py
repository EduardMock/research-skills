#!/usr/bin/env python3
"""
Multi-View Comparison

Create synchronized side-by-side views of molecular structures for comparison.
Ideal for comparing stereoisomers, conformers, reaction intermediates, or
highlighting different regions of the same catalyst.

Usage:
    # Compare two stereoisomers
    python multi_view_comparison.py isomer_R.pdb isomer_S.pdb

    # Compare same structure with different views
    python multi_view_comparison.py catalyst.pdb --focus1 "_Pd" --focus2 "1-20"

    # Trajectory comparison at different frames
    python multi_view_comparison.py --traj reaction.xyz --top catalyst.pdb \
        --frame1 0 --frame2 50

Dependencies:
    - nglview
    - mdtraj or pytraj or MDAnalysis (for trajectories)
    - jupyter notebook or jupyterlab
    - ipywidgets (for layout)

Example:
    >>> view1 = nv.NGLWidget()
    >>> comp1 = view1.add_component('isomer1.pdb')
    >>> view1.clear_representations()
    >>> view2 = nv.NGLWidget()
    >>> comp2 = view2.add_component('isomer2.pdb')
    >>> view2.clear_representations()
    >>> view1._set_sync_camera([view2])  # Sync camera rotation
"""

import argparse
import sys
from pathlib import Path


def load_structure(structure_file, backend='file'):
    """
    Load a structure file.

    Args:
        structure_file (str): Path to structure file
        backend (str): Loading backend

    Returns:
        nglview widget
    """
    import nglview as nv

    if backend == 'file':
        view = nv.NGLWidget()
        comp = view.add_component(structure_file)
        view.clear_representations()
        return view
    elif backend == 'mdtraj':
        import mdtraj as md
        traj = md.load(structure_file)
        view = nv.NGLWidget()
        comp = view.add_trajectory(traj)
        view.clear_representations()
        return view
    elif backend == 'pytraj':
        import pytraj as pt
        traj = pt.load(structure_file)
        view = nv.NGLWidget()
        comp = view.add_trajectory(traj)
        view.clear_representations()
        return view
    elif backend == 'mdanalysis':
        from MDAnalysis import Universe
        u = Universe(structure_file)
        view = nv.NGLWidget()
        comp = view.add_trajectory(u)
        view.clear_representations()
        return view
    else:
        raise ValueError(f"Unknown backend: {backend}")


def load_trajectory(traj_file, top_file=None, backend='mdtraj'):
    """
    Load trajectory with topology.

    Args:
        traj_file (str): Path to trajectory file
        top_file (str): Path to topology file
        backend (str): Loading backend

    Returns:
        nglview widget
    """
    import nglview as nv

    if backend == 'mdtraj':
        import mdtraj as md
        if top_file:
            traj = md.load(traj_file, top=top_file)
        else:
            traj = md.load(traj_file)
        view = nv.NGLWidget()
        comp = view.add_trajectory(traj)
        view.clear_representations()
        return view

    elif backend == 'pytraj':
        import pytraj as pt
        if top_file:
            traj = pt.load(traj_file, top=top_file)
        else:
            traj = pt.load(traj_file)
        view = nv.NGLWidget()
        comp = view.add_trajectory(traj)
        view.clear_representations()
        return view

    elif backend == 'mdanalysis':
        from MDAnalysis import Universe
        if top_file:
            u = Universe(top_file, traj_file)
        else:
            u = Universe(traj_file)
        view = nv.NGLWidget()
        comp = view.add_trajectory(u)
        view.clear_representations()
        return view

    else:
        raise ValueError(f"Unknown backend: {backend}")


def setup_representation(view, repr_type='ball_and_stick', color='element',
                        selection='all', focus=None):
    """
    Configure representation and focus.

    Args:
        view: NGLView widget
        repr_type (str): Representation type
        color (str): Color scheme
        selection (str): Atom selection for representation
        focus (str): Selection to center on (None for all)
    """
    # Clear default representations
    view.clear_representations()

    # Add representation
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

    # Center on focus or all
    if focus:
        view.center(selection=focus)
    else:
        view.center(selection=selection)


def sync_views(view1, view2, sync_camera=True, sync_repr=False):
    """
    Synchronize two views.

    Args:
        view1: First NGLView widget (master)
        view2: Second NGLView widget (slave)
        sync_camera (bool): Synchronize camera rotation/zoom
        sync_repr (bool): Synchronize representations
    """
    if sync_camera:
        view1._set_sync_camera([view2])
        print("Camera synchronization enabled")

    if sync_repr:
        view1._set_sync_repr([view2])
        print("Representation synchronization enabled")


def create_layout(view1, view2, layout='horizontal', labels=None):
    """
    Create layout for multiple views.

    Args:
        view1: First NGLView widget
        view2: Second NGLView widget
        layout (str): 'horizontal' or 'vertical'
        labels (list): Optional labels for views

    Returns:
        ipywidgets layout widget
    """
    from ipywidgets import HBox, VBox, Label

    # Create labels if provided
    if labels:
        label1 = Label(value=labels[0])
        label2 = Label(value=labels[1])

        if layout == 'horizontal':
            return HBox([
                VBox([label1, view1]),
                VBox([label2, view2])
            ])
        else:  # vertical
            return VBox([
                HBox([label1]),
                view1,
                HBox([label2]),
                view2
            ])
    else:
        if layout == 'horizontal':
            return HBox([view1, view2])
        else:  # vertical
            return VBox([view1, view2])


def compare_structures(file1, file2, repr1='ball_and_stick', repr2='ball_and_stick',
                      color1='element', color2='element', focus1='all', focus2='all',
                      sync_camera=True, layout='horizontal', labels=None):
    """
    Compare two different structures side by side.

    Args:
        file1 (str): First structure file
        file2 (str): Second structure file
        repr1 (str): Representation for first view
        repr2 (str): Representation for second view
        color1 (str): Color scheme for first view
        color2 (str): Color scheme for second view
        focus1 (str): Focus selection for first view
        focus2 (str): Focus selection for second view
        sync_camera (bool): Synchronize camera
        layout (str): Layout orientation
        labels (list): View labels

    Returns:
        ipywidgets layout widget
    """
    # Load structures
    view1 = load_structure(file1)
    view2 = load_structure(file2)

    # Setup representations
    setup_representation(view1, repr1, color1, 'all', focus1)
    setup_representation(view2, repr2, color2, 'all', focus2)

    # Synchronize
    if sync_camera:
        sync_views(view1, view2, sync_camera=True, sync_repr=False)

    # Create layout
    return create_layout(view1, view2, layout, labels)


def compare_same_structure(structure_file, focus1='all', focus2='all',
                          repr1='ball_and_stick', repr2='ball_and_stick',
                          color1='element', color2='element',
                          sync_camera=True, layout='horizontal', labels=None):
    """
    Compare different views of the same structure.

    Args:
        structure_file (str): Structure file
        focus1 (str): Focus selection for first view
        focus2 (str): Focus selection for second view
        repr1 (str): Representation for first view
        repr2 (str): Representation for second view
        color1 (str): Color scheme for first view
        color2 (str): Color scheme for second view
        sync_camera (bool): Synchronize camera
        layout (str): Layout orientation
        labels (list): View labels

    Returns:
        ipywidgets layout widget
    """
    # Load same structure twice
    view1 = load_structure(structure_file)
    view2 = load_structure(structure_file)

    # Setup different representations/focuses
    setup_representation(view1, repr1, color1, 'all', focus1)
    setup_representation(view2, repr2, color2, 'all', focus2)

    # Synchronize
    if sync_camera:
        sync_views(view1, view2, sync_camera=True, sync_repr=False)

    # Create layout
    return create_layout(view1, view2, layout, labels)


def compare_trajectory_frames(traj_file, top_file=None, frame1=0, frame2=None,
                             repr_type='ball_and_stick', color='element',
                             focus='all', sync_camera=True, layout='horizontal',
                             labels=None, backend='mdtraj'):
    """
    Compare different frames of the same trajectory.

    Args:
        traj_file (str): Trajectory file
        top_file (str): Topology file
        frame1 (int): First frame number
        frame2 (int): Second frame number (None = last frame)
        repr_type (str): Representation type
        color (str): Color scheme
        focus (str): Focus selection
        sync_camera (bool): Synchronize camera
        layout (str): Layout orientation
        labels (list): View labels
        backend (str): Loading backend

    Returns:
        ipywidgets layout widget
    """
    # Load trajectory twice
    view1 = load_trajectory(traj_file, top_file, backend)
    view2 = load_trajectory(traj_file, top_file, backend)

    # Set frames
    view1.frame = frame1
    if frame2 is None:
        view2.frame = view2.max_frame
    else:
        view2.frame = frame2

    # Setup representations
    setup_representation(view1, repr_type, color, 'all', focus)
    setup_representation(view2, repr_type, color, 'all', focus)

    # Synchronize
    if sync_camera:
        sync_views(view1, view2, sync_camera=True, sync_repr=False)

    # Create layout with frame info in labels
    if labels is None:
        labels = [f"Frame {frame1}", f"Frame {frame2 if frame2 else view2.max_frame}"]

    return create_layout(view1, view2, layout, labels)


def main():
    """Main entry point for multi-view comparison."""
    parser = argparse.ArgumentParser(
        description='Create side-by-side molecular structure comparisons',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two stereoisomers
  python multi_view_comparison.py isomer_R.pdb isomer_S.pdb

  # Compare different views of same structure
  python multi_view_comparison.py catalyst.pdb --focus1 "_Pd" --focus2 "1-20"

  # Compare trajectory frames
  python multi_view_comparison.py --traj reaction.xyz --frame1 0 --frame2 50

  # Compare with custom representations
  python multi_view_comparison.py complex1.pdb complex2.pdb \
      --repr1 ball_and_stick --repr2 licorice --color1 element --color2 residue
        """
    )

    # Input files
    parser.add_argument('structure1', nargs='?', help='First structure file')
    parser.add_argument('structure2', nargs='?', help='Second structure file (optional)')
    parser.add_argument('--traj', help='Trajectory file for frame comparison')
    parser.add_argument('--top', help='Topology file for trajectory')

    # Frame selection (for trajectories)
    parser.add_argument('--frame1', type=int, default=0,
                       help='First frame number (default: 0)')
    parser.add_argument('--frame2', type=int,
                       help='Second frame number (default: last frame)')

    # Representations
    parser.add_argument('--repr1', default='ball_and_stick',
                       help='Representation for first view')
    parser.add_argument('--repr2', default='ball_and_stick',
                       help='Representation for second view')

    # Colors
    parser.add_argument('--color1', default='element',
                       help='Color scheme for first view')
    parser.add_argument('--color2', default='element',
                       help='Color scheme for second view')

    # Focus selections
    parser.add_argument('--focus1', default='all',
                       help='Selection to center first view on')
    parser.add_argument('--focus2', default='all',
                       help='Selection to center second view on')

    # Layout
    parser.add_argument('--layout', default='horizontal',
                       choices=['horizontal', 'vertical'],
                       help='Layout orientation')
    parser.add_argument('--label1', help='Label for first view')
    parser.add_argument('--label2', help='Label for second view')
    parser.add_argument('--no-sync', action='store_true',
                       help='Disable camera synchronization')

    # Backend
    parser.add_argument('--backend', default='mdtraj',
                       choices=['mdtraj', 'pytraj', 'mdanalysis', 'file'],
                       help='Backend library')

    args = parser.parse_args()

    # Check if in Jupyter
    try:
        get_ipython()  # noqa: F821
        in_jupyter = True
    except NameError:
        in_jupyter = False

    if not in_jupyter:
        print("Error: This script must run in Jupyter notebooks.")
        print("\nTo use:")
        print("1. Start Jupyter: jupyter notebook")
        print("2. Create notebook and run: %run multi_view_comparison.py <files>")
        sys.exit(1)

    # Create labels if provided
    labels = None
    if args.label1 and args.label2:
        labels = [args.label1, args.label2]

    sync_camera = not args.no_sync

    # Determine comparison mode
    if args.traj:
        # Trajectory frame comparison
        print(f"Comparing trajectory frames: {args.traj}")
        print(f"Frame 1: {args.frame1}")
        print(f"Frame 2: {args.frame2 if args.frame2 else 'last'}")

        widget = compare_trajectory_frames(
            args.traj, args.top, args.frame1, args.frame2,
            args.repr1, args.color1, args.focus1,
            sync_camera, args.layout, labels, args.backend
        )

    elif args.structure1 and args.structure2:
        # Two different structures
        print(f"Comparing structures:")
        print(f"  1: {args.structure1}")
        print(f"  2: {args.structure2}")

        widget = compare_structures(
            args.structure1, args.structure2,
            args.repr1, args.repr2, args.color1, args.color2,
            args.focus1, args.focus2, sync_camera, args.layout, labels
        )

    elif args.structure1:
        # Same structure, different views
        print(f"Comparing views of: {args.structure1}")
        print(f"Focus 1: {args.focus1}")
        print(f"Focus 2: {args.focus2}")

        widget = compare_same_structure(
            args.structure1, args.focus1, args.focus2,
            args.repr1, args.repr2, args.color1, args.color2,
            sync_camera, args.layout, labels
        )

    else:
        parser.print_help()
        sys.exit(1)

    print("\nMulti-view comparison ready!")
    print(f"Layout: {args.layout}")
    print(f"Camera sync: {'enabled' if sync_camera else 'disabled'}")

    return widget


if __name__ == '__main__':
    widget = main()
    display(widget)  # noqa: F821
