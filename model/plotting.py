"""Shared chart styling for the Discovering Cricket Data notebooks.

Every chart is drawn twice - once for a light background and once for a dark one -
so the README can serve whichever matches the reader's theme.
"""
import os

import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path

FIG_DIR = '../figures'
SOURCE = 'Source: Cricsheet T20 international data (ODC-By 1.0)'

THEMES = {
    'light': {
        'surface': '#fcfcfb', 'ink': '#0b0b0b', 'ink_2': '#52514e', 'muted': '#898781',
        'grid': '#e1e0d9', 'axis': '#c3c2b7', 'wash': '#0b0b0b',
        'men': '#2a78d6', 'women': '#eb6834', 'context': '#898781',
    },
    'dark': {
        'surface': '#1a1a19', 'ink': '#f0efec', 'ink_2': '#c3c2b7', 'muted': '#898781',
        'grid': '#2c2c2a', 'axis': '#383835', 'wash': '#f0efec',
        'men': '#3987e5', 'women': '#d95926', 'context': '#898781',
    },
}

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Noto Sans', 'Open Sans', 'DejaVu Sans'],
    'font.size': 10,
    'figure.dpi': 100,
    'savefig.dpi': 200,
})


def new_figure(theme, nrows=1, figsize=(9, 5), **kwargs):
    fig, axes = plt.subplots(nrows, 1, figsize=figsize, facecolor=theme['surface'], **kwargs)
    for ax in (axes if nrows > 1 else [axes]):
        style_axes(ax, theme)
    return fig, axes


def style_axes(ax, theme):
    """Recessive chrome: hairline y-grid, a single baseline, no tick marks."""
    ax.set_facecolor(theme['surface'])
    for side in ('top', 'right', 'left'):
        ax.spines[side].set_visible(False)
    ax.spines['bottom'].set_color(theme['axis'])
    ax.tick_params(which='both', length=0, labelcolor=theme['ink_2'], pad=6)
    ax.grid(axis='y', color=theme['grid'], linewidth=1)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(theme['ink_2'])
    ax.yaxis.label.set_color(theme['ink_2'])


def titles(fig, theme, title, subtitle=None, source=SOURCE):
    """Left-aligned title and subtitle above the plot, source note below it."""
    fig.text(0.06, 0.965, title, color=theme['ink'], fontsize=14, fontweight='medium', va='top')
    if subtitle:
        fig.text(0.06, 0.915, subtitle, color=theme['ink_2'], fontsize=10.5, va='top')
    if source:
        fig.text(0.06, 0.02, source, color=theme['muted'], fontsize=8, va='bottom')


def column(ax, x, bottom, top, width, color, radius_px=4, round_top=True):
    """A column with 4px rounded corners at its data end and a square baseline.

    Call after the axis limits are final - the radius is converted from pixels to data units.
    """
    if top <= bottom:
        return
    (x0_px, y0_px), (x1_px, y1_px) = ax.transData.transform([(0, 0), (1, 1)])
    rx = radius_px / (x1_px - x0_px)
    ry = min(radius_px / (y1_px - y0_px), (top - bottom) / 2)
    left, right = x - width / 2, x + width / 2
    if not round_top:
        rx = ry = 0
    verts = [(left, bottom), (left, top - ry), (left, top), (left + rx, top),
             (right - rx, top), (right, top), (right, top - ry), (right, bottom), (left, bottom)]
    codes = [Path.MOVETO, Path.LINETO, Path.CURVE3, Path.CURVE3,
             Path.LINETO, Path.CURVE3, Path.CURVE3, Path.LINETO, Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), facecolor=color, edgecolor='none'))


def px_to_data_y(ax, px):
    (_, y0), (_, y1) = ax.transData.transform([(0, 0), (0, 1)])
    return px / (y1 - y0)


def save_both(plot_fn, name, *args, **kwargs):
    """Render plot_fn(theme, ...) in light and dark; keep the light figure open for the notebook."""
    os.makedirs(FIG_DIR, exist_ok=True)
    for mode, theme in THEMES.items():
        fig = plot_fn(theme, *args, **kwargs)
        fig.savefig(f'{FIG_DIR}/{name}-{mode}.png', facecolor=theme['surface'])
        if mode == 'dark':
            plt.close(fig)
