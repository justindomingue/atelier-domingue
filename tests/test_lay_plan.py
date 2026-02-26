import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from garment_programs.lay_plan import (
    _counter_reflect_text_groups,
    _extract_outline_polygon,
    _parse_translate,
    _parse_svg_path_data,
    _select_layout_candidate,
    _tag,
)


class LayPlanParserTests(unittest.TestCase):
    def test_parse_translate(self):
        self.assertEqual(_parse_translate("translate(12 34)"), (12.0, 34.0))
        self.assertEqual(_parse_translate("rotate(10) translate(5.5,-2.25)"), (5.5, -2.25))
        self.assertEqual(_parse_translate("translate(9.75)"), (9.75, 0.0))
        self.assertIsNone(_parse_translate("scale(1,-1)"))

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

    def test_counter_reflect_text_groups_x(self):
        root = ET.Element(_tag('svg'))
        text_group = ET.SubElement(root, _tag('g'), {'id': 'text_1'})
        ET.SubElement(
            text_group,
            _tag('g'),
            {'transform': 'translate(12.5 34.0) scale(0.1 -0.1)'},
        )

        _counter_reflect_text_groups(root, transform='flip_h')

        wrapper = list(root)[0]
        self.assertEqual(wrapper.tag, _tag('g'))
        self.assertEqual(
            wrapper.get('transform'),
            'matrix(-1.000000 0.000000 0.000000 1.000000 25.000000 0.000000)',
        )
        self.assertIs(list(wrapper)[0], text_group)

    def test_counter_reflect_text_groups_y(self):
        root = ET.Element(_tag('svg'))
        text_group = ET.SubElement(root, _tag('g'), {'id': 'text_2'})
        ET.SubElement(
            text_group,
            _tag('g'),
            {'transform': 'translate(8, 15) scale(0.1 -0.1)'},
        )

        _counter_reflect_text_groups(root, transform='flip_v')

        wrapper = list(root)[0]
        self.assertEqual(wrapper.tag, _tag('g'))
        self.assertEqual(
            wrapper.get('transform'),
            'matrix(1.000000 0.000000 0.000000 -1.000000 0.000000 30.000000)',
        )
        self.assertIs(list(wrapper)[0], text_group)

    def test_counter_reflect_text_groups_ccw_flip_v(self):
        root = ET.Element(_tag('svg'))
        text_group = ET.SubElement(root, _tag('g'), {'id': 'text_3'})
        ET.SubElement(
            text_group,
            _tag('g'),
            {'transform': 'translate(8 15) scale(0.1 -0.1)'},
        )

        _counter_reflect_text_groups(root, transform='ccw_flip_v')

        wrapper = list(root)[0]
        self.assertEqual(wrapper.tag, _tag('g'))
        self.assertEqual(
            wrapper.get('transform'),
            'matrix(0.000000 1.000000 1.000000 0.000000 -7.000000 7.000000)',
        )
        self.assertIs(list(wrapper)[0], text_group)


if __name__ == '__main__':
    unittest.main()
