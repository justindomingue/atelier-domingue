"""Lay plan — skyline-pack piece SVGs within a fabric width.

Works for any garment: reads individual piece SVGs, packs them into a
single composite SVG that represents the lay plan on fabric of a given
width.

Layout orientation (horizontal):
    x-axis = fabric length (grows rightward)
    y-axis = fabric width  (constrained, e.g. 31" for selvedge denim)

Pieces are placed WITHOUT rotation so their grainline (SVG x-axis,
waist-to-hem) naturally aligns with fabric length.  Selvedge-constrained
pieces are forced against the top/bottom edges of the layout so the
outseam sits on the selvedge.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np

# SVG namespace
SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

INKSCAPE_NS = 'http://www.inkscape.org/namespaces/inkscape'
ET.register_namespace('inkscape', INKSCAPE_NS)

from garment_programs.geometry import INCH as CM_PER_INCH
from garment_programs.plot_utils import SEAMLINE, CUTLINE

PTS_PER_INCH = 72.0


def _tag(name):
    """Namespaced SVG element tag."""
    return f'{{{SVG_NS}}}{name}'


def parse_svg_dimensions(svg_path):
    """Read SVG width/height attributes and return (w_inches, h_inches).

    Handles values in points (default for matplotlib) and plain numbers.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    w_str = root.get('width', '0')
    h_str = root.get('height', '0')

    def _to_inches(val):
        val = val.strip()
        if val.endswith('pt'):
            return float(val[:-2]) / PTS_PER_INCH
        elif val.endswith('in'):
            return float(val[:-2])
        elif val.endswith('px'):
            return float(val[:-2]) / 96.0
        else:
            return float(val) / PTS_PER_INCH

    return _to_inches(w_str), _to_inches(h_str)


def skyline_pack(pieces, fabric_width, gap=0.25, initial_skyline=None,
                 return_skyline=False):
    """Skyline packing — horizontal layout within a fixed fabric width.

    Pieces grow along x (fabric length) and are constrained to
    ``fabric_width`` on y (fabric width).

    Parameters
    ----------
    pieces : list of (name, grain_len, cross_w) or (..., edge)
        grain_len : extent along fabric length (x-axis, grows).
        cross_w   : extent across fabric (y-axis, must fit in fabric_width).
        edge      : 'top' | 'bottom' | None — forces piece against that
                    selvedge edge.
    fabric_width : float
        Available width in inches (y-axis constraint).
    gap : float
        Spacing between pieces in inches.
    initial_skyline : list of (y_start, y_end, x_right), optional
        Pre-existing skyline state (e.g. from a previous selvedge pack).
        Allows continuing packing into existing gaps.
    return_skyline : bool
        If True, return the skyline state as a third element.

    Returns
    -------
    positions : dict
        {name: (x, y)} placement positions (top-left corner, y-down).
    total_length : float
        Total fabric length needed (inches, x-extent).
    skyline : list, optional
        Final skyline state (only if ``return_skyline=True``).
    """
    if not pieces:
        if return_skyline:
            return {}, 0.0, initial_skyline or [(0.0, fabric_width, 0.0)]
        return {}, 0.0

    # Normalize to 4-tuples
    normalized = []
    for p in pieces:
        if len(p) == 3:
            normalized.append((*p, None))
        else:
            normalized.append(p)

    # Pair top/bottom constrained pieces that can nest within fabric width,
    # then free pieces (longest grain first).
    tops = sorted([p for p in normalized if p[3] == 'top'],
                  key=lambda p: p[1], reverse=True)   # longest grain first
    bottoms = sorted([p for p in normalized if p[3] == 'bottom'],
                     key=lambda p: p[1], reverse=True)
    free = sorted([p for p in normalized if not p[3]],
                  key=lambda p: p[1], reverse=True)

    # Greedily pair each top piece with a compatible bottom piece
    constrained = []
    used_bottoms = set()
    for t in tops:
        best_idx = None
        best_waste = float('inf')
        for i, b in enumerate(bottoms):
            if i in used_bottoms:
                continue
            if t[2] + b[2] <= fabric_width:
                # Prefer similar grain length (less wasted x-extent)
                waste = abs(t[1] - b[1])
                if waste < best_waste:
                    best_idx = i
                    best_waste = waste
        constrained.append(t)
        if best_idx is not None:
            constrained.append(bottoms[best_idx])
            used_bottoms.add(best_idx)
    for i, b in enumerate(bottoms):
        if i not in used_bottoms:
            constrained.append(b)
    ordered = constrained + free

    # Skyline: list of (y_start, y_end, x_right) segments.
    # Tracks how far right (x) pieces extend at each y position.
    skyline = initial_skyline or [(0.0, fabric_width, 0.0)]
    positions = {}

    for name, grain_len, cross_w, edge in ordered:
        if cross_w > fabric_width + 0.001:
            print(f"  Warning: '{name}' ({cross_w:.1f}\") wider than "
                  f"fabric ({fabric_width:.1f}\")")

        # Determine candidate y-positions based on edge constraint
        if edge == 'top':
            candidates = [0.0]
        elif edge == 'bottom':
            candidates = [max(0.0, fabric_width - cross_w)]
        else:
            candidates = [seg[0] for seg in skyline]

        best_x = float('inf')
        best_y = None

        for y_start in candidates:
            y_end = y_start + cross_w
            if y_end > fabric_width + 0.001:
                continue
            if y_start < -0.001:
                continue

            # Max x_right across spanned skyline segments
            max_x = 0.0
            for seg_y0, seg_y1, seg_x in skyline:
                if seg_y0 < y_end - 0.001 and seg_y1 > y_start + 0.001:
                    max_x = max(max_x, seg_x)

            if max_x < best_x:
                best_x = max_x
                best_y = y_start

        if best_y is None:
            best_y = 0.0
            best_x = max(s[2] for s in skyline)

        # Place piece — no extra gap against selvedge edges
        px = best_x + gap / 2
        if edge in ('top', 'bottom'):
            py = best_y
        else:
            py = best_y + gap / 2
        positions[name] = (px, py)

        # Update skyline
        new_right = best_x + grain_len + gap
        piece_top = best_y
        piece_bottom = best_y + cross_w + (gap / 2 if edge else gap)

        new_skyline = []
        for seg_y0, seg_y1, seg_x in skyline:
            if seg_y1 <= piece_top or seg_y0 >= piece_bottom:
                new_skyline.append((seg_y0, seg_y1, seg_x))
            else:
                if seg_y0 < piece_top:
                    new_skyline.append((seg_y0, piece_top, seg_x))
                if seg_y1 > piece_bottom:
                    new_skyline.append((piece_bottom, seg_y1, seg_x))

        new_skyline.append((piece_top, piece_bottom, new_right))
        skyline = sorted(new_skyline, key=lambda s: s[0])

    total_length = max(s[2] for s in skyline)
    if return_skyline:
        return positions, total_length, skyline
    return positions, total_length


# ---------------------------------------------------------------------------
# Polygon extraction from piece SVGs
# ---------------------------------------------------------------------------

