"""Share over time: 100% stacked area of weekly token share (spec, "Chart design").

Phase 1 draws weights: open-weight on the bottom, closed-weight on top,
with a dashed 50% line. Stealth models are left out of the split.
"""

import textwrap

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.patches import Ellipse

from charts.frame import Frame


def weekly_shares(weekly, dimension, values):
    rows = weekly[(weekly["dimension"] == dimension) & weekly["value"].isin(values)]
    table = rows.pivot(index="period", columns="value", values="share").fillna(0)
    table.index = pd.to_datetime(table.index)
    return table[values].sort_index()


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


def bubble(ax, frame, x, y, text, color, radius_px):
    """A filled circle on the data with white text inside (like a year marker)."""
    px_per_x = ax.bbox.width / (ax.get_xlim()[1] - ax.get_xlim()[0])
    px_per_y = ax.bbox.height / (ax.get_ylim()[1] - ax.get_ylim()[0])
    ax.add_patch(Ellipse((x, y), 2 * radius_px / px_per_x, 2 * radius_px / px_per_y,
                         facecolor=color, edgecolor=frame.colors["background"], linewidth=2,
                         zorder=6, clip_on=False))
    ax.text(x, y, text, ha="center", va="center", color="#FFFFFF", zorder=7,
            fontproperties=frame.font("semibold", frame.sizes["bubble"]), clip_on=False)


def render(weekly, footer_text, style, size):
    text = style["text"]["weights_share"]
    colors = style["colors"]
    sizes = style["text_sizes"]
    shares = weekly_shares(weekly, "weights", ["open", "closed"])
    x, open_, closed = shares.index, shares["open"], shares["closed"]
    xn = mdates.date2num(x)
    last_week_end = x[-1] + pd.Timedelta(days=6)

    frame = Frame(style, size)
    frame.title(text["title"].format(share=round(open_.iloc[-1] * 100)))
    frame.subtitle(text["subtitle"].format(first=x[0].strftime("%b %Y"),
                                           last=last_week_end.strftime("%b %Y")))
    frame.units(text["units"])
    frame.footer(footer_text)
    ax = frame.chart_area(right_px=96, below_px=66)

    # Bands, with a white line between them and white gridlines on top
    ax.fill_between(xn, 0, open_, color=colors["open"], linewidth=0, zorder=1)
    ax.fill_between(xn, open_, 1, color=colors["closed"], linewidth=0, zorder=1)
    ax.plot(xn, open_, color=colors["background"], linewidth=2.5, zorder=2)
    for y in (0.25, 0.75):
        ax.axhline(y, color=colors["background"], linewidth=1.2, alpha=0.9, zorder=2)
    ax.axhline(0.5, color=colors["reference_line"], linewidth=1.6, linestyle=(0, (5, 3)),
               zorder=3)

    ax.set_xlim(xn[0], xn[-1])
    ax.set_ylim(0, 1)
    ax.yaxis.tick_right()
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1], ["0", "25", "50", "75", "100"])
    for label in ax.get_yticklabels():
        label.set_fontproperties(frame.font("regular", sizes["axis"]))
        label.set_color(colors["text_muted"])
    ax.tick_params(axis="y", length=0, pad=48)  # room for the end marker
    month_ticks(ax, x[0], x[-1], frame)

    # Labels written on the bands
    i_open = int(len(xn) * 0.72)
    ax.text(xn[i_open], open_.iloc[i_open] * 0.42, text["open"], ha="center", va="center",
            color=colors["open_dark"], fontproperties=frame.font("bold", sizes["label"]),
            zorder=4)
    i_closed = int(len(xn) * 0.62)
    ax.text(xn[i_closed], (1 + open_.iloc[i_closed]) / 2 + 0.03, text["closed"],
            ha="center", va="center", color=colors["closed_dark"],
            fontproperties=frame.font("bold", sizes["label"]), zorder=4)

    # Latest share in a marker at the right edge
    bubble(ax, frame, xn[-1], open_.iloc[-1], f"{open_.iloc[-1]:.0%}", colors["open_dark"], 33)

    # Crossover: marker with the date, plus a short note with an arrow
    week = lasting_crossover(open_)
    if week is not None:
        wx = mdates.date2num(week)
        bubble(ax, frame, wx, 0.5, text["crossover_bubble"].format(date=week.strftime("%b %-d")),
               colors["accent"], 36)
        note = textwrap.fill(text["crossover_note"].format(date=week.strftime("%b %-d")), 34)
        ax.text(0.03, 0.95, "→", transform=ax.transAxes, ha="left", va="top",
                color=colors["accent"], fontproperties=frame.font("bold", sizes["annotation"]),
                zorder=5)
        ax.text(0.03 + 26 / ax.bbox.width, 0.95, note, transform=ax.transAxes, ha="left",
                va="top", color=colors["text"], linespacing=1.25, zorder=5,
                fontproperties=frame.font("regular", sizes["annotation"]))

    return frame
