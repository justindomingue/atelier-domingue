"""Jeans Back Panel — pygarment version.

Replicates the geometry from jeans_back.py using pygarment's
Panel / Edge / CurveEdge API.  Drafted relative to the front panel,
same as the original.
"""
import numpy as np
from pathlib import Path

import pygarment as pyg
from pygarment.pattern.wrappers import VisPattern

from .jeans_front_pyg import INCH, load_measurements, compute_front_points


class JeansBackPanel(pyg.Panel):
    """Historical jeans back panel (1873 style) as a pygarment Panel.

    Built on top of the front construction points, matching
    jeans_back.draft_jeans_back().
    """

    def __init__(self, name, m):
        """
        Parameters
        ----------
        name : str
            Unique panel name.
        m : dict
            Measurements in cm (output of load_measurements).
        """
        super().__init__(name)

        # Front construction points (back is drafted relative to front)
        fp = compute_front_points(m)
        pt0, pt1, pt2, pt4 = fp['0'], fp['1'], fp['2'], fp['4']
        pt0_drop, pt3_drop = fp["0'"], fp["3'"]
        pt6, pt8 = fp['6'], fp['8']
        pt1_adj, pt7_adj = fp["1'"], fp["7'"]

        # === Back-specific construction (same as draft_jeans_back) ===

        # Step 1 — back leg widths: extend hem and knee by 3/4"
        ext = 3 / 4 * INCH
        back_hem = pt0_drop + np.array([0, -ext])
        pt12 = pt3_drop + np.array([0, -ext])

        # Step 2 — initial pt11 position: seat/16 below pt6
        pt11_initial = pt6 + np.array([0, -(m['seat'] / 16)])

        # Steps 3-5 — adjust pt11 along 12→11 direction so that
        # dist(12,11) = dist(6,3') - 1/4"
        dir_12_to_11 = pt11_initial - pt12
        dir_12_to_11_norm = dir_12_to_11 / np.linalg.norm(dir_12_to_11)
        target_dist = np.linalg.norm(pt6 - pt3_drop) - 1 / 4 * INCH
        pt11 = pt12 + dir_12_to_11_norm * target_dist

        # Construction line from 11 through 12 to hem level
        dir_11_12 = pt12 - pt11
        t_hem = (0 - pt11[0]) / dir_11_12[0]
        back_hem_inseam = pt11 + t_hem * dir_11_12  # noqa: F841

        # Back inseam curve: original 11→12, need 12→11
        dir_11_to_12 = pt12 - pt11
        dir_11_to_12_norm = dir_11_to_12 / np.linalg.norm(dir_11_to_12)
        angle = np.radians(15)
        tan_at_11 = np.array([
            dir_11_to_12_norm[0] * np.cos(angle)
            - dir_11_to_12_norm[1] * np.sin(angle),
            dir_11_to_12_norm[0] * np.sin(angle)
            + dir_11_to_12_norm[1] * np.cos(angle),
        ])
        straight_dir = back_hem - pt12
        straight_dir_norm = straight_dir / np.linalg.norm(straight_dir)
        dist_11_12 = np.linalg.norm(dir_11_to_12)
        # Original CPs: CP1 = pt11+tan*(d/4), CP2 = pt12-straight*(d/4)
        # Reversed for 12→11: swap CP order
        inseam_cp1 = pt12 - straight_dir_norm * (dist_11_12 / 4)
        inseam_cp2 = pt11 + tan_at_11 * (dist_11_12 / 4)

        # === Seat angle ===

        new_pt2 = pt2 + np.array([-3 / 8 * INCH, 0])
        dir_4to8 = pt8 - pt4
        dir_4to8_norm = dir_4to8 / np.linalg.norm(dir_4to8)
        new_pt8 = pt8 + dir_4to8_norm * (1 * INCH)

        seat_line_dir = new_pt8 - new_pt2
        seat_line_dir_norm = seat_line_dir / np.linalg.norm(seat_line_dir)

        # Perpendicular to seat line at new_pt8, toward waist
        seat_angle_dir = np.array([seat_line_dir[1], -seat_line_dir[0]])
        seat_angle_dir_norm = seat_angle_dir / np.linalg.norm(seat_angle_dir)
        if seat_angle_dir_norm[0] > 0:
            seat_angle_dir_norm = -seat_angle_dir_norm

        # Seat/crotch curve tangent directions
        seat_to_crotch_dir = -seat_angle_dir_norm
        dist_8_11 = np.linalg.norm(pt11 - new_pt8)

        inseam_dir_at_11 = pt12 - pt11
        inseam_dir_at_11_norm = inseam_dir_at_11 / np.linalg.norm(
            inseam_dir_at_11)
        perp_inseam = np.array(
            [-inseam_dir_at_11_norm[1], inseam_dir_at_11_norm[0]])
        if np.dot(perp_inseam, new_pt8 - pt11) < 0:
            perp_inseam = -perp_inseam

        # Seat lower curve: original 8'→11, need 11→8'
        # Original CPs: CP1 = new_pt8+seat_to_crotch*(d/3),
        #               CP2 = pt11+perp_inseam*(d/3)
        # Reversed for 11→8': swap CP order
        seat_lower_cp1 = pt11 + perp_inseam * (dist_8_11 / 3)
        seat_lower_cp2 = new_pt8 + seat_to_crotch_dir * (dist_8_11 / 3)

        # === Waist seam ===

        waist_line_dir = seat_line_dir_norm.copy()
        if waist_line_dir[1] > 0:
            waist_line_dir = -waist_line_dir

        # Intersection of waist line with seat angle line
        A = np.column_stack([waist_line_dir, -seat_angle_dir_norm])
        b_vec = new_pt8 - pt1
        params = np.linalg.solve(A, b_vec)

        # Back waist width
        front_waist_width = np.linalg.norm(pt7_adj - pt1_adj)
        back_waist_target = m['waist'] / 2 + 3 / 4 * INCH
        back_waist_width = back_waist_target - front_waist_width
        back_waist_pt = pt1 + waist_line_dir * (
            back_waist_width / np.linalg.norm(waist_line_dir))

        # === Build shared vertices ===
        v_1 = pt1.tolist()
        v_4 = pt4.tolist()
        v_0 = pt0.tolist()
        v_back_hem = back_hem.tolist()
        v_12 = pt12.tolist()
        v_11 = pt11.tolist()
        v_8p = new_pt8.tolist()
        v_bw = back_waist_pt.tolist()

        # === Build edges (CW loop: 1→4→0→back_hem→12→11→8'→bw→1) ===

        outseam_upper = pyg.Edge(v_1, v_4)

        outseam_lower = pyg.Edge(outseam_upper.end, v_0)

        hem_edge = pyg.Edge(outseam_lower.end, v_back_hem)

        lower_inseam = pyg.Edge(hem_edge.end, v_12)

        back_inseam = pyg.CurveEdge(
            lower_inseam.end, v_11,
            control_points=[inseam_cp1.tolist(), inseam_cp2.tolist()],
            relative=False,
        )

        seat_lower = pyg.CurveEdge(
            back_inseam.end, v_8p,
            control_points=[seat_lower_cp1.tolist(), seat_lower_cp2.tolist()],
            relative=False,
        )

        seat_upper = pyg.Edge(seat_lower.end, v_bw)

        waist_edge = pyg.Edge(seat_upper.end, outseam_upper.start)

        # === Assemble edge loop ===
        self.edges = pyg.EdgeSequence(
            outseam_upper, outseam_lower, hem_edge, lower_inseam,
            back_inseam, seat_lower, seat_upper, waist_edge,
        )

        # === Interfaces ===
        self.interfaces = {
            'outseam': pyg.Interface(
                self, pyg.EdgeSequence(outseam_upper, outseam_lower)),
            'hem': pyg.Interface(self, hem_edge),
            'inseam': pyg.Interface(
                self, pyg.EdgeSequence(lower_inseam, back_inseam)),
            'seat': pyg.Interface(
                self, pyg.EdgeSequence(seat_lower, seat_upper)),
            'waist': pyg.Interface(self, waist_edge),
        }


def run(measurements_path=None, output_dir='Logs'):
    """Load measurements, build the back panel, and serialize to JSON + SVG."""
    if measurements_path is None:
        measurements_path = (
            Path(__file__).resolve().parent.parent.parent
            / 'measurements' / 'justin_1873_jeans.yaml'
        )

    m = load_measurements(measurements_path)
    panel = JeansBackPanel('jeans_back', m)

    pattern = panel.assembly()

    vis = VisPattern()
    vis.name = pattern.name
    vis.spec = pattern.spec
    vis.pattern = pattern.pattern
    vis.properties = pattern.properties

    log_dir = vis.serialize(
        str(output_dir),
        to_subfolder=True,
        with_3d=False,
        with_text=False,
        view_ids=False,
    )
    print(f'Serialized to {log_dir}')
    return log_dir


if __name__ == '__main__':
    run()