def _parse_svg_path_data(d_string, curve_steps=10):
    """Parse an SVG path ``d`` attribute into polyline vertices.

    Supports M/L/H/V/C/Q/Z path commands (absolute + relative) and
    approximates Bezier segments into line segments.

    Returns
    -------
    vertices : list[(float, float)]
    closed : bool
        True when a closepath command is present or start/end coincide.
    """
    token_re = re.compile(r'[MmLlHhVvCcQqZz]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')
    tokens = token_re.findall(d_string)
    if not tokens:
        return [], False

    def _is_cmd(tok):
        return len(tok) == 1 and tok.isalpha()

    def _as_float(idx):
        return float(tokens[idx])

    i = 0
    cmd = None
    current = np.array([0.0, 0.0], dtype=float)
    subpath_start = None
    vertices = []
    closed = False

    while i < len(tokens):
        if _is_cmd(tokens[i]):
            cmd = tokens[i]
            i += 1
        if cmd is None:
            break

        abs_cmd = cmd.upper()
        rel = cmd.islower()

        if abs_cmd == 'M':
            # First pair is move-to; subsequent pairs are implicit line-to.
            if i + 1 >= len(tokens) or _is_cmd(tokens[i]):
                continue
            x = _as_float(i)
            y = _as_float(i + 1)
            i += 2
            target = np.array([x, y], dtype=float)
            if rel:
                target = current + target
            current = target
            subpath_start = current.copy()
            vertices.append((current[0], current[1]))
            cmd = 'l' if rel else 'L'
            continue

        if abs_cmd == 'Z':
            if subpath_start is not None:
                current = subpath_start.copy()
                vertices.append((current[0], current[1]))
                closed = True
            continue

        if abs_cmd == 'L':
            while i + 1 < len(tokens) and not _is_cmd(tokens[i]):
                x = _as_float(i)
                y = _as_float(i + 1)
                i += 2
                target = np.array([x, y], dtype=float)
                if rel:
                    target = current + target
                current = target
                vertices.append((current[0], current[1]))
            continue

        if abs_cmd == 'H':
            while i < len(tokens) and not _is_cmd(tokens[i]):
                x = _as_float(i)
                i += 1
                target = current.copy()
                target[0] = current[0] + x if rel else x
                current = target
                vertices.append((current[0], current[1]))
            continue

        if abs_cmd == 'V':
            while i < len(tokens) and not _is_cmd(tokens[i]):
                y = _as_float(i)
                i += 1
                target = current.copy()
                target[1] = current[1] + y if rel else y
                current = target
                vertices.append((current[0], current[1]))
            continue

        if abs_cmd == 'Q':
            while i + 3 < len(tokens) and not _is_cmd(tokens[i]):
                qx = _as_float(i)
                qy = _as_float(i + 1)
                x = _as_float(i + 2)
                y = _as_float(i + 3)
                i += 4
                c = np.array([qx, qy], dtype=float)
                p = np.array([x, y], dtype=float)
                if rel:
                    c = current + c
                    p = current + p
                p0 = current.copy()
                for step in range(1, curve_steps + 1):
                    t = step / curve_steps
                    pt = (1 - t) ** 2 * p0 + 2 * (1 - t) * t * c + t ** 2 * p
                    vertices.append((pt[0], pt[1]))
                current = p
            continue

        if abs_cmd == 'C':
            while i + 5 < len(tokens) and not _is_cmd(tokens[i]):
                c1x = _as_float(i)
                c1y = _as_float(i + 1)
                c2x = _as_float(i + 2)
                c2y = _as_float(i + 3)
                x = _as_float(i + 4)
                y = _as_float(i + 5)
                i += 6
                c1 = np.array([c1x, c1y], dtype=float)
                c2 = np.array([c2x, c2y], dtype=float)
                p = np.array([x, y], dtype=float)
                if rel:
                    c1 = current + c1
                    c2 = current + c2
                    p = current + p
                p0 = current.copy()
                for step in range(1, curve_steps + 1):
                    t = step / curve_steps
                    pt = (
                        (1 - t) ** 3 * p0
                        + 3 * (1 - t) ** 2 * t * c1
                        + 3 * (1 - t) * t ** 2 * c2
                        + t ** 3 * p
                    )
                    vertices.append((pt[0], pt[1]))
                current = p
            continue

        # Unsupported command in token stream: skip one token to avoid stalling.
        if i < len(tokens):
            i += 1

    if not closed and len(vertices) >= 3:
        p0 = np.array(vertices[0], dtype=float)
        p1 = np.array(vertices[-1], dtype=float)
        closed = np.linalg.norm(p0 - p1) < 1e-3
    return vertices, closed


def _shoelace_area(pts):
    """Signed area of a polygon via the shoelace formula."""
    n = len(pts)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += pts[i][0] * pts[j][1]
        area -= pts[j][0] * pts[i][1]
    return area / 2.0


def _extract_outline_polygon(svg_path):
    """Extract the cut-boundary polygon from a piece SVG.

    Finds all ``<path>`` elements inside the drawing area (``g#axes_1``),
    parses their M/L vertices, and selects the path with the largest
    absolute area — this is the seam-allowance or cut outline.

    Returns
    -------
    polygon : list of (float, float)
        Vertices in inches, normalized to origin.  If no suitable closed
        path is found, falls back to a bounding-box rectangle.
    pad_x : float
        Horizontal offset from SVG origin to polygon min-x, in inches.
    pad_y : float
        Vertical offset from SVG origin to polygon min-y, in inches.
    """
    sidecar = Path(svg_path).with_suffix('.outline.json')
    if sidecar.exists():
        try:
            payload = json.loads(sidecar.read_text())
            poly = payload.get('polygon', [])
            if isinstance(poly, list) and len(poly) >= 3:
                points = [(float(p[0]), float(p[1])) for p in poly if len(p) == 2]
                if len(points) >= 3:
                    return (
                        points,
                        float(payload.get('pad_x', 0.0)),
                        float(payload.get('pad_y', 0.0)),
                    )
        except (json.JSONDecodeError, ValueError, KeyError, OSError):
            # Invalid sidecar should not break layout generation.
            pass

    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns = {'svg': SVG_NS}

    # Get SVG bounding box for fallback
    w_in, h_in = parse_svg_dimensions(svg_path)

    # Search inside axes_1 for drawing paths (not font glyphs in <defs>)
    axes = root.find(f'.//{_tag("g")}[@id="axes_1"]')
    if axes is None:
        # Fallback: bounding-box rectangle
        return [(0, 0), (w_in, 0), (w_in, h_in), (0, h_in)], 0.0, 0.0

    best_poly = None
    best_area = 0.0

    for g in axes.iter(_tag('g')):
        gid = g.get('id', '')
        if not gid.startswith('line2d_'):
            continue
        for path_el in g.findall(_tag('path')):
            style = path_el.get('style', '')
            if not style:
                continue  # skip glyph definitions (no inline style)
            d = path_el.get('d', '')
            verts, closed = _parse_svg_path_data(d)
            if len(verts) < 3 or not closed:
                continue
            area = abs(_shoelace_area(verts))
            if area > best_area:
                best_area = area
                best_poly = verts

    # Minimum area threshold: must be at least 1% of bounding box area (in pts²)
    bbox_area_pts = (w_in * PTS_PER_INCH) * (h_in * PTS_PER_INCH)
    if best_poly is None or best_area < bbox_area_pts * 0.01:
        # Fallback to bounding-box rectangle
        return [(0, 0), (w_in, 0), (w_in, h_in), (0, h_in)], 0.0, 0.0

    # Normalize to origin and convert pts → inches
    min_x = min(p[0] for p in best_poly)
    min_y = min(p[1] for p in best_poly)
    poly_inches = [
        ((p[0] - min_x) / PTS_PER_INCH, (p[1] - min_y) / PTS_PER_INCH)
        for p in best_poly
    ]
    pad_x = min_x / PTS_PER_INCH
    pad_y = min_y / PTS_PER_INCH

    return poly_inches, pad_x, pad_y


def _transform_polygon(polygon, transform, w_inches, h_inches):
    """Apply a layout transform to polygon vertices.

    Mirrors the SVG embedding transforms used in generate_lay_plan().

    Parameters
    ----------
    polygon : list of (float, float)
        Vertices in the piece's local coordinate space (inches).
    transform : str
        'none', 'ccw' (90° counter-clockwise), or 'flip_v' (vertical mirror).
    w_inches, h_inches : float
        Original SVG dimensions in inches (before transform).
    """
    if transform == 'none':
        return polygon

    if transform == 'ccw':
        # 90° CCW rotation: (x, y) → (y, w - x)
        # SVG height becomes layout width, SVG width becomes layout height.
        # After rotation, the piece's x-extent = h_inches, y-extent = w_inches.
        rotated = [(y, w_inches - x) for x, y in polygon]
        # Re-normalize to origin
        min_x = min(p[0] for p in rotated)
        min_y = min(p[1] for p in rotated)
        return [(p[0] - min_x, p[1] - min_y) for p in rotated]

    if transform == 'cw':
        # 90° CW rotation: (x, y) → (h - y, x)
        rotated = [(h_inches - y, x) for x, y in polygon]
        min_x = min(p[0] for p in rotated)
        min_y = min(p[1] for p in rotated)
        return [(p[0] - min_x, p[1] - min_y) for p in rotated]

    if transform == 'flip_h':
        # Horizontal mirror: (x, y) → (w - x, y)
        flipped = [(w_inches - x, y) for x, y in polygon]
        min_x = min(p[0] for p in flipped)
        return [(p[0] - min_x, p[1]) for p in flipped]

    if transform == 'ccw_flip_h':
        # CCW rotation + horizontal flip: (x, y) → (h - y, w - x)
        transformed = [(h_inches - y, w_inches - x) for x, y in polygon]
        min_x = min(p[0] for p in transformed)
        min_y = min(p[1] for p in transformed)
        return [(p[0] - min_x, p[1] - min_y) for p in transformed]

    if transform == 'ccw_flip_v':
        # CCW rotation + vertical flip: (x, y) → (y, x)
        transformed = [(y, x) for x, y in polygon]
        min_x = min(p[0] for p in transformed)
        min_y = min(p[1] for p in transformed)
        return [(p[0] - min_x, p[1] - min_y) for p in transformed]

    if transform == 'flip_v':
        # Vertical mirror: (x, y) → (x, h - y)
        flipped = [(x, h_inches - y) for x, y in polygon]
        min_y = min(p[1] for p in flipped)
        return [(p[0], p[1] - min_y) for p in flipped]

    return polygon


