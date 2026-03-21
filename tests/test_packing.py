"""Tests for lay_plan packing algorithms.

Covers the algorithmic core: skyline_pack, polygon_nest, and the
geometry helpers they rely on (_shoelace_area, _polygon_y_range_at_x,
_intersect_ranges).
"""

import io
from contextlib import redirect_stdout

import numpy as np
from numpy.testing import assert_allclose

from garment_programs.lay_plan import (
    Piece,
    _intersect_ranges,
    _polygon_y_range_at_x,
    _shoelace_area,
    polygon_nest,
    skyline_pack,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rect(w: float, h: float) -> list[tuple[float, float]]:
    """Axis-aligned rectangle polygon with origin at (0, 0)."""
    return [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]


def _rects_overlap(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, ay2: float, bw: float, bh: float,
    eps: float = 1e-6,
) -> bool:
    """True if two axis-aligned rectangles overlap in both x and y."""
    x_overlap = ax < (bx + bw) - eps and bx < (ax + aw) - eps
    y_overlap = ay < (ay2 + bh) - eps and ay2 < (ay + ah) - eps
    return x_overlap and y_overlap


def _assert_no_overlap(positions: dict, sizes: dict) -> None:
    names = list(positions.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            na, nb = names[i], names[j]
            ax, ay = positions[na]
            bx, by = positions[nb]
            aw, ah = sizes[na]
            bw, bh = sizes[nb]
            assert not _rects_overlap(ax, ay, aw, ah, bx, by, bw, bh), (
                f"pieces {na!r} and {nb!r} overlap: "
                f"{na}=({ax:.2f},{ay:.2f},{aw:.2f},{ah:.2f}) "
                f"{nb}=({bx:.2f},{by:.2f},{bw:.2f},{bh:.2f})"
            )


# ---------------------------------------------------------------------------
# skyline_pack
# ---------------------------------------------------------------------------

class TestSkylinePack:
    def test_zero_pieces_returns_empty(self):
        positions, total = skyline_pack([], fabric_width=30.0)
        assert positions == {}
        assert_allclose(total, 0.0)

    def test_zero_pieces_with_return_skyline(self):
        positions, total, skyline = skyline_pack(
            [], fabric_width=30.0, return_skyline=True
        )
        assert positions == {}
        assert_allclose(total, 0.0)
        # Initial skyline spans the full fabric width at x=0.
        assert len(skyline) == 1
        y0, y1, x = skyline[0]
        assert_allclose([y0, y1, x], [0.0, 30.0, 0.0])

    def test_three_small_pieces_fit_without_overlap(self):
        pieces = [
            ("a", 5.0, 4.0),
            ("b", 3.0, 6.0),
            ("c", 4.0, 5.0),
        ]
        sizes = {name: (gl, cw) for name, gl, cw in pieces}
        fabric_width = 30.0
        gap = 0.25

        positions, total = skyline_pack(pieces, fabric_width, gap=gap)

        assert set(positions) == {"a", "b", "c"}
        _assert_no_overlap(positions, sizes)

        # Every piece stays inside the fabric width.
        for name, (_, cw) in sizes.items():
            _, y = positions[name]
            assert y >= 0.0
            assert y + cw <= fabric_width + 1e-6

        # All three pieces fit across the 30" width, so they should
        # stack in a single column: total length is the longest piece
        # plus gap (5" + 0.25").
        max_grain = max(gl for _, gl, _ in pieces)
        assert_allclose(total, max_grain + gap)

    def test_piece_wider_than_fabric_warns_and_places(self):
        pieces = [("wide", 10.0, 40.0)]
        gap = 0.25
        buf = io.StringIO()
        with redirect_stdout(buf):
            positions, total = skyline_pack(pieces, fabric_width=30.0, gap=gap)

        # Still placed (via the best_y fallback) rather than raised.
        assert "wide" in positions
        _, y = positions["wide"]
        # Free pieces get a half-gap offset; best_y falls back to 0.
        assert_allclose(y, gap / 2)
        assert "Warning" in buf.getvalue()
        # Length reflects the piece's grain extent plus gap.
        assert_allclose(total, 10.0 + gap)

    def test_exact_width_tiling_packs_in_one_column(self):
        # Three 10"-wide pieces exactly fill a 30" fabric width.
        pieces = [
            ("p1", 6.0, 10.0),
            ("p2", 6.0, 10.0),
            ("p3", 6.0, 10.0),
        ]
        gap = 0.0
        positions, total = skyline_pack(pieces, fabric_width=30.0, gap=gap)

        # With zero gap and exact tiling, all three stack at x=0.
        xs = sorted(x for x, _ in positions.values())
        assert_allclose(xs, [0.0, 0.0, 0.0])
        ys = sorted(y for _, y in positions.values())
        assert_allclose(ys, [0.0, 10.0, 20.0])
        # Total length is a single column: max piece grain length.
        assert_allclose(total, 6.0)

    def test_selvedge_edges_pinned(self):
        pieces = [
            ("top_piece", 8.0, 5.0, "top"),
            ("bot_piece", 8.0, 5.0, "bottom"),
        ]
        fabric_width = 20.0
        positions, _ = skyline_pack(pieces, fabric_width, gap=0.25)

        _, ty = positions["top_piece"]
        _, by = positions["bot_piece"]
        assert_allclose(ty, 0.0)
        assert_allclose(by, fabric_width - 5.0)


# ---------------------------------------------------------------------------
# _shoelace_area
# ---------------------------------------------------------------------------

class TestShoelaceArea:
    def test_unit_square_ccw(self):
        square = [(0, 0), (1, 0), (1, 1), (0, 1)]
        assert_allclose(_shoelace_area(square), 1.0)

    def test_triangle_ccw(self):
        # Right triangle with legs of length 4 and 3 → area 6.
        tri = [(0, 0), (4, 0), (0, 3)]
        assert_allclose(_shoelace_area(tri), 6.0)

    def test_cw_winding_is_negative(self):
        square_cw = [(0, 0), (0, 1), (1, 1), (1, 0)]
        assert_allclose(_shoelace_area(square_cw), -1.0)

    def test_degenerate_returns_zero(self):
        assert_allclose(_shoelace_area([(0, 0), (1, 1)]), 0.0)
        assert_allclose(_shoelace_area([]), 0.0)


# ---------------------------------------------------------------------------
# _polygon_y_range_at_x
# ---------------------------------------------------------------------------

class TestPolygonYRangeAtX:
    def test_rectangle_interior(self):
        rect = _rect(10.0, 5.0)
        result = _polygon_y_range_at_x(rect, x=5.0)
        assert result is not None
        lo, hi = result
        assert_allclose([lo, hi], [0.0, 5.0])

    def test_triangle_narrows_toward_apex(self):
        # Triangle with base on x-axis (0..10) and apex at (5, 10).
        tri = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0)]

        base = _polygon_y_range_at_x(tri, x=5.0)
        near_apex = _polygon_y_range_at_x(tri, x=1.0)

        assert base is not None and near_apex is not None
        # Mid-span at x=5 covers the full height 0..10.
        assert_allclose(base[0], 0.0, atol=1e-6)
        assert_allclose(base[1], 10.0, atol=1e-6)
        # Near the left base corner (x=1), the right edge is at
        # y = 10 - 2*1 = — wait, left edge: from (0,0)→(5,10) at x=1
        # gives y=2. So span is [0, 2].
        assert_allclose(near_apex[0], 0.0, atol=1e-6)
        assert_allclose(near_apex[1], 2.0, atol=1e-6)
        # Span near the base corner is narrower than at mid-span.
        assert (near_apex[1] - near_apex[0]) < (base[1] - base[0])

    def test_outside_bounds_returns_none(self):
        rect = _rect(10.0, 5.0)
        assert _polygon_y_range_at_x(rect, x=-1.0) is None
        assert _polygon_y_range_at_x(rect, x=11.0) is None


