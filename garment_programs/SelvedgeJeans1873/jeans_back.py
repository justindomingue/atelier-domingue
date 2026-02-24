"""
Historical Jeans Back Panel (1873 style)
Based on: Historical Tailoring Masterclasses - Drafting the Back

Drafted relative to the front panel.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from garment_programs.plot_utils import SEAMLINE, draw_seam_allowance
from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _bezier_cubic, _bezier_quad,
    _annotate_curve, _annotate_segment,
    _point_at_arclength, _curve_up_to_arclength,
    _curve_length,
)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_back(m, front):
    """
    Compute back panel geometry, built on top of the front draft.

    Parameters
    ----------
    m : dict
        Measurements in cm.
    front : dict
        Result of draft_jeans_front(m).

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    fpts = front['points']

    # -- Step 1: Back Leg Widths --
    ext = 3/4 * INCH  # 3/4" extension for back

    # Extend hem and knee lines by 3/4"
    back_hem = fpts["0'"] + np.array([0, -ext])
    pt12 = fpts["3'"] + np.array([0, -ext])  # back knee point ("12")

    # Step 2: 6–11 = seat/16 (initial position)
    pt11_initial = fpts['6'] + np.array([0, -(m['seat'] / 16)])

    # Step 3-5: Construction line from 11 through 12; adjust 11 along it
    # so that dist(12,11) = dist(6,3') - 1/4" (denim adjustment)
    # Use front's 6→3' measurement as instructed ("measure on the front pattern piece")
    dir_from_12_to_11 = pt11_initial - pt12
    dir_from_12_to_11_norm = dir_from_12_to_11 / np.linalg.norm(dir_from_12_to_11)
    target_dist = np.linalg.norm(fpts['6'] - fpts["3'"]) - 1/4 * INCH
    pt11 = pt12 + dir_from_12_to_11_norm * target_dist

    # Construction line from 11 through 12 to hem level (x = 0)
    dir_11_12 = pt12 - pt11
    t_hem = (0 - pt11[0]) / dir_11_12[0]
    back_hem_inseam = pt11 + t_hem * dir_11_12  # where line hits hem level

    # -- Step 1b: Back inseam curve (11 → 12) --
    dir_11_to_12 = pt12 - pt11
    dir_11_to_12_norm = dir_11_to_12 / np.linalg.norm(dir_11_to_12)
    angle = np.radians(15)
    tan_at_11 = np.array([
        dir_11_to_12_norm[0] * np.cos(angle) - dir_11_to_12_norm[1] * np.sin(angle),
        dir_11_to_12_norm[0] * np.sin(angle) + dir_11_to_12_norm[1] * np.cos(angle),
    ])
    # Use the actual straight-segment direction (12 → back_hem) for the arrival
    # tangent so the curve flows naturally into the straight lower inseam.
    # (back_hem_inseam is only a construction point; back_hem is the real endpoint.)
    straight_dir = back_hem - pt12
    straight_dir_norm = straight_dir / np.linalg.norm(straight_dir)
    dist_11_12 = np.linalg.norm(dir_11_to_12)
    curve_back_inseam = _bezier_cubic(
        pt11,
        pt11 + tan_at_11 * (dist_11_12 / 4),
        pt12 - straight_dir_norm * (dist_11_12 / 4),
        pt12,
    )

    # -- Step 2: The Seat Angle --

    # 3/8" from pt2 on the baseline toward pt4 (more negative x)
    new_pt2 = fpts['2'] + np.array([-3/8 * INCH, 0])

    # Extend hip line from pt4 past pt8 by 1"
    dir_4to8 = fpts['8'] - fpts['4']
    dir_4to8_norm = dir_4to8 / np.linalg.norm(dir_4to8)
    new_pt8 = fpts['8'] + dir_4to8_norm * (1 * INCH)

    # Line from new_pt2 through new_pt8
    seat_line_dir = new_pt8 - new_pt2
    seat_line_dir_norm = seat_line_dir / np.linalg.norm(seat_line_dir)

    # Seat angle: perpendicular to seat_line_dir at new_pt8, toward the waist
    seat_angle_dir = np.array([seat_line_dir[1], -seat_line_dir[0]])
    seat_angle_dir_norm = seat_angle_dir / np.linalg.norm(seat_angle_dir)
    if seat_angle_dir_norm[0] > 0:
        seat_angle_dir_norm = -seat_angle_dir_norm

    seat_angle_end = new_pt8 + seat_angle_dir_norm * 40

    # Seat/crotch curve tangent directions
    seat_to_crotch_dir = -seat_angle_dir_norm
    dist_8_11 = np.linalg.norm(pt11 - new_pt8)

    inseam_dir_at_11 = (pt12 - pt11)
    inseam_dir_at_11_norm = inseam_dir_at_11 / np.linalg.norm(inseam_dir_at_11)
    perp_inseam = np.array([-inseam_dir_at_11_norm[1], inseam_dir_at_11_norm[0]])
    if np.dot(perp_inseam, new_pt8 - pt11) < 0:
        perp_inseam = -perp_inseam

    # -- Step 3: The Waist Seam --

    # Waist line from pt1, perpendicular to seat angle (= parallel to seat line)
    waist_line_dir = seat_line_dir_norm.copy()
    if waist_line_dir[1] > 0:
        waist_line_dir = -waist_line_dir

    # Intersection of waist line with seat angle line
    A = np.column_stack([waist_line_dir, -seat_angle_dir_norm])
    b = new_pt8 - fpts['1']
    params = np.linalg.solve(A, b)
    waist_seat_intersection = fpts['1'] + params[0] * waist_line_dir

    # Back waist width
    # Use arc length of rise curve (the actual seam length),
    # not the chord distance, per MHTML: "measure the waist seam of the front"
    front_waist_width = _curve_length(front['curves']['rise'])
    back_waist_target = m['waist'] / 2 + 3/4 * INCH
    back_waist_width = back_waist_target - front_waist_width
    back_waist_pt = fpts['1'] + waist_line_dir * (back_waist_width / np.linalg.norm(waist_line_dir))

    # -- Final seat seam (back_waist_pt → 8' → 11) --

    # Upper seat: gentle curve from back_waist to 8', departing at 90° to waist
    # MHTML: "starting at 90 degrees to the waist, gently curving into point 8"
    # The waist direction is waist_line_dir; perpendicular (toward 8') is the
    # seat angle direction.  We use that as the departure tangent at back_waist.
    dist_bw_8 = np.linalg.norm(new_pt8 - back_waist_pt)
    # At back_waist: depart perpendicular to waist (= along seat_angle direction)
    bw_tangent = -seat_angle_dir_norm  # toward 8', away from waist
    if np.dot(bw_tangent, new_pt8 - back_waist_pt) < 0:
        bw_tangent = seat_angle_dir_norm
    # At 8': arrive along the seat angle direction (blending into seat_lower)
    curve_seat_upper = _bezier_cubic(
        back_waist_pt,
        back_waist_pt + bw_tangent * (dist_bw_8 / 3),
        new_pt8 + seat_angle_dir_norm * (dist_bw_8 / 3),
        new_pt8,
    )

    curve_seat_lower = _bezier_cubic(
        new_pt8,
        new_pt8 + seat_to_crotch_dir * (dist_8_11 / 3),
        pt11 + perp_inseam * (dist_8_11 / 3),
        pt11,
    )

    # -- Yoke seam reference line (same geometry as draft_jeans_yoke) --
    # yoke_side: 1.5" from pt1 toward pt4 along the outseam
    dir_1_to_4      = fpts['4'] - fpts['1']
    dir_1_to_4_norm = dir_1_to_4 / np.linalg.norm(dir_1_to_4)
    yoke_side = fpts['1'] + dir_1_to_4_norm * (1.5 * INCH)
    # yoke_seat: 2.75" along seat_upper from back_waist
    yoke_seat = _point_at_arclength(curve_seat_upper, 2.75 * INCH)
    # sub-curve of seat_upper from back_waist to yoke_seat
    yoke_seat_curve = _curve_up_to_arclength(curve_seat_upper, 2.75 * INCH)

    return {
        'points': {
            'back_hem': back_hem,
            '11': pt11,
            '12': pt12,
            "2'": new_pt2,
            "8'": new_pt8,
            'back_waist': back_waist_pt,
            'waist_seat_x': waist_seat_intersection,
            'yoke_side': yoke_side,
            'yoke_seat': yoke_seat,
        },
        'curves': {
            'back_inseam': curve_back_inseam,
            'seat_upper': curve_seat_upper,
            'seat_lower': curve_seat_lower,
            'yoke_seat_curve': yoke_seat_curve,   # seat_upper sub-curve to yoke_seat
        },
        'construction': {
            'inseam_line_start': pt11,
            'inseam_line_end': back_hem_inseam,
            'seat_line_start': new_pt2,
            'seat_line_end': new_pt2 + seat_line_dir_norm * 50,
            'seat_angle_start': new_pt8,
            'seat_angle_end': seat_angle_end,
            'waist_line_start': fpts['1'],
            'waist_line_end': fpts['1'] + waist_line_dir * 40,
        },
        'metadata': {
            'title': 'Historical Jeans Back Panel (1873)',
            'cut_count': 2,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_back(front, back, output_path='Logs/jeans_back.svg', debug=False, units='cm',
                    pdf_pages=None, ax=None, pocket=None):
    """Render the back panel and save as PNG.

    Always draws the pattern outline and internal reference lines.
    With debug=True, adds construction lines, point labels, and grid.
    If pocket is provided, draws the pocket placement outline.

    units : 'cm' or 'inch' — display unit for axes and annotations.
    """
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'
    fpts = {k: v * s for k, v in front['points'].items()}
    fcurves = {k: v * s for k, v in front['curves'].items()}
    bpts = {k: v * s for k, v in back['points'].items()}
    bcurves = {k: v * s for k, v in back['curves'].items()}
    bcon = {k: v * s for k, v in back['construction'].items()}

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    OUTLINE = SEAMLINE
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
    CON_STYLE = dict(color='gray', linewidth=0.5, linestyle='--', alpha=0.3)

    # -- Debug: front panel + construction lines --
    if debug:
        FRONT_STYLE = dict(color='gray', linewidth=1, alpha=0.3)
        for curve in fcurves.values():
            ax.plot(curve[:, 0], curve[:, 1], **FRONT_STYLE)
        for a, b in [('4', '0'), ("7'", '8'), ("3'", "0'"), ("0'", '0')]:
            ax.plot([fpts[a][0], fpts[b][0]], [fpts[a][1], fpts[b][1]], **FRONT_STYLE)

        # Construction: inseam line, seat line, seat angle, waist line
        ax.plot([bcon['inseam_line_start'][0], bcon['inseam_line_end'][0]],
                [bcon['inseam_line_start'][1], bcon['inseam_line_end'][1]], **CON_STYLE)
        ax.plot([bcon['seat_line_start'][0], bcon['seat_line_end'][0]],
                [bcon['seat_line_start'][1], bcon['seat_line_end'][1]], **CON_STYLE)
        ax.plot([bcon['seat_angle_start'][0], bcon['seat_angle_end'][0]],
                [bcon['seat_angle_start'][1], bcon['seat_angle_end'][1]],
                color='blue', linewidth=0.8, linestyle='--', alpha=0.4)
        ax.plot([bcon['waist_line_start'][0], bcon['waist_line_end'][0]],
                [bcon['waist_line_start'][1], bcon['waist_line_end'][1]], **CON_STYLE)

    # -- Pattern outline --

    # Waist line (pt1 → back_waist)
    ax.plot([fpts['1'][0], bpts['back_waist'][0]],
            [fpts['1'][1], bpts['back_waist'][1]], **OUTLINE)

    # Seat seam curves (back_waist → 8' → 11)
    ax.plot(bcurves['seat_upper'][:, 0], bcurves['seat_upper'][:, 1], **OUTLINE)
    ax.plot(bcurves['seat_lower'][:, 0], bcurves['seat_lower'][:, 1], **OUTLINE)

    # Back inseam curve (11 → 12)
    ax.plot(bcurves['back_inseam'][:, 0], bcurves['back_inseam'][:, 1], **OUTLINE)

    # Lower inseam straight (12 → back_hem)
    ax.plot([bpts['12'][0], bpts['back_hem'][0]],
            [bpts['12'][1], bpts['back_hem'][1]], **OUTLINE)

    # Outseam: back_hem → 0 → 4 → 1
    ax.plot([bpts['back_hem'][0], fpts['0'][0]],
            [bpts['back_hem'][1], fpts['0'][1]], **OUTLINE)
    ax.plot([fpts['0'][0], fpts['4'][0]],
            [fpts['0'][1], fpts['4'][1]], **OUTLINE)
    ax.plot([fpts['4'][0], fpts['1'][0]],
            [fpts['4'][1], fpts['1'][1]], **OUTLINE)

    # -- Yoke seam reference line (always shown) --
    # Shows where to cut the yoke away from the back body panel.
    YOKE_REF = dict(color='steelblue', linewidth=1.2, linestyle='--')
    ax.plot(bcurves['yoke_seat_curve'][:, 0], bcurves['yoke_seat_curve'][:, 1],
            **YOKE_REF)
    ax.plot([bpts['yoke_seat'][0], bpts['yoke_side'][0]],
            [bpts['yoke_seat'][1], bpts['yoke_side'][1]], **YOKE_REF)
    ax.plot([bpts['yoke_side'][0], fpts['1'][0]],
            [bpts['yoke_side'][1], fpts['1'][1]], **YOKE_REF)
    # Label near the midpoint of the straight yoke seam segment
    yoke_mid = (bpts['yoke_seat'] + bpts['yoke_side']) / 2
    ax.annotate('yoke seam', yoke_mid, textcoords="offset points",
                xytext=(0, -14), fontsize=7, color='steelblue', ha='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))
    # Notch at midpoint of straight yoke seam — matches the yoke piece
    _seam_d    = bpts['yoke_seat'] - bpts['yoke_side']
    _seam_norm = _seam_d / np.linalg.norm(_seam_d)
    _perp      = np.array([-_seam_norm[1], _seam_norm[0]])
    _nsize     = 0.25 * INCH * s
    ax.plot([yoke_mid[0] - _perp[0]*_nsize, yoke_mid[0] + _perp[0]*_nsize],
            [yoke_mid[1] - _perp[1]*_nsize, yoke_mid[1] + _perp[1]*_nsize],
            color='steelblue', linewidth=1.2)

    # -- Reference lines (clipped to pattern outline bounding box) --
    outline_pts = [fpts['1'], fpts['4'], fpts['0'], bpts['back_hem'],
                   bpts['12'], bpts['11'], bpts["8'"], bpts['back_waist']]
    y_lo = min(p[1] for p in outline_pts)
    y_hi = max(p[1] for p in outline_pts)
    x_lo = min(p[0] for p in outline_pts)
    x_hi = max(p[0] for p in outline_pts)

    seat_x = fpts['4'][0]
    ax.plot([seat_x, seat_x], [y_lo, y_hi], **REF)
    ax.annotate('seat', (seat_x, y_hi), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    hip_x = fpts['2'][0]
    ax.plot([hip_x, hip_x], [y_lo, y_hi], **REF)
    ax.annotate('hip', (hip_x, y_hi), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    knee_x = fpts['3'][0]
    ax.plot([knee_x, knee_x], [y_lo, y_hi], **REF)
    ax.annotate('knee', (knee_x, y_hi), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    cf_mid = (x_lo + x_hi) / 2
    ax.plot([x_lo, x_hi], [fpts['10'][1], fpts['10'][1]], **REF)
    ax.annotate('center front', (cf_mid, fpts['10'][1]), textcoords="offset points",
                xytext=(0, 4), fontsize=7, color='gray', ha='center')

    # -- Debug: point labels --
    if debug:
        for name, pt in bpts.items():
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=5, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=8)
        for name, pt in fpts.items():
            if name == 'temp':
                continue
            ax.plot(pt[0], pt[1], 'o', color='gray', markersize=3, zorder=5, alpha=0.4)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=7, color='gray', alpha=0.5)

        # Measurement annotations
        _annotate_segment(ax, fpts['1'], bpts['back_waist'], offset=(0, 8))
        _annotate_curve(ax, bcurves['seat_upper'], offset=(-10, 0))
        _annotate_curve(ax, bcurves['seat_lower'], offset=(-10, 0))
        _annotate_curve(ax, bcurves['back_inseam'], offset=(10, 0))
        _annotate_segment(ax, bpts['12'], bpts['back_hem'], offset=(10, 0))
        _annotate_segment(ax, bpts['back_hem'], fpts['0'], offset=(0, 8))
        _annotate_segment(ax, fpts['0'], fpts['4'], offset=(0, 8))
        _annotate_segment(ax, fpts['4'], fpts['1'], offset=(-10, 0))

    # --- Seam allowances (always drawn) ---
    from .seam_allowances import SEAM_ALLOWANCES
    SA = SEAM_ALLOWANCES['back']
    SA_SIDE    = SA['side']
    SA_HEM     = SA['hem']
    SA_INSEAM  = SA['inseam']
    SA_SEAT    = SA['seat']
    SA_YOKE    = SA['yoke']

    # Extra cutting width at the yoke seam for gathering/easing into the yoke
    EASE_YOKE = 3/4 * INCH
    SA_YOKE_TOTAL = SA_YOKE + EASE_YOKE

    # CW outline: outseam(1→4→0) → hem(0→back_hem) → lower_inseam(back_hem→12)
    #   → back_inseam(12→11) → seat_lower(11→8') → seat_upper(8'→back_waist)
    #   → waist(back_waist→1)
    sa_edges = [
        (np.array([fpts['1'], fpts['4']]),                       SA_SIDE),    # outseam upper
        (np.array([fpts['4'], fpts['0']]),                       SA_SIDE),    # outseam lower
        (np.array([fpts['0'], bpts['back_hem']]),                SA_HEM),     # hem
        (np.array([bpts['back_hem'], bpts['12']]),               SA_INSEAM),  # lower inseam straight
        (bcurves['back_inseam'][::-1],                           SA_INSEAM),  # back inseam curve (12→11)
        (bcurves['seat_lower'][::-1],                            SA_SEAT),    # seat lower (11→8')
        (bcurves['seat_upper'][::-1],                            SA_SEAT),    # seat upper (8'→back_waist)
        (np.array([bpts['back_waist'], fpts['1']]),              SA_YOKE_TOTAL),  # waist (SA + ease)
    ]
    draw_seam_allowance(ax, sa_edges, scale=s)

    # Annotate the ease at yoke seam
    yoke_ease_pt = (bpts['back_waist'] + fpts['1']) / 2
    _ease_dir = fpts['1'] - bpts['back_waist']
    _ease_perp = np.array([-_ease_dir[1], _ease_dir[0]])
    _ease_perp = _ease_perp / np.linalg.norm(_ease_perp)
    # Point away from the pattern (same side as the SA)
    if _ease_perp[0] > 0:
        _ease_perp = -_ease_perp
    ax.annotate('\u00be" SA + \u00be" ease \u2014 gather to fit yoke',
                yoke_ease_pt + _ease_perp * SA_YOKE_TOTAL * s * 1.3,
                fontsize=6, ha='center', va='center', color='steelblue',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))

    # --- Back pocket placement outline ---
    if pocket is not None:
        POCKET_STYLE = dict(color='steelblue', linewidth=1.0, linestyle='--', alpha=0.6)
        ppts = {k: v * s for k, v in pocket['points'].items()}
        p_order = ['f_tl', 'f_tr', 'f_ref_r', 'f_bottom', 'f_ref_l', 'f_tl']
        px = [ppts[k][0] for k in p_order]
        py = [ppts[k][1] for k in p_order]
        ax.plot(px, py, **POCKET_STYLE)
        p_mid = (ppts['f_tl'] + ppts['f_tr']) / 2
        ax.annotate('back pocket', p_mid, textcoords="offset points",
                    xytext=(0, 8), fontsize=7, color='steelblue', ha='center',
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))


    # --- Grainline and piece label (pattern mode only) ---
    if not debug:
        from garment_programs.plot_utils import draw_grainline, draw_piece_label
        # Grainline vertical, midpoint between outseam and inseam, waist to hem
        mid_y = (fpts['0'][1] + bpts['back_hem'][1]) / 2
        grain_x = (fpts['0'][0] + fpts['1'][0]) / 2  # midpoint of outseam range
        grain_top_pt = np.array([fpts['1'][0] * 0.85 + fpts['0'][0] * 0.15, mid_y])
        grain_bot_pt = np.array([fpts['1'][0] * 0.15 + fpts['0'][0] * 0.85, mid_y])
        draw_grainline(ax, grain_top_pt, grain_bot_pt)

        # Piece label at bounding-box center
        all_x = [fpts['0'][0], fpts['1'][0], bpts['back_hem'][0], bpts['11'][0]]
        all_y = [fpts['0'][1], fpts['1'][1], bpts['back_hem'][1], bpts['11'][1]]
        center = ((min(all_x) + max(all_x)) / 2, (min(all_y) + max(all_y)) / 2)
        draw_piece_label(ax, center, back['metadata']['title'],
                         back['metadata'].get('cut_count'))

    if not debug:
        ax.axis('off')
    else:
        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)

    if standalone:
        from garment_programs.plot_utils import save_pattern
        save_pattern(fig, ax, output_path, units=units, calibration=not debug,
                     pdf_pages=pdf_pages)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None):
    """Uniform interface called by the generic runner."""
    m = load_measurements(measurements_path)
    front = draft_jeans_front(m)
    back = draft_jeans_back(m, front)
    # Draft pocket so we can show its placement on the back panel
    from .jeans_yoke_1873 import draft_jeans_yoke
    from .jeans_back_pocket import draft_jeans_back_pocket
    yoke = draft_jeans_yoke(m, front, back)
    pocket = draft_jeans_back_pocket(m, front, back, yoke)
    plot_jeans_back(front, back, output_path, debug=debug, units=units,
                    pdf_pages=pdf_pages, pocket=pocket)