# ---------------------------------------------------------------------------
# Void filling — place free pieces in curved voids within selvedge zone
# ---------------------------------------------------------------------------

def _polygon_y_range_at_x(polygon, x):
    """Find the y-extent of a closed polygon at a given x coordinate.

    Returns (y_min, y_max) or None if x is outside the polygon's x-range.
    Works by finding all edge–vertical-line intersections and returning
    the outermost y values.
    """
    intersections = []
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        if abs(x2 - x1) < 1e-10:
            # Vertical edge — include both endpoints if at this x
            if abs(x - x1) < 0.05:
                intersections.extend([y1, y2])
            continue
        t = (x - x1) / (x2 - x1)
        if -0.001 <= t <= 1.001:
            intersections.append(y1 + t * (y2 - y1))
    if len(intersections) >= 2:
        return min(intersections), max(intersections)
    return None


def _intersect_ranges(ranges_a, ranges_b):
    """Compute intersection of two sorted lists of (lo, hi) ranges."""
    result = []
    i = j = 0
    while i < len(ranges_a) and j < len(ranges_b):
        lo = max(ranges_a[i][0], ranges_b[j][0])
        hi = min(ranges_a[i][1], ranges_b[j][1])
        if lo < hi - 0.01:
            result.append((lo, hi))
        if ranges_a[i][1] < ranges_b[j][1]:
            i += 1
        else:
            j += 1
    return result


def _void_fill(selvedge_pieces, sel_positions, free_pieces, fabric_width,
               gap=0.25, step=0.5):
    """Place free pieces into curved voids within the selvedge zone.

    Scans the selvedge region with a polygon-aware profile: at each
    x-column, compute the y-ranges actually occupied by selvedge piece
    polygons (not bounding boxes).  The void is the complement within
    [0, fabric_width].  Free pieces are greedily placed (largest area
    first) into the widest contiguous rectangular voids.

    Parameters
    ----------
    selvedge_pieces : list of (name, grain_len, cross_w, edge, poly, pad_x, pad_y)
    sel_positions : dict  {name: (svg_x, svg_y)}
    free_pieces : list of (name, grain_len, cross_w, edge, poly, pad_x, pad_y)
    fabric_width : float
    gap : float
    step : float
        X-discretization step in inches.

    Returns
    -------
    placed : dict  {name: (svg_x, svg_y)}
    remaining : list of unplaced free piece tuples
    """
    # Build absolute polygons for selvedge pieces
    abs_polys = []
    for name, gl, cw, edge, poly, px, py in selvedge_pieces:
        if name not in sel_positions:
            continue
        sx, sy = sel_positions[name]
        abs_polys.append([(vx + sx + px, vy + sy + py) for vx, vy in poly])

    if not abs_polys:
        return {}, list(free_pieces)

    sel_x_max = max(max(vx for vx, vy in p) for p in abs_polys)

    # Build void profile: at each x-column, available (y_lo, y_hi) ranges
    x_cols = []
    x = 0.0
    while x <= sel_x_max:
        x_cols.append(x)
        x += step

    void_profile = {}
    for xc in x_cols:
        occupied = []
        for poly in abs_polys:
            yr = _polygon_y_range_at_x(poly, xc)
            if yr:
                occupied.append((max(0, yr[0] - gap / 2),
                                 min(fabric_width, yr[1] + gap / 2)))
        occupied.sort()
        # Merge overlapping occupied ranges
        merged = []
        for ylo, yhi in occupied:
            if merged and ylo <= merged[-1][1] + 0.01:
                merged[-1] = (merged[-1][0], max(merged[-1][1], yhi))
            else:
                merged.append((ylo, yhi))
        # Void = complement within [0, fabric_width]
        voids = []
        prev = 0.0
        for ylo, yhi in merged:
            if ylo > prev + 0.01:
                voids.append((prev, ylo))
            prev = max(prev, yhi)
        if prev < fabric_width - 0.01:
            voids.append((prev, fabric_width))
        void_profile[xc] = voids

    # Sort free pieces by area (largest first) for greedy placement
    remaining = sorted(free_pieces, key=lambda p: p[1] * p[2], reverse=True)
    placed = {}

    for piece in remaining[:]:
        name, gl, cw, edge, poly, px, py = piece
        best_pos = None

        for si in range(len(x_cols)):
            sx = x_cols[si]
            if sx + gl > sel_x_max + 0.01:
                break

            # Find common void across all x-columns spanned by [sx, sx+gl]
            common = list(void_profile.get(x_cols[si], []))
            for ci in range(si + 1, len(x_cols)):
                if x_cols[ci] > sx + gl:
                    break
                common = _intersect_ranges(common,
                                           void_profile.get(x_cols[ci], []))
                if not common:
                    break

            # Check if any common void fits the SVG bounding box
            for vy0, vy1 in common:
                if vy1 - vy0 >= cw + gap:
                    svg_x = sx + gap / 2
                    svg_y = vy0 + gap / 2
                    if svg_x >= -0.01 and svg_y >= -0.01:
                        best_pos = (svg_x, svg_y)
                        break
            if best_pos:
                break

        if best_pos:
            placed[name] = best_pos

            # Block this SVG bounding box in the void profile
            bx, by = best_pos
            for ci, xc in enumerate(x_cols):
                if xc < bx - gap - 0.01 or xc > bx + gl + 0.01:
                    continue
                blocked = (max(0, by - gap / 2),
                           min(fabric_width, by + cw + gap / 2))
                new_voids = []
                for v0, v1 in void_profile[xc]:
                    if blocked[1] <= v0 + 0.01 or blocked[0] >= v1 - 0.01:
                        new_voids.append((v0, v1))
                    else:
                        if v0 < blocked[0] - 0.01:
                            new_voids.append((v0, blocked[0]))
                        if v1 > blocked[1] + 0.01:
                            new_voids.append((blocked[1], v1))
                void_profile[xc] = new_voids

            remaining.remove(piece)

    return placed, remaining


