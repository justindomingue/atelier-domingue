"""Pattern nesting — arrange all pieces on a single fabric strip.

Packing strategy
~~~~~~~~~~~~~~~~
1. **Selvedge pairing** — Front/back panels are pinned to opposite
   selvedge edges (outseam on selvedge).  Mirrored copies face each
   other across the strip.  Smaller selvedge pieces (waistband, cinch,
   fly) fill the opposite edge.

2. **Polygon void-fill** — After placing selvedge pairs, the crotch
   curves leave large voids between the panels.  Free pieces are packed
   into those voids using a discretized polygon profile.

3. **FFDH fallback** — Any pieces that don't fit in voids are placed
   via First Fit Decreasing Height shelf packing after the selvedge zone.

Grain alignment
~~~~~~~~~~~~~~~
Every piece is rotated so its grain line runs parallel to the fabric
length (packing Y-axis).  Pieces whose draft has grain along the
X-axis are rotated 90° clockwise: (x, y) → (y, −x).  This also maps
bottom-selvedge edges to packing x = 0.

Coordinate system (packing)
~~~~~~~~~~~~~~~~~~~~~~~~~~~
    x-axis = across fabric width  (0 = bottom selvedge, strip_width = top)
    y-axis = along fabric length  (grows with each placed piece)

For rendering, x↔y are swapped so fabric length runs horizontally.
"""
import importlib

import numpy as np
import matplotlib.pyplot as plt


# -- Grain rotation -----------------------------------------------------------

# Modules whose grain runs along the draft X-axis.
# These need a 90° CW rotation to align grain with packing Y (fabric length).
# Modules NOT listed here have grain along draft Y and need no rotation.
_GRAIN_ROTATE_90 = {
    'jeans_front',
    'jeans_back',
    'jeans_yoke_1873',
    'jeans_yoke_modern',
    'jeans_waistband',
    'jeans_front_pocket_bag',
    'jeans_front_facing',
    'jeans_back_cinch',
}


def _rotate_90cw(outline):
    """Rotate outline 90° clockwise: (x, y) → (y, −x)."""
    return np.column_stack([outline[:, 1], -outline[:, 0]])


# -- Outline extraction dispatch ----------------------------------------------

_OUTLINE_DISPATCH = {
    'jeans_front':       lambda mod, d: mod.get_outline_front(d['front']),
    'jeans_back':        lambda mod, d: mod.get_outline_back(d['front'], d['back']),
    'jeans_yoke_1873':   lambda mod, d: mod.get_outline_yoke_1873(
                             d['front'], d['back'], d['yoke_1873']),
    'jeans_yoke_modern': lambda mod, d: mod.get_outline_yoke_modern(d['yoke_modern']),
    'jeans_waistband':   lambda mod, d: mod.get_outline_waistband(d['waistband']),
    'jeans_fly_1873':    lambda mod, d: mod.get_outline_fly_1873(d['fly_1873']),
    'jeans_fly_one_piece': lambda mod, d: mod.get_outline_fly_one_piece(d['fly_one_piece']),
    'jeans_front_pocket_bag': lambda mod, d: mod.get_outline_front_pocket(d['front_pocket']),
    'jeans_front_facing': lambda mod, d: mod.get_outline_front_facing(d['front_facing']),
    'jeans_back_pocket': lambda mod, d: mod.get_outline_back_pocket(d['back_pocket']),
    'jeans_back_cinch':  lambda mod, d: mod.get_outline_back_cinch(d['back_cinch']),
}

