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

from garment_programs.core.runtime import cache_draft, resolve_measurements
from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _bezier_cubic, _curve_length, _annotate_segment,
    _point_at_arclength,
    _curve_up_to_arclength,
)
from .seam_allowances import SEAM_ALLOWANCES, SEAM_LABELS
from garment_programs.plot_utils import (
    SEAMLINE, CUTLINE, offset_polyline, draw_seam_allowance, draw_notch,
    display_scale, setup_figure, finalize_figure, draw_fold_line,
)


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
            'title': 'Watch Pocket',
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
    pt1 = fpts["1'"]

    # -- Graduated ruler scaling (Devere's method) --
    # Base pocket dimensions are for a 38" hip.  Above that threshold,
    # scale proportionally so the opening stays in proportion to the body.
    BASE_HIP = 38.0 * INCH
    pocket_scale = max(1.0, m['seat'] / BASE_HIP)
    POCKET_LOWER_DIST = 3.25 * INCH * pocket_scale
    POCKET_UPPER_DIST = 4.75 * INCH * pocket_scale

    # -- 1. Lower pocket opening along the outseam from pt1' --
    outseam_path = np.vstack([pt1.reshape(1, 2), front['curves']['hip']])
    pocket_lower = _point_at_arclength(outseam_path, POCKET_LOWER_DIST)

    # -- 2. Upper pocket opening along the waist/rise from pt1' --
    rise_path = np.vstack([pt1.reshape(1, 2), front['curves']['rise']])
    pocket_upper = _point_at_arclength(rise_path, POCKET_UPPER_DIST)

    # -- 3. Pocket opening curve (traditional J-shape) --
    # Traditional pocket mouth: departs perpendicular to the waist (rise),
    # arrives tangent to the side seam (hip).  Control-point directions
    # are derived from the parent curves at the pocket endpoints.
    chord = pocket_lower - pocket_upper
    chord_len = np.linalg.norm(chord)

    # Tangent of rise at pocket_upper
    rise_sub = _curve_up_to_arclength(rise_path, POCKET_UPPER_DIST)
    rise_tan = rise_sub[-1] - rise_sub[-2]
    rise_tan = rise_tan / np.linalg.norm(rise_tan)

    # Tangent of hip at pocket_lower
    hip_sub = _curve_up_to_arclength(outseam_path, POCKET_LOWER_DIST)
    hip_tan = hip_sub[-1] - hip_sub[-2]
    hip_tan = hip_tan / np.linalg.norm(hip_tan)

    # Depart perpendicular to the rise, toward the side seam
    depart = np.array([-rise_tan[1], rise_tan[0]])
    if np.dot(depart, chord) < 0:
        depart = -depart

    # Arrive perpendicular to hip (from below) — right angle at side seam.
    # 90° CW rotation of hip_tan points downward, placing P2 below
    # pocket_lower so the curve arrives heading upward into the side seam.
    arrive = np.array([hip_tan[1], -hip_tan[0]])

    opening_curve = _bezier_cubic(
        pocket_upper,
        pocket_upper + depart * (chord_len * 0.50),
        pocket_lower + arrive * (chord_len * 0.45),
        pocket_lower,
    )

    # -- 4. Pocket bag outline --
    bag_depth = 10.0 * INCH

    # bag_inner_top: 1" further along the rise from pocket_upper → ON the outline
    bag_inner_top = _point_at_arclength(rise_path, POCKET_UPPER_DIST + 1.0 * INCH)

    # Inner edge perpendicular to the waist (for cut-on-fold)
    waist_dir = fpts["7'"] - fpts["1'"]
    perp = np.array([-waist_dir[1], waist_dir[0]])
    if perp[0] < 0:              # ensure it points toward the hem
        perp = -perp
    perp_norm = perp / np.linalg.norm(perp)
    bag_inner_bottom = bag_inner_top + perp_norm * bag_depth

    # Connection to side seam: ~2" below pocket opening along the outseam
    bag_sideseam = _point_at_arclength(outseam_path, POCKET_LOWER_DIST + 2.0 * INCH)

    # Bag bottom curve: S-curve from inner bottom back to the side seam
    chord = bag_sideseam - bag_inner_bottom
    chord_perp = np.array([-chord[1], chord[0]])
    chord_perp_norm = chord_perp / np.linalg.norm(chord_perp)
    if np.dot(chord_perp_norm, perp_norm) < 0:   # ensure outward = toward hem
        chord_perp_norm = -chord_perp_norm
    bag_bottom_curve = _bezier_cubic(
        bag_inner_bottom,
        bag_inner_bottom + chord * 0.50 + chord_perp_norm * (3.0 * INCH),
        bag_sideseam   - chord * 0.35 - chord_perp_norm * (1.5 * INCH),
        bag_sideseam,
    )

    # -- 5. Pocket facing --
    # The facing is a ~1/2" band inside the pocket opening, extending
    # ~1.5" below the opening along the side seam.
    facing_offset = 0.5 * INCH
    # Offset the opening inward. Travel is pocket_upper → pocket_lower;
    # negative offset = right of travel = toward body center (inward).
    facing_inner = offset_polyline(opening_curve, -facing_offset)

    # Facing extends ~1.5" below pocket_lower along the side seam.
    facing_sideseam = _point_at_arclength(outseam_path, (3.25 + 1.5) * INCH)

    # -- 6. 1873 Watch pocket --
    watch = _draft_watch_pocket(m, front, pocket_upper, pocket_lower, opening_curve)

    # -- 7. Bag extension curves (pt1 → bag edges) --
    # These define the bag outline above the pocket opening so the bag
    # extends all the way up to the waistband seam.
    rise_to_bag = _curve_up_to_arclength(rise_path, (4.75 + 1.0) * INCH)
    hip_to_bag = _curve_up_to_arclength(outseam_path, (3.25 + 2.0) * INCH)

    # -- 8. Mirror across inner edge (cut-on-fold) --
    def _reflect_across_line(pts, A, B):
        """Reflect points across the line through A and B."""
        d = (B - A)
        d = d / np.linalg.norm(d)
        diff = pts - A
        proj = A + np.outer(diff @ d, d)
        return 2 * proj - pts

    mirror_rise_to_bag = _reflect_across_line(rise_to_bag, bag_inner_top, bag_inner_bottom)
    mirror_hip_to_bag = _reflect_across_line(hip_to_bag, bag_inner_top, bag_inner_bottom)
    mirror_bag_bottom = _reflect_across_line(bag_bottom_curve, bag_inner_top, bag_inner_bottom)
    mirror_pt1 = _reflect_across_line(pt1.reshape(1, 2), bag_inner_top, bag_inner_bottom).ravel()
    mirror_bag_sideseam = _reflect_across_line(bag_sideseam.reshape(1, 2), bag_inner_top, bag_inner_bottom).ravel()

    return {
        'points': {
            'pt1': pt1,
            'pocket_upper': pocket_upper,
            'pocket_lower': pocket_lower,
            'bag_inner_top': bag_inner_top,
            'bag_inner_bottom': bag_inner_bottom,
            'bag_sideseam': bag_sideseam,
            'facing_sideseam': facing_sideseam,
            'mirror_pt1': mirror_pt1,
            'mirror_bag_sideseam': mirror_bag_sideseam,
        },
        'curves': {
            'opening': opening_curve,
            'bag_bottom': bag_bottom_curve,
            'facing_inner': facing_inner,
            'rise_to_bag': rise_to_bag,
            'hip_to_bag': hip_to_bag,
            'mirror_rise_to_bag': mirror_rise_to_bag,
            'mirror_hip_to_bag': mirror_hip_to_bag,
            'mirror_bag_bottom': mirror_bag_bottom,
        },
        'construction': {
            'pocket_lower_dist': POCKET_LOWER_DIST,
            'pocket_upper_dist': POCKET_UPPER_DIST,
        },
        'watch_pocket': watch,
        'metadata': {
            'title': 'Pocket Bag',
            'cut_count': 1,
            'fold': True,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_front_pocket(piece, output_path='Logs/jeans_front_pocket.svg',
                            debug=False, units='cm', pdf_pages=None, ax=None):
    """Plot the front pocket bag as a cut-on-fold butterfly pattern piece.

    The butterfly outline mirrors the bag across the inner edge (fold line).
    SA is drawn on all perimeter edges; the fold line is a dashed reference.
    """
    s, unit_label = display_scale(units)

    # --- Build butterfly outline from draft curves ---
    def _dedup(pts, tol=1e-10):
        """Remove consecutive near-duplicate points (avoids zero-length segs)."""
        keep = [0]
        for i in range(1, len(pts)):
            if np.linalg.norm(pts[i] - pts[keep[-1]]) > tol:
                keep.append(i)
        return pts[np.array(keep)]

    rise_to_bag = _dedup(piece['curves']['rise_to_bag'])
    hip_to_bag = _dedup(piece['curves']['hip_to_bag'])
    bag_bottom = piece['curves']['bag_bottom']
    mirror_rise = _dedup(piece['curves']['mirror_rise_to_bag'])
    mirror_hip = _dedup(piece['curves']['mirror_hip_to_bag'])
    mirror_bottom = piece['curves']['mirror_bag_bottom']
    bag_inner_top = piece['points']['bag_inner_top']
    bag_inner_bottom = piece['points']['bag_inner_bottom']
    opening = piece['curves']['opening']

    # Butterfly outline (CW): 6 edges
    #   rise → mirror_rise(rev) → mirror_hip → mirror_bottom(rev)
    #   → bottom → hip(rev)
    outline = np.vstack([
        rise_to_bag,              # pt1 → bag_inner_top
        mirror_rise[::-1],        # bag_inner_top → mirror_pt1
        mirror_hip,               # mirror_pt1 → mirror_bag_sideseam
        mirror_bottom[::-1],      # mirror_bag_sideseam → bag_inner_bottom
        bag_bottom,               # bag_inner_bottom → bag_sideseam
        hip_to_bag[::-1],         # bag_sideseam → pt1
    ])

    # --- Rotate so fold line is exactly vertical ---
    fold_vec = bag_inner_bottom - bag_inner_top
    fold_angle = np.arctan2(fold_vec[1], fold_vec[0])
    rot_angle = -np.pi / 2 - fold_angle          # map fold_vec → straight down
    cos_a, sin_a = np.cos(rot_angle), np.sin(rot_angle)

    def rotate(pts):
        return np.column_stack([
            pts[:, 0] * cos_a - pts[:, 1] * sin_a,
            pts[:, 0] * sin_a + pts[:, 1] * cos_a,
        ])

    def rotate_pt(pt):
        return np.array([
            pt[0] * cos_a - pt[1] * sin_a,
            pt[0] * sin_a + pt[1] * cos_a,
        ])

    rot_rise = rotate(rise_to_bag)
    rot_mirror_rise = rotate(mirror_rise)
    rot_mirror_hip = rotate(mirror_hip)
    rot_mirror_bottom = rotate(mirror_bottom)
    rot_bottom = rotate(bag_bottom)
    rot_hip = rotate(hip_to_bag)
    rot_opening = rotate(opening)
    rot_outline = rotate(outline)
    rot_fold_top = rotate_pt(bag_inner_top)
    rot_fold_bottom = rotate_pt(bag_inner_bottom)

    # --- Shift so bounding-box starts at origin ---
    xy_min = rot_outline.min(axis=0)

    def shift(c):
        return c - xy_min

    def shift_pt(pt):
        return pt - xy_min

    rot_rise = shift(rot_rise)
    rot_mirror_rise = shift(rot_mirror_rise)
    rot_mirror_hip = shift(rot_mirror_hip)
    rot_mirror_bottom = shift(rot_mirror_bottom)
    rot_bottom = shift(rot_bottom)
    rot_hip = shift(rot_hip)
    rot_opening = shift(rot_opening)
    rot_outline = shift(rot_outline)
    rot_fold_top = shift_pt(rot_fold_top)
    rot_fold_bottom = shift_pt(rot_fold_bottom)

    # --- Scale ---
    rot_rise *= s
    rot_mirror_rise *= s
    rot_mirror_hip *= s
    rot_mirror_bottom *= s
    rot_bottom *= s
    rot_hip *= s
    rot_opening *= s
    rot_outline *= s
    rot_fold_top = rot_fold_top * s
    rot_fold_bottom = rot_fold_bottom * s

    # --- Draw seamlines (6 edges) ---
    fig, ax, standalone = setup_figure(ax, figsize=(14, 14))
    ax.plot(rot_rise[:, 0], rot_rise[:, 1], **SEAMLINE)
    ax.plot(rot_mirror_rise[::-1, 0], rot_mirror_rise[::-1, 1], **SEAMLINE)
    ax.plot(rot_mirror_hip[:, 0], rot_mirror_hip[:, 1], **SEAMLINE)
    ax.plot(rot_mirror_bottom[::-1, 0], rot_mirror_bottom[::-1, 1], **SEAMLINE)
    ax.plot(rot_bottom[:, 0], rot_bottom[:, 1], **SEAMLINE)
    ax.plot(rot_hip[::-1, 0], rot_hip[::-1, 1], **SEAMLINE)

    # Fold line — dash-dot center reference
    draw_fold_line(ax, rot_fold_top, rot_fold_bottom)

    # Pocket opening — dashed reference line (shows where facing attaches)
    ax.plot(rot_opening[:, 0], rot_opening[:, 1],
            color='darkorange', linewidth=1.0, linestyle='--', alpha=0.7)

    # --- Seam allowances (all edges except fold, CW winding) ---
    _sa = SEAM_ALLOWANCES['front_pocket_bag']
    _sl = SEAM_LABELS['front_pocket_bag']
    sa_edges = [
        (rot_hip,                  _sa['sideseam'], _sl['sideseam']),
        (rot_bottom[::-1],         _sa['bottom'], _sl['bottom']),
        (rot_mirror_bottom,        _sa['bottom'], _sl['bottom']),
        (rot_mirror_hip[::-1],     _sa['sideseam'], _sl['sideseam']),
        (rot_mirror_rise,          _sa['waist'], _sl['waist']),
        (rot_rise[::-1],           _sa['waist'], _sl['waist']),
    ]
    draw_seam_allowance(ax, sa_edges, scale=s, label_sas=not debug, units=units)

    # --- Notches: matching marks for pocket assembly ---
    rot_pocket_upper = rot_opening[0]
    rot_pocket_lower = rot_opening[-1]
    NOTCH_OFFSET = 0.375 * INCH   # 3/8" away from pocket mouth
    draw_notch(ax, rot_rise, rot_pocket_upper, _sa['waist'], scale=s,
               tangent_offset=NOTCH_OFFSET, flip=True)
    draw_notch(ax, rot_hip, rot_pocket_lower, _sa['sideseam'], scale=s,
               tangent_offset=NOTCH_OFFSET)

    # --- Grainline (parallel to fold line, centered on piece) ---
    from garment_programs.plot_utils import draw_grainline, draw_piece_label
    bbox_max = rot_outline.max(axis=0)
    fold_dir = rot_fold_bottom - rot_fold_top
    fold_len = np.linalg.norm(fold_dir)
    fold_unit = fold_dir / fold_len
    center = bbox_max / 2
    grain_half = fold_len * 0.35
    grain_top = center - fold_unit * grain_half
    grain_bottom = center + fold_unit * grain_half
    draw_grainline(ax, grain_top, grain_bottom)

    # --- Piece label ---
    if not debug:
        center = (bbox_max[0] / 2, bbox_max[1] / 2)
        draw_piece_label(ax, center, piece['metadata']['title'],
                         piece['metadata'].get('cut_count'),
                         fold=piece['metadata'].get('fold', False),
                         metadata=piece.get('metadata'))

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug,
                    pdf_pages=pdf_pages)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None,
        context=None):
    m = resolve_measurements(context, measurements_path, load_measurements)
    front = cache_draft(context, 'selvedge.front', lambda: draft_jeans_front(m))
    pocket = cache_draft(
        context,
        'selvedge.front_pocket',
        lambda: draft_jeans_front_pocket(m, front),
    )
    plot_jeans_front_pocket(pocket, output_path, debug=debug, units=units,
                            pdf_pages=pdf_pages)
