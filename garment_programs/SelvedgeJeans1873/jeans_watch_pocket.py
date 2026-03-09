"""
Watch Pocket (1873) — Standalone Pattern Piece
Based on: Historical Tailoring Masterclasses - Drafting the Pockets and Accessories

Extracted from the front pocket draft as its own printable cut piece.

Shape: pentagon / shield — straight top, straight sides, V-bottom.
  Top width:    3 1/2" (1 3/4" each side of center)
  Straight:     4" downward
  Bottom width: 3" (1 1/2" each side) at 4"
  V-point:      4 1/2" total height

Seam allowances:
  Top:              7/8" (double fold for waistband)
  Sides and bottom: 3/8"

Grain line: centerline (vertical).
"""
import numpy as np
import matplotlib.pyplot as plt

from garment_programs.core.runtime import cache_draft, resolve_measurements
from .jeans_front import (
    INCH, load_measurements, draft_jeans_front,
    _annotate_segment,
)
from .jeans_front_pocket_bag import draft_jeans_front_pocket
from garment_programs.plot_utils import (
    SEAMLINE, CUTLINE, draw_seam_allowance, display_scale, setup_figure, finalize_figure,
)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_watch_pocket(m):
    """Draft the watch pocket as a standalone piece.

    Extracts the pentagon geometry from the front pocket draft and re-origins
    it to (0, 0) so the top-left corner sits at the origin.

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
    watch = pocket['watch_pocket']

    outline = watch['outline']  # 5-point pentagon (Nx2)
    wpts = watch['points']

    # Re-origin: shift so top-left is at (0, 0).
    # The outline is oriented along the waist angle.  For a standalone piece
    # we rotate it upright (top edge horizontal) and place top-left at origin.
    tl = wpts['top_left']
    tr = wpts['top_right']

    # Rotation: make top edge horizontal (left to right = +x direction)
    top_edge = tr - tl
    angle = -np.arctan2(top_edge[1], top_edge[0])
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    rot = np.array([[cos_a, -sin_a],
                    [sin_a,  cos_a]])

    # Rotate all points around top-left, then shift so top-left = (0, 0)
    def transform(pt):
        return rot @ (pt - tl)

    new_pts = {k: transform(v) for k, v in wpts.items()}
    new_outline = np.array([transform(p) for p in outline])

    # After rotation the pocket hangs in +y (v_point at large y, top edge
    # near y=0).  Negate y so the flat top edge sits at the TOP of the
    # figure and v_point at the bottom.  This also flips the winding from
    # CCW to CW, which makes draw_seam_allowance offset outward with
    # positive SA values.
    for k in new_pts:
        new_pts[k] = np.array([new_pts[k][0], -new_pts[k][1]])
    new_outline[:, 1] = -new_outline[:, 1]

    # Shift so bounding box starts at (0, 0)
    all_pts_arr = np.array(list(new_pts.values()))
    xy_min = all_pts_arr.min(axis=0)
    for k in new_pts:
        new_pts[k] = new_pts[k] - xy_min
    new_outline -= xy_min

    sa_top = watch['metadata']['sa_top']
    sa_sides = watch['metadata']['sa_sides']
    sa_bottom = watch['metadata']['sa_bottom']

    # Compute dimensions for metadata
    width = np.linalg.norm(tr - tl)
    height = np.linalg.norm(wpts['v_point'] - (tl + tr) / 2)

    # Grain line (vertical center)
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


# -- Visualization -----------------------------------------------------------

def plot_jeans_watch_pocket(piece, output_path='Logs/jeans_watch_pocket.svg',
                            debug=False, units='cm', pdf_pages=None, ax=None):
    s, unit_label = display_scale(units)

    pts = {k: v * s for k, v in piece['points'].items()}
    outline = piece['outline'] * s
    meta = piece['metadata']

    fig, ax, standalone = setup_figure(ax, figsize=(8, 10))
    OUTLINE = SEAMLINE
    SA_STYLE = CUTLINE

    # Finished outline (closed pentagon)
    outline_closed = np.vstack([outline, outline[0:1]])
    ax.plot(outline_closed[:, 0], outline_closed[:, 1], **OUTLINE)

    # Seam allowances via draw_seam_allowance
    # Pentagon order: top_left → top_right → bottom_right → v_point → bottom_left
    # Edges: top, right side, lower-right, lower-left, left side
    sa_top = meta['sa_top']
    sa_sides = meta['sa_sides']
    sa_bottom = meta['sa_bottom']
    seam_top = 'Pocket top double-turn hem'
    seam_side = 'Pocket attach seam'

    sa_edges = [
        (np.array([pts['top_left'], pts['top_right']]),       sa_top, seam_top),     # top
        (np.array([pts['top_right'], pts['bottom_right']]),   sa_sides, seam_side),   # right side
        (np.array([pts['bottom_right'], pts['v_point']]),     sa_bottom, seam_side),  # lower-right
        (np.array([pts['v_point'], pts['bottom_left']]),      sa_bottom, seam_side),  # lower-left
        (np.array([pts['bottom_left'], pts['top_left']]),     sa_sides, seam_side),   # left side
    ]
    draw_seam_allowance(ax, sa_edges, scale=s, label_sas=not debug, units=units)

    # Grain line arrow (double-headed)
    from garment_programs.plot_utils import draw_grainline, draw_piece_label
    draw_grainline(ax, pts['grain_top'], pts['grain_bottom'])

    # Piece label (pattern mode only)
    if not debug:
        center = ((pts['top_left'][0] + pts['top_right'][0]) / 2,
                  (pts['top_center'][1] + pts['v_point'][1]) / 2)
        draw_piece_label(ax, center, piece['metadata']['title'],
                         piece['metadata'].get('cut_count'),
                         metadata=piece.get('metadata'))

    if debug:
        # Point labels
        for name, pt in pts.items():
            if name.startswith('grain'):
                continue
            ax.plot(pt[0], pt[1], 'o', color='steelblue', markersize=4, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), ha='left', fontsize=6, color='steelblue')

        # Dimension annotations
        _annotate_segment(ax, pts['top_left'], pts['top_right'], offset=(0, 8))
        _annotate_segment(ax, pts['top_right'], pts['bottom_right'], offset=(10, 0))
        _annotate_segment(ax, pts['bottom_right'], pts['v_point'], offset=(10, 0))

        # SA labels
        width_s = meta['width'] * s
        ax.annotate('7/8" SA (top)',
                    ((pts['top_left'][0] + pts['top_right'][0]) / 2,
                     pts['top_left'][1] + sa_top * s + 2 * s),
                    fontsize=6, ha='center', color='gray')
        ax.annotate('3/8" SA',
                    (pts['v_point'][0], pts['v_point'][1] - sa_bottom * s - 2 * s),
                    fontsize=6, ha='center', color='gray')

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug,
                    pdf_pages=pdf_pages)


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None,
        context=None):
    m = resolve_measurements(context, measurements_path, load_measurements)
    piece = cache_draft(
        context,
        'selvedge.watch_pocket',
        lambda: draft_jeans_watch_pocket(m),
    )
    plot_jeans_watch_pocket(piece, output_path, debug=debug, units=units,
                            pdf_pages=pdf_pages)
    return {'watch_pocket': piece}
