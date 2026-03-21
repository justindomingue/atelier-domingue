"""
Back Pocket — drafted on the back panel
Based on: Historical Tailoring Masterclasses - Drafting the Pockets and Accessories

Positioned relative to the yoke seam on the back panel so the pocket
inherits the panel's coordinate system (grain along x, parallel to CB).

Placement (from source):
  Right (outseam) edge:  2" below yoke seam, 2 1/2" from selvedge
  Left  (inseam) edge:  1 1/2" below yoke   (0.5" higher → slight upward tilt)

Pentagon dimensions:
  Mouth:   6 3/4" (top edge)
  Narrows: 5 1/4" at 6" depth
  Point:   center at 7" depth

Seam allowances:
  Sides and bottom: 3/8"
  Top:              7/8" (double fold + denim thickness)

Notes on 1873 jeans: only one pocket on the right side.
Modern jeans: one pocket on each side.
"""
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from garment_programs.core.runtime import cache_draft, resolve_measurements
from .jeans_front import INCH, load_measurements, draft_jeans_front, _annotate_segment
from .jeans_back import draft_jeans_back
from .jeans_yoke_1873 import draft_jeans_yoke
from garment_programs.plot_utils import (
    SEAMLINE, CUTLINE, draw_seam_allowance, display_scale, setup_figure, finalize_figure,
)


# -- Drafting ----------------------------------------------------------------

def draft_jeans_back_pocket(m, front, back, yoke):
    """Draft the back pocket positioned on the back panel.

    Parameters
    ----------
    m : dict
        Measurements in cm.
    front : dict
        Result of draft_jeans_front(m).
    back : dict
        Result of draft_jeans_back(m, front).
    yoke : dict
        Result of draft_jeans_yoke(m, front, back).

    Returns
    -------
    dict with keys: points, curves, construction, metadata
    """
    fpts = front['points']

    # -- Direction vectors (outseam-based, orthogonal) --
    yoke_side = yoke['points']['yoke_side']
    yoke_seat = yoke['points']['yoke_seat']

    outseam_vec = fpts['4'] - fpts['1']
    outseam_dir = outseam_vec / np.linalg.norm(outseam_vec)
    # Perpendicular to outseam, pointing inward from selvedge
    outseam_perp = np.array([-outseam_dir[1], outseam_dir[0]])
    if np.dot(outseam_perp, yoke_seat - yoke_side) < 0:
        outseam_perp = -outseam_perp

    # -- Pocket dimensions --
    mouth_width = 6.75 * INCH      # 6 3/4" total mouth
    top_half    = mouth_width / 2   # 3 3/8" each side from center
    mid_half    = 2.625 * INCH      # 2 5/8" each side at 6" mark
    mid_depth   = 6.0 * INCH       # depth to narrowing
    total_depth = 7.0 * INCH       # depth to bottom point

    # Seam allowances
    from .seam_allowances import SEAM_ALLOWANCES
    _sa = SEAM_ALLOWANCES['back_pocket']
    sa_side = _sa['side']
    sa_top  = _sa['top']

    # -- Position the pocket mouth on the back panel --
    # Right (outseam) corner: 2" below yoke along side seam, 2 1/2" inward from selvedge
    pocket_tr = yoke_side + outseam_dir * (2.0 * INCH) + outseam_perp * (2.5 * INCH)
    # Mouth tilted: left (CB) side is 1 1/2" below yoke, right is 2" → 0.5" higher
    mouth_raw = outseam_perp * mouth_width + outseam_dir * (-0.5 * INCH)
    mouth_dir = mouth_raw / np.linalg.norm(mouth_raw)
    # Left (inseam) corner: exactly mouth_width along the tilted mouth line
    pocket_tl = pocket_tr + mouth_dir * mouth_width
    mouth_center = (pocket_tl + pocket_tr) / 2

    # -- Pocket local axes --
    # depth_dir: perpendicular to mouth, pointing "downward" (toward hem)
    depth_dir = np.array([mouth_dir[1], -mouth_dir[0]])
    if np.dot(depth_dir, outseam_dir) < 0:
        depth_dir = -depth_dir

    # -- Finished-shape pentagon --
    f_tl    = pocket_tl
    f_tr    = pocket_tr
    f_ref_l = mouth_center + mouth_dir * mid_half + depth_dir * mid_depth
    f_ref_r = mouth_center - mouth_dir * mid_half + depth_dir * mid_depth
    f_bottom = mouth_center + depth_dir * total_depth

    # -- Grainline (along depth direction — parallel to CB) --
    grain_top    = mouth_center + depth_dir * (total_depth * 0.20)
    grain_bottom = mouth_center + depth_dir * (total_depth * 0.85)

    return {
        'points': {
            'f_tl': f_tl, 'f_tr': f_tr,
            'f_ref_l': f_ref_l, 'f_ref_r': f_ref_r,
            'f_bottom': f_bottom,
            'grain_top': grain_top, 'grain_bottom': grain_bottom,
        },
        'curves': {},
        'construction': {
            'ref_mark_depth': np.float64(mid_depth),
            'mouth_center': mouth_center,
            'depth_dir': depth_dir,
            'mouth_dir': mouth_dir,
        },
        'metadata': {
            'title': 'Back Pocket',
            'cut_count': 1,
            'width': mouth_width,
            'height': total_depth,
        },
    }


