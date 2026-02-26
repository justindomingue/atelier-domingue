import warnings
from fractions import Fraction
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from garment_programs.geometry import INCH
from garment_programs.core.pattern_metadata import get_active_pattern_context

CM_PER_INCH = INCH  # alias for backward compat in save_pattern / lay_plan

# -- Standard line styles for pattern pieces --------------------------------
# Seamline: the finished sewing line (thinner)
SEAMLINE = dict(color='blue', linewidth=1.0)
# Cutline: the seam-allowance / cutting line (thicker)
CUTLINE = dict(color='black', linewidth=1.5)


def draw_fold_line(ax, top, bottom):
    """Draw a dash-dot fold line with centered 'FOLD' label."""
    ax.plot([top[0], bottom[0]], [top[1], bottom[1]],
            color='black', linewidth=0.8, linestyle='-.', alpha=0.6)
    mid = ((top[0] + bottom[0]) / 2, (top[1] + bottom[1]) / 2)
    angle = np.degrees(np.arctan2(top[1] - bottom[1], top[0] - bottom[0]))
    ax.text(mid[0], mid[1], 'FOLD', fontsize=7, ha='center', va='center',
            rotation=angle, color='black', alpha=0.6,
            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))


def draw_piece_label(ax, center, title, cut_count=None, fold=False, fontsize=9,
                     metadata=None):
    """Render a piece title block with cut/count info and pattern codes."""
    metadata = metadata or {}
    context = get_active_pattern_context()

    pattern_set_code = metadata.get('pattern_set_code') or context.get('pattern_set_code')
    size_code = metadata.get('size_code') or context.get('size_code')

    label_lines = [title]
    if cut_count:
        cut_line = f'Cut {cut_count}'
        if fold:
            cut_line += ' on fold'
        label_lines.append(cut_line)
    if pattern_set_code:
        label_lines.append(f'Pattern {pattern_set_code}')
    if size_code:
        attrs = []
        if size_code:
            attrs.append(f'Size {size_code}')
        label_lines.append(' | '.join(attrs))
    label = '\n'.join(label_lines)

    ax.text(center[0], center[1], label,
            fontsize=fontsize, ha='center', va='center',
            color='black', alpha=0.6,
            bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='none', alpha=0.5))


def draw_grainline(ax, top, bottom, label=None):
    """Draw a double-headed grainline arrow between two points.

    If ``label`` is provided, it is drawn centered on the arrow.
    """
    ax.annotate('', xy=top, xytext=bottom,
                arrowprops=dict(arrowstyle='<->', color='black', lw=0.8))
    if label:
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


# -- Notch utility -----------------------------------------------------------