# ---------------------------------------------------------------------------
# _intersect_ranges
# ---------------------------------------------------------------------------

class TestIntersectRanges:
    def test_overlapping(self):
        result = _intersect_ranges([(0.0, 10.0)], [(5.0, 15.0)])
        assert len(result) == 1
        assert_allclose(result[0], (5.0, 10.0))

    def test_disjoint(self):
        result = _intersect_ranges([(0.0, 5.0)], [(10.0, 15.0)])
        assert result == []

    def test_one_contains_other(self):
        result = _intersect_ranges([(0.0, 20.0)], [(5.0, 10.0)])
        assert len(result) == 1
        assert_allclose(result[0], (5.0, 10.0))

    def test_multiple_segments(self):
        a = [(0.0, 5.0), (10.0, 15.0)]
        b = [(3.0, 12.0)]
        result = _intersect_ranges(a, b)
        assert len(result) == 2
        assert_allclose(result[0], (3.0, 5.0))
        assert_allclose(result[1], (10.0, 12.0))

    def test_empty_input(self):
        assert _intersect_ranges([], [(0.0, 1.0)]) == []
        assert _intersect_ranges([(0.0, 1.0)], []) == []


# ---------------------------------------------------------------------------
# polygon_nest
# ---------------------------------------------------------------------------

