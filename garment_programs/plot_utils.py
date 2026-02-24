from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

CM_PER_INCH = 2.54

# -- Standard line styles for pattern pieces --------------------------------
# Seamline: the finished sewing line (thinner)
SEAMLINE = dict(color='blue', linewidth=1.0)
# Cutline: the seam-allowance / cutting line (thicker)
CUTLINE = dict(color='black', linewidth=1.5)


def draw_piece_label(ax, center, title, cut_count=None, fontsize=9):
    """Render piece name and cut count at center of the pattern piece."""
    label = title
    if cut_count:
        label += f'\nCut {cut_count}'
    ax.text(center[0], center[1], label,
            fontsize=fontsize, ha='center', va='center',
            color='black', alpha=0.6,
            bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='none', alpha=0.5))


def draw_grainline(ax, top, bottom, label='GRAIN'):
    """Draw a double-headed grainline arrow between two points."""
    ax.annotate('', xy=top, xytext=bottom,
                arrowprops=dict(arrowstyle='<->', color='black', lw=0.8))
    mid = ((top[0] + bottom[0]) / 2, (top[1] + bottom[1]) / 2)
    angle = np.degrees(np.arctan2(top[1] - bottom[1], top[0] - bottom[0]))
    ax.text(mid[0], mid[1], label, fontsize=7, ha='center', va='center',
            rotation=angle, color='black', alpha=0.6,
            bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))


def draw_calibration_square(ax, size_cm=5.0):
    """Draw a calibration square in the bottom-right corner of the axes.

    Must be called *after* final axis limits are set (save_pattern does
    this automatically when calibration=True).
    """
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    margin = 1.0
    x0 = xmax - margin - size_cm
    y0 = ymin + margin

    rect = mpatches.Rectangle(
        (x0, y0), size_cm, size_cm,
        linewidth=0.8, edgecolor='black', facecolor='none', zorder=5,
    )
    ax.add_patch(rect)
    ax.text(x0 + size_cm / 2, y0 + size_cm / 2,
            f'{size_cm:.0f}\u2009cm', fontsize=6,
            ha='center', va='center', color='black', zorder=5)


def save_pattern(fig, ax, output_path, units='cm', pad_cm=1.0, calibration=False,
                 pdf_pages=None):
    """Save a pattern figure at 1:1 real-world scale.

    Sets figure dimensions so that 1 data-unit maps to 1 physical unit
    in the output file (1 cm on screen = 1 cm in reality).

    If calibration=True, draws a 5 cm calibration square in the corner.
    If pdf_pages is provided, also adds the figure to the multi-page PDF.
    """
    ax.set_aspect('equal')
    ax.margins(0)
    ax.relim()
    ax.autoscale_view()

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    # Minimal padding for SVG intermediates; full padding for printed formats
    if str(output_path).endswith('.svg'):
        pad = 0.1 if units == 'cm' else 0.1 / CM_PER_INCH
    else:
        pad = pad_cm if units == 'cm' else pad_cm / CM_PER_INCH
    xmin -= pad
    xmax += pad
    ymin -= pad
    ymax += pad
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    if calibration and not str(output_path).endswith('.svg'):
        draw_calibration_square(ax)

    data_w = xmax - xmin
    data_h = ymax - ymin
    scale = CM_PER_INCH if units == 'cm' else 1.0
    fig.set_size_inches(data_w / scale, data_h / scale)

    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    if pdf_pages is not None:
        pdf_pages.savefig(fig)
    plt.close(fig)
    print(f"Saved visualization to {output_path}")
