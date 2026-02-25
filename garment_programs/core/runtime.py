"""Runtime helpers for shared measurement resolution and draft memoization."""

from pathlib import Path
from typing import Callable, TypeVar

from garment_programs.core.types import PieceRuntimeContext

T = TypeVar("T")


def resolve_measurements(
    context: PieceRuntimeContext | None,
    measurements_path: str,
    loader: Callable[[str], dict[str, float]],
) -> dict[str, float]:
    """Resolve measurements from shared context when possible."""
    normalized = str(Path(measurements_path))
    if context is not None and context.measurements_path == normalized:
        return context.measurements
    return loader(measurements_path)


def cache_draft(
    context: PieceRuntimeContext | None,
    key: str,
    factory: Callable[[], T],
) -> T:
    """Memoize draft artifacts inside a shared context."""
    if context is None:
        return factory()
    if key not in context.cache:
        context.cache[key] = factory()
    return context.cache[key]
