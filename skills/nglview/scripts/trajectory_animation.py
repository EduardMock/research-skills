#!/usr/bin/env python3
"""
Trajectory Animation Generator

Create movies and animations from molecular dynamics trajectories or reaction
coordinates. Optimized for small molecules, catalysts, and reaction pathways.

Usage:
    # Generate GIF from reaction coordinate
    python trajectory_animation.py reaction.xyz --output movie.gif --fps 10

    # Generate MP4 with frame range
    python trajectory_animation.py --traj dynamics.xtc --top catalyst.gro \
        --output movie.mp4 --frames 0:100:2 --fps 15

    # High-quality rendering
    python trajectory_animation.py reaction.xyz --output hq_movie.mp4 \
        --width 1920 --height 1080 --fps 30

Dependencies:
    - nglview
    - mdtraj or pytraj or MDAnalysis (for trajectories)
    - jupyter notebook or jupyterlab
    - pillow (for GIF export)
    - imageio or moviepy (for MP4/AVI export)

Example:
    >>> from nglview.contrib.movie import MovieMaker
    >>> mov = MovieMaker(view, output='movie.gif', fps=10)
    >>> mov.make()
"""

import argparse
import sys
import time
from pathlib import Path


def parse_frame_range(frame_string, max_frame):
    """
    Parse frame range string like '0:100:2' into (start, stop, step).

    Args:
        frame_string (str): Frame range as 'start:stop:step' or 'all'
        max_frame (int): Maximum frame number

    Returns:
        tuple: (start, stop, step)
    """
    if frame_string == 'all' or frame_string is None:
        return 0, max_frame + 1, 1

    parts = frame_string.split(':')
    if len(parts) == 1:
        # Single frame
        frame = int(parts[0])
        return frame, frame + 1, 1
    elif len(parts) == 2:
        # Start and stop
        start = int(parts[0]) if parts[0] else 0
        stop = int(parts[1]) if parts[1] else max_frame + 1
        return start, stop, 1
    elif len(parts) == 3:
        # Start, stop, and step
        start = int(parts[0]) if parts[0] else 0
        stop = int(parts[1]) if parts[1] else max_frame + 1
        step = int(parts[2]) if parts[2] else 1
        return start, stop, step
    else:
        raise ValueError(f"Invalid frame range: {frame_string}")


def load_trajectory(traj_file, top_file=None, backend='mdtraj'):
    """
    Load trajectory with appropriate backend.

    Args:
        traj_file (str): Path to trajectory file
        top_file (str): Path to topology file (if needed)
        backend (str): Backend to use

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

    elif backend == 'file':
        view = nv.NGLWidget()
        comp = view.add_component(traj_file)
        view.clear_representations()
        return view

    else:
        raise ValueError(f"Unknown backend: {backend}")


def setup_visualization(view, repr_type='ball_and_stick', color='element',
                       selection='all', camera='perspective'):
    """
    Configure visualization for animation.

    Args:
        view: NGLView widget
        repr_type (str): Representation type
        color (str): Color scheme
        selection (str): Atom selection
        camera (str): Camera mode ('perspective' or 'orthographic')
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

    # Center and camera
    view.center(selection=selection)
    view.camera = camera


def create_movie_moviemaker(view, output_file, start=0, stop=None, step=1,
                           fps=10, width=None, height=None):
    """
    Create movie using NGLView's MovieMaker class.

    Args:
        view: NGLView widget
        output_file (str): Output filename (.gif, .mp4, .avi)
        start (int): Starting frame
        stop (int): Ending frame
        step (int): Frame step
        fps (int): Frames per second
        width (int): Image width (optional)
        height (int): Image height (optional)
    """
    from nglview.contrib.movie import MovieMaker

    if stop is None:
        stop = view.max_frame + 1

    print(f"Creating movie with MovieMaker...")
    print(f"  Frames: {start} to {stop} (step {step})")
    print(f"  FPS: {fps}")
    print(f"  Output: {output_file}")

    # Create MovieMaker instance
    movie_params = {
        'output': output_file,
        'start': start,
        'stop': stop,
        'step': step,
        'fps': fps,
    }

    # Add size if specified
    if width and height:
        movie_params['size'] = (width, height)
        print(f"  Size: {width} x {height}")

    mov = MovieMaker(view, **movie_params)

    # Generate movie
    print("Rendering frames...")
    mov.make()
    print(f"Movie saved to: {output_file}")


def create_movie_manual(view, output_file, start=0, stop=None, step=1,
                       fps=10, width=800, height=600):
    """
    Create movie manually by iterating frames and capturing images.

    This method provides more control but requires manual implementation.

    Args:
        view: NGLView widget
        output_file (str): Output filename
        start (int): Starting frame
        stop (int): Ending frame
        step (int): Frame step
        fps (int): Frames per second
        width (int): Image width
        height (int): Image height
    """
    import imageio

    if stop is None:
        stop = view.max_frame + 1

    frames_to_render = list(range(start, stop, step))
    images = []

    print(f"Rendering {len(frames_to_render)} frames manually...")

    for i, frame_num in enumerate(frames_to_render):
        # Set frame
        view.frame = frame_num

        # Wait for rendering
        time.sleep(0.1)

        # Capture image
        img_data = view.render_image(factor=2, trim=False, transparent=False)

        if img_data:
            images.append(img_data)

        # Progress
        if (i + 1) % 10 == 0:
            print(f"  Rendered {i + 1}/{len(frames_to_render)} frames")

    # Save as movie
    print(f"Saving movie to {output_file}...")
    imageio.mimsave(output_file, images, fps=fps)
    print(f"Movie saved to: {output_file}")


