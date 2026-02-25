import unittest

from garment_programs.core.runtime import cache_draft, resolve_measurements
from garment_programs.core.types import PieceRuntimeContext


class CoreRuntimeTests(unittest.TestCase):
    def test_cache_draft_memoizes_value(self):
        calls = {'count': 0}

        def factory():
            calls['count'] += 1
            return {'value': 42}

        ctx = PieceRuntimeContext(measurements_path='measurements/x.yaml', measurements={})
        a = cache_draft(ctx, 'k', factory)
        b = cache_draft(ctx, 'k', factory)

        self.assertEqual(a, {'value': 42})
        self.assertIs(a, b)
        self.assertEqual(calls['count'], 1)

    def test_resolve_measurements_prefers_context(self):
        ctx = PieceRuntimeContext(
            measurements_path='measurements/a.yaml',
            measurements={'waist': 86.0},
        )

        def loader(_path):
            raise AssertionError('loader should not be called')

        m = resolve_measurements(ctx, 'measurements/a.yaml', loader)
        self.assertEqual(m['waist'], 86.0)

    def test_resolve_measurements_falls_back_to_loader(self):
        ctx = PieceRuntimeContext(
            measurements_path='measurements/a.yaml',
            measurements={'waist': 86.0},
        )

        def loader(_path):
            return {'waist': 90.0}

        m = resolve_measurements(ctx, 'measurements/b.yaml', loader)
        self.assertEqual(m['waist'], 90.0)


if __name__ == '__main__':
    unittest.main()