# SA (cut-line) outline dispatch — modules that have get_sa_outline_*()
_SA_OUTLINE_DISPATCH = {
    'jeans_front':       lambda mod, d: mod.get_sa_outline_front(d['front']),
    'jeans_back':        lambda mod, d: mod.get_sa_outline_back(d['front'], d['back']),
    'jeans_yoke_1873':   lambda mod, d: mod.get_sa_outline_yoke_1873(
                             d['front'], d['back'], d['yoke_1873']),
    'jeans_front_pocket_bag': lambda mod, d: mod.get_sa_outline_front_pocket(d['front_pocket']),
    'jeans_front_facing': lambda mod, d: mod.get_sa_outline_front_facing(d['front_facing']),
    'jeans_back_pocket': lambda mod, d: mod.get_sa_outline_back_pocket(d['back_pocket']),
    'jeans_back_cinch':  lambda mod, d: mod.get_sa_outline_back_cinch(d['back_cinch']),
    # Waistband rectangle already includes SA — same outline
    'jeans_waistband':   lambda mod, d: mod.get_outline_waistband(d['waistband']),
}

# Default SA for pieces without explicit SA data (3/8" ≈ 0.95 cm)
_DEFAULT_SA_CM = 3/8 * 2.54

# Selvedge edge constraint per module (in packing coordinates, after rotation).
#   'top'    = outseam at packing x = strip_width  (front/back panels)
#   'bottom' = edge at packing x = 0               (mirrored copies)
# Only the main panels are selvedge-pinned — their outseam sits on the
# fabric selvedge, the signature feature of selvedge denim.  Smaller
# pieces (waistband, fly, cinch) are left free so they can void-fill
# into the crotch gaps between the paired panels.
_SELVEDGE_MAP = {
    'jeans_front': 'top',
    'jeans_back': 'top',
}

# Selvedge edge flips when a piece is mirrored across x.
_SELVEDGE_FLIP = {'top': 'bottom', 'bottom': 'top'}


# -- Polygon void-fill helpers ------------------------------------------------

def _polygon_x_range_at_y(outline, y):
    """Find the x-extent of a closed polygon at a given y-coordinate.

    Returns (x_min, x_max) or None if y is outside the polygon.
    """
    intersections = []
    n = len(outline)
    for i in range(n - 1):
        x1, y1 = outline[i]
        x2, y2 = outline[i + 1]
        if abs(y2 - y1) < 1e-10:
            if abs(y - y1) < 0.1:
                intersections.extend([x1, x2])
            continue
        t = (y - y1) / (y2 - y1)
        if -0.001 <= t <= 1.001:
            intersections.append(x1 + t * (x2 - x1))
    if len(intersections) >= 2:
        return min(intersections), max(intersections)
    return None


def _intersect_ranges(ranges_a, ranges_b):
    """Intersect two sorted lists of (lo, hi) ranges."""
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


