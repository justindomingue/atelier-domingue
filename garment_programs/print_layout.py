"""Generic cutting layout — skyline-pack piece SVGs within a fabric width.

Works for any garment: reads individual piece SVGs, packs them into a
single composite SVG that represents the cutting layout on fabric of a
given width.

Layout orientation (horizontal):
    x-axis = fabric length (grows rightward)
    y-axis = fabric width  (constrained, e.g. 31" for selvedge denim)

Pieces are placed WITHOUT rotation so their grainline (SVG x-axis,
waist-to-hem) naturally aligns with fabric length.  Selvedge-constrained
pieces are forced against the top/bottom edges of the layout so the
outseam sits on the selvedge.
"""

import math
import re
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path

# SVG namespace
SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)
ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

PTS_PER_INCH = 72.0
CM_PER_INCH = 2.54


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

def _parse_svg_path_data(d_string):
    """Parse an SVG path ``d`` attribute (M/L commands only) into vertices.

    Handles whitespace/newline variations in matplotlib's SVG output.
    Returns a list of (x, y) float tuples.  Ignores Q/C/z commands
    (quadratic/cubic beziers, closepath) — those appear in grainline arrows
    and font glyphs, not in piece outlines.
    """
    vertices = []
    # Tokenize: find all M or L commands followed by two numbers
    for m in re.finditer(
        r'([ML])\s+([-\d.eE]+)\s*[,\s]\s*([-\d.eE]+)', d_string
    ):
        vertices.append((float(m.group(2)), float(m.group(3))))
    return vertices


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
            verts = _parse_svg_path_data(d)
            if len(verts) < 3:
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

    Mirrors the SVG embedding transforms used in generate_cutting_layout().

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


