"""Task mix: share of classified tokens by task for the last 7 days, as ranked bars
colored by task group (spec, "Content library", phase 3).

The data is OpenRouter's sampled task classification (/classifications/task),
saved weekly in raw/. Shares are of classified tokens only. The change column
appears once a snapshot from about four weeks earlier exists.
"""

import json
from datetime import date

import pandas as pd
from matplotlib.patches import Rectangle

from charts.frame import Frame
from charts.leaderboard import change_text

SHOWN = 10
TASK_FILE = "task_classifications.json"


def load_snapshot(folder):
    data = json.loads((folder / TASK_FILE).read_text(encoding="utf-8"))["data"]
    tasks = pd.DataFrame([{"tag": c["tag"], "name": c["display_name"],
                           "group": c["macro_category"], "share": c["token_share"]}
                          for c in data["classifications"]])
    groups = {m["key"]: (m["label"], m["token_share"]) for m in data["macro_categories"]}
    return data["as_of"], tasks, groups


def snapshot_four_weeks_before(folder):
    """The saved snapshot closest to 28 days before this one (21-35 days back), or None."""
    day = date.fromisoformat(folder.name)
    best = None
    for other in folder.parent.iterdir():
        if not (other / TASK_FILE).exists():
            continue
        gap = (day - date.fromisoformat(other.name)).days
        if 21 <= gap <= 35 and (best is None or abs(gap - 28) < abs(best[0] - 28)):
            best = (gap, other)
    return best[1] if best else None


def snapshot_count(raw_dir):
    return sum(1 for p in raw_dir.iterdir() if (p / TASK_FILE).exists())


def available(data):
    return (data["folder"] / TASK_FILE).exists()


def title(data, spec):
    _, tasks, _ = load_snapshot(data["folder"])
    top = tasks.sort_values(["share", "tag"], ascending=[False, True]).iloc[0]
    return spec["title"].format(name=top["name"], share=round(top["share"] * 100))


def render(data, footer_text, style, size, spec):
    colors = style["colors"]
    sizes = style["text_sizes"]
    folder = data["folder"]
    as_of, tasks, groups = load_snapshot(folder)
    rows = tasks.sort_values(["share", "tag"], ascending=[False, True]).head(SHOWN)
    rows = rows.reset_index(drop=True)
    earlier = snapshot_four_weeks_before(folder)
    before = load_snapshot(earlier)[1].set_index("tag")["share"] if earlier else None

    group_order = [g for g in spec["groups"] if g in groups]
    group_color = {g: colors["categorical"][i] for i, g in enumerate(group_order)}

    frame = Frame(style, size)
    frame.title(title(data, spec))
    frame.subtitle(spec["subtitle"].format(as_of=date.fromisoformat(as_of).strftime("%b %-d, %Y")))
    frame.footer(footer_text)

    # Key: one swatch per task group with its share of classified tokens
    x = frame.margin["left"]
    key_y = frame.cursor - 8
    for g in group_order:
        label, share = groups[g]
        frame.fig.add_artist(Rectangle((x / frame.width, (key_y - 8) / frame.height),
                                       16 / frame.width, 16 / frame.height,
                                       transform=frame.fig.transFigure,
                                       facecolor=group_color[g], edgecolor="none"))
        t = frame.text(x + 24, key_y, f"{label} {share * 100:.0f}%", "regular",
                       sizes["axis"], colors["text"], va="center")
        x += 24 + frame.width_of(t) + 30
    frame.cursor -= 70
    ax = frame.chart_area(left_px=290, right_px=130 if before is not None else 40, below_px=0)

    n = len(rows)
    xmax = max(0.05, -(-(rows["share"].max() * 100 + 3) // 5) * 5 / 100)
    ax.set_xlim(0, xmax)
    ax.set_ylim(n - 0.4, -0.6)
    step = 0.05 if xmax <= 0.3 else 0.1
    ticks = [i * step for i in range(int(round(xmax / step)))]
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
    if before is not None:
        ax.text(right, 1.0 + 8 / ax.bbox.height, style["layout"]["change_header"],
                transform=ax.transAxes, ha="right", va="bottom", color=colors["text_muted"],
                fontproperties=frame.font("regular", sizes["axis"]))
    for i, row in rows.iterrows():
        ax.barh(i, row["share"], height=0.62, color=group_color.get(row["group"],
                colors["others_fill"]), linewidth=0, zorder=2)
        ax.text(-16 / ax.bbox.width, i, row["name"], transform=edge, ha="right", va="center",
                color=colors["text"], fontproperties=frame.font("regular", sizes["bar_label"]))
        ax.annotate(f"{row['share'] * 100:.1f}", (row["share"], i), xytext=(8, 0),
                    textcoords="offset points", ha="left", va="center", color=colors["text"],
                    fontproperties=frame.font("regular", sizes["bar_value"]))
        if before is not None:
            points = (row["share"] - before.get(row["tag"], float("nan"))) * 100
            ax.text(right, i, change_text(points), transform=edge, ha="right", va="center",
                    color=(colors["text_muted"] if pd.isna(points) or round(points, 1) == 0
                           else colors["up"] if points > 0 else colors["down"]),
                    fontproperties=frame.font("medium", sizes["bar_value"]))
    return frame