def preview_animation(view, start=0, stop=None, step=1, delay=0.1):
    """
    Preview animation in Jupyter by cycling through frames.

    Args:
        view: NGLView widget
        start (int): Starting frame
        stop (int): Ending frame
        step (int): Frame step
        delay (float): Delay between frames (seconds)
    """
    if stop is None:
        stop = view.max_frame + 1

    frames_to_show = list(range(start, stop, step))

    print(f"Previewing animation: {len(frames_to_show)} frames")
    print("(To stop, interrupt the kernel)")

    try:
        while True:
            for frame_num in frames_to_show:
                view.frame = frame_num
                time.sleep(delay)
    except KeyboardInterrupt:
        print("\nAnimation stopped")


def main():
    """Main entry point for trajectory animation."""
    parser = argparse.ArgumentParser(
        description='Create movies from molecular trajectories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create GIF from reaction coordinate (XYZ file)
  python trajectory_animation.py reaction.xyz --output movie.gif --fps 10

  # Create MP4 with frame selection
  python trajectory_animation.py --traj dynamics.xtc --top catalyst.gro \
      --output movie.mp4 --frames 0:100:2 --fps 15

  # High-quality rendering
  python trajectory_animation.py reaction.xyz --output hq_movie.mp4 \
      --width 1920 --height 1080 --fps 30

  # Preview animation in notebook
  python trajectory_animation.py reaction.xyz --preview
        """
    )

    # Input files
    parser.add_argument('structure', nargs='?',
                       help='Structure/trajectory file (XYZ, PDB, etc.)')
    parser.add_argument('--traj', help='Trajectory file')
    parser.add_argument('--top', help='Topology file')

    # Output
    parser.add_argument('--output', '-o', default='movie.gif',
                       help='Output filename (.gif, .mp4, .avi)')

    # Frame selection
    parser.add_argument('--frames', default='all',
                       help='Frame range as start:stop:step (e.g., 0:100:2)')
    parser.add_argument('--fps', type=int, default=10,
                       help='Frames per second (default: 10)')

    # Visualization
    parser.add_argument('--repr', default='ball_and_stick',
                       choices=['ball_and_stick', 'licorice', 'spacefill', 'line'],
                       help='Representation type')
    parser.add_argument('--color', default='element',
                       help='Color scheme')
    parser.add_argument('--selection', default='all',
                       help='Atom selection')

    # Rendering quality
    parser.add_argument('--width', type=int, help='Image width')
    parser.add_argument('--height', type=int, help='Image height')

    # Backend
    parser.add_argument('--backend', default='mdtraj',
                       choices=['mdtraj', 'pytraj', 'mdanalysis', 'file'],
                       help='Backend library')

    # Preview mode
    parser.add_argument('--preview', action='store_true',
                       help='Preview animation instead of saving')
    parser.add_argument('--delay', type=float, default=0.1,
                       help='Delay between frames in preview mode (seconds)')

    # Method
    parser.add_argument('--method', default='moviemaker',
                       choices=['moviemaker', 'manual'],
                       help='Movie generation method')

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
        print("2. Create notebook and run: %run trajectory_animation.py <file>")
        sys.exit(1)

    # Load trajectory
    if args.traj:
        traj_file = args.traj
        top_file = args.top
        print(f"Loading trajectory: {traj_file}")
    elif args.structure:
        traj_file = args.structure
        top_file = None
        print(f"Loading structure: {traj_file}")
    else:
        parser.print_help()
        sys.exit(1)

    view = load_trajectory(traj_file, top_file, args.backend)

    # Setup visualization
    setup_visualization(view, args.repr, args.color, args.selection)

    # Parse frame range
    start, stop, step = parse_frame_range(args.frames, view.max_frame)

    print(f"\nTrajectory info:")
    print(f"  Total frames: {view.max_frame + 1}")
    print(f"  Selected frames: {start}:{stop}:{step}")
    print(f"  Frames to render: {len(range(start, stop, step))}")

    # Preview or create movie
    if args.preview:
        print("\nPreviewing animation...")
        preview_animation(view, start, stop, step, args.delay)
        return view
    else:
        # Create movie
        if args.method == 'moviemaker':
            create_movie_moviemaker(view, args.output, start, stop, step,
                                   args.fps, args.width, args.height)
        else:
            create_movie_manual(view, args.output, start, stop, step,
                               args.fps, args.width or 800, args.height or 600)

        print("\nDone!")
        return view


if __name__ == '__main__':
    view = main()
    display(view)  # noqa: F821
