"""
Geometry-snapshot regression tests.

For each case in ``SNAPSHOT_CASES`` we re-run the draft function, serialize
the resulting points/curves, and compare against the checked-in JSON snapshot.
Any coordinate that drifts by more than 0.01 cm (0.1 mm) fails the test with
a report of which key moved and by how much.

If you intentionally change geometry, regenerate with::

    python -m tests.regression.generate_snapshots
"""
from __future__ import annotations

import pytest

from tests.regression.generate_snapshots import (
    SNAPSHOT_CASES,
    SnapshotCase,
    run_case,
    snapshot_path,
)
from tests.regression.snapshot_utils import compare_drafts, load_snapshot


@pytest.mark.parametrize(
    "case", SNAPSHOT_CASES, ids=[c.name for c in SNAPSHOT_CASES]
)
def test_draft_matches_snapshot(case: SnapshotCase):
    snap_file = snapshot_path(case)
    if not snap_file.exists():
        pytest.skip(
            f"Snapshot not generated — run "
            f"`python -m tests.regression.generate_snapshots`"
        )

    expected = load_snapshot(snap_file)
    actual = run_case(case)

    diffs = compare_drafts(actual, expected, tol=0.01)
    if diffs:
        header = f"{case.name}: {len(diffs)} geometry diff(s) vs {snap_file.name}"
        pytest.fail(header + "\n  " + "\n  ".join(diffs))