def draw_notch(ax, curve, point, sa_distance, scale=1.0, tangent_offset=0,
               flip=False, notch_length=0.5 * INCH, style='line',
               count=1, notch_spacing=0.25 * INCH, notch_width=0.25 * INCH,
               line_from_cutline=True, line_to_seamline=False):
    """Draw notch marks perpendicular to the cut line.

    Parameters
    ----------
    ax : matplotlib Axes
    curve : ndarray (N, 2)
        The seamline polyline (already display-scaled).
    point : ndarray (2,)
        Location on the seamline (already display-scaled).
    sa_distance : float
        Seam allowance in cm (pre-scaling), retained for compatibility.
    scale : float
        Display scale factor.
    tangent_offset : float
        Distance in cm (pre-scaling) to shift the notch along the curve
        from *point*.  Positive = forward along curve travel direction.
    flip : bool
        If True, flip the outward normal (use when the curve runs opposite
        to the SA edge winding direction).
    notch_length : float | None
        Notch depth in cm (pre-scaling). For line notches drawn from cutline,
        depth is measured inward toward the garment interior.
        Use None to fall back to legacy behavior (SA + 1/8").
    style : str
        ``'line'`` (default) or ``'triangle'``.
    count : int
        Number of notch marks (1=single, 2=double, 3=triple).
    notch_spacing : float
        Spacing between notch centers in cm (pre-scaling) for multiple notches.
    notch_width : float
        Base width of triangular notch in cm (pre-scaling).
    line_from_cutline : bool
        For ``style='line'``, start the notch at the cut line (default).
        When False, uses legacy seamline-origin behavior.
    line_to_seamline : bool
        For ``style='line'`` with cutline origin, end the notch exactly at
        the seamline, ignoring ``notch_length``.
    """
    if len(curve) < 2:
        return

    # Find tangent at nearest point on curve
    dists = np.linalg.norm(curve - point, axis=1)
    idx = np.argmin(dists)
    if idx == 0:
        tangent = curve[1] - curve[0]
    elif idx >= len(curve) - 1:
        tangent = curve[-1] - curve[-2]
    else:
        tangent = curve[idx + 1] - curve[idx - 1]
    tangent_norm = np.linalg.norm(tangent)
    if tangent_norm == 0:
        return
    tangent = tangent / tangent_norm

    # Normal perpendicular to tangent (left of travel = outward for CW)
    normal = np.array([-tangent[1], tangent[0]])
    if flip:
        normal = -normal
    if notch_length is None:
        notch_len = abs(sa_distance) + 0.125 * INCH
    else:
        notch_len = abs(notch_length)
    notch_len *= scale

    base = point + tangent * (tangent_offset * scale)
    count = max(1, int(count))
    spacing = notch_spacing * scale
    half_span = (count - 1) / 2

    sa_depth = abs(sa_distance) * scale
    for i in range(count):
        center = base + tangent * ((i - half_span) * spacing)
        if style == 'line':
            if line_from_cutline:
                start = center + normal * sa_depth
                if line_to_seamline:
                    end = center
                else:
                    end = start - normal * notch_len
            else:
                start = center
                end = center + normal * notch_len
            ax.plot([start[0], end[0]], [start[1], end[1]],
                    color='black', linewidth=1.2, solid_capstyle='butt', zorder=6)
            continue

        # Default standard: triangular notch with base on seamline.
        half_w = (notch_width * scale) / 2
        left = center - tangent * half_w
        right = center + tangent * half_w
        apex = center + normal * notch_len
        tri = mpatches.Polygon(
            [left, right, apex],
            closed=True,
            fill=False,
            edgecolor='black',
            linewidth=1.0,
            zorder=6,
        )
        ax.add_patch(tri)


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


def _polyline_length(pts):
    """Return total length of a polyline."""
    if len(pts) < 2:
        return 0.0
    diffs = np.diff(pts, axis=0)
    return float(np.sum(np.linalg.norm(diffs, axis=1)))


def _polyline_midpoint_tangent(pts):
    """Return midpoint and unit tangent at midpoint of a polyline."""
    pts = np.asarray(pts, dtype=float)
    if len(pts) < 2:
        return pts[0], np.array([1.0, 0.0])

    segs = np.diff(pts, axis=0)
    seg_lens = np.linalg.norm(segs, axis=1)
    total = float(np.sum(seg_lens))
    if total < 1e-12:
        tangent = segs[0]
        norm = np.linalg.norm(tangent)
        if norm < 1e-12:
            tangent = np.array([1.0, 0.0])
        else:
            tangent = tangent / norm
        return pts[0], tangent

    target = total / 2.0
    run = 0.0
    for i, seg_len in enumerate(seg_lens):
        next_run = run + seg_len
        if next_run >= target:
            if seg_len < 1e-12:
                return pts[i], np.array([1.0, 0.0])
            t = (target - run) / seg_len
            point = pts[i] + segs[i] * t
            tangent = segs[i] / seg_len
            return point, tangent
        run = next_run

    last = segs[-1]
    norm = np.linalg.norm(last)
    tangent = np.array([1.0, 0.0]) if norm < 1e-12 else last / norm
    return pts[-1], tangent


def _format_inch_fraction(value_in):
    """Format inches with 1/16\" precision as a mixed fraction."""
    frac = Fraction(value_in).limit_denominator(16)
    whole = frac.numerator // frac.denominator
    rem = Fraction(frac.numerator % frac.denominator, frac.denominator)
    if whole and rem:
        return f'{whole} {rem.numerator}/{rem.denominator}'
    if whole:
        return str(whole)
    return f'{rem.numerator}/{rem.denominator}'


