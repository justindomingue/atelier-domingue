# SVG Rendering Inconsistencies

Pieces use different approaches to draw their outlines, which makes automated
polygon extraction unreliable for some pieces.  The "standard" approach is
`_draw_seam_allowance()` (defined in `jeans_front.py`) which produces a single
closed `<path>` with CUTLINE style — ideal for polygon extraction.

## Pieces using `_draw_seam_allowance()` (single closed CUTLINE path)

| Piece | Largest path area (pts²) | Vertices | Notes |
|-------|--------------------------|----------|-------|
| Front Panel | 2,395,359 | 135 | Curved SA outline |
| Back Panel | 2,785,097 | 99 | Curved SA outline |
| Front Pocket Bag | 310,688 | 91 | Curved SA outline |
| Back Pocket | 261,350 | 6 | Rectangular SA |
| Yoke (1873) | 171,650 | 9 | Polygonal SA |
| Watch Pocket | 111,103 | 11 | Polygonal SA |
| Front Pocket Facing | 71,461 | 72 | Curved SA outline |

## Pieces NOT using `_draw_seam_allowance()` — need fixing

### Fly (1873) — `jeans_fly_1873.py`

**Problem**: Draws outline as individual `ax.plot()` segments with SEAMLINE
style (blue, 1.0).  No single closed path exists.

- Top edge: `fold_top → outer_top` (1 segment)
- Outer edge: `outer_top → curve_start` (1 segment)
- Bottom curve: `curves['bottom']` (~100 pts, 1 segment)
- Fold line: drawn dashed, not part of outline

**Impact**: Falls back to bounding-box rectangle for polygon extraction.
Fly is nearly rectangular anyway (1.8" × 10.1"), so impact is minimal.

**Fix**: Add `_draw_seam_allowance()` with edges ordered CW.  The fold edge
gets SA=0 (cut on fold), other edges get `S['narrow']` (½").  Need to add a
`fly_1873` entry to `seam_allowances.py`.

### Back Cinch Belt — `jeans_back_cinch.py`

**Problem**: Draws ALL edges as individual 2-point `ax.plot()` segments
(lines 100–112).  Nine separate line segments, none forming a closed path.

```python
# Current: 9 separate segments
for a, b in [('sa_tl', 'sa_tr'), ('f_tl', 'f_tr'), ...]:
    ax.plot([pts[a][0], pts[b][0]], [pts[a][1], pts[b][1]], **LINE)
```

**Impact**: Falls back to bounding-box rectangle.  Cinch is nearly rectangular
(~0.5" taper over 6"), so impact is minimal.

**Fix**: Draw the SA outline as a single closed path:
```python
from garment_programs.plot_utils import CUTLINE
sa_xs = [pts[k][0] for k in ('sa_tl', 'sa_tr', 'sa_br', 'sa_bl', 'sa_tl')]
sa_ys = [pts[k][1] for k in ('sa_tl', 'sa_tr', 'sa_br', 'sa_bl', 'sa_tl')]
ax.plot(sa_xs, sa_ys, **CUTLINE)
```

### Waistband — `jeans_waistband.py`

**Problem**: Rectangle outline drawn with SEAMLINE style (blue, 1.0) instead
of CUTLINE (black, 1.5).  The rectangle IS the cut boundary (SA included in
the 3¾" width), but it's styled as a seamline.

```python
OUTLINE = SEAMLINE  # line 91 — should be CUTLINE
```

**Impact**: Polygon extraction still works (largest-area path is correctly
identified regardless of color), but visual inconsistency.

**Fix**: Change `OUTLINE = SEAMLINE` to `OUTLINE = CUTLINE` on line 91, and
import CUTLINE from `plot_utils`.

## Summary

| Piece | Drawing method | Polygon extraction | Priority |
|-------|---------------|-------------------|----------|
| Fly 1873 | Individual segments (SEAMLINE) | Bbox fallback | Medium |
| Back Cinch | Individual segments (custom) | Bbox fallback | Low |
| Waistband | Single rect (SEAMLINE color) | Works (wrong color) | Low |
