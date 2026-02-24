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

from garment_programs.plot_utils import display_scale, setup_figure, finalize_figure
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
                          debug=False, units='cm', pdf_pages=None, ax=None):
    s, unit_label = display_scale(units)

    pts = {k: v * s for k, v in cinch['points'].items()}

    # Rotate the whole piece so the bottom SA edge is horizontal (grainline
    # parallel to the selvedge).  Applied here so the draft stays clean.
    sel_dir = pts['sa_br'] - pts['sa_bl']
    angle = np.arctan2(sel_dir[1], sel_dir[0])
    ca, sn = np.cos(-angle), np.sin(-angle)
    R = np.array([[ca, -sn], [sn, ca]])
    pivot = pts['f_bl'].copy()
    pts = {k: pivot + R @ (v - pivot) for k, v in pts.items()}

    fig, ax, standalone = setup_figure(ax, figsize=(12, 4))
    LINE = dict(color='black', linewidth=1.5)

    # -- Long edges (SA top, finished top, center, finished bottom, SA bottom) --
    for a, b in [('sa_tl', 'sa_tr'), ('f_tl', 'f_tr'),
                 ('f_bl', 'f_br'), ('sa_bl', 'sa_br')]:
        ax.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]], **LINE)
    # Center line (midpoints of finished ends)
    center_l = (pts['f_tl'] + pts['f_bl']) / 2
    center_r = (pts['f_tr'] + pts['f_br']) / 2
    ax.plot([center_l[0], center_r[0]], [center_l[1], center_r[1]], **LINE)

    # -- End lines at wide end and narrow end --
    for t, b in [('f_tl', 'f_bl'), ('f_tr', 'f_br'),
                 ('sa_tl', 'sa_bl'), ('sa_tr', 'sa_br')]:
        ax.plot([pts[t][0], pts[b][0]], [pts[t][1], pts[b][1]], **LINE)

    # 1/2" labels beside the end SA lines
    mid_left = (pts['sa_tl'] + pts['sa_bl']) / 2
    ax.text(mid_left[0] - 0.15 * s, mid_left[1], '1/2"',
            fontsize=12, ha='right', va='center')
    mid_right = (pts['sa_tr'] + pts['sa_br']) / 2
    ax.text(mid_right[0] + 0.15 * s, mid_right[1], '1/2"',
            fontsize=12, ha='left', va='center')

    # --- Grainline and piece label (pattern mode only) ---
    if not debug:
        from garment_programs.plot_utils import draw_grainline, draw_piece_label
        # Grainline along the selvedge direction (now horizontal)
        center = (center_l + center_r) / 2
        sel_norm = sel_dir / np.linalg.norm(sel_dir)
        grain_half = np.linalg.norm(center_r - center_l) * 0.35
        grain_left = center - np.array([grain_half, 0])
        grain_right = center + np.array([grain_half, 0])
        draw_grainline(ax, grain_right, grain_left)

        # Piece label
        draw_piece_label(ax, (center[0], center[1]), cinch['metadata']['title'],
                         cinch['metadata'].get('cut_count'))

    if debug:
        for name, pt in pts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=4, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(4, 4), ha='left', fontsize=6)

        _annotate_segment(ax, pts['f_bl'], pts['f_br'], offset=(0, -10))
        _annotate_segment(ax, pts['f_tl'], pts['f_bl'], offset=(-14, 0))
        _annotate_segment(ax, pts['f_tr'], pts['f_br'], offset=(10, 0))

        sel_mid = (pts['f_bl'] + pts['f_br']) / 2
        ax.annotate('selvedge edge', (sel_mid[0], sel_mid[1]),
                    textcoords="offset points", xytext=(0, -6),
                    fontsize=6, color='gray', ha='center')

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug,
                    pdf_pages=pdf_pages)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None):
    m = load_measurements(measurements_path)
    cinch = draft_jeans_back_cinch(m)
    plot_jeans_back_cinch(cinch, output_path, debug=debug, units=units,
                          pdf_pages=pdf_pages)
