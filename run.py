"""Generic TUI runner — select measurements and garment program via fzf."""
import argparse
import importlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MEASUREMENTS_DIR = Path('measurements')
PROGRAMS_DIR = Path('garment_programs')


def _fzf_select(choices, prompt):
    """Pipe choices to fzf and return the selected one, or None."""
    if not choices:
        print(f"No options found for: {prompt}", file=sys.stderr)
        sys.exit(1)
    if len(choices) == 1:
        print(f"Auto-selected {choices[0]} (only option)")
        return choices[0]
    try:
        result = subprocess.run(
            ['fzf', '--prompt', f'{prompt}: '],
            input='\n'.join(choices),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("fzf not found. Install it or use --measurements and --program flags.", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        sys.exit(130)  # user cancelled
    return result.stdout.strip()


def _discover_garments():
    """Find packages that define a GARMENT or GARMENTS in __init__.py."""
    garments = []
    for init in sorted(PROGRAMS_DIR.glob('*/__init__.py')):
        pkg = init.parent.name
        mod = importlib.import_module(f'garment_programs.{pkg}')
        if hasattr(mod, 'GARMENTS'):
            for garment in mod.GARMENTS:
                garments.append((pkg, garment))
        elif hasattr(mod, 'GARMENT'):
            garments.append((pkg, mod.GARMENT))
    return garments


def _run_piece(pkg, piece, measurements_path, debug, units, fmt='svg', output_dir=None):
    """Import and run a single piece module, returning the output path."""
    piece_module = piece['module']
    full_module = f'garment_programs.{pkg}.{piece_module}'
    module = importlib.import_module(full_module)
    measurements_stem = Path(measurements_path).stem
    if output_dir:
        output_path = f'{output_dir}/{piece_module}.{fmt}'
    else:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output_path = f'Logs/{pkg}.{piece_module}_{measurements_stem}_{timestamp}.{fmt}'
    kwargs = piece.get('kwargs', {})
    module.run(measurements_path, output_path, debug=debug, units=units, **kwargs)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurements', '-m', help='path to measurements YAML file')
    parser.add_argument(
        '--program', '-p',
        help=('garment name, unambiguous package name, or single-piece module '
              '(e.g. "1873 Selvedge Denim Jeans", SelvedgeJeans1873.jeans_front)')
    )
    parser.add_argument('--debug', '-d', action='store_true',
                        help='show construction lines, point labels, and grid')
    parser.add_argument('--units', '-u', choices=['cm', 'inch'], default=None,
                        help='display units for the plot (default: prompt via fzf)')
    parser.add_argument('--format', '-f', choices=['svg', 'pdf'], default=None,
                        help='output format (default: prompt via fzf)')
    parser.add_argument('--fabric-width', type=float, default=None,
                        help='fabric width in inches (overrides garment default)')
    parser.add_argument(
        '--shortest-layout',
        action='store_true',
        help='prefer shortest lay-plan length over matching front/back panel pairing',
    )
    args = parser.parse_args()

    # --- measurements selection ---
    if args.measurements:
        measurements_path = args.measurements
    else:
        yamls = sorted(str(p) for p in MEASUREMENTS_DIR.glob('*.yaml'))
        measurements_path = _fzf_select(yamls, 'Measurements')

    # --- discover garments ---
    garments = _discover_garments()
    # Map by garment name → (pkg, garment) for name-based lookup,
    # and by pkg name when only one garment exists for that package.
    garment_by_name = {garment['name']: (pkg, garment) for pkg, garment in garments}
    # Also allow lookup by package name when unambiguous (single garment per pkg)
    pkg_counts = {}
    for pkg, garment in garments:
        pkg_counts.setdefault(pkg, []).append(garment)
    garment_by_pkg = {pkg: gs[0] for pkg, gs in pkg_counts.items() if len(gs) == 1}

    # --- program selection ---
    if args.program:
        program_name = args.program
    else:
        choices = [garment['name'] for _, garment in garments]
        selected = _fzf_select(choices, 'Program')
        program_name = selected

    # --- mode selection ---
    # -d / --debug enables debug mode; when omitted AND running non-interactively
    # (all other args provided), default to pattern mode without prompting.
    if args.debug:
        debug = True
    elif args.measurements and args.program:
        debug = False
    else:
        mode = _fzf_select(['pattern', 'debug (construction lines, labels, grid)'], 'Mode')
        debug = mode.startswith('debug')

    # --- units selection ---
    if args.units:
        units = args.units
    else:
        units = _fzf_select(['inch', 'cm'], 'Units')

    # --- format selection ---
    if args.format:
        fmt = args.format
    else:
        fmt = _fzf_select(['pdf', 'svg'], 'Output format')

    # --- import and run ---
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    measurements_stem = Path(measurements_path).stem

    # Resolve program_name to (pkg, garment) if it's a garment.
    # Package names are only accepted when unambiguous (single garment).
    resolved = None
    if program_name in garment_by_name:
        resolved = garment_by_name[program_name]
    elif program_name in garment_by_pkg:
        resolved = (program_name, garment_by_pkg[program_name])
    elif program_name in pkg_counts and len(pkg_counts[program_name]) > 1:
        print(
            f"Ambiguous program '{program_name}': package contains multiple garments.",
            file=sys.stderr,
        )
        print("Use one of:", file=sys.stderr)
        for g in pkg_counts[program_name]:
            print(f"  - {g['name']}", file=sys.stderr)
        print(
            "Or run a single piece module (e.g. "
            f"{program_name}.{pkg_counts[program_name][0]['pieces'][0]['module']}).",
            file=sys.stderr,
        )
        sys.exit(2)

    if resolved:
        pkg, garment = resolved
        output_dir = f'Logs/{garment["name"]}_{measurements_stem}_{timestamp}'
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        print(f"\n--- {garment['name']} ---")
        print(f"Output: {output_dir}/")

        outputs = []
        fabric_pieces = {}  # fabric_name -> [(svg_path, cut_count, selvedge_edge, grain_axis)]

        for piece in garment['pieces']:
            print(f"  Drafting {piece['name']}...")

            # Always generate SVG (intermediate for layout)
            svg_path = _run_piece(pkg, piece, measurements_path, debug, units,
                                  fmt='svg', output_dir=output_dir)

            # Also generate requested format if not SVG
            if fmt != 'svg':
                out = _run_piece(pkg, piece, measurements_path, debug, units,
                                 fmt=fmt, output_dir=output_dir)
            else:
                out = svg_path

            outputs.append((piece['name'], out))

            # Collect pieces per fabric for lay plan
            cut_count = piece.get('cut_count', 0)
            if cut_count <= 0:
                continue
            fabric = piece.get('fabric', 'main')
            fabric_pieces.setdefault(fabric, []).append(
                (svg_path, cut_count, piece.get('selvedge_edge'),
                 piece.get('grain_axis', 'x')))
            # Interfacing: same SVG, also placed on interfacing fabric
            if piece.get('interfacing'):
                fabric_pieces.setdefault('interfacing', []).append(
                    (svg_path, cut_count, None,
                     piece.get('grain_axis', 'x')))

        print(f"\nGenerated {len(outputs)} pieces:")
        for name, path in outputs:
            print(f"  {name} -> {path}")

        # Build fabric groups and generate lay plan (pattern mode only)
        if fabric_pieces and not debug:
            from garment_programs.lay_plan import generate_lay_plan

            FABRIC_DEFAULTS = {
                'main':        {'label': 'Main Fabric',  'selvedge': True,  'width': 60},
                'pocketing':   {'label': 'Pocketing',    'selvedge': False, 'width': 45},
                'interfacing': {'label': 'Interfacing',  'selvedge': False, 'width': 20},
            }
            garment_widths = garment.get('fabric_widths', {})

            fabric_groups = []
            for name in ['main'] + sorted(k for k in fabric_pieces if k != 'main'):
                if name not in fabric_pieces:
                    continue
                defaults = FABRIC_DEFAULTS.get(
                    name, {'label': name.title(), 'selvedge': False, 'width': 45})
                fabric_groups.append({
                    'name': name,
                    'label': defaults['label'],
                    'fabric_width': (
                        garment_widths.get(name, defaults['width'])
                        if name != 'main'
                        else (args.fabric_width
                              or garment.get('fabric_width', defaults['width']))
                    ),
                    'selvedge': defaults['selvedge'],
                    'pieces': fabric_pieces[name],
                })

            layout_path = f'{output_dir}/lay_plan.{fmt}'
            print(f"\n  Generating lay plan...")
            generate_lay_plan(fabric_groups, layout_path,
                              units=units, fmt=fmt,
                              prefer_panel_pairing=not args.shortest_layout)
    else:
        # Single piece — may be dotted (pkg.module) or standalone
        parts = program_name.split('.', 1)
        if len(parts) == 2 and parts[0] in pkg_counts:
            # Build a synthetic piece dict for the single-piece run
            piece = {'module': parts[1]}
            _run_piece(parts[0], piece, measurements_path, debug, units, fmt=fmt)
        else:
            if program_name in pkg_counts:
                # Unambiguous package names are handled above; this catches any
                # remaining package-only input before module import.
                print(
                    f"Program '{program_name}' is a garment package, not a runnable piece module.",
                    file=sys.stderr,
                )
                print(
                    "Use a garment name or a dotted piece module "
                    f"(e.g. {program_name}.{pkg_counts[program_name][0]['pieces'][0]['module']}).",
                    file=sys.stderr,
                )
                sys.exit(2)
            module = importlib.import_module(f'garment_programs.{program_name}')
            output_path = f'Logs/{program_name}_{measurements_stem}_{timestamp}.{fmt}'
            module.run(measurements_path, output_path, debug=debug, units=units)


if __name__ == '__main__':
    main()
