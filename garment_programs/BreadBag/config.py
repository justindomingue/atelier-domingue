"""Parametrized dimensions for the Kinto-style bread bag.

All values in cm.  The two preset sizes match the Kinto Futo Bread Bag ALI
(product 24263 = small, 24266 = large).  Override any field to customise.
"""

from dataclasses import dataclass


@dataclass
class BreadBagConfig:
    """Finished (post-sewing) dimensions of the bread bag."""

    # --- bag body ---
    width: float = 11.0       # finished width (front face)
    depth: float = 9.0        # finished depth (boxed bottom)
    height: float = 24.0      # finished height (bottom of bag to roll-top fold)
    roll_top: float = 8.0     # extra height for the roll-top closure

    # --- straps ---
    strap_width: float = 1.5   # finished strap width (folded in half)
    strap_tail: float = 25.0   # free tail length extending past each side

    # --- construction ---
    seam_allowance: float = 1.0   # cm
    hem_allowance: float = 1.0    # top edge turn-under (enclosed by lining)

    @classmethod
    def from_measurements(cls, m: dict[str, float]) -> 'BreadBagConfig':
        """Build config from a measurements dict (values already in cm)."""
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in m.items() if k in fields})


SMALL = BreadBagConfig()

LARGE = BreadBagConfig(
    width=15.0,
    depth=11.0,
    height=28.0,
    roll_top=10.0,
    strap_width=2.0,
    strap_tail=30.0,
)
