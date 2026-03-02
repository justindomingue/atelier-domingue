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

## Dependencies

- Python 3.12
- numpy, matplotlib, scipy, pyyaml, cairosvg, pypdf, flask
- System: fzf, cairo

## Workflow

- Workflow: "Start application" — runs `python pocket_editor/app.py` as webview on port 5000