def polygon_nest(pieces, fabric_width, gap=0.25):
    """Polygon-aware nesting with void filling and skyline fallback.

    Strategy:
    1. Always compute baseline via skyline_pack (handles selvedge pinning
       and interleaving perfectly).
    2. Place selvedge pieces via skyline, then run a void-fill pass to
       tuck free pieces into the curved voids within selvedge bounding boxes.
    3. Remaining free pieces go through skyline continuation.
    4. If spyrrow is available, also try polygon nesting as an alternative.
    5. Use whichever strategy produces the shortest total length.

    Same return signature as skyline_pack() plus a ``use_polygons`` flag.

    Parameters
    ----------
    pieces : list of tuples
        (name, grain_len, cross_w, edge, polygon, pad_x, pad_y)
    fabric_width : float
    gap : float

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
    remaining_sky_pos, vf_total = skyline_pack(
        remaining_input, fabric_width, gap=gap,
        initial_skyline=vf_skyline)

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

    # --- Pick the best strategy (prefer void fill on ties) ---
    candidates = [
        (vf_total, 0, vf_positions, True, "void fill + skyline"),
        (sky_length, 1, sky_positions, False, "baseline skyline"),
        (sky_cont_total, 2, sky_cont_positions, False, "skyline continuation"),
    ]
    best_total, _, best_pos, best_poly, best_label = min(
        candidates, key=lambda c: (c[0], c[1]))

    # Report
    others = [(t, l) for t, _, _, _, l in candidates if l != best_label]
    other_str = ", ".join(f"{l}={t:.1f}\"" for t, l in others)
    print(f"  Best: {best_label} = {best_total:.1f}\" ({other_str})")

    return best_pos, best_total, best_poly


def generate_cutting_layout(svg_paths, fabric_width, output_path,
                            units='inch', gap=0.25):
    """Composite piece SVGs into a single cutting layout SVG.

    Pieces are placed WITHOUT rotation — their SVG x-axis (grainline)
    maps directly to the layout x-axis (fabric length).

    Parameters
    ----------
    svg_paths : list of (svg_file_path, cut_count, selvedge_edge, grain_axis)
        Each entry is an SVG file, how many copies to cut, an optional
        selvedge edge indicator ('top' in SVG coords) specifying which edge
        should sit on the fabric selvedge, and the grain axis ('x' or 'y')
        indicating which SVG axis carries the grainline.
    fabric_width : float
        Fabric width in inches.
    output_path : str or Path
        Where to write the combined SVG.
    units : str
        'inch' or 'cm' — used for ruler labels.
    gap : float
        Gap between pieces in inches.
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
                for i in range(cut_count):
                    pieces.append((f'{name}_{i+1}', grain_len, cross_w,
                                   svg_path, base_transform, None))

    if not pieces:
        print("No pieces to lay out.")
        return

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

    positions, total_length, use_polygons = polygon_nest(
        pieces_with_polys, fabric_width, gap=gap)

    # --- Build composite SVG (horizontal) ---
    # x = fabric length, y = fabric width
    svg_w_pt = total_length * PTS_PER_INCH
    svg_h_pt = fabric_width * PTS_PER_INCH

    root = ET.Element(_tag('svg'), {
        'width': f'{svg_w_pt:.2f}pt',
        'height': f'{svg_h_pt:.2f}pt',
        'viewBox': f'0 0 {svg_w_pt:.2f} {svg_h_pt:.2f}',
    })

    # Background
    ET.SubElement(root, _tag('rect'), {
        'width': '100%', 'height': '100%',
        'fill': '#faf8f5', 'stroke': 'none',
    })

    # --- Selvedge markers (horizontal lines at top and bottom) ---
    selvedge_style = 'stroke:#c44;stroke-width:1.5;stroke-dasharray:8,4'
    ET.SubElement(root, _tag('line'), {
        'x1': '0', 'y1': '0',
        'x2': str(svg_w_pt), 'y2': '0',
        'style': selvedge_style,
    })
    ET.SubElement(root, _tag('line'), {
        'x1': '0', 'y1': str(svg_h_pt),
        'x2': str(svg_w_pt), 'y2': str(svg_h_pt),
        'style': selvedge_style,
    })

    # Selvedge labels
    for y_pos, baseline in [(12, 'hanging'), (svg_h_pt - 4, 'auto')]:
        label = ET.SubElement(root, _tag('text'), {
            'x': '5', 'y': str(y_pos),
            'font-family': 'sans-serif', 'font-size': '10',
            'fill': '#c44', 'text-anchor': 'start',
            'dominant-baseline': baseline,
        })
        label.text = 'SELVEDGE'

    # --- Length rulers (vertical lines every 12 inches / 1 foot) ---
    ruler_interval = 12.0
    x_ruler = ruler_interval
    while x_ruler < total_length:
        x_pt = x_ruler * PTS_PER_INCH
        ET.SubElement(root, _tag('line'), {
            'x1': str(x_pt), 'y1': '0',
            'x2': str(x_pt), 'y2': str(svg_h_pt),
            'style': 'stroke:#aaa;stroke-width:0.5;stroke-dasharray:4,8',
        })
        if units == 'cm':
            label_text = f'{x_ruler * CM_PER_INCH:.0f} cm'
        else:
            feet = int(x_ruler // 12)
            inches = int(x_ruler % 12)
            label_text = f"{feet}'" if inches == 0 else f"{feet}' {inches}\""
        ruler_label = ET.SubElement(root, _tag('text'), {
            'x': str(x_pt + 3), 'y': str(svg_h_pt - 5),
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

    ET.SubElement(root, _tag('rect'), {
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
        el = ET.SubElement(root, _tag('text'), {
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
    ET.SubElement(root, _tag('rect'), {
        'x': str(cal_x), 'y': str(cal_y),
        'width': f'{cal_pt:.1f}', 'height': f'{cal_pt:.1f}',
        'fill': 'none', 'stroke': '#444', 'stroke-width': '0.75',
    })
    cal_label = ET.SubElement(root, _tag('text'), {
        'x': str(cal_x + cal_pt / 2), 'y': str(cal_y + cal_pt / 2 + 3),
        'font-family': 'sans-serif', 'font-size': '7',
        'fill': '#444', 'text-anchor': 'middle',
    })
    cal_label.text = '5\u2009cm'

    # --- Embed each piece SVG ---
    for name, grain_len, cross_w, svg_path, transform, edge in pieces:
        x, y = positions[name]
        x_pt = x * PTS_PER_INCH
        y_pt = y * PTS_PER_INCH
        gl_pt = grain_len * PTS_PER_INCH
        cw_pt = cross_w * PTS_PER_INCH

        piece_tree = ET.parse(svg_path)
        piece_root = piece_tree.getroot()

        # Strip the white background rectangle (patch_1) so overlapping
        # bounding boxes don't hide adjacent pieces in the cutting layout.
        patch1 = piece_root.find(
            f'.//{_tag("g")}[@id="patch_1"]')
        if patch1 is not None:
            parent = piece_root.find(
                f'.//{_tag("g")}[@id="figure_1"]')
            if parent is not None:
                parent.remove(patch1)

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

        nested = ET.SubElement(root, _tag('svg'), {
            'x': f'{x_pt:.2f}',
            'y': f'{y_pt:.2f}',
            'width': f'{gl_pt:.2f}',
            'height': f'{cw_pt:.2f}',
        })

        if transform == 'cw':
            # 90° CW: SVG top → right.  (x,y) → (y, -x+vh)
            nested.set('viewBox', f'0 0 {vh} {vw}')
            wrapper = ET.SubElement(nested, _tag('g'), {
                'transform': f'translate({vh}, 0) rotate(90)',
            })
            for child in piece_root:
                wrapper.append(child)
        elif transform == 'ccw':
            # 90° CCW: SVG top → left.  (x,y) → (-y+vw, x)
            nested.set('viewBox', f'0 0 {vh} {vw}')
            wrapper = ET.SubElement(nested, _tag('g'), {
                'transform': f'translate(0, {vw}) rotate(-90)',
            })
            for child in piece_root:
                wrapper.append(child)
        elif transform == 'flip_v':
            # Vertical flip: outseam (SVG top) moves to bottom of piece.
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

    # --- Write output ---
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')
    tree.write(str(output_path), xml_declaration=True, encoding='utf-8')
    print(f"Saved cutting layout to {output_path}")
    print(f"  Fabric: {fabric_width}\" wide x {total_length:.1f}\" long")
    print(f"  Yardage: {yards:.2f} yd  ({metres:.2f} m)")
    print(f"  Pieces: {len(pieces)}")
