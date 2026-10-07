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
        label.set_fontproperties(frame.font("regular", frame.style["text_sizes"]["axis"]))
        label.set_color(frame.colors["text_muted"])
    ax.tick_params(axis="x", length=0, pad=8)


def render(weekly, footer_text, style, size):
    text = style["text"]["weights_share"]
    colors = style["colors"]
    sizes = style["text_sizes"]
    shares = weekly_shares(weekly, "weights", ["open", "closed"])
    x, open_, closed = shares.index, shares["open"], shares["closed"]
    last_week_end = x[-1] + pd.Timedelta(days=6)

    frame = Frame(style, size)
    frame.headline(text["headline"].format(share=round(open_.iloc[-1] * 100)))
    frame.subtitle(text["subtitle"].format(first=x[0].strftime("%b %Y"),
                                           last=last_week_end.strftime("%b %Y")))
    frame.footer(footer_text)
    ax = frame.chart_area(left_px=56, right_px=style["layout"]["end_label_space"], below_px=76)

    ax.stackplot(x, open_, closed, colors=[colors["open"], colors["closed"]], linewidth=0)
    ax.plot(x, open_, color=colors["background"], linewidth=2)  # 2px gap between bands
    for y in (0.25, 0.75):
        ax.axhline(y, color=colors["background"], linewidth=1, alpha=0.6)
    ax.axhline(0.5, color=colors["reference_line"], linewidth=1.5, linestyle=(0, (6, 4)))

    ax.set_xlim(x[0], x[-1])
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1], ["0%", "25%", "50%", "75%", "100%"])
    for label in ax.get_yticklabels():
        label.set_fontproperties(frame.font("regular", sizes["axis"]))
        label.set_color(colors["text_muted"])
    ax.tick_params(axis="y", length=0, pad=10)
    month_ticks(ax, x[0], x[-1], frame)

    # End labels: latest share of each band at its right edge, in the band's color
    edge = ax.get_yaxis_transform()
    for name, mid, value, color in [
            (text["open"], open_.iloc[-1] / 2, open_.iloc[-1], colors["open_label"]),
            (text["closed"], open_.iloc[-1] + closed.iloc[-1] / 2, closed.iloc[-1],
             colors["closed_label"])]:
        ax.text(1.03, mid, f"{value:.0%}\n{name}", transform=edge, va="center", ha="left",
                color=color, fontproperties=frame.font("bold", sizes["end_label"]),
                linespacing=1.1)

    # Crossover marker: dot and short label where open-weight passed 50% for good
    week = lasting_crossover(open_)
    if week is not None:
        ax.plot([week], [0.5], "o", markersize=pt(14), color=colors["accent"],
                markeredgecolor=colors["background"], markeredgewidth=2, zorder=5)
        # Label sits inside the open band, just below and right of the dot
        ax.annotate(text["crossover"].format(date=week.strftime("%b %-d")), (week, 0.5),
                    xytext=(10, -14), textcoords="offset points", ha="left", va="top",
                    color=colors["background"],
                    fontproperties=frame.font("semibold", sizes["marker"]))

    return frame
