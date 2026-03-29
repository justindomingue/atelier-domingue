"""Lining panel for the Kinto-style bread bag.

Same as the outer body but shorter — no roll-top allowance.  The lining
sits inside and is seamed to the outer at the top edge, then the bag is
turned right-side-out through a gap left in the lining bottom seam.
"""
from garment_programs.plot_utils import display_scale
from .bag_body import draft_bag_body, plot_bag_body
from .config import BreadBagConfig, SMALL


def run(measurements_path, output_path, debug=False, units='cm', context=None, **kwargs):
    if context is not None and context.measurements:
        cfg = BreadBagConfig.from_measurements(context.measurements)
    else:
        cfg = kwargs.pop('config', None) or SMALL
    draft = draft_bag_body(cfg, include_lining=True)
    outline = plot_bag_body(draft, output_path, debug=debug, units=units)
    if outline:
        return {'layout_outline': outline}
