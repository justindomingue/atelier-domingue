import unittest

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from garment_programs.geometry import INCH
from garment_programs.plot_utils import draw_notch, draw_seam_allowance


class PlotUtilsNotchTests(unittest.TestCase):
    def test_draw_notch_triangle_count(self):
        fig, ax = plt.subplots()
        curve = np.array([[0.0, 0.0], [10.0, 0.0]])
        point = np.array([5.0, 0.0])

        draw_notch(
            ax,
            curve,
            point,
            sa_distance=0.0,
            scale=1.0,
            style='triangle',
            count=3,
            notch_length=0.2 * INCH,
            notch_spacing=0.2 * INCH,
            notch_width=0.12 * INCH,
        )
        self.assertEqual(len(ax.patches), 3)
        plt.close(fig)

    def test_draw_notch_line_count(self):
        fig, ax = plt.subplots()
        curve = np.array([[0.0, 0.0], [10.0, 0.0]])
        point = np.array([5.0, 0.0])

        draw_notch(
            ax,
            curve,
            point,
            sa_distance=0.0,
            scale=1.0,
            style='line',
            count=2,
            notch_length=0.2 * INCH,
            notch_spacing=0.2 * INCH,
        )
        self.assertEqual(len(ax.lines), 2)
        plt.close(fig)

    def test_draw_notch_line_starts_at_cutline_and_goes_inward(self):
        fig, ax = plt.subplots()
        curve = np.array([[0.0, 0.0], [10.0, 0.0]])
        point = np.array([5.0, 0.0])

        draw_notch(
            ax,
            curve,
            point,
            sa_distance=1.0,   # cm
            scale=1.0,
            style='line',
            count=1,
            notch_length=2.0,  # cm inward from cutline
        )
        self.assertEqual(len(ax.lines), 1)
        line = ax.lines[0]
        xs = line.get_xdata()
        ys = line.get_ydata()
        self.assertAlmostEqual(xs[0], 5.0, places=6)
        self.assertAlmostEqual(xs[1], 5.0, places=6)
        self.assertAlmostEqual(ys[0], 1.0, places=6)   # cutline at +SA
        self.assertAlmostEqual(ys[1], -1.0, places=6)  # inward by 2 cm
        plt.close(fig)

    def test_draw_notch_line_can_end_at_seamline(self):
        fig, ax = plt.subplots()
        curve = np.array([[0.0, 0.0], [10.0, 0.0]])
        point = np.array([5.0, 0.0])

        draw_notch(
            ax,
            curve,
            point,
            sa_distance=1.0,     # cm
            scale=1.0,
            style='line',
            count=1,
            notch_length=3.0,    # ignored when line_to_seamline=True
            line_to_seamline=True,
        )
        self.assertEqual(len(ax.lines), 1)
        line = ax.lines[0]
        ys = line.get_ydata()
        self.assertAlmostEqual(ys[0], 1.0, places=6)   # cutline
        self.assertAlmostEqual(ys[1], 0.0, places=6)   # seamline
        plt.close(fig)

    def test_draw_seam_allowance_labels_include_seam_type(self):
        fig, ax = plt.subplots()
        edges = [
            (np.array([[0.0, 4.0], [8.0, 4.0]]), 0.5 * INCH, 'Flat-felled seam'),
            (np.array([[8.0, 4.0], [8.0, 0.0]]), 0.5 * INCH, 'Flat-felled seam'),
            (np.array([[8.0, 0.0], [0.0, 0.0]]), 0.5 * INCH, 'Flat-felled seam'),
            (np.array([[0.0, 0.0], [0.0, 4.0]]), 0.5 * INCH, 'Flat-felled seam'),
        ]

        draw_seam_allowance(ax, edges, scale=1.0, label_sas=True, units='inch')
        labels = [text.get_text() for text in ax.texts]
        self.assertTrue(any('SA' in label for label in labels))
        self.assertTrue(any('Flat-felled seam' in label for label in labels))
        plt.close(fig)


if __name__ == '__main__':
    unittest.main()
