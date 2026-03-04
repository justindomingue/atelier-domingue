"""Generate a fully parametric Seamly2D .sm2d pattern for the 1873 Jeans Front.

Approach B: All drafting logic lives in Seamly2D's formula system. Point
positions, curve tangents, and lengths are Seamly2D formulas referencing
measurement variables. Feeding in different .smis measurements re-resolves
everything automatically.

Coordinate system (matching Seamly2D screen):
    X increases rightward  → we use this for "across the body" (inseam direction)
    Y increases downward   → we use this for "along the leg" (waist toward hem)

So pt0 (hem) is at the bottom, pt1 (waist) is above, and widths go right.
"""

import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path

INCH = "2.54"


def _indent_xml(root: ET.Element) -> str:
    rough = ET.tostring(root, encoding="unicode", xml_declaration=True)
    dom = minidom.parseString(rough)
    return dom.toprettyxml(indent="    ").replace(
        '<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>'
    )


class IdAlloc:
    def __init__(self):
        self._n = 1
    def next(self) -> int:
        v = self._n; self._n += 1; return v


CUSTOM_DEFAULTS = {
    "wb": f"1.5*{INCH}",
    "hemW": f"18*{INCH}",
    "kneeW": f"20*{INCH}",
}


def build_jeans_front(measurements_path: str, custom_measurements: dict | None = None) -> str:
    ids = IdAlloc()
    root = ET.Element("pattern")
    ET.SubElement(root, "version").text = "0.6.0"
    ET.SubElement(root, "unit").text = "cm"
    ET.SubElement(root, "description").text = "1873 Selvedge Jeans — Front Panel (parametric)"
    ET.SubElement(root, "notes")
    ET.SubElement(root, "measurements").text = measurements_path

    cm = custom_measurements or {}

    increments = ET.SubElement(root, "increments")
    for name, default_formula, desc in [
        ("wb", CUSTOM_DEFAULTS["wb"], "Waistband width"),
        ("hemW", CUSTOM_DEFAULTS["hemW"], "Hem opening full width"),
        ("kneeW", CUSTOM_DEFAULTS["kneeW"], "Knee opening full width"),
        ("saS", f"0.75*{INCH}", "SA side seam"),
        ("saH", f"2.375*{INCH}", "SA hem"),
        ("saI", f"0.375*{INCH}", "SA inseam"),
        ("saC", f"0.375*{INCH}", "SA crotch"),
        ("saF", f"0.75*{INCH}", "SA fly"),
        ("saW", f"0.375*{INCH}", "SA waist"),
    ]:
        formula = cm.get(name, default_formula)
        inc = ET.SubElement(increments, "increment")
        inc.set("name", f"#{name}")
        inc.set("formula", str(formula))
        inc.set("description", desc)

    draw = ET.SubElement(root, "draw")
    draw.set("name", "JeansFront")
    calc = ET.SubElement(draw, "calculation")
    modeling = ET.SubElement(draw, "modeling")
    details = ET.SubElement(draw, "details")

    MX, MY = "0.13", "0.26"

    def pt_single(name, x, y):
        pid = ids.next()
        e = ET.SubElement(calc, "point")
        for k, v in [("id", str(pid)), ("type", "single"), ("name", name),
                      ("x", str(x)), ("y", str(y)), ("mx", MX), ("my", MY)]:
            e.set(k, v)
        return pid

    def pt_end(name, base, angle, length, style="none", color="black"):
        pid = ids.next()
        e = ET.SubElement(calc, "point")
        for k, v in [("id", str(pid)), ("type", "endLine"), ("name", name),
                      ("basePoint", str(base)), ("angle", str(angle)),
                      ("length", str(length)), ("typeLine", style),
                      ("lineColor", color), ("mx", MX), ("my", MY)]:
            e.set(k, v)
        return pid

    def pt_along(name, first, second, length, style="none", color="black"):
        pid = ids.next()
        e = ET.SubElement(calc, "point")
        for k, v in [("id", str(pid)), ("type", "alongLine"), ("name", name),
                      ("firstPoint", str(first)), ("secondPoint", str(second)),
                      ("length", str(length)), ("typeLine", style),
                      ("lineColor", color), ("mx", MX), ("my", MY)]:
            e.set(k, v)
        return pid

    def ln(p1, p2, style="none", color="black"):
        lid = ids.next()
        e = ET.SubElement(calc, "line")
        for k, v in [("id", str(lid)), ("firstPoint", str(p1)),
                      ("secondPoint", str(p2)), ("typeLine", style),
                      ("lineColor", color)]:
            e.set(k, v)
        return lid

    def spl(pt1, pt4, a1, l1, a2, l2, color="black", pen="hair"):
        sid = ids.next()
        e = ET.SubElement(calc, "spline")
        for k, v in [("id", str(sid)), ("type", "simpleInteractive"),
                      ("point1", str(pt1)), ("point4", str(pt4)),
                      ("angle1", str(a1)), ("length1", str(l1)),
                      ("angle2", str(a2)), ("length2", str(l2)),
                      ("color", color), ("penStyle", pen)]:
            e.set(k, v)
        return sid

    def m_pt(cid):
        mid = ids.next()
        e = ET.SubElement(modeling, "point")
        for k, v in [("id", str(mid)), ("idObject", str(cid)),
                      ("inUse", "true"), ("type", "modeling")]:
            e.set(k, v)
        return mid

    def m_spl(cid):
        mid = ids.next()
        e = ET.SubElement(modeling, "spline")
        for k, v in [("id", str(mid)), ("idObject", str(cid)),
                      ("inUse", "true"), ("type", "modelingSpline")]:
            e.set(k, v)
        return mid

    # =========================================================================
    # Coordinate system:
    #   Origin = waist/outseam corner (pt1_adj in original)
    #   X increases right → across body (widths)
    #   Y increases down → along leg toward hem
    # This puts waist at top, hem at bottom, outseam on left, inseam on right.
    # =========================================================================

    # --- A: Origin (waist/outseam corner, adjusted) ---
    A = pt_single("A", 0, 0)

    # --- B: Hem end of outseam ---
    # Distance from waist to hem = side_length - waistband - 3/8" adjustment
    # Original: pt0 is at [0,0], pt1_adj is at [-(side_length - wb), -3/8"]
    # So distance from pt1_adj to pt0 along x = side_length - wb
    # But pt0 is also shifted in y by the 3/8" adjustment.
    # For simplicity, let's measure: the outseam runs from waist to hem
    # vertically (in our Y-axis).
    B = pt_end("B", A, "270", f"leg_waist_side_to_floor - #wb", style="hair")

    # --- C: Seat level on outseam ---
    # Original pt4 is at x = -(inseam - seat/12) from hem.
    # Distance from waist (A) to seat = (side_length - wb) - (inseam - seat/12)
    # = leg_waist_side_to_floor - #wb - leg_crotch_to_floor + hip_circ/12
    C = pt_end("C", A, "270",
               f"leg_waist_side_to_floor - #wb - leg_crotch_to_floor + (hip_circ/2)/6",
               style="dashLine", color="blue")

    # --- D: Crotch level on outseam ---
    # Distance from waist to crotch = side_length - wb - inseam... wait, this
    # doesn't account for the 3/8" adjustment. Let me recalculate.
    # Original: pt2 = [-inseam, 0], pt1_adj = [-(side_length-wb), -3/8"]
    # Distance from pt1_adj to pt2 along x = inseam - (side_length - wb)
    # But inseam < side_length - wb, so this is negative → pt2 is ABOVE pt1_adj... no.
    # Actually: side_length > inseam (41.5 > 32), so pt1 is further left (higher).
    # pt1_adj.x = -(side_length - wb) ≈ -40
    # pt2.x = -inseam = -32
    # So pt2 is to the RIGHT of pt1 (closer to hem). Distance = (side_length-wb) - inseam
    D = pt_end("D", A, "270",
               f"leg_waist_side_to_floor - #wb - leg_crotch_to_floor",
               style="hair", color="blue")

    # --- E: Knee level on outseam ---
    # Original pt3 is at x = inseam/2 - 2" from hem
    # Distance from waist to knee = (side_length-wb) - (inseam/2 - 2")
    E = pt_end("E", A, "270",
               f"leg_waist_side_to_floor - #wb - leg_crotch_to_floor/2 + 2*{INCH}",
               style="dashLine", color="blue")

    # === WIDTHS (rightward from outseam) ===

    # --- F: Waist/fly corner (pt7_adj in original) ---
    # Original: pt7 is at [pt1.x, -seat/4], pt7_adj = shifted 3/8" along 7→8 + 5/8" up
    # In our coords: from A, go right by seat/4, then adjust.
    # pt7 (before adjustment) is at seat/4 to the right of A
    F_pre = pt_end("Fp", A, "0", "hip_circ/4", style="dashLine", color="blue")

    # Seat level end of width line (pt8 in original: same y as seat level, same width)
    # pt8 is directly right of C by seat/4
    G = pt_end("G", C, "0", "hip_circ/4", style="dashLine", color="blue")

    # pt7_adj: from F_pre, shift along F_pre→G direction by 3/8", then UP by 5/8"
    F_s = pt_along("Fs", F_pre, G, f"0.375*{INCH}")
    F = pt_end("F", F_s, "90", f"0.625*{INCH}")

    # --- H: Crotch fork (pt6 in original) ---
    # pt5 = crotch level + seat/4 width, pt6 = pt5 + crotch extension downward
    H_base = pt_end("Hb", D, "0", "hip_circ/4", style="dashLine", color="blue")
    H = pt_end("H", H_base, "0", f"(hip_circ/2)/6 - 1*{INCH}")

    # --- I: Knee width point (pt3_drop in original) ---
    I = pt_end("I", E, "0", f"#kneeW/2 - 0.375*{INCH}")

    # --- J: Hem width point (pt0_drop in original) ---
    J = pt_end("J", B, "0", f"#hemW/2 - 0.375*{INCH}")

    # --- K: Crotch curve midpoint helper (pt9 in original) ---
    # pt9 = midpoint of pt5→pt6 shifted 45° inward-downward
    # In our coords: pt5 = H_base, pt6 = H
    # Midpoint of Hb→H, then shift at 315° (right-down in screen = original 45° inward-down)
    # Actually, in original: pt9 = pt5 + half_dist * [-cos45, -sin45]
    # = rightward and downward... In our coord system, original -cos45 in x = leftward,
    # original -sin45 in y = upward (since original -y = our upward)
    # Wait: I need to reconsider the coordinate mapping more carefully.

    # In original code:
    #   x-axis: negative = toward waist (left), positive = toward hem (right)
    #   y-axis: negative = toward outseam (up), positive = toward inseam (down)
    # In our Seamly2D layout:
    #   X-axis: rightward = across body (original y positive direction = inseam)
    #   Y-axis: downward = along leg toward hem (original x positive direction = hem)
    # So the mapping is: original_x → our -Y (up), original_y → our X (right)
    # Actually I set up: A at origin, B below A (toward hem) = Y increases down = original x increases
    # And widths go rightward = X increases = original y direction (negative = outseam)...
    # Hmm, let me reconsider. In original:
    #   pt0 = [0, 0] (hem, outseam baseline)
    #   pt1 = [-40, 0] (waist on outseam baseline)
    #   pt5 = [-32, -25.4] (crotch level, seat/4 AWAY from baseline toward inseam)
    # The y-axis goes NEGATIVE toward inseam. So:
    #   original y negative → our X positive (rightward) ✓ (widths go right = inseam direction)
    #   original x negative → our Y negative (upward) ✓ (waist is above hem)

    # For pt9: pt9 = pt5 + half_dist * [-cos(pi/4), -sin(pi/4)]
    # In original: [-cos45, -sin45] = move in negative-x (toward waist) AND negative-y (toward inseam)
    # In our coords: negative-x → upward (Y decreases), negative-y → rightward (X increases)
    # So pt9 is UP and to the RIGHT of midpoint of pt5→pt6
    # In Seamly2D angles: up-right = between 0° and 90° 
    # Specifically: angle = 45° (northeast in screen coords... but screen Y is down)
    # Since Seamly2D uses math angles where 0° = right, 90° = up:
    # Going right + up = angle 45° (or close to it)

    # midpoint of Hb→H
    K_mid = pt_along("Km", H_base, H, f"Line_Hb_H/2")
    # Shift at 45° (right and up in screen = X+, Y-) by half the distance
    K = pt_end("K", K_mid, "45", f"Line_Hb_H/2")

    # =========================================================================
    # CONSTRUCTION LINES (for Line_ variables and visual reference)
    # =========================================================================

    # Lines needed for distance/angle references in spline formulas
    ln(A, C, style="none")       # Line_A_C for hip curve distance
    ln(A, F, style="none")       # Line_A_F for rise curve Y-span
    ln(H, I, style="none")       # Line_H_I for inseam distance
    ln(I, J, style="none")       # Line_I_J / AngleLine_I_J for inseam tangent

    # Visual reference lines
    ln(C, G, style="dashLine", color="blue")   # seat line
    ln(D, H_base, style="dashLine", color="blue")  # hip/crotch line
    ln(E, I, style="dashLine", color="blue")   # knee line
    ln(F, G, style="dashLine", color="darkBlue")  # fly line

    # =========================================================================
    # CURVES
    # =========================================================================

    # --- 1. Hip curve: A → C ---
    # Original: cubic Bézier with
    #   CP1 = pt1_adj + [dist/3, rise_1]  (toward hem and outseam)
    #   CP2 = pt4 - [dist/3, 0]  (back toward waist along x only)
    # In our coords:
    #   CP1 direction from A: right by (rise in original y) and down by (dist/3 in original x)
    #     → angle pointing right-down ≈ AngleLine_A_C direction shifted
    #   CP2 direction from C: back up toward A along the Y-axis only
    #     → angle = 90° (upward)
    # Actually let me use helper points for the tangent directions.
    # 
    # CP1 in original = pt1_adj + [dist/3, rise_1]
    # rise_1 = pt4.y - pt1_adj.y = 0 - (-3/8") = 3/8" (tiny compared to dist/3)
    # dist = distance(pt1_adj, pt4)
    # In our coords:
    #   From A, the "dist/3" goes toward C direction (downward = 270°)
    #   The "rise_1" goes leftward (toward outseam = original positive y... wait)
    # Let me trace rise_1 more carefully:
    #   rise_1 = pt4[1] - pt1_adj[1] = 0 - (-3/8*INCH) = 3/8*INCH > 0
    #   In original y, positive = toward inseam
    #   In our coords, toward inseam = rightward (0°)
    # So CP1 is below-right of A: down by dist/3 and right by 3/8"
    # CP2 = pt4 - [dist/3, 0] = above pt4 by dist/3 (in original x, negative = toward waist = up in ours)
    #   In our coords: upward (90°)
    
    # Helper for CP1 direction: go down from A by dist/3, then right by 3/8"
    hip_h1 = pt_end("Ha", A, "270", f"Line_A_C/3")
    hip_h2 = pt_end("Hh", hip_h1, "0", f"0.375*{INCH}")
    # Now angle from A to hip_h2 and distance from A to hip_h2 give us tangent 1
    ln(A, hip_h2, style="none")  # for Line_A_Hh

    # For CP2: from C, go upward by dist/3
    hip_h3 = pt_end("Hc", C, "90", f"Line_A_C/3")
    ln(C, hip_h3, style="none")  # for Line_C_Hc

    hip_curve = spl(A, C,
                    f"AngleLine_A_Hh", f"Line_A_Hh",
                    f"AngleLine_C_Hc", f"Line_A_C/3")

    # --- 2. Rise curve: A → F ---
    # Original: CP1 = pt1_adj + [0, -y_arm] where y_arm = |pt7_adj.y - pt1_adj.y| / 3
    # In original: [0, -y_arm] = no x change, move toward inseam (negative y)
    # In our coords: toward inseam = rightward (0°)
    # CP2 = pt7_adj + [0, +y_arm] = move away from inseam (positive y) = leftward (180°)
    # y_arm = distance between A and F divided by... actually it's the Y-component only.
    # In original: |pt7_adj[1] - pt1_adj[1]| = the width difference
    # In our coords: this is the X-distance between A and F
    # Since both A and F have Y components too, the X-distance alone:
    #   A is at (0,0), F is roughly at (seat/4 + adjustments, small adjustment)
    # For simplicity, use Line_A_F / 3 as the arm length (close enough — the 
    # original also uses 1/3 of the span)
    rise_curve = spl(A, F,
                     "0", f"Line_A_F/3",
                     "180", f"Line_A_F/3")

    # --- 3. Crotch curve: G → H ---
    # Using K (pt9 midpoint helper) for tangent directions
    # Tangent at G toward K, tangent at H toward K
    # Length = 2/3 of distance to K (from degree-elevation of quadratic)
    ln(G, K, style="none")
    ln(H, K, style="none")
    crotch_curve = spl(G, H,
                       f"AngleLine_G_K", f"Line_G_K*2/3",
                       f"AngleLine_H_K", f"Line_H_K*2/3")

    # --- 4. Inseam curve: H → I ---
    # Tangent at H: direction from H toward I, rotated -20° (CW)
    # Tangent at I: direction from I toward J (toward hem along inseam)
    # Lengths: dist(H,I) / 4
    inseam_curve = spl(H, I,
                       f"AngleLine_H_I - 20", f"Line_H_I/4",
                       f"AngleLine_I_J", f"Line_H_I/4")

    # =========================================================================
    # OUTLINE LINES (straight segments of the pattern piece)
    # =========================================================================
    ln(C, B, style="none")    # outseam: seat to hem
    ln(B, J, style="none")    # hem
    ln(G, F, style="none")    # fly

    # =========================================================================
    # DETAIL PIECE
    # =========================================================================
    # CW winding: A → hip → C → B → J → I → inseam(rev) → H → crotch(rev) → G → F → rise(rev) → A

    mA   = m_pt(A)
    mHip = m_spl(hip_curve)
    mC   = m_pt(C)
    mB   = m_pt(B)
    mJ   = m_pt(J)
    mI   = m_pt(I)
    mIns = m_spl(inseam_curve)
    mH   = m_pt(H)
    mCro = m_spl(crotch_curve)
    mG   = m_pt(G)
    mF   = m_pt(F)
    mRis = m_spl(rise_curve)

    detail = ET.SubElement(details, "detail")
    did = ids.next()
    detail.set("id", str(did))
    detail.set("name", "Jeans Front")
    detail.set("closed", "1")
    detail.set("inLayout", "true")
    detail.set("seamAllowance", "true")
    detail.set("width", "1")
    detail.set("forbidFlipping", "false")
    detail.set("mx", "0")
    detail.set("my", "0")

    data = ET.SubElement(detail, "data")
    for k, v in [("letter", ""), ("visible", "false"), ("fontSize", "0"),
                 ("mx", "0"), ("my", "0"), ("width", "1"), ("height", "1"),
                 ("rotation", "0"), ("onFold", "false"), ("annotation", ""),
                 ("orientation", ""), ("rotationWay", ""), ("tilt", ""),
                 ("foldPosition", "")]:
        data.set(k, v)

    pi = ET.SubElement(detail, "patternInfo")
    for k, v in [("visible", "false"), ("fontSize", "0"), ("mx", "0"),
                 ("my", "0"), ("width", "1"), ("height", "1"), ("rotation", "0")]:
        pi.set(k, v)

    gl = ET.SubElement(detail, "grainline")
    for k, v in [("visible", "true"), ("arrows", "0"), ("length", "15"),
                 ("mx", "0"), ("my", "0"), ("rotation", "90")]:
        gl.set(k, v)

    nodes = ET.SubElement(detail, "nodes")

    def nd(obj, ntype="NodePoint", rev=False, bef=None, aft=None):
        n = ET.SubElement(nodes, "node")
        n.set("idObject", str(obj))
        n.set("type", ntype)
        if rev:
            n.set("reverse", "1")
        if bef is not None:
            n.set("before", str(bef))
        if aft is not None:
            n.set("after", str(aft))

    nd(mHip, "NodeSpline")
    nd(mC, aft="#saS")
    nd(mB, bef="#saS", aft="#saH")
    nd(mJ, bef="#saH", aft="#saI")
    nd(mI, bef="#saI")
    nd(mIns, "NodeSpline", rev=True)
    nd(mH, aft="#saC")
    nd(mCro, "NodeSpline", rev=True)
    nd(mG, bef="#saC", aft="#saF")
    nd(mF, bef="#saF", aft="#saW")
    nd(mRis, "NodeSpline", rev=True)
    nd(mA, bef="#saW", aft="#saS")

    return _indent_xml(root)


def generate(yaml_path: str, output_path: str, measurements_smis: str):
    xml = build_jeans_front(measurements_smis)
    with open(output_path, "w") as f:
        f.write(xml)
    print(f"Generated parametric pattern: {output_path}")


if __name__ == "__main__":
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else "measurements/justin_1873_jeans.yaml"
    output = sys.argv[2] if len(sys.argv) > 2 else "seamly2d_port/jeans_front.sm2d"
    smis = sys.argv[3] if len(sys.argv) > 3 else "justin_measurements.smis"
    generate(yaml_path, output, smis)
