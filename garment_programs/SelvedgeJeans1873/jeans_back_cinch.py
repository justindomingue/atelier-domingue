"""
Back Cinch Belt
Based on: Historical Tailoring Masterclasses - Drafting the Back Cinch Belt

A tapered belt used on 1873 and other selvedge denim jeans.

Finished shape:
  Length = 5"
  Wide end (point 0)  = 5/8" + 5/8" = 1 1/4" total
  Narrow end (point 5) = 1/2" + 1/2" = 1" total  (fits standard buckle)

Seam allowances:
  Long edges at wide end:   3/4" each side
  Long edges at narrow end: 5/8" each side
  Short ends:               1/2" each end
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import INCH, load_measurements, _annotate_segment


# -- Drafting ----------------------------------------------------------------

def draft_jeans_back_cinch(m):
    """Draft the back cinch belt (tapered strip with SA).

    Parameters
    ----------
    m : dict
        Measurements in cm (not used — fixed dimensions).

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    length = 5 * INCH

    # Finished half-widths (from center line)
    wide_half = 5 / 8 * INCH
    narrow_half = 1 / 2 * INCH

    # Finished shape (centered on y = 0)
    f_tl = np.array([0.0, wide_half])
    f_bl = np.array([0.0, -wide_half])
    f_tr = np.array([length, narrow_half])
    f_br = np.array([length, -narrow_half])

    # Seam allowances
    from .seam_allowances import SEAM_ALLOWANCES
    _sa = SEAM_ALLOWANCES['back_cinch']
    sa_wide = _sa['wide']
    sa_narrow = _sa['narrow']
    sa_end = _sa['end']

    sa_tl = np.array([-sa_end, wide_half + sa_wide])
    sa_bl = np.array([-sa_end, -(wide_half + sa_wide)])
    sa_tr = np.array([length + sa_end, narrow_half + sa_narrow])
    sa_br = np.array([length + sa_end, -(narrow_half + sa_narrow)])

    return {
        'points': {
            'f_tl': f_tl, 'f_bl': f_bl, 'f_tr': f_tr, 'f_br': f_br,
            'sa_tl': sa_tl, 'sa_bl': sa_bl, 'sa_tr': sa_tr, 'sa_br': sa_br,
        },
        'curves': {},
        'construction': {},
        'metadata': {
            'title': 'Back Cinch Belt',
            'length': length,
            'cut_count': 1,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_back_cinch(cinch, output_path='Logs/jeans_back_cinch.svg',
                          debug=False, units='cm'):
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    pts = {k: v * s for k, v in cinch['points'].items()}

    fig, ax = plt.subplots(1, 1, figsize=(12, 4))
    LINE = dict(color='black', linewidth=1.5)
    SA_END = dict(color='red', linewidth=1.5)

    length_s = cinch['metadata']['length'] * s

    # -- Horizontal lines (5 levels: SA top, finished top, center,
    #    finished bottom, SA bottom) --
    for a, b in [('sa_tl', 'sa_tr'), ('f_tl', 'f_tr'),
                 ('f_bl', 'f_br'), ('sa_bl', 'sa_br')]:
        ax.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]], **LINE)
    # Center line
    ax.plot([0, length_s], [0, 0], **LINE)

    # -- Vertical lines at wide end (point 0) and narrow end (point 5) --
    ax.plot([pts['f_tl'][0], pts['f_tl'][0]],
            [pts['sa_tl'][1], pts['sa_bl'][1]], **LINE)
    ax.plot([pts['f_tr'][0], pts['f_tr'][0]],
            [pts['sa_tr'][1], pts['sa_br'][1]], **LINE)

    # -- 1/2" end SA verticals (red) --
    ax.plot([pts['sa_tl'][0], pts['sa_tl'][0]],
            [pts['sa_tl'][1], pts['sa_bl'][1]], **SA_END)
    ax.plot([pts['sa_tr'][0], pts['sa_tr'][0]],
            [pts['sa_tr'][1], pts['sa_br'][1]], **SA_END)

    # 1/2" labels beside the red end SA lines
    mid_y_left = (pts['sa_tl'][1] + pts['sa_bl'][1]) / 2
    ax.text(pts['sa_tl'][0] - 0.15 * s, mid_y_left, '1/2"',
            fontsize=12, ha='right', va='center')
    mid_y_right = (pts['sa_tr'][1] + pts['sa_br'][1]) / 2
    ax.text(pts['sa_tr'][0] + 0.15 * s, mid_y_right, '1/2"',
            fontsize=12, ha='left', va='center')

    # --- Grainline and piece label (pattern mode only) ---
    if not debug:
        from garment_programs.plot_utils import draw_grainline, draw_piece_label
        # Horizontal grainline along center line
        grain_left = np.array([length_s * 0.15, 0])
        grain_right = np.array([length_s * 0.85, 0])
        draw_grainline(ax, grain_right, grain_left)

        # Piece label
        center = (length_s / 2, 0)
        draw_piece_label(ax, center, cinch['metadata']['title'],
                         cinch['metadata'].get('cut_count'))

    if debug:
        for name, pt in pts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=4, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(4, 4), ha='left', fontsize=6)

        _annotate_segment(ax, pts['f_bl'], pts['f_br'], offset=(0, -10))
        _annotate_segment(ax, pts['f_tl'], pts['f_bl'], offset=(-14, 0))
        _annotate_segment(ax, pts['f_tr'], pts['f_br'], offset=(10, 0))

        ax.annotate('selvedge edge', (length_s / 2, pts['f_bl'][1]),
                    textcoords="offset points", xytext=(0, -6),
                    fontsize=6, color='gray', ha='center')

        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)
    else:
        ax.axis('off')

    from garment_programs.plot_utils import save_pattern
    save_pattern(fig, ax, output_path, units=units, calibration=not debug)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm'):
    m = load_measurements(measurements_path)
    cinch = draft_jeans_back_cinch(m)
    plot_jeans_back_cinch(cinch, output_path, debug=debug, units=units)
