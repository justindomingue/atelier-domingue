"""Outer body panel for the Kinto-style bread bag.

The body is a rectangle with notched bottom corners for boxed-corner
construction.  Each notch is depth/2 square — when you sew the side
seam down to the notch, then sew the bottom, you open the notch flat
and stitch across to form the boxed bottom.

    panel_width  = width + depth
    panel_height = height + roll_top + depth/2
    notch         = depth/2 × depth/2 at each bottom corner
"""
import numpy as np

from garment_programs.plot_utils import (
    setup_figure, finalize_figure, display_scale,
    draw_seam_allowance, draw_grainline, draw_piece_label, draw_fold_line,
    SEAMLINE,
)
from .config import BreadBagConfig, SMALL


def draft_bag_body(cfg: BreadBagConfig | None = None, include_lining: bool = False):
    """Return points and metadata for one body panel (outer or lining).

    The lining omits the roll-top allowance so it sits below the fold line.
    The bottom corners are notched (depth/2 square) for boxed-corner sewing.
    """
    c = cfg or SMALL
    sa = c.seam_allowance

    panel_height = c.height + (0.0 if include_lining else c.roll_top) + c.depth / 2
    panel_width = c.width + c.depth
    notch = c.depth / 2

    # Seamline with notched corners (square cut-outs at each bottom corner)
    #
    #   tl──────────────────tr
    #   │                    │
    #   │                    │
    #   nl_o  ┌──────┐  nr_o
    #   │     │      │      │
    #         nl_i  nr_i
    #         │      │
    #         nl_b──nr_b
    #
    nl_b  = np.array([notch, 0.0])                # left notch, bottom
    nl_i  = np.array([notch, notch])              # left notch, inner corner
    nl_o  = np.array([0.0, notch])                # left notch, outer corner
    tl    = np.array([0.0, panel_height])
    tr    = np.array([panel_width, panel_height])
    nr_o  = np.array([panel_width, notch])        # right notch, outer corner
    nr_i  = np.array([panel_width - notch, notch])  # right notch, inner corner
    nr_b  = np.array([panel_width - notch, 0.0])  # right notch, bottom

    return {
        'points': {
            'nl_b': nl_b, 'nl_i': nl_i, 'nl_o': nl_o,
            'tl': tl, 'tr': tr,
            'nr_o': nr_o, 'nr_i': nr_i, 'nr_b': nr_b,
        },
        'panel_width': panel_width,
        'panel_height': panel_height,
        'notch': notch,
        'config': c,
        'sa': sa,
        'is_lining': include_lining,
    }


def plot_bag_body(draft, output_path, debug=False, units='cm'):
    pts = draft['points']
    sa = draft['sa']
    cfg = draft['config']
    s, _ = display_scale(units)

    fig, ax, standalone = setup_figure(figsize=(10, 14))

    # Scale points for display
    nl_b = pts['nl_b'] * s
    nl_i = pts['nl_i'] * s
    nl_o = pts['nl_o'] * s
    tl   = pts['tl'] * s
    tr   = pts['tr'] * s
    nr_o = pts['nr_o'] * s
    nr_i = pts['nr_i'] * s
    nr_b = pts['nr_b'] * s

    # Draw seamline (CW: bottom-left up around to bottom-right)
    seamline = np.array([nl_b, nl_i, nl_o, tl, tr, nr_o, nr_i, nr_b, nl_b])
    ax.plot(seamline[:, 0], seamline[:, 1], **SEAMLINE)

    # Seam allowance edges (CW around the notched shape)
    sa_edges = [
        (np.array([nl_b, nl_i]), sa, 'box corner'),
        (np.array([nl_i, nl_o]), sa, 'box corner'),
        (np.array([nl_o, tl]),   sa, 'side seam'),
        (np.array([tl, tr]),     sa, 'top edge'),
        (np.array([tr, nr_o]),   sa, 'side seam'),
        (np.array([nr_o, nr_i]), sa, 'box corner'),
        (np.array([nr_i, nr_b]), sa, 'box corner'),
        (np.array([nr_b, nl_b]), sa, 'bottom seam'),
    ]
    sa_path = draw_seam_allowance(ax, sa_edges, scale=s, label_sas=True, units=units)

    # Grainline (vertical, centred)
    cx = draft['panel_width'] / 2 * s
    margin = 2.0 * s
    draw_grainline(ax, (cx, draft['panel_height'] * s - margin),
                       (cx, draft['notch'] * s + margin), label='GRAIN')

    # Roll-top fold line (outer body only)
    if not draft['is_lining']:
        fold_y = (cfg.height + cfg.depth / 2) * s
        draw_fold_line(ax, (tl[0], fold_y), (nr_o[0], fold_y))

    # Label
    label = 'Lining Body' if draft['is_lining'] else 'Outer Body'
    draw_piece_label(ax, (cx, draft['panel_height'] / 2 * s), label, cut_count=2)

    # Outline for lay plan
    cut_outline = sa_path

    return finalize_figure(ax, fig, standalone, output_path, units=units,
                           debug=debug, outline_pts=cut_outline)


def run(measurements_path, output_path, debug=False, units='cm', context=None, **kwargs):
    if context is not None and context.measurements:
        cfg = BreadBagConfig.from_measurements(context.measurements)
    else:
        cfg = kwargs.pop('config', None) or SMALL
    draft = draft_bag_body(cfg, include_lining=False)
    outline = plot_bag_body(draft, output_path, debug=debug, units=units)
    if outline:
        return {'layout_outline': outline}
