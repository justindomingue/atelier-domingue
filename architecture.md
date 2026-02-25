# Atelier Domingue — Architecture

Personal garment drafting programs based on historical tailoring methods.

## Directory layout

```
atelier-domingue/
├── architecture.md
├── garment_programs/
│   ├── core/                        # Shared runtime utilities
│   │   ├── types.py                 # PieceRuntimeContext, DraftData
│   │   └── runtime.py               # Shared measurement/cache helpers
│   ├── SelvedgeJeans1873/          # Selvedge jeans variants (1873 + modern)
│   │   ├── __init__.py             # GARMENTS list (2 variants)
│   │   ├── jeans_front.py
│   │   ├── jeans_back.py
│   │   ├── jeans_yoke_1873.py
│   │   ├── jeans_yoke_modern.py
│   │   ├── jeans_waistband.py
│   │   ├── jeans_fly_1873.py
│   │   ├── jeans_fly_one_piece.py
│   │   ├── jeans_front_facing.py
│   │   ├── jeans_front_pocket_bag.py
│   │   ├── jeans_watch_pocket.py
│   │   ├── jeans_back_pocket.py
│   │   ├── jeans_back_cinch.py
│   │   ├── *_instructions.md       # Step-by-step drafting instructions
│   │   └── verify.py               # Edge-length verification
│   └── MMSTrouserBlock/            # MM&S trouser block: 0, 1, or 2 pleats (2 pieces)
│       ├── __init__.py             # GARMENTS list (3 variants)
│       ├── trouser_front.py
│       └── trouser_back.py
├── measurements/
│   ├── justin_1873_jeans.yaml
│   ├── andrew_1873_jeans.yaml
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

# Non-interactive garment run (use garment name)
python run.py -m measurements/justin_1873_jeans.yaml -p "1873 Selvedge Denim Jeans" -u cm

# Single piece
python run.py -m measurements/justin_1873_jeans.yaml -p SelvedgeJeans1873.jeans_front -u cm

# Optional: prioritize shortest lay-plan length over panel pairing
python run.py -m measurements/justin_1873_jeans.yaml -p "1873 Selvedge Denim Jeans" -u cm --shortest-layout
```

Output goes to `Logs/`.

Program selection notes:
- `--program` accepts garment names, unambiguous package names, or dotted piece modules.
- If a package contains multiple garments (for example `SelvedgeJeans1873`), use a garment name or a dotted module.
- Lay-plan default prefers matching front/back panel pairing; use `--shortest-layout` to optimize only for minimum length.

### Adding a new garment program

1. Create `garment_programs/MyGarment/` with an `__init__.py` defining a `GARMENT` dict (or `GARMENTS` list for multiple variants)
2. Each piece module exposes `run(measurements_path, output_path, debug, units, context=None)`
3. Use `context` to access shared converted measurements and cached draft data when available
4. Optionally return `{"layout_outline": ...}` from `run()` to emit `<piece>.outline.json` sidecars for lay planning
5. It will automatically appear in the fzf selection

## Measurements

Measurements are stored in YAML with explicit `unit` (`inch` or `cm`). The `load_measurements()` function converts to cm at load time, since all internal geometry is in cm.

To use different measurements, create a new file in `measurements/`.

## Module structure

Each garment program module typically exposes:

- **`load_measurements(yaml_path)`** — reads YAML, converts units, returns a dict
- **`draft_*(m)`** — takes measurements dict, computes all points/curves/construction geometry, returns a structured result dict
- **`plot_*(draft, output_path)`** — renders the draft to a matplotlib figure
- **`run(measurements_path, output_path, debug, units, context=None)`** — top-level entry point (supports shared runtime context)

Runtime notes:
- `run.py` loads and validates measurements once per invocation and passes them through `PieceRuntimeContext`.
- `garment_programs.core.runtime.resolve_measurements()` provides backward-compatible access to shared measurements.
- `garment_programs.core.runtime.cache_draft()` allows piece modules to reuse draft computations across runs.

This is intentionally procedural (not class-based). Historical drafting is a sequence of geometric operations, and functions map naturally to that.

## Design decisions

- **Bezier curves** for hip, rise, crotch, and inseam — cubic for curves needing tangent control at both ends, quadratic when passing through a specific midpoint
- **matplotlib for visualization** — supports both clean pattern output and debug mode with construction lines, point labels, and grid
- **All geometry in cm internally** — conversions happen at the boundary (load and display)
- **Drafting instructions colocated** with the program code — `*_instructions.md` lives next to the `.py` so the source material is always at hand
- **Generic runner with fzf** — auto-discovers measurements and programs so adding a new garment only requires creating the module
