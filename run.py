#!/usr/bin/env python3
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
    """Import and run a single piece module, returning (output_path, drafts)."""
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
    result = module.run(measurements_path, output_path, debug=debug, units=units, **kwargs)
    return output_path, result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurements', '-m', help='path to measurements YAML file')
    parser.add_argument('--program', '-p', help='garment program module name (e.g. SelvedgeJeans1873 or SelvedgeJeans1873.jeans_front)')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='show construction lines, point labels, and grid')
    parser.add_argument('--units', '-u', choices=['cm', 'inch'], default=None,
                        help='display units for the plot (default: prompt via fzf)')
    parser.add_argument('--format', '-f', choices=['svg', 'pdf'], default=None,
                        help='output format (default: prompt via fzf)')
    parser.add_argument('--nest', action='store_true',
                        help='nest all pieces onto a single fabric strip')
    parser.add_argument('--width', type=float, default=78.74,
                        help='fabric strip width in cm for nesting (default: 78.74 = 31")')
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

    # Resolve program_name to (pkg, garment) if it's a garment
    resolved = None
    if program_name in garment_by_name:
        resolved = garment_by_name[program_name]
    elif program_name in garment_by_pkg:
        resolved = (program_name, garment_by_pkg[program_name])

    if resolved:
        pkg, garment = resolved
        output_dir = f'Logs/{garment["name"]}_{measurements_stem}_{timestamp}'
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        print(f"\n--- {garment['name']} ---")
        print(f"Output: {output_dir}/")
        outputs = []
        drafts_by_module = {}
        for piece in garment['pieces']:
            print(f"  Drafting {piece['name']}...")
            out, result = _run_piece(pkg, piece, measurements_path, debug, units, fmt=fmt, output_dir=output_dir)
            outputs.append((piece['name'], out))
            if result is not None:
                drafts_by_module[piece['module']] = result
        if args.nest:
            from garment_programs.nesting import nest_garment
            nest_path = f'{output_dir}/nested.{fmt}'
            nest_garment(garment['pieces'], drafts_by_module, nest_path,
                         strip_width=args.width, units=units)
            outputs.append(('Nested Layout', nest_path))
        print(f"\nGenerated {len(outputs)} pieces:")
        for name, path in outputs:
            print(f"  {name} -> {path}")
    else:
        # Single piece — may be dotted (pkg.module) or standalone
        parts = program_name.split('.', 1)
        if len(parts) == 2 and parts[0] in pkg_counts:
            # Build a synthetic piece dict for the single-piece run
            piece = {'module': parts[1]}
            _run_piece(parts[0], piece, measurements_path, debug, units, fmt=fmt)[0]
        else:
            module = importlib.import_module(f'garment_programs.{program_name}')
            output_path = f'Logs/{program_name}_{measurements_stem}_{timestamp}.{fmt}'
            module.run(measurements_path, output_path, debug=debug, units=units)


if __name__ == '__main__':
    main()
