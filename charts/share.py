"""Share over time: 100% stacked area of weekly token share (spec, "Chart design").

Phase 1 draws weights: open-weight on the bottom, closed-weight on top,
with a dashed 50% line. Stealth models are left out of the split.
"""

import pandas as pd

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
    ax.set_xticks(months, labels)
    for label in ax.get_xticklabels():
        label.set_fontproperties(frame.font("regular", frame.sizes["axis"]))
        label.set_color(frame.colors["text_muted"])
    ax.tick_params(axis="x", length=0, pad=10)


def callout(ax, frame, xy, text, offset, ha):
    """Annotation with a thin leader line, in the text color."""
    ax.annotate(text, xy, xytext=offset, textcoords="offset points", ha=ha, va="bottom",
                color=frame.colors["text"], linespacing=1.2,
                fontproperties=frame.font("semibold", frame.sizes["callout"]),
                arrowprops={"arrowstyle": "-", "color": frame.colors["text"], "lw": 1,
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

    ax.stackplot(x, open_, closed, colors=[colors["open"], colors["closed"]], linewidth=0)
    ax.plot(x, open_, color=colors["background"], linewidth=2.5)  # gap between bands
    ax.axhline(0.5, color=colors["reference_line"], linewidth=1.2, linestyle=(0, (5, 4)),
               alpha=0.8)
    ax.text(x[0], 0.5, " 50%", va="bottom", ha="left", color=colors["text"],
            fontproperties=frame.font("semibold", sizes["axis"]))

    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    month_ticks(ax, x[0], x[-1], frame)

    # End labels: latest share of each band at its right edge
    edge = ax.get_yaxis_transform()
    for name, mid, value, color in [
            (text["open"], open_.iloc[-1] / 2, open_.iloc[-1], colors["open_label"]),
            (text["closed"], open_.iloc[-1] + closed.iloc[-1] / 2, closed.iloc[-1],
             colors["closed_label"])]:
        ax.text(1.04, mid + 0.02, f"{value:.0%}", transform=edge, va="bottom", ha="left",
                color=color, fontproperties=frame.font("hero", sizes["end_label"] * 1.4))
        ax.text(1.04, mid, name.upper(), transform=edge, va="top", ha="left", color=color,
                fontproperties=frame.font("bold", sizes["kicker"]))

    # Crossover: magenta dot where open passed 50% for good, with a callout
    week = lasting_crossover(open_)
    if week is not None:
        ax.plot([week], [0.5], "o", markersize=pt(18), color=colors["accent"],
                markeredgecolor=colors["background"], markeredgewidth=2.5, zorder=5)
        callout(ax, frame, (week, 0.5),
                text["crossover"].format(date=week.strftime("%b %-d")), (-30, 70), "right")

    # Peak: the highest open share in the window
    peak_week = open_.idxmax()
    if peak_week != x[-1]:
        ax.plot([peak_week], [open_.max()], "o", markersize=pt(10), color=colors["text"],
                zorder=5)
        callout(ax, frame, (peak_week, open_.max()),
                text["peak"].format(share=round(open_.max() * 100)), (0, 34), "center")

    return frame
