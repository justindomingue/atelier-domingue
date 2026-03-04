"""Generate a Seamly2D .sm2d pattern for the 1873 Jeans Front panel.

Uses the existing Atelier Domingue drafting function to compute all geometry,
then translates the results into Seamly2D XML via the pattern_generator module.
"""

import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from garment_programs.geometry import INCH
from garment_programs.measurements import load_measurements
from garment_programs.SelvedgeJeans1873.jeans_front import draft_jeans_front
from seamly2d_port.pattern_generator import (
    Sm2dBuilder, control_points_to_seamly, quadratic_to_cubic,
)
from seamly2d_port.measurements import load_yaml_measurements, to_cm, build_increments_xml


def _rebuild_control_points(m: dict) -> dict:
    """Recompute the Bézier control points from the drafting logic.

    The draft function returns sampled polylines (100 points each), but
    Seamly2D needs the original control points. We reconstruct them here
    by replaying the math from draft_jeans_front.
    """
    pt0 = np.array([0.0, 0.0])
    waistband = m.get('waistband_width', 1.5 * INCH)
    pt1 = np.array([-(m['side_length'] - waistband), 0.0])
    pt2 = np.array([-m['inseam'], 0.0])
    pt3 = np.array([pt2[0] / 2 - 2 * INCH, 0.0])
    pt4 = np.array([pt2[0] - (m['seat'] / 2) / 6, 0.0])

    hem_drop = m['hem_width'] / 2 - 3 / 8 * INCH
    pt0_drop = np.array([pt0[0], -hem_drop])

    knee_drop = m['knee_width'] / 2 - 3 / 8 * INCH
    pt3_drop = np.array([pt3[0], -knee_drop])

    seat_quarter = m['seat'] / 4
    pt5 = np.array([pt2[0], -seat_quarter])

    crotch_ext = (m['seat'] / 2) / 6 - 1 * INCH
    pt6 = np.array([pt5[0], pt5[1] - crotch_ext])

    pt7 = np.array([pt1[0], -seat_quarter])
    pt8 = np.array([pt4[0], -seat_quarter])

    pt1_adj = pt1.copy()
    pt1_adj[1] -= 3 / 8 * INCH

    dir_7to8 = pt8 - pt7
    dir_7to8_norm = dir_7to8 / np.linalg.norm(dir_7to8)
    pt7_shifted = pt7 + dir_7to8_norm * (3 / 8 * INCH)
    pt7_adj = pt7_shifted.copy()
    pt7_adj[1] += 5 / 8 * INCH

    dist_5to6 = np.linalg.norm(pt6 - pt5)
    half_dist = dist_5to6 / 2
    pt9 = pt5 + half_dist * np.array([-np.cos(np.pi / 4), -np.sin(np.pi / 4)])

    dist_14 = np.linalg.norm(pt4 - pt1_adj)
    rise_1 = pt4[1] - pt1_adj[1]
    hip_cp1 = pt1_adj + np.array([dist_14 / 3, rise_1])
    hip_cp2 = pt4 - np.array([dist_14 / 3, 0])

    y_arm = abs(pt7_adj[1] - pt1_adj[1]) / 3
    rise_cp1 = pt1_adj + np.array([0.0, -y_arm])
    rise_cp2 = pt7_adj + np.array([0.0, y_arm])

    crotch_ctrl_quad = 2 * pt9 - 0.5 * (pt8 + pt6)
    _, crotch_cp1, crotch_cp2, _ = quadratic_to_cubic(pt8, crotch_ctrl_quad, pt6)

    dir_6_to_3 = pt3_drop - pt6
    dir_6_to_3_norm = dir_6_to_3 / np.linalg.norm(dir_6_to_3)
    angle = np.radians(20)
    inseam_tan_at_6 = np.array([
        dir_6_to_3_norm[0] * np.cos(angle) - dir_6_to_3_norm[1] * np.sin(angle),
        dir_6_to_3_norm[0] * np.sin(angle) + dir_6_to_3_norm[1] * np.cos(angle)
    ])
    inseam_straight_dir = pt0_drop - pt3_drop
    inseam_straight_dir_norm = inseam_straight_dir / np.linalg.norm(inseam_straight_dir)
    dist_63 = np.linalg.norm(pt3_drop - pt6)
    inseam_cp1 = pt6 + inseam_tan_at_6 * (dist_63 / 4)
    inseam_cp2 = pt3_drop - inseam_straight_dir_norm * (dist_63 / 4)

    return {
        'points': {
            '0': pt0, '1_adj': pt1_adj, '4': pt4, '0_drop': pt0_drop,
            '3_drop': pt3_drop, '5': pt5, '6': pt6, '7_adj': pt7_adj,
            '8': pt8,
        },
        'curves': {
            'hip': {'P0': pt1_adj, 'CP1': hip_cp1, 'CP2': hip_cp2, 'P3': pt4},
            'rise': {'P0': pt1_adj, 'CP1': rise_cp1, 'CP2': rise_cp2, 'P3': pt7_adj},
            'crotch': {'P0': pt8, 'CP1': crotch_cp1, 'CP2': crotch_cp2, 'P3': pt6},
            'inseam': {'P0': pt6, 'CP1': inseam_cp1, 'CP2': inseam_cp2, 'P3': pt3_drop},
        },
    }


