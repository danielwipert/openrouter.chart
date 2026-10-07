"""Rank changes: monthly rank by share of tokens for today's top names, as lines
(a bump chart; spec, "Content library"). Draws company and family.

Months the window cuts short are left out, so every point is a full month.
Ranks below 10 drop off the bottom, so a line starts when a name enters the top 10.
"""

import pandas as pd

from charts.frame import Frame

SHOWN_RANKS = 10
HIGHLIGHTED = 3  # the top three today get colors; the rest are grey


def monthly_ranks(monthly, dimension, stealth_value):
    rows = monthly[(monthly["dimension"] == dimension) & monthly["share"].notna()
                   & ~monthly["partial"] & (monthly["value"] != stealth_value)]
    rows = rows.sort_values(["period", "share", "value"], ascending=[True, False, True])
    rows = rows.assign(rank=rows.groupby("period").cumcount() + 1)
    return rows.pivot(index="period", columns="value", values="rank")


def headline_story(ranks, names, spec):
    """Pick the title's story and the name it is about.

    1. The biggest climber among names that start on the chart (visible story).
    2. Otherwise today's No. 1, if it started outside the top 10 (a newcomer).
    3. Otherwise today's No. 1 holding its place.
    """
    first, last = ranks.iloc[0], ranks.iloc[-1]
    visible = [n for n in names if pd.notna(first.get(n)) and first[n] <= SHOWN_RANKS]
    climbs = {n: first[n] - last[n] for n in visible if first[n] > last[n]}
    if climbs:
        name = max(climbs, key=lambda n: (climbs[n], -last[n]))
        return name, spec["title"].format(name=name, before=int(first[name]),
                                          after=int(last[name]))
    leader = names[0]
    if pd.isna(first.get(leader)) or first[leader] > SHOWN_RANKS:
        return leader, spec["title_newcomer"].format(name=leader, after=int(last[leader]))
    return leader, spec["title_steady"].format(name=leader)


def title(weekly, monthly, spec):
    ranks = monthly_ranks(monthly, spec["dimension"], spec["stealth_value"])
    names = list(ranks.iloc[-1].sort_values().index[:spec["top"]])
    return headline_story(ranks, names, spec)[1]


def render(weekly, monthly, footer_text, style, size, spec):
    colors = style["colors"]
    sizes = style["text_sizes"]
    ranks = monthly_ranks(monthly, spec["dimension"], spec["stealth_value"])
    names = list(ranks.iloc[-1].sort_values().index[:spec["top"]])
    months = pd.to_datetime(ranks.index)

    name, title = headline_story(ranks, names, spec)
    frame = Frame(style, size)
    frame.title(title)
    frame.subtitle(spec["subtitle"].format(first=months[0].strftime("%b %Y"),
                                           last=months[-1].strftime("%b %Y")))
    frame.footer(footer_text)
    frame.cursor -= 36  # room for the "Rank" label
    ax = frame.chart_area(left_px=56, right_px=230, below_px=66)

    xs = list(range(len(months)))
    ax.set_xlim(-0.3, len(months) - 0.7)
    ax.set_ylim(SHOWN_RANKS + 0.5, 0.5)
    ax.set_yticks(range(1, SHOWN_RANKS + 1), [f"{r}" for r in range(1, SHOWN_RANKS + 1)])
    ax.set_xticks(xs, [m.strftime("%b\n%Y") if (m.month == 1 or i == 0) else m.strftime("%b")
                       for i, m in enumerate(months)])
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(frame.font("regular", sizes["axis"]))
        label.set_color(colors["text_muted"])
    ax.tick_params(length=0, pad=10)
    ax.grid(axis="y", color=colors["grid"], linewidth=1)
    ax.set_axisbelow(True)
    ax.text(-0.3, 0.2, "Rank", ha="left", va="bottom", color=colors["text_muted"],
            fontproperties=frame.font("regular", sizes["axis"]))

    edge = ax.get_yaxis_transform()
    # Grey lines first, then the highlighted ones on top
    # The top three today, plus the title's climber, get colors
    colored = names[:HIGHLIGHTED] + ([name] if name not in names[:HIGHLIGHTED] else [])
    for idx, value in sorted(enumerate(names), key=lambda p: -p[0]):
        series = ranks[value].where(ranks[value] <= SHOWN_RANKS)
        lit = value in colored
        color = colors["categorical"][colored.index(value)] if lit else colors["line_muted"]
        width = 4.5 if lit else 2.5
        z = 5 if lit else 3
        ax.plot(xs, series, color=color, linewidth=width, zorder=z, solid_capstyle="round")
        ax.scatter(xs, series, s=110 if lit else 55, color=color, zorder=z + 1,
                   edgecolors=colors["background"], linewidths=1.5)
        rank_now = int(ranks[value].iloc[-1])
        ax.text(1.0 + 16 / ax.bbox.width, rank_now, value, transform=edge, ha="left",
                va="center", color=colors["text"],
                fontproperties=frame.font("semibold" if lit else "regular",
                                          sizes["bar_value"]))
    return frame
