"""Bridge between the pocket editor UI and the existing drafting pipeline.

Takes user-defined Bézier control points for the pocket opening curve and
generates all derived pocket pieces (bag, facing, watch pocket) using the
existing garment_programs code.
"""
import os
import tempfile

import numpy as np
import matplotlib
matplotlib.use('Agg')

from garment_programs.geometry import INCH, _bezier_cubic, _curve_up_to_arclength
from garment_programs.measurements import load_measurements
from garment_programs.SelvedgeJeans1873.jeans_front import draft_jeans_front
from garment_programs.SelvedgeJeans1873.jeans_front_pocket_bag import (
    draft_jeans_front_pocket,
    plot_jeans_front_pocket,
)
from garment_programs.SelvedgeJeans1873.jeans_watch_pocket import (
    plot_jeans_watch_pocket,
)
from garment_programs.SelvedgeJeans1873.jeans_front_facing import (
    plot_jeans_front_facing,
)
from garment_programs.SelvedgeJeans1873.seam_allowances import SEAM_ALLOWANCES, SEAM_LABELS
from garment_programs.core.pattern_metadata import (
    set_active_pattern_context,
    clear_active_pattern_context,
)


VALID_MEASUREMENTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'measurements',
)


def _validate_measurements_path(measurements_path):
    """Ensure the path is inside the measurements directory."""
    real = os.path.realpath(measurements_path)
    base = os.path.realpath(VALID_MEASUREMENTS_DIR)
    if not real.startswith(base + os.sep) and real != base:
        raise ValueError(f"Invalid measurements path: {measurements_path}")
    return real


def get_default_control_points(measurements_path):
    """Compute the default pocket opening J-curve control points.

    Returns the 4 cubic Bézier control points (P0, P1, P2, P3) that the
    existing drafting code would produce for the given measurements.
    """
    measurements_path = _validate_measurements_path(measurements_path)
    m = load_measurements(measurements_path)
    front = draft_jeans_front(m)
    pocket = draft_jeans_front_pocket(m, front)

    opening = pocket['curves']['opening']

    p0 = opening[0]
    p3 = opening[-1]

    fpts = front['points']
    pt1p = fpts["1'"]
    BASE_HIP = 38.0 * INCH
    pocket_scale = max(1.0, m['seat'] / BASE_HIP)
    POCKET_UPPER_DIST = 4.75 * INCH * pocket_scale
    POCKET_LOWER_DIST = 3.25 * INCH * pocket_scale

    rise_path = np.vstack([pt1p.reshape(1, 2), front['curves']['rise']])
    outseam_path = np.vstack([pt1p.reshape(1, 2), front['curves']['hip']])

    rise_sub = _curve_up_to_arclength(rise_path, POCKET_UPPER_DIST)
    rise_tan = rise_sub[-1] - rise_sub[-2]
    rise_tan = rise_tan / np.linalg.norm(rise_tan)

    hip_sub = _curve_up_to_arclength(outseam_path, POCKET_LOWER_DIST)
    hip_tan = hip_sub[-1] - hip_sub[-2]
    hip_tan = hip_tan / np.linalg.norm(hip_tan)

    chord = p3 - p0
    chord_len = np.linalg.norm(chord)

    depart = np.array([-rise_tan[1], rise_tan[0]])
    if np.dot(depart, chord) < 0:
        depart = -depart

    arrive = np.array([hip_tan[1], -hip_tan[0]])

    p1 = p0 + depart * (chord_len * 0.50)
    p2 = p3 + arrive * (chord_len * 0.45)

    def _downsample(curve, n=50):
        """Downsample a curve to n points for lighter JSON payload."""
        if len(curve) <= n:
            return curve.tolist()
        indices = np.linspace(0, len(curve) - 1, n, dtype=int)
        return curve[indices].tolist()

    front_panel = {
        'pt1': fpts["1'"].tolist(),
        'pt7': fpts["7'"].tolist(),
        'pt0': fpts["0'"].tolist(),
        'pt9': fpts["9"].tolist(),
        'pt10': fpts["10"].tolist(),
        'hip': _downsample(front['curves']['hip']),
        'rise': _downsample(front['curves']['rise']),
        'crotch': _downsample(front['curves']['crotch']),
        'inseam': _downsample(front['curves']['inseam']),
    }

    watch_outline = pocket['watch_pocket']['outline'].tolist()

    return {
        'control_points': [p0.tolist(), p1.tolist(), p2.tolist(), p3.tolist()],
        'pocket_upper': p0.tolist(),
        'pocket_lower': p3.tolist(),
        'front_panel': front_panel,
        'watch_pocket_outline': watch_outline,
    }