def _format_sa_label(sa_cm, units, seam_label=None):
    """Format seam allowance text label."""
    value = abs(float(sa_cm))
    if value < 1e-9:
        return None
    if units == 'inch':
        base = f'SA {_format_inch_fraction(value / INCH)}"'
    else:
        base = f'SA {value:.1f} cm'
    if seam_label:
        return f'{base} | {seam_label}'
    return base


def _draw_seam_allowance_labels(ax, edges, scale, units='cm', fontsize=6):
    """Draw per-edge seam-allowance callouts near the cutline."""
    min_edge_len = 0.35 if units == 'inch' else 1.0
    placed = []
    for pts, sa_cm, seam_label in edges:
        pts = np.asarray(pts, dtype=float)
        if len(pts) < 2:
            continue
        label = _format_sa_label(sa_cm, units, seam_label=seam_label)
        if not label:
            continue
        if _polyline_length(pts) < min_edge_len:
            continue

        midpoint, tangent = _polyline_midpoint_tangent(pts)
        normal = np.array([-tangent[1], tangent[0]])
        normal_norm = np.linalg.norm(normal)
        if normal_norm < 1e-12:
            continue
        normal = normal / normal_norm
        offset = max(abs(sa_cm) * scale * 0.55, 0.12 if units == 'inch' else 0.3)
        position = midpoint + normal * offset

        # Skip labels that would stack nearly on top of one another.
        if any(np.linalg.norm(position - p) < (0.45 if units == 'inch' else 1.2) for p in placed):
            continue
        placed.append(position)

        angle = np.degrees(np.arctan2(tangent[1], tangent[0]))
        if angle > 90:
            angle -= 180
        if angle < -90:
            angle += 180
        ax.text(
            position[0], position[1], label,
            fontsize=fontsize, ha='center', va='center',
            rotation=angle, color='dimgray',
            bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.75),
            zorder=7,
        )


def draw_seam_allowance(ax, edges, scale=1.0, label_sas=False, units=None,
                        label_fontsize=6):
    """Draw a continuous seam-allowance boundary for an ordered list of edges.

    Edges must be ordered so that they form a continuous CW perimeter
    (each edge's last point ≈ the next edge's first point).  The function
    offsets each edge by its SA, then connects adjacent offset segments at
    their intersection (miter point) to produce one unbroken cutting line.

    Parameters
    ----------
    ax : matplotlib Axes
    edges : list of tuples
        *pts* is an (N,2) ndarray (already display-scaled),
        *sa_distance* is the seam allowance in **cm** (pre-scaling),
        and optional third value is plain-language seam text for labels.
    scale : float
        Display scale factor (e.g. 1/INCH for inch mode).
    label_sas : bool
        When True, place a seam-allowance text callout on each major edge.
    units : str | None
        ``'cm'`` or ``'inch'``. If omitted, inferred from ``scale``.
    label_fontsize : float
        Font size for SA callouts.
    """
    norm_edges = []
    for edge in edges:
        if len(edge) == 2:
            pts, sa_cm = edge
            seam_label = None
        elif len(edge) == 3:
            pts, sa_cm, seam_label = edge
        else:
            raise ValueError("Each seam allowance edge must be (pts, sa) or (pts, sa, label)")
        norm_edges.append((np.asarray(pts, dtype=float), float(sa_cm), seam_label))

    # Validate CW winding via signed area of edge start-points
    if len(edges) >= 3:
        verts = np.array([e[0][0] for e in norm_edges])
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
    for pts, sa_cm, _ in norm_edges:
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

    if label_sas:
        if units is None:
            units = 'inch' if np.isclose(scale, 1 / INCH, atol=1e-6) else 'cm'
        _draw_seam_allowance_labels(
            ax, norm_edges, scale=scale, units=units, fontsize=label_fontsize
        )


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
