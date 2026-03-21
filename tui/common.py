"""Shared helpers for TUI prototypes."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
MEASUREMENTS_DIR = ROOT / "measurements"


@dataclass
class RunConfig:
    measurements: str
    program: str
    units: str | None = None
    output_format: str = "svg"
    debug: bool = False


def discover_measurements() -> list[str]:
    """Return available measurement YAML file paths."""
    return sorted(str(p.relative_to(ROOT)) for p in MEASUREMENTS_DIR.glob("*.yaml"))


def discover_programs() -> list[str]:
    """Return garment names discovered from the project runner."""
    root_str = str(ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    from run import _discover_garments  # noqa: WPS433 - intentional local import

    names = sorted(garment["name"] for _, garment in _discover_garments())
    return names


def build_run_command(config: RunConfig) -> list[str]:
    """Build the run.py command line for a given config."""
    cmd = [
        sys.executable,
        str(ROOT / "run.py"),
        "-m",
        config.measurements,
        "-p",
        config.program,
        "-f",
        config.output_format,
    ]
    if config.units is not None:
        cmd.extend(["-u", config.units])
    if config.debug:
        cmd.append("-d")
    return cmd


def run_with_live_output(
    cmd: list[str],
    on_line: Callable[[str], None] | None = None,
) -> tuple[int, list[str]]:
    """Run command and stream stdout/stderr lines as they arrive."""
    # Force the child's Python stdout to be unbuffered — without this it
    # block-buffers when piped and we only see output at process exit.
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    process = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    output: list[str] = []
    assert process.stdout is not None
    for raw in iter(process.stdout.readline, ""):
        line = raw.rstrip("\n")
        output.append(line)
        if on_line is not None:
            on_line(line)
    return process.wait(), output


def extract_output_dir(lines: list[str]) -> str | None:
    """Extract output directory from run output."""
    pattern = re.compile(r"^Output:\s+(.+)$")
    for line in lines:
        match = pattern.search(line.strip())
        if match:
            return match.group(1).rstrip("/")
    return None

