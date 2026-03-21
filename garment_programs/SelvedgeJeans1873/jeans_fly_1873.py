"""
1873 Jeans Fly (Two-Piece, cut on fold)
Based on: Historical Tailoring Masterclasses - Drafting the Fly and Waistband

Drafted from the completed front panel.  The fly piece is symmetric about
a fold line.  Only the half-piece is drawn; cut on fold to produce the full
fly.

Steps:
1. Draw a line parallel to the front fly line, 1 3/4" from the seam line.
2. Draw a curve at the bottom of the fly extension.
3. Copy outline to fresh sheet.
4. Add ~1" inlay at the top edge.
5. Cut on fold.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from garment_programs.core.runtime import cache_draft, resolve_measurements
from garment_programs.plot_utils import (
    SEAMLINE, CUTLINE, draw_seam_allowance, display_scale, setup_figure, finalize_figure,
)
from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _bezier_cubic, _curve_length, _annotate_segment,
)
from .seam_allowances import SEAM_ALLOWANCES, SEAM_LABELS


# -- Drafting ----------------------------------------------------------------

def draft_jeans_fly_1873(m, front):
    """Draft the 1873 two-piece fly (half-piece, cut on fold).

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
    # Fly height = length of the straight fly line (7' → 8)
    fly_height = np.linalg.norm(front['points']["7'"] - front['points']['8'])
    half_width = 1.75 * INCH   # 1 3/4" from seam line
    inlay = 1.0 * INCH         # extra at top to be trimmed

    # Standalone coordinate system:
    #   origin at bottom of fold line, Y up, X to the right
    fold_bottom = np.array([0.0, 0.0])
    fold_top = np.array([0.0, fly_height + inlay])
    outer_top = np.array([half_width, fly_height + inlay])
    # The outer edge runs straight down to where the bottom curve begins
    curve_start = np.array([half_width, fly_height * 0.15])

    # Bottom curve from curve_start back to the fold line
    curve_bottom = _bezier_cubic(
        curve_start,
        np.array([half_width, 0.0]),
        np.array([half_width * 0.3, 0.0]),
        fold_bottom,
    )

    return {
        'points': {
            'fold_bottom': fold_bottom,
            'fold_top': fold_top,
            'outer_top': outer_top,
            'curve_start': curve_start,
        },
        'curves': {
            'bottom': curve_bottom,
        },
        'construction': {
            'inlay_y': np.float64(fly_height),
        },
        'metadata': {
            'title': 'Fly',
            'cut_count': 2,
            'fly_height': fly_height,
            'half_width': half_width,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_fly_1873(fly, output_path='Logs/jeans_fly_1873.svg',
                        debug=False, units='cm', pdf_pages=None, ax=None,
                        include_seam_allowance=True):
    s, unit_label = display_scale(units)

    pts = {k: v * s for k, v in fly['points'].items()}
    curves = {k: v * s for k, v in fly['curves'].items()}
    con = {k: v * s for k, v in fly['construction'].items()}

    fig, ax, standalone = setup_figure(ax, figsize=(6, 12))
    SA = SEAM_ALLOWANCES['fly_1873']
    SL = SEAM_LABELS['fly_1873']

    # Fold line (dashed — visual reference, not a cut edge)
    ax.plot([pts['fold_bottom'][0], pts['fold_top'][0]],
            [pts['fold_bottom'][1], pts['fold_top'][1]],
            color='black', linewidth=1.5, linestyle='--')

    # Finished outline (individual segments for the seamline)
    OUTLINE = SEAMLINE
    ax.plot([pts['fold_top'][0], pts['outer_top'][0]],
            [pts['fold_top'][1], pts['outer_top'][1]], **OUTLINE)
    ax.plot([pts['outer_top'][0], pts['curve_start'][0]],
            [pts['outer_top'][1], pts['curve_start'][1]], **OUTLINE)
    ax.plot(curves['bottom'][:, 0], curves['bottom'][:, 1], **OUTLINE)

    # Seam allowance outline — single closed CUTLINE path.
    # Edges ordered CW (in matplotlib Y-up coords: top→right→bottom→left).
    # The fold edge (left side) gets SA=0 since the piece is cut on fold.
    sa_edges = [
        (np.array([pts['fold_top'], pts['outer_top']]),       SA['top'], SL['top']),
        (np.array([pts['outer_top'], pts['curve_start']]),    SA['outer'], SL['outer']),
        (curves['bottom'],                                     SA['bottom'], SL['bottom']),
        (np.array([pts['fold_bottom'], pts['fold_top']]),     SA['fold'], SL['fold']),
    ]
    if include_seam_allowance:
        cut_outline = draw_seam_allowance(ax, sa_edges, scale=s,
                                          label_sas=not debug, units=units)
    else:
        # Interfacing net shape: use the seamline/fold boundary (no SA).
        cut_outline = np.vstack([
            np.array([pts['fold_top'], pts['outer_top'], pts['curve_start']]),
            curves['bottom'],
            np.array([pts['fold_top']]),
        ])
        ax.plot(cut_outline[:, 0], cut_outline[:, 1], **CUTLINE)

    # Thin boundary line at the trim/inlay separation
    ax.plot([0, pts['outer_top'][0]],
            [con['inlay_y'], con['inlay_y']],
            color='dimgray', linewidth=0.8, linestyle='--')
    ax.annotate('trim here', (pts['outer_top'][0] / 2, con['inlay_y']),
                textcoords="offset points", xytext=(0, 5),
                fontsize=7, color='dimgray', ha='center')

    # Fold label
    mid_y = (pts['fold_bottom'][1] + pts['fold_top'][1]) / 2
    ax.annotate('FOLD', (pts['fold_bottom'][0] - 0.2 * s, mid_y),
                fontsize=8, ha='right', va='center', rotation=90)

    # --- Grainline and piece label (pattern mode only) ---
    if not debug:
        from garment_programs.plot_utils import draw_grainline, draw_piece_label
        # Grainline parallel to fold line (vertical, offset from fold)
        fly_height_s = fly['metadata']['fly_height'] * s
        grain_x = pts['outer_top'][0] * 0.5  # midway between fold and outer edge
        grain_top_pt = np.array([grain_x, fly_height_s * 0.85])
        grain_bot_pt = np.array([grain_x, fly_height_s * 0.15])
        draw_grainline(ax, grain_top_pt, grain_bot_pt)

        # Piece label
        center = (pts['outer_top'][0] / 2,
                  (pts['fold_bottom'][1] + pts['fold_top'][1]) / 2)
        draw_piece_label(ax, center, fly['metadata']['title'],
                         fly['metadata'].get('cut_count'),
                         metadata=fly.get('metadata'))

    if debug:
        for name, pt in pts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=5, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6)

        _annotate_segment(ax, pts['fold_top'], pts['outer_top'], offset=(0, 8))
        _annotate_segment(ax, pts['fold_bottom'],
                          np.array([0, con['inlay_y']]), offset=(-14, 0))

    return finalize_figure(ax, fig, standalone, output_path, units=units,
                           debug=debug, pdf_pages=pdf_pages,
                           outline_pts=cut_outline)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None,
        context=None, include_seam_allowance=True):
    m = resolve_measurements(context, measurements_path, load_measurements)
    front = cache_draft(context, 'selvedge.front', lambda: draft_jeans_front(m))
    fly = cache_draft(
        context,
        'selvedge.fly_1873',
        lambda: draft_jeans_fly_1873(m, front),
    )
    outline = plot_jeans_fly_1873(fly, output_path, debug=debug, units=units,
                                  pdf_pages=pdf_pages,
                                  include_seam_allowance=include_seam_allowance)
    if outline:
        return {'layout_outline': outline}
