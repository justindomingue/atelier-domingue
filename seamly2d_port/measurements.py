"""Convert Atelier Domingue YAML measurement files to Seamly2D .smis format."""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import yaml
import sys
from pathlib import Path

INCH_TO_CM = 2.54

MEASUREMENT_MAP = {
    "waist": "waist_circ",
    "seat": "hip_circ",
    "inseam": "leg_crotch_to_floor",
    "side_length": "leg_waist_side_to_floor",
}

CUSTOM_MEASUREMENTS = {
    "waistband_width",
    "hem_width",
    "knee_width",
}


def load_yaml_measurements(yaml_path: str) -> tuple[dict, str]:
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    raw = data["measurements"]
    unit = raw.pop("unit", "inch")
    return raw, unit


def to_cm(value: float, unit: str) -> float:
    if unit == "inch":
        return round(value * INCH_TO_CM, 4)
    return round(value, 4)


def build_smis_xml(
    raw_measurements: dict,
    unit: str,
    family_name: str = "",
    given_name: str = "",
) -> str:
    root = ET.Element("smis")
    ET.SubElement(root, "version").text = "0.3.4"
    ET.SubElement(root, "read-only").text = "false"
    ET.SubElement(root, "notes")
    ET.SubElement(root, "unit").text = "cm"
    ET.SubElement(root, "pm_system").text = "998"

    personal = ET.SubElement(root, "personal")
    ET.SubElement(personal, "family-name").text = family_name
    ET.SubElement(personal, "given-name").text = given_name
    ET.SubElement(personal, "birth-date").text = "1800-01-01"
    ET.SubElement(personal, "gender").text = "unknown"
    ET.SubElement(personal, "email")

    body = ET.SubElement(root, "body-measurements")

    for yaml_name, value in raw_measurements.items():
        cm_value = to_cm(value, unit)

        if yaml_name in MEASUREMENT_MAP:
            seamly_name = MEASUREMENT_MAP[yaml_name]
            m = ET.SubElement(body, "m")
            m.set("name", seamly_name)
            m.set("value", str(cm_value))
        else:
            pass

    rough = ET.tostring(root, encoding="unicode", xml_declaration=True)
    dom = minidom.parseString(rough)
    return dom.toprettyxml(indent="    ").replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>')


def build_increments_xml(raw_measurements: dict, unit: str) -> list[tuple[str, str]]:
    increments = []
    for yaml_name, value in raw_measurements.items():
        if yaml_name in CUSTOM_MEASUREMENTS:
            cm_value = to_cm(value, unit)
            increments.append((yaml_name, str(cm_value)))
    return increments


def convert(yaml_path: str, output_path: str | None = None) -> str:
    raw, unit = load_yaml_measurements(yaml_path)

    stem = Path(yaml_path).stem
    parts = stem.split("_", 1)
    given_name = parts[0].title() if parts else ""

    xml_str = build_smis_xml(raw, unit, given_name=given_name)

    if output_path is None:
        output_path = str(Path(yaml_path).with_suffix(".smis"))

    with open(output_path, "w") as f:
        f.write(xml_str)

    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python measurements.py <input.yaml> [output.smis]")
        sys.exit(1)

    yaml_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    result = convert(yaml_path, output_path)
    print(f"Wrote {result}")
