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


def skyline_pack(pieces, fabric_width, gap=0.25):
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

    Returns
    -------
    positions : dict
        {name: (x, y)} placement positions (top-left corner, y-down).
    total_length : float
        Total fabric length needed (inches, x-extent).
    """
    if not pieces:
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
    skyline = [(0.0, fabric_width, 0.0)]
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
    return positions, total_length


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
            # Selvedge piece — outseam is at SVG top (y=0).
            # First copy: top edge on top selvedge (y=0) — no flip.
            # Second copy: flipped vertically so outseam is at bottom selvedge.
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
                               svg_path, base_transform, 'top'))
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

    # --- Pack ---
    pack_input = [(name, grain_len, cross_w, edge)
                  for name, grain_len, cross_w, _, _, edge in pieces]
    positions, total_length = skyline_pack(pack_input, fabric_width, gap=gap)

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
