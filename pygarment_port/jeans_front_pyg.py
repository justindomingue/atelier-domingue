"""Jeans Front Panel — pygarment version.

Replicates the geometry from jeans_front.py using pygarment's
Panel / Edge / CurveEdge API for serialization (JSON + SVG) and stitching.
"""
import yaml
import numpy as np
from pathlib import Path

import pygarment as pyg
from pygarment.pattern.wrappers import VisPattern

INCH = 2.54  # cm per inch


def load_measurements(yaml_path):
    """Load measurements from YAML, converting inches to cm."""
    with open(yaml_path) as f:
        raw = yaml.safe_load(f)['measurements']

    unit = raw.get('unit', 'inch')
    scale = INCH if unit == 'inch' else 1.0

    m = {}
    for key, val in raw.items():
        if key == 'unit':
            continue
        m[key] = val * scale
    return m


def compute_front_points(m):
    """Compute all front-panel construction points from measurements.

    Shared by both front and back panels (the back is drafted relative
    to the front).  Returns a dict of numpy arrays keyed by point name.
    """
    pt0 = np.array([0.0, 0.0])
    pt1 = np.array([-m['side_length'], 0.0])
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

    return {
        '0': pt0, '1': pt1, '2': pt2, '3': pt3, '4': pt4,
        "0'": pt0_drop, "3'": pt3_drop,
        '5': pt5, '6': pt6, '7': pt7, '8': pt8,
        "1'": pt1_adj, "7'": pt7_adj,
    }


class JeansFrontPanel(pyg.Panel):
    """Historical jeans front panel (1873 style) as a pygarment Panel.

    The geometry exactly reproduces jeans_front.draft_jeans_front(),
    re-expressed as pygarment Edge / CurveEdge objects forming a single
    closed edge loop.
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

        fp = compute_front_points(m)
        pt0, pt1, pt4 = fp['0'], fp['1'], fp['4']
        pt0_drop, pt3_drop = fp["0'"], fp["3'"]
        pt5, pt6, pt8 = fp['5'], fp['6'], fp['8']
        pt1_adj, pt7_adj = fp["1'"], fp["7'"]

        # === Bezier control points ===

        # Hip curve: 1' → 4 (cubic)
        hip_curve_end = pt4.copy()
        dist_14 = np.linalg.norm(hip_curve_end - pt1_adj)
        rise_1 = hip_curve_end[1] - pt1_adj[1]
        hip_cp1 = pt1_adj + np.array([dist_14 / 3, rise_1])
        hip_cp2 = hip_curve_end - np.array([dist_14 / 3, 0])

        # Rise curve: original 1' → 7', need 7' → 1' (reverse control points)
        y_arm = abs(pt7_adj[1] - pt1_adj[1]) / 3
        rise_cp1 = pt7_adj + np.array([0.0, y_arm])
        rise_cp2 = pt1_adj + np.array([0.0, -y_arm])

        # Crotch curve: original 8 → 6 (quadratic), need 6 → 8
        dist_5to6 = np.linalg.norm(pt6 - pt5)
        half_dist = dist_5to6 / 2
        pt9 = pt5 + half_dist * np.array([-np.cos(np.pi / 4),
                                           -np.sin(np.pi / 4)])
        crotch_ctrl = 2 * pt9 - 0.5 * (pt8 + pt6)

        # Inseam curve: original 6 → 3' (cubic), need 3' → 6
        dir_6_to_3 = pt3_drop - pt6
        dir_6_to_3_norm = dir_6_to_3 / np.linalg.norm(dir_6_to_3)
        angle = np.radians(20)
        inseam_tan_at_6 = np.array([
            dir_6_to_3_norm[0] * np.cos(angle)
            - dir_6_to_3_norm[1] * np.sin(angle),
            dir_6_to_3_norm[0] * np.sin(angle)
            + dir_6_to_3_norm[1] * np.cos(angle),
        ])
        inseam_straight_dir = pt0_drop - pt3_drop
        inseam_straight_dir_norm = (inseam_straight_dir
                                    / np.linalg.norm(inseam_straight_dir))
        dist_63 = np.linalg.norm(pt3_drop - pt6)
        # Reverse control point order for 3' → 6 direction
        inseam_cp1 = pt3_drop - inseam_straight_dir_norm * (dist_63 / 4)
        inseam_cp2 = pt6 + inseam_tan_at_6 * (dist_63 / 4)

        # === Build shared vertices (lists for reference identity) ===
        v_1p = pt1_adj.tolist()
        v_4 = pt4.tolist()
        v_0 = pt0.tolist()
        v_0p = pt0_drop.tolist()
        v_3p = pt3_drop.tolist()
        v_6 = pt6.tolist()
        v_8 = pt8.tolist()
        v_7p = pt7_adj.tolist()

        # === Build edges (closed loop: 1'→4→0→0'→3'→6→8→7'→1') ===

        hip_edge = pyg.CurveEdge(
            v_1p, v_4,
            control_points=[hip_cp1.tolist(), hip_cp2.tolist()],
            relative=False,
        )

        side_seam = pyg.Edge(hip_edge.end, v_0)

        hem_edge = pyg.Edge(side_seam.end, v_0p)

        lower_inseam = pyg.Edge(hem_edge.end, v_3p)

        inseam_edge = pyg.CurveEdge(
            lower_inseam.end, v_6,
            control_points=[inseam_cp1.tolist(), inseam_cp2.tolist()],
            relative=False,
        )

        crotch_edge = pyg.CurveEdge(
            inseam_edge.end, v_8,
            control_points=[crotch_ctrl.tolist()],
            relative=False,
        )

        fly_edge = pyg.Edge(crotch_edge.end, v_7p)

        rise_edge = pyg.CurveEdge(
            fly_edge.end, hip_edge.start,  # closes the loop back to 1'
            control_points=[rise_cp1.tolist(), rise_cp2.tolist()],
            relative=False,
        )

        # === Assemble edge loop ===
        self.edges = pyg.EdgeSequence(
            hip_edge, side_seam, hem_edge, lower_inseam,
            inseam_edge, crotch_edge, fly_edge, rise_edge,
        )

        # === Interfaces (for future stitching) ===
        self.interfaces = {
            'outseam': pyg.Interface(
                self, pyg.EdgeSequence(hip_edge, side_seam)),
            'hem': pyg.Interface(self, hem_edge),
            'inseam': pyg.Interface(
                self, pyg.EdgeSequence(lower_inseam, inseam_edge)),
            'crotch': pyg.Interface(self, crotch_edge),
            'fly': pyg.Interface(self, fly_edge),
            'waist': pyg.Interface(self, rise_edge),
        }


def run(measurements_path=None, output_dir='Logs'):
    """Load measurements, build the panel, and serialize to JSON + SVG.

    Parameters
    ----------
    measurements_path : str or Path, optional
        Path to a YAML measurements file.  Defaults to the bundled
        ``justin_1873_jeans.yaml`` next to this module.
    output_dir : str or Path
        Directory under which output files are written.
    """
    if measurements_path is None:
        measurements_path = (
            Path(__file__).resolve().parent.parent.parent
            / 'measurements' / 'justin_1873_jeans.yaml'
        )

    m = load_measurements(measurements_path)
    panel = JeansFrontPanel('jeans_front', m)

    # Assemble into a serializable pattern and serialize
    pattern = panel.assembly()

    # Upgrade to VisPattern for SVG output
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
