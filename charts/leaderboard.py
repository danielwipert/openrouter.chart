"""Leaderboard: ranked horizontal bars for the latest week, with the change vs
4 weeks earlier (spec, "Content library"). Phase 1 draws company.
"""

import pandas as pd

from charts.frame import Frame

STEALTH = "Stealth (undisclosed)"


def latest_and_before(weekly, dimension, weeks_back=4):
    rows = weekly[(weekly["dimension"] == dimension) & weekly["share"].notna()]
    latest = rows["period"].max()
    before = (pd.Timestamp(latest) - pd.Timedelta(weeks=weeks_back)).strftime("%Y-%m-%d")
    now = rows[rows["period"] == latest].set_index("value")["share"]
    then = rows[rows["period"] == before].set_index("value")["share"]
    table = pd.DataFrame({"share": now, "before": then.reindex(now.index)})  # NaN = new
    table = table.reset_index().sort_values(["share", "value"], ascending=[False, True])
    return latest, table.reset_index(drop=True)


def leader(table):
    """The top company, skipping stealth. Returns (row, stealth_is_on_top)."""
    named = table[table["value"] != STEALTH]
    return named.iloc[0], table.iloc[0]["value"] == STEALTH


def headline(table, text):
    top, stealth_on_top = leader(table)
    template = text["headline_stealth_top"] if stealth_on_top else text["headline"]
    return template.format(company=top["value"])


def change_text(points):
    if pd.isna(points):
        return "NEW"
    if round(points, 1) == 0:
        return "–"
    return f"{'▲' if points > 0 else '▼'} {abs(points):.1f}"


def render(weekly, footer_text, style, size):
    text = style["text"]["company_leaderboard"]
    colors = style["colors"]
    sizes = style["text_sizes"]
    latest, table = latest_and_before(weekly, "company")
    rows = table.head(style["layout"]["leaderboard_rows"]).reset_index(drop=True)
    top, _ = leader(table)
    week_start = pd.Timestamp(latest)
    week_end = week_start + pd.Timedelta(days=6)

    frame = Frame(style, size)
    frame.kicker(text["kicker"])
    frame.hero(text["hero"].format(share=f"{top['share'] * 100:.1f}"), headline(table, text))
    frame.subtitle(text["subtitle"].format(
        week=f"{week_start.strftime('%b %-d')} to {week_end.strftime('%b %-d, %Y')}"))
    frame.footer(footer_text)
    ax = frame.chart_area(left_px=56, right_px=110, below_px=0)

    n = len(rows)
    ax.set_xlim(0, rows["share"].max() * 1.18)
    ax.set_ylim(n - 0.35, -0.75)  # rank 1 at the top
    ax.set_xticks([])
    ax.set_yticks([])
    edge = ax.get_yaxis_transform()
    right = 1.0 + 110 / ax.bbox.width

    ax.text(right, -0.75, text["change_header"], transform=edge, ha="right", va="bottom",
            color=colors["text_muted"], fontproperties=frame.font("bold", sizes["footer"]))
    for i, row in rows.iterrows():
        is_top = row["value"] == top["value"]
        is_stealth = row["value"] == STEALTH
        color = (colors["bar_muted"] if is_stealth else
                 colors["bar_lead"] if is_top else colors["bar"])
        ax.barh(i + 0.12, row["share"], height=0.42, color=color, linewidth=0)
        # Rank number, name above the bar, value at its end, change at the right
        ax.text(-56 / ax.bbox.width, i + 0.12, f"{i + 1:02d}", transform=edge, ha="left",
                va="center", color=colors["text_muted"],
                fontproperties=frame.font("hero", sizes["rank"]))
        name = row["value"] + (f"  ·  {text['stealth_note']}" if is_stealth else "")
        ax.text(0, i - 0.16, name, ha="left", va="bottom", color=colors["text"],
                fontproperties=frame.font("bold" if is_top else "semibold",
                                          sizes["bar_label"]))
        ax.text(row["share"], i + 0.12, f"  {row['share']:.1%}", ha="left", va="center",
                color=colors["text"], fontproperties=frame.font("hero", sizes["bar_value"]))
        ax.text(right, i + 0.12, change_text((row["share"] - row["before"]) * 100),
                transform=edge, ha="right", va="center", color=colors["text_muted"],
                fontproperties=frame.font("semibold", sizes["axis"]))
    return frame