def _void_fill(placed_outlines, free_pieces, strip_width,
               selvedge_height, gap=1.0, step=0.5):
    """Place free pieces into polygon voids within the selvedge zone.

    Scans the selvedge region column by column.  At each y-slice, computes
    the x-ranges actually occupied by placed piece polygons (not bounding
    boxes).  The void is the complement within [0, strip_width].  Free
    pieces are greedily placed (largest area first) into contiguous
    rectangular voids.

    Parameters
    ----------
    placed_outlines : list of (N,2) ndarray
        Absolute outline coordinates of already-placed selvedge pieces.
    free_pieces : list of dict
        Candidate pieces with outline, origin, bbox_w, bbox_h, name.
    strip_width : float
    selvedge_height : float
        Y-extent of the selvedge zone.
    gap : float
    step : float
        Y-discretization step in cm.

    Returns
    -------
    placements : list of (name, x, y, w, h)
    remaining : list of dict
        Free pieces that couldn't be placed in voids.
    """
    if not placed_outlines or not free_pieces:
        return [], list(free_pieces)

    # Build void profile: at each y-slice, list of (x_lo, x_hi) voids
    y_values = list(np.arange(0, selvedge_height, step))
    profile = {}

    for y in y_values:
        occupied = []
        for ol in placed_outlines:
            xr = _polygon_x_range_at_y(ol, y)
            if xr:
                occupied.append((max(0, xr[0] - gap / 2),
                                 min(strip_width, xr[1] + gap / 2)))
        occupied.sort()

        # Merge overlapping occupied ranges
        merged = []
        for xlo, xhi in occupied:
            if merged and xlo <= merged[-1][1] + 0.01:
                merged[-1] = (merged[-1][0], max(merged[-1][1], xhi))
            else:
                merged.append((xlo, xhi))

        # Void = complement within [0, strip_width]
        voids = []
        prev = 0.0
        for xlo, xhi in merged:
            if xlo > prev + 0.1:
                voids.append((prev, xlo))
            prev = max(prev, xhi)
        if prev < strip_width - 0.1:
            voids.append((prev, strip_width))
        profile[y] = voids

    # Largest-area-first gives the best void utilization — big irregular
    # pieces reclaim the most wasted space.  Small singles pack cheaply
    # in FFDH overflow, so they don't need priority here.
    remaining = sorted(free_pieces,
                       key=lambda p: -(p['bbox_w'] * p['bbox_h']))
    placements = []

    for piece in remaining[:]:
        w = piece['bbox_w']
        h = piece['bbox_h']
        placed = False

        for yi_start in range(len(y_values)):
            y0 = y_values[yi_start]
            if y0 + h + gap > selvedge_height + 0.01:
                break

            # Find common void across all y-slices spanned by [y0, y0+h]
            common = list(profile[y_values[yi_start]])
            for yi in range(yi_start + 1, len(y_values)):
                if y_values[yi] > y0 + h:
                    break
                common = _intersect_ranges(common, profile[y_values[yi]])
                if not common:
                    break

            # Check if any common void fits the piece
            for vx0, vx1 in common:
                if vx1 - vx0 >= w + gap:
                    px = vx0 + gap / 2
                    py = y0
                    placements.append((piece['name'], px, py, w, h))

                    # Block this region in the profile
                    bx0 = max(0, px - gap / 2)
                    bx1 = min(strip_width, px + w + gap / 2)
                    for yi2 in range(len(y_values)):
                        yv = y_values[yi2]
                        if yv < y0 - 0.01 or yv > y0 + h + gap + 0.01:
                            continue
                        new_voids = []
                        for v0, v1 in profile[yv]:
                            if bx1 <= v0 + 0.01 or bx0 >= v1 - 0.01:
                                new_voids.append((v0, v1))
                            else:
                                if v0 < bx0 - 0.01:
                                    new_voids.append((v0, bx0))
                                if v1 > bx1 + 0.01:
                                    new_voids.append((bx1, v1))
                        profile[yv] = new_voids

                    remaining.remove(piece)
                    placed = True
                    break
            if placed:
                break

    return placements, remaining


# -- Skyline helpers ----------------------------------------------------------

def _build_skyline(placements, strip_width, gap):
    """Build a skyline frontier from already-placed pieces.

    The skyline is a piecewise-constant function y_max(x) representing
    the highest y-extent (including gap) at each x-band.  It is stored
    as a sorted list of ``(x_start, x_end, y_high)`` segments covering
    ``[0, strip_width]``.
    """
    # Collect all x-coordinates that define segment boundaries
    x_events = {0.0, strip_width}
    for _, px, py, w, h in placements:
        x_events.add(max(0.0, px))
        x_events.add(min(px + w, strip_width))
    x_sorted = sorted(x_events)

    # For each x-segment, find max y_bottom from overlapping placements
    segments = []
    for i in range(len(x_sorted) - 1):
        x0, x1 = x_sorted[i], x_sorted[i + 1]
        if x1 - x0 < 0.001:
            continue
        x_mid = (x0 + x1) / 2
        y_max = 0.0
        for _, px, py, w, h in placements:
            if px <= x_mid + 0.001 and px + w >= x_mid - 0.001:
                y_max = max(y_max, py + h + gap)
        segments.append((x0, x1, y_max))

    if not segments:
        return [(0.0, strip_width, 0.0)]

    # Merge adjacent segments with the same y_max
    merged = [segments[0]]
    for seg in segments[1:]:
        if abs(seg[2] - merged[-1][2]) < 0.01:
            merged[-1] = (merged[-1][0], seg[1], merged[-1][2])
        else:
            merged.append(seg)

    return merged


