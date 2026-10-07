"""Share over time: 100% stacked area of weekly token share (spec, "Chart design").

Phase 1 draws weights: open-weight on the bottom, closed-weight on top,
with a dashed 50% line. Stealth models are left out of the split.
"""

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from charts.frame import Frame, pt


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
    ax.tick_params(axis="x", length=0, pad=10)


def callout(ax, frame, xy, text, offset, ha):
    """Annotation with a thin leader line. It sits on the closed band, so it uses
    the ink color that reads on that band."""
    ink = frame.colors["closed_pill"][1]
    ax.annotate(text, xy, xytext=offset, textcoords="offset points", ha=ha, va="bottom",
                color=ink, linespacing=1.2,
                fontproperties=frame.font("bold", frame.sizes["callout"]),
                arrowprops={"arrowstyle": "-", "color": ink, "lw": 1.2,
                            "shrinkA": 4, "shrinkB": 8})


def render(weekly, footer_text, style, size):
    text = style["text"]["weights_share"]
    colors = style["colors"]
    sizes = style["text_sizes"]
    shares = weekly_shares(weekly, "weights", ["open", "closed"])
    x, open_, closed = shares.index, shares["open"], shares["closed"]
    last_week_end = x[-1] + pd.Timedelta(days=6)

    frame = Frame(style, size)
    frame.kicker(text["kicker"])
    frame.hero(text["hero"].format(share=round(open_.iloc[-1] * 100)), text["headline"])
    frame.subtitle(text["subtitle"].format(first=x[0].strftime("%b %Y"),
                                           last=last_week_end.strftime("%b %Y")))
    frame.footer(footer_text)
    ax = frame.chart_area(left_px=0, right_px=style["layout"]["end_label_space"], below_px=70)

    xn = mdates.date2num(x)
    ax.fill_between(xn, open_, 1, color=colors["closed"], linewidth=0)
    # Open band: vertical gradient, clipped to the area under the open line
    shape = ax.fill_between(xn, 0, open_, color="none", linewidth=0)
    ramp = LinearSegmentedColormap.from_list("open", colors["open_gradient"])
    image = ax.imshow(np.linspace(0, 1, 256).reshape(-1, 1), cmap=ramp, origin="lower",
                      extent=[xn[0], xn[-1], 0, 1], aspect="auto", zorder=1)
    image.set_clip_path(shape.get_paths()[0], transform=ax.transData)
    ax.plot(xn, open_, color=colors["background"], linewidth=2.5, zorder=2)
    ink = colors["closed_pill"][1]  # reads on the closed band
    ax.axhline(0.5, color=ink, linewidth=1.2, linestyle=(0, (5, 4)), alpha=0.8, zorder=3)
    ax.text(xn[0], 0.5, " 50%", va="bottom", ha="left", color=ink, zorder=3,
            fontproperties=frame.font("semibold", sizes["axis"]))

    ax.set_xlim(xn[0], xn[-1])
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    month_ticks(ax, x[0], x[-1], frame)

    # End labels: latest share of each band in a pill at its right edge
    edge = ax.get_yaxis_transform()
    for name, mid, value, (fill, ink) in [
            (text["open"], open_.iloc[-1] / 2, open_.iloc[-1], colors["open_pill"]),
            (text["closed"], open_.iloc[-1] + closed.iloc[-1] / 2, closed.iloc[-1],
             colors["closed_pill"])]:
        ax.text(1.05, mid, f"{value:.0%}\n{name.upper()}", transform=edge, va="center",
                ha="left", color=ink, linespacing=1.0, multialignment="left",
                fontproperties=frame.font("hero", sizes["end_label"]),
                bbox={"boxstyle": "round,pad=0.5,rounding_size=0.6", "facecolor": fill,
                      "edgecolor": "none"})

    # Crossover: magenta dot where open passed 50% for good, with a callout
    week = lasting_crossover(open_)
    if week is not None:
        week = mdates.date2num(week)
        ax.plot([week], [0.5], "o", markersize=pt(18), color=colors["accent"],
                markeredgecolor=colors["background"], markeredgewidth=2.5, zorder=5)
        callout(ax, frame, (week, 0.5),
                text["crossover"].format(date=mdates.num2date(week).strftime("%b %-d")),
                (-30, 70), "right")

    # Peak: the highest open share in the window
    peak_week = open_.idxmax()
    if peak_week != x[-1]:
        peak_week = mdates.date2num(peak_week)
        ax.plot([peak_week], [open_.max()], "o", markersize=pt(10), color=ink,
                zorder=5)
        callout(ax, frame, (peak_week, open_.max()),
                text["peak"].format(share=round(open_.max() * 100)), (0, 34), "center")

    return frame
