"""Strap for the Kinto-style bread bag.

Each strap is a continuous strip that spans the bag width with tails
extending from each side.  It is folded in half lengthwise, topstitched
closed, then laid flat across one face of the bag and topstitched at the
centre.  The two straps (one per face) cross over the roll-top to tie.

    cut_width  = strap_width × 2   (folded in half)
    cut_length = bag_width + 2 × strap_tail
"""
import numpy as np

from garment_programs.plot_utils import (
    setup_figure, finalize_figure, display_scale,
    draw_seam_allowance, draw_grainline, draw_piece_label, draw_fold_line,
    SEAMLINE,
)
from .config import BreadBagConfig, SMALL


def draft_bag_strap(cfg: BreadBagConfig | None = None):
    c = cfg or SMALL
    sa = c.seam_allowance

    cut_width = c.strap_width * 2
    cut_length = c.width + 2 * c.strap_tail

    bl = np.array([0.0, 0.0])
    br = np.array([cut_width, 0.0])
    tr = np.array([cut_width, cut_length])
    tl = np.array([0.0, cut_length])

    return {
        'points': {'bl': bl, 'br': br, 'tr': tr, 'tl': tl},
        'cut_width': cut_width,
        'cut_length': cut_length,
        'config': c,
        'sa': sa,
    }


def plot_bag_strap(draft, output_path, debug=False, units='cm'):
    pts = draft['points']
    sa = draft['sa']
    cfg = draft['config']
    s, _ = display_scale(units)

    fig, ax, standalone = setup_figure(figsize=(6, 12))

    bl = pts['bl'] * s
    br = pts['br'] * s
    tr = pts['tr'] * s
    tl = pts['tl'] * s

    seamline = np.array([bl, br, tr, tl, bl])
    ax.plot(seamline[:, 0], seamline[:, 1], **SEAMLINE)

    sa_edges = [
        (np.array([bl, tl]), sa, 'fold/topstitch'),
        (np.array([tl, tr]), sa, 'tuck under'),
        (np.array([tr, br]), sa, 'fold/topstitch'),
        (np.array([br, bl]), sa, 'tuck under'),
    ]
    sa_path = draw_seam_allowance(ax, sa_edges, scale=s, label_sas=True, units=units)

    # Centre fold line (lengthwise)
    fold_x = cfg.strap_width * s
    draw_fold_line(ax, (fold_x, tl[1]), (fold_x, bl[1]))

    # Grainline along the length
    cx = draft['cut_width'] / 2 * s
    margin = 1.5 * s
    draw_grainline(ax, (cx, draft['cut_length'] * s - margin),
                       (cx, margin), label='GRAIN')

    draw_piece_label(ax, (cx, draft['cut_length'] / 2 * s), 'Side Strap', cut_count=2)

    cut_outline = sa_path
    return finalize_figure(ax, fig, standalone, output_path, units=units,
                           debug=debug, outline_pts=cut_outline)


def run(measurements_path, output_path, debug=False, units='cm', context=None, **kwargs):
    if context is not None and context.measurements:
        cfg = BreadBagConfig.from_measurements(context.measurements)
    else:
        cfg = kwargs.pop('config', None) or SMALL
    draft = draft_bag_strap(cfg)
    outline = plot_bag_strap(draft, output_path, debug=debug, units=units)
    if outline:
        return {'layout_outline': outline}
