"""End-to-end pipeline: YAML measurements → Seamly2D .sm2d → PDF/SVG output.

Usage:
    python seamly2d_port/run_seamly.py [options]

Options:
    --yaml PATH          YAML measurement file (default: measurements/justin_1873_jeans.yaml)
    --pattern PATH       Pre-built .sm2d pattern file (default: generates jeans front)
    --format FORMAT      Output format: svg, pdf, tiled, png, dxf (default: tiled)
    --output-dir PATH    Output directory (default: seamly2d_port/output)
    --basename NAME      Base filename for output (default: jeans_front)
    --generate-only      Only generate .sm2d/.smis, skip Seamly2D export
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from measurements import convert as generate_smis, load_yaml_measurements, to_cm
from generate_jeans_front import build_jeans_front

FORMAT_MAP = {
    "svg": 0,
    "pdf": 1,
    "tiled": 2,
    "png": 3,
    "dxf": 14,
}


def find_seamly2d() -> str:
    for name in ["seamly2d"]:
        result = subprocess.run(["which", name], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    raise FileNotFoundError(
        "seamly2d not found. Install via Nix: nix-env -iA nixpkgs.seamly2d"
    )


def run_pipeline(
    yaml_path: str,
    pattern_path: str | None,
    output_format: str,
    output_dir: str,
    basename: str,
    generate_only: bool = False,
) -> list[str]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    smis_path = output_dir / f"{basename}_measurements.smis"
    generate_smis(yaml_path, str(smis_path))
    print(f"  Generated measurements: {smis_path}")

    if pattern_path is None:
        pattern_path = output_dir / f"{basename}.sm2d"
        raw, unit = load_yaml_measurements(yaml_path)
        custom = {}
        yaml_to_inc = {
            "waistband_width": "wb",
            "hem_width": "hemW",
            "knee_width": "kneeW",
        }
        for yaml_key, inc_key in yaml_to_inc.items():
            if yaml_key in raw:
                custom[inc_key] = str(to_cm(raw[yaml_key], unit))
        xml = build_jeans_front(str(smis_path), custom_measurements=custom)
        with open(pattern_path, "w") as f:
            f.write(xml)
        print(f"  Generated pattern: {pattern_path}")
    else:
        pattern_path = Path(pattern_path)

    if generate_only:
        print("  Generate-only mode; skipping Seamly2D export.")
        return [str(smis_path), str(pattern_path)]

    seamly_bin = find_seamly2d()
    fmt_num = FORMAT_MAP.get(output_format, 0)

    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    if "XDG_RUNTIME_DIR" not in env:
        env["XDG_RUNTIME_DIR"] = "/tmp/runtime-runner"

    cmd = [
        seamly_bin,
        "-b", basename,
        "-f", str(fmt_num),
        "-d", str(output_dir.resolve()),
        "-m", str(smis_path.resolve()),
        str(pattern_path.resolve()),
    ]

    print(f"  Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        print(f"  Seamly2D stderr:\n{result.stderr}", file=sys.stderr)
        raise RuntimeError(f"Seamly2D exited with code {result.returncode}")

    outputs = sorted(output_dir.glob(f"{basename}*"))
    exported = [
        str(f) for f in outputs
        if f.suffix in (".svg", ".pdf", ".png", ".dxf") and f.name != pattern_path.name
    ]

    print(f"  Exported {len(exported)} file(s):")
    for f in exported:
        size = Path(f).stat().st_size
        print(f"    {f} ({size:,} bytes)")

    return exported


def main():
    parser = argparse.ArgumentParser(
        description="Atelier Domingue → Seamly2D pipeline"
    )
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    default_yaml = str(project_root / "measurements" / "justin_1873_jeans.yaml")

    parser.add_argument(
        "--yaml", default=default_yaml,
        help="YAML measurement file"
    )
    parser.add_argument(
        "--pattern", default=None,
        help="Pre-built .sm2d pattern file (default: auto-generate jeans front)"
    )
    parser.add_argument(
        "--format", default="tiled", choices=FORMAT_MAP.keys(),
        help="Output format (default: tiled)"
    )
    parser.add_argument(
        "--output-dir", default="seamly2d_port/output",
        help="Output directory"
    )
    parser.add_argument(
        "--basename", default="jeans_front",
        help="Base filename for output"
    )
    parser.add_argument(
        "--generate-only", action="store_true",
        help="Only generate .sm2d/.smis, skip export"
    )

    args = parser.parse_args()

    print("Atelier Domingue → Seamly2D Pipeline")
    print("=" * 40)

    try:
        files = run_pipeline(
            yaml_path=args.yaml,
            pattern_path=args.pattern,
            output_format=args.format,
            output_dir=args.output_dir,
            basename=args.basename,
            generate_only=args.generate_only,
        )
        print(f"\nDone. {len(files)} output file(s).")
        return 0
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
