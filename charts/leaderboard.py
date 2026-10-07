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


def headline(table, text):
    top = table.iloc[0]
    if top["value"] == STEALTH:
        named = table[table["value"] != STEALTH].iloc[0]
        return text["headline_stealth_top"].format(company=named["value"],
                                                   share=f"{named['share'] * 100:.1f}")
    return text["headline"].format(company=top["value"], share=f"{top['share'] * 100:.1f}")


def change_text(points):
    if pd.isna(points):
        return "new"
    if round(points, 1) == 0:
        return "no change"
    return f"{'▲' if points > 0 else '▼'} {abs(points):.1f} pts"


def render(weekly, footer_text, style, size):
    text = style["text"]["company_leaderboard"]
    colors = style["colors"]
    sizes = style["text_sizes"]
    latest, table = latest_and_before(weekly, "company")
    rows = table.head(style["layout"]["leaderboard_rows"])
    week_start = pd.Timestamp(latest)
    week_end = week_start + pd.Timedelta(days=6)

    frame = Frame(style, size)
    frame.headline(headline(table, text))
    frame.subtitle(text["subtitle"].format(
        week=f"{week_start.strftime('%b %-d')} to {week_end.strftime('%b %-d, %Y')}"))
    frame.footer(footer_text)
    ax = frame.chart_area(left_px=250, right_px=150, below_px=16)

    y = range(len(rows))
    bar_colors = [colors["bar_muted"] if v == STEALTH else colors["bar"] for v in rows["value"]]
    ax.barh(list(y), rows["share"], color=bar_colors, height=0.66)
    ax.set_ylim(len(rows) - 0.5, -0.5)  # largest at the top
    ax.set_xlim(0, rows["share"].max() * 1.22)
    ax.set_xticks([])
    ax.set_yticks(list(y), rows["value"])
    for label in ax.get_yticklabels():
        label.set_fontproperties(frame.font("regular", sizes["bar_label"]))
        label.set_color(colors["text"])
    ax.tick_params(axis="y", length=0, pad=12)

    edge = ax.get_yaxis_transform()
    for i, row in rows.iterrows():
        ax.text(row["share"], i, f"  {row['share']:.1%}", va="center", ha="left",
                color=colors["text"], fontproperties=frame.font("bold", sizes["bar_label"]))
        ax.text(1.0 + 150 / ax.bbox.width, i, change_text((row["share"] - row["before"]) * 100),
                transform=edge, va="center", ha="right", color=colors["text_muted"],
                fontproperties=frame.font("regular", sizes["axis"]))

    ax.text(1.0 + 150 / ax.bbox.width, -0.75, text["change_header"], transform=edge,
            va="bottom", ha="right", color=colors["text_muted"],
            fontproperties=frame.font("regular", sizes["footer"]))
    return frame
