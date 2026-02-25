import tempfile
import textwrap
import unittest
from pathlib import Path

from garment_programs.measurements import load_measurements


def _write_temp_yaml(content: str) -> str:
    tmp = tempfile.NamedTemporaryFile('w', suffix='.yaml', delete=False)
    tmp.write(textwrap.dedent(content))
    tmp.flush()
    tmp.close()
    return tmp.name


class MeasurementLoaderTests(unittest.TestCase):
    def test_converts_inches_to_cm(self):
        path = _write_temp_yaml(
            """
            measurements:
              unit: inch
              waist: 34
            """
        )
        self.addCleanup(lambda: Path(path).unlink(missing_ok=True))
        m = load_measurements(path)
        self.assertAlmostEqual(m['waist'], 86.36, places=3)

    def test_accepts_cm_without_scaling(self):
        path = _write_temp_yaml(
            """
            measurements:
              unit: cm
              waist: 86.0
            """
        )
        self.addCleanup(lambda: Path(path).unlink(missing_ok=True))
        m = load_measurements(path)
        self.assertEqual(m['waist'], 86.0)

    def test_rejects_invalid_unit(self):
        path = _write_temp_yaml(
            """
            measurements:
              unit: mm
              waist: 860
            """
        )
        self.addCleanup(lambda: Path(path).unlink(missing_ok=True))
        with self.assertRaises(ValueError):
            load_measurements(path)

    def test_rejects_missing_measurements_mapping(self):
        path = _write_temp_yaml(
            """
            unit: inch
            waist: 34
            """
        )
        self.addCleanup(lambda: Path(path).unlink(missing_ok=True))
        with self.assertRaises(ValueError):
            load_measurements(path)

    def test_rejects_non_numeric_measurement(self):
        path = _write_temp_yaml(
            """
            measurements:
              unit: inch
              waist: "thirty four"
            """
        )
        self.addCleanup(lambda: Path(path).unlink(missing_ok=True))
        with self.assertRaises(TypeError):
            load_measurements(path)


if __name__ == '__main__':
    unittest.main()
