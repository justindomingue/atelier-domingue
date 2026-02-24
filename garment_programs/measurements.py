"""
Shared measurement loading for garment pattern programs.

Reads measurements from YAML files, converting from inches (as measured
with a tape) to centimeters (used internally for all geometry).
"""
import yaml

from garment_programs.geometry import INCH


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
