"""Generic TUI runner — select measurements and garment program via fzf."""
import argparse
import importlib
import inspect
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from garment_programs.geometry import INCH
from garment_programs.core.pattern_metadata import (
    clear_active_pattern_context,
    set_active_pattern_context,
)
from garment_programs.measurements import load_measurements
from garment_programs.core.types import PieceRuntimeContext

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


def _supports_param(fn, name):
    """Return True when *fn* accepts *name* or arbitrary keyword args."""
    sig = inspect.signature(fn)
    if name in sig.parameters:
        return True
    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def _invoke_run(module, measurements_path, output_path, debug, units, kwargs=None,
                context=None):
    """Invoke a piece module run() with safe optional kwargs."""
    run_kwargs = dict(kwargs or {})
    if context is not None and _supports_param(module.run, 'context'):
        run_kwargs['context'] = context
    result = module.run(measurements_path, output_path, debug=debug, units=units, **run_kwargs)
    if (
        isinstance(result, dict)
        and str(output_path).endswith('.svg')
        and isinstance(result.get('layout_outline'), dict)
    ):
        sidecar_path = Path(output_path).with_suffix('.outline.json')
        sidecar_path.write_text(json.dumps(result['layout_outline']))
    return result


def _run_piece(pkg, piece, measurements_path, debug, units, fmt='svg', output_dir=None,
               context=None, output_basename=None, extra_kwargs=None):
    """Import and run a single piece module, returning the output path."""
    piece_module = piece['module']
    full_module = f'garment_programs.{pkg}.{piece_module}'
    module = importlib.import_module(full_module)
    measurements_stem = Path(measurements_path).stem
    basename = output_basename or piece_module
    if output_dir:
        output_path = f'{output_dir}/{basename}.{fmt}'
    else:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output_path = f'Logs/{pkg}.{basename}_{measurements_stem}_{timestamp}.{fmt}'
    kwargs = dict(piece.get('kwargs', {}))
    if extra_kwargs:
        kwargs.update(extra_kwargs)
    _invoke_run(module, measurements_path, output_path, debug, units,
                kwargs=kwargs, context=context)
    return output_path


def _sanitize_code_token(value, default='NA'):
    """Return an uppercase alphanumeric token safe for pattern codes."""
    token = re.sub(r'[^A-Za-z0-9]+', '', str(value).upper())
    return token or default


def _infer_variant_code(garment_name):
    """Infer a short variant token from garment name."""
    upper = garment_name.upper()
    if 'MODERN' in upper:
        return 'MOD'
    if '1873' in upper or 'HISTORICAL' in upper:
        return 'HIST'
    return 'STD'


def _infer_garment_code(garment_name):
    """Infer a stable garment token from garment name."""
    upper = garment_name.upper()
    if 'JEANS' in upper and '1873' in upper:
        return 'JE1873'
    words = [w for w in re.split(r'[^A-Za-z0-9]+', upper) if w]
    if not words:
        return 'GARMENT'
    return _sanitize_code_token(''.join(w[:3] for w in words[:3]), default='GARMENT')


def _size_code_from_measurements(measurements):
    """Build a short printable size token from waist measurement."""
    waist_cm = measurements.get('waist')
    if waist_cm is None:
        return 'CUST'
    waist_in = float(waist_cm) / INCH
    rounded = round(waist_in)
    if abs(waist_in - rounded) < 0.05:
        return f'{int(rounded):02d}'
    return f'{waist_in:.1f}'.replace('.', 'P')


def _build_pattern_codes(garment_name, measurements):
    """Build set-level pattern code fields for title blocks."""
    brand = _sanitize_code_token(os.environ.get('PATTERN_BRAND', 'AD'))
    revision = _sanitize_code_token(os.environ.get('PATTERN_REVISION', 'R01'))
    garment_code = _infer_garment_code(garment_name)
    variant = _infer_variant_code(garment_name)
    size_code = _size_code_from_measurements(measurements)
    pattern_set_code = f'{brand}-{garment_code}-{variant}-{size_code}-{revision}'
    return {
        'pattern_set_code': pattern_set_code,
        'size_code': size_code,
        'revision': revision,
    }