def _skyline_place(skyline, pieces, strip_width, gap):
    """Place pieces using skyline bottom-left: each piece goes where the
    frontier is lowest, minimising total fabric length.

    Parameters
    ----------
    skyline : list of (x_start, x_end, y_high)
        Current frontier (from ``_build_skyline`` or prior iteration).
    pieces : list of dict
        Pieces to place, each with ``name``, ``bbox_w``, ``bbox_h``.
    strip_width, gap : float

    Returns
    -------
    placements : list of (name, x, y, w, h)
    total_height : float
    skyline : list — updated frontier
    """
    placements = []

    for piece in pieces:
        w = piece['bbox_w']
        h = piece['bbox_h']

        best_y = float('inf')
        best_x = None

        # Try every segment start as a candidate x-position.
        # Within a segment y is constant, so starting at the left edge
        # is always at least as good as starting anywhere inside.
        for seg in skyline:
            x_start = seg[0]
            x_end = x_start + w
            if x_end > strip_width + 0.01:
                continue

            # Max y across all skyline segments spanned by [x_start, x_end]
            max_y = 0.0
            for sx0, sx1, sy in skyline:
                if sx0 < x_end - 0.001 and sx1 > x_start + 0.001:
                    max_y = max(max_y, sy)

            if max_y < best_y:
                best_y = max_y
                best_x = x_start

        if best_x is None:
            # Piece wider than any gap — place at x=0 past everything
            best_x = 0.0
            best_y = max(s[2] for s in skyline)

        placements.append((piece['name'], best_x, best_y, w, h))

        # Update skyline: replace covered segments with new_y
        piece_right = best_x + w
        new_y = best_y + h + gap

        new_skyline = []
        for sx0, sx1, sy in skyline:
            if sx1 <= best_x + 0.001 or sx0 >= piece_right - 0.001:
                new_skyline.append((sx0, sx1, sy))
            else:
                if sx0 < best_x - 0.001:
                    new_skyline.append((sx0, best_x, sy))
                if sx1 > piece_right + 0.001:
                    new_skyline.append((piece_right, sx1, sy))
        new_skyline.append((best_x, piece_right, new_y))
        skyline = sorted(new_skyline, key=lambda s: s[0])

        # Merge adjacent same-height segments
        merged = [skyline[0]]
        for seg in skyline[1:]:
            if (abs(seg[2] - merged[-1][2]) < 0.01
                    and abs(seg[0] - merged[-1][1]) < 0.01):
                merged[-1] = (merged[-1][0], seg[1], merged[-1][2])
            else:
                merged.append(seg)
        skyline = merged

    total_height = max(s[2] for s in skyline) if skyline else 0.0
    return placements, total_height, skyline


# -- Main packer --------------------------------------------------------------

