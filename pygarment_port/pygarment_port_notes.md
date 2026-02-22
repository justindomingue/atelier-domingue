# Pygarment Port — Findings & Limitations

Notes from porting the jeans front and back panels from the standalone
matplotlib-based drafting system to pygarment's `Panel` / `Edge` / `CurveEdge`
API.

## What was ported

| File | Original | Pygarment version |
|------|----------|-------------------|
| Front panel | `jeans_front.py` (501 lines) | `jeans_front_pyg.py` (245 lines) |
| Back panel | `jeans_back.py` (375 lines) | `jeans_back_pyg.py` (170 lines) |

Both pygarment versions produce identical geometry (edge lengths match within
0.0001 cm) and output JSON specification + SVG + PNG via `VisPattern.serialize()`.

## What pygarment gives us

- **JSON serialization** — full pattern spec with vertices, edges, curvature
  params, stitching rules. Machine-readable, diffable, versionable.
- **Stitching interfaces** — named `Interface` objects (`outseam`, `hem`,
  `inseam`, `crotch`, `fly`, `waist`, `seat`) that can be connected to other
  panels via `Stitches`.
- **3D placement** — `Panel.translation` / `Panel.rotation` for positioning
  in 3D space (for simulation).
- **Mirroring** — `panel.mirror()` to generate left/right pairs.
- **Edge operations** — `subdivide_len`, `subdivide_param`, `reverse`,
  `extend`, `reflect` on edges and sequences.
- **Analytic curves** — Bezier edges stored analytically (via `svgpathtools`),
  not as sampled polylines. Exact arc-length computation, correct subdivision.

## What was removed (replaced by pygarment)

~330 lines of infrastructure that pygarment handles internally:

- Bezier sampling functions (`_bezier_cubic`, `_bezier_quad`)
- Arc-length helpers (`_point_at_arclength`, `_curve_up_to_arclength`,
  `_curve_length`)
- Seam allowance engine (`_offset_polyline`, `_draw_seam_allowance`, all SA
  constants)
- Full matplotlib visualization (`plot_jeans_front`, `plot_jeans_back`)

## Limitations — what pygarment cannot represent

### No notches

Pygarment has no concept of notch marks. The closest mechanism is `edge.label`
(a semantic string stored in the JSON but not rendered visually). There is no
way to place a visual mark at a specific point along an edge.

### No internal reference lines

The pattern output contains only the panel outline. There is no way to include:

- **Hip line** — vertical reference at the crotch-fork level
- **Knee line** — vertical reference at the knee level
- **Seat line** — vertical reference at the seat level
- **Center front line** — horizontal reference
- **Yoke seam reference** — dashed line showing where to cut the yoke

These are always-visible production marks in the original output, not debug
aids. A pattern maker needs them.

### No seam allowance visualization

The original draws a dashed SA boundary with per-edge SA widths (side 3/4",
hem 2 3/8", inseam 3/8", crotch 3/8", fly 3/4", waist 3/8") including a
transition zone on the crotch curve. Pygarment has no SA rendering — SA is
handled at simulation time, not at the pattern level.

### No grain line

Standard pattern pieces include a grain line (arrow indicating fabric
direction). Pygarment has no grain line concept.

### No measurement annotations

The original's debug mode labels each edge with its arc length. Pygarment's SVG
output can show vertex/edge ID numbers but not measurement values.

### SVG output is minimal

`VisPattern.serialize()` produces:
- A filled polygon path (the panel outline)
- Optional text labels (panel name, vertex IDs, edge IDs)

That's it. No line styles, no dashes, no colors per edge, no internal geometry.

## Translation recipe

For future panel ports, the mechanical steps are:

1. **Copy point computation verbatim** from the original `draft_*()` function.
   All the numpy math stays identical.

2. **Identify the CW outline loop** from the SA edges list in the original's
   `plot_*()` function — that list already defines the edge order and direction.

3. **For each curve**, check if its original direction matches the loop
   direction. If not, swap CP1/CP2 (for cubic) or leave unchanged (for
   quadratic — single control point is symmetric).

4. **Chain edges via shared vertex references**: pass `prev_edge.end` as the
   next edge's start. Close the loop by passing `first_edge.start` as the last
   edge's end.

5. **Define interfaces** by grouping edges into named `EdgeSequence` objects.

6. **Serialize** via `panel.assembly()` → `VisPattern` → `.serialize()`.

## Recommendation

Keep the original matplotlib modules (`jeans_front.py`, `jeans_back.py`) as the
production visualization path. Use the pygarment modules (`*_pyg.py`) for JSON
serialization and stitching when integrating with the rest of the pygarment
ecosystem. A future improvement would be adding a `plot()` method to each pyg
panel class that renders the outline from the edge loop plus reference lines via
matplotlib — single source of truth for geometry, rich visual output.
