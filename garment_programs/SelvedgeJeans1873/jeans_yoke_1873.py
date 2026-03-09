"""
Historical Jeans Yoke (1873 style)
Based on: Historical Tailoring Masterclasses - Drafting the Yoke

Drafted after the back panel is complete.  Separates the upper back panel
(waist to yoke line) from the lower back.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from garment_programs.core.runtime import cache_draft, resolve_measurements
from garment_programs.plot_utils import (
    SEAMLINE, draw_notch, draw_seam_allowance, display_scale, setup_figure,
    finalize_figure,
)
from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _annotate_segment,
    _point_at_arclength, _curve_up_to_arclength,
)
from .jeans_back import draft_jeans_back
from .seam_allowances import YOKE_SEAT_DEPTH


# -- Drafting ----------------------------------------------------------------

def draft_jeans_yoke(m, front, back):
    """
    Compute yoke geometry from the completed front and back drafts.

    Parameters
    ----------
    m : dict
        Measurements in cm.
    front : dict
        Result of ``draft_jeans_front(m)``.
    back : dict
        Result of ``draft_jeans_back(m, front)``.

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    fpts = front['points']
    bpts = back['points']

    # -- 1. Yoke point on outseam (side seam) --
    # 1.5" from pt 1 toward pt 4 along the back outseam (straight line)
    dir_1_to_4 = fpts['4'] - fpts['1']
    dir_1_to_4_norm = dir_1_to_4 / np.linalg.norm(dir_1_to_4)
    yoke_side = fpts['1'] + dir_1_to_4_norm * (1.5 * INCH)

    # -- 2. Yoke point on seat seam --
    # Walk the seat_upper curve (back_waist → 8') from the start
    yoke_seat_dist = YOKE_SEAT_DEPTH
    yoke_seat = _point_at_arclength(back['curves']['seat_upper'], yoke_seat_dist)

    # -- 3. Dart position — 1/3 of waist from pt 1 toward back_waist --
    pt1 = fpts['1']
    back_waist = bpts['back_waist']
    waist_vec = back_waist - pt1
    waist_thirds_1 = pt1 + waist_vec / 3          # closest to pt 1
    waist_thirds_2 = pt1 + 2 * waist_vec / 3
    dart_center_waist = waist_thirds_1

    # -- 4. Dart guideline — perpendicular to waist, intersect yoke line --
    waist_dir_norm = waist_vec / np.linalg.norm(waist_vec)
    perp = np.array([-waist_dir_norm[1], waist_dir_norm[0]])
    # Ensure perpendicular points toward the yoke line (away from waist)
    yoke_mid = (yoke_side + yoke_seat) / 2
    if np.dot(perp, yoke_mid - dart_center_waist) < 0:
        perp = -perp

    # Line–line intersection:  dart_center_waist + t·perp = yoke_side + s·yoke_dir
    yoke_dir = yoke_seat - yoke_side
    A = np.column_stack([perp, -yoke_dir])
    b_vec = yoke_side - dart_center_waist
    params = np.linalg.solve(A, b_vec)
    dart_center_yoke = dart_center_waist + params[0] * perp

    # -- 5. Dart edges — 3/8" on each side along waist direction --
    hw = 3 / 8 * INCH
    dart_left_waist  = dart_center_waist - waist_dir_norm * hw
    dart_right_waist = dart_center_waist + waist_dir_norm * hw
    dart_left_yoke   = dart_center_yoke  - waist_dir_norm * hw
    dart_right_yoke  = dart_center_yoke  + waist_dir_norm * hw

    return {
        'points': {
            'yoke_side':          yoke_side,
            'yoke_seat':          yoke_seat,
            'dart_center_waist':  dart_center_waist,
            'dart_center_yoke':   dart_center_yoke,
            'dart_left_waist':    dart_left_waist,
            'dart_right_waist':   dart_right_waist,
            'dart_left_yoke':     dart_left_yoke,
            'dart_right_yoke':    dart_right_yoke,
        },
        'curves': {},          # all straight lines — no Bézier curves
        'construction': {
            'waist_thirds_1': waist_thirds_1,
            'waist_thirds_2': waist_thirds_2,
        },
        'metadata': {
            'title': 'Yoke',
            'cut_count': 2,
            'yoke_seat_dist': yoke_seat_dist,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_yoke(front, back, yoke, output_path='Logs/jeans_yoke.svg',
                    debug=False, units='cm', pdf_pages=None, ax=None):
    """Render the yoke overlaid on the back panel and save as PNG.

    Always draws the yoke outline and dart.
    With debug=True, adds point labels, measurements, and grid.

    units : 'cm' or 'inch' — display unit for axes and annotations.
    """
    s, unit_label = display_scale(units)

    fpts   = {k: v * s for k, v in front['points'].items()}
    bpts   = {k: v * s for k, v in back['points'].items()}
    bcurves = {k: v * s for k, v in back['curves'].items()}
    ypts   = {k: v * s for k, v in yoke['points'].items()}
    ycon   = {k: v * s for k, v in yoke['construction'].items()}

    # Seat-seam curve segment for yoke right side
    yoke_seat_dist = yoke['metadata']['yoke_seat_dist']
    seat_seg = _curve_up_to_arclength(back['curves']['seat_upper'], yoke_seat_dist) * s

    fig, ax, standalone = setup_figure(ax, figsize=(16, 10))
    OUTLINE  = SEAMLINE
    CONTEXT  = dict(color='lightgray', linewidth=1, alpha=0.5)
    DART_STY = dict(color='black', linewidth=1.2, linestyle='--')

    # -- Back panel outline as context (light gray, debug only) --
    if debug:
        ax.plot([fpts['1'][0], bpts['back_waist'][0]],
                [fpts['1'][1], bpts['back_waist'][1]], **CONTEXT)
        ax.plot(bcurves['seat_upper'][:, 0], bcurves['seat_upper'][:, 1], **CONTEXT)
        ax.plot(bcurves['seat_lower'][:, 0], bcurves['seat_lower'][:, 1], **CONTEXT)
        ax.plot(bcurves['back_inseam'][:, 0], bcurves['back_inseam'][:, 1], **CONTEXT)
        ax.plot([bpts['12'][0], bpts['back_hem'][0]],
                [bpts['12'][1], bpts['back_hem'][1]], **CONTEXT)
        ax.plot([bpts['back_hem'][0], fpts['0'][0]],
                [bpts['back_hem'][1], fpts['0'][1]], **CONTEXT)
        ax.plot([fpts['0'][0], fpts['4'][0]],
                [fpts['0'][1], fpts['4'][1]], **CONTEXT)
        ax.plot([fpts['4'][0], fpts['1'][0]],
                [fpts['4'][1], fpts['1'][1]], **CONTEXT)

    # -- Yoke outline (black) --
    # Top: waist line (pt 1 → back_waist)
    ax.plot([fpts['1'][0], bpts['back_waist'][0]],
            [fpts['1'][1], bpts['back_waist'][1]], **OUTLINE)
    # Right side: seat_upper curve segment (back_waist → yoke_seat)
    ax.plot(seat_seg[:, 0], seat_seg[:, 1], **OUTLINE)
    # Bottom: yoke line (yoke_seat → yoke_side)
    ax.plot([ypts['yoke_seat'][0], ypts['yoke_side'][0]],
            [ypts['yoke_seat'][1], ypts['yoke_side'][1]], **OUTLINE)
    # Left side: outseam (yoke_side → pt 1) — straight line
    ax.plot([ypts['yoke_side'][0], fpts['1'][0]],
            [ypts['yoke_side'][1], fpts['1'][1]], **OUTLINE)

    # -- Dart --
    ax.plot([ypts['dart_left_waist'][0],  ypts['dart_left_yoke'][0]],
            [ypts['dart_left_waist'][1],  ypts['dart_left_yoke'][1]],  **DART_STY)
    ax.plot([ypts['dart_right_waist'][0], ypts['dart_right_yoke'][0]],
            [ypts['dart_right_waist'][1], ypts['dart_right_yoke'][1]], **DART_STY)

    # -- Debug overlays --
    if debug:
        # Yoke point labels
        for name, pt in ypts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=5, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=7)

        # Construction: waist division points
        for label in ('waist_thirds_1', 'waist_thirds_2'):
            pt = ycon[label]
            ax.plot(pt[0], pt[1], 'x', color='blue', markersize=6, zorder=5)
            ax.annotate(label, pt, textcoords="offset points",
                        xytext=(6, -8), ha='left', fontsize=6, color='blue')

        # Dart center guideline
        ax.plot([ypts['dart_center_waist'][0], ypts['dart_center_yoke'][0]],
                [ypts['dart_center_waist'][1], ypts['dart_center_yoke'][1]],
                color='blue', linewidth=0.6, linestyle=':', alpha=0.5)

        # Measurements
        _annotate_segment(ax, fpts['1'], bpts['back_waist'], offset=(0, 8))
        _annotate_segment(ax, ypts['yoke_seat'], ypts['yoke_side'], offset=(0, -10))
        _annotate_segment(ax, ypts['dart_left_waist'], ypts['dart_right_waist'],
                          offset=(0, 8))

        # Back/front panel point labels (faint context)
        all_context = {**fpts, **bpts}
        for name, pt in all_context.items():
            if name == 'temp':
                continue
            ax.plot(pt[0], pt[1], 'o', color='gray', markersize=3,
                    zorder=4, alpha=0.3)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6,
                        color='gray', alpha=0.4)

    # --- Seam allowances (always drawn) ---
    from .seam_allowances import SEAM_ALLOWANCES, SEAM_LABELS
    _sa = SEAM_ALLOWANCES['yoke']
    _sl = SEAM_LABELS['yoke']
    SA_SEAT_YOKE  = _sa['seat']
    SA_SIDE_YOKE  = _sa['side']
    SA_WAIST_YOKE = _sa['waist']

    # CW outline: outseam(1→yoke_side) → yoke_line(yoke_side→yoke_seat)
    #   → seat_seg reversed(yoke_seat→back_waist) → waist(back_waist→1)
    sa_edges = [
        (np.array([fpts['1'], ypts['yoke_side']]),               SA_SIDE_YOKE, _sl['side']),   # side seam
        (np.array([ypts['yoke_side'], ypts['yoke_seat']]),       SA_WAIST_YOKE, _sl['waist']),  # yoke seam (bottom)
        (seat_seg[::-1],                                         SA_SEAT_YOKE, _sl['seat']),   # seat seam segment (reversed)
        (np.array([bpts['back_waist'], fpts['1']]),              SA_WAIST_YOKE, _sl['waist']),  # waist
    ]
    draw_seam_allowance(ax, sa_edges, scale=s, label_sas=not debug, units=units)

    # -- Notch on yoke seam (midpoint, 1/2" from seamline) --
    yoke_seam = np.array([ypts['yoke_side'], ypts['yoke_seat']])
    notch_mid = (ypts['yoke_side'] + ypts['yoke_seat']) / 2
    draw_notch(ax, yoke_seam, notch_mid, SA_WAIST_YOKE, scale=s, count=2)

    # --- Grainline and piece label (pattern mode only) ---
    if not debug:
        from garment_programs.plot_utils import draw_grainline, draw_piece_label
        # Grainline parallel to center back (along x-axis, perpendicular to waist)
        grain_center = (fpts['1'] + bpts['back_waist'] + ypts['yoke_side'] + ypts['yoke_seat']) / 4
        yoke_height = abs(fpts['1'][0] - ypts['yoke_side'][0])
        grain_half = yoke_height * 0.3
        grain_top = np.array([grain_center[0] + grain_half, grain_center[1]])
        grain_bot = np.array([grain_center[0] - grain_half, grain_center[1]])
        draw_grainline(ax, grain_top, grain_bot)

        # Piece label
        draw_piece_label(ax, (grain_center[0], grain_center[1]),
                         yoke['metadata']['title'],
                         yoke['metadata'].get('cut_count'),
                         metadata=yoke.get('metadata'))

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug,
                    pdf_pages=pdf_pages)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None,
        context=None):
    """Uniform interface called by the generic runner."""
    m = resolve_measurements(context, measurements_path, load_measurements)
    front = cache_draft(context, 'selvedge.front', lambda: draft_jeans_front(m))
    back = cache_draft(context, 'selvedge.back:0.0000', lambda: draft_jeans_back(m, front))
    yoke = cache_draft(context, 'selvedge.yoke_1873:0.0000', lambda: draft_jeans_yoke(m, front, back))
    plot_jeans_yoke(front, back, yoke, output_path, debug=debug, units=units,
                    pdf_pages=pdf_pages)
