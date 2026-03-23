"""
Trouser Front Panel (MM&S Basic Block)

Based on: MM&S - Basic Block: Trousers (0, 1, or 2 Pleats) - Front Pattern

Coordinate system:
  - Origin A at bottom-left (hemline, left reference edge)
  - X axis: positive to the right
  - Y axis: positive upward
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from garment_programs.core.types import DraftData
from garment_programs.geometry import (
    INCH, _bezier_cubic, _bezier_quad, _curve_length, _annotate_len,
)
from garment_programs.measurements import load_measurements
from .ease_config import EaseConfig, load_ease
from .seam_allowances import SEAM_ALLOWANCES

# -- Pleat configuration by count ---------------------------------------------
# Each pleat_offsets entry is (left_offset, right_offset) relative to creaseline_x.
# The 0-pleat variant is MM&S "Trousers with Dart" (pp. 30–33) — it carries a
# front DART, not zero shaping. A dart converges to an apex; a pleat folds.
PLEAT_CONFIGS = {
    0: {'ftw_ease': 0.0, 'pleat_offsets': [],
        'dart': {'intake': 2.0, 'length': 9.5},   # centred on creaseline; 9–10 cm
        'cf_waist_taper': 0.5,                    # CF pulled in 0.5 cm at waist
        'sideseam_relocation': 1.0, 'half_ease_range': (2.5, 4.5)},
    1: {'ftw_ease': 1.0, 'pleat_offsets': [(-3.5, 0.0)],
        'dart': None, 'cf_waist_taper': 0.0,
        'sideseam_relocation': 1.5, 'half_ease_range': (3.5, 5.5)},
    2: {'ftw_ease': 3.5, 'pleat_offsets': [(-3.5, 0.5), (-9.5, -7.0)],
        'dart': None, 'cf_waist_taper': 0.0,
        'sideseam_relocation': 1.0, 'half_ease_range': (5.5, 8.0)},
}
PLEAT_NAMES = {0: 'Dart', 1: '1-Pleat', 2: '2-Pleat'}




# -- Drafting ----------------------------------------------------------------

def draft_trouser_front(m: dict[str, float], num_pleats: int = 1,
                        ease: EaseConfig = EaseConfig()) -> DraftData:
    """
    Compute all geometry for the trouser front.

    Parameters
    ----------
    m : dict  Measurements in cm.
    num_pleats : int  Number of pleats (0, 1, or 2).
    ease : EaseConfig  Tunable ease/fit parameters (range midpoints by default).

    Returns
    -------
    dict with keys: points, levels, construction, curves, measurements, metadata
    """
    config = PLEAT_CONFIGS[num_pleats]

    # -- Extract measurements --
    Wbg = m['waist']        # waistband girth (full circumference)
    Hg  = m['seat']         # hip girth (full circumference)
    Hw  = m['hem_width']    # hem width (full circumference)
    Sl  = m['side_length']  # side length (waist to floor)
    Is  = m['inseam']       # inseam (crotch to floor)

    # -- Derived measurements --
    Br  = Sl - Is                        # body rise
    Kh  = Is / 2 + Is / 10 - 2.0         # knee height
    Ftw = Hg / 4 + config['ftw_ease']    # front trouser width
    Fcw = Hg / 2 / 10 + 1.0              # front crotch width
    Cw  = Hg / 4 - ease.cw_reduction     # crotch width (total)
    Bcw = Cw - Fcw                       # back crotch width
    Btw = Hg / 4 + ease.btw_ease         # back trouser width

    # ==========================================================
    # Step 1: Framework — vertical + horizontal reference lines
    # ==========================================================
    hem_y    = 0.0
    knee_y   = Kh
    crotch_y = Is
    hip_rise = Hg / 2 / 10 + 3.0     # 1/10 of 1/2 Hg + 3 cm above crotch
    hip_y    = crotch_y + hip_rise
    waist_y  = Sl

    # ==========================================================
    # Step 2: Widths and creaseline
    # ==========================================================
    ftw_x        = Ftw                 # Ftw perpendicular on hipline
    fcw_mark_x   = Ftw + Fcw          # Fcw construction mark (total front width)
    creaseline_x = fcw_mark_x / 2     # midpoint: front creaseline / grainline
    mid_hip_crotch_y = (hip_y + crotch_y) / 2

    # ==========================================================
    # Step 3: Hem widths, pleat, CF
    # ==========================================================
    hem_half = Hw / 4 - 1.0           # each side of creaseline
    hem_side_x   = creaseline_x - hem_half
    hem_inseam_x = creaseline_x + hem_half

    # 0.5 cm inward from each hem edge → sideseam/inseam guidelines
    hem_side_guide_x   = hem_side_x + 0.5
    hem_inseam_guide_x = hem_inseam_x - 0.5

    # Pleat edges: (left, right) offsets from creaseline_x
    pleats = [(creaseline_x + lo, creaseline_x + ro)
              for lo, ro in config['pleat_offsets']]
    pleat_intake = sum(ro - lo for lo, ro in pleats)

    # Front dart (0-pleat / "Trousers with Dart" variant only):
    # centred on the creaseline, converges to an apex dart_length below waist.
    dart_spec = config['dart']
    if dart_spec:
        dart_intake = dart_spec['intake']
        dart_length = dart_spec['length']
        front_dart = {
            'left':  creaseline_x - dart_intake / 2,
            'right': creaseline_x + dart_intake / 2,
            'apex':  np.array([creaseline_x, waist_y - dart_length]),
            'intake': dart_intake,
        }
    else:
        dart_intake = 0.0
        front_dart = None

    # Total front-waist shaping intake (pleats + dart) — drives the waist
    # formula here and the back-pattern waist-transfer subtraction.
    pleat_total_intake = pleat_intake + dart_intake

    # Centre front (CF): Ftw + 0.5 on hipline, angled to Ftw at waistline.
    # The dart variant additionally tapers CF inward 0.5 cm at the waist.
    cf_hip_x   = Ftw + 0.5
    cf_waist_x = Ftw - config['cf_waist_taper']

    # Crotch point: interpolated along the inseam guideline rather than placed
    # directly at (Ftw+Fcw, crotch_y) per PDF step 2. The PDF placement shifts
    # the point ~0.6 cm outward and produces a worse curve shape in practice;
    # the interpolated position gives a cleaner J-curve. See audit notes.
    t_crotch = (crotch_y - hem_y) / (hip_y - hem_y)
    crotch_pt_x = hem_inseam_guide_x + t_crotch * (fcw_mark_x - hem_inseam_guide_x)
    crotch_pt = np.array([crotch_pt_x, crotch_y])

    # ==========================================================
    # Step 4: Shaping
    # ==========================================================
    # Knee points: intersect sideseam guideline at knee line, then taper 1 cm out.
    # Sideseam guideline: hem_side_guide (hem_side_guide_x, 0) → mid_side (0, mid_hip_crotch_y)
    t_knee_side = (knee_y - hem_y) / (mid_hip_crotch_y - hem_y)
    knee_side_on_guide = hem_side_guide_x + t_knee_side * (0.0 - hem_side_guide_x)
    knee_side_x   = knee_side_on_guide + 1.0  # 1 cm inward (toward creaseline)
    # Measure to creaseline and transfer to the right
    knee_side_dist = creaseline_x - knee_side_x
    knee_inseam_x = creaseline_x + knee_side_dist

    # CF direction (waist→hip, continuing downward) — kept for construction display
    cf_dir = np.array([cf_hip_x - cf_waist_x, hip_y - waist_y])
    t_cf_crotch = (crotch_y - waist_y) / cf_dir[1]
    cf_at_crotch = np.array([cf_waist_x + t_cf_crotch * cf_dir[0], crotch_y])

    # Crotch guide: half the distance from CF@crotch to crotch_pt, transferred
    # upward from CF@crotch. Deviates from the PDF's (Ftw, hip_y+Fcw/2)
    # placement — paired with the interpolated crotch point above, this gives
    # a cleaner J-curve shape. See audit notes.
    half_crotch_dist = (crotch_pt_x - cf_at_crotch[0]) / 2
    crotch_guide = np.array([cf_at_crotch[0], crotch_y + half_crotch_dist])

    # Waist sideseam (MM&S step 4): from CF on the waistline measure left by
    #   ¼ Wbg + pleat depth − sideseam relocation.
    # The residual distance from x=0 is the hip-curve intake; the PDF says
    # it "should be no larger than 1–1.5 cm for a shallow hip curve."
    sideseam_relocation = config['sideseam_relocation']
    waist_width = Wbg / 4 + pleat_total_intake - sideseam_relocation
    waist_side_x = cf_waist_x - waist_width
    if waist_side_x > 1.5:
        print(f"WARNING: front waist intake {waist_side_x:.1f} cm exceeds "
              f"1.5 cm — hip curve may be too pronounced. Reduce Ftw ease or "
              f"adjust pleat/sideseam relocation.")
    elif waist_side_x < 0:
        print(f"WARNING: front waist intake {waist_side_x:.1f} cm is negative "
              f"— waist wider than hip draft. Check Wbg/Hg ratio.")

    # ==========================================================
    # Step 5: Final curves
    # ==========================================================
    # Raise waistline 0.7 cm at sideseam
    waist_side_raised = np.array([waist_side_x, waist_y + 0.7])

    # Key outline points
    hem_side   = np.array([hem_side_x, hem_y])
    hem_inseam = np.array([hem_inseam_x, hem_y])
    hem_perp   = 4.0  # cm perpendicular at hem edge
    hem_side_top   = np.array([hem_side_x, hem_y + hem_perp])
    hem_inseam_top = np.array([hem_inseam_x, hem_y + hem_perp])
    knee_side  = np.array([knee_side_x, knee_y])
    knee_inseam = np.array([knee_inseam_x, knee_y])
    mid_side   = np.array([0.0, mid_hip_crotch_y])  # sideseam at x=0
    hip_side   = np.array([0.0, hip_y])              # sideseam at hipline
    cf_waist   = np.array([cf_waist_x, waist_y])
    cf_hip     = np.array([cf_hip_x, hip_y])

    # -- Waistline curve: waist_side_raised → cf_waist --
    # Slightly curved inward (dips below the straight line) from sideseam
    # to around the pleat, then levels out to CF.
    waist_span = cf_waist_x - waist_side_x
    waist_dip = 0.5  # cm inward (downward)
    curve_waistline = _bezier_cubic(
        waist_side_raised,
        waist_side_raised + np.array([waist_span / 3, -waist_dip]),
        cf_waist + np.array([-waist_span / 3, 0.0]),
        cf_waist,
    )

    # -- Sideseam upper: mid_side → knee_side (subtle shallow curve) --
    # Built before the hip curve so the hip curve can match its tangent at
    # mid_side.  P2 tangent matches the straight knee→hem segment for smooth
    # flow into the lower leg.
    side_span_y = mid_side[1] - knee_side[1]
    side_hollow = 0.15  # cm inward (toward creaseline = rightward)
    leg_dir = knee_side - hem_side_top
    leg_unit = leg_dir / np.linalg.norm(leg_dir)
    curve_side_upper = _bezier_cubic(
        mid_side,
        mid_side + np.array([side_hollow, -side_span_y / 3]),
        knee_side + leg_unit * (side_span_y / 3),         # arrives aligned with leg
        knee_side,
    )

    # -- Hip curve: mid_side → waist_side_raised --
    # MM&S step 5: "Draw the hip curve from the midpoint between crotch line
    # and hipline to the raised waistline."
    # Quadratic Bezier guarantees a pure C-curve (a parabolic arc cannot
    # inflect). Control point placed above the hipline, left of the chord,
    # so the curve bows outward and departs mid_side near-vertically —
    # matching side_upper's ~vertical tangent there within ~1°.
    hip_span_y = waist_side_raised[1] - mid_side[1]
    hip_bulge = max(0.25, waist_side_x * 0.3)
    curve_hip = _bezier_quad(
        mid_side,
        mid_side + np.array([-hip_bulge, hip_span_y * 0.55]),
        waist_side_raised,
    )

    # -- Crotch curve: cf_hip → crotch_pt --
    # Starts at CF on the hipline, sweeps as a shallow curve down to the
    # crotch point. P2 follows the slant direction (crotch_pt → crotch_guide)
    # so the curve stays above the guide line.
    crotch_span_y = cf_hip[1] - crotch_pt[1]
    slant_dir = crotch_guide - crotch_pt
    slant_len = np.linalg.norm(slant_dir)
    slant_unit = slant_dir / slant_len
    curve_crotch = _bezier_cubic(
        cf_hip,
        cf_hip + np.array([0.0, -crotch_span_y / 2]),
        crotch_pt + slant_unit * (slant_len / 2),
        crotch_pt,
    )

    # -- Inseam upper: crotch_pt → knee_inseam (gentle C-curve) --
    inseam_mid = (crotch_pt + knee_inseam) / 2
    curve_inseam_upper = _bezier_quad(
        crotch_pt,
        inseam_mid + np.array([-0.3, 0.0]),  # slight inward bow toward creaseline
        knee_inseam,
    )

    # -- Collect everything --
    points = {
        'A':                np.array([0.0, 0.0]),
        'hem_side':         hem_side,
        'hem_inseam':       hem_inseam,
        'hem_side_top':     hem_side_top,
        'hem_inseam_top':   hem_inseam_top,
        'hem_side_guide':   np.array([hem_side_guide_x, hem_y]),
        'hem_inseam_guide': np.array([hem_inseam_guide_x, hem_y]),
        'knee_side':        knee_side,
        'knee_inseam':      knee_inseam,
        'crotch_pt':        crotch_pt,
        'crotch_guide':     crotch_guide,
        'cf_at_crotch':     cf_at_crotch,   # construction only
        'cf_waist':         cf_waist,
        'cf_hip':           cf_hip,
        'mid_side':         mid_side,
        'hip_side':         hip_side,
        'waist_side':       np.array([waist_side_x, waist_y]),
        'waist_side_raised': waist_side_raised,
    }

    levels = {
        'hemline':     hem_y,
        'knee line':   knee_y,
        'crotch line': crotch_y,
        'hipline':     hip_y,
        'waistline':   waist_y,
    }

    construction = {
        'ftw_x':             ftw_x,
        'fcw_mark_x':        fcw_mark_x,
        'crotch_pt_x':       crotch_pt_x,
        'creaseline_x':      creaseline_x,
        'cf_hip_x':          cf_hip_x,
        'cf_waist_x':        cf_waist_x,
        'mid_hip_crotch_y':  mid_hip_crotch_y,
        'hem_half':          hem_half,
        'pleats':            pleats,
        'front_dart':        front_dart,
    }

    curves = {
        'waistline':     curve_waistline,
        'hip':           curve_hip,
        'crotch':        curve_crotch,
        'inseam_upper':  curve_inseam_upper,
        'side_upper':    curve_side_upper,
    }

    return {
        'points': points,
        'levels': levels,
        'construction': construction,
        'curves': curves,
        'measurements': {
            'Wbg': Wbg, 'Hg': Hg, 'Hw': Hw, 'Sl': Sl, 'Is': Is,
            'Br': Br, 'Kh': Kh, 'Ftw': Ftw, 'Fcw': Fcw,
            'Cw': Cw, 'Bcw': Bcw, 'Btw': Btw,
            'cf_hip_x': cf_hip_x, 'cf_waist_x': cf_waist_x,
            'waist_side_x': waist_side_x,
            'pleat_total_intake': pleat_total_intake,
        },
        'metadata': {'title': f'{PLEAT_NAMES[num_pleats]} Trouser Front (MM&S)'},
    }


# -- Visualization -----------------------------------------------------------

def plot_trouser_front(draft, output_path='Logs/trouser_front.svg',
                       debug=False, units='cm', step=5):
    """Render the trouser front draft up to the given step (1-5).

    debug=False (pattern mode): clean outline + grainline + pleat symbols only.
    debug=True: adds construction lines, reference lines, point labels, dimensions.
    """
    pts = draft['points']
    lvl = draft['levels']
    con = draft['construction']
    mm  = draft['measurements']
    crv = draft['curves']

    from garment_programs.plot_utils import draw_seam_allowance, setup_figure, finalize_figure
    fig, ax, standalone = setup_figure(figsize=(10, 16))
    plt.rcParams['lines.solid_capstyle'] = 'butt'
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
    CON = dict(color='cornflowerblue', linewidth=0.6, linestyle=':', alpha=0.5)
    x_max = con['fcw_mark_x'] + 5

    if debug:
        # ── Step 1: Framework ─────────────────────────────────────────
        # Horizontal reference lines
        for name, y in lvl.items():
            ax.plot([-2, x_max], [y, y], **REF)
            ax.annotate(name, (x_max, y), textcoords='offset points',
                        xytext=(4, 2), fontsize=7, color='gray')

        # Left vertical reference (A upward)
        ax.plot([0, 0], [-3, lvl['waistline'] + 5], 'k-', linewidth=0.8)

        # Dimension annotations (left side)
        for val, label, xoff in [(mm['Kh'], 'Kh', -5),
                                  (mm['Is'], 'Is', -7),
                                  (mm['Sl'], 'Sl', -9)]:
            ax.annotate('', xy=(-3, 0), xytext=(-3, val),
                        arrowprops=dict(arrowstyle='<->', color='dimgray', lw=0.7))
            ax.text(xoff, val / 2, f"{label}={val:.1f}", fontsize=6,
                    color='dimgray', ha='right', va='center', rotation=90)

        # Point A
        ax.plot(0, 0, 'ko', markersize=5)
        ax.annotate('A', (0, 0), textcoords='offset points',
                    xytext=(-8, -8), fontsize=9, fontweight='bold')

    if step < 2:
        _finish_plot(fig, ax, draft, output_path, step, debug, units=units)
        return

    if debug:
        # ── Step 2: Widths and creaseline ─────────────────────────────
        # Ftw perpendicular (crotch → waist)
        ax.plot([con['ftw_x'], con['ftw_x']],
                [lvl['crotch line'], lvl['waistline']],
                'k-', linewidth=0.6, alpha=0.5)

        # Crotch point
        ax.plot(*pts['crotch_pt'], 'ko', markersize=4)
        ax.annotate('crotch pt', pts['crotch_pt'], textcoords='offset points',
                    xytext=(4, -8), fontsize=6, color='black')

        # Mid hip/crotch mark
        ax.plot([-1, 3], [con['mid_hip_crotch_y']] * 2, **CON)
        ax.annotate('1/2', (-1, con['mid_hip_crotch_y']), textcoords='offset points',
                    xytext=(-8, 2), fontsize=6, color='cornflowerblue')

        # Ftw / Fcw dimension arrows
        ax.annotate('', xy=(0, lvl['hipline'] + 1),
                    xytext=(con['ftw_x'], lvl['hipline'] + 1),
                    arrowprops=dict(arrowstyle='<->', color='blue', lw=0.6))
        ax.text(con['ftw_x'] / 2, lvl['hipline'] + 2.5, f"Ftw={mm['Ftw']:.1f}",
                fontsize=6, color='blue', ha='center')

        ax.annotate('', xy=(con['ftw_x'], lvl['hipline'] + 1),
                    xytext=(con['fcw_mark_x'], lvl['hipline'] + 1),
                    arrowprops=dict(arrowstyle='<->', color='blue', lw=0.6))
        ax.text((con['ftw_x'] + con['fcw_mark_x']) / 2, lvl['hipline'] + 2.5,
                f"Fcw={mm['Fcw']:.1f}", fontsize=6, color='blue', ha='center')

    # Creaseline / grainline (always shown)
    ax.plot([con['creaseline_x'], con['creaseline_x']],
            [-3, lvl['waistline'] + 3],
            'k-.', linewidth=0.6, alpha=0.5)
    if debug:
        ax.annotate('front creaseline', (con['creaseline_x'], -3),
                    fontsize=7, color='black', ha='center', va='top')

    if step < 3:
        _finish_plot(fig, ax, draft, output_path, step, debug, units=units)
        return

    if debug:
        # ── Step 3: Hem widths, pleat, CF ─────────────────────────────
        # Hem width marks
        for pt_name in ('hem_side', 'hem_inseam'):
            p = pts[pt_name]
            ax.plot(p[0], p[1], 'k+', markersize=6)
        # Hem width dimension
        ax.annotate('', xy=(pts['hem_side'][0], -2),
                    xytext=(con['creaseline_x'], -2),
                    arrowprops=dict(arrowstyle='<->', color='green', lw=0.5))
        ax.text((pts['hem_side'][0] + con['creaseline_x']) / 2, -3.5,
                f"{con['hem_half']:.1f}", fontsize=6, color='green', ha='center')
        ax.annotate('', xy=(con['creaseline_x'], -2),
                    xytext=(pts['hem_inseam'][0], -2),
                    arrowprops=dict(arrowstyle='<->', color='green', lw=0.5))
        ax.text((con['creaseline_x'] + pts['hem_inseam'][0]) / 2, -3.5,
                f"{con['hem_half']:.1f}", fontsize=6, color='green', ha='center')

        # 0.5 cm guideline marks
        for pt_name in ('hem_side_guide', 'hem_inseam_guide'):
            p = pts[pt_name]
            ax.plot(p[0], p[1], 'x', color='gray', markersize=4)

    # Front dart (Trousers-with-Dart variant): two legs from the waistline
    # converging to the apex, plus a centre line.
    waist_crv = crv['waistline']
    dart = con['front_dart']
    if dart:
        dy_l = np.interp(dart['left'],  waist_crv[:, 0], waist_crv[:, 1])
        dy_r = np.interp(dart['right'], waist_crv[:, 0], waist_crv[:, 1])
        apex = dart['apex']
        ax.plot([dart['left'], apex[0], dart['right']],
                [dy_l, apex[1], dy_r], 'k-', linewidth=0.8)
        ax.plot([apex[0], apex[0]], [apex[1], max(dy_l, dy_r)],
                'k-', linewidth=0.5, alpha=0.5)
        if debug:
            ax.annotate(f"dart {dart['intake']:.1f}", apex,
                        textcoords='offset points', xytext=(4, -8),
                        fontsize=6, color='black')

    # Pleat symbols: loop over all pleats (empty for dart variant)
    chev_h = 1.5               # chevron height
    drop   = 6.0               # vertical lines extend below waist curve
    for pl, pr in con['pleats']:
        pm = (pr + pl) / 2     # midpoint
        # Interpolate raised waistline y at each pleat edge and midpoint
        py_l = np.interp(pl, waist_crv[:, 0], waist_crv[:, 1])
        py_r = np.interp(pr, waist_crv[:, 0], waist_crv[:, 1])
        py_m = np.interp(pm, waist_crv[:, 0], waist_crv[:, 1])
        # Vertical lines at pleat edges (from raised waistline down)
        ax.plot([pl, pl], [py_l, py_l - drop], 'k-', linewidth=0.6, alpha=0.6)
        ax.plot([pr, pr], [py_r, py_r - drop], 'k-', linewidth=0.6, alpha=0.6)
        # Upper chevron (pointing down from waistline)
        ax.plot([pl, pm, pr],
                [py_l - 0.5, py_m - 0.5 - chev_h, py_r - 0.5],
                'k-', linewidth=0.8)
        # Lower chevron
        ax.plot([pl, pm, pr],
                [py_l - 0.5 - chev_h, py_m - 0.5 - 2 * chev_h, py_r - 0.5 - chev_h],
                'k-', linewidth=0.8)

    if debug:
        # CF line (angled: hipline → waistline)
        ax.plot([con['cf_hip_x'], con['cf_waist_x']],
                [lvl['hipline'], lvl['waistline']],
                'k-', linewidth=0.8, alpha=0.6)
        ax.annotate('CF', (con['cf_waist_x'], lvl['waistline']),
                    textcoords='offset points', xytext=(4, 4),
                    fontsize=7, fontweight='bold', color='black')

        # Sideseam guideline: hem_side_guide angled to mid_side (halfway between hip & crotch)
        ax.plot([pts['hem_side_guide'][0], pts['mid_side'][0]],
                [pts['hem_side_guide'][1], pts['mid_side'][1]],
                'k-', linewidth=0.5, alpha=0.4)

        # Inseam guideline: hem_inseam_guide angled to Fcw mark on hipline
        ax.plot([pts['hem_inseam_guide'][0], con['fcw_mark_x']],
                [pts['hem_inseam_guide'][1], lvl['hipline']],
                'k-', linewidth=0.5, alpha=0.4)

    if step < 4:
        _finish_plot(fig, ax, draft, output_path, step, debug, units=units)
        return

    if debug:
        # ── Step 4: Shaping ───────────────────────────────────────────
        # Hem perpendiculars (~4 cm tall)
        for p in (pts['hem_side'], pts['hem_inseam']):
            ax.plot([p[0], p[0]], [p[1], p[1] + 4], **CON)

        # Knee points
        ax.plot(*pts['knee_side'], 'ko', markersize=3)
        ax.plot(*pts['knee_inseam'], 'ko', markersize=3)
        ax.annotate('knee (side)', pts['knee_side'], textcoords='offset points',
                    xytext=(-10, -8), fontsize=5, color='gray')
        ax.annotate('knee (inseam)', pts['knee_inseam'], textcoords='offset points',
                    xytext=(4, -8), fontsize=5, color='gray')

        # Crotch guide and slanted line
        ax.plot(*pts['crotch_guide'], 'o', color='cornflowerblue', markersize=4)
        ax.plot([pts['crotch_guide'][0], pts['crotch_pt'][0]],
                [pts['crotch_guide'][1], pts['crotch_pt'][1]], **CON)
        ax.annotate('crotch guide', pts['crotch_guide'], textcoords='offset points',
                    xytext=(-12, 6), fontsize=5, color='cornflowerblue')

        # Waist sideseam point (only show un-raised version in step 4)
        if step < 5:
            ax.plot(*pts['waist_side'], 'ko', markersize=4)
            ax.annotate(f"waist side ({mm['waist_side_x']:.1f})",
                        pts['waist_side'], textcoords='offset points',
                        xytext=(-8, 6), fontsize=5, color='black')

    if step < 5:
        _finish_plot(fig, ax, draft, output_path, step, debug, units=units)
        return

    # ── Step 5: Final curves and complete outline ─────────────────
    if debug:
        # Raised waist point
        ax.plot(*pts['waist_side_raised'], 'ko', markersize=4)

    # Waistline curve
    ax.plot(crv['waistline'][:, 0], crv['waistline'][:, 1],
            'k-', linewidth=1.5, zorder=4)

    # Hip curve (mid_side → raised waist, with intake)
    ax.plot(crv['hip'][:, 0], crv['hip'][:, 1],
            'k-', linewidth=1.5, zorder=4)

    # CF straight segment (waist → hipline)
    ax.plot([pts['cf_waist'][0], pts['cf_hip'][0]],
            [pts['cf_waist'][1], pts['cf_hip'][1]],
            'k-', linewidth=1.5, zorder=4)

    # Crotch curve (cf_top → crotch_pt)
    ax.plot(crv['crotch'][:, 0], crv['crotch'][:, 1],
            'k-', linewidth=1.5, zorder=4)

    # Inseam upper curve (crotch_pt → knee_inseam)
    ax.plot(crv['inseam_upper'][:, 0], crv['inseam_upper'][:, 1],
            'k-', linewidth=1.5, zorder=4)

    # Inseam lower: knee → hem_inseam_top (angled)
    ax.plot([pts['knee_inseam'][0], pts['hem_inseam_top'][0]],
            [pts['knee_inseam'][1], pts['hem_inseam_top'][1]],
            'k-', linewidth=1.5, zorder=4)

    # Hem perpendicular drops + hemline (one continuous polyline, butt caps)
    ax.plot([pts['hem_inseam_top'][0], pts['hem_inseam'][0],
             pts['hem_side'][0], pts['hem_side_top'][0]],
            [pts['hem_inseam_top'][1], pts['hem_inseam'][1],
             pts['hem_side'][1], pts['hem_side_top'][1]],
            'k-', linewidth=1.5, zorder=4, solid_capstyle='butt')

    # Sideseam: mid_side → knee (curve) → hem_side_top (angled)
    ax.plot(crv['side_upper'][:, 0], crv['side_upper'][:, 1],
            'k-', linewidth=1.5, zorder=4)
    ax.plot([pts['knee_side'][0], pts['hem_side_top'][0]],
            [pts['knee_side'][1], pts['hem_side_top'][1]],
            'k-', linewidth=1.5, zorder=4)

    # Seam allowances (CW outline order for outward offset)
    sa = SEAM_ALLOWANCES['front']
    sa_edges = [
        (crv['waistline'],                                        sa['waist']),
        (np.array([pts['cf_waist'], pts['cf_hip']]),              sa['cf']),
        (crv['crotch'],                                           sa['crotch']),
        (crv['inseam_upper'],                                     sa['inseam']),
        (np.array([pts['knee_inseam'], pts['hem_inseam_top']]),   sa['inseam']),
        # Hem: split so the vertical perpendicular drops carry the leg SA, not
        # the 4 cm turn-up. When the hem folds up, the allowance sides then
        # lie inside the tapered leg instead of sticking out as 4 cm ears.
        (np.array([pts['hem_inseam_top'], pts['hem_inseam']]),    sa['inseam']),
        (np.array([pts['hem_inseam'], pts['hem_side']]),          sa['hem']),
        (np.array([pts['hem_side'], pts['hem_side_top']]),        sa['side']),
        (np.array([pts['hem_side_top'], pts['knee_side']]),       sa['side']),
        (crv['side_upper'][::-1],                                 sa['side']),
        (crv['hip'],                                              sa['side']),
    ]
    cut_outline = draw_seam_allowance(ax, sa_edges, scale=1.0)

    # ── Debug: outline dimension annotations ──────────────────────
    if debug:
        _annotate_len(ax, crv['waistline'], offset=(0, 8))
        _annotate_len(ax, crv['hip'], offset=(-10, 0))
        _annotate_len(ax, crv['crotch'], offset=(6, 6))
        _annotate_len(ax, crv['inseam_upper'], offset=(8, 0))
        _annotate_len(ax, crv['side_upper'], offset=(-10, 0))
        _annotate_len(ax, np.array([pts['cf_waist'], pts['cf_hip']]), offset=(6, 0))
        _annotate_len(ax, np.array([pts['knee_inseam'], pts['hem_inseam_top']]), offset=(8, 0))
        _annotate_len(ax, np.array([pts['knee_side'], pts['hem_side_top']]), offset=(-10, 0))
        _annotate_len(ax, np.array([pts['hem_side'], pts['hem_inseam']]), offset=(0, -8))

    return _finish_plot(fig, ax, draft, output_path, step, debug, units=units,
                        outline_pts=cut_outline)


def _finish_plot(fig, ax, draft, output_path, step, debug=False, units='cm',
                 outline_pts=None):
    """Common plot finalization."""
    from garment_programs.plot_utils import finalize_figure
    return finalize_figure(ax, fig, True, output_path, units=units, debug=debug,
                           outline_pts=outline_pts)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', num_pleats=1):
    """Uniform interface called by the generic runner."""
    m = load_measurements(measurements_path)
    ease = load_ease(measurements_path)
    draft = draft_trouser_front(m, num_pleats=num_pleats, ease=ease)
    outline = plot_trouser_front(draft, output_path, debug=debug, units=units,
                                 step=5)
    if outline:
        return {'layout_outline': outline}
