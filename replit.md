# Atelier Domingue

Personal garment pattern drafting programs based on historical tailoring methods.

## Project Overview

A Python CLI application that generates sewing pattern pieces for historical garments (selvedge jeans, trouser blocks, etc.) using geometric drafting algorithms. Output is SVG or PDF pattern pieces with lay plans.

## Architecture

- `run.py` — Main CLI entry point. Uses `fzf` for interactive selections, or accepts `--measurements`, `--program`, `--units`, `--format` flags for non-interactive use.
- `garment_programs/` — Garment pattern modules. Each subdirectory is a garment package with an `__init__.py` defining `GARMENT` or `GARMENTS`.
  - `core/` — Shared runtime utilities (types, measurement loading, caching)
  - `SelvedgeJeans1873/` — 1873-style selvedge jeans (2 variants)
  - `MMSTrouserBlock/` — MM&S trouser block (3 variants: 0, 1, 2 pleats)
- `measurements/` — YAML measurement files (converted to cm internally)
- `tests/` — Pytest test suite
- Output goes to `Logs/` directory

## Running

```bash
# Interactive (uses fzf)
python run.py

# Non-interactive
python run.py -m measurements/justin_1873_jeans.yaml -p "1873 Selvedge Denim Jeans" -u cm -f svg
```

## Dependencies

- Python 3.12
- numpy, matplotlib, scipy, pyyaml, cairosvg, pypdf
- System: fzf, cairo

## Workflow

- Workflow: "Start application" — runs `python run.py` as a console app