def _piece_slug(module_name):
    """Convert a module name to a short piece code token."""
    slug = str(module_name)
    if slug.startswith('jeans_'):
        slug = slug[len('jeans_'):]
    return _sanitize_code_token(slug.replace('_', ''), default='PIECE')[:12]


def _build_piece_code_map(garment, pattern_set_code):
    """Assign stable per-piece codes in garment order."""
    piece_codes = {}
    piece_no = 1
    for piece in garment.get('pieces', []):
        if piece.get('cut_count', 0) <= 0:
            continue
        module = piece['module']
        if module in piece_codes:
            continue
        piece_codes[module] = (
            f'{pattern_set_code}-P{piece_no:02d}-{_piece_slug(module)}'
        )
        piece_no += 1
    return piece_codes


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
    parser.add_argument('--format', '-f', choices=['svg', 'pdf', 'dxf'], default=None,
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
    runtime_context = PieceRuntimeContext(
        measurements_path=str(Path(measurements_path)),
        measurements=load_measurements(measurements_path),
    )

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
        fmt = _fzf_select(['pdf', 'svg', 'dxf'], 'Output format')

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
        pattern_codes = _build_pattern_codes(garment['name'], runtime_context.measurements)
        piece_code_map = _build_piece_code_map(garment, pattern_codes['pattern_set_code'])

        for piece in garment['pieces']:
            print(f"  Drafting {piece['name']}...")
            set_active_pattern_context({
                **pattern_codes,
                'piece_code': piece_code_map.get(piece['module']),
            })

            interfacing_svg_path = None
            try:
                # Always generate SVG (intermediate for layout)
                svg_path = _run_piece(pkg, piece, measurements_path, debug, units,
                                      fmt='svg', output_dir=output_dir,
                                      context=runtime_context)

                # Interfacing gets a dedicated net-shape SVG (no seam allowances)
                if piece.get('interfacing') and not debug:
                    interfacing_svg_path = _run_piece(
                        pkg,
                        piece,
                        measurements_path,
                        debug,
                        units,
                        fmt='svg',
                        output_dir=output_dir,
                        context=runtime_context,
                        output_basename=f"{piece['module']}.interfacing",
                        extra_kwargs={'include_seam_allowance': False},
                    )

                # Also generate requested format if not SVG or DXF
                if fmt not in ['svg', 'dxf']:
                    out = _run_piece(pkg, piece, measurements_path, debug, units,
                                     fmt=fmt, output_dir=output_dir,
                                     context=runtime_context)
                else:
                    out = svg_path
            finally:
                clear_active_pattern_context()

            outputs.append((piece['name'], out))

            # Collect pieces per fabric for lay plan
            cut_count = piece.get('cut_count', 0)
            if cut_count <= 0:
                continue
            fabric = piece.get('fabric', 'main')
            fabric_pieces.setdefault(fabric, []).append(
                (svg_path, cut_count, piece.get('selvedge_edge'),
                 piece.get('grain_axis', 'x')))
            # Interfacing: use dedicated net-shape SVG when available.
            if piece.get('interfacing'):
                interfacing_path = interfacing_svg_path or svg_path
                fabric_pieces.setdefault('interfacing', []).append(
                    (interfacing_path, cut_count, None,
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
            set_active_pattern_context({})
            try:
                # Single pieces can only be output to SVG or PDF directly from matplotlib
                output_fmt = 'svg' if fmt == 'dxf' else fmt
                _run_piece(parts[0], piece, measurements_path, debug, units, fmt=output_fmt,
                           context=runtime_context)
            finally:
                clear_active_pattern_context()
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
            set_active_pattern_context({})
            try:
                _invoke_run(module, measurements_path, output_path, debug, units,
                            context=runtime_context)
            finally:
                clear_active_pattern_context()


if __name__ == '__main__':
    main()
