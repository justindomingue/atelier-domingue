"""Typed models for pattern drafting runtime data."""

from dataclasses import dataclass, field
from typing import Any, TypedDict


class DraftData(TypedDict, total=False):
    """Common draft structure returned by piece draft functions."""

    points: dict[str, Any]
    curves: dict[str, Any]
    construction: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class PieceRuntimeContext:
    """Shared runtime context for a single measurement set."""

    measurements_path: str
    measurements: dict[str, float]
    cache: dict[str, Any] = field(default_factory=dict)
