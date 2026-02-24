"""
Shared geometric primitives for garment pattern drafting.

Provides Bezier curve evaluation, arc-length interpolation, and measurement
annotation helpers used across all garment programs.
"""
import numpy as np

INCH = 2.54  # cm per inch -- single source of truth for unit conversion


# -- Bezier helpers -----------------------------------------------------------

def _bezier_cubic(P0, P1, P2, P3, n=100):
    """Evaluate a cubic Bezier curve at *n* equally-spaced parameter values."""
    t = np.linspace(0, 1, n).reshape(-1, 1)
    return (1-t)**3 * P0 + 3*(1-t)**2 * t * P1 + 3*(1-t) * t**2 * P2 + t**3 * P3


def _bezier_quad(P0, P1, P2, n=100):
    """Evaluate a quadratic Bezier curve at *n* equally-spaced parameter values."""
    t = np.linspace(0, 1, n).reshape(-1, 1)
    return (1-t)**2 * P0 + 2*(1-t) * t * P1 + t**2 * P2


# -- Arc-length helpers -------------------------------------------------------

def _curve_length(pts):
    """Arc length of a polyline (Nx2 array)."""
    diffs = np.diff(pts, axis=0)
    return np.sum(np.sqrt(diffs[:, 0]**2 + diffs[:, 1]**2))


def _point_at_arclength(curve, dist):
    """Interpolated (x, y) at *dist* arc-length from the start of a polyline."""
    diffs = np.diff(curve, axis=0)
    seg_lengths = np.sqrt(diffs[:, 0]**2 + diffs[:, 1]**2)
    cum = np.concatenate([[0.0], np.cumsum(seg_lengths)])
    if dist <= 0:
        return curve[0].copy()
    if dist >= cum[-1]:
        return curve[-1].copy()
    idx = max(0, int(np.searchsorted(cum, dist)) - 1)
    idx = min(idx, len(curve) - 2)
    t = (dist - cum[idx]) / seg_lengths[idx]
    return curve[idx] * (1 - t) + curve[idx + 1] * t


def _curve_up_to_arclength(curve, dist):
    """Sub-polyline from ``curve[0]`` to the point at *dist* arc-length."""
    diffs = np.diff(curve, axis=0)
    seg_lengths = np.sqrt(diffs[:, 0]**2 + diffs[:, 1]**2)
    cum = np.concatenate([[0.0], np.cumsum(seg_lengths)])
    if dist >= cum[-1]:
        return curve.copy()
    idx = max(0, int(np.searchsorted(cum, dist)) - 1)
    idx = min(idx, len(curve) - 2)
    t = (dist - cum[idx]) / seg_lengths[idx]
    endpoint = curve[idx] * (1 - t) + curve[idx + 1] * t
    return np.vstack([curve[:idx + 1], endpoint.reshape(1, 2)])


def _curve_from_arclength(curve, dist):
    """Sub-polyline from the point at *dist* arc-length to ``curve[-1]``."""
    diffs = np.diff(curve, axis=0)
    seg_lengths = np.sqrt(diffs[:, 0]**2 + diffs[:, 1]**2)
    cum = np.concatenate([[0.0], np.cumsum(seg_lengths)])
    if dist <= 0:
        return curve.copy()
    if dist >= cum[-1]:
        return curve[-1:].copy()
    idx = max(0, int(np.searchsorted(cum, dist)) - 1)
    idx = min(idx, len(curve) - 2)
    t = (dist - cum[idx]) / seg_lengths[idx]
    startpoint = curve[idx] * (1 - t) + curve[idx + 1] * t
    return np.vstack([startpoint.reshape(1, 2), curve[idx + 1:]])


# -- Annotation helpers -------------------------------------------------------

def _annotate_curve(ax, pts, offset=(0, 6)):
    """Label a curve with its arc length at the midpoint."""
    length = _curve_length(pts)
    mid = pts[len(pts) // 2]
    ax.annotate(f'{length:.1f}', mid, textcoords="offset points",
                xytext=offset, fontsize=6, color='darkblue', ha='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))


def _annotate_segment(ax, p0, p1, offset=(0, 6)):
    """Label a straight segment with its length at the midpoint."""
    length = np.linalg.norm(p1 - p0)
    mid = (p0 + p1) / 2
    ax.annotate(f'{length:.1f}', mid, textcoords="offset points",
                xytext=offset, fontsize=6, color='darkblue', ha='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))


def _annotate_len(ax, pts, offset=(0, 6), label=None):
    """Label a polyline/curve with its arc length at the midpoint.

    Like _annotate_curve but with an optional prefix label.
    """
    length = _curve_length(np.atleast_2d(pts))
    mid = pts[len(pts) // 2]
    text = f'{length:.1f}' if label is None else f'{label} {length:.1f}'
    ax.annotate(text, mid, textcoords='offset points',
                xytext=offset, fontsize=6, color='darkblue', ha='center',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='none', alpha=0.7))
