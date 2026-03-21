"""
Golden/tolerance regression tests for SelvedgeJeans1873 draft.

Mirrors the sanity checks from ``garment_programs/SelvedgeJeans1873/verify.py``
but asserts (instead of printing) so that a future refactor of
``draft_jeans_front`` / ``draft_jeans_back`` that shifts a seam by a few cm
will fail loudly in CI.
"""
import unittest
from pathlib import Path

from garment_programs.core.runtime import cache_draft, resolve_measurements
from garment_programs.core.types import PieceRuntimeContext
from garment_programs.SelvedgeJeans1873.jeans_front import (
    INCH,
    load_measurements,
    draft_jeans_front,
    _curve_length,
)
from garment_programs.SelvedgeJeans1873.jeans_back import draft_jeans_back
from garment_programs.SelvedgeJeans1873.verify import _seg

REPO_ROOT = Path(__file__).resolve().parents[1]
MEASUREMENTS_PATH = str(REPO_ROOT / 'measurements' / 'justin_1873_jeans.yaml')

# Tolerances (inches), matching verify._row defaults and its custom overrides.
TOL_DEFAULT = 0.5
TOL_HIP = 5.0
TOL_BACK_FRONT_INSEAM = 0.05


class SelvedgeJeansVerifyTests(unittest.TestCase):
    """Re-run the verify.py checks as pytest assertions."""

    @classmethod
    def setUpClass(cls):
        # Build a shared PieceRuntimeContext so front/back drafts are
        # memoised the same way the generic runner does it.
        m = load_measurements(MEASUREMENTS_PATH)
        cls.ctx = PieceRuntimeContext(
            measurements_path=str(Path(MEASUREMENTS_PATH)),
            measurements=m,
        )
        cls.m = resolve_measurements(cls.ctx, MEASUREMENTS_PATH, load_measurements)
        cls.front = cache_draft(
            cls.ctx, 'selvedge.front', lambda: draft_jeans_front(cls.m)
        )
        cls.back = cache_draft(
            cls.ctx, 'selvedge.back:0.0000', lambda: draft_jeans_back(cls.m, cls.front)
        )

    # -- helpers --------------------------------------------------------

    def _assert_inch(self, label: str, actual_cm: float, target_cm: float,
                     tol_in: float = TOL_DEFAULT):
        diff_in = (actual_cm - target_cm) / INCH
        self.assertLessEqual(
            abs(diff_in), tol_in,
            f"{label}: {actual_cm/INCH:.3f}\" vs target {target_cm/INCH:.3f}\" "
            f"(diff {diff_in:+.3f}\", tol {tol_in}\")",
        )

    # -- 1. WAIST -------------------------------------------------------

    def test_waist_circumference(self):
        fpts = self.front['points']
        fcurves = self.front['curves']
        bpts = self.back['points']

        front_waist = _curve_length(fcurves['rise'])
        back_waist = _seg(fpts['1'], bpts['back_waist'])
        half_net = front_waist + back_waist - 3/4 * INCH
        full_waist = 2 * half_net

        self._assert_inch('Full waist (×2)', full_waist, self.m['waist'])

    # -- 2. HIPS --------------------------------------------------------

    def test_hip_circumference_and_ease(self):
        fpts = self.front['points']
        bpts = self.back['points']

        front_hip_half = abs(fpts['8'][1] - fpts['4'][1])
        back_hip_half = abs(bpts["8'"][1] - fpts['4'][1])
        total_hip_full = 2 * (front_hip_half + back_hip_half)

        self._assert_inch(
            'Total hip (×2)', total_hip_full, self.m['seat'], tol_in=TOL_HIP
        )

        ease_in = (total_hip_full - self.m['seat']) / INCH
        self.assertGreaterEqual(ease_in, 1.0, f"Hip ease {ease_in:.3f}\" < 1\"")
        self.assertLessEqual(ease_in, 5.0, f"Hip ease {ease_in:.3f}\" > 5\"")

    # -- 4. LENGTHS -----------------------------------------------------

    def test_side_seam_length(self):
        fpts = self.front['points']
        fcurves = self.front['curves']

        side_arc = _curve_length(fcurves['hip'])
        side_str = _seg(fpts['4'], fpts['0'])
        side_total = side_arc + side_str

        waistband = self.m.get('waistband_width', 1.5 * INCH)
        side_target = self.m['side_length'] - waistband

        self._assert_inch('Side total', side_total, side_target)

    def test_front_inseam_length(self):
        fpts = self.front['points']
        fcurves = self.front['curves']

        arc = _curve_length(fcurves['inseam'])
        straight = _seg(fpts["3'"], fpts["0'"])
        inseam = arc + straight

        self._assert_inch('Front inseam total', inseam, self.m['inseam'])

    def test_back_inseam_quarter_inch_shorter_than_front(self):
        fcurves = self.front['curves']
        bcurves = self.back['curves']

        front_arc = _curve_length(fcurves['inseam'])
        back_arc = _curve_length(bcurves['back_inseam'])
        diff_in = (back_arc - front_arc) / INCH  # want −0.250"

        self.assertAlmostEqual(
            diff_in, -0.25, delta=TOL_BACK_FRONT_INSEAM,
            msg=f"Back − front curved diff {diff_in:+.3f}\" (want −0.250\")",
        )

    # -- 5. WIDTHS ------------------------------------------------------

    def test_hem_opening(self):
        fpts = self.front['points']
        bpts = self.back['points']

        front_half = _seg(fpts['0'], fpts["0'"])
        back_half = _seg(fpts['0'], bpts['back_hem'])
        full_hem = front_half + back_half

        self._assert_inch('Full hem opening', full_hem, self.m['hem_width'])

    def test_knee_opening(self):
        fpts = self.front['points']

        front_knee_half = abs(fpts["3'"][1] - fpts['3'][1])
        back_knee_ext = 3/4 * INCH
        full_knee = front_knee_half + (front_knee_half + back_knee_ext)

        self._assert_inch('Full knee opening', full_knee, self.m['knee_width'])

    # -- memoisation smoke-test ----------------------------------------

    def test_draft_cache_shared(self):
        """cache_draft should hand back the same front/back objects."""
        front2 = cache_draft(
            self.ctx, 'selvedge.front', lambda: draft_jeans_front(self.m)
        )
        self.assertIs(front2, self.front)


if __name__ == '__main__':
    unittest.main()
