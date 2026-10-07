"""Leaderboard: ranked horizontal bars for the latest week, with the change vs
4 weeks earlier (spec, "Content library"). Draws company and country.
"""

import pandas as pd

from charts.frame import Frame


def latest_and_before(weekly, dimension, weeks_back=4):
    rows = weekly[(weekly["dimension"] == dimension) & weekly["share"].notna()]
    latest = rows["period"].max()
    before = (pd.Timestamp(latest) - pd.Timedelta(weeks=weeks_back)).strftime("%Y-%m-%d")
    now = rows[rows["period"] == latest].set_index("value")["share"]
    then = rows[rows["period"] == before].set_index("value")["share"]
    table = pd.DataFrame({"share": now, "before": then.reindex(now.index)})  # NaN = new
    table = table.reset_index().sort_values(["share", "value"], ascending=[False, True])
    return latest, table.reset_index(drop=True)


def leader(table, stealth_value):
    """The top named value, skipping stealth. Returns (row, stealth_is_on_top)."""
    named = table[table["value"] != stealth_value]
    return named.iloc[0], table.iloc[0]["value"] == stealth_value


def headline(table, spec):
    top, stealth_on_top = leader(table, spec["stealth_value"])
    name = spec.get("demonyms", {}).get(top["value"], top["value"])
    template = spec["title_stealth_top"] if stealth_on_top else spec["title"]
    return template.format(name=name, share=f"{top['share'] * 100:.1f}")


def title(weekly, monthly, spec):
    return headline(latest_and_before(weekly, spec["dimension"])[1], spec)


def change_text(points):
    if pd.isna(points):
        return "new"
    if round(points, 1) == 0:
        return "–"
    return f"{'+' if points > 0 else '−'}{abs(points):.1f}"


def render(weekly, monthly, footer_text, style, size, spec):
    colors = style["colors"]
    sizes = style["text_sizes"]
    latest, table = latest_and_before(weekly, spec["dimension"])
    rows = table.head(style["layout"]["leaderboard_rows"]).reset_index(drop=True)
    top, _ = leader(table, spec["stealth_value"])
    week_start = pd.Timestamp(latest)
    week_end = week_start + pd.Timedelta(days=6)

    frame = Frame(style, size)
    frame.title(headline(table, spec))
    frame.subtitle(spec["subtitle"].format(
        week=f"{week_start.strftime('%b %-d')} to {week_end.strftime('%b %-d, %Y')}"))
    frame.footer(footer_text)
    frame.cursor -= 44  # room for the axis numbers above the bars
    ax = frame.chart_area(left_px=300, right_px=130, below_px=0)

    n = len(rows)
    # Axis end: the next multiple of 5 points, leaving room for the value label
    xmax = max(0.05, -(-(rows["share"].max() * 100 + 3) // 5) * 5 / 100)
    ax.set_xlim(0, xmax)
    ax.set_ylim(n - 0.4, -0.6)  # rank 1 at the top

    # Top axis with light grey vertical gridlines
    step = 0.05 if xmax <= 0.3 else 0.1
    ticks = [i * step for i in range(int(round(xmax / step)))]  # last one left off: no clash
    ax.xaxis.tick_top()
    ax.set_xticks(ticks, [f"{t * 100:.0f}" for t in ticks])
    for label in ax.get_xticklabels():
        label.set_fontproperties(frame.font("regular", sizes["axis"]))
        label.set_color(colors["text_muted"])
    ax.tick_params(axis="x", length=0, pad=8)
    ax.grid(axis="x", color=colors["grid"], linewidth=1)
    ax.set_axisbelow(True)
    ax.set_yticks([])

    edge = ax.get_yaxis_transform()
    right = 1.0 + 130 / ax.bbox.width
    ax.text(right, 1.0 + 8 / ax.bbox.height, style["layout"]["change_header"],
            transform=ax.transAxes, ha="right", va="bottom", color=colors["text_muted"],
            fontproperties=frame.font("regular", sizes["axis"]))
    for i, row in rows.iterrows():
        is_top = row["value"] == top["value"]
        is_stealth = row["value"] == spec["stealth_value"]
        color = (colors["bar_muted"] if is_stealth else
                 colors["bar_lead"] if is_top else colors["bar"])
        ax.barh(i, row["share"], height=0.62, color=color, linewidth=0, zorder=2)
        name = spec["stealth_label"] if is_stealth else row["value"]
        ax.text(-16 / ax.bbox.width, i, name, transform=edge, ha="right", va="center",
                color=colors["text"],
                fontproperties=frame.font("semibold" if is_top else "regular",
                                          sizes["bar_label"]))
        ax.annotate(f"{row['share'] * 100:.1f}", (row["share"], i), xytext=(8, 0),
                    textcoords="offset points", ha="left", va="center", zorder=3,
                    color=colors["open_dark"] if is_top else colors["text"],
                    fontproperties=frame.font("semibold" if is_top else "regular",
                                              sizes["bar_value"]))
        points = (row["share"] - row["before"]) * 100
        ax.text(right, i, change_text(points), transform=edge, ha="right", va="center",
                color=(colors["text_muted"] if pd.isna(points) or round(points, 1) == 0 else
                       colors["up"] if points > 0 else colors["down"]),
                fontproperties=frame.font("medium", sizes["bar_value"]))
    return frame