def _draft_facing_from_pocket(front, pocket):
    """Draft the front facing using pre-computed front and pocket data.

    This mirrors draft_jeans_front_facing() but accepts already-computed
    front/pocket so we can inject the custom opening curve.
    """
    pt1 = front['points']["1'"]
    pocket_upper = pocket['points']['pocket_upper']
    pocket_lower = pocket['points']['pocket_lower']
    opening = pocket['curves']['opening']

    rise_to_upper = _curve_up_to_arclength(
        front['curves']['rise'],
        pocket['construction']['pocket_upper_dist'],
    )
    rise_to_upper[-1] = pocket_upper

    hip_to_lower = _curve_up_to_arclength(
        front['curves']['hip'],
        pocket['construction']['pocket_lower_dist'],
    )
    hip_to_lower[-1] = pocket_lower

    outline = np.vstack([
        rise_to_upper,
        opening,
        hip_to_lower[::-1],
    ])

    rotated_outline = np.column_stack([outline[:, 1], -outline[:, 0]])
    rotated_rise = np.column_stack([rise_to_upper[:, 1], -rise_to_upper[:, 0]])
    rotated_opening = np.column_stack([opening[:, 1], -opening[:, 0]])
    rotated_hip = np.column_stack([hip_to_lower[::-1, 1], -hip_to_lower[::-1, 0]])

    def rotate_pt(pt):
        return np.array([pt[1], -pt[0]])

    new_pt1 = rotate_pt(pt1)
    new_pocket_upper = rotate_pt(pocket_upper)
    new_pocket_lower = rotate_pt(pocket_lower)

    watch_outline = pocket['watch_pocket']['outline']
    rotated_watch = np.column_stack([watch_outline[:, 1], -watch_outline[:, 0]])

    all_pts = rotated_outline
    xy_min = all_pts.min(axis=0)

    def shift(pt):
        return pt - xy_min

    def shift_curve(c):
        return c - xy_min

    new_pt1 = shift(new_pt1)
    new_pocket_upper = shift(new_pocket_upper)
    new_pocket_lower = shift(new_pocket_lower)
    rotated_rise = shift_curve(rotated_rise)
    rotated_opening = shift_curve(rotated_opening)
    rotated_hip = shift_curve(rotated_hip)
    rotated_watch = shift_curve(rotated_watch)

    _sa = SEAM_ALLOWANCES['front_facing']
    _sl = SEAM_LABELS['front_facing']

    bbox_max = shift_curve(all_pts).max(axis=0)
    cx = bbox_max[0] / 2
    grain_top = np.array([cx, bbox_max[1] * 0.85])
    grain_bottom = np.array([cx, bbox_max[1] * 0.15])

    return {
        'points': {
            'pt1': new_pt1,
            'pocket_upper': new_pocket_upper,
            'pocket_lower': new_pocket_lower,
            'grain_top': grain_top,
            'grain_bottom': grain_bottom,
        },
        'curves': {
            'rise': rotated_rise,
            'opening': rotated_opening,
            'hip': rotated_hip,
            'watch_pocket': rotated_watch,
        },
        'construction': {},
        'metadata': {
            'title': 'Facing',
            'cut_count': 2,
            'sa_waist': _sa['waist'],
            'sa_sideseam': _sa['sideseam'],
            'sa_opening': _sa['opening'],
        },
    }