# -- Visualization -----------------------------------------------------------

def _to_local(pts_dict, mouth_dir, depth_dir, origin):
    """Rotate panel-coordinate points into pocket-local frame.

    Local frame: x = across (mouth_dir), y = up (opposite depth_dir).
    Origin is placed at the mouth center so the pocket is centered horizontally
    with mouth at top.
    """
    # Build rotation matrix: rows are the new basis vectors
    R = np.array([mouth_dir, -depth_dir])  # x=across, y=up (flip depth)
    return {k: R @ (v - origin) for k, v in pts_dict.items()}


def plot_jeans_back_pocket(pocket, output_path='Logs/jeans_back_pocket.svg',
                           debug=False, units='cm', pdf_pages=None, ax=None):
    s, unit_label = display_scale(units)

    # Rotate points into pocket-local frame (mouth horizontal, depth downward)
    mouth_dir = pocket['construction']['mouth_dir']
    depth_dir = pocket['construction']['depth_dir']
    origin = pocket['construction']['mouth_center']
    raw_pts = {k: v for k, v in pocket['points'].items()}
    local_pts = _to_local(raw_pts, mouth_dir, depth_dir, origin)
    pts = {k: v * s for k, v in local_pts.items()}

    fig, ax, standalone = setup_figure(ax, figsize=(8, 10))
    from .seam_allowances import SEAM_ALLOWANCES, SEAM_LABELS
    SA = SEAM_ALLOWANCES['back_pocket']
    SL = SEAM_LABELS['back_pocket']

    # Finished shape (pentagon: tl → tr → ref_r → bottom → ref_l → tl)
    f_order = ['f_tl', 'f_ref_l', 'f_bottom', 'f_ref_r', 'f_tr', 'f_tl']
    fx = [pts[k][0] for k in f_order]
    fy = [pts[k][1] for k in f_order]
    ax.plot(fx, fy, **SEAMLINE)

    # SA outline via draw_seam_allowance (CW in local coords)
    sa_edges = [
        (np.array([pts['f_tl'], pts['f_ref_l']]),      SA['side'], SL['side']),
        (np.array([pts['f_ref_l'], pts['f_bottom']]),  SA['side'], SL['side']),
        (np.array([pts['f_bottom'], pts['f_ref_r']]),  SA['side'], SL['side']),
        (np.array([pts['f_ref_r'], pts['f_tr']]),      SA['side'], SL['side']),
        (np.array([pts['f_tr'], pts['f_tl']]),         SA['top'], SL['top']),
    ]
    draw_seam_allowance(ax, sa_edges, scale=s, label_sas=not debug, units=units)

    # Grain line arrow (double-headed, now vertical in local frame)
    from garment_programs.plot_utils import draw_grainline, draw_piece_label
    draw_grainline(ax, pts['grain_top'], pts['grain_bottom'])

    # Piece label (pattern mode only)
    if not debug:
        centroid = (pts['f_tl'] + pts['f_tr'] + pts['f_ref_l'] + pts['f_ref_r'] + pts['f_bottom']) / 5
        draw_piece_label(ax, (centroid[0], centroid[1]),
                         pocket['metadata']['title'],
                         pocket['metadata'].get('cut_count'),
                         metadata=pocket.get('metadata'))

    if debug:
        for name in ['f_tl', 'f_tr', 'f_ref_l', 'f_ref_r', 'f_bottom']:
            pt = pts[name]
            ax.plot(pt[0], pt[1], 'o', color='black', markersize=4, zorder=5)
            ax.annotate(name, pt, textcoords="offset points",
                        xytext=(6, 4), fontsize=6, ha='left')

        _annotate_segment(ax, pts['f_tl'], pts['f_tr'], offset=(0, 8))
        _annotate_segment(ax, pts['f_tr'], pts['f_ref_r'], offset=(10, 0))
        _annotate_segment(ax, pts['f_ref_r'], pts['f_bottom'], offset=(10, 0))

    finalize_figure(ax, fig, standalone, output_path, units=units, debug=debug,
                    pdf_pages=pdf_pages)