def _offset_nest_selvedge(top_pieces, bot_pieces, fabric_width, gap=0.25,
                          step=0.5):
    """Try to offset-nest top/bottom selvedge piece pairs.

    For each (top, bottom) pair whose bounding-box cross widths exceed
    fabric_width, find the minimum lengthwise (x) offset where their actual
    polygon shapes fit within fabric_width at every x-column.

    Both selvedge pieces taper from wide (seat) to narrow (hem), so a
    staggered placement lets the narrow end of one share fabric width
    with the wide end of the other.

    Parameters
    ----------
    top_pieces : list of (name, grain_len, cross_w, edge, poly, pad_x, pad_y)
    bot_pieces : list of (name, grain_len, cross_w, edge, poly, pad_x, pad_y)
    fabric_width : float
    gap : float
        Minimum clearance between pieces in inches.
    step : float
        X-discretization step for offset scanning and column checking.

    Returns
    -------
    nested_positions : dict  {name: (svg_x, svg_y)}
    remaining_tops : list of unpaired top piece tuples
    remaining_bots : list of unpaired bottom piece tuples
    """
    # Build candidate pairs, prioritising cross-type main-panel pairings
    # (front+back) over same-type (back+back) or accessory pairs.
    # This ensures the lay plan always pairs front and back side-by-side
    # on the fabric width, using offset nesting when they don't fit.
    def _stem(name):
        for sfx in ('_L', '_R', '_1', '_2', '_3', '_4'):
            if name.endswith(sfx):
                return name[:-len(sfx)]
        return name

    main_threshold = fabric_width * 0.3   # e.g. 9.3" for 31" fabric

    candidates = []
    for ti, top in enumerate(top_pieces):
        for bi, bot in enumerate(bot_pieces):
            excess = top[2] + bot[2] - fabric_width
            # Priority: 0 = cross-pair of two main panels,
            #           1 = same-family or involves accessory piece
            is_cross_main = (
                _stem(top[0]) != _stem(bot[0])
                and top[2] > main_threshold
                and bot[2] > main_threshold
            )
            priority = 0 if is_cross_main else 1
            candidates.append((priority, excess, ti, bi))
    candidates.sort()  # (priority ASC, excess ASC)

    nested_positions = {}
    used_tops = set()
    used_bots = set()
    # Track cumulative x-offset so successive pairs don't overlap
    pair_x_cursor = 0.0

    for _priority, _excess, ti, bi in candidates:
        if ti in used_tops or bi in used_bots:
            continue
        top = top_pieces[ti]
        bot = bot_pieces[bi]
        # Only offset-nest main panels, not accessories (waistband, cinch)
        if top[2] < main_threshold or bot[2] < main_threshold:
            continue
        t_name, t_gl, t_cw, _, t_poly, t_px, t_py = top
        b_name, b_gl, b_cw, _, b_poly, b_px, b_py = bot

        # "Unflip" the bottom polygon to original orientation
        # (outseam at y=0) so y_max gives the cross-grain extent
        # from the selvedge.
        b_poly_h = max(p[1] for p in b_poly) if b_poly else 0
        b_poly_orig = [(x, b_poly_h - y) for x, y in b_poly]

        t_poly_xmax = max(p[0] for p in t_poly) if t_poly else t_gl
        b_poly_xmax = (max(p[0] for p in b_poly_orig)
                       if b_poly_orig else b_gl)

        # Scan offsets from 0 upward
        max_offset = max(t_poly_xmax, b_poly_xmax)
        n_steps = int(max_offset / step) + 2

        best_offset = None
        for oi in range(n_steps):
            offset = oi * step

            # Overlap region: x-columns where both pieces are present
            overlap_start = offset
            overlap_end = min(t_poly_xmax, offset + b_poly_xmax)

            if overlap_start >= overlap_end:
                # No overlap — pieces are separate along x
                best_offset = offset
                break

            fits = True
            xc = overlap_start
            while xc <= overlap_end + 0.001:
                t_yr = _polygon_y_range_at_x(t_poly, xc)
                b_yr = _polygon_y_range_at_x(b_poly_orig, xc - offset)

                t_extent = t_yr[1] if t_yr else 0.0
                b_extent = b_yr[1] if b_yr else 0.0

                if t_extent + b_extent + gap > fabric_width:
                    fits = False
                    break

                xc += step

            if fits:
                best_offset = offset
                break

        if best_offset is not None:
            # Only nest if it actually saves fabric vs sequential
            sequential_len = t_gl + b_gl + gap
            nested_len = max(t_gl, best_offset + b_gl) + gap
            savings = sequential_len - nested_len

            if savings > step:
                nested_positions[t_name] = (pair_x_cursor + gap / 2, 0.0)
                nested_positions[b_name] = (pair_x_cursor + best_offset
                                            + gap / 2,
                                            fabric_width - b_cw)
                used_tops.add(ti)
                used_bots.add(bi)
                pair_x_cursor += nested_len
                print(f"    Offset nest: {t_name} + {b_name} "
                      f"offset={best_offset:.1f}\" "
                      f"(saves {savings:.1f}\" lengthwise)")

    remaining_tops = [t for i, t in enumerate(top_pieces)
                      if i not in used_tops]
    remaining_bots = [b for i, b in enumerate(bot_pieces)
                      if i not in used_bots]

    return nested_positions, remaining_tops, remaining_bots


def _select_layout_candidate(candidates, preferred_label=None):
    """Choose a layout candidate by label preference or shortest length."""
    if preferred_label:
        for candidate in candidates:
            if candidate[4] == preferred_label:
                return candidate
    return min(candidates, key=lambda c: (c[0], c[1]))


def polygon_nest(pieces, fabric_width, gap=0.25, prefer_offset_nest=True):
    """Polygon-aware nesting with void filling and skyline fallback.

    Strategy:
    1. Always compute baseline via skyline_pack (handles selvedge pinning
       and interleaving perfectly).
    2. Place selvedge pieces via skyline, then run a void-fill pass to
       tuck free pieces into the curved voids within selvedge bounding boxes.
    3. Remaining free pieces go through skyline continuation.
    4. If spyrrow is available, also try polygon nesting as an alternative.
    5. By default, prefer offset-nested front/back panel pairing when available
       (matches typical cutting workflow). If disabled, choose the shortest
       total-length strategy.

    Same return signature as skyline_pack() plus a ``use_polygons`` flag.

    Parameters
    ----------
    pieces : list of tuples
        (name, grain_len, cross_w, edge, polygon, pad_x, pad_y)
    fabric_width : float
    gap : float
    prefer_offset_nest : bool
        When True, prefer the offset-nest strategy if available, even when
        another strategy is slightly shorter.

    Returns
    -------
    positions : dict  {name: (x, y)}
    total_length : float
    use_polygons : bool
        True if polygon nesting was used (caller should strip backgrounds).
    """
    if not pieces:
        return {}, 0.0, False

    # --- Baseline: skyline_pack for ALL pieces (interleaved) ---
    all_input = [(name, gl, cw, edge)
                 for name, gl, cw, edge, _, _, _ in pieces]
    sky_positions, sky_length = skyline_pack(all_input, fabric_width, gap=gap)

    selvedge = [p for p in pieces if p[3] in ('top', 'bottom')]
    free = [p for p in pieces if p[3] not in ('top', 'bottom')]

    if not free:
        return sky_positions, sky_length, False

    # --- Selvedge skyline with state export ---
    sel_input = [(name, gl, cw, edge)
                 for name, gl, cw, edge, _, _, _ in selvedge]
    sel_positions, sel_length, sel_skyline = skyline_pack(
        sel_input, fabric_width, gap=gap, return_skyline=True)

    # --- Strategy A: Void fill + skyline continuation ---
    void_placed, remaining = _void_fill(
        selvedge, sel_positions, free, fabric_width, gap=gap)

    if void_placed:
        print(f"    Void fill: placed {len(void_placed)} piece(s) "
              f"in selvedge voids")

    # Update skyline to account for void-filled pieces so that
    # remaining pieces don't overlap them.
    vf_skyline = list(sel_skyline)
    for vname, (vx, vy) in void_placed.items():
        vpiece = next(p for p in free if p[0] == vname)
        vgl, vcw = vpiece[1], vpiece[2]
        new_right = vx + vgl + gap
        ptop = vy
        pbot = vy + vcw + gap
        new_sky = []
        for sy0, sy1, sx in vf_skyline:
            if sy1 <= ptop or sy0 >= pbot:
                new_sky.append((sy0, sy1, sx))
            else:
                if sy0 < ptop:
                    new_sky.append((sy0, ptop, sx))
                if sy1 > pbot:
                    new_sky.append((pbot, sy1, sx))
        new_sky.append((ptop, pbot, new_right))
        vf_skyline = sorted(new_sky, key=lambda s: s[0])

    remaining_input = [(name, gl, cw, None)
                       for name, gl, cw, _, _, _, _ in remaining]
    if remaining_input:
        remaining_sky_pos, vf_total = skyline_pack(
            remaining_input, fabric_width, gap=gap,
            initial_skyline=vf_skyline)
    else:
        # All free pieces void-filled — total length is the skyline extent
        remaining_sky_pos = {}
        vf_total = max(s[2] for s in vf_skyline)

    vf_positions = {}
    vf_positions.update(sel_positions)
    vf_positions.update(void_placed)
    vf_positions.update(remaining_sky_pos)

    # --- Strategy B: Pure skyline continuation (no void fill) ---
    all_free_input = [(name, gl, cw, None)
                      for name, gl, cw, _, _, _, _ in free]
    all_free_sky_pos, sky_cont_total = skyline_pack(
        all_free_input, fabric_width, gap=gap,
        initial_skyline=sel_skyline)

    sky_cont_positions = {}
    sky_cont_positions.update(sel_positions)
    sky_cont_positions.update(all_free_sky_pos)

    # --- Strategy C: Offset nesting for too-wide selvedge pairs ---
    # For selvedge pairs whose bounding-box widths exceed fabric_width,
    # try offset nesting using actual polygon shapes.
    sel_tops = [p for p in selvedge if p[3] == 'top']
    sel_bots = [p for p in selvedge if p[3] == 'bottom']

    has_wide_pair = any(
        t[2] + b[2] > fabric_width
        for t in sel_tops for b in sel_bots
    )

    c_result = None
    if has_wide_pair:
        offset_pos, rem_tops, rem_bots = _offset_nest_selvedge(
            sel_tops, sel_bots, fabric_width, gap=gap)

        if offset_pos:
            # Build skyline from offset-nested pieces
            c_skyline = [(0.0, fabric_width, 0.0)]
            for oname in offset_pos:
                ox, oy = offset_pos[oname]
                opiece = next(p for p in selvedge if p[0] == oname)
                ogl, ocw, oedge = opiece[1], opiece[2], opiece[3]
                best_x = ox - gap / 2
                new_right = best_x + ogl + gap
                ptop = oy
                pbot = oy + ocw + (gap / 2
                                    if oedge in ('top', 'bottom') else gap)
                new_sky = []
                for sy0, sy1, sx in c_skyline:
                    if sy1 <= ptop or sy0 >= pbot:
                        new_sky.append((sy0, sy1, sx))
                    else:
                        if sy0 < ptop:
                            new_sky.append((sy0, ptop, sx))
                        if sy1 > pbot:
                            new_sky.append((pbot, sy1, sx))
                new_sky.append((ptop, pbot, new_right))
                c_skyline = sorted(new_sky, key=lambda s: s[0])

            # Remaining selvedge pieces via skyline
            rem_sel = rem_tops + rem_bots
            rem_sel_input = [(n, gl, cw, edge)
                             for n, gl, cw, edge, _, _, _ in rem_sel]
            if rem_sel_input:
                rem_sel_pos, _, c_skyline = skyline_pack(
                    rem_sel_input, fabric_width, gap=gap,
                    initial_skyline=c_skyline, return_skyline=True)
            else:
                rem_sel_pos = {}

            # Combine all selvedge positions for void filling
            all_sel_pos_c = {}
            all_sel_pos_c.update(offset_pos)
            all_sel_pos_c.update(rem_sel_pos)

            # Void fill free pieces into selvedge voids, then skyline
            # the remainder — this combines offset-nest savings with
            # void-fill savings.
            c_void_placed, c_remaining = _void_fill(
                selvedge, all_sel_pos_c, free, fabric_width, gap=gap)

            if c_void_placed:
                print(f"    Offset + void fill: placed {len(c_void_placed)} "
                      f"piece(s) in selvedge voids")

            # Update skyline for void-filled pieces
            cv_skyline = list(c_skyline)
            for vn, (vx, vy) in c_void_placed.items():
                vp = next(p for p in free if p[0] == vn)
                v_right = vx + vp[1] + gap
                vtop, vbot = vy, vy + vp[2] + gap
                new_sky = []
                for sy0, sy1, sx in cv_skyline:
                    if sy1 <= vtop or sy0 >= vbot:
                        new_sky.append((sy0, sy1, sx))
                    else:
                        if sy0 < vtop:
                            new_sky.append((sy0, vtop, sx))
                        if sy1 > vbot:
                            new_sky.append((vbot, sy1, sx))
                new_sky.append((vtop, vbot, v_right))
                cv_skyline = sorted(new_sky, key=lambda s: s[0])

            # Skyline-pack remaining free pieces
            c_rem_input = [(n, gl, cw, None)
                           for n, gl, cw, _, _, _, _ in c_remaining]
            if c_rem_input:
                free_pos_c, c_total = skyline_pack(
                    c_rem_input, fabric_width, gap=gap,
                    initial_skyline=cv_skyline)
            else:
                free_pos_c = {}
                c_total = max(s[2] for s in cv_skyline)

            c_positions = {}
            c_positions.update(offset_pos)
            c_positions.update(rem_sel_pos)
            c_positions.update(c_void_placed)
            c_positions.update(free_pos_c)
            c_result = (c_total, c_positions)

    # --- Pick the best strategy ---
    # Offset nesting yields a cutter-friendly pairing of front/back panels;
    # keep it as the default preference, but allow shortest-length selection.
    candidates = [
        (vf_total, 0, vf_positions, True, "void fill + skyline"),
        (sky_length, 1, sky_positions, False, "baseline skyline"),
        (sky_cont_total, 2, sky_cont_positions, False, "skyline continuation"),
    ]
    if c_result is not None:
        candidates.append(
            (c_result[0], 3, c_result[1], False, "offset nest + skyline")
        )

    preferred = "offset nest + skyline" if c_result is not None and prefer_offset_nest else None
    best_total, _, best_pos, best_poly, best_label = _select_layout_candidate(
        candidates, preferred_label=preferred
    )

    # Report
    others = [(t, l) for t, _, _, _, l in candidates if l != best_label]
    other_str = ", ".join(f"{l}={t:.1f}\"" for t, l in others)
    print(f"  Best: {best_label} = {best_total:.1f}\" ({other_str})")

    return best_pos, best_total, best_poly


