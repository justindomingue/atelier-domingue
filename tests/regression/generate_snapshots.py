"""
Generate geometry-snapshot JSON baselines for the regression tests.

Run with::

    python -m tests.regression.generate_snapshots

Each case below calls a ``draft_*`` function with a fixed measurements file,
serializes the resulting geometry, and writes it to ``tests/snapshots/<name>.json``.
Check those files in — they ARE the regression baseline.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from garment_programs.core.runtime import cache_draft
from garment_programs.core.types import PieceRuntimeContext
from garment_programs.measurements import load_measurements

from tests.regression.snapshot_utils import save_snapshot, serialize_draft

REPO_ROOT = Path(__file__).resolve().parents[2]
MEASUREMENTS_DIR = REPO_ROOT / "measurements"
SNAPSHOTS_DIR = REPO_ROOT / "tests" / "snapshots"


@dataclass(frozen=True)
class SnapshotCase:
    """One draft-call to snapshot.

    ``builder`` receives a ``PieceRuntimeContext`` (so dependent pieces can
    share cached upstream drafts — e.g. jeans back needs jeans front) and
    returns the ``DraftData`` dict to serialize.
    """

    name: str
    measurements_file: str
    builder: Callable[[PieceRuntimeContext], dict]


# ---------------------------------------------------------------------------
# Case builders. Each knows how to import and call its draft function.
# The ``ctx``/``cache_draft`` dance mirrors how the runner and
# ``tests/test_verify_selvedge_jeans.py`` memoise dependent drafts.
# ---------------------------------------------------------------------------

def _jeans_front(ctx: PieceRuntimeContext) -> dict:
    from garment_programs.SelvedgeJeans1873.jeans_front import draft_jeans_front

    return cache_draft(ctx, "selvedge.front", lambda: draft_jeans_front(ctx.measurements))


def _jeans_back(ctx: PieceRuntimeContext) -> dict:
    from garment_programs.SelvedgeJeans1873.jeans_back import draft_jeans_back

    front = _jeans_front(ctx)
    return cache_draft(
        ctx, "selvedge.back:0.0000",
        lambda: draft_jeans_back(ctx.measurements, front),
    )


def _trouser_front(ctx: PieceRuntimeContext) -> dict:
    from garment_programs.MMSTrouserBlock.trouser_front import draft_trouser_front

    return cache_draft(ctx, "mms.front", lambda: draft_trouser_front(ctx.measurements))


def _trouser_back(ctx: PieceRuntimeContext) -> dict:
    from garment_programs.MMSTrouserBlock.trouser_back import draft_trouser_back

    front = _trouser_front(ctx)
    return cache_draft(
        ctx, "mms.back",
        lambda: draft_trouser_back(ctx.measurements, front),
    )


def _shirt_front(ctx: PieceRuntimeContext) -> dict:
    from garment_programs.BasicShirtBlock.shirt_front import draft_shirt_front

    return cache_draft(ctx, "shirt.front", lambda: draft_shirt_front(ctx.measurements))


def _shirt_back(ctx: PieceRuntimeContext) -> dict:
    from garment_programs.BasicShirtBlock.shirt_back import draft_shirt_back

    return cache_draft(ctx, "shirt.back", lambda: draft_shirt_back(ctx.measurements))


SNAPSHOT_CASES: list[SnapshotCase] = [
    SnapshotCase("jeans_front", "justin_1873_jeans.yaml", _jeans_front),
    SnapshotCase("jeans_back", "justin_1873_jeans.yaml", _jeans_back),
    SnapshotCase("trouser_front", "size_50.yaml", _trouser_front),
    SnapshotCase("trouser_back", "size_50.yaml", _trouser_back),
    SnapshotCase("shirt_front", "shirt.yaml", _shirt_front),
    SnapshotCase("shirt_back", "shirt.yaml", _shirt_back),
]


# ---------------------------------------------------------------------------


def build_context(measurements_file: str) -> PieceRuntimeContext:
    path = MEASUREMENTS_DIR / measurements_file
    m = load_measurements(str(path))
    return PieceRuntimeContext(measurements_path=str(path), measurements=m)


def run_case(case: SnapshotCase, ctx: PieceRuntimeContext | None = None) -> dict:
    """Build a fresh context (unless one is supplied), run the draft,
    serialize, and return the snapshot dict."""
    if ctx is None:
        ctx = build_context(case.measurements_file)
    draft = case.builder(ctx)
    return serialize_draft(draft)


def snapshot_path(case: SnapshotCase) -> Path:
    return SNAPSHOTS_DIR / f"{case.name}.json"


def main() -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    # Group cases by measurements file so dependent drafts (jeans back needs
    # jeans front, trouser back needs trouser front) share a cache.
    contexts: dict[str, PieceRuntimeContext] = {}
    for case in SNAPSHOT_CASES:
        ctx = contexts.setdefault(
            case.measurements_file, build_context(case.measurements_file)
        )
        snap = run_case(case, ctx)
        out = snapshot_path(case)
        save_snapshot(out, snap)
        n_points = len(snap.get("points", {}))
        n_curves = len(snap.get("curves", {}))
        size_kb = out.stat().st_size / 1024
        print(
            f"  {case.name:<16} → {out.relative_to(REPO_ROOT)}  "
            f"({n_points} points, {n_curves} curves, {size_kb:.1f} KB)"
        )
    print(f"\nWrote {len(SNAPSHOT_CASES)} snapshot(s) to {SNAPSHOTS_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
