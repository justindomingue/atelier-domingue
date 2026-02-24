import warnings
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from garment_programs.geometry import INCH

CM_PER_INCH = INCH  # alias for backward compat in save_pattern / lay_plan

# -- Standard line styles for pattern pieces --------------------------------
# Seamline: the finished sewing line (thinner)
SEAMLINE = dict(color='blue', linewidth=1.0)
# Cutline: the seam-allowance / cutting line (thicker)
CUTLINE = dict(color='black', linewidth=1.5)


def draw_piece_label(ax, center, title, cut_count=None, fontsize=9):
    """Render piece name and cut count at center of the pattern piece."""
    label = title
    if cut_count:
        label += f'\nCut {cut_count}'
    ax.text(center[0], center[1], label,
            fontsize=fontsize, ha='center', va='center',
            color='black', alpha=0.6,
            bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='none', alpha=0.5))


def draw_grainline(ax, top, bottom, label='GRAIN'):
    """Draw a double-headed grainline arrow between two points."""
    ax.annotate('', xy=top, xytext=bottom,
                arrowprops=dict(arrowstyle='<->', color='black', lw=0.8))
    mid = ((top[0] + bottom[0]) / 2, (top[1] + bottom[1]) / 2)
    angle = np.degrees(np.arctan2(top[1] - bottom[1], top[0] - bottom[0]))
    ax.text(mid[0], mid[1], label, fontsize=7, ha='center', va='center',
            rotation=angle, color='black', alpha=0.6,
            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))


def draw_calibration_square(ax, size_cm=5.0):
    """Draw a calibration square in the bottom-right corner of the axes.

    Must be called *after* final axis limits are set (save_pattern does
    this automatically when calibration=True).
    """
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    margin = 1.0
    x0 = xmax - margin - size_cm
    y0 = ymin + margin

    rect = mpatches.Rectangle(
        (x0, y0), size_cm, size_cm,
        linewidth=0.8, edgecolor='black', facecolor='none', zorder=5,
    )
    ax.add_patch(rect)
    ax.text(x0 + size_cm / 2, y0 + size_cm / 2,
            f'{size_cm:.0f}\u2009cm', fontsize=6,
            ha='center', va='center', color='black', zorder=5)


def save_pattern(fig, ax, output_path, units='cm', pad_cm=1.0, calibration=False,
                 pdf_pages=None):
    """Save a pattern figure at 1:1 real-world scale.

    Sets figure dimensions so that 1 data-unit maps to 1 physical unit
    in the output file (1 cm on screen = 1 cm in reality).

    If calibration=True, draws a 5 cm calibration square in the corner.
    If pdf_pages is provided, also adds the figure to the multi-page PDF.
    """
    ax.set_aspect('equal')
    ax.margins(0)
    ax.relim()
    ax.autoscale_view()

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    # Minimal padding for SVG intermediates; full padding for printed formats
    if str(output_path).endswith('.svg'):
        pad = 0.1 if units == 'cm' else 0.1 / CM_PER_INCH
    else:
        pad = pad_cm if units == 'cm' else pad_cm / CM_PER_INCH
    xmin -= pad
    xmax += pad
    ymin -= pad
    ymax += pad
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    if calibration and not str(output_path).endswith('.svg'):
        draw_calibration_square(ax)

    data_w = xmax - xmin
    data_h = ymax - ymin
    scale = CM_PER_INCH if units == 'cm' else 1.0
    fig.set_size_inches(data_w / scale, data_h / scale)

    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    if pdf_pages is not None:
        pdf_pages.savefig(fig)
    plt.close(fig)
    print(f"Saved visualization to {output_path}")


# -- Seam-allowance offset utilities ----------------------------------------

def offset_polyline(pts, distance):
    """Offset a polyline by *distance* to the left of the travel direction.

    For a clockwise outline, positive *distance* pushes outward.

    Parameters
    ----------
    pts : ndarray, shape (N, 2)
        Ordered polyline vertices.
    distance : float
        Offset distance (positive = left of travel = outward for CW).

    Returns
    -------
    ndarray, shape (N, 2)
        Offset polyline (same number of points, miter-joined).
    """
    pts = np.asarray(pts, dtype=float)
    n = len(pts)
    if n < 2:
        return pts.copy()

    # Per-segment unit normals (left of travel direction)
    seg = np.diff(pts, axis=0)                       # (N-1, 2)
    lengths = np.sqrt(seg[:, 0]**2 + seg[:, 1]**2)
    lengths = np.where(lengths == 0, 1e-12, lengths)  # avoid div-by-zero
    normals = np.column_stack([-seg[:, 1], seg[:, 0]]) / lengths[:, None]

    out = np.empty_like(pts)

    # First and last points: simple normal offset
    out[0] = pts[0] + normals[0] * distance
    out[-1] = pts[-1] + normals[-1] * distance

    # Interior points: average of adjacent normals (miter)
    for i in range(1, n - 1):
        avg = normals[i - 1] + normals[i]
        length = np.linalg.norm(avg)
        if length < 1e-12:
            avg = normals[i]
        else:
            avg = avg / length
        # Miter scale: project onto either normal
        cos_half = np.dot(avg, normals[i])
        if abs(cos_half) < 0.3:
            cos_half = 0.3  # miter limit: max ~3.3× offset distance
        out[i] = pts[i] + avg * (distance / cos_half)

    return out


