"""Generate Seamly2D .sm2d pattern files from Atelier Domingue drafting output.

Takes the computed points and curves from the existing numpy-based drafting
pipeline and translates them into Seamly2D's XML pattern format.
"""

import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path


class Sm2dBuilder:
    """Builds a Seamly2D .sm2d pattern XML document."""

    def __init__(self, measurements_path: str, unit: str = "cm"):
        self._next_id = 1
        self._unit = unit
        self._measurements_path = measurements_path
        self._draws: list[dict] = []
        self._increments: list[tuple[str, str]] = []

    def _alloc_id(self) -> int:
        obj_id = self._next_id
        self._next_id += 1
        return obj_id

    def add_increment(self, name: str, formula: str):
        self._increments.append((name, formula))

    def new_piece(self, name: str) -> "PieceBuilder":
        piece = PieceBuilder(name, self)
        self._draws.append(piece)
        return piece

    def to_xml(self) -> str:
        root = ET.Element("pattern")
        ET.SubElement(root, "version").text = "0.6.0"
        ET.SubElement(root, "unit").text = self._unit
        ET.SubElement(root, "description")
        ET.SubElement(root, "notes")
        ET.SubElement(root, "measurements").text = self._measurements_path

        increments = ET.SubElement(root, "increments")
        for inc_name, inc_formula in self._increments:
            inc = ET.SubElement(increments, "increment")
            inc.set("name", f"#{inc_name}")
            inc.set("formula", inc_formula)

        for piece in self._draws:
            piece._build_xml(root)

        rough = ET.tostring(root, encoding="unicode", xml_declaration=True)
        dom = minidom.parseString(rough)
        xml_str = dom.toprettyxml(indent="    ")
        return xml_str.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>')


