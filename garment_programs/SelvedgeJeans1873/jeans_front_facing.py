"""
Front Pocket Facing — Standalone Pattern Piece
Based on: Historical Tailoring Masterclasses - Drafting the Pockets and Accessories

Extracted from the front panel draft as its own printable cut piece.

The facing is the cutoff piece from the front panel between the waist,
side seam, and pocket opening.  It is the visible band of fabric that
shows when the pocket is open.

Shape:
  - Waist edge: rise curve from pt1 to pocket_upper
  - Pocket opening curve from pocket_upper to pocket_lower
  - Side seam: hip curve from pocket_lower back to pt1

Seam allowances:
  Waist (rise):       3/8"
  Side seam (hip):    3/4"
  Pocket opening:     3/8"

Grain line: vertical (parallel to side seam).
"""
import numpy as np
import matplotlib.pyplot as plt

from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _offset_polyline, _draw_seam_allowance,
    _annotate_segment, _annotate_curve, _curve_length,
    _curve_up_to_arclength,
)
from .jeans_front_pocket import draft_jeans_front_pocket


# -- Drafting ----------------------------------------------------------------

def draft_jeans_front_facing(m):
    """Draft the front pocket facing as a standalone piece.

    The facing is the portion of the front panel between the waist corner
    (pt1), the rise/waist edge, the pocket opening, and the side seam.

    Parameters
    ----------
    m : dict
        Measurements in cm (output of load_measurements).

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    front = draft_jeans_front(m)
    pocket = draft_jeans_front_pocket(m, front)

    pt1 = front['points']['1']
    pocket_upper = pocket['points']['pocket_upper']
    pocket_lower = pocket['points']['pocket_lower']
    opening = pocket['curves']['opening']  # pocket_upper → pocket_lower

    # Sub-curves from pt1 to the pocket endpoints
    # Rise: pt1 → pocket_upper (4.75" along the rise)
    rise_path = np.vstack([pt1.reshape(1, 2), front['curves']['rise']])
    rise_to_upper = _curve_up_to_arclength(rise_path, 4.75 * INCH)

    # Hip: pt1 → pocket_lower (3.25" along the outseam/hip)
    outseam_path = np.vstack([pt1.reshape(1, 2), front['curves']['hip']])
    hip_to_lower = _curve_up_to_arclength(outseam_path, 3.25 * INCH)

    # Closed outline (CW for correct SA offset):
    #   rise (pt1 → pocket_upper) → opening (pocket_upper → pocket_lower)
    #   → hip reversed (pocket_lower → pt1)
    # Combine into one polyline for the outline
    outline = np.vstack([
        rise_to_upper,
        opening,
        hip_to_lower[::-1],
    ])

    # --- Re-origin and rotate 90° CW ---
    # Rotate 90° clockwise: (x, y) → (y, -x)
    rotated_outline = np.column_stack([outline[:, 1], -outline[:, 0]])
    rotated_rise = np.column_stack([rise_to_upper[:, 1], -rise_to_upper[:, 0]])
    rotated_opening = np.column_stack([opening[:, 1], -opening[:, 0]])
    rotated_hip = np.column_stack([hip_to_lower[::-1, 1], -hip_to_lower[::-1, 0]])

    def rotate_pt(pt):
        return np.array([pt[1], -pt[0]])

    new_pt1 = rotate_pt(pt1)
    new_pocket_upper = rotate_pt(pocket_upper)
    new_pocket_lower = rotate_pt(pocket_lower)

    # Shift so bounding box starts at (0, 0)
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

    # SA values
    sa_waist = 3 / 8 * INCH     # rise / waist edge
    sa_sideseam = 3 / 4 * INCH  # side seam (hip edge)
    sa_opening = 3 / 8 * INCH   # pocket opening (cut edge)

    # Grain line (vertical, centered in the piece)
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
        },
        'construction': {},
        'metadata': {
            'title': 'Front Pocket Facing',
            'sa_waist': sa_waist,
            'sa_sideseam': sa_sideseam,
            'sa_opening': sa_opening,
        },
    }


# -- Visualization -----------------------------------------------------------

def plot_jeans_front_facing(piece, output_path='Logs/jeans_front_facing.svg',
                            debug=False, units='cm'):
    s = 1 / INCH if units == 'inch' else 1.0
    unit_label = 'in' if units == 'inch' else 'cm'

    pts = {k: v * s for k, v in piece['points'].items()}
    curves = {k: v * s for k, v in piece['curves'].items()}
    meta = piece['metadata']

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    OUTLINE = dict(color='black', linewidth=1.5)

    # Finished outline: rise → opening → hip (all continuous)
    rise = curves['rise']
    opening = curves['opening']
    hip = curves['hip']

    ax.plot(rise[:, 0], rise[:, 1], **OUTLINE)
    ax.plot(opening[:, 0], opening[:, 1], **OUTLINE)
    ax.plot(hip[:, 0], hip[:, 1], **OUTLINE)

    # Seam allowances
    # Edges travel CW (after 90° rotation):
    #   rise (pt1 → pocket_upper), opening (pocket_upper → pocket_lower),
    #   hip reversed (pocket_lower → pt1)
    sa_waist = meta['sa_waist']
    sa_sideseam = meta['sa_sideseam']
    sa_opening = meta['sa_opening']

    # Outline winds CCW after 90° rotation, so negate SA to push outward
    sa_edges = [
        (rise,    -sa_waist),      # waist / rise edge
        (opening, -sa_opening),    # pocket opening (cut edge)
        (hip,     -sa_sideseam),   # side seam
    ]
    _draw_seam_allowance(ax, sa_edges, scale=s)

    # Grain line arrow
    ax.annotate('', xy=pts['grain_top'], xytext=pts['grain_bottom'],
                arrowprops=dict(arrowstyle='->', color='gray', lw=0.8))
    ax.annotate('grain', (pts['grain_top'][0], pts['grain_top'][1]),
                textcoords="offset points", xytext=(8, 0),
                fontsize=7, color='gray')

    if debug:
        for name, pt in pts.items():
            if name.startswith('grain'):
                continue
            ax.plot(pt[0], pt[1], 'o', color='darkorange', markersize=4, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6, color='darkorange')

        _annotate_curve(ax, curves['rise'], offset=(0, -8))
        _annotate_curve(ax, curves['opening'], offset=(8, 0))
        _annotate_curve(ax, curves['hip'], offset=(0, 8))

        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)
    else:
        ax.axis('off')

    from garment_programs.plot_utils import save_pattern
    save_pattern(fig, ax, output_path, units=units, calibration=not debug)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm'):
    m = load_measurements(measurements_path)
    piece = draft_jeans_front_facing(m)
    plot_jeans_front_facing(piece, output_path, debug=debug, units=units)
