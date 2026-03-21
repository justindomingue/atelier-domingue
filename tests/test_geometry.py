"""Tests for garment_programs.geometry primitives."""
import numpy as np
from numpy.testing import assert_allclose

from garment_programs.geometry import (
    _bezier_cubic,
    _bezier_quad,
    _curve_from_arclength,
    _curve_length,
    _curve_up_to_arclength,
    _point_at_arclength,
)


# -- Bezier helpers -----------------------------------------------------------

def test_bezier_cubic_endpoints_and_sample_count():
    P0 = np.array([0.0, 0.0])
    P1 = np.array([1.0, 2.0])
    P2 = np.array([3.0, 2.0])
    P3 = np.array([4.0, 0.0])
    n = 50
    pts = _bezier_cubic(P0, P1, P2, P3, n=n)
    assert pts.shape == (n, 2)
    assert_allclose(pts[0], P0)
    assert_allclose(pts[-1], P3)


def test_bezier_quad_endpoints_and_sample_count():
    P0 = np.array([0.0, 0.0])
    P1 = np.array([2.0, 3.0])
    P2 = np.array([4.0, 0.0])
    n = 30
    pts = _bezier_quad(P0, P1, P2, n=n)
    assert pts.shape == (n, 2)
    assert_allclose(pts[0], P0)
    assert_allclose(pts[-1], P2)


# -- Arc length ---------------------------------------------------------------

def test_curve_length_straight_line():
    line = np.array([[0.0, 0.0], [3.0, 4.0]])
    assert_allclose(_curve_length(line), 5.0)


def test_curve_length_right_angle_polyline():
    poly = np.array([[0.0, 0.0], [3.0, 0.0], [3.0, 4.0]])
    assert_allclose(_curve_length(poly), 7.0)


def test_curve_length_closed_square():
    sq = np.array([
        [0.0, 0.0],
        [2.0, 0.0],
        [2.0, 2.0],
        [0.0, 2.0],
        [0.0, 0.0],
    ])
    assert_allclose(_curve_length(sq), 8.0)


# -- Point at arc length ------------------------------------------------------

def test_point_at_arclength_start():
    line = np.array([[1.0, 2.0], [5.0, 2.0]])
    assert_allclose(_point_at_arclength(line, 0.0), [1.0, 2.0])


def test_point_at_arclength_end():
    line = np.array([[1.0, 2.0], [5.0, 2.0]])
    total = _curve_length(line)
    assert_allclose(_point_at_arclength(line, total), [5.0, 2.0])


def test_point_at_arclength_midpoint_on_straight_line():
    line = np.array([[0.0, 0.0], [10.0, 0.0]])
    assert_allclose(_point_at_arclength(line, 5.0), [5.0, 0.0])


# -- Curve split / rejoin -----------------------------------------------------

def test_curve_split_and_rejoin_recovers_total_length():
    line = np.array([[0.0, 0.0], [10.0, 0.0]])
    total = _curve_length(line)
    mid = total / 2

    head = _curve_up_to_arclength(line, mid)
    tail = _curve_from_arclength(line, mid)

    # Head runs from start to midpoint
    assert_allclose(head[0], [0.0, 0.0])
    assert_allclose(head[-1], [5.0, 0.0])

    # Tail runs from midpoint to end
    assert_allclose(tail[0], [5.0, 0.0])
    assert_allclose(tail[-1], [10.0, 0.0])

    # Combined length equals the original
    assert_allclose(_curve_length(head) + _curve_length(tail), total)
