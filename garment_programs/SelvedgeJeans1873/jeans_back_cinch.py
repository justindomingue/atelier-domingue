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

from garment_programs.core.runtime import cache_draft, resolve_measurements
from garment_programs.plot_utils import (
    SEAMLINE, CUTLINE, display_scale, setup_figure, finalize_figure,
)
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

    # Finished seamline shape (centered on y = 0)
    seam_tl = np.array([0.0, wide_half])
    seam_bl = np.array([0.0, -wide_half])
    seam_tr = np.array([length, narrow_half])
    seam_br = np.array([length, -narrow_half])

    # Seam allowances
    from .seam_allowances import SEAM_ALLOWANCES
    _sa = SEAM_ALLOWANCES['back_cinch']
    sa_wide = _sa['wide']
    sa_narrow = _sa['narrow']
    sa_end = _sa['end']

    # Cutline built directly from the drafting instructions:
    #   - 3/4" long-edge SA at wide end
    #   - 5/8" long-edge SA at narrow end
    #   - 1/2" SA at both short ends
    cut_tl = np.array([-sa_end, wide_half + sa_wide])
    cut_bl = np.array([-sa_end, -(wide_half + sa_wide)])
    cut_tr = np.array([length + sa_end, narrow_half + sa_narrow])
    cut_br = np.array([length + sa_end, -(narrow_half + sa_narrow)])

    return {
        'points': {
            'seam_tl': seam_tl, 'seam_bl': seam_bl,
            'seam_tr': seam_tr, 'seam_br': seam_br,
            'cut_tl': cut_tl, 'cut_bl': cut_bl,
            'cut_tr': cut_tr, 'cut_br': cut_br,
        },
        'curves': {},
        'construction': {},
        'metadata': {
            'title': 'Cinch Belt',
            'length': length,
            'cut_count': 1,
            'sa_wide': sa_wide,
            'sa_narrow': sa_narrow,
            'sa_end': sa_end,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_back_cinch(cinch, output_path='Logs/jeans_back_cinch.svg',
                          debug=False, units='cm', pdf_pages=None, ax=None):
    s, _unit_label = display_scale(units)

    pts = {k: v * s for k, v in cinch['points'].items()}

    # Rotate the whole piece so the bottom cut edge is horizontal (grainline
    # parallel to the selvedge).  Applied here so the draft stays clean.
    sel_dir = pts['cut_br'] - pts['cut_bl']
    angle = np.arctan2(sel_dir[1], sel_dir[0])
    ca, sn = np.cos(-angle), np.sin(-angle)
    R = np.array([[ca, -sn], [sn, ca]])
    pivot = pts['seam_bl'].copy()
    pts = {k: pivot + R @ (v - pivot) for k, v in pts.items()}

    fig, ax, standalone = setup_figure(ax, figsize=(12, 4))
    REF = dict(color='dimgray', linewidth=0.8, linestyle='--', alpha=0.7)

    # Seamline (finished size) and cutline (with SA) as closed outlines.
    seam_outline = np.array([
        pts['seam_tl'], pts['seam_tr'], pts['seam_br'], pts['seam_bl'], pts['seam_tl'],
    ])
    cut_outline = np.array([
        pts['cut_tl'], pts['cut_tr'], pts['cut_br'], pts['cut_bl'], pts['cut_tl'],
    ])
    ax.plot(seam_outline[:, 0], seam_outline[:, 1], **SEAMLINE)
    ax.plot(cut_outline[:, 0], cut_outline[:, 1], **CUTLINE)

    # Center guideline
    center_l = (pts['seam_tl'] + pts['seam_bl']) / 2
    center_r = (pts['seam_tr'] + pts['seam_br']) / 2
    ax.plot([center_l[0], center_r[0]], [center_l[1], center_r[1]], **REF)

    # 1/2" labels beside the end SA lines
    mid_left = (pts['cut_tl'] + pts['cut_bl']) / 2
    ax.text(mid_left[0] - 0.15 * s, mid_left[1], '1/2"',
            fontsize=12, ha='right', va='center')
    mid_right = (pts['cut_tr'] + pts['cut_br']) / 2
    ax.text(mid_right[0] + 0.15 * s, mid_right[1], '1/2"',
            fontsize=12, ha='left', va='center')

    # --- Grainline and piece label (pattern mode only) ---
    if not debug:
        from garment_programs.plot_utils import draw_grainline, draw_piece_label
        # Grainline along the selvedge direction (now horizontal)
        center = (center_l + center_r) / 2
        grain_half = np.linalg.norm(center_r - center_l) * 0.35
        grain_left = center - np.array([grain_half, 0])
        grain_right = center + np.array([grain_half, 0])
        draw_grainline(ax, grain_right, grain_left)

        # Piece label
        draw_piece_label(ax, (center[0], center[1]), cinch['metadata']['title'],
                         cinch['metadata'].get('cut_count'),
                         metadata=cinch.get('metadata'))

    if debug:
        for name, pt in pts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=4, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(4, 4), ha='left', fontsize=6)

        _annotate_segment(ax, pts['seam_bl'], pts['seam_br'], offset=(0, -10))
        _annotate_segment(ax, pts['seam_tl'], pts['seam_bl'], offset=(-14, 0))
        _annotate_segment(ax, pts['seam_tr'], pts['seam_br'], offset=(10, 0))

        sel_mid = (pts['cut_bl'] + pts['cut_br']) / 2
        ax.annotate('selvedge edge', (sel_mid[0], sel_mid[1]),
                    textcoords="offset points", xytext=(0, -6),
                    fontsize=6, color='gray', ha='center')

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug,
                    pdf_pages=pdf_pages)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None,
        context=None):
    m = resolve_measurements(context, measurements_path, load_measurements)
    cinch = cache_draft(context, 'selvedge.back_cinch', lambda: draft_jeans_back_cinch(m))
    plot_jeans_back_cinch(cinch, output_path, debug=debug, units=units,
                          pdf_pages=pdf_pages)
