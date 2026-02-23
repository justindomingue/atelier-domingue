"""
Seam construction types and their standard seam allowances.

Shared across all garment programs.  Each entry describes a method of
joining two pieces and the SA width it requires (in cm).

Individual garment seam_allowances modules reference these types so that
changing a construction method propagates everywhere automatically.
"""

INCH = 2.54

SEAM_TYPES = {
    'flat_fell':    3/8 * INCH,           # flat-felled seam (each side)
    'lapped':       3/8 * INCH,           # lapped seam (each side)
    'simple':       3/8 * INCH,           # plain seam, pressed open
    'wide':         5/8 * INCH,           # wide plain seam
    'hem':          (1.5 + 7/8) * INCH,   # hem turn-up (1½" fold + ⅞" allowance)
    'pocket_fold':  7/8 * INCH,           # pocket top double fold
    'narrow':       1/2 * INCH,           # minimal finish (belt ends, fly side SA)
}
