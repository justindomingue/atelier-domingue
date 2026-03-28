"""
Historical Jeans Back Panel (1873 style)
Based on: Historical Tailoring Masterclasses - Drafting the Back

Drafted relative to the front panel.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from garment_programs.plot_utils import (
    SEAMLINE, draw_notch, draw_seam_allowance, display_scale, setup_figure,
    finalize_figure,
)
from garment_programs.core.types import DraftData
from garment_programs.core.runtime import cache_draft, resolve_measurements
from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _bezier_cubic, _bezier_quad,
    _annotate_curve, _annotate_segment,
    _point_at_arclength, _curve_up_to_arclength, _curve_from_arclength,
    _curve_length,
)
from .seam_allowances import YOKE_SEAT_DEPTH


# -- Drafting ----------------------------------------------------------------

def draft_jeans_back(m: dict[str, float], front: DraftData,
                     gathering_amount=0) -> DraftData:
    """
    Compute back panel geometry, built on top of the front draft.

    Parameters
    ----------
    m : dict
        Measurements in cm.
    front : dict
        Result of draft_jeans_front(m).
    gathering_amount : float, optional
        Extra width (in cm) to add at the yoke/seat junction, tapering
        to zero at pt 8'.  Creates gathering on the 1873 backs.
        Default 0 (no gathering).

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
    # yoke_seat: walk along seat_upper from back_waist
    yoke_seat = _point_at_arclength(curve_seat_upper, YOKE_SEAT_DEPTH)
    # sub-curve of seat_upper from back_waist to yoke_seat
    yoke_seat_curve = _curve_up_to_arclength(curve_seat_upper, YOKE_SEAT_DEPTH)
    # sub-curve of seat_upper from yoke_seat to 8' (body below yoke)
    seat_upper_below_yoke = _curve_from_arclength(curve_seat_upper, YOKE_SEAT_DEPTH)

    # -- Gathering taper (1873 variant) --
    # MHTML: "extend the yoke seam on the seat seam side by 1/2" to 1"
    # and taper that into the seat seam just above the crotch curve."
    # This adds a wedge of extra fabric between the yoke seam and pt 8'
    # on the back body; the extra width gets gathered into the yoke.
    gathering = None
    if gathering_amount > 0:
        yoke_seam_dir = yoke_seat - yoke_side
        yoke_seam_dir_norm = yoke_seam_dir / np.linalg.norm(yoke_seam_dir)
        gathering_ext_pt = yoke_seat + yoke_seam_dir_norm * gathering_amount
        # Smooth taper from the extension back to pt 8' (top of crotch curve)
        taper_dist = np.linalg.norm(new_pt8 - gathering_ext_pt)
        gathering_taper = _bezier_cubic(
            gathering_ext_pt,
            gathering_ext_pt + (new_pt8 - gathering_ext_pt) / 3,
            new_pt8 + seat_angle_dir_norm * (taper_dist / 4),
            new_pt8,
        )
        gathering = {
            'ext_pt': gathering_ext_pt,
            'taper': gathering_taper,
            'amount': gathering_amount,
        }

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
            'seat_upper_below_yoke': seat_upper_below_yoke,  # seat_upper from yoke_seat to 8'
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
        'gathering': gathering,
        'metadata': {
            'title': 'Back',
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
    s, unit_label = display_scale(units)
    fpts = {k: v * s for k, v in front['points'].items()}
    fcurves = {k: v * s for k, v in front['curves'].items()}
    bpts = {k: v * s for k, v in back['points'].items()}
    bcurves = {k: v * s for k, v in back['curves'].items()}
    bcon = {k: v * s for k, v in back['construction'].items()}

    fig, ax, standalone = setup_figure(ax, figsize=(16, 10))
    OUTLINE = SEAMLINE
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
    CON_STYLE = dict(color='gray', linewidth=0.5, linestyle='--', alpha=0.3)

    gathering = back.get('gathering')
    if gathering is not None:
        g_ext = gathering['ext_pt'] * s
        g_taper = gathering['taper'] * s

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

    # -- Outline and seam allowances (mode-dependent) --
    from .seam_allowances import SEAM_ALLOWANCES, SEAM_LABELS
    SA = SEAM_ALLOWANCES['back']
    SL = SEAM_LABELS['back']
    SA_SIDE    = SA['side']
    SA_HEM     = SA['hem']
    SA_INSEAM  = SA['inseam']
    SA_SEAT    = SA['seat']
    SA_YOKE    = SA['yoke']

    if debug:
        # -- Full panel outline (debug mode) --
        ax.plot([fpts['1'][0], bpts['back_waist'][0]],
                [fpts['1'][1], bpts['back_waist'][1]], **OUTLINE)
        ax.plot(bcurves['seat_upper'][:, 0], bcurves['seat_upper'][:, 1], **OUTLINE)
        ax.plot(bcurves['seat_lower'][:, 0], bcurves['seat_lower'][:, 1], **OUTLINE)
        ax.plot(bcurves['back_inseam'][:, 0], bcurves['back_inseam'][:, 1], **OUTLINE)
        ax.plot([bpts['12'][0], bpts['back_hem'][0]],
                [bpts['12'][1], bpts['back_hem'][1]], **OUTLINE)
        ax.plot([bpts['back_hem'][0], fpts['0'][0]],
                [bpts['back_hem'][1], fpts['0'][1]], **OUTLINE)
        ax.plot([fpts['0'][0], fpts['4'][0]],
                [fpts['0'][1], fpts['4'][1]], **OUTLINE)
        ax.plot([fpts['4'][0], fpts['1'][0]],
                [fpts['4'][1], fpts['1'][1]], **OUTLINE)

        # -- Yoke seam reference line --
        YOKE_REF = dict(color='steelblue', linewidth=1.2, linestyle='--')
        ax.plot(bcurves['yoke_seat_curve'][:, 0], bcurves['yoke_seat_curve'][:, 1],
                **YOKE_REF)
        ax.plot([bpts['yoke_seat'][0], bpts['yoke_side'][0]],
                [bpts['yoke_seat'][1], bpts['yoke_side'][1]], **YOKE_REF)
        ax.plot([bpts['yoke_side'][0], fpts['1'][0]],
                [bpts['yoke_side'][1], fpts['1'][1]], **YOKE_REF)
        yoke_mid = (bpts['yoke_seat'] + bpts['yoke_side']) / 2
        ax.annotate('yoke seam', yoke_mid, textcoords="offset points",
                    xytext=(0, -14), fontsize=7, color='steelblue', ha='center',
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))

        # -- Gathering taper annotation (1873 variant) --
        if gathering is not None:
            GATHER = dict(color='red', linewidth=1.2)
            ax.plot([bpts['yoke_seat'][0], g_ext[0]],
                    [bpts['yoke_seat'][1], g_ext[1]], **GATHER)
            ax.plot(g_taper[:, 0], g_taper[:, 1], **GATHER)
            g_mid = (g_ext + bpts["8'"]) / 2
            ax.annotate('gathering', g_mid, textcoords="offset points",
                        xytext=(-12, -8), fontsize=7, color='red', ha='center',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white',
                                  ec='none', alpha=0.8))

        # -- SA on full outline --
        sa_edges = [
            (np.array([fpts['1'], fpts['4']]),                       SA_SIDE, SL['side']),
            (np.array([fpts['4'], fpts['0']]),                       SA_SIDE, SL['side']),
            (np.array([fpts['0'], bpts['back_hem']]),                SA_HEM, SL['hem']),
            (np.array([bpts['back_hem'], bpts['12']]),               SA_INSEAM, SL['inseam']),
            (bcurves['back_inseam'][::-1],                           SA_INSEAM, SL['inseam']),
            (bcurves['seat_lower'][::-1],                            SA_SEAT, SL['seat']),
            (bcurves['seat_upper'][::-1],                            SA_SEAT, SL['seat']),
            (np.array([bpts['back_waist'], fpts['1']]),              SA_YOKE, SL['yoke']),
        ]
    else:
        # -- Body below yoke (pattern mode) --
        # Outseam below yoke
        ax.plot([bpts['yoke_side'][0], fpts['4'][0]],
                [bpts['yoke_side'][1], fpts['4'][1]], **OUTLINE)
        ax.plot([fpts['4'][0], fpts['0'][0]],
                [fpts['4'][1], fpts['0'][1]], **OUTLINE)
        # Hem
        ax.plot([fpts['0'][0], bpts['back_hem'][0]],
                [fpts['0'][1], bpts['back_hem'][1]], **OUTLINE)
        # Inseam
        ax.plot([bpts['back_hem'][0], bpts['12'][0]],
                [bpts['back_hem'][1], bpts['12'][1]], **OUTLINE)
        ax.plot(bcurves['back_inseam'][:, 0], bcurves['back_inseam'][:, 1], **OUTLINE)
        # Seat lower
        ax.plot(bcurves['seat_lower'][:, 0], bcurves['seat_lower'][:, 1], **OUTLINE)

        if gathering is not None:
            # Original center back (ungathered) as dotted reference
            ORIG_REF = dict(color='gray', linewidth=0.8, linestyle=':', alpha=0.5)
            ax.plot(bcurves['seat_upper_below_yoke'][:, 0],
                    bcurves['seat_upper_below_yoke'][:, 1], **ORIG_REF)
            ax.plot([bpts['yoke_seat'][0], bpts['yoke_side'][0]],
                    [bpts['yoke_seat'][1], bpts['yoke_side'][1]], **ORIG_REF)
            # Gathering taper replaces seat_upper_below_yoke — drawn in red
            GATHER_LINE = dict(color='red', linewidth=1.5)
            ax.plot(g_taper[:, 0], g_taper[:, 1], **GATHER_LINE)
            # Yoke seam extends to gathering extension point
            ax.plot([g_ext[0], bpts['yoke_side'][0]],
                    [g_ext[1], bpts['yoke_side'][1]], **OUTLINE)
            # Gathering annotation (visible in lay plan)
            g_mid = (g_ext + bpts["8'"]) / 2
            ax.annotate('gathering', g_mid, textcoords="offset points",
                        xytext=(-12, -8), fontsize=7, color='red', ha='center',
                        bbox=dict(boxstyle='round,pad=0.2', fc='white',
                                  ec='none', alpha=0.8))
            sa_edges = [
                (np.array([bpts['yoke_side'], fpts['4']]),           SA_SIDE, SL['side']),
                (np.array([fpts['4'], fpts['0']]),                   SA_SIDE, SL['side']),
                (np.array([fpts['0'], bpts['back_hem']]),            SA_HEM, SL['hem']),
                (np.array([bpts['back_hem'], bpts['12']]),           SA_INSEAM, SL['inseam']),
                (bcurves['back_inseam'][::-1],                       SA_INSEAM, SL['inseam']),
                (bcurves['seat_lower'][::-1],                        SA_SEAT, SL['seat']),
                (g_taper[::-1],                                      SA_SEAT, SL['seat']),
                (np.array([g_ext, bpts['yoke_side']]),               SA_YOKE, SL['yoke']),
            ]
        else:
            # Seat upper below yoke
            ax.plot(bcurves['seat_upper_below_yoke'][:, 0],
                    bcurves['seat_upper_below_yoke'][:, 1], **OUTLINE)
            # Yoke seam (top boundary)
            ax.plot([bpts['yoke_seat'][0], bpts['yoke_side'][0]],
                    [bpts['yoke_seat'][1], bpts['yoke_side'][1]], **OUTLINE)
            sa_edges = [
                (np.array([bpts['yoke_side'], fpts['4']]),           SA_SIDE, SL['side']),
                (np.array([fpts['4'], fpts['0']]),                   SA_SIDE, SL['side']),
                (np.array([fpts['0'], bpts['back_hem']]),            SA_HEM, SL['hem']),
                (np.array([bpts['back_hem'], bpts['12']]),           SA_INSEAM, SL['inseam']),
                (bcurves['back_inseam'][::-1],                       SA_INSEAM, SL['inseam']),
                (bcurves['seat_lower'][::-1],                        SA_SEAT, SL['seat']),
                (bcurves['seat_upper_below_yoke'][::-1],             SA_SEAT, SL['seat']),
                (np.array([bpts['yoke_seat'], bpts['yoke_side']]),   SA_YOKE, SL['yoke']),
            ]

    cut_outline = draw_seam_allowance(ax, sa_edges, scale=s, label_sas=not debug,
                                      units=units)

    # -- Yoke seam notch (matches yoke piece notch placement) --
    seam_start = g_ext if gathering is not None else bpts['yoke_seat']
    seam_end = bpts['yoke_side']
    seam_mid = (seam_start + seam_end) / 2
    draw_notch(ax, np.array([seam_start, seam_end]), seam_mid, SA_YOKE, scale=s,
               count=2)

    # -- Ease note on yoke seam (back is wrap side of the flat-fell; its cut
    #    edge runs longer than the yoke's — distribute fullness when basting) --
    if not debug and gathering is None:
        ax.annotate('ease into yoke', seam_mid, textcoords="offset points",
                    xytext=(0, -12), fontsize=7, color='gray', ha='center',
                    bbox=dict(boxstyle='round,pad=0.2', fc='white',
                              ec='none', alpha=0.8))

    # -- Balance notches: knee + hem on side seam and inseam --
    # Hem notches are pulled slightly off the corners to avoid seam intersections.
    hem_t = 0.06
    side_hem_pt = fpts['0'] + (fpts['4'] - fpts['0']) * hem_t
    inseam_hem_pt = bpts['back_hem'] + (bpts['12'] - bpts['back_hem']) * hem_t
    draw_notch(ax, np.array([fpts['4'], fpts['0']]), fpts['3'], SA_SIDE, scale=s)
    draw_notch(ax, np.array([bpts['back_hem'], bpts['12']]), bpts['12'], SA_INSEAM, scale=s)
    draw_notch(ax, np.array([fpts['4'], fpts['0']]), side_hem_pt, SA_SIDE, scale=s)
    draw_notch(ax, np.array([bpts['back_hem'], bpts['12']]), inseam_hem_pt, SA_INSEAM, scale=s)

    # -- Reference lines (clipped to piece outline at each x-position) --
    if debug:
        outline_pts = [fpts['1'], fpts['4'], fpts['0'], bpts['back_hem'],
                       bpts['12'], bpts['11'], bpts["8'"], bpts['back_waist']]
    else:
        outline_pts = [bpts['yoke_side'], fpts['4'], fpts['0'], bpts['back_hem'],
                       bpts['12'], bpts['11'], bpts["8'"], bpts['yoke_seat']]
        if gathering is not None:
            outline_pts.append(g_ext)
    x_lo = min(p[0] for p in outline_pts)
    x_hi = max(p[0] for p in outline_pts)

    # Seat line — clipped to outseam (pt4) → inseam (pt8')
    seat_x = fpts['4'][0]
    ax.plot([seat_x, seat_x], [fpts['4'][1], bpts["8'"][1]], **REF)
    ax.annotate('seat', (seat_x, fpts['4'][1]), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    # Hip line — clipped to baseline (pt2) → seat depth (pt5)
    hip_x = fpts['2'][0]
    ax.plot([hip_x, hip_x], [fpts['2'][1], fpts['5'][1]], **REF)
    ax.annotate('hip', (hip_x, fpts['2'][1]), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    # Knee line — clipped to baseline (pt3) → back knee point (pt12)
    knee_x = fpts['3'][0]
    ax.plot([knee_x, knee_x], [fpts['3'][1], bpts['12'][1]], **REF)
    ax.annotate('knee', (knee_x, fpts['3'][1]), textcoords="offset points",
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
        # Grainline vertical, midpoint between outseam and inseam, yoke to hem
        top_ref = bpts['yoke_side']
        mid_y = (fpts['0'][1] + bpts['back_hem'][1]) / 2
        grain_top_pt = np.array([top_ref[0] * 0.85 + fpts['0'][0] * 0.15, mid_y])
        grain_bot_pt = np.array([top_ref[0] * 0.15 + fpts['0'][0] * 0.85, mid_y])
        draw_grainline(ax, grain_top_pt, grain_bot_pt)

        # Piece label at bounding-box center (top = yoke seam)
        all_x = [fpts['0'][0], bpts['yoke_side'][0], bpts['back_hem'][0], bpts['11'][0]]
        all_y = [fpts['0'][1], bpts['yoke_side'][1], bpts['back_hem'][1], bpts['11'][1]]
        center = ((min(all_x) + max(all_x)) / 2, (min(all_y) + max(all_y)) / 2)
        draw_piece_label(ax, center, back['metadata']['title'],
                         back['metadata'].get('cut_count'),
                         metadata=back.get('metadata'))

    return finalize_figure(ax, fig, standalone, output_path, units=units,
                           debug=debug, pdf_pages=pdf_pages,
                           outline_pts=cut_outline)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None,
        gathering_amount=0, context=None):
    """Uniform interface called by the generic runner."""
    m = resolve_measurements(context, measurements_path, load_measurements)
    front = cache_draft(context, 'selvedge.front', lambda: draft_jeans_front(m))
    back_key = f'selvedge.back:{gathering_amount:.4f}'
    back = cache_draft(
        context,
        back_key,
        lambda: draft_jeans_back(m, front, gathering_amount=gathering_amount),
    )
    # Draft pocket so we can show its placement on the back panel
    from .jeans_yoke_1873 import draft_jeans_yoke
    from .jeans_back_pocket import draft_jeans_back_pocket
    yoke = cache_draft(
        context,
        f'selvedge.yoke_1873:{gathering_amount:.4f}',
        lambda: draft_jeans_yoke(m, front, back),
    )
    pocket = cache_draft(
        context,
        f'selvedge.back_pocket:{gathering_amount:.4f}',
        lambda: draft_jeans_back_pocket(m, front, back, yoke),
    )
    outline = plot_jeans_back(front, back, output_path, debug=debug, units=units,
                              pdf_pages=pdf_pages, pocket=pocket)
    if outline:
        return {'layout_outline': outline}
