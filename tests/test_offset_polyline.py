"""Tests for plot_utils.offset_polyline."""
import numpy as np
from numpy.testing import assert_allclose

from garment_programs.plot_utils import offset_polyline


def test_offset_horizontal_line_parallel_1cm_left():
    # Travel in +x → left-of-travel normal is +y
    line = np.array([[0.0, 0.0], [10.0, 0.0]])
    out = offset_polyline(line, 1.0)
    assert_allclose(out, [[0.0, 1.0], [10.0, 1.0]])


def test_offset_right_angle_miter_corner():
    # L-shape: +x then +y.  Left-of-travel is +y along the base, -x up the riser.
    # Miter at the inside corner lands at (corner_x - d, corner_y + d).
    L = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 10.0]])
    out = offset_polyline(L, 1.0)
    expected = np.array([
        [0.0, 1.0],    # start pushed +y
        [9.0, 1.0],    # miter join
        [9.0, 10.0],   # end pushed -x
    ])
    assert_allclose(out, expected)


def test_zero_offset_returns_same_points():
    poly = np.array([[0.0, 0.0], [3.0, 4.0], [6.0, 0.0]])
    out = offset_polyline(poly, 0.0)
    assert_allclose(out, poly)