def nest_pack(pieces, strip_width, gap=1.0):
    """Pack pieces using row-based selvedge pairing, polygon void-fill,
    and skyline overflow.

    Strategy:
    1. **Row pairing** — pair top-selvedge pieces with bottom-selvedge
       pieces into rows sharing a y-start.  Prioritise same-module pairs
       (Front L + Front R) over cross-module pairs for wider, more
       symmetric centre voids.
    2. **Polygon void-fill** — fill curved voids inside selvedge
       bounding boxes with free pieces (largest area first).
    3. **Skyline overflow** — remaining pieces are placed using a
       skyline algorithm starting from the Phase 1+2 frontier.

    Parameters
    ----------
    pieces : list of dict
        Each with keys: name, outline, origin, bbox_w, bbox_h,
        selvedge_edge, module.
    strip_width : float
    gap : float

    Returns
    -------
    placements : list of (name, x, y, w, h)
    total_height : float
    """
    top = sorted([p for p in pieces if p.get('selvedge_edge') == 'top'],
                 key=lambda p: p['bbox_h'], reverse=True)
    bottom = sorted([p for p in pieces if p.get('selvedge_edge') == 'bottom'],
                    key=lambda p: p['bbox_h'], reverse=True)
    free = [p for p in pieces if not p.get('selvedge_edge')]

    # -- Phase 1: Pair top + bottom selvedge pieces into rows ---------------
    # Greedy height-matching: pair the top piece with the bottom piece that
    # minimises height waste (|h_top - h_bottom|) while fitting across the
    # strip.
    rows = []
    used_bottom = set()

    for t in top:
        best_idx = None
        best_waste = float('inf')
        for i, b in enumerate(bottom):
            if i in used_bottom:
                continue
            if t['bbox_w'] + b['bbox_w'] + gap <= strip_width:
                waste = abs(t['bbox_h'] - b['bbox_h'])
                if waste < best_waste:
                    best_idx = i
                    best_waste = waste
        if best_idx is not None:
            rows.append((t, bottom[best_idx]))
            used_bottom.add(best_idx)
        else:
            rows.append((t, None))

    for i, b in enumerate(bottom):
        if i not in used_bottom:
            rows.append((None, b))

    placements = []
    placed_outlines = []
    y_cursor = 0.0

    for t_piece, b_piece in rows:
        row_h = max(
            t_piece['bbox_h'] if t_piece else 0,
            b_piece['bbox_h'] if b_piece else 0
        ) + gap

        if t_piece:
            px = strip_width - t_piece['bbox_w']
            py = y_cursor
            placements.append((t_piece['name'], px, py,
                               t_piece['bbox_w'], t_piece['bbox_h']))
            abs_ol = (t_piece['outline'] - t_piece['origin']
                      + np.array([px, py]))
            placed_outlines.append(abs_ol)

        if b_piece:
            px = 0.0
            py = y_cursor
            placements.append((b_piece['name'], px, py,
                               b_piece['bbox_w'], b_piece['bbox_h']))
            abs_ol = (b_piece['outline'] - b_piece['origin']
                      + np.array([px, py]))
            placed_outlines.append(abs_ol)

        y_cursor += row_h

    selvedge_height = y_cursor

    # -- Phase 2: Void-fill free pieces into selvedge zone ------------------
    if placed_outlines and free:
        void_placements, free = _void_fill(
            placed_outlines, free, strip_width, selvedge_height, gap)
        placements.extend(void_placements)
        if void_placements:
            names = [vp[0] for vp in void_placements]
            print(f"  Void fill: placed {len(void_placements)} piece(s) "
                  f"in selvedge voids ({', '.join(names)})")

    # -- Phase 3: Skyline overflow for remaining free pieces ----------------
    if free:
        skyline = _build_skyline(placements, strip_width, gap)

        # Group pairs so they land adjacent
        def _base_name(name):
            for suffix in (' L', ' R', ' (R)', ' #2'):
                if name.endswith(suffix):
                    return name[:-len(suffix)]
            return name

        from itertools import groupby
        keyed = sorted(free, key=lambda p: _base_name(p['name']))
        groups = []
        for _, g in groupby(keyed, key=lambda p: _base_name(p['name'])):
            members = sorted(g, key=lambda p: p['bbox_h'], reverse=True)
            groups.append(members)
        groups.sort(key=lambda g: g[0]['bbox_h'], reverse=True)
        free = [p for g in groups for p in g]

        sky_placements, y_cursor, _ = _skyline_place(
            skyline, free, strip_width, gap)
        placements.extend(sky_placements)

    return placements, y_cursor


# -- Piece data collection ----------------------------------------------------

