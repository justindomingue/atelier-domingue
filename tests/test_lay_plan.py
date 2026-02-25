import json
import tempfile
import unittest
from pathlib import Path

from garment_programs.lay_plan import (
    _extract_outline_polygon,
    _parse_svg_path_data,
    _select_layout_candidate,
)


class LayPlanParserTests(unittest.TestCase):
    def test_parse_svg_path_handles_curves_and_close(self):
        d = "M 0 0 C 5 0 5 10 10 10 L 10 0 Z"
        verts, closed = _parse_svg_path_data(d)
        self.assertTrue(closed)
        self.assertGreater(len(verts), 5)

    def test_parse_svg_path_open_polyline(self):
        d = "M 0 0 L 10 0 L 10 10"
        verts, closed = _parse_svg_path_data(d)
        self.assertFalse(closed)
        self.assertEqual(verts[0], (0.0, 0.0))
        self.assertEqual(verts[-1], (10.0, 10.0))

    def test_select_layout_candidate_prefers_label(self):
        candidates = [
            (100.0, 0, {}, False, "a"),
            (80.0, 1, {}, False, "b"),
        ]
        chosen = _select_layout_candidate(candidates, preferred_label="a")
        self.assertEqual(chosen[4], "a")

        chosen_shortest = _select_layout_candidate(candidates, preferred_label=None)
        self.assertEqual(chosen_shortest[4], "b")

    def test_extract_outline_uses_sidecar_when_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            svg = Path(tmpdir) / "piece.svg"
            sidecar = Path(tmpdir) / "piece.outline.json"
            svg.write_text("not parsed because sidecar exists")
            sidecar.write_text(
                json.dumps(
                    {
                        "polygon": [[0, 0], [10, 0], [10, 5], [0, 5]],
                        "pad_x": 0.25,
                        "pad_y": 0.5,
                    }
                )
            )
            poly, pad_x, pad_y = _extract_outline_polygon(svg)
            self.assertEqual(len(poly), 4)
            self.assertAlmostEqual(pad_x, 0.25)
            self.assertAlmostEqual(pad_y, 0.5)


if __name__ == '__main__':
    unittest.main()