# -- Nesting Extractors -----------------------------------------------------

def get_outline_back_pocket(draft):
    """Return the finished seamline for the back pocket.
    Shape: pentagon (tl -> ref_l -> bottom -> ref_r -> tr -> tl)
    """
    pts = draft['points']
    outline = np.array([
        pts['f_tl'],
        pts['f_ref_l'],
        pts['f_bottom'],
        pts['f_ref_r'],
        pts['f_tr'],
    ])
    return outline

def get_sa_outline_back_pocket(draft):
    """Return the full cut line boundary for the back pocket.
    This outline is used for polygon packing and bounding boxes.
    """
    pts = draft['points']

    # We need to construct the SA outline relative to the local origin
    # to match the packing logic, but the draft stores absolute coordinates
    # on the back panel. We use the _to_local transform for extractors too.
    mouth_dir = draft['construction']['mouth_dir']
    depth_dir = draft['construction']['depth_dir']
    origin = draft['construction']['mouth_center']
    local_pts = _to_local(pts, mouth_dir, depth_dir, origin)

    # SA outline is built in pocket-local coordinates (vertical grain)
    from garment_programs.plot_utils import offset_polyline
    from .seam_allowances import SEAM_ALLOWANCES
    SA = SEAM_ALLOWANCES['back_pocket']

    # CW edge order in local frame:
    # side(tl->ref_l), side(ref_l->bottom), side(bottom->ref_r),
    # side(ref_r->tr), top(tr->tl)
    outline = np.vstack([
        offset_polyline(np.array([local_pts['f_tl'], local_pts['f_ref_l']]), SA['side']),
        offset_polyline(np.array([local_pts['f_ref_l'], local_pts['f_bottom']]), SA['side']),
        offset_polyline(np.array([local_pts['f_bottom'], local_pts['f_ref_r']]), SA['side']),
        offset_polyline(np.array([local_pts['f_ref_r'], local_pts['f_tr']]), SA['side']),
        offset_polyline(np.array([local_pts['f_tr'], local_pts['f_tl']]), SA['top']),
    ])
    outline = np.vstack([outline, outline[0:1]])
    return outline


# -- Entry point for generic runner ------------------------------------------

def run(measurements_path, output_path, debug=False, units='cm', pdf_pages=None,
        context=None):
    m = resolve_measurements(context, measurements_path, load_measurements)
    front = cache_draft(context, 'selvedge.front', lambda: draft_jeans_front(m))
    back = cache_draft(context, 'selvedge.back:0.0000', lambda: draft_jeans_back(m, front))
    yoke = cache_draft(context, 'selvedge.yoke_1873:0.0000', lambda: draft_jeans_yoke(m, front, back))
    pocket = cache_draft(
        context,
        'selvedge.back_pocket:0.0000',
        lambda: draft_jeans_back_pocket(m, front, back, yoke),
    )
    plot_jeans_back_pocket(pocket, output_path, debug=debug, units=units,
                           pdf_pages=pdf_pages)
    return {'back_pocket': pocket}

