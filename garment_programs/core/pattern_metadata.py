"""Shared render metadata for pattern labeling."""

from __future__ import annotations

from typing import Any

_ACTIVE_PATTERN_CONTEXT: dict[str, Any] = {}


def set_active_pattern_context(context: dict[str, Any] | None) -> None:
    """Set the active pattern-render context for this process."""
    global _ACTIVE_PATTERN_CONTEXT
    if not context:
        _ACTIVE_PATTERN_CONTEXT = {}
        return
    _ACTIVE_PATTERN_CONTEXT = {k: v for k, v in context.items() if v is not None}


def clear_active_pattern_context() -> None:
    """Clear any active pattern-render context."""
    _ACTIVE_PATTERN_CONTEXT.clear()


def get_active_pattern_context() -> dict[str, Any]:
    """Return a copy of the active pattern-render context."""
    return dict(_ACTIVE_PATTERN_CONTEXT)
