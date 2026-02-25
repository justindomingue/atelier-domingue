"""Typed models for pattern drafting runtime data."""

from dataclasses import dataclass, field
from typing import Any, Dict, TypedDict


class DraftData(TypedDict, total=False):
    """Common draft structure returned by piece draft functions."""

    points: Dict[str, Any]
    curves: Dict[str, Any]
    construction: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class PieceRuntimeContext:
    """Shared runtime context for a single measurement set."""

    measurements_path: str
    measurements: Dict[str, float]
    cache: Dict[str, Any] = field(default_factory=dict)
