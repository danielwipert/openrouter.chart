"""Share over time: 100% stacked area of weekly token share (spec, "Chart design").

One function draws every share chart in style.yaml (weights, price tier, free,
input type, reasoning): bands bottom to top in the configured order, labels
written on the bands, the latest share of the bottom band in a marker, and for
two-way splits a dashed 50% line with the crossover marked.
"""

import textwrap

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.patches import Ellipse

from charts.frame import Frame


def weekly_shares(weekly, dimension, values):
    rows = weekly[(weekly["dimension"] == dimension) & weekly["value"].isin(values)]
    table = rows.pivot(index="period", columns="value", values="share")
    table = table.reindex(columns=values).fillna(0)
    table.index = pd.to_datetime(table.index)
    return table.sort_index()


def lasting_crossover(series):
    """First week after which the series stayed above 50%, or None."""
    above = series > 0.5
    if not above.iloc[-1]:
        return None
    below = above[~above]
    return series.index[0] if below.empty else above[above.index > below.index[-1]].index[0]


def month_ticks(ax, start, end, frame):
    months = pd.date_range(start.replace(day=1), end, freq="MS")
    months = months[months >= start]
    labels = [m.strftime("%b\n%Y") if (m.month == 1 or i == 0) else m.strftime("%b")
              for i, m in enumerate(months)]
    ax.set_xticks(mdates.date2num(months), labels)
    for label in ax.get_xticklabels():
        label.set_fontproperties(frame.font("regular", frame.sizes["axis"]))
        label.set_color(frame.colors["text_muted"])
    ax.tick_params(axis="x", length=6, width=1, color=frame.colors["text_muted"], pad=8)


def percent_axis(ax, frame, pad=10):
    """0-100 axis on the right, grey numbers, no tick marks."""
    ax.set_ylim(0, 1)
    ax.yaxis.tick_right()
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1], ["0", "25", "50", "75", "100"])
    for label in ax.get_yticklabels():
        label.set_fontproperties(frame.font("regular", frame.sizes["axis"]))
        label.set_color(frame.colors["text_muted"])
    ax.tick_params(axis="y", length=0, pad=pad)


def bubble(ax, frame, x, y, text, color, radius_px):
    """A filled circle on the data with white text inside (like a year marker)."""
    px_per_x = ax.bbox.width / (ax.get_xlim()[1] - ax.get_xlim()[0])
    px_per_y = ax.bbox.height / (ax.get_ylim()[1] - ax.get_ylim()[0])
    ax.add_patch(Ellipse((x, y), 2 * radius_px / px_per_x, 2 * radius_px / px_per_y,
                         facecolor=color, edgecolor=frame.colors["background"], linewidth=2,
                         zorder=6, clip_on=False))
    ax.text(x, y, text, ha="center", va="center", color="#FFFFFF", zorder=7,
            fontproperties=frame.font("semibold", frame.sizes["bubble"]), clip_on=False)


def label_spot(bottom, top, start_fraction=0.35, end_fraction=0.85):
    """Index of the week where a band is thickest, looking at the later part of
    the chart (labels read best near the present) but not at its right edge."""
    first, last = int(len(bottom) * start_fraction), int(len(bottom) * end_fraction)
    thickness = (top - bottom)[first:last]
    if thickness.max() < 0.15:  # thin band late on: use its thickest week anywhere
        first = int(len(bottom) * 0.05)
        thickness = (top - bottom)[first:last]
    return first + int(np.argmax(thickness))


def title(weekly, monthly, spec):
    focus = weekly_shares(weekly, spec["dimension"], spec["values"])[spec["values"][0]]
    return spec["title"].format(share=round(focus.iloc[-1] * 100))


def render(weekly, monthly, footer_text, style, size, spec):
    colors = style["colors"]
    sizes = style["text_sizes"]
    values = spec["values"]
    shares = weekly_shares(weekly, spec["dimension"], values)
    x = shares.index
    xn = mdates.date2num(x)
    focus = shares[values[0]]
    last_week_end = x[-1] + pd.Timedelta(days=6)

    frame = Frame(style, size)
    frame.title(title(weekly, monthly, spec))
    frame.subtitle(spec["subtitle"].format(first=x[0].strftime("%b %Y"),
                                           last=last_week_end.strftime("%b %Y")))
    frame.units(style["layout"]["units"])
    frame.footer(footer_text)
    ax = frame.chart_area(right_px=96, below_px=66)
    ax.set_xlim(xn[0], xn[-1])
    percent_axis(ax, frame, pad=48)  # room for the end marker
    month_ticks(ax, x[0], x[-1], frame)

    # Bands, a white line between each, white gridlines on top
    bottom = np.zeros(len(x))
    edges = []
    for value, fill in zip(values, spec["fills"]):
        top = bottom + shares[value].to_numpy()
        ax.fill_between(xn, bottom, top, color=fill, linewidth=0, zorder=1)
        edges.append((bottom, top))
        bottom = top
    for lower, _ in edges[1:]:
        ax.plot(xn, lower, color=colors["background"], linewidth=2.5, zorder=2)
    for y in (0.25, 0.75):
        ax.axhline(y, color=colors["background"], linewidth=1.2, alpha=0.9, zorder=2)

    # Labels written on each band, where it is thickest
    for (lower, upper), label, ink in zip(edges, spec["labels"], spec["inks"]):
        i = label_spot(lower, upper)
        if upper[i] - lower[i] > 0.07:
            y = (lower[i] + upper[i]) / 2
            if len(values) == 2 and abs(y - 0.5) < 0.05:  # step off the dashed 50% line
                y = 0.5 + 0.06 if y >= 0.5 else 0.5 - 0.06
            ax.text(xn[i], y, label, ha="center", va="center",
                    color=ink, fontproperties=frame.font("bold", sizes["label"]), zorder=4)

    # Latest share of the bottom band in a marker at the right edge
    marker_y = min(max(focus.iloc[-1], 0.07), 0.92)  # keep clear of the 0 and 100 labels
    bubble(ax, frame, xn[-1], marker_y, f"{focus.iloc[-1]:.0%}", spec["inks"][0]
           if spec["inks"][0] != "#FFFFFF" else colors["open_dark"], 33)

    # Two-way splits: dashed 50% line, crossover marker and note
    if len(values) == 2:
        ax.axhline(0.5, color=colors["reference_line"], linewidth=1.6, linestyle=(0, (5, 3)),
                   zorder=3)
        week = lasting_crossover(focus)
        if week is not None and week != x[0] and spec.get("crossover_note"):
            date = week.strftime("%b %-d")
            bubble(ax, frame, mdates.date2num(week), 0.5, date, colors["accent"], 36)
            note = textwrap.fill(spec["crossover_note"].format(date=date), 34)
            ax.text(0.03, 0.95, "→", transform=ax.transAxes, ha="left", va="top",
                    color=colors["accent"], zorder=5,
                    fontproperties=frame.font("bold", sizes["annotation"]))
            ax.text(0.03 + 26 / ax.bbox.width, 0.95, note, transform=ax.transAxes, ha="left",
                    va="top", color=colors["text"], linespacing=1.25, zorder=5,
                    fontproperties=frame.font("regular", sizes["annotation"]))
    return frame