# ---------------------------------------------------------------------------
# Layout helper — expand piece SVGs and run nesting for a single fabric
# ---------------------------------------------------------------------------

def _layout_fabric(svg_paths, fabric_width, gap=0.25,
                   prefer_panel_pairing=True):
    """Expand piece SVGs and pack them onto a fabric width.

    Parameters
    ----------
    svg_paths : list of (svg_file_path, cut_count, selvedge_edge, grain_axis)
    fabric_width : float
    gap : float
    prefer_panel_pairing : bool
        If True, prefer matched front/back panel pairing when offset nesting
        is available.

    Returns
    -------
    pieces : list of (name, grain_len, cross_w, svg_path, transform, edge)
        Expanded piece list with transforms applied.
    positions : dict  {name: (x, y)}
    total_length : float
    """
    # --- Parse dimensions and build piece list ---
    # Each entry: (unique_name, grain_len, cross_w, svg_path, transform, edge)
    #   grain_len : extent along fabric length (layout x-axis)
    #   cross_w   : extent across fabric (layout y-axis)
    #   transform : 'none' | 'cw' | 'flip_v'
    #               'cw'     = 90° CW rotation (for grain_axis='y' pieces)
    #               'flip_v' = vertical mirror (for second selvedge copy)
    #   edge      : 'top' | 'bottom' | None
    pieces = []
    for entry in svg_paths:
        svg_path = entry[0]
        cut_count = entry[1]
        selvedge_edge = entry[2] if len(entry) > 2 else None
        grain_axis = entry[3] if len(entry) > 3 else 'x'

        w_orig, h_orig = parse_svg_dimensions(svg_path)
        name = Path(svg_path).stem

        # Determine layout dimensions based on grain axis.
        # grain_axis='x': grain already along SVG x → no rotation needed.
        # grain_axis='y': grain along SVG y → rotate 90° CCW so y maps to x
        #                 (top of piece faces left in layout).
        if grain_axis == 'y':
            grain_len = h_orig   # SVG height becomes layout x (grain)
            cross_w = w_orig     # SVG width becomes layout y (cross-grain)
            base_transform = 'ccw'
        else:
            grain_len = w_orig   # SVG width = grain = layout x
            cross_w = h_orig     # SVG height = cross-grain = layout y
            base_transform = 'none'

        if cross_w + gap > fabric_width:
            print(f"  Warning: '{name}' cross-grain ({cross_w:.1f}\") "
                  f"exceeds fabric width ({fabric_width:.1f}\")")

        if selvedge_edge:
            # Selvedge piece — for 'top' pieces the outseam is at SVG top (y=0);
            # for 'bottom' pieces the selvedge edge is at SVG bottom.
            # First copy: placed at the configured edge, no flip.
            # Second copy: flipped vertically for the opposite edge.
            if cut_count >= 2:
                pieces.append((f'{name}_L', grain_len, cross_w,
                               svg_path, base_transform, 'top'))
                pieces.append((f'{name}_R', grain_len, cross_w,
                               svg_path, 'flip_v', 'bottom'))
                for i in range(2, cut_count):
                    pieces.append((f'{name}_{i+1}', grain_len, cross_w,
                                   svg_path, base_transform, None))
            else:
                pieces.append((name, grain_len, cross_w,
                               svg_path, base_transform, selvedge_edge))
        else:
            if cut_count <= 1:
                pieces.append((name, grain_len, cross_w,
                               svg_path, base_transform, None))
            else:
                # Mirror transform for the second copy (vertical flip):
                #   grain_axis='x' (none) → flip_v
                #   grain_axis='y' (ccw)  → ccw_flip_v (rotate then flip)
                mirror_transform = 'flip_v' if base_transform == 'none' else 'ccw_flip_v'
                pieces.append((f'{name}_1', grain_len, cross_w,
                               svg_path, base_transform, None))
                pieces.append((f'{name}_2', grain_len, cross_w,
                               svg_path, mirror_transform, None))
                for i in range(2, cut_count):
                    pieces.append((f'{name}_{i+1}', grain_len, cross_w,
                                   svg_path, base_transform, None))

    if not pieces:
        return [], {}, 0.0

    # --- Extract polygons and pack ---
    pieces_with_polys = []
    for name, grain_len, cross_w, svg_path, transform, edge in pieces:
        poly, pad_x, pad_y = _extract_outline_polygon(svg_path)
        svg_w, svg_h = parse_svg_dimensions(svg_path)

        # Transform padding to layout space (matching the polygon transform).
        # pad_x/pad_y are the polygon's offset from SVG origin in SVG coords.
        # After rotation, the offset within the layout box changes.
        if transform == 'ccw':
            poly_w_orig = max(p[0] for p in poly) if poly else 0
            layout_pad_x = pad_y
            layout_pad_y = svg_w - pad_x - poly_w_orig
        elif transform == 'cw':
            poly_h_orig = max(p[1] for p in poly) if poly else 0
            layout_pad_x = svg_h - pad_y - poly_h_orig
            layout_pad_y = pad_x
        elif transform == 'flip_h':
            poly_w_orig = max(p[0] for p in poly) if poly else 0
            layout_pad_x = svg_w - pad_x - poly_w_orig
            layout_pad_y = pad_y
        elif transform == 'ccw_flip_h':
            poly_w_orig = max(p[0] for p in poly) if poly else 0
            poly_h_orig = max(p[1] for p in poly) if poly else 0
            layout_pad_x = svg_h - pad_y - poly_h_orig
            layout_pad_y = svg_w - pad_x - poly_w_orig
        elif transform == 'ccw_flip_v':
            # (x,y) → (y, x): pad maps as (pad_y, pad_x) → layout (pad_x, pad_y)
            layout_pad_x = pad_y
            layout_pad_y = pad_x
        elif transform == 'flip_v':
            poly_h_orig = max(p[1] for p in poly) if poly else 0
            layout_pad_x = pad_x
            layout_pad_y = svg_h - pad_y - poly_h_orig
        else:
            layout_pad_x = pad_x
            layout_pad_y = pad_y

        poly = _transform_polygon(poly, transform, svg_w, svg_h)

        # Debug: compare polygon extent vs SVG bounding box
        if poly:
            poly_w = max(p[0] for p in poly) - min(p[0] for p in poly)
            poly_h = max(p[1] for p in poly) - min(p[1] for p in poly)
            waste_x = grain_len - poly_w
            waste_y = cross_w - poly_h
            if waste_x > 0.5 or waste_y > 0.5:
                print(f"    {name:20s}  SVG: {grain_len:5.1f}×{cross_w:5.1f}  "
                      f"poly: {poly_w:5.1f}×{poly_h:5.1f}  "
                      f"waste: {waste_x:+.1f}×{waste_y:+.1f}")

        pieces_with_polys.append(
            (name, grain_len, cross_w, edge, poly,
             layout_pad_x, layout_pad_y))

    positions, total_length, _use_polygons = polygon_nest(
        pieces_with_polys, fabric_width, gap=gap,
        prefer_offset_nest=prefer_panel_pairing)

    return pieces, positions, total_length


