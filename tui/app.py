"""Interactive TUI for pattern generation (questionary-based)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import questionary
import yaml
from questionary import Choice

if __package__ in (None, ""):
    # Support `python tui/app.py` as well as `python -m tui.app`.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tui.common import (  # type: ignore
        ROOT,
        RunConfig,
        build_run_command,
        discover_measurements,
        discover_programs,
        extract_output_dir,
        run_with_live_output,
    )
else:
    from .common import (
        ROOT,
        RunConfig,
        build_run_command,
        discover_measurements,
        discover_programs,
        extract_output_dir,
        run_with_live_output,
    )


_PREVIEW_KEYS = ("waist", "chest", "seat", "hip", "inseam")


def _preview(path: str) -> str:
    """Summarise a few key measurements from a YAML file."""
    try:
        data = yaml.safe_load((ROOT / path).read_text()) or {}
    except Exception:
        return ""
    meas = data.get("measurements", data)
    unit = meas.get("unit", "")
    parts = [f"{k}={meas[k]}" for k in _PREVIEW_KEYS if k in meas]
    hint = ", ".join(parts[:3])
    return f"  ({hint}{' ' + unit if unit else ''})" if hint else ""


def _cancelled(answer) -> bool:
    return answer is None


def _collect_config(last: RunConfig | None) -> RunConfig | None:
    programs = discover_programs()
    measurements = discover_measurements()
    if not programs or not measurements:
        questionary.print(
            "No garments or measurements found.", style="bold fg:red"
        )
        return None

    program = questionary.select(
        "Garment program",
        choices=programs,
        default=last.program if last and last.program in programs else None,
    ).ask()
    if _cancelled(program):
        return None

    m_choices = [
        Choice(title=f"{Path(m).name}{_preview(m)}", value=m) for m in measurements
    ]
    m_default = next(
        (c for c in m_choices if c.value == (last.measurements if last else None)),
        None,
    )
    meas = questionary.select(
        "Measurements", choices=m_choices, default=m_default
    ).ask()
    if _cancelled(meas):
        return None

    units = questionary.select(
        "Display units",
        choices=["cm", "inch"],
        default=(last.units if last and last.units else "cm"),
    ).ask()
    if _cancelled(units):
        return None

    debug = questionary.confirm(
        "Debug mode (construction lines, grid)?",
        default=last.debug if last else False,
    ).ask()
    if _cancelled(debug):
        return None

    fmt = questionary.select(
        "Output format",
        choices=["svg", "pdf", "dxf"],
        default=last.output_format if last else "svg",
    ).ask()
    if _cancelled(fmt):
        return None

    fw_default = str(last.fabric_width) if last and last.fabric_width else ""
    fw_answer = questionary.text(
        "Fabric width in inches (leave blank for garment default)",
        default=fw_default,
    ).ask()
    if _cancelled(fw_answer):
        return None
    fabric_width = float(fw_answer) if fw_answer.strip() else None

    return RunConfig(
        measurements=meas,
        program=program,
        units=units,
        output_format=fmt,
        debug=debug,
        fabric_width=fabric_width,
    )


def _confirm(config: RunConfig) -> bool:
    questionary.print("\n── Configuration ──", style="bold")
    questionary.print(f"  Garment      : {config.program}")
    questionary.print(f"  Measurements : {config.measurements}")
    questionary.print(f"  Units        : {config.units}")
    questionary.print(f"  Format       : {config.output_format}")
    questionary.print(f"  Debug        : {'yes' if config.debug else 'no'}")
    fw_display = f'{config.fabric_width}"' if config.fabric_width else "garment default"
    questionary.print(f"  Fabric width : {fw_display}")
    lay = "no (debug mode)" if config.debug else f"yes ({config.output_format})"
    questionary.print(f"  Lay plan     : {lay}")
    ok = questionary.confirm("Run?", default=True).ask()
    return bool(ok)


def _run(config: RunConfig) -> str | None:
    cmd = build_run_command(config)
    questionary.print("\n── Running ──", style="bold")
    questionary.print(" ".join(cmd), style="fg:gray")
    print()
    rc, lines = run_with_live_output(
        cmd, on_line=lambda s: print(s, flush=True)
    )
    print()
    if rc != 0:
        questionary.print(f"run.py exited with code {rc}", style="bold fg:red")
        return None
    out_dir = extract_output_dir(lines)
    if out_dir:
        questionary.print(f"Output → {out_dir}", style="bold fg:green")
    return out_dir


def _open_dir(out_dir: str) -> None:
    path = ROOT / out_dir
    if sys.platform == "darwin":
        subprocess.run(["open", str(path)])
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", str(path)])
    else:
        questionary.print(f"Open manually: {path}")


def main() -> int:
    if not sys.stdin.isatty():
        print("tui.app requires an interactive terminal.", file=sys.stderr)
        return 1
    questionary.print("Atelier — Pattern Generator", style="bold underline")
    last: RunConfig | None = None
    while True:
        config = _collect_config(last)
        if config is None:
            return 0
        if not _confirm(config):
            return 0
        last = config
        out_dir = _run(config)

        choices = ["Run again", "Quit"]
        if out_dir:
            choices.insert(0, "Open output folder")
        nxt = questionary.select("Next", choices=choices).ask()
        if nxt == "Open output folder" and out_dir:
            _open_dir(out_dir)
            nxt = questionary.select("Next", choices=["Run again", "Quit"]).ask()
        if nxt != "Run again":
            return 0
        print()


if __name__ == "__main__":
    sys.exit(main())
