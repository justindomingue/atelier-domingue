"""
Bounding-box inflation analysis for jeans front and back panels.

Compares three bounding-box methods:
  1. Outline-only: min/max of just outline points and curves
  2. With SA: outline expanded by seam allowance offsets
  3. Matplotlib auto-sized: what matplotlib computes via relim()/autoscale_view()
"""
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, '/Users/justindomingue/Downloads/atelier-domingue/.claude/worktrees/swift-ray-yd4p')

from garment_programs.SelvedgeJeans1873.jeans_front import (
    load_measurements, draft_jeans_front, INCH,
    _offset_polyline, _curve_length, _curve_up_to_arclength,
)
from garment_programs.SelvedgeJeans1873.jeans_back import draft_jeans_back


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def outline_bbox_front(draft):
    """Compute bounding box from just the outline geometry of the front panel.

    Outline consists of:
      - curves: hip, rise, crotch, inseam
      - straight segments: 4->0, 7'->8, 3'->0', 0'->0
    """
    pts = draft['points']
    curves = draft['curves']

    # Collect all outline points into one array
    outline_pts = []

    # Curves
    for name in ('hip', 'rise', 'crotch', 'inseam'):
        outline_pts.append(curves[name])

    # Straight segments
    for a, b in [('4', '0'), ("7'", '8'), ("3'", "0'"), ("0'", '0')]:
        outline_pts.append(np.array([pts[a], pts[b]]))

    all_pts = np.vstack(outline_pts)
    xmin, ymin = all_pts.min(axis=0)
    xmax, ymax = all_pts.max(axis=0)
    return xmin, ymin, xmax, ymax


def outline_bbox_back(front, back):
    """Compute bounding box from just the outline geometry of the back panel.

    Outline consists of:
      - curves: seat_upper, seat_lower, back_inseam
      - straight segments: 1->back_waist (waist), 12->back_hem, back_hem->0, 0->4, 4->1
    """
    fpts = front['points']
    bpts = back['points']
    bcurves = back['curves']

    outline_pts = []

    # Curves
    for name in ('seat_upper', 'seat_lower', 'back_inseam'):
        outline_pts.append(bcurves[name])

    # Straight segments
    segments = [
        (fpts['1'], bpts['back_waist']),    # waist
        (bpts['12'], bpts['back_hem']),      # lower inseam
        (bpts['back_hem'], fpts['0']),       # hem
        (fpts['0'], fpts['4']),              # outseam lower
        (fpts['4'], fpts['1']),              # outseam upper
    ]
    for a, b in segments:
        outline_pts.append(np.array([a, b]))

    all_pts = np.vstack(outline_pts)
    xmin, ymin = all_pts.min(axis=0)
    xmax, ymax = all_pts.max(axis=0)
    return xmin, ymin, xmax, ymax