# ---------------------------------------------------------------------------
# Rendering helper — draw fabric strip contents into a parent SVG element
# ---------------------------------------------------------------------------

def _parse_translate(transform):
    """Parse the first SVG translate(tx[, ty]) from a transform string."""
    if not transform:
        return None
    m = re.search(r'translate\(\s*([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)'
                  r'(?:[\s,]+([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?))?\s*\)', transform)
    if not m:
        return None
    tx = float(m.group(1))
    ty = float(m.group(2)) if m.group(2) is not None else 0.0
    return tx, ty


def _find_parent(root, child):
    """Return (parent, index) for *child* in an ElementTree rooted at *root*."""
    for parent in root.iter():
        children = list(parent)
        for idx, node in enumerate(children):
            if node is child:
                return parent, idx
    return None, None


def _infer_text_anchor(group):
    """Infer a local anchor point for a matplotlib text group."""
    # Matplotlib text groups usually contain a descendant with
    # transform="translate(x y) scale(...)". Use that translation anchor.
    for node in [group, *list(group.iter())]:
        tr = node.get('transform')
        parsed = _parse_translate(tr)
        if parsed is not None:
            return parsed
    return None


def _reflection_matrix_for_transform(transform):
    """Return the reflection matrix coefficients (a,b,c,d) for a transform."""
    return {
        'flip_h': (-1.0, 0.0, 0.0, 1.0),
        'flip_v': (1.0, 0.0, 0.0, -1.0),
        'ccw_flip_h': (0.0, -1.0, -1.0, 0.0),
        'ccw_flip_v': (0.0, 1.0, 1.0, 0.0),
    }.get(transform)


def _matrix_about_anchor(a, b, c, d, ax, ay):
    """Build an SVG matrix(...) string applying linear map around anchor."""
    e = ax - (a * ax + c * ay)
    f = ay - (b * ax + d * ay)
    return f'matrix({a:.6f} {b:.6f} {c:.6f} {d:.6f} {e:.6f} {f:.6f})'


def _counter_reflect_text_groups(piece_root, transform):
    """Counter-reflect text_* groups so mirrored placements remain readable."""
    coeffs = _reflection_matrix_for_transform(transform)
    if coeffs is None:
        return
    a, b, c, d = coeffs

    text_groups = []
    for g in piece_root.findall(f'.//{_tag("g")}'):
        if g.get('id', '').startswith('text_'):
            text_groups.append(g)

    for group in text_groups:
        anchor = _infer_text_anchor(group)
        if anchor is None:
            continue
        ax, ay = anchor
        corr = _matrix_about_anchor(a, b, c, d, ax, ay)

        parent, idx = _find_parent(piece_root, group)
        if parent is None:
            continue
        wrapper = ET.Element(_tag('g'), {'transform': corr})
        parent.remove(group)
        wrapper.append(group)
        parent.insert(idx, wrapper)


def _embed_piece_svg(container, svg_path, x_pt, y_pt, gl_pt, cw_pt, transform):
    """Parse a piece SVG and embed it into *container* with the given transform.

    Factored out of _render_strip to keep the per-transform logic in one
    place (identical for both SVG-layer and PDF-page rendering).
    """
    piece_tree = ET.parse(svg_path)
    piece_root = piece_tree.getroot()

    # Strip the white background rectangle (patch_1) so overlapping
    # bounding boxes don't hide adjacent pieces in the cutting layout.
    patch1 = piece_root.find(f'.//{_tag("g")}[@id="patch_1"]')
    if patch1 is not None:
        fig_g = piece_root.find(f'.//{_tag("g")}[@id="figure_1"]')
        if fig_g is not None:
            fig_g.remove(patch1)

    # For mirrored placements, counter-reflect text groups locally so
    # labels remain readable while preserving mirrored geometry placement.
    _counter_reflect_text_groups(piece_root, transform=transform)

    viewBox = piece_root.get('viewBox')
    if not viewBox:
        pw = piece_root.get('width', '0')
        ph = piece_root.get('height', '0')
        pw_num = float(pw.replace('pt', '').replace('in', '')
                       .replace('px', ''))
        ph_num = float(ph.replace('pt', '').replace('in', '')
                       .replace('px', ''))
        viewBox = f'0 0 {pw_num} {ph_num}'

    vb_parts = viewBox.split()
    vw, vh = float(vb_parts[2]), float(vb_parts[3])

    nested = ET.SubElement(container, _tag('svg'), {
        'x': f'{x_pt:.2f}',
        'y': f'{y_pt:.2f}',
        'width': f'{gl_pt:.2f}',
        'height': f'{cw_pt:.2f}',
    })

    if transform == 'cw':
        nested.set('viewBox', f'0 0 {vh} {vw}')
        wrapper = ET.SubElement(nested, _tag('g'), {
            'transform': f'translate({vh}, 0) rotate(90)',
        })
        for child in piece_root:
            wrapper.append(child)
    elif transform == 'ccw':
        nested.set('viewBox', f'0 0 {vh} {vw}')
        wrapper = ET.SubElement(nested, _tag('g'), {
            'transform': f'translate(0, {vw}) rotate(-90)',
        })
        for child in piece_root:
            wrapper.append(child)
    elif transform == 'flip_h':
        nested.set('viewBox', viewBox)
        wrapper = ET.SubElement(nested, _tag('g'), {
            'transform': f'translate({vw}, 0) scale(-1, 1)',
        })
        for child in piece_root:
            wrapper.append(child)
    elif transform == 'ccw_flip_h':
        nested.set('viewBox', f'0 0 {vh} {vw}')
        wrapper = ET.SubElement(nested, _tag('g'), {
            'transform':
                f'translate({vh}, 0) scale(-1, 1) '
                f'translate(0, {vw}) rotate(-90)',
        })
        for child in piece_root:
            wrapper.append(child)
    elif transform == 'ccw_flip_v':
        nested.set('viewBox', f'0 0 {vh} {vw}')
        wrapper = ET.SubElement(nested, _tag('g'), {
            'transform':
                f'translate(0, {vw}) scale(1, -1) '
                f'translate(0, {vw}) rotate(-90)',
        })
        for child in piece_root:
            wrapper.append(child)
    elif transform == 'flip_v':
        nested.set('viewBox', viewBox)
        wrapper = ET.SubElement(nested, _tag('g'), {
            'transform': f'translate(0, {vh}) scale(1, -1)',
        })
        for child in piece_root:
            wrapper.append(child)
    else:
        nested.set('viewBox', viewBox)
        for child in piece_root:
            nested.append(child)

