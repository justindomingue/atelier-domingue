# Atelier Domingue

Personal garment pattern drafting programs based on historical tailoring methods.

## Project Overview

A Python application with two interfaces:
1. **CLI** (`run.py`) — TUI runner using fzf for interactive garment pattern generation (SVG/PDF output)
2. **Pocket Shape Editor** (`pocket_editor/`) — Web-based Bézier curve editor for front pocket opening design

## Architecture

- `run.py` — CLI entry point. Uses fzf for selections, or `--measurements`, `--program`, `--units`, `--format` flags.
- `garment_programs/` — Garment pattern modules. Each subdirectory is a garment package with `__init__.py` defining `GARMENT` or `GARMENTS`.
  - `core/` — Shared runtime utilities (types, measurement loading, caching)
  - `SelvedgeJeans1873/` — 1873-style selvedge jeans (2 variants)
  - `MMSTrouserBlock/` — MM&S trouser block (3 variants: 0, 1, 2 pleats)
- `pocket_editor/` — Flask web app for interactive pocket shape editing
  - `app.py` — Flask server on port 5000
  - `generate.py` — Bridges editor control points to the existing drafting pipeline
  - `templates/index.html` — Editor page
  - `static/editor.js` — Canvas-based Bézier curve editor
  - `static/style.css` — Editor styling
- `measurements/` — YAML measurement files (converted to cm internally)
- `tests/` — Pytest test suite
- Output goes to `Logs/` directory

## Running

The default workflow runs the pocket shape editor web app on port 5000.

```bash
# Pocket editor (web)
python pocket_editor/app.py

# CLI (interactive, uses fzf)
python run.py

# CLI (non-interactive)
python run.py -m measurements/justin_1873_jeans.yaml -p "1873 Selvedge Denim Jeans" -u cm -f svg
```

## Seamly2D Integration (`seamly2d_port/`)

A secondary rendering backend using Seamly2D's headless CLI for tiled PDF, full-size PDF, DXF, and SVG export.

- `measurements.py` — Converts YAML measurements → `.smis` (Seamly2D individual measurements format)
- `generate_jeans_front.py` — Builds a fully parametric `.sm2d` pattern for the jeans front panel (Approach B: formulas reference measurement variables directly)
- `run_seamly.py` — End-to-end pipeline: YAML → .smis → .sm2d → Seamly2D CLI → output files
- `format_notes.md` — Reference for .sm2d/.smis XML schemas, formula syntax, and CLI flags
- `feasibility_notes.md` — Go/no-go assessment comparing Seamly2D vs Python pipeline capabilities

### Usage
```bash
cd seamly2d_port
python run_seamly.py --format tiled    # Tiled PDF for home printers
python run_seamly.py --format pdf      # Full-size PDF
python run_seamly.py --format svg      # SVG
python run_seamly.py --format dxf      # AutoCAD DXF
python run_seamly.py --generate-only   # Just create .sm2d/.smis, no export
```

## Dependencies

- Python 3.12
- numpy, matplotlib, scipy, pyyaml, cairosvg, pypdf, flask
- System: fzf, cairo, seamly2d (via Nix)

## Workflow

- Workflow: "Start application" — runs `python pocket_editor/app.py` as webview on port 5000
