"""
Historical Jeans Front Panel (1873 style)
Based on: Historical Tailoring Masterclasses - Drafting the Front

Refactored from the step-by-step exploration into a reusable module.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from garment_programs.geometry import (
    INCH, _bezier_cubic, _bezier_quad,
    _curve_length, _point_at_arclength, _curve_up_to_arclength,
    _curve_from_arclength,
    _annotate_curve, _annotate_segment,
)
from garment_programs.measurements import load_measurements
from garment_programs.plot_utils import (
    SEAMLINE, CUTLINE, offset_polyline, draw_seam_allowance,
    display_scale, setup_figure, finalize_figure,
)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_front(m):
    """
    Compute all points, curves, and construction geometry for the jeans front.

    Parameters
    ----------
    m : dict
        Measurements in cm (output of load_measurements).

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    # Step 1: Marking out the lengths
    # MHTML: "0-1: Side Length to measure minus 1½" or the width of your waistband."
    pt0 = np.array([0.0, 0.0])
    waistband = m.get('waistband_width', 1.5 * INCH)
    pt1 = np.array([-(m['side_length'] - waistband), 0.0])
    pt2 = np.array([-m['inseam'], 0.0])
    pt3 = np.array([pt2[0] / 2 - 2 * INCH, 0.0])
    pt4 = np.array([pt2[0] - (m['seat'] / 2) / 6, 0.0])

    # Step 2: Marking out the widths
    hem_drop = m['hem_width'] / 2 - 3/8 * INCH
    pt0_drop = np.array([pt0[0], -hem_drop])

    knee_drop = m['knee_width'] / 2 - 3/8 * INCH
    pt3_drop = np.array([pt3[0], -knee_drop])

    seat_quarter = m['seat'] / 4
    pt5 = np.array([pt2[0], -seat_quarter])

    crotch_ext = (m['seat'] / 2) / 6 - 1 * INCH
    pt6 = np.array([pt5[0], pt5[1] - crotch_ext])

    pt7 = np.array([pt1[0], -seat_quarter])
    pt8 = np.array([pt4[0], -seat_quarter])

    # Step 3: Point adjustments
    pt1_adj = pt1.copy()
    pt1_adj[1] -= 3/8 * INCH

    dir_7to8 = pt8 - pt7
    dir_7to8_norm = dir_7to8 / np.linalg.norm(dir_7to8)
    pt7_shifted = pt7 + dir_7to8_norm * (3/8 * INCH)
    pt7_adj = pt7_shifted.copy()
    pt7_adj[1] += 5/8 * INCH

    dist_5to6 = np.linalg.norm(pt6 - pt5)
    half_dist = dist_5to6 / 2
    pt9 = pt5 + half_dist * np.array([-np.cos(np.pi/4), -np.sin(np.pi/4)])

    # Step 4: Construction lines
    fly_dir = pt8 - pt7_adj
    fly_dir_norm = fly_dir / np.linalg.norm(fly_dir)
    fly_start = pt7_adj
    fly_end = pt8 + fly_dir_norm * 5

    # Step 5: Curves
    # 1. Side hip curve (1' -> 4)
    hip_curve_end = pt4.copy()
    dist_14 = np.linalg.norm(hip_curve_end - pt1_adj)
    rise_1 = hip_curve_end[1] - pt1_adj[1]
    curve_hip = _bezier_cubic(
        pt1_adj,
        pt1_adj + np.array([dist_14 / 3, rise_1]),
        hip_curve_end - np.array([dist_14 / 3, 0]),
        hip_curve_end
    )

    # 2. Front rise / waist curve (1' -> 7')
    # Both endpoints tangent in the −y direction (toward the side seam).
    # This guarantees a C-curve with no inflection: the x-component of the
    # Bézier is the product of two non-negative Bernstein terms → monotone.
    # The curve bows slightly toward the hem (+x) at the midpoint — the
    # natural "waist dip" shape — and arrives at pt7_adj flowing toward the
    # side seam, as required.
    y_arm = abs(pt7_adj[1] - pt1_adj[1]) / 3   # ≈ 1/3 of the y-span
    curve_rise = _bezier_cubic(
        pt1_adj,
        pt1_adj + np.array([0.0, -y_arm]),   # tangent: straight toward side seam
        pt7_adj + np.array([0.0,  y_arm]),   # tangent: arriving from the side seam
        pt7_adj
    )

    # 3. Crotch curve (8 -> 9 -> 6)
    crotch_ctrl = 2 * pt9 - 0.5 * (pt8 + pt6)
    curve_crotch = _bezier_quad(pt8, crotch_ctrl, pt6)

    # 4. Inseam curve (6 -> 3')
    dir_6_to_3 = pt3_drop - pt6
    dir_6_to_3_norm = dir_6_to_3 / np.linalg.norm(dir_6_to_3)
    angle = np.radians(20)
    inseam_tan_at_6 = np.array([
        dir_6_to_3_norm[0] * np.cos(angle) - dir_6_to_3_norm[1] * np.sin(angle),
        dir_6_to_3_norm[0] * np.sin(angle) + dir_6_to_3_norm[1] * np.cos(angle)
    ])
    inseam_straight_dir = pt0_drop - pt3_drop
    inseam_straight_dir_norm = inseam_straight_dir / np.linalg.norm(inseam_straight_dir)
    dist_63 = np.linalg.norm(pt3_drop - pt6)
    curve_inseam = _bezier_cubic(
        pt6,
        pt6 + inseam_tan_at_6 * (dist_63 / 4),
        pt3_drop - inseam_straight_dir_norm * (dist_63 / 4),
        pt3_drop
    )

    # Step 6: Center front line
    dist_2to5 = np.linalg.norm(pt5 - pt2)
    half_2to5 = dist_2to5 / 2
    dir_2to5 = (pt5 - pt2) / dist_2to5
    pt_temp = pt2 + dir_2to5 * half_2to5
    pt10 = pt_temp - dir_2to5 * (3/4 * INCH)

    return {
        'points': {
            '0': pt0, '1': pt1, '2': pt2, '3': pt3, '4': pt4,
            "0'": pt0_drop, "3'": pt3_drop,
            '5': pt5, '6': pt6, '7': pt7, '8': pt8,
            "1'": pt1_adj, "7'": pt7_adj, '9': pt9,
            '10': pt10, 'temp': pt_temp,
        },
        'curves': {
            'hip': curve_hip,
            'rise': curve_rise,
            'crotch': curve_crotch,
            'inseam': curve_inseam,
        },
        'construction': {
            'fly_start': fly_start,
            'fly_end': fly_end,
        },
        'metadata': {
            'title': 'Historical Jeans Front Panel (1873)',
            'cut_count': 2,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_front(draft, output_path='Logs/jeans_front.svg', debug=False, units='cm',
                     pocket=None, pdf_pages=None, ax=None):
    """Render the draft to a matplotlib figure and save as PNG.

    Always draws the pattern outline and internal reference lines (hip, knee, CF).
    With debug=True, adds construction lines, point labels, legend, and grid.

    units : 'cm' or 'inch' — display unit for axes and annotations.
    """
    s, unit_label = display_scale(units)
    pts = {k: v * s for k, v in draft['points'].items()}
    curves = {k: v * s for k, v in draft['curves'].items()}
    con = {k: v * s for k, v in draft['construction'].items()}
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)

    fig, ax, standalone = setup_figure(ax, figsize=(16, 10))

    # --- Debug-only: construction scaffolding ---
    if debug:
        # Baseline
        baseline_xs = sorted(p[0] for p in [pts['0'], pts['1'], pts['2'], pts['3'], pts['4']])
        ax.plot([baseline_xs[0] - 5, baseline_xs[-1] + 5], [0, 0],
                'k-', linewidth=0.5, alpha=0.2)

        # Drop lines
        for base_k, drop_k in [('0', "0'"), ('3', "3'"), ('2', '5'), ('4', '8'), ('1', '7')]:
            ax.plot([pts[base_k][0], pts[drop_k][0]],
                    [pts[base_k][1], pts[drop_k][1]],
                    'k--', linewidth=0.5, alpha=0.1)
        ax.plot([pts['5'][0], pts['6'][0]], [pts['5'][1], pts['6'][1]],
                'k--', linewidth=0.5, alpha=0.1)

        # Fly line
        ax.plot([con['fly_start'][0], con['fly_end'][0]],
                [con['fly_start'][1], con['fly_end'][1]],
                'k--', linewidth=0.5, alpha=0.15)
        # Inseam straight
        ax.plot([pts['6'][0], pts["3'"][0], pts["0'"][0]],
                [pts['6'][1], pts["3'"][1], pts["0'"][1]],
                'k--', linewidth=0.5, alpha=0.15)

        # CF construction (2→5 dashed)
        ax.plot([pts['2'][0], pts['5'][0]], [pts['2'][1], pts['5'][1]],
                'c--', linewidth=0.5, alpha=0.2)

    # --- Pattern outline: curves ---
    c = curves
    if debug:
        ax.plot(c['hip'][:, 0], c['hip'][:, 1],
                'b-', linewidth=2, label="Side hip (1'->4)", zorder=4)
        ax.plot(c['rise'][:, 0], c['rise'][:, 1],
                'r-', linewidth=2, label="Front rise (1'->7')", zorder=4)
        ax.plot(c['crotch'][:, 0], c['crotch'][:, 1],
                'g-', linewidth=2, label='Crotch (8->9->6)', zorder=4)
        ax.plot(c['inseam'][:, 0], c['inseam'][:, 1],
                'm-', linewidth=2, label="Inseam (6->3')", zorder=4)
    else:
        for curve in c.values():
            ax.plot(curve[:, 0], curve[:, 1], 'k-', linewidth=1.5)

    # --- Pattern outline: straight segments ---
    for a, b in [('4', '0'), ("7'", '8'), ("3'", "0'"), ("0'", '0')]:
        ax.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]],
                'k-', linewidth=1.5)

    # --- Internal reference lines (always shown) ---
    # Each vertical line is clipped to the piece outline width at that x,
    # not the global bounding box (which would overshoot at the crotch fork).
    outline_keys = ['0', "0'", "3'", '4', "1'", "7'", '8', '6']
    x_lo = min(pts[k][0] for k in outline_keys)
    x_hi = max(pts[k][0] for k in outline_keys)

    # Seat line — vertical at pt4 x-level, clipped to outseam (pt4) → inseam (pt8)
    seat_x = pts['4'][0]
    ax.plot([seat_x, seat_x], [pts['4'][1], pts['8'][1]], **REF)
    ax.annotate('seat', (seat_x, pts['4'][1]), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    # Hip line — vertical at pt2 x-level, clipped to baseline (pt2) → inseam (pt5)
    hip_x = pts['2'][0]
    ax.plot([hip_x, hip_x], [pts['2'][1], pts['5'][1]], **REF)
    ax.annotate('hip', (hip_x, pts['2'][1]), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    # Knee line — vertical at knee x-level, clipped to baseline (pt3) → inseam (pt3')
    knee_x = pts['3'][0]
    ax.plot([knee_x, knee_x], [pts['3'][1], pts["3'"][1]], **REF)
    ax.annotate('knee', (knee_x, pts['3'][1]), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    # Center front line — horizontal at CF y-offset
    cf_mid = (x_lo + x_hi) / 2
    ax.plot([x_lo, x_hi], [pts['10'][1], pts['10'][1]], **REF)
    ax.annotate('center front', (cf_mid, pts['10'][1]), textcoords="offset points",
                xytext=(0, 4), fontsize=7, color='gray', ha='center')

    # --- Debug-only: point labels, legend, grid ---
    if debug:
        for name, pt in pts.items():
            if name == 'temp':
                continue
            ax.plot(pt[0], pt[1], 'o', color='gray', markersize=4, zorder=5, alpha=0.5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=8, alpha=0.6)
        ax.legend(loc='lower right', fontsize=9)
        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)

        # Measurement annotations
        _annotate_curve(ax, curves['hip'], offset=(0, -10))
        _annotate_curve(ax, curves['rise'], offset=(-10, 0))
        _annotate_curve(ax, curves['crotch'], offset=(0, -10))
        _annotate_curve(ax, curves['inseam'], offset=(10, 0))
        _annotate_segment(ax, pts['4'], pts['0'], offset=(0, 8))
        _annotate_segment(ax, pts["7'"], pts['8'])
        _annotate_segment(ax, pts["3'"], pts["0'"], offset=(10, 0))
        _annotate_segment(ax, pts["0'"], pts['0'], offset=(8, 0))

    # --- Pocket internal lines (if provided) ---
    if pocket is not None:
        ppts = {k: v * s for k, v in pocket['points'].items()}
        pcurves = {k: v * s for k, v in pocket['curves'].items()}

        POCKET_OPEN = dict(color='black', linewidth=1.5, zorder=3)
        POCKET_BAG = dict(color='green', linewidth=1, linestyle='--', alpha=0.6, zorder=3)
        WATCH = dict(color='steelblue', linewidth=1.2, zorder=3)

        # Pocket opening (solid)
        ax.plot(pcurves['opening'][:, 0], pcurves['opening'][:, 1], **POCKET_OPEN)

        # Pocket bag (dashed)
        ax.plot([ppts['bag_inner_top'][0], ppts['bag_inner_bottom'][0]],
                [ppts['bag_inner_top'][1], ppts['bag_inner_bottom'][1]], **POCKET_BAG)
        ax.plot(pcurves['bag_bottom'][:, 0], pcurves['bag_bottom'][:, 1], **POCKET_BAG)
        ax.plot([ppts['bag_sideseam'][0], ppts['pocket_lower'][0]],
                [ppts['bag_sideseam'][1], ppts['pocket_lower'][1]], **POCKET_BAG)
        ax.plot([ppts['pocket_upper'][0], ppts['bag_inner_top'][0]],
                [ppts['pocket_upper'][1], ppts['bag_inner_top'][1]], **POCKET_BAG)

        # Facing: not drawn on the front overlay — the facing is traced from
        # the opening and gets extra SA at the bottom when cut as a separate
        # piece (data stored in pocket dict for later extraction).

        # Watch pocket (steelblue)
        watch = pocket['watch_pocket']
        wp = watch['outline'] * s
        # Close the pentagon by appending the first point
        wp_closed = np.vstack([wp, wp[0:1]])
        ax.plot(wp_closed[:, 0], wp_closed[:, 1], **WATCH)

        if debug:
            for name, pt in ppts.items():
                ax.plot(pt[0], pt[1], 'o', color='darkorange', markersize=4, zorder=5)
                ax.annotate(name, pt, textcoords="offset points",
                            xytext=(6, 4), ha='left', fontsize=6, color='darkorange')
            wpts = {k: v * s for k, v in watch['points'].items()}
            for name, pt in wpts.items():
                ax.plot(pt[0], pt[1], 'o', color='steelblue', markersize=3, zorder=5)
                ax.annotate(name, pt, textcoords="offset points",
                            xytext=(6, -8), ha='left', fontsize=5, color='steelblue')

    # --- Seam allowances (always drawn) ---
    from .seam_allowances import SEAM_ALLOWANCES
    SA = SEAM_ALLOWANCES['front']
    SA_SIDE   = SA['side']
    SA_HEM    = SA['hem']
    SA_INSEAM = SA['inseam']
    SA_CROTCH = SA['crotch']
    SA_FLY    = SA['fly']
    SA_WAIST  = SA['waist']

    # SA transition: 3/4" kicks in 1/2" before pt8 on the crotch curve
    _crotch_rev = curves['crotch'][::-1]          # scaled, pt6 → pt8
    _crotch_len = _curve_length(_crotch_rev)
    _split      = 0.5 * INCH * s
    _crotch_body = _curve_up_to_arclength(_crotch_rev, _crotch_len - _split)
    _crotch_end  = _curve_up_to_arclength(_crotch_rev[::-1], _split)[::-1]

    # Build edges: (polyline, sa_distance_cm)
    # Outline travels CW: hip(1'→4) → hem(4→0) → hem_drop(0→0') → inseam(0'→3')
    #   → inseam_curve(3'→6) → crotch(6→8) → fly(8→7') → rise(7'→1')
    sa_edges = [
        (curves['hip'],                                          SA_SIDE),    # side seam (waist→seat)
        (np.array([pts['4'], pts['0']]),                         SA_SIDE),    # side seam (seat→hem)
        (np.array([pts['0'], pts["0'"]]),                        SA_HEM),     # hem
        (np.array([pts["0'"], pts["3'"]]),                       SA_INSEAM),  # lower inseam straight
        (curves['inseam'][::-1],                                 SA_INSEAM),  # inseam curve (3'→6)
        (_crotch_body,                                           SA_CROTCH),  # crotch (6 → transition)
        (_crotch_end,                                            SA_FLY),     # last 1/2" of crotch: 3/4"
        (np.array([pts['8'], pts["7'"]]),                        SA_FLY),     # fly: full 3/4"
        (curves['rise'][::-1],                                   SA_WAIST),   # rise / waist (7'→1')
    ]
    draw_seam_allowance(ax, sa_edges, scale=s)

    # --- Pocket notches (always drawn when pocket data is available) ---
    if pocket is not None:
        from garment_programs.plot_utils import draw_notch
        ppts = {k: v * s for k, v in pocket['points'].items()}
        pcurves = {k: v * s for k, v in pocket['curves'].items()}

        # Notch 1: pocket_upper on the rise curve (waist edge)
        #   rise curve travels 1'→7', pocket_upper is at 4.75" along it
        draw_notch(ax, curves['rise'], ppts['pocket_upper'],
                   SA_WAIST, scale=s)

        # Notch 2: pocket_lower on the hip curve (side seam)
        #   hip curve travels 1'→4, pocket_lower is at 3.25" along it
        draw_notch(ax, curves['hip'], ppts['pocket_lower'],
                   SA_SIDE, scale=s)

        # Notch 3: bag_inner_top on the rise curve (waist edge)
        #   5.75" from 1' along rise — where pocket bag inner edge meets waist
        draw_notch(ax, curves['rise'], ppts['bag_inner_top'],
                   SA_WAIST, scale=s, count=2)

        # Notch 4: bag_sideseam on the hip curve (side seam)
        #   5.25" from 1' along hip — where pocket bag meets side seam
        draw_notch(ax, curves['hip'], ppts['bag_sideseam'],
                   SA_SIDE, scale=s, count=2)

    # --- Grainline and piece label (pattern mode only) ---
    if not debug:
        from garment_programs.plot_utils import draw_grainline, draw_piece_label
        # Grainline along center-front x, spanning waist to near hem
        cf_x = pts['10'][1]  # center-front y-offset used as grainline x
        grain_top = np.array([pts['1'][0] * 0.85 + pts['0'][0] * 0.15, cf_x])
        grain_bottom = np.array([pts['1'][0] * 0.15 + pts['0'][0] * 0.85, cf_x])
        draw_grainline(ax, grain_top, grain_bottom)

        # Piece label at bounding-box center
        all_x = [pts[k][0] for k in ('0', "1'", "7'", '6')]
        all_y = [pts[k][1] for k in ('0', "1'", "7'", '6')]
        center = ((min(all_x) + max(all_x)) / 2, (min(all_y) + max(all_y)) / 2)
        draw_piece_label(ax, center, draft['metadata']['title'],
                         draft['metadata'].get('cut_count'))

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug,
                    pdf_pages=pdf_pages)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None):
    """Uniform interface called by the generic runner."""
    m = load_measurements(measurements_path)
    draft = draft_jeans_front(m)
    from .jeans_front_pocket import draft_jeans_front_pocket
    pocket = draft_jeans_front_pocket(m, draft)
    plot_jeans_front(draft, output_path, debug=debug, units=units, pocket=pocket,
                     pdf_pages=pdf_pages)