def _mirror_x(outline):
    """Mirror outline across the X-axis (negate X coordinate)."""
    return np.column_stack([-outline[:, 0], outline[:, 1]])


def _uniform_sa_offset(outline, sa_cm):
    """Offset a closed CW outline outward by a uniform seam allowance.

    Uses the miter-join offset from plot_utils.offset_polyline.
    """
    from garment_programs.plot_utils import offset_polyline
    # For a closed polygon, offset the open path (drop closing duplicate)
    # then re-close.
    open_path = outline[:-1] if np.allclose(outline[0], outline[-1]) else outline
    offset = offset_polyline(open_path, sa_cm)
    return np.vstack([offset, offset[:1]])


def collect_piece_data(garment_pieces, drafts_by_module):
    """Build nestable piece list from garment definitions and draft results.

    Respects ``cut`` (number of copies, default 1) and ``mirror`` (whether
    the second copy is flipped across the grain line) from the garment config.
    Mirrored copies have their selvedge edge flipped (top↔bottom).

    Parameters
    ----------
    garment_pieces : list of dict
        Piece definitions from the garment config (module, name, kwargs).
        Optional keys: cut (int), mirror (bool).
    drafts_by_module : dict
        module_name -> return value from that module's run().

    Returns
    -------
    list of dict with keys:
        name, module, outline, origin, bbox_w, bbox_h, selvedge_edge
    """
    pieces = []
    for piece in garment_pieces:
        module_name = piece['module']
        drafts = drafts_by_module.get(module_name)
        if drafts is None:
            continue

        extractor = _OUTLINE_DISPATCH.get(module_name)
        if extractor is None:
            continue

        mod = importlib.import_module(
            f'garment_programs.SelvedgeJeans1873.{module_name}')
        seamline = extractor(mod, drafts)

        # SA outline: use module-specific SA or uniform default
        sa_extractor = _SA_OUTLINE_DISPATCH.get(module_name)
        if sa_extractor:
            sa_outline = sa_extractor(mod, drafts)
        else:
            sa_outline = _uniform_sa_offset(seamline, _DEFAULT_SA_CM)

        # Rotate so grain runs along packing Y (fabric length)
        if module_name in _GRAIN_ROTATE_90:
            seamline = _rotate_90cw(seamline)
            sa_outline = _rotate_90cw(sa_outline)

        cut = piece.get('cut', 1)
        mirror = piece.get('mirror', False)
        selvedge = _SELVEDGE_MAP.get(module_name)

        for i in range(cut):
            if i == 1 and mirror:
                sl = _mirror_x(seamline)
                sa = _mirror_x(sa_outline)
                name = piece['name'] + ' (R)'
                sel = _SELVEDGE_FLIP.get(selvedge) if selvedge else None
            elif i >= 1:
                sl = seamline.copy()
                sa = sa_outline.copy()
                name = piece['name'] + f' #{i+1}'
                sel = selvedge
            else:
                sl = seamline
                sa = sa_outline
                name = piece['name']
                sel = selvedge

            # Bbox and origin from SA outline (the cut boundary)
            xmin, ymin = sa.min(axis=0)
            xmax, ymax = sa.max(axis=0)

            pieces.append({
                'name': name,
                'module': module_name,
                'outline': sa,       # cut line (SA boundary) — used for packing
                'seamline': sl,      # seamline — drawn lighter inside
                'origin': np.array([xmin, ymin]),
                'bbox_w': xmax - xmin,
                'bbox_h': ymax - ymin,
                'selvedge_edge': sel,
                'cut': cut,          # total copies of this piece
            })

    return pieces


# -- Rendering ----------------------------------------------------------------

