# Seamly2D Backend: Feasibility Assessment

## Summary

**Recommendation: Conditional Go — Seamly2D is viable for PDF/tiled export but should complement, not replace, the existing Python pipeline.**

The proof-of-concept successfully ported the jeans front panel to a fully parametric `.sm2d` pattern that Seamly2D processes headlessly. Different measurements produce different patterns automatically with zero Python math at render time. The tiled PDF, full-size PDF, and SVG exports all work via CLI.

However, the current Python pipeline has capabilities that Seamly2D cannot replicate, making a hybrid approach the practical path forward.

---

## What Seamly2D Handles Better

| Capability | Details |
|---|---|
| **Tiled PDF output** | Built-in multi-page tiling with registration marks, overlap, and page numbering. The existing pipeline has no equivalent. |
| **DXF export** | Native support for AutoCAD DXF R10 through DXF 2007, useful for laser cutters and industrial plotters. |
| **Standard pattern marks** | Grainlines, seam allowance generation, and notch placement follow industry-standard CAD conventions. |
| **Parametric re-grading** | Changing measurements in the `.smis` file re-resolves every formula in the pattern automatically. No code changes needed. |
| **Multiple export formats** | SVG, PDF, PNG, JPG, BMP, TIF, PS, EPS, OBJ, DXF — all from the same CLI invocation. |

## What's Lost or Harder

| Capability | Status in Seamly2D |
|---|---|
| **Lay planning (skyline packing)** | Not available. Seamly2D lays out pieces for single-sheet export but has no multi-piece nesting with selvedge constraints or void-filling optimization. |
| **Debug / construction mode** | Partially available. Construction lines render in draft view but the CLI export only outputs the detail (finished) pieces. Custom debug annotations (point labels, measurement readouts) are not supported. |
| **Per-node seam allowance widths** | Supported via `before`/`after` attributes on detail nodes. Works as well as the Python pipeline. |
| **Custom notch styles** | Seamly2D supports notch marks but only in specific styles. The Python pipeline's triangular notches may not translate exactly. |
| **Pocket editor integration** | The interactive pocket drafting tools in the Python pipeline have no Seamly2D equivalent. Pockets would need to be built as separate pattern pieces. |
| **Complex math (atan2, normalization)** | Seamly2D's formula system lacks `atan2` and vector operations. Workarounds exist (helper points + `AngleLine_` references) but are verbose. |
| **Multi-piece garment assembly** | Each draw block in an `.sm2d` file is independent. Cross-piece references (e.g., matching back yoke to front waist) require manual coordination of shared measurement variables. |
| **Interfacing net-shape patterns** | Would need a second detail piece (no SA) in the same draw block, which is supported but doubles the modeling/detail work. |

## Architecture: Recommended Hybrid Approach

```
YAML measurements
       │
       ▼
  measurements.py  ──►  .smis file
       │
       ▼
  generate_*.py    ──►  .sm2d file (parametric)
       │
       ▼
  run_seamly.py    ──►  Seamly2D CLI  ──►  Tiled PDF / Full-size PDF / DXF
       │
       └──────────────►  Python/Matplotlib pipeline  ──►  Lay plan SVG/PDF
                                                          Debug mode
                                                          JSON outlines
```

- **Use Seamly2D for**: tiled printing (home printers), DXF export (laser/plotter), and as a secondary validation of pattern geometry.
- **Keep Python pipeline for**: lay planning, debug mode, pocket editor, and any output requiring custom annotations or multi-piece nesting.
- **Measurement source stays YAML**: Both pipelines read from the same YAML files. `measurements.py` generates `.smis` for Seamly2D; the existing YAML loader feeds Python.

## Effort Estimate for Full Port

| Task | Estimated effort | Notes |
|---|---|---|
| Port remaining jeans pieces (11 pieces) | 3–5 days | Each piece follows the same pattern as jeans_front. The back piece and yoke have the most complex curves. |
| Validate geometry against Python output | 1–2 days | Overlay SVG exports and compare point positions. The hip curve and crotch curve need careful tangent matching. |
| Add notch support | 0.5 day | Seamly2D supports notches on detail nodes; needs mapping from Python notch positions. |
| Add grainline support | 0.5 day | Already partially implemented (grainline element exists in detail). Needs correct anchor points. |
| Build multi-format runner | Done | `run_seamly.py` handles SVG, PDF, tiled PDF, and DXF. |
| Integrate into existing CLI (`run.py`) | 1 day | Add `--backend seamly2d` flag to existing TUI runner. |

**Total for full integration: ~6–9 days of focused work.**

## Technical Notes

### Seamly2D Formula Limitations
- No `atan2()` — use helper points and `AngleLine_PointA_PointB` instead
- No vector normalize — use `Line_A_B` for distance, `AngleLine_A_B` for direction
- Formulas on `endLine` length/angle are strings (formulas OK); `single` point x/y are doubles (literals only)
- `Line_A_B` / `AngleLine_A_B` variables only exist when an explicit `<line>` element connects A and B, or when A is derived from B via `endLine` / `alongLine`

### Schema Gotchas
- `increment` elements require a `description` attribute (can be empty)
- Points use `typeLine`; splines use `penStyle`
- Modeling section: points use `type="modeling"`, splines use `type="modelingSpline"`
- Measurement file version is 0.3.4 (`.smis` format); pattern version is 0.6.0 (`.sm2d` format)
- Custom variables (increments) use `#name` prefix in formulas

### CLI Flags (Seamly2D 0.6.0.1)
```
seamly2d -b BASENAME -f FORMAT -d OUTPUT_DIR -m MEASUREMENTS_FILE PATTERN_FILE
```
Requires `QT_QPA_PLATFORM=offscreen` for headless operation.

Format codes: 0=SVG, 1=PDF, 2=Tiled PDF, 3=PNG, 10–15=DXF variants.