class PieceBuilder:
    """Builds a single draw group (pattern piece) in the .sm2d file."""

    def __init__(self, name: str, parent: Sm2dBuilder):
        self.name = name
        self._parent = parent
        self._calc_elements: list[ET.Element] = []
        self._modeling_elements: list[ET.Element] = []
        self._detail_nodes: list[dict] = []
        self._point_ids: dict[str, int] = {}
        self._sa_width = 1.0
        self._piece_name = name
        self._grainline_rotation = 90
        self._grainline_length = 10
        self._grainline_visible = False

    def add_single_point(self, name: str, x: float, y: float) -> int:
        obj_id = self._parent._alloc_id()
        pt = ET.Element("point")
        pt.set("id", str(obj_id))
        pt.set("type", "single")
        pt.set("name", name)
        pt.set("x", str(round(x, 4)))
        pt.set("y", str(round(y, 4)))
        pt.set("mx", "0.13")
        pt.set("my", "0.26")
        self._calc_elements.append(pt)
        self._point_ids[name] = obj_id
        return obj_id

    def add_end_line_point(self, name: str, base_id: int,
                           angle: float, length: float,
                           line_style: str = "hair",
                           color: str = "black") -> int:
        obj_id = self._parent._alloc_id()
        pt = ET.Element("point")
        pt.set("id", str(obj_id))
        pt.set("type", "endLine")
        pt.set("name", name)
        pt.set("basePoint", str(base_id))
        pt.set("angle", str(round(angle, 4)))
        pt.set("length", str(round(length, 4)))
        pt.set("typeLine", line_style)
        pt.set("lineColor", color)
        pt.set("mx", "0.13")
        pt.set("my", "0.26")
        self._calc_elements.append(pt)
        self._point_ids[name] = obj_id
        return obj_id

    def add_line(self, pt1_id: int, pt2_id: int,
                 line_style: str = "hair", color: str = "black") -> int:
        obj_id = self._parent._alloc_id()
        line = ET.Element("line")
        line.set("id", str(obj_id))
        line.set("firstPoint", str(pt1_id))
        line.set("secondPoint", str(pt2_id))
        line.set("typeLine", line_style)
        line.set("lineColor", color)
        self._calc_elements.append(line)
        return obj_id

    def add_cubic_spline(self, pt1_id: int, pt4_id: int,
                         angle1: float, length1: float,
                         angle2: float, length2: float,
                         color: str = "black",
                         pen_style: str = "hair") -> int:
        obj_id = self._parent._alloc_id()
        spline = ET.Element("spline")
        spline.set("id", str(obj_id))
        spline.set("type", "simpleInteractive")
        spline.set("point1", str(pt1_id))
        spline.set("point4", str(pt4_id))
        spline.set("angle1", str(round(angle1, 4)))
        spline.set("length1", str(round(length1, 4)))
        spline.set("angle2", str(round(angle2, 4)))
        spline.set("length2", str(round(length2, 4)))
        spline.set("color", color)
        spline.set("penStyle", pen_style)
        self._calc_elements.append(spline)
        return obj_id

    def add_point_to_detail(self, calc_id: int, sa_before: float | None = None,
                            sa_after: float | None = None):
        model_id = self._parent._alloc_id()
        m = ET.Element("point")
        m.set("id", str(model_id))
        m.set("idObject", str(calc_id))
        m.set("inUse", "true")
        m.set("type", "modeling")
        self._modeling_elements.append(m)

        node_info = {"idObject": model_id, "type": "NodePoint"}
        if sa_before is not None:
            node_info["before"] = sa_before
        if sa_after is not None:
            node_info["after"] = sa_after
        self._detail_nodes.append(node_info)

    def add_spline_to_detail(self, calc_id: int, reverse: bool = False):
        model_id = self._parent._alloc_id()
        m = ET.Element("spline")
        m.set("id", str(model_id))
        m.set("idObject", str(calc_id))
        m.set("inUse", "true")
        m.set("type", "modeling")
        self._modeling_elements.append(m)

        node_info = {"idObject": model_id, "type": "NodeSpline"}
        if reverse:
            node_info["reverse"] = 1
        self._detail_nodes.append(node_info)

    def set_seam_allowance(self, width: float):
        self._sa_width = width

    def set_grainline(self, rotation: float = 90, length: float = 10, visible: bool = True):
        self._grainline_rotation = rotation
        self._grainline_length = length
        self._grainline_visible = visible

    def _build_xml(self, root: ET.Element):
        draw = ET.SubElement(root, "draw")
        draw.set("name", self.name)

        calc = ET.SubElement(draw, "calculation")
        for el in self._calc_elements:
            calc.append(el)

        modeling = ET.SubElement(draw, "modeling")
        for el in self._modeling_elements:
            modeling.append(el)

        details = ET.SubElement(draw, "details")
        detail = ET.SubElement(details, "detail")
        detail_id = self._parent._alloc_id()
        detail.set("id", str(detail_id))
        detail.set("name", self._piece_name)
        detail.set("closed", "1")
        detail.set("inLayout", "true")
        detail.set("seamAllowance", "true")
        detail.set("width", str(self._sa_width))
        detail.set("forbidFlipping", "false")
        detail.set("mx", "0")
        detail.set("my", "0")

        data = ET.SubElement(detail, "data")
        data.set("letter", "")
        data.set("visible", "false")
        data.set("fontSize", "0")
        data.set("mx", "0")
        data.set("my", "0")
        data.set("width", "1")
        data.set("height", "1")
        data.set("rotation", "0")
        data.set("onFold", "false")
        data.set("annotation", "")
        data.set("orientation", "")
        data.set("rotationWay", "")
        data.set("tilt", "")
        data.set("foldPosition", "")

        pi = ET.SubElement(detail, "patternInfo")
        pi.set("visible", "false")
        pi.set("fontSize", "0")
        pi.set("mx", "0")
        pi.set("my", "0")
        pi.set("width", "1")
        pi.set("height", "1")
        pi.set("rotation", "0")

        gl = ET.SubElement(detail, "grainline")
        gl.set("visible", "true" if self._grainline_visible else "false")
        gl.set("arrows", "0")
        gl.set("length", str(self._grainline_length))
        gl.set("mx", "0")
        gl.set("my", "0")
        gl.set("rotation", str(self._grainline_rotation))

        nodes = ET.SubElement(detail, "nodes")
        for nd in self._detail_nodes:
            node = ET.SubElement(nodes, "node")
            node.set("idObject", str(nd["idObject"]))
            node.set("type", nd["type"])
            if "reverse" in nd:
                node.set("reverse", str(nd["reverse"]))
            if "before" in nd:
                node.set("before", str(nd["before"]))
            if "after" in nd:
                node.set("after", str(nd["after"]))


def control_points_to_seamly(P0, CP1, CP2, P3):
    """Convert cubic Bézier control points to Seamly2D angle/length pairs.

    Seamly2D uses Y-down screen coordinates. The Atelier Domingue drafting
    also uses Y-down (negative Y = up in the pattern).

    Returns (angle1, length1, angle2, length2).
    """
    d1 = CP1 - P0
    angle1 = np.degrees(np.arctan2(d1[1], d1[0]))
    length1 = float(np.linalg.norm(d1))

    d2 = CP2 - P3
    angle2 = np.degrees(np.arctan2(d2[1], d2[0]))
    length2 = float(np.linalg.norm(d2))

    return angle1, length1, angle2, length2


def quadratic_to_cubic(P0, P1, P2):
    """Degree-elevate a quadratic Bézier to cubic, returning (P0, CP1, CP2, P2)."""
    CP1 = P0 + 2.0 / 3.0 * (P1 - P0)
    CP2 = P2 + 2.0 / 3.0 * (P1 - P2)
    return P0, CP1, CP2, P2