def render_nested(pieces, placements, total_height, strip_width,
                  output_path, units='cm'):
    """Draw all pieces at their packed positions on a single sheet.

    Parameters
    ----------
    pieces : list of dict
        Piece data from collect_piece_data().
    placements : list of (name, x, y, w, h)
        Packing results from nest_pack().
    total_height : float
        Total strip height in cm.
    strip_width : float
        Strip width in cm.
    output_path : str
        File path for the output SVG/PDF.
    units : str
        'cm' or 'inch'.
    """
    from garment_programs.plot_utils import save_pattern, CM_PER_INCH

    s = 1 / CM_PER_INCH if units == 'inch' else 1.0
    piece_map = {p['name']: p for p in pieces}

    fig, ax = plt.subplots(1, 1, figsize=(16, 10))

    # Horizontal layout: fabric length along x, fabric width along y.
    # The packer places pieces with px along strip_width and py along
    # strip length, so we swap x↔y when rendering.
    for name, px, py, w, h in placements:
        piece = piece_map[name]
        outline = piece['outline']    # SA boundary (cut line)
        origin = piece['origin']
        offset = np.array([px, py])

        # Place in packing coords, then swap axes for horizontal view
        placed = (outline - origin + offset) * s
        ax.plot(placed[:, 1], placed[:, 0], 'k-', linewidth=1.0)

        # Draw seamline inside (if available)
        if 'seamline' in piece:
            sl = piece['seamline']
            sl_placed = (sl - origin + offset) * s
            ax.plot(sl_placed[:, 1], sl_placed[:, 0],
                    color='gray', linewidth=0.5, linestyle='--', alpha=0.5)

        # Label at center (swapped)
        cx = (py + h / 2) * s
        cy = (px + w / 2) * s
        ax.text(cx, cy, name, fontsize=6, ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white',
                          ec='none', alpha=0.7))

    # Strip boundary: length along x, width along y
    sw = strip_width * s
    th = total_height * s
    ax.plot([0, th, th, 0, 0], [0, 0, sw, sw, 0],
            color='gray', linewidth=0.8, linestyle=':', alpha=0.5)
    # Both edges are selvedge (shuttle-loom denim)
    ax.annotate('selvedge', (th / 2, -0.5 * s), fontsize=7,
                ha='center', va='top', color='gray')
    ax.annotate('selvedge', (th / 2, sw + 0.5 * s), fontsize=7,
                ha='center', va='bottom', color='gray')

    # Grain direction arrow (parallel to fabric length / x-axis)
    ax.annotate('', xy=(th * 0.55, -2.0 * s), xytext=(th * 0.45, -2.0 * s),
                arrowprops=dict(arrowstyle='->', color='#555555', lw=0.8))
    ax.text(th * 0.5, -2.8 * s, 'grain', fontsize=6, ha='center',
            va='top', color='#555555')

    ax.axis('off')
    save_pattern(fig, ax, output_path, units=units, calibration=False)


# -- Top-level entry ----------------------------------------------------------

def nest_garment(garment_pieces, drafts_by_module, output_path,
                 strip_width=78.74, units='cm'):
    """Collect pieces, pack them, and render the nested layout.

    Parameters
    ----------
    garment_pieces : list of dict
        Piece definitions from the garment config.
    drafts_by_module : dict
        module_name -> drafts dict returned by each module's run().
    output_path : str
        Output file path for the nested layout.
    strip_width : float
        Fabric strip width in cm (default 78.74 cm = 31" selvedge).
    units : str
        Display units ('cm' or 'inch').
    """
    pieces = collect_piece_data(garment_pieces, drafts_by_module)
    if not pieces:
        print("No pieces to nest.")
        return

    placements, total_height = nest_pack(pieces, strip_width)
    render_nested(pieces, placements, total_height, strip_width,
                  output_path, units=units)

    total_area = sum(p['bbox_w'] * p['bbox_h'] for p in pieces)
    strip_area = strip_width * total_height
    utilization = total_area / strip_area * 100 if strip_area > 0 else 0
    print(f"Nested {len(pieces)} pieces: "
          f"strip {strip_width:.0f} x {total_height:.1f} cm, "
          f"{utilization:.0f}% utilization")
