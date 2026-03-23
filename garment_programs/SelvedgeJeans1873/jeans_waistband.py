"""
Jeans Waistband
Based on: Historical Tailoring Masterclasses - Drafting the Fly and Waistband

Simple rectangular strip, one long edge on the selvedge.
No fold — the piece is cut as a single layer.

Seamline width breakdown (bottom to top):
  1 1/2" — inside of waistband
  1 1/2" — outside of waistband
  3/8"   — inside-turn allowance (selvedge wraps to bottom inside)
  Total = 3 3/8"

Seam allowances (added by visualization):
  Top:    0     — selvedge edge (no SA needed)
  Bottom: 3/8"  — seam to jeans body
  Ends:   3/8"  — for finishing

Total cut width = 3 3/8" seamline + 3/8" bottom SA = 3 3/4"

Length = waist measurement + 3"–4" extra on each side (for turning under ends
and room for error).
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from garment_programs.core.runtime import cache_draft, resolve_measurements
from garment_programs.plot_utils import (
    SEAMLINE, CUTLINE, draw_seam_allowance, display_scale, setup_figure, finalize_figure,
)
from .jeans_front import (
    INCH, load_measurements, _annotate_segment,
)
from .seam_allowances import SEAM_ALLOWANCES, SEAM_LABELS


# -- Drafting ----------------------------------------------------------------

def draft_jeans_waistband(m):
    """Draft the waistband as a rectangular strip (seamline only, no SA).

    Parameters
    ----------
    m : dict
        Measurements in cm.

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    extra = 3 * INCH   # extra on each side (3" min per instructions)
    length = m['waist'] + 2 * extra
    # 1 1/2" inside + 1 1/2" outside + 3/8" inside-turn allowance so the
    # selvedge wraps past the body seam on the inside.  With the 3/8"
    # bottom SA this gives the source's 3 3/4" total cut width.
    width = 3.375 * INCH

    center_y = 1.5 * INCH   # inside / outside division

    # Corner points (seamline boundary)
    bl = np.array([0.0, 0.0])
    br = np.array([length, 0.0])
    tr = np.array([length, width])
    tl = np.array([0.0, width])

    return {
        'points': {
            'bl': bl, 'br': br, 'tr': tr, 'tl': tl,
        },
        'curves': {},
        'construction': {
            'center_y':    np.float64(center_y),
            'extra':       np.float64(extra),
        },
        'metadata': {
            'title': 'Waistband',
            'cut_count': 1,
            'length': length,
            'width': width,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_waistband(wb, output_path='Logs/jeans_waistband.svg',
                         debug=False, units='cm', pdf_pages=None, ax=None,
                         include_seam_allowance=True):
    s, unit_label = display_scale(units)

    pts = {k: v * s for k, v in wb['points'].items()}
    con = {k: v * s for k, v in wb['construction'].items()}
    length_s = wb['metadata']['length'] * s
    width_s  = wb['metadata']['width'] * s

    fig, ax, standalone = setup_figure(ax, figsize=(18, 4))
    SA = SEAM_ALLOWANCES['waistband']
    SL = SEAM_LABELS['waistband']
    REF = dict(color='dimgray', linewidth=0.8, linestyle='--', alpha=0.6)

    # --- Seamline (finished waistband outline) ---
    xs = [0, length_s, length_s, 0, 0]
    ys = [0, 0, width_s, width_s, 0]
    ax.plot(xs, ys, **SEAMLINE)

    # --- Seam allowance outline (CUTLINE) ---
    # CW edge order: top \u2192 right \u2192 bottom \u2192 left
    sa_edges = [
        (np.array([pts['tl'], pts['tr']]),  SA['top'], SL['top']),      # selvedge \u2014 SA=0
        (np.array([pts['tr'], pts['br']]),  SA['end'], SL['end']),      # right end
        (np.array([pts['br'], pts['bl']]),  SA['bottom'], SL['bottom']),   # bottom seam
        (np.array([pts['bl'], pts['tl']]),  SA['end'], SL['end']),      # left end
    ]
    if include_seam_allowance:
        cut_outline = draw_seam_allowance(ax, sa_edges, scale=s,
                                          label_sas=not debug, units=units)
    else:
        # Interfacing net shape: cut boundary equals the seamline rectangle.
        ax.plot(xs, ys, **CUTLINE)
        cut_outline = np.column_stack([xs, ys])

    # --- Reference lines ---

    # Fold line (center of waistband) \u2014 dash-dot per pattern convention
    FOLD = dict(color='black', linewidth=1.0, linestyle='-.', alpha=0.7)
    ax.plot([0, length_s], [con['center_y'], con['center_y']], **FOLD)
    ax.annotate('\u2014 FOLD \u2014',
                (length_s / 2, con['center_y']),
                textcoords="offset points", xytext=(0, 5),
                fontsize=8, ha='center', va='bottom', color='black',
                fontweight='bold')
    ax.annotate('inside  1\u00bd"',
                (length_s / 2, con['center_y'] / 2),
                fontsize=7, ha='center', va='center', color='dimgray')
    ax.annotate('outside  1\u00bd"',
                (length_s / 2, (con['center_y'] + width_s) / 2),
                fontsize=7, ha='center', va='center', color='dimgray')

    # Selvedge label on top edge
    ax.annotate('SELVEDGE', (length_s / 2, width_s),
                textcoords="offset points", xytext=(0, 5),
                fontsize=7, ha='center', va='bottom', color='dimgray')

    # --- End extent marks \u2014 show where the waist measurement runs ---
    extra_s = con['extra']
    for x in [extra_s, length_s - extra_s]:
        ax.plot([x, x], [0, width_s],
                color='steelblue', linewidth=0.9, linestyle='--', alpha=0.7)
    ax.annotate('\u2190 waist \u2192',
                (length_s / 2, width_s + 0.15 * s),
                fontsize=7, ha='center', va='bottom', color='steelblue')

    # --- Grainline and piece label (pattern mode only) ---
    if not debug:
        from garment_programs.plot_utils import draw_grainline, draw_piece_label
        # Horizontal grainline along the length (selvedge direction)
        grain_left = np.array([length_s * 0.15, width_s / 2])
        grain_right = np.array([length_s * 0.85, width_s / 2])
        draw_grainline(ax, grain_right, grain_left)

        # Piece label
        center = (length_s / 2, width_s / 2)
        draw_piece_label(ax, center, wb['metadata']['title'],
                         wb['metadata'].get('cut_count'),
                         metadata=wb.get('metadata'))

    if debug:
        _annotate_segment(ax, pts['bl'], pts['br'], offset=(0, -10))
        _annotate_segment(ax, pts['tl'], pts['bl'], offset=(-14, 0))

    return finalize_figure(ax, fig, standalone, output_path, units=units,
                           debug=debug, pdf_pages=pdf_pages,
                           outline_pts=cut_outline)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None,
        context=None, include_seam_allowance=True):
    m = resolve_measurements(context, measurements_path, load_measurements)
    wb = cache_draft(context, 'selvedge.waistband', lambda: draft_jeans_waistband(m))
    outline = plot_jeans_waistband(wb, output_path, debug=debug, units=units,
                                   pdf_pages=pdf_pages,
                                   include_seam_allowance=include_seam_allowance)
    if outline:
        return {'layout_outline': outline}
