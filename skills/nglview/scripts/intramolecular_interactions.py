#!/usr/bin/env python3
"""
Intramolecular Interaction Visualization with Arrow Overlays

Visualize intramolecular interactions (H-bonds, contacts, dihedrals) between
atom pairs using arrow shapes that update dynamically during trajectory playback.
Supports grid layouts for comparing multiple interaction sets side by side.

Usage (Jupyter Notebook):
    >>> import nglview as nv
    >>> import MDAnalysis as mda
    >>> from intramolecular_interactions import (
    ...     build_interaction_view,
    ...     build_comparison_grid,
    ... )

    # Single view with arrow overlays
    >>> u = mda.Universe('topology.pdb', 'trajectory.xtc')
    >>> atom_pairs = [('H1', 'O2'), ('H3', 'N1'), ('H5', 'O4')]
    >>> view = build_interaction_view(u, atom_pairs, resid=2)
    >>> view

    # Side-by-side comparison of interaction sets
    >>> interaction_sets = {
    ...     'Set A': [('H1', 'O2'), ('H3', 'N1')],
    ...     'Set B': [('H5', 'O4'), ('H7', 'O6')],
    ...     'Set C': [('H9', 'O8'), ('H11', 'N3')],
    ... }
    >>> grid = build_comparison_grid(u, interaction_sets, resid=2)
    >>> grid

Dependencies:
    - nglview
    - MDAnalysis
    - ipywidgets (for GridspecLayout)

Example:
    >>> import nglview as nv
    >>> view = nv.NGLWidget()
    >>> comp = view.add_component('catalyst.pdb')
    >>> view.clear_representations()
    >>> view.add_licorice()
"""

import nglview as nv
import MDAnalysis as mda
from ipywidgets import GridspecLayout


def build_interaction_view(
    universe,
    atom_pairs,
    resid=None,
    selection=None,
    arrow_color=None,
    arrow_radius=0.1,
    size=('600px', '600px'),
):
    """Create an NGLWidget with arrow overlays for atom pair interactions.

    Parameters
    ----------
    universe : mda.Universe
        MDAnalysis Universe with topology (and optionally trajectory).
    atom_pairs : list of tuple
        List of (atom_name_1, atom_name_2) pairs to draw arrows between.
    resid : int or None
        Residue ID to restrict the selection. If None, selects all.
    selection : mda.AtomGroup or None
        Pre-selected atom group to visualize. If None, selects based on resid.
    arrow_color : list of float or None
        RGB color for arrows as [r, g, b] with values 0-1.
        Default: [0, 0.502, 0.502] (teal).
    arrow_radius : float
        Radius of arrow shapes. Default: 0.1.
    size : tuple of str
        Widget size as (width, height). Default: ('600px', '600px').

    Returns
    -------
    nv.NGLWidget
        Widget with structure and arrow overlays.
    """
    if arrow_color is None:
        arrow_color = [0, 128 / 255, 128 / 255]

    resid_sel = f" and resid {resid}" if resid is not None else ""

    # Select atoms for visualization
    if selection is not None:
        atoms = selection
    else:
        atoms = universe.select_atoms(f"all{resid_sel}")

    # Build view with componentwise pattern (MANDATORY)
    view = nv.NGLWidget()
    comp = view.add_trajectory(atoms)
    view.clear_representations()
    view.add_licorice()

    view._set_size(size[0], size[1])
    view.center()

    # Draw initial arrows
    _draw_arrows(view, universe, atom_pairs, resid_sel, arrow_color, arrow_radius)

    # Register frame observer to update arrows on trajectory playback
    def _on_frame_change(change):
        _remove_shape_components(view)
        _draw_arrows(view, universe, atom_pairs, resid_sel, arrow_color, arrow_radius)

    view.observe(_on_frame_change, ['frame'])

    return view


def _draw_arrows(view, universe, atom_pairs, resid_sel, color, radius):
    """Draw arrow shapes between atom pairs at the current frame."""
    shapes = []
    for name1, name2 in atom_pairs:
        at1 = universe.select_atoms(f"name {name1}{resid_sel}")
        at2 = universe.select_atoms(f"name {name2}{resid_sel}")
        for i in range(len(at1.positions)):
            shapes.append((
                'arrow',
                at1.positions[i].tolist(),
                at2.positions[i].tolist(),
                color,
                radius,
            ))
    if shapes:
        view._add_shape(shapes, name='interactions')


def _remove_shape_components(view):
    """Remove all shape components (keeping the first structural component)."""
    # Shape components are added after the structure component (index 0)
    while len(view._ngl_component_ids) > 1:
        view.remove_component(view._ngl_component_ids[-1])


def build_comparison_grid(
    universe,
    interaction_sets,
    resid=None,
    selection=None,
    arrow_radius=0.1,
    size=('400px', '400px'),
):
    """Create a grid of views comparing different interaction sets.

    Parameters
    ----------
    universe : mda.Universe
        MDAnalysis Universe with topology (and optionally trajectory).
    interaction_sets : dict
        Dictionary mapping labels to lists of (atom1, atom2) pairs.
        Example: {'H-bonds': [('H1','O2')], 'Contacts': [('C1','C5')]}
    resid : int or None
        Residue ID to restrict the selection.
    selection : mda.AtomGroup or None
        Pre-selected atom group to visualize.
    arrow_radius : float
        Radius of arrow shapes.
    size : tuple of str
        Size of each individual view widget.

    Returns
    -------
    GridspecLayout
        ipywidgets grid with one view per interaction set.
    """
    # Color palette for different interaction sets
    colors = [
        [0, 128 / 255, 128 / 255],    # teal
        [200 / 255, 50 / 255, 50 / 255],   # red
        [50 / 255, 100 / 255, 200 / 255],  # blue
        [200 / 255, 150 / 255, 0],          # gold
        [100 / 255, 180 / 255, 50 / 255],   # green
    ]

    labels = list(interaction_sets.keys())
    n_cols = len(labels)
    grid = GridspecLayout(1, n_cols)

    for i, label in enumerate(labels):
        pairs = interaction_sets[label]
        color = colors[i % len(colors)]

        view = build_interaction_view(
            universe,
            pairs,
            resid=resid,
            selection=selection,
            arrow_color=color,
            arrow_radius=arrow_radius,
            size=size,
        )
        grid[0, i] = view

    return grid