def sa_bbox_front(draft):
    """Compute bounding box including seam allowance offsets for the front panel."""
    pts = draft['points']
    curves = draft['curves']

    SA_SIDE   = 3/4 * INCH
    SA_HEM    = (1.5 + 7/8) * INCH
    SA_INSEAM = 3/8 * INCH
    SA_CROTCH = 3/8 * INCH
    SA_FLY    = 3/4 * INCH
    SA_WAIST  = 3/8 * INCH

    # Build SA edges exactly as in plot_jeans_front
    _crotch_rev = curves['crotch'][::-1]
    _crotch_len = _curve_length(_crotch_rev)
    _split      = 0.5 * INCH
    _crotch_body = _curve_up_to_arclength(_crotch_rev, _crotch_len - _split)
    _crotch_end  = _curve_up_to_arclength(_crotch_rev[::-1], _split)[::-1]

    sa_edges = [
        (curves['hip'],                                          SA_SIDE),
        (np.array([pts['4'], pts['0']]),                         SA_SIDE),
        (np.array([pts['0'], pts["0'"]]),                        SA_HEM),
        (np.array([pts["0'"], pts["3'"]]),                       SA_INSEAM),
        (curves['inseam'][::-1],                                 SA_INSEAM),
        (_crotch_body,                                           SA_CROTCH),
        (_crotch_end,                                            SA_FLY),
        (np.array([pts['8'], pts["7'"]]),                        SA_FLY),
        (curves['rise'][::-1],                                   SA_WAIST),
    ]

    # Build offset polylines
    all_sa_pts = []
    for edge_pts, sa_dist in sa_edges:
        offset = _offset_polyline(edge_pts, sa_dist)
        all_sa_pts.append(offset)

    # Also include the outline itself
    outline_pts = []
    for name in ('hip', 'rise', 'crotch', 'inseam'):
        outline_pts.append(curves[name])
    for a, b in [('4', '0'), ("7'", '8'), ("3'", "0'"), ("0'", '0')]:
        outline_pts.append(np.array([pts[a], pts[b]]))

    all_pts = np.vstack(outline_pts + all_sa_pts)
    xmin, ymin = all_pts.min(axis=0)
    xmax, ymax = all_pts.max(axis=0)
    return xmin, ymin, xmax, ymax


def sa_bbox_back(front, back):
    """Compute bounding box including seam allowance offsets for the back panel."""
    fpts = front['points']
    bpts = back['points']
    bcurves = back['curves']

    SA_SIDE    = 3/4 * INCH
    SA_HEM     = (1.5 + 7/8) * INCH
    SA_INSEAM  = 3/4 * INCH
    SA_SEAT    = 5/8 * INCH
    SA_YOKE    = 3/4 * INCH

    sa_edges = [
        (np.array([fpts['1'], fpts['4']]),                       SA_SIDE),
        (np.array([fpts['4'], fpts['0']]),                       SA_SIDE),
        (np.array([fpts['0'], bpts['back_hem']]),                SA_HEM),
        (np.array([bpts['back_hem'], bpts['12']]),               SA_INSEAM),
        (bcurves['back_inseam'][::-1],                           SA_INSEAM),
        (bcurves['seat_lower'][::-1],                            SA_SEAT),
        (bcurves['seat_upper'][::-1],                            SA_SEAT),
        (np.array([bpts['back_waist'], fpts['1']]),              SA_YOKE),
    ]

    # Build offset polylines
    all_sa_pts = []
    for edge_pts, sa_dist in sa_edges:
        offset = _offset_polyline(edge_pts, sa_dist)
        all_sa_pts.append(offset)

    # Also include the outline itself
    outline_pts = []
    for name in ('seat_upper', 'seat_lower', 'back_inseam'):
        outline_pts.append(bcurves[name])
    segments = [
        (fpts['1'], bpts['back_waist']),
        (bpts['12'], bpts['back_hem']),
        (bpts['back_hem'], fpts['0']),
        (fpts['0'], fpts['4']),
        (fpts['4'], fpts['1']),
    ]
    for a, b in segments:
        outline_pts.append(np.array([a, b]))

    all_pts = np.vstack(outline_pts + all_sa_pts)
    xmin, ymin = all_pts.min(axis=0)
    xmax, ymax = all_pts.max(axis=0)
    return xmin, ymin, xmax, ymax


