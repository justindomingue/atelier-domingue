from pathlib import Path

import matplotlib.pyplot as plt

CM_PER_INCH = 2.54


def save_pattern(fig, ax, output_path, units='cm', pad_cm=1.0):
    """Save a pattern figure at 1:1 real-world scale.

    Sets figure dimensions so that 1 data-unit maps to 1 physical unit
    in the output file (1 cm on screen = 1 cm in reality).
    """
    ax.set_aspect('equal')
    ax.margins(0)
    ax.relim()
    ax.autoscale_view()

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()

    pad = pad_cm if units == 'cm' else pad_cm / CM_PER_INCH
    xmin -= pad
    xmax += pad
    ymin -= pad
    ymax += pad
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    data_w = xmax - xmin
    data_h = ymax - ymin
    scale = CM_PER_INCH if units == 'cm' else 1.0
    fig.set_size_inches(data_w / scale, data_h / scale)

    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Saved visualization to {output_path}")
