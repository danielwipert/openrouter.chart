"""Share race: today's top six as a 100% stacked area, plus stealth and "all
others" (spec, "Content library"). Draws company and family.
"""

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from charts.frame import Frame
from charts.share import month_ticks

TOP_N = 6
OTHERS = "__others__"


def race_table(weekly, dimension, stealth_value):
    """Weekly shares for the top six (by the latest week), stealth and all others."""
    rows = weekly[(weekly["dimension"] == dimension) & weekly["share"].notna()]
    table = rows.pivot(index="period", columns="value", values="share").fillna(0)
    latest = table.iloc[-1].drop(stealth_value, errors="ignore")
    latest = latest.reset_index().sort_values(by=[latest.name, "value"],
                                               ascending=[False, True])
    top = list(latest["value"].head(TOP_N))
    out = table[top].copy()
    out[stealth_value] = table[stealth_value] if stealth_value in table else 0.0
    out[OTHERS] = (1 - out.sum(axis=1)).clip(lower=0)
    out.index = pd.to_datetime(out.index)
    return out.sort_index(), top


def biggest_gainer(table, top):
    """The top-six value whose share grew most: first 4 weeks vs last 4 weeks."""
    before, after = table[top].head(4).mean(), table[top].tail(4).mean()
    name = (after - before).idxmax()
    return name, before[name], after[name]


def spread_labels(wanted, gap, low=0.0, high=1.0):
    """Move label positions apart so neighbours are at least `gap` apart."""
    order = np.argsort(wanted)
    placed = np.array(wanted, dtype=float)[order]
    for i in range(1, len(placed)):
        placed[i] = max(placed[i], placed[i - 1] + gap)
    overflow = placed[-1] - high
    if overflow > 0:
        placed -= overflow
        for i in range(len(placed) - 2, -1, -1):
            placed[i] = min(placed[i], placed[i + 1] - gap)
    placed = np.maximum(placed, low)
    out = np.empty_like(placed)
    out[order] = placed
    return out


def title(weekly, monthly, spec):
    table, top = race_table(weekly, spec["dimension"], spec["stealth_value"])
    name, before, after = biggest_gainer(table, top)
    if after > before and before < 0.005:
        return spec["title_from_zero"].format(name=name, after=round(after * 100))
    if after > before:
        return spec["title"].format(name=name, before=round(before * 100),
                                    after=round(after * 100))
    return spec["title_flat"].format(name=top[0], after=round(table[top[0]].iloc[-1] * 100))


def render(weekly, monthly, footer_text, style, size, spec):
    colors = style["colors"]
    sizes = style["text_sizes"]
    stealth = spec["stealth_value"]
    table, top = race_table(weekly, spec["dimension"], stealth)
    x = table.index
    xn = mdates.date2num(x)
    last_week_end = x[-1] + pd.Timedelta(days=6)

    title_text = title(weekly, monthly, spec)

    frame = Frame(style, size)
    frame.title(title_text)
    frame.subtitle(spec["subtitle"].format(first=x[0].strftime("%b %Y"),
                                           last=last_week_end.strftime("%b %Y")))
    frame.units(style["layout"]["units"])
    frame.footer(footer_text)
    ax = frame.chart_area(left_px=44, right_px=250, below_px=66)
    ax.set_xlim(xn[0], xn[-1])
    ax.set_ylim(0, 1)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1], ["0", "25", "50", "75", "100"])
    for label in ax.get_yticklabels():
        label.set_fontproperties(frame.font("regular", sizes["axis"]))
        label.set_color(colors["text_muted"])
    ax.tick_params(axis="y", length=0, pad=10)
    month_ticks(ax, x[0], x[-1], frame)

    names = top + [stealth, OTHERS]
    fills = colors["categorical"][:len(top)] + [colors["stealth_fill"], colors["others_fill"]]
    labels = top + [spec["stealth_label"], spec["others_label"]]
    bottom = np.zeros(len(x))
    mids = []
    for value, fill in zip(names, fills):
        top_edge = bottom + table[value].to_numpy()
        ax.fill_between(xn, bottom, top_edge, color=fill, linewidth=0, zorder=1)
        ax.plot(xn, top_edge, color=colors["background"], linewidth=1.5, zorder=2)
        mids.append((bottom[-1] + top_edge[-1]) / 2)
        bottom = top_edge

    # Labels at the right edge: color swatch, name and latest share
    gap = sizes["bar_value"] * 1.35 / ax.bbox.height
    placed = spread_labels(mids, gap)
    for value, fill, label, mid, y in zip(names, fills, labels, mids, placed):
        share = table[value].iloc[-1]
        x0 = 1.0 + 14 / ax.bbox.width
        if abs(y - mid) > 0.005:  # thin leader line when a label had to move
            ax.plot([1.0, x0], [mid, y], transform=ax.transAxes, color=colors["text_muted"],
                    linewidth=0.8, clip_on=False)
        sw = 14 / ax.bbox.width
        ax.add_patch(Rectangle((x0, y - 7 / ax.bbox.height), sw, 14 / ax.bbox.height,
                               transform=ax.transAxes, facecolor=fill, edgecolor="none",
                               clip_on=False))
        ax.text(x0 + sw + 8 / ax.bbox.width, y, f"{label}  {share * 100:.0f}",
                transform=ax.transAxes, ha="left", va="center", color=colors["text"],
                fontproperties=frame.font("semibold" if value in top[:1] else "regular",
                                          sizes["bar_value"]))
    return frame