class TestPolygonNest:
    def test_empty_input(self):
        positions, total, use_polygons = polygon_nest([], fabric_width=30.0)
        assert positions == {}
        assert_allclose(total, 0.0)
        assert use_polygons is False

    def test_simple_rectangles_produce_valid_layout(self):
        # Piece: (name, grain_len, cross_w, edge, polygon, pad_x, pad_y)
        pieces = [
            Piece("a", 5.0, 4.0, None, _rect(5.0, 4.0), 0.0, 0.0),
            Piece("b", 3.0, 6.0, None, _rect(3.0, 6.0), 0.0, 0.0),
            Piece("c", 4.0, 5.0, None, _rect(4.0, 5.0), 0.0, 0.0),
        ]
        sizes = {p.name: (p.grain_len, p.cross_w) for p in pieces}
        fabric_width = 30.0
        gap = 0.25

        buf = io.StringIO()
        with redirect_stdout(buf):
            positions, total, _ = polygon_nest(
                pieces, fabric_width, gap=gap
            )

        # All pieces placed.
        assert set(positions) == {"a", "b", "c"}

        # No overlap between any pair.
        _assert_no_overlap(positions, sizes)

        # All within fabric width, and length is sane (at least the
        # longest piece, at most the sum of all).
        for name, (gl, cw) in sizes.items():
            x, y = positions[name]
            assert y >= -1e-6
            assert y + cw <= fabric_width + 1e-6
            assert x >= -1e-6

        grain_lengths = [p.grain_len for p in pieces]
        assert total >= max(grain_lengths)
        assert total <= sum(grain_lengths) + len(pieces) * gap + 1.0

    def test_selvedge_only_falls_back_to_skyline(self):
        # No free pieces → polygon_nest should early-return with the
        # baseline skyline result (use_polygons=False).
        pieces = [
            Piece("front", 10.0, 8.0, "top", _rect(10.0, 8.0), 0.0, 0.0),
            Piece("back", 10.0, 8.0, "bottom", _rect(10.0, 8.0), 0.0, 0.0),
        ]
        buf = io.StringIO()
        with redirect_stdout(buf):
            positions, total, use_polygons = polygon_nest(
                pieces, fabric_width=30.0, gap=0.25
            )

        assert use_polygons is False
        assert set(positions) == {"front", "back"}
        _, fy = positions["front"]
        _, by = positions["back"]
        assert_allclose(fy, 0.0)
        assert_allclose(by, 30.0 - 8.0)