def _render_strip(container, pieces, positions, total_length,
                  fabric_width, units='inch', gap=0.25, selvedge=True):
    """Render a fabric strip (background, markers, rulers, pieces, yardage)
    into a parent SVG element.

    Parameters
    ----------
    container : Element
        SVG element to append children to (``<g>`` layer or ``<svg>`` root).
    pieces : list of (name, grain_len, cross_w, svg_path, transform, edge)
    positions : dict  {name: (x, y)}
    total_length : float
    fabric_width : float
    units : str
    gap : float
    selvedge : bool
        True for selvedge fabric (red dashed edge lines), False for
        plain-edge fabric (gray solid edge lines).
    """
    svg_w_pt = total_length * PTS_PER_INCH
    svg_h_pt = fabric_width * PTS_PER_INCH

    # Background (transparent — keeps bounding box for Inkscape layer extents)
    ET.SubElement(container, _tag('rect'), {
        'width': f'{svg_w_pt:.2f}', 'height': f'{svg_h_pt:.2f}',
        'fill': 'none', 'stroke': 'none',
    })

    # --- Edge markers (horizontal lines at top and bottom) ---
    if selvedge:
        edge_style = 'stroke:#c44;stroke-width:1.5;stroke-dasharray:8,4'
        edge_label = 'SELVEDGE'
        edge_color = '#c44'
    else:
        edge_style = 'stroke:#888;stroke-width:0.75;stroke-dasharray:4,2'
        edge_label = 'EDGE'
        edge_color = '#888'

    ET.SubElement(container, _tag('line'), {
        'x1': '0', 'y1': '0',
        'x2': f'{svg_w_pt:.2f}', 'y2': '0',
        'style': edge_style,
    })
    ET.SubElement(container, _tag('line'), {
        'x1': '0', 'y1': f'{svg_h_pt:.2f}',
        'x2': f'{svg_w_pt:.2f}', 'y2': f'{svg_h_pt:.2f}',
        'style': edge_style,
    })

    # Edge labels
    for y_pos, baseline in [(12, 'hanging'), (svg_h_pt - 4, 'auto')]:
        label = ET.SubElement(container, _tag('text'), {
            'x': '5', 'y': str(y_pos),
            'font-family': 'sans-serif', 'font-size': '10',
            'fill': edge_color, 'text-anchor': 'start',
            'dominant-baseline': baseline,
        })
        label.text = edge_label

    # --- Length rulers (vertical lines every 12 inches / 1 foot) ---
    ruler_interval = 12.0
    x_ruler = ruler_interval
    while x_ruler < total_length:
        x_pt = x_ruler * PTS_PER_INCH
        ET.SubElement(container, _tag('line'), {
            'x1': str(x_pt), 'y1': '0',
            'x2': str(x_pt), 'y2': f'{svg_h_pt:.2f}',
            'style': 'stroke:#aaa;stroke-width:0.5;stroke-dasharray:4,8',
        })
        if units == 'cm':
            label_text = f'{x_ruler * CM_PER_INCH:.0f} cm'
        else:
            feet = int(x_ruler // 12)
            inches = int(x_ruler % 12)
            label_text = f"{feet}'" if inches == 0 else f"{feet}' {inches}\""
        ruler_label = ET.SubElement(container, _tag('text'), {
            'x': str(x_pt + 3), 'y': f'{svg_h_pt - 5:.2f}',
            'font-family': 'sans-serif', 'font-size': '8',
            'fill': '#999', 'text-anchor': 'start',
        })
        ruler_label.text = label_text
        x_ruler += ruler_interval

    # --- Yardage info box + calibration square ---
    yards = total_length / 36.0
    metres = total_length * CM_PER_INCH / 100.0
    box_w, box_h = 160, 72
    box_x = svg_w_pt - box_w - 8
    box_y = 8  # top-right corner

    ET.SubElement(container, _tag('rect'), {
        'x': str(box_x), 'y': str(box_y),
        'width': str(box_w), 'height': str(box_h),
        'rx': '4',
        'fill': 'white', 'stroke': '#999', 'stroke-width': '0.75',
    })

    info_lines = [
        (f'{fabric_width:.0f}" wide', 12),
        (f'{total_length:.1f}" long', 24),
        (f'{yards:.2f} yd  /  {metres:.2f} m', 38),
        (f'{len(pieces)} pieces', 50),
    ]
    for text, dy in info_lines:
        el = ET.SubElement(container, _tag('text'), {
            'x': str(box_x + box_w / 2), 'y': str(box_y + dy),
            'font-family': 'sans-serif', 'font-size': '9',
            'fill': '#444', 'text-anchor': 'middle',
        })
        el.text = text

    # 5 cm calibration square inside the info box
    cal_cm = 5.0
    cal_pt = cal_cm / CM_PER_INCH * PTS_PER_INCH  # 5 cm in points
    cal_x = box_x + (box_w - cal_pt) / 2
    cal_y = box_y + 54
    ET.SubElement(container, _tag('rect'), {
        'x': str(cal_x), 'y': str(cal_y),
        'width': f'{cal_pt:.1f}', 'height': f'{cal_pt:.1f}',
        'fill': 'none', 'stroke': '#444', 'stroke-width': '0.75',
    })
    cal_label = ET.SubElement(container, _tag('text'), {
        'x': str(cal_x + cal_pt / 2), 'y': str(cal_y + cal_pt / 2 + 3),
        'font-family': 'sans-serif', 'font-size': '7',
        'fill': '#444', 'text-anchor': 'middle',
    })
    cal_label.text = '5\u2009cm'

    # --- Embed each piece SVG ---
    for name, grain_len, cross_w, svg_path, transform, edge in pieces:
        x, y = positions[name]
        _embed_piece_svg(container, svg_path,
                         x * PTS_PER_INCH, y * PTS_PER_INCH,
                         grain_len * PTS_PER_INCH, cross_w * PTS_PER_INCH,
                         transform)


# ---------------------------------------------------------------------------
# Output writers — SVG (Inkscape layers) and PDF (multi-page)
# ---------------------------------------------------------------------------

def _write_svg(layouts, output_path, units, gap):
    """Write a single SVG with Inkscape layers (one per fabric)."""
    # Canvas = max dimensions across all fabrics
    max_length = max(tl for _, _, _, tl in layouts)
    max_width = max(g['fabric_width'] for g, _, _, _ in layouts)
    svg_w_pt = max_length * PTS_PER_INCH
    svg_h_pt = max_width * PTS_PER_INCH

    root = ET.Element(_tag('svg'), {
        'width': f'{svg_w_pt:.2f}pt',
        'height': f'{svg_h_pt:.2f}pt',
        'viewBox': f'0 0 {svg_w_pt:.2f} {svg_h_pt:.2f}',
    })

    for i, (group, pieces, positions, total_length) in enumerate(layouts):
        label = f"{group['label']} ({group['fabric_width']}\""
        if group['selvedge']:
            label += ' selvedge'
        label += ')'

        display = 'inline' if i == 0 else 'none'
        layer = ET.SubElement(root, _tag('g'), {
            f'{{{INKSCAPE_NS}}}groupmode': 'layer',
            f'{{{INKSCAPE_NS}}}label': label,
            'id': f"layer-{group['name']}",
            'style': f'display:{display}',
        })

        _render_strip(layer, pieces, positions, total_length,
                      group['fabric_width'], units=units, gap=gap,
                      selvedge=group['selvedge'])

    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')
    tree.write(str(output_path), xml_declaration=True, encoding='utf-8')


def _write_pdf(layouts, output_path, units, gap):
    """Write a multi-page PDF (one page per fabric) at 1:1 scale."""
    import io

    try:
        import cairosvg
    except ImportError:
        print("cairosvg not installed — install with: pip install cairosvg")
        print("Falling back to SVG output.")
        _write_svg(layouts, output_path.with_suffix('.svg'), units, gap)
        return

    try:
        from pypdf import PdfWriter, PdfReader
    except ImportError:
        print("pypdf not installed — install with: pip install pypdf")
        print("Falling back to SVG output.")
        _write_svg(layouts, output_path.with_suffix('.svg'), units, gap)
        return

    writer = PdfWriter()

    for group, pieces, positions, total_length in layouts:
        svg_w_pt = total_length * PTS_PER_INCH
        svg_h_pt = group['fabric_width'] * PTS_PER_INCH

        svg_root = ET.Element(_tag('svg'), {
            'width': f'{svg_w_pt:.2f}pt',
            'height': f'{svg_h_pt:.2f}pt',
            'viewBox': f'0 0 {svg_w_pt:.2f} {svg_h_pt:.2f}',
        })

        _render_strip(svg_root, pieces, positions, total_length,
                      group['fabric_width'], units=units, gap=gap,
                      selvedge=group['selvedge'])

        # Serialize to SVG bytes
        svg_tree = ET.ElementTree(svg_root)
        ET.indent(svg_tree, space='  ')
        buf = io.BytesIO()
        svg_tree.write(buf, xml_declaration=True, encoding='utf-8')
        svg_bytes = buf.getvalue()

        # Convert to PDF via cairosvg
        pdf_bytes = cairosvg.svg2pdf(bytestring=svg_bytes)

        # Add page(s) to the writer
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page in reader.pages:
            writer.add_page(page)

    with open(output_path, 'wb') as f:
        writer.write(f)


# Named-color → hex equivalents for the specific colors plot_utils uses.
# Matplotlib's SVG backend may emit either the name, the long hex, or the
# short hex depending on version/rcParams, so we normalize all forms.
_COLOR_ALIASES = {
    'blue':  ('blue', '#0000ff', '#00f'),
    'black': ('black', '#000000', '#000'),
}


def _style_has_stroke_color(style_str, color_name):
    """Return True if *style_str* has a ``stroke:`` property matching *color_name*.

    Whitespace-tolerant and accepts named/hex/short-hex equivalents.
    """
    if not style_str:
        return False
    norm = re.sub(r'\s+', '', style_str).lower()
    aliases = _COLOR_ALIASES.get(color_name.lower(), (color_name.lower(),))
    return any(f'stroke:{a}' in norm for a in aliases)


def _style_matches_seamline(style_str):
    return _style_has_stroke_color(style_str, SEAMLINE['color'])


def _style_matches_cutline(style_str):
    return _style_has_stroke_color(style_str, CUTLINE['color'])


def _write_dxf(layouts, output_path, units, gap):
    """Write a multi-layer DXF (one layer per fabric) at 1:1 scale."""
    try:
        import ezdxf
    except ImportError:
        print("ezdxf not installed — install with: pip install ezdxf")
        print("Falling back to SVG output.")
        _write_svg(layouts, output_path.with_suffix('.svg'), units, gap)
        return

    doc = ezdxf.new('R2010')

    if units == 'cm':
        doc.header['$INSUNITS'] = 5
        scale_factor = CM_PER_INCH / PTS_PER_INCH
    else:
        doc.header['$INSUNITS'] = 1
        scale_factor = 1.0 / PTS_PER_INCH

    msp = doc.modelspace()
    colors = [1, 5, 2, 3, 4, 6]  # Red, Blue, Yellow, Green, Cyan, Magenta

    for i, (group, pieces, positions, total_length) in enumerate(layouts):
        layer_name = group['name'].upper()
        color = colors[i % len(colors)]
        if layer_name not in doc.layers:
            doc.layers.add(layer_name, color=color)

        fabric_w_pt = group['fabric_width'] * PTS_PER_INCH

        for name, grain_len, cross_w, svg_path, transform, edge in pieces:
            x_in, y_in = positions[name]
            x_pt = x_in * PTS_PER_INCH
            y_pt = y_in * PTS_PER_INCH

            tree = ET.parse(svg_path)
            root = tree.getroot()

            viewBox = root.get('viewBox')
            if not viewBox:
                pw = float(root.get('width', '0').replace('pt','').replace('in','').replace('px',''))
                ph = float(root.get('height', '0').replace('pt','').replace('in','').replace('px',''))
                vw, vh = pw, ph
            else:
                vb_parts = viewBox.split()
                vw, vh = float(vb_parts[2]), float(vb_parts[3])

            axes = root.find(f'.//{{http://www.w3.org/2000/svg}}g[@id="axes_1"]')
            if axes is None:
                continue

            for g in axes.iter(f'{{http://www.w3.org/2000/svg}}g'):
                if not g.get('id', '').startswith('line2d_'):
                    continue
                for path_el in g.findall(f'{{http://www.w3.org/2000/svg}}path'):
                    d = path_el.get('d', '')
                    style = path_el.get('style', '')
                    if not d: continue
                    verts, closed = _parse_svg_path_data(d, curve_steps=20)
                    if len(verts) < 2: continue

                    dxf_verts = []
                    for px, py in verts:
                        if transform == 'cw':
                            tx, ty = vh - py, px
                        elif transform == 'ccw':
                            tx, ty = py, vw - px
                        elif transform == 'flip_h':
                            tx, ty = vw - px, py
                        elif transform == 'ccw_flip_h':
                            tx, ty = vh - py, vw - px
                        elif transform == 'ccw_flip_v':
                            tx, ty = py, px
                        elif transform == 'flip_v':
                            tx, ty = px, vh - py
                        else:
                            tx, ty = px, py

                        fx_pt = tx + x_pt
                        fy_pt = ty + y_pt

                        dxf_x = fx_pt * scale_factor
                        dxf_y = (fabric_w_pt - fy_pt) * scale_factor
                        dxf_verts.append((dxf_x, dxf_y))

                    # Route polylines to _SEAM / _CUT sublayers based on the
                    # stroke color that plot_utils.SEAMLINE / CUTLINE emit.
                    target_layer = layer_name
                    if _style_matches_seamline(style):
                        target_layer = layer_name + '_SEAM'
                        if target_layer not in doc.layers:
                            doc.layers.add(target_layer, color=color)
                    elif _style_matches_cutline(style):
                        target_layer = layer_name + '_CUT'
                        if target_layer not in doc.layers:
                            doc.layers.add(target_layer, color=color)

                    msp.add_lwpolyline(dxf_verts, close=closed, dxfattribs={'layer': target_layer})

    doc.saveas(output_path)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_lay_plan(fabric_groups, output_path, units='inch', gap=0.25,
                      fmt='svg', prefer_panel_pairing=True):
    """Generate a multi-fabric lay plan as SVG (with Inkscape layers) or PDF.

    Parameters
    ----------
    fabric_groups : list of dict
        Each dict has keys:
          name         — fabric identifier ('main', 'pocketing', …)
          label        — human-readable name ('Main Fabric', …)
          fabric_width — width in inches
          selvedge     — bool (True for selvedge markers)
          pieces       — list of (svg_path, cut_count, selvedge_edge, grain_axis)
    output_path : str or Path
    units : str  ('inch' or 'cm')
    gap : float  (spacing between pieces in inches)
    fmt : str    ('svg' or 'pdf')
    prefer_panel_pairing : bool
        If True (default), prefer matched front/back panel pairing when
        offset nesting is available.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- Layout phase: pack each fabric group ---
    layouts = []  # (group, pieces, positions, total_length)
    for group in fabric_groups:
        print(f"\n  Laying out {group['label']} ({group['fabric_width']}\" wide)...")
        pieces, positions, total_length = _layout_fabric(
            group['pieces'], group['fabric_width'], gap=gap,
            prefer_panel_pairing=prefer_panel_pairing)
        if not pieces:
            print(f"    (no pieces)")
            continue
        layouts.append((group, pieces, positions, total_length))

    if not layouts:
        print("No pieces to lay out.")
        return

    # --- Summary per fabric ---
    for group, pieces, positions, total_length in layouts:
        yards = total_length / 36.0
        metres = total_length * CM_PER_INCH / 100.0
        print(f"  {group['label']}: {group['fabric_width']}\" wide × "
              f"{total_length:.1f}\" long = {yards:.2f} yd ({metres:.2f} m), "
              f"{len(pieces)} pieces")

    # --- Write output ---
    if fmt == 'pdf':
        _write_pdf(layouts, output_path, units, gap)
    elif fmt == 'dxf':
        _write_dxf(layouts, output_path, units, gap)
    else:
        _write_svg(layouts, output_path, units, gap)

    print(f"\nSaved lay plan to {output_path}")
