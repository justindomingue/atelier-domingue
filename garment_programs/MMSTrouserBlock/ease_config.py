"""Tunable ease parameters for the MM&S trouser block.

Centralises every place the Müller & Sohn draft gives a *range* rather than
a fixed value, so toile-fitting adjustments live in one immutable record
instead of scattered module constants.

YAML hook — three forms accepted under the ``mms_ease`` key::

    # 1. Omit entirely → 'standard' preset (range midpoints)

    # 2. Named preset
    mms_ease: relaxed

    # 3. Preset with per-field overrides
    mms_ease:
      preset: relaxed
      cb_slant: 2.0        # keep the rest of 'relaxed' but tighten CB slant
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace

import yaml


@dataclass(frozen=True)
class EaseConfig:
    """Ease and fit parameters for the MM&S trouser block.

    Defaults are range midpoints from Müller & Sohn *Fundamentals* pp. 13–19.
    Adjust after toile fitting, or pick a preset (``slim``/``standard``/
    ``relaxed``) as a starting point.

    ``ftw_ease`` is intentionally *not* here — it lives in ``PLEAT_CONFIGS``
    because the PDF ties front-width ease to pleat count (0/1/2-pleat each
    carry a different Ftw allowance), not to body fit.
    """

    # --- Derived-measurement ease ---------------------------------------
    cw_reduction: float | None = None
    """PDF: 4–5 cm. Crotch width = ¼Hg − this. More → narrower crotch.
    None = use the per-variant default from PLEAT_CONFIGS (dart=4.5,
    pleated=4.0 — matching the PDF's per-variant charts). Set a value
    only to override all variants uniformly."""

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

    hip_verify_ease: float | None = None
    """PDF: 2.5–3.5 cm (dart/1-pleat) or 3–4 cm (2-pleat). Back hip width
    check = ¼Hg + this. None = use per-variant range from PLEAT_CONFIGS.
    Set a value only to override with a ±0.5 cm window around it."""


_FIELD_NAMES = {f.name for f in fields(EaseConfig)}


# Each preset encodes a coherent fit intent — not simply "all low end" or
# "all high end". Note e.g. *slim* pairs a low btw_ease (tighter seat) with
# a HIGH cw_reduction (narrower crotch), and a straighter CB (less seat
# length) since a closer fit needs less sitting ease.
PRESETS: dict[str, EaseConfig] = {
    'slim': EaseConfig(
        btw_ease=3.0, cw_reduction=5.0,
        creaseline_shift=1.0, cb_slant=2.0, cb_height_extra=0.0,
        sideseam_intake_target=1.0,
    ),
    'standard': EaseConfig(),
    'relaxed': EaseConfig(
        btw_ease=4.0,
        creaseline_shift=1.5, cb_slant=3.0, cb_height_extra=1.0,
        sideseam_intake_target=1.5,
    ),
}


def load_ease(yaml_path: str) -> EaseConfig:
    """Return an ``EaseConfig`` from the optional ``mms_ease`` block.

    Accepts a bare preset name, or a mapping with an optional ``preset``
    key plus per-field overrides. Unknown presets or field names raise
    ``ValueError`` so typos fail loudly.
    """
    with open(yaml_path) as f:
        payload = yaml.safe_load(f) or {}

    block = payload.get('mms_ease')
    if block is None:
        return EaseConfig()

    if isinstance(block, str):
        if block not in PRESETS:
            raise ValueError(
                f"{yaml_path}: unknown mms_ease preset {block!r}; "
                f"choose from {sorted(PRESETS)}"
            )
        return PRESETS[block]

    if not isinstance(block, dict):
        raise ValueError(
            f"{yaml_path}: mms_ease must be a preset name or a mapping"
        )

    overrides = dict(block)
    preset_name = overrides.pop('preset', 'standard')
    if preset_name not in PRESETS:
        raise ValueError(
            f"{yaml_path}: unknown mms_ease preset {preset_name!r}; "
            f"choose from {sorted(PRESETS)}"
        )
    base = PRESETS[preset_name]

    unknown = set(overrides) - _FIELD_NAMES
    if unknown:
        raise ValueError(
            f"{yaml_path}: unknown mms_ease key(s) {sorted(unknown)}; "
            f"valid keys are {sorted(_FIELD_NAMES)}"
        )

    return replace(base, **{k: float(v) for k, v in overrides.items()})