def generate_jeans_front_sm2d(
    yaml_path: str,
    output_path: str,
    measurements_smis: str = "justin_measurements.smis",
):
    """Generate a .sm2d pattern file for the 1873 jeans front panel."""
    m = load_measurements(yaml_path)
    cp = _rebuild_control_points(m)

    raw_m, unit = load_yaml_measurements(yaml_path)
    custom_increments = build_increments_xml(raw_m, unit)

    builder = Sm2dBuilder(measurements_smis, unit="cm")
    for name, formula in custom_increments:
        builder.add_increment(name, formula)

    piece = builder.new_piece("JeansFront")
    piece.set_seam_allowance(1.0)
    piece.set_grainline(rotation=90, length=15, visible=True)

    pts = cp['points']
    curves = cp['curves']

    pt_ids = {}
    for name, coord in [
        ("A", pts['1_adj']),
        ("B", pts['4']),
        ("C", pts['0']),
        ("D", pts['0_drop']),
        ("E", pts['3_drop']),
        ("F", pts['6']),
        ("G", pts['8']),
        ("H", pts['7_adj']),
    ]:
        pt_ids[name] = piece.add_single_point(name, coord[0], coord[1])

    hip_angles = control_points_to_seamly(
        curves['hip']['P0'], curves['hip']['CP1'],
        curves['hip']['CP2'], curves['hip']['P3'])
    hip_id = piece.add_cubic_spline(
        pt_ids['A'], pt_ids['B'],
        hip_angles[0], hip_angles[1],
        hip_angles[2], hip_angles[3])

    rise_angles = control_points_to_seamly(
        curves['rise']['P0'], curves['rise']['CP1'],
        curves['rise']['CP2'], curves['rise']['P3'])
    rise_id = piece.add_cubic_spline(
        pt_ids['A'], pt_ids['H'],
        rise_angles[0], rise_angles[1],
        rise_angles[2], rise_angles[3])

    crotch_angles = control_points_to_seamly(
        curves['crotch']['P0'], curves['crotch']['CP1'],
        curves['crotch']['CP2'], curves['crotch']['P3'])
    crotch_id = piece.add_cubic_spline(
        pt_ids['G'], pt_ids['F'],
        crotch_angles[0], crotch_angles[1],
        crotch_angles[2], crotch_angles[3])

    inseam_angles = control_points_to_seamly(
        curves['inseam']['P0'], curves['inseam']['CP1'],
        curves['inseam']['CP2'], curves['inseam']['P3'])
    inseam_id = piece.add_cubic_spline(
        pt_ids['F'], pt_ids['E'],
        inseam_angles[0], inseam_angles[1],
        inseam_angles[2], inseam_angles[3])

    piece.add_line(pt_ids['B'], pt_ids['C'], line_style="none")
    piece.add_line(pt_ids['D'], pt_ids['E'], line_style="none")
    piece.add_line(pt_ids['C'], pt_ids['D'], line_style="none")
    piece.add_line(pt_ids['G'], pt_ids['H'], line_style="none")

    SA_SIDE = 1.905
    SA_HEM = 6.0325
    SA_INSEAM = 0.9525
    SA_CROTCH = 0.9525
    SA_FLY = 1.905
    SA_WAIST = 0.9525

    piece.add_spline_to_detail(hip_id)
    piece.add_point_to_detail(pt_ids['B'], sa_after=SA_SIDE)
    piece.add_point_to_detail(pt_ids['C'], sa_before=SA_SIDE, sa_after=SA_HEM)
    piece.add_point_to_detail(pt_ids['D'], sa_before=SA_HEM, sa_after=SA_INSEAM)
    piece.add_point_to_detail(pt_ids['E'], sa_before=SA_INSEAM)
    piece.add_spline_to_detail(inseam_id, reverse=True)
    piece.add_point_to_detail(pt_ids['F'], sa_after=SA_CROTCH)
    piece.add_spline_to_detail(crotch_id, reverse=True)
    piece.add_point_to_detail(pt_ids['G'], sa_before=SA_CROTCH, sa_after=SA_FLY)
    piece.add_point_to_detail(pt_ids['H'], sa_before=SA_FLY, sa_after=SA_WAIST)
    piece.add_spline_to_detail(rise_id, reverse=True)
    piece.add_point_to_detail(pt_ids['A'], sa_before=SA_WAIST, sa_after=SA_SIDE)

    xml_str = builder.to_xml()
    with open(output_path, "w") as f:
        f.write(xml_str)

    print(f"Generated: {output_path}")
    return output_path


if __name__ == "__main__":
    yaml_path = sys.argv[1] if len(sys.argv) > 1 else "measurements/justin_1873_jeans.yaml"
    output = sys.argv[2] if len(sys.argv) > 2 else "seamly2d_port/jeans_front.sm2d"
    smis = sys.argv[3] if len(sys.argv) > 3 else "justin_measurements.smis"
    generate_jeans_front_sm2d(yaml_path, output, smis)