def _draft_watch_pocket_from_pocket(pocket):
    """Draft the watch pocket using pre-computed pocket data.

    Mirrors draft_jeans_watch_pocket() but uses the pocket data directly.
    """
    watch = pocket['watch_pocket']
    outline = watch['outline']
    wpts = watch['points']

    tl = wpts['top_left']
    tr = wpts['top_right']

    top_edge = tr - tl
    angle = -np.arctan2(top_edge[1], top_edge[0])
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    rot = np.array([[cos_a, -sin_a],
                    [sin_a, cos_a]])

    def transform(pt):
        return rot @ (pt - tl)

    new_pts = {k: transform(v) for k, v in wpts.items()}
    new_outline = np.array([transform(p) for p in outline])

    for k in new_pts:
        new_pts[k] = np.array([new_pts[k][0], -new_pts[k][1]])
    new_outline[:, 1] = -new_outline[:, 1]

    all_pts_arr = np.array(list(new_pts.values()))
    xy_min = all_pts_arr.min(axis=0)
    for k in new_pts:
        new_pts[k] = new_pts[k] - xy_min
    new_outline -= xy_min

    sa_top = watch['metadata']['sa_top']
    sa_sides = watch['metadata']['sa_sides']
    sa_bottom = watch['metadata']['sa_bottom']

    width = np.linalg.norm(tr - tl)
    height = np.linalg.norm(wpts['v_point'] - (tl + tr) / 2)

    cx = new_pts['top_center'][0]
    grain_top = np.array([cx, new_pts['top_center'][1] * 0.85 + new_pts['v_point'][1] * 0.15])
    grain_bottom = np.array([cx, new_pts['top_center'][1] * 0.20 + new_pts['v_point'][1] * 0.80])

    return {
        'points': {
            **new_pts,
            'grain_top': grain_top,
            'grain_bottom': grain_bottom,
        },
        'curves': {},
        'construction': {},
        'outline': new_outline,
        'metadata': {
            'title': 'Watch Pocket',
            'cut_count': 1,
            'width': width,
            'height': height,
            'sa_top': sa_top,
            'sa_sides': sa_sides,
            'sa_bottom': sa_bottom,
        },
    }


def generate_pieces(control_points, measurements_path, units='cm'):
    """Generate pocket pieces from custom Bézier control points.

    Parameters
    ----------
    control_points : list of [x, y]
        Four control points [P0, P1, P2, P3] for the cubic Bézier opening curve.
    measurements_path : str
        Path to measurements YAML file.
    units : str
        Display units ('cm' or 'inch').

    Returns
    -------
    dict with SVG strings for each piece.
    """
    measurements_path = _validate_measurements_path(measurements_path)
    m = load_measurements(measurements_path)
    front = draft_jeans_front(m)

    for cp in control_points:
        if not isinstance(cp, (list, tuple)) or len(cp) != 2:
            raise ValueError("Each control point must be [x, y]")
        if not all(isinstance(v, (int, float)) for v in cp):
            raise ValueError("Control point coordinates must be numeric")

    pts = [np.array(p, dtype=float) for p in control_points]
    custom_opening = _bezier_cubic(pts[0], pts[1], pts[2], pts[3])

    pocket = draft_jeans_front_pocket(m, front)
    pocket['curves']['opening'] = custom_opening
    pocket['points']['pocket_upper'] = pts[0]
    pocket['points']['pocket_lower'] = pts[3]

    results = {}

    bag_svg = _render_piece_svg(
        plot_jeans_front_pocket, pocket, units
    )
    results['pocket_bag'] = bag_svg

    try:
        facing = _draft_facing_from_pocket(front, pocket)
        facing_svg = _render_piece_svg(
            plot_jeans_front_facing, facing, units
        )
        results['facing'] = facing_svg
    except Exception as e:
        results['facing_error'] = str(e)

    try:
        watch = _draft_watch_pocket_from_pocket(pocket)
        watch_svg = _render_piece_svg(
            plot_jeans_watch_pocket, watch, units
        )
        results['watch_pocket'] = watch_svg
    except Exception as e:
        results['watch_pocket_error'] = str(e)

    return results


def _render_piece_svg(plot_fn, piece, units='cm'):
    """Render a piece to SVG string via a temp file."""
    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as f:
        tmp_path = f.name

    set_active_pattern_context({})
    try:
        plot_fn(piece, output_path=tmp_path, units=units)
        with open(tmp_path, 'r') as f:
            svg = f.read()
        return svg
    finally:
        clear_active_pattern_context()
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
