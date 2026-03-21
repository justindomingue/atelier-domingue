"""
One-Piece Fly (Modern / Post-1877)
Based on: Historical Tailoring Masterclasses - Drafting the Fly and Waistband

The one-piece fly is a rectangle, folded in half.

Layout (left to right):
  1/2"   — seam allowance
  1 3/4" — front half
  -------- FOLD --------
  1 3/4" — back half
  1/2"   — seam allowance
  Total width = 4 1/2"

Length = 2 × fly_extension + 2"
  where fly_extension is the fly extension segment (7'→8) from the front panel.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from garment_programs.core.runtime import cache_draft, resolve_measurements
from garment_programs.plot_utils import (
    SEAMLINE, display_scale, setup_figure, finalize_figure,
)
from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _curve_length, _annotate_segment,
)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_fly_one_piece(m, front):
    """Draft the one-piece (modern) fly as a rectangle.

    Parameters
    ----------
    m : dict
        Measurements in cm.
    front : dict
        Result of ``draft_jeans_front(m)``.

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    fly_extension = np.linalg.norm(front['points']["7'"] - front['points']['8'])
    length = 2 * fly_extension + 2 * INCH
    width = 4.5 * INCH

    from .seam_allowances import SEAM_ALLOWANCES
    sa = SEAM_ALLOWANCES['fly_one_piece']['side']
    front_half = 1.75 * INCH    # front half width
    fold_x = sa + front_half    # fold line position

    bl = np.array([0.0, 0.0])
    br = np.array([width, 0.0])
    tr = np.array([width, length])
    tl = np.array([0.0, length])

    return {
        'points': {
            'bl': bl, 'br': br, 'tr': tr, 'tl': tl,
        },
        'curves': {},
        'construction': {
            'fold_x': np.float64(fold_x),
            'sa_left_x': np.float64(sa),
            'sa_right_x': np.float64(width - sa),
        },
        'metadata': {
            'title': 'Fly',
            'cut_count': 1,
            'length': length,
            'width': width,
            'fly_extension': fly_extension,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_fly_one_piece(fly, output_path='Logs/jeans_fly_one_piece.svg',
                          debug=False, units='cm', pdf_pages=None, ax=None):
    s, unit_label = display_scale(units)

    pts = {k: v * s for k, v in fly['points'].items()}
    con = {k: v * s for k, v in fly['construction'].items()}
    length_s = fly['metadata']['length'] * s
    width_s = fly['metadata']['width'] * s

    fig, ax, standalone = setup_figure(ax, figsize=(6, 14))
    OUTLINE = SEAMLINE

    # Rectangle
    xs = [0, width_s, width_s, 0, 0]
    ys = [0, 0, length_s, length_s, 0]
    ax.plot(xs, ys, **OUTLINE)

    # Fold line
    ax.plot([con['fold_x'], con['fold_x']], [0, length_s],
            color='black', linewidth=1.2, linestyle='--')
    ax.annotate('FOLD', (con['fold_x'], length_s / 2),
                textcoords="offset points", xytext=(4, 0),
                fontsize=8, ha='left', rotation=90)

    # --- Grainline and piece label (pattern mode only) ---
    if not debug:
        from garment_programs.plot_utils import draw_grainline, draw_piece_label
        # Grainline parallel to fold line (vertical)
        grain_x = con['fold_x']
        grain_top_pt = np.array([grain_x + width_s * 0.15, length_s * 0.85])
        grain_bot_pt = np.array([grain_x + width_s * 0.15, length_s * 0.15])
        draw_grainline(ax, grain_top_pt, grain_bot_pt)

        # Piece label
        center = (width_s / 2, length_s / 2)
        draw_piece_label(ax, center, fly['metadata']['title'],
                         fly['metadata'].get('cut_count'),
                         metadata=fly.get('metadata'))

    if debug:
        # Seam allowance lines
        ax.plot([con['sa_left_x'], con['sa_left_x']], [0, length_s],
                color='blue', linewidth=0.5, linestyle=':', alpha=0.5)
        ax.plot([con['sa_right_x'], con['sa_right_x']], [0, length_s],
                color='blue', linewidth=0.5, linestyle=':', alpha=0.5)
        ax.annotate('SA', (con['sa_left_x'] / 2, length_s / 2),
                    fontsize=6, ha='center', color='blue', rotation=90)
        ax.annotate('SA', ((con['sa_right_x'] + width_s) / 2, length_s / 2),
                    fontsize=6, ha='center', color='blue', rotation=90)

        # Section labels
        ax.annotate('front',
                    ((con['sa_left_x'] + con['fold_x']) / 2, length_s / 2),
                    fontsize=7, ha='center', va='center', color='gray',
                    rotation=90)
        ax.annotate('back',
                    ((con['fold_x'] + con['sa_right_x']) / 2, length_s / 2),
                    fontsize=7, ha='center', va='center', color='gray',
                    rotation=90)

        _annotate_segment(ax, pts['bl'], pts['br'], offset=(0, -10))
        _annotate_segment(ax, pts['br'], pts['tr'], offset=(10, 0))

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug,
                    pdf_pages=pdf_pages)


# -- Nesting Extractors -----------------------------------------------------

def get_outline_fly_one_piece(draft):
    """Return the full cut boundary for the one-piece fly.
    Since it is a simple rectangle rotated to align with the grainline/fold,
    the outline is exactly the bounding box points.
    """
    pts = draft['points']
    
    from garment_programs.plot_utils import offset_polyline
    from .seam_allowances import SEAM_ALLOWANCES
    SA = SEAM_ALLOWANCES['fly_one_piece']

    # CCW outline construction starting from top left
    outline = np.vstack([
        offset_polyline(np.array([pts['tr'], pts['tl']]), SA['top']),
        offset_polyline(np.array([pts['tl'], pts['bl']]), SA['side']),
        offset_polyline(np.array([pts['bl'], pts['br']]), SA['bottom']),
        offset_polyline(np.array([pts['br'], pts['tr']]), SA['side']),
    ])
    outline = np.vstack([outline, outline[0:1]])
    return outline

def get_sa_outline_fly_one_piece(draft):
    """Alias for getter as cutline and seamline logic is identical for rectangle packing."""
    return get_outline_fly_one_piece(draft)

# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None,
        context=None):
    m = resolve_measurements(context, measurements_path, load_measurements)
    front = cache_draft(context, 'selvedge.front', lambda: draft_jeans_front(m))
    fly = cache_draft(
        context,
        'selvedge.fly_one_piece',
        lambda: draft_jeans_fly_one_piece(m, front),
    )
    plot_jeans_fly_one_piece(fly, output_path, debug=debug, units=units,
                             pdf_pages=pdf_pages)
    return {'fly_one_piece': fly}

