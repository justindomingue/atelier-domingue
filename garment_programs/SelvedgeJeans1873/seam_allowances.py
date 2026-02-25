"""
Centralized seam allowance constants for all SelvedgeJeans1873 pattern pieces.

All values are in centimeters.  Each piece maps edge-name → SA distance,
referencing shared SEAM_TYPES so the *construction method* is explicit.
"""

from garment_programs.seam_types import SEAM_TYPES, INCH

S = SEAM_TYPES  # short alias for readability

YOKE_SEAT_DEPTH = 2.75 * INCH   # yoke point along seat_upper curve from back_waist

SEAM_ALLOWANCES = {
    'front': {
        'side':    2 * S['flat_fell'],       # 3/4" — outseam, flat-felled (wrap side)
        'hem':     S['hem'],
        'inseam':  S['flat_fell'],
        'crotch':  S['flat_fell'],
        'fly':     2 * S['flat_fell'],       # 3/8" crotch + 3/8" extension
        'waist':   S['flat_fell'],
    },
    'back': {
        'side':    2 * S['flat_fell'],       # 3/4" — outseam, flat-felled (wrap side)
        'hem':     S['hem'],
        'inseam':  2 * S['flat_fell'],       # 3/4" — inseam, flat-felled (wrap side)
        'seat':    S['wide'],
        'yoke':    2 * S['flat_fell'],       # 3/4" — yoke seam (wrap side)
    },
    'yoke': {
        'seat':    S['wide'],                # long side / seat seam
        'side':    2 * S['flat_fell'],       # 3/4" — short edge / side seam
        'waist':   S['simple'],              # waist and yoke seams
    },
    'back_cinch': {
        'wide':    3/4 * INCH,               # specific to cinch belt construction
        'narrow':  S['wide'],
        'end':     S['narrow'],
    },
    'back_pocket': {
        'side':    S['flat_fell'],
        'top':     S['pocket_fold'],
    },
    'watch_pocket': {
        'top':     S['pocket_fold'],
        'sides':   S['flat_fell'],
        'bottom':  S['flat_fell'],
    },
    'front_facing': {
        'waist':    S['flat_fell'],              # 3/8" — matches front panel waist SA
        'sideseam': 2 * S['flat_fell'],          # 3/4" — matches front panel side seam SA
        'opening':  (1 + 1/4) * INCH,            # 1¼" — 1" facing wrap + ¼" turnover
    },
    'front_pocket_bag': {
        'waist':    S['flat_fell'],     # top edge, caught in waistband
        'sideseam': S['flat_fell'],     # side, caught in side seam
        'bottom':   S['flat_fell'],     # bottom curve
    },
    'waistband': {
        'top':     0,                   # selvedge edge — no SA
        'bottom':  S['flat_fell'],      # 3/8" — seam to jeans body
        'end':     S['flat_fell'],      # 3/8" — end finish
    },
    'fly_one_piece': {
        'side':    S['narrow'],
    },
    'fly_1873': {
        'fold':    0,                   # cut on fold — no SA
        'top':     S['narrow'],         # 1/2" — top edge
        'outer':   S['narrow'],         # 1/2" — outer/side edge
        'bottom':  S['narrow'],         # 1/2" — bottom curve
    },
}