def matplotlib_bbox_front(draft):
    """Render the front panel and capture matplotlib's auto-sized bounding box.

    We replicate the plot_jeans_front logic but capture ax limits before
    save_pattern adjusts them.
    """
    from garment_programs.SelvedgeJeans1873.jeans_front import (
        _draw_seam_allowance, _curve_up_to_arclength, _curve_length,
    )
    pts = draft['points']
    curves = draft['curves']

    s = 1.0  # cm units
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))

    # Pattern outline: curves
    for curve in curves.values():
        ax.plot(curve[:, 0] * s, curve[:, 1] * s, 'k-', linewidth=1.5)

    # Pattern outline: straight segments
    for a, b in [('4', '0'), ("7'", '8'), ("3'", "0'"), ("0'", '0')]:
        ax.plot([pts[a][0] * s, pts[b][0] * s],
                [pts[a][1] * s, pts[b][1] * s], 'k-', linewidth=1.5)

    # Reference lines (these extend BEYOND the outline)
    y_lo = min(pts['6'][1], pts['5'][1]) * s - 2
    y_hi = 2

    seat_x = pts['4'][0] * s
    ax.plot([seat_x, seat_x], [y_lo, y_hi], **REF)
    ax.annotate('seat', (seat_x, y_hi), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    hip_x = pts['2'][0] * s
    ax.plot([hip_x, hip_x], [y_lo, y_hi], **REF)
    ax.annotate('hip', (hip_x, y_hi), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    knee_x = pts['3'][0] * s
    ax.plot([knee_x, knee_x], [y_lo, y_hi], **REF)
    ax.annotate('knee', (knee_x, y_hi), textcoords="offset points",
                xytext=(4, 4), fontsize=7, color='gray')

    x_left, x_right = pts['1'][0] * s - 3, pts['0'][0] * s + 3
    cf_mid = (x_left + x_right) / 2
    ax.plot([x_left, x_right], [pts['10'][1] * s, pts['10'][1] * s], **REF)
    ax.annotate('center front', (cf_mid, pts['10'][1] * s), textcoords="offset points",
                xytext=(0, 4), fontsize=7, color='gray', ha='center')

    # Seam allowances
    SA_SIDE   = 3/4 * INCH
    SA_HEM    = (1.5 + 7/8) * INCH
    SA_INSEAM = 3/8 * INCH
    SA_CROTCH = 3/8 * INCH
    SA_FLY    = 3/4 * INCH
    SA_WAIST  = 3/8 * INCH

    scaled_curves = {k: v * s for k, v in curves.items()}
    scaled_pts = {k: v * s for k, v in pts.items()}

    _crotch_rev = scaled_curves['crotch'][::-1]
    _crotch_len = _curve_length(_crotch_rev)
    _split      = 0.5 * INCH * s
    _crotch_body = _curve_up_to_arclength(_crotch_rev, _crotch_len - _split)
    _crotch_end  = _curve_up_to_arclength(_crotch_rev[::-1], _split)[::-1]

    sa_edges = [
        (scaled_curves['hip'],                                          SA_SIDE),
        (np.array([scaled_pts['4'], scaled_pts['0']]),                  SA_SIDE),
        (np.array([scaled_pts['0'], scaled_pts["0'"]]),                 SA_HEM),
        (np.array([scaled_pts["0'"], scaled_pts["3'"]]),                SA_INSEAM),
        (scaled_curves['inseam'][::-1],                                 SA_INSEAM),
        (_crotch_body,                                                  SA_CROTCH),
        (_crotch_end,                                                   SA_FLY),
        (np.array([scaled_pts['8'], scaled_pts["7'"]]),                 SA_FLY),
        (scaled_curves['rise'][::-1],                                   SA_WAIST),
    ]
    _draw_seam_allowance(ax, sa_edges, scale=s)

    ax.axis('off')

    # Now capture matplotlib's auto-sized bbox
    ax.set_aspect('equal')
    ax.margins(0)
    ax.relim()
    ax.autoscale_view()

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    plt.close(fig)
    return xmin, ymin, xmax, ymax


def matplotlib_bbox_back(front, back):
    """Render the back panel and capture matplotlib's auto-sized bounding box."""
    from garment_programs.SelvedgeJeans1873.jeans_front import (
        _draw_seam_allowance,
    )
    fpts = front['points']
    bpts = back['points']
    bcurves = back['curves']
    fcurves = front['curves']

    s = 1.0
    OUTLINE = dict(color='black', linewidth=1.5)
    REF = dict(color='gray', linewidth=0.8, linestyle='--', alpha=0.4)
    YOKE_REF = dict(color='steelblue', linewidth=1.2, linestyle='--')

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))

    # Pattern outline
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

    # Yoke seam reference line
    ax.plot(bcurves['yoke_seat_curve'][:, 0], bcurves['yoke_seat_curve'][:, 1], **YOKE_REF)
    ax.plot([bpts['yoke_seat'][0], bpts['yoke_side'][0]],
            [bpts['yoke_seat'][1], bpts['yoke_side'][1]], **YOKE_REF)
    ax.plot([bpts['yoke_side'][0], fpts['1'][0]],
            [bpts['yoke_side'][1], fpts['1'][1]], **YOKE_REF)
    yoke_mid = (bpts['yoke_seat'] + bpts['yoke_side']) / 2
    ax.annotate('yoke seam', yoke_mid, textcoords="offset points",
                xytext=(0, -14), fontsize=7, color='steelblue', ha='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.8))
    _seam_d    = bpts['yoke_seat'] - bpts['yoke_side']
    _seam_norm = _seam_d / np.linalg.norm(_seam_d)
    _perp      = np.array([-_seam_norm[1], _seam_norm[0]])
    _nsize     = 0.25 * INCH
    ax.plot([yoke_mid[0] - _perp[0]*_nsize, yoke_mid[0] + _perp[0]*_nsize],
            [yoke_mid[1] - _perp[1]*_nsize, yoke_mid[1] + _perp[1]*_nsize],
            color='steelblue', linewidth=1.2)

    # Reference lines
    y_lo = min(bpts['11'][1], fpts['6'][1]) - 3
    y_hi = 2

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

    x_left, x_right = fpts['1'][0] - 3, fpts['0'][0] + 3
    cf_mid = (x_left + x_right) / 2
    ax.plot([x_left, x_right], [fpts['10'][1], fpts['10'][1]], **REF)
    ax.annotate('center front', (cf_mid, fpts['10'][1]), textcoords="offset points",
                xytext=(0, 4), fontsize=7, color='gray', ha='center')

    # Seam allowances
    SA_SIDE    = 3/4 * INCH
    SA_HEM     = (1.5 + 7/8) * INCH
    SA_INSEAM  = 3/4 * INCH
    SA_SEAT    = 5/8 * INCH
    SA_YOKE    = 3/4 * INCH

    sa_edges = [
        (np.array([fpts['1'], fpts['4']]),                       SA_SIDE),
        (np.array([fpts['4'], fpts['0']]),                       SA_SIDE),
        (np.array([fpts['0'], bpts['back_hem']]),                SA_HEM),
        (np.array([bpts['back_hem'], bpts['12']]),               SA_INSEAM),
        (bcurves['back_inseam'][::-1],                           SA_INSEAM),
        (bcurves['seat_lower'][::-1],                            SA_SEAT),
        (bcurves['seat_upper'][::-1],                            SA_SEAT),
        (np.array([bpts['back_waist'], fpts['1']]),              SA_YOKE),
    ]
    _draw_seam_allowance(ax, sa_edges, scale=s)

    ax.axis('off')

    ax.set_aspect('equal')
    ax.margins(0)
    ax.relim()
    ax.autoscale_view()

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    plt.close(fig)
    return xmin, ymin, xmax, ymax


def bbox_dims(bbox):
    """Return (width, height, area) for a bbox tuple (xmin, ymin, xmax, ymax)."""
    xmin, ymin, xmax, ymax = bbox
    w = xmax - xmin
    h = ymax - ymin
    return w, h, w * h


def print_table(piece_name, outline_bb, sa_bb, mpl_bb):
    """Print a comparison table for one piece."""
    o_w, o_h, o_a = bbox_dims(outline_bb)
    s_w, s_h, s_a = bbox_dims(sa_bb)
    m_w, m_h, m_a = bbox_dims(mpl_bb)

    inflation_sa = ((s_a / o_a) - 1) * 100 if o_a > 0 else 0
    inflation_mpl = ((m_a / o_a) - 1) * 100 if o_a > 0 else 0

    print(f"\n{'='*70}")
    print(f"  {piece_name}")
    print(f"{'='*70}")
    print(f"  {'Method':<25} {'Width (cm)':>12} {'Height (cm)':>12} {'Area (cm2)':>12} {'Inflation':>10}")
    print(f"  {'-'*25} {'-'*12} {'-'*12} {'-'*12} {'-'*10}")
    print(f"  {'Outline-only':<25} {o_w:>12.2f} {o_h:>12.2f} {o_a:>12.2f} {'baseline':>10}")
    print(f"  {'With SA':<25} {s_w:>12.2f} {s_h:>12.2f} {s_a:>12.2f} {inflation_sa:>9.1f}%")
    print(f"  {'Matplotlib auto-sized':<25} {m_w:>12.2f} {m_h:>12.2f} {m_a:>12.2f} {inflation_mpl:>9.1f}%")
    print()
    print(f"  Bbox coordinates (xmin, ymin, xmax, ymax) in cm:")
    print(f"    Outline:    ({outline_bb[0]:8.2f}, {outline_bb[1]:8.2f}, {outline_bb[2]:8.2f}, {outline_bb[3]:8.2f})")
    print(f"    With SA:    ({sa_bb[0]:8.2f}, {sa_bb[1]:8.2f}, {sa_bb[2]:8.2f}, {sa_bb[3]:8.2f})")
    print(f"    Matplotlib: ({mpl_bb[0]:8.2f}, {mpl_bb[1]:8.2f}, {mpl_bb[2]:8.2f}, {mpl_bb[3]:8.2f})")

    return o_a, s_a, m_a


def draw_visual_comparison(draft, front_outline_bb, front_sa_bb, front_mpl_bb, output_path):
    """Draw the front panel with all three bounding boxes overlaid."""
    pts = draft['points']
    curves = draft['curves']

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))

    # Draw outline
    for name, curve in curves.items():
        ax.plot(curve[:, 0], curve[:, 1], 'k-', linewidth=1.5)

    for a, b in [('4', '0'), ("7'", '8'), ("3'", "0'"), ("0'", '0')]:
        ax.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]], 'k-', linewidth=1.5)

    # Draw bounding boxes
    def draw_rect(ax, bbox, color, label, lw=2, ls='-'):
        xmin, ymin, xmax, ymax = bbox
        rect = plt.Rectangle((xmin, ymin), xmax - xmin, ymax - ymin,
                              linewidth=lw, edgecolor=color, facecolor=color,
                              alpha=0.08, linestyle=ls, label=label)
        ax.add_patch(rect)
        # Also draw just the border for clarity
        ax.plot([xmin, xmax, xmax, xmin, xmin],
                [ymin, ymin, ymax, ymax, ymin],
                color=color, linewidth=lw, linestyle=ls)

    draw_rect(ax, front_mpl_bb, 'red', 'Matplotlib auto-sized', lw=2.5, ls='--')
    draw_rect(ax, front_sa_bb, 'blue', 'With seam allowance', lw=2, ls='-.')
    draw_rect(ax, front_outline_bb, 'green', 'Outline-only', lw=2, ls='-')

    # Annotations for areas
    o_w, o_h, o_a = bbox_dims(front_outline_bb)
    s_w, s_h, s_a = bbox_dims(front_sa_bb)
    m_w, m_h, m_a = bbox_dims(front_mpl_bb)

    text = (
        f"Outline:    {o_w:.1f} x {o_h:.1f} = {o_a:.0f} cm$^2$\n"
        f"With SA:    {s_w:.1f} x {s_h:.1f} = {s_a:.0f} cm$^2$ (+{((s_a/o_a)-1)*100:.1f}%)\n"
        f"Matplotlib: {m_w:.1f} x {m_h:.1f} = {m_a:.0f} cm$^2$ (+{((m_a/o_a)-1)*100:.1f}%)"
    )

    ax.text(0.02, 0.02, text, transform=ax.transAxes, fontsize=9,
            verticalalignment='bottom', fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', alpha=0.9))

    ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
    ax.set_aspect('equal')
    ax.set_title('Jeans Front Panel: Bounding Box Comparison', fontsize=14)
    ax.set_xlabel('cm')
    ax.set_ylabel('cm')
    ax.grid(True, alpha=0.15)

    # Ensure everything is visible
    all_bbs = [front_outline_bb, front_sa_bb, front_mpl_bb]
    pad = 3
    ax.set_xlim(min(bb[0] for bb in all_bbs) - pad, max(bb[2] for bb in all_bbs) + pad)
    ax.set_ylim(min(bb[1] for bb in all_bbs) - pad, max(bb[3] for bb in all_bbs) + pad)

    fig.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\nSaved visual comparison to {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    measurements_path = '/Users/justindomingue/Downloads/atelier-domingue/.claude/worktrees/swift-ray-yd4p/measurements/justin.yaml'
    m = load_measurements(measurements_path)

    print("Drafting jeans front and back panels...")
    front = draft_jeans_front(m)
    back = draft_jeans_back(m, front)

    # --- Front panel ---
    front_outline_bb = outline_bbox_front(front)
    front_sa_bb = sa_bbox_front(front)
    front_mpl_bb = matplotlib_bbox_front(front)

    # --- Back panel ---
    back_outline_bb = outline_bbox_back(front, back)
    back_sa_bb = sa_bbox_back(front, back)
    back_mpl_bb = matplotlib_bbox_back(front, back)

    # --- Print tables ---
    front_o_a, front_s_a, front_m_a = print_table(
        "JEANS FRONT PANEL", front_outline_bb, front_sa_bb, front_mpl_bb
    )
    back_o_a, back_s_a, back_m_a = print_table(
        "JEANS BACK PANEL", back_outline_bb, back_sa_bb, back_mpl_bb
    )

    # --- Combined totals ---
    total_outline = front_o_a + back_o_a
    total_sa = front_s_a + back_s_a
    total_mpl = front_m_a + back_m_a

    print(f"\n{'='*70}")
    print(f"  COMBINED TOTALS (Front + Back)")
    print(f"{'='*70}")
    print(f"  {'Method':<25} {'Total Area (cm2)':>16} {'Inflation vs Outline':>22}")
    print(f"  {'-'*25} {'-'*16} {'-'*22}")
    print(f"  {'Outline-only':<25} {total_outline:>16.2f} {'baseline':>22}")
    print(f"  {'With SA':<25} {total_sa:>16.2f} {((total_sa/total_outline)-1)*100:>21.1f}%")
    print(f"  {'Matplotlib auto-sized':<25} {total_mpl:>16.2f} {((total_mpl/total_outline)-1)*100:>21.1f}%")
    print()

    savings_vs_mpl = ((total_mpl - total_outline) / total_mpl) * 100
    savings_vs_sa = ((total_sa - total_outline) / total_sa) * 100
    print(f"  Space savings using outline-only vs matplotlib: {savings_vs_mpl:.1f}%")
    print(f"  Space savings using outline-only vs SA:         {savings_vs_sa:.1f}%")
    print(f"  Space savings using SA-based vs matplotlib:     {((total_mpl - total_sa) / total_mpl) * 100:.1f}%")

    # --- Visual comparison ---
    draw_visual_comparison(
        front, front_outline_bb, front_sa_bb, front_mpl_bb,
        '/tmp/bbox_comparison.png'
    )


if __name__ == '__main__':
    main()
