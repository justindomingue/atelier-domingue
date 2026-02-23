# Atelier Domingue — Architecture

Personal garment drafting programs based on historical tailoring methods.

## Directory layout

```
atelier-domingue/
├── architecture.md
├── garment_programs/
│   ├── SelvedgeJeans1873/          # 1873 selvedge jeans (11 pieces)
│   │   ├── __init__.py             # GARMENT definition
│   │   ├── jeans_front.py
│   │   ├── jeans_back.py
│   │   ├── jeans_yoke_1873.py
│   │   ├── jeans_waistband.py
│   │   ├── jeans_fly_1873.py
│   │   ├── jeans_front_pocket.py
│   │   ├── jeans_back_pocket.py
│   │   ├── jeans_back_cinch.py
│   │   ├── *_instructions.md       # Step-by-step drafting instructions
│   │   └── verify.py               # Edge-length verification
│   └── MMSTrouserBlock/            # MM&S trouser block: 0, 1, or 2 pleats (2 pieces)
│       ├── __init__.py             # GARMENTS list (3 variants)
│       ├── trouser_front.py
│       └── trouser_back.py
├── measurements/
│   ├── justin.yaml
│   ├── andrew.yaml
│   └── size_50.yaml
├── pygarment_port/                 # Archived pygarment port experiments
│   ├── jeans_front_pyg.py
│   ├── jeans_back_pyg.py
│   └── pygarment_port_notes.md
├── run.py                          # TUI runner (fzf-based)
└── requirements.txt
```

## How to run

```bash
# Interactive — uses fzf to pick measurements, program, mode, and units
python run.py

# Non-interactive
python run.py -m measurements/justin.yaml -p SelvedgeJeans1873 -d -u cm

# Single piece
python run.py -m measurements/justin.yaml -p SelvedgeJeans1873.jeans_front -d -u cm
```

Output goes to `Logs/`.

### Adding a new garment program

1. Create `garment_programs/MyGarment/` with an `__init__.py` defining a `GARMENT` dict (or `GARMENTS` list for multiple variants)
2. Each piece module exposes a `run(measurements_path, output_path, debug, units)` function
3. It will automatically appear in the fzf selection

## Measurements

Measurements are stored in YAML in **inches** (how they're actually taken with a tape measure). The `load_measurements()` function converts to cm at load time, since all internal geometry is in cm.

To use different measurements, create a new file in `measurements/`.

## Module structure

Each garment program module exposes:

- **`load_measurements(yaml_path)`** — reads YAML, converts units, returns a dict
- **`draft_*(m)`** — takes measurements dict, computes all points/curves/construction geometry, returns a structured result dict
- **`plot_*(draft, output_path)`** — renders the draft to a matplotlib figure
- **`run(measurements_path, output_path, debug, units)`** — top-level entry point

This is intentionally procedural (not class-based). Historical drafting is a sequence of geometric operations, and functions map naturally to that.

## Design decisions

- **Bezier curves** for hip, rise, crotch, and inseam — cubic for curves needing tangent control at both ends, quadratic when passing through a specific midpoint
- **matplotlib for visualization** — supports both clean pattern output and debug mode with construction lines, point labels, and grid
- **All geometry in cm internally** — conversions happen at the boundary (load and display)
- **Drafting instructions colocated** with the program code — `*_instructions.md` lives next to the `.py` so the source material is always at hand
- **Generic runner with fzf** — auto-discovers measurements and programs so adding a new garment only requires creating the module