def _line_line_intersect(p1, p2, p3, p4):
    """Intersection of lines through (p1→p2) and (p3→p4), or None if parallel."""
    d1 = np.asarray(p2, dtype=float) - np.asarray(p1, dtype=float)
    d2 = np.asarray(p4, dtype=float) - np.asarray(p3, dtype=float)
    cross = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(cross) < 1e-12:
        return None
    dp = np.asarray(p3, dtype=float) - np.asarray(p1, dtype=float)
    t = (dp[0] * d2[1] - dp[1] * d2[0]) / cross
    return np.asarray(p1, dtype=float) + t * d1


def draw_seam_allowance(ax, edges, scale=1.0):
    """Draw a continuous seam-allowance boundary for an ordered list of edges.

    Edges must be ordered so that they form a continuous CW perimeter
    (each edge's last point ≈ the next edge's first point).  The function
    offsets each edge by its SA, then connects adjacent offset segments at
    their intersection (miter point) to produce one unbroken cutting line.

    Parameters
    ----------
    ax : matplotlib Axes
    edges : list of (pts, sa_distance) tuples
        *pts* is an (N,2) ndarray (already display-scaled),
        *sa_distance* is the seam allowance in **cm** (pre-scaling).
    scale : float
        Display scale factor (e.g. 1/INCH for inch mode).
    """
    # Validate CW winding via signed area of edge start-points
    if len(edges) >= 3:
        verts = np.array([np.asarray(e[0])[0] for e in edges])
        x, y = verts[:, 0], verts[:, 1]
        signed_area = np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y) / 2
        if signed_area > 1e-6:
            warnings.warn(
                "SA edges appear to be wound counter-clockwise (signed area "
                f"= {signed_area:.2f}).  Seam allowance will draw inward.  "
                "Reverse the edge order to fix.",
                stacklevel=2,
            )
    # Offset each edge independently
    offsets = []
    scaled_sas = []
    for pts, sa_cm in edges:
        sa = sa_cm * scale
        scaled_sas.append(abs(sa))
        offsets.append(offset_polyline(pts, sa))

    n = len(offsets)

    # Miter each junction: extend adjacent offset segments to their intersection.
    # Cap the miter distance to prevent spikes at sharp corners.
    for i in range(n):
        j = (i + 1) % n
        cur, nxt = offsets[i], offsets[j]
        if len(cur) >= 2 and len(nxt) >= 2:
            ip = _line_line_intersect(cur[-2], cur[-1], nxt[0], nxt[1])
            if ip is not None:
                max_sa = max(scaled_sas[i], scaled_sas[j])
                miter_dist = np.linalg.norm(ip - cur[-1])
                if max_sa < 1e-12 or miter_dist < 4 * max_sa:
                    cur[-1] = ip
                    nxt[0] = ip

    # Build continuous SA path from mitered segments
    sa_pts = list(offsets[0])
    for i in range(1, n):
        sa_pts.extend(offsets[i].tolist())

    # Close the loop back to the starting point
    sa_pts.append(sa_pts[0])
    sa_path = np.array(sa_pts)
    ax.plot(sa_path[:, 0], sa_path[:, 1], **CUTLINE)


# -- Plot boilerplate helpers ------------------------------------------------

def display_scale(units):
    """Return (scale_factor, unit_label) for converting from cm to display units."""
    s = 1 / INCH if units == 'inch' else 1.0
    label = 'in' if units == 'inch' else 'cm'
    return s, label


def setup_figure(ax=None, figsize=(16, 10)):
    """Create or reuse a figure/axes pair.

    Returns (fig, ax, standalone).  When *standalone* is True, the caller
    should call :func:`finalize_figure` to save and close the figure.
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(1, 1, figsize=figsize)
    else:
        fig = ax.get_figure()
    return fig, ax, standalone


def finalize_figure(ax, fig, standalone, output_path, units='cm', debug=False,
                    pdf_pages=None):
    """Clean up axes and save the figure if standalone.

    debug=True:  show xlabel, ylabel, and grid.
    debug=False: turn off axes.
    Always saves via save_pattern when standalone.
    """
    if not debug:
        ax.axis('off')
    else:
        _, unit_label = display_scale(units)
        ax.set_xlabel(unit_label)
        ax.set_ylabel(unit_label)
        ax.grid(True, alpha=0.2)

    if standalone:
        save_pattern(fig, ax, output_path, units=units, calibration=not debug,
                     pdf_pages=pdf_pages)
