"""Seam allowance defaults for MM&S trouser block pieces.

Traditional tailored trouser profile:
- No yoke seam.
- No flat-felled seam allowances.
- Extra center-back inlay for fitting.

All values are in centimeters.
"""

# Tailored defaults (cm)
# 1.0 cm  ≈ 3/8"
# 1.5 cm  ≈ 5/8"
# 3.0 cm  ≈ 1 3/16"
SEAM_ALLOWANCES = {
    'front': {
        'waist':  1.0,
        'side':   1.5,
        'inseam': 1.5,
        'crotch': 1.0,
        'cf':     1.0,
        'hem':    4.0,
    },
    'back': {
        'waist':  1.0,
        'side':   1.5,
        'inseam': 1.5,
        'crotch': 1.5,
        'cb':     3.0,
        'hem':    4.0,
    },
}
