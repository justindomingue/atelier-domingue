"""
Shared measurement loading for garment pattern programs.

Reads measurements from YAML files, converting from inches (as measured
with a tape) to centimeters (used internally for all geometry).
"""
import yaml

from garment_programs.geometry import INCH

VALID_UNITS = {'inch', 'cm'}

def load_measurements(yaml_path: str) -> dict[str, float]:
    """Load measurements from YAML, validating schema and converting to cm."""
    with open(yaml_path) as f:
        payload = yaml.safe_load(f) or {}
    if 'measurements' not in payload or not isinstance(payload['measurements'], dict):
        raise ValueError(f"{yaml_path}: expected top-level 'measurements' mapping")
    raw = payload['measurements']

    unit = raw.get('unit', 'inch')
    if unit not in VALID_UNITS:
        raise ValueError(f"{yaml_path}: unsupported unit '{unit}' (expected one of {sorted(VALID_UNITS)})")
    scale = INCH if unit == 'inch' else 1.0

    m: dict[str, float] = {}
    for key, val in raw.items():
        if key == 'unit':
            continue
        if not isinstance(val, (int, float)):
            raise TypeError(f"{yaml_path}: measurement '{key}' must be numeric")
        m[key] = float(val) * scale
    return m
