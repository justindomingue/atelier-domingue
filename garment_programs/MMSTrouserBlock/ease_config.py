"""Tunable ease parameters for the MM&S trouser block.

Centralises every place the Müller & Sohn draft gives a *range* rather than
a fixed value, so toile-fitting adjustments live in one immutable record
instead of scattered module constants.

YAML hook: add an optional ``ease:`` block to a measurements file and
``load_ease`` will override the matching defaults.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace

import yaml


@dataclass(frozen=True)
class EaseConfig:
    """Ease and fit parameters for the MM&S 1-pleat trouser block.

    Defaults are range midpoints from Müller & Sohn *Fundamentals* pp. 13–19.
    Adjust after toile fitting.

    ``ftw_ease`` is intentionally *not* here — it lives in ``PLEAT_CONFIGS``
    because the PDF ties front-width ease to pleat count (0/1/2-pleat each
    carry a different Ftw allowance), not to body fit.
    """

    # --- Derived-measurement ease ---------------------------------------
    cw_reduction: float = 4.5
    """PDF: 4–5 cm. Crotch width = ¼Hg − this. More → narrower crotch."""

    btw_ease: float = 3.5
    """PDF: 3–4 cm. Back trouser width = ¼Hg + this. More → roomier seat."""

    # --- Back-draft slant (standing vs sitting trade-off) ----------------
    creaseline_shift: float = 1.25
    """PDF: 1–1.5 cm. More → straighter CB, better standing fit."""

    cb_slant: float = 2.5
    """PDF: 2–3 cm. More → straighter CB. Less → more seat length, comfier sitting."""

    cb_height_extra: float = 0.5
    """PDF: 0–1 cm. Extra back-waist height at CB; affects seat length."""

    # --- Fit targets -----------------------------------------------------
    sideseam_intake_target: float = 1.25
    """PDF: 1–1.5 cm. Back waist equation solves darts to land on this intake."""

    hip_verify_ease: float = 3.0
    """PDF: 2.5–3.5 cm. Expected back hip width = ¼Hg + this."""


_FIELD_NAMES = {f.name for f in fields(EaseConfig)}


def load_ease(yaml_path: str) -> EaseConfig:
    """Return an ``EaseConfig`` from the optional ``ease:`` block in *yaml_path*.

    Missing block → all defaults. Unknown keys raise ``ValueError`` so typos
    fail loudly instead of being silently ignored.
    """
    with open(yaml_path) as f:
        payload = yaml.safe_load(f) or {}

    raw = payload.get('ease')
    if not raw:
        return EaseConfig()
    if not isinstance(raw, dict):
        raise ValueError(f"{yaml_path}: 'ease' must be a mapping")

    unknown = set(raw) - _FIELD_NAMES
    if unknown:
        raise ValueError(
            f"{yaml_path}: unknown ease key(s) {sorted(unknown)}; "
            f"valid keys are {sorted(_FIELD_NAMES)}"
        )

    overrides = {k: float(v) for k, v in raw.items()}
    return replace(EaseConfig(), **overrides)
