"""
Helpers for serializing and comparing draft geometry snapshots.

We snapshot the ``points`` and ``curves`` dicts returned by ``draft_*``
functions — the actual coordinate data — rather than rendered images.
Coordinates are rounded to 4 decimals (≈1 micron) for deterministic JSON
output; comparison uses a looser 0.01 cm (0.1 mm) tolerance so float noise
never trips a test but real seam drift does.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

# Keys in a DraftData dict that carry geometry we want to snapshot.
# Everything else (metadata, measurements, construction scalars, levels, …)
# is either derivative or not coordinate-bearing.
GEOMETRY_KEYS = ("points", "curves")

ROUND_DECIMALS = 4


def _round_array(arr: np.ndarray) -> list:
    """Round a numpy array to ROUND_DECIMALS and return a nested list.

    Works for 1-D points ``(2,)``, polylines ``(N, 2)``, and any other
    ndarray shape — ``np.round`` + ``tolist()`` handles nesting.
    """
    return np.round(np.asarray(arr, dtype=float), ROUND_DECIMALS).tolist()


def serialize_draft(draft: dict) -> dict:
    """Convert a DraftData dict to a JSON-serializable geometry-only dict.

    Only ``points`` and ``curves`` are retained. Each numpy array is rounded
    and converted to nested Python lists. Non-array values under those keys
    are skipped (some drafts stash floats or tuples in ``construction`` but
    points/curves should always be arrays).
    """
    out: dict[str, dict] = {}
    for section in GEOMETRY_KEYS:
        src = draft.get(section)
        if not src:
            continue
        serialized: dict[str, list] = {}
        for key in sorted(src):
            val = src[key]
            if isinstance(val, np.ndarray):
                serialized[key] = _round_array(val)
        if serialized:
            out[section] = serialized
    return out


def save_snapshot(path: str | Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def load_snapshot(path: str | Path) -> dict:
    with open(path) as f:
        return json.load(f)


def _flatten(xs) -> list[float]:
    """Flatten an arbitrarily nested list of numbers into a flat list."""
    return np.asarray(xs, dtype=float).ravel().tolist()


def compare_drafts(actual: dict, expected: dict, tol: float = 0.01) -> list[str]:
    """Compare two serialized drafts coordinate-by-coordinate.

    Returns a list of human-readable diff strings. Empty list = match.
    Each entry names the section/key that diverged, the worst-case delta,
    and the index of that worst coordinate.
    """
    diffs: list[str] = []

    for section in GEOMETRY_KEYS:
        a_sec = actual.get(section, {})
        e_sec = expected.get(section, {})

        a_keys = set(a_sec)
        e_keys = set(e_sec)
        for missing in sorted(e_keys - a_keys):
            diffs.append(f"{section}[{missing!r}]: missing in actual")
        for extra in sorted(a_keys - e_keys):
            diffs.append(f"{section}[{extra!r}]: extra in actual (not in snapshot)")

        for key in sorted(a_keys & e_keys):
            a = _flatten(a_sec[key])
            e = _flatten(e_sec[key])
            if len(a) != len(e):
                diffs.append(
                    f"{section}[{key!r}]: length changed "
                    f"({len(e)} → {len(a)} coords)"
                )
                continue
            deltas = [abs(av - ev) for av, ev in zip(a, e)]
            max_delta = max(deltas) if deltas else 0.0
            if max_delta > tol:
                worst_i = deltas.index(max_delta)
                diffs.append(
                    f"{section}[{key!r}]: max delta {max_delta:.4f} cm "
                    f"at coord index {worst_i} "
                    f"(actual={a[worst_i]:.4f}, expected={e[worst_i]:.4f})"
                )

    return diffs
