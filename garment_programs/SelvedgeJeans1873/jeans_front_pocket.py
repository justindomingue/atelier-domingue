"""
Front Pocket (opening, bag, and facing)
Based on: Historical Tailoring Masterclasses - Drafting the Pockets and Accessories

Drafted on the front leg pattern:
1. Mark 3 1/4" from the outseam waist corner along the side seam
   → lower pocket opening point.
2. Mark 4 3/4" along the waist from the same corner
   → upper pocket opening point.
3. Connect with a smooth curve → pocket opening.
4. Add 3/8" SA to the opening.
5. Pocket bag: ~1" from opening, 10"–12" long, angled slightly upward
   toward the side seam, ending ~1 1/2" from the side seam.
6. Connect bag bottom to side seam ~2" below opening with a curve.
7. Pocket facing: ~1/2" inside the opening, depth 1"–2" below opening.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _bezier_cubic, _curve_length, _annotate_segment,
    _point_at_arclength, _offset_polyline,
    _curve_up_to_arclength, _draw_seam_allowance,
)
from .seam_allowances import SEAM_ALLOWANCES
from garment_programs.plot_utils import SEAMLINE, CUTLINE


# -- Watch pocket helper -----------------------------------------------------

def _draft_watch_pocket(m, front, pocket_upper, pocket_lower, opening_curve):
    """Draft the 1873 watch pocket (pentagon/shield shape).

    Dimensions from the source:
    - Top width: 3 1/2" (1 3/4" each side of center)
    - Height: 4" straight section
    - Bottom width: 3" (1 1/2" each side of center)
    - Below 4": tapers to center point at 4 1/2" total height
    - Shape: straight top, straight sides, V-bottom

    Positioning (from the pattern book):
    - About 1"–1 1/2" below the top edge (waist seamline)
    - About 1 1/2" from the side seam
    - Following the angle of the waist seam
    """
    fpts = front['points']

    # -- Positioning --
    # The waist seam runs from pt1' to pt7'.  Use its direction to orient
    # the watch pocket so it follows the waist angle.
    pt1p = fpts["1'"]
    pt7p = fpts["7'"]
    waist_dir = pt7p - pt1p
    waist_dir_norm = waist_dir / np.linalg.norm(waist_dir)
    # "Down" from waist = perpendicular, toward the hem (+x direction).
    down = np.array([-waist_dir_norm[1], waist_dir_norm[0]])
    # Make sure "down" points toward the hem (positive x)
    if down[0] < 0:
        down = -down

    # Top-center of the watch pocket:
    #   - 1 1/4" below the waist (midpoint of 1"–1 1/2" range)
    #   - 1 1/2" from the side seam to the nearest edge
    # pt1' is the outseam-waist corner.  Move along the waist toward
    # the fly by (1 1/2" + half-width) so the nearest edge clears the
    # side seam, then step down 1 1/4" perpendicular.
    hw_top = 1.75 * INCH      # half-width at top
    top_center = (pt1p
                  + waist_dir_norm * ((1.5 + 1.75) * INCH)
                  + down * (1.25 * INCH))

    # -- Shield geometry (relative to top_center, oriented along waist) --
    hw_bot = 1.5 * INCH       # half-width at 4" height
    h_straight = 4.0 * INCH   # height of straight section
    h_total = 4.5 * INCH      # total height to V-point

    # "across" follows the waist seam direction (waist_dir_norm)
    # "down" is perpendicular, toward the hem
    pts = np.array([
        top_center - waist_dir_norm * hw_top,                              # top-left
        top_center + waist_dir_norm * hw_top,                              # top-right
        top_center + waist_dir_norm * hw_bot + down * h_straight,          # bottom-right
        top_center + down * h_total,                                       # V-point
        top_center - waist_dir_norm * hw_bot + down * h_straight,          # bottom-left
    ])

    return {
        'points': {
            'top_center': top_center,
            'top_left': pts[0],
            'top_right': pts[1],
            'bottom_right': pts[2],
            'v_point': pts[3],
            'bottom_left': pts[4],
        },
        'outline': pts,
        'metadata': {
            'title': '1873 Watch Pocket',
            'sa_top': SEAM_ALLOWANCES['watch_pocket']['top'],
            'sa_sides': SEAM_ALLOWANCES['watch_pocket']['sides'],
            'sa_bottom': SEAM_ALLOWANCES['watch_pocket']['bottom'],
        },
    }


# -- Drafting ----------------------------------------------------------------

def draft_jeans_front_pocket(m, front):
    """Draft the front pocket opening, bag, and facing.

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
    fpts = front['points']
    pt1 = fpts['1']

    # -- 1. Lower pocket opening: 3 1/4" along the outseam from pt1 --
    # The outseam runs: pt1 → 1' → hip curve → pt4.
    # Build a combined polyline and walk it by arc-length.
    outseam_path = np.vstack([pt1.reshape(1, 2), front['curves']['hip']])
    pocket_lower = _point_at_arclength(outseam_path, 3.25 * INCH)

    # -- 2. Upper pocket opening: 4 3/4" along the waist/rise from pt1 --
    # The waist/fly edge runs: pt1 → 1' → rise curve → 7'.
    rise_path = np.vstack([pt1.reshape(1, 2), front['curves']['rise']])
    pocket_upper = _point_at_arclength(rise_path, 4.75 * INCH)

    # -- 3. Pocket opening curve --
    chord = pocket_lower - pocket_upper
    chord_len = np.linalg.norm(chord)
    perp = np.array([chord[1], -chord[0]])
    perp_norm = perp / np.linalg.norm(perp)
    bow = chord_len * 0.15
    opening_curve = _bezier_cubic(
        pocket_upper,
        pocket_upper + (chord / 3) + perp_norm * bow,
        pocket_lower - (chord / 3) + perp_norm * bow,
        pocket_lower,
    )

    # -- 4. Pocket bag outline --
    bag_depth = 10.0 * INCH

    # bag_inner_top: 1" further along the rise from pocket_upper → ON the outline
    bag_inner_top = _point_at_arclength(rise_path, (4.75 + 1.0) * INCH)

    # Bag extends toward the hem, roughly parallel to the fly line
    fly_start = front['construction']['fly_start']
    fly_end = front['construction']['fly_end']
    fly_dir = fly_end - fly_start
    fly_dir_norm = fly_dir / np.linalg.norm(fly_dir)
    bag_inner_bottom = bag_inner_top + fly_dir_norm * bag_depth

    # Connection to side seam: ~2" below pocket opening along the outseam
    bag_sideseam = _point_at_arclength(outseam_path, (3.25 + 2.0) * INCH)

    # Bag bottom curve: from inner bottom, angling back to the side seam
    bag_bottom_curve = _bezier_cubic(
        bag_inner_bottom,
        bag_inner_bottom + np.array([0, bag_depth * 0.08]),
        bag_sideseam + fly_dir_norm * (1.5 * INCH),
        bag_sideseam,
    )

    # -- 5. Pocket facing --
    # The facing is a ~1/2" band inside the pocket opening, extending
    # ~1.5" below the opening along the side seam.
    facing_offset = 0.5 * INCH
    # Offset the opening inward. Travel is pocket_upper → pocket_lower;
    # negative offset = right of travel = toward body center (inward).
    facing_inner = _offset_polyline(opening_curve, -facing_offset)

    # Facing extends ~1.5" below pocket_lower along the side seam.
    facing_sideseam = _point_at_arclength(outseam_path, (3.25 + 1.5) * INCH)

    # -- 6. 1873 Watch pocket --
    watch = _draft_watch_pocket(m, front, pocket_upper, pocket_lower, opening_curve)

    # -- 7. Bag extension curves (pt1 → bag edges) --
    # These define the bag outline above the pocket opening so the bag
    # extends all the way up to the waistband seam.
    rise_to_bag = _curve_up_to_arclength(rise_path, (4.75 + 1.0) * INCH)
    hip_to_bag = _curve_up_to_arclength(outseam_path, (3.25 + 2.0) * INCH)

    return {
        'points': {
            'pt1': pt1,
            'pocket_upper': pocket_upper,
            'pocket_lower': pocket_lower,
            'bag_inner_top': bag_inner_top,
            'bag_inner_bottom': bag_inner_bottom,
            'bag_sideseam': bag_sideseam,
            'facing_sideseam': facing_sideseam,
        },
        'curves': {
            'opening': opening_curve,
            'bag_bottom': bag_bottom_curve,
            'facing_inner': facing_inner,
            'rise_to_bag': rise_to_bag,
            'hip_to_bag': hip_to_bag,
        },
        'construction': {},
        'watch_pocket': watch,
        'metadata': {
            'title': 'Front Pocket Bag',
            'cut_count': 2,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_front_pocket(piece, output_path='Logs/jeans_front_pocket.svg',
                            debug=False, units='cm', pdf_pages=None, ax=None):
    """Plot the front pocket bag as a standalone pattern piece.

    The bag extends from the waistband seam (pt1) down to the bag bottom,
    with the pocket opening shown as a dashed reference line.
    """
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    # --- Build closed outline from draft curves ---
    rise_to_bag = piece['curves']['rise_to_bag']
    hip_to_bag = piece['curves']['hip_to_bag']
    bag_bottom = piece['curves']['bag_bottom']
    bag_inner_top = piece['points']['bag_inner_top']
    bag_inner_bottom = piece['points']['bag_inner_bottom']
    opening = piece['curves']['opening']

    # Inner edge: straight line from bag_inner_top → bag_inner_bottom
    inner_edge = np.vstack([bag_inner_top.reshape(1, 2),
                            bag_inner_bottom.reshape(1, 2)])

    # Outline: rise (pt1 → bag_inner_top) → inner → bottom → hip reversed
    outline = np.vstack([
        rise_to_bag,
        inner_edge,
        bag_bottom,
        hip_to_bag[::-1],
    ])

    # --- Rotate 90° CW: (x, y) → (y, -x) ---
    def rotate(pts):
        return np.column_stack([pts[:, 1], -pts[:, 0]])

    def rotate_pt(pt):
        return np.array([pt[1], -pt[0]])

    rot_rise = rotate(rise_to_bag)
    rot_inner = rotate(inner_edge)
    rot_bottom = rotate(bag_bottom)
    rot_hip = rotate(hip_to_bag[::-1])
    rot_opening = rotate(opening)
    rot_outline = rotate(outline)

    # --- Shift so bounding-box starts at origin ---
    xy_min = rot_outline.min(axis=0)

    def shift(c):
        return c - xy_min

    rot_rise = shift(rot_rise)
    rot_inner = shift(rot_inner)
    rot_bottom = shift(rot_bottom)
    rot_hip = shift(rot_hip)
    rot_opening = shift(rot_opening)
    rot_outline = shift(rot_outline)

    # --- Scale ---
    rot_rise *= s
    rot_inner *= s
    rot_bottom *= s
    rot_hip *= s
    rot_opening *= s
    rot_outline *= s

    # --- Draw ---
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(1, 1, figsize=(10, 14))
    ax.plot(rot_rise[:, 0], rot_rise[:, 1], **SEAMLINE)
    ax.plot(rot_inner[:, 0], rot_inner[:, 1], **SEAMLINE)
    ax.plot(rot_bottom[:, 0], rot_bottom[:, 1], **SEAMLINE)
    ax.plot(rot_hip[:, 0], rot_hip[:, 1], **SEAMLINE)

    # Pocket opening — dashed reference line (shows where facing attaches)
    ax.plot(rot_opening[:, 0], rot_opening[:, 1],
            color='darkorange', linewidth=1.0, linestyle='--', alpha=0.7)

    # --- Seam allowances ---
    _sa = SEAM_ALLOWANCES['front_pocket_bag']
    sa_edges = [
        (rot_rise,   -_sa['waist']),
        (rot_inner,  -_sa['inner']),
        (rot_bottom, -_sa['bottom']),
        (rot_hip,    -_sa['sideseam']),
    ]
    _draw_seam_allowance(ax, sa_edges, scale=s)

    # --- Grainline (vertical, centered) ---
    from garment_programs.plot_utils import draw_grainline, draw_piece_label
    bbox_max = rot_outline.max(axis=0)
    cx = bbox_max[0] / 2
    grain_top = np.array([cx, bbox_max[1] * 0.85])
    grain_bottom = np.array([cx, bbox_max[1] * 0.15])
    draw_grainline(ax, grain_top, grain_bottom)

    # --- Piece label ---
    if not debug:
        center = (bbox_max[0] / 2, bbox_max[1] / 2)
        draw_piece_label(ax, center, piece['metadata']['title'],
                         piece['metadata'].get('cut_count'))

    if debug:
        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)
    else:
        ax.axis('off')

    if standalone:
        from garment_programs.plot_utils import save_pattern
        save_pattern(fig, ax, output_path, units=units, calibration=not debug,
                     pdf_pages=pdf_pages)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None):
    m = load_measurements(measurements_path)
    front = draft_jeans_front(m)
    pocket = draft_jeans_front_pocket(m, front)
    plot_jeans_front_pocket(pocket, output_path, debug=debug, units=units,
                            pdf_pages=pdf_pages)
