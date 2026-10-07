"""Launch curve: each new model's share of tokens by weeks since it was added to
OpenRouter, all aligned at week 0 (spec, "Content library", phase 3).

"New" means added inside the window. The five biggest launches (by peak share
in their first WEEKS_SHOWN weeks) are drawn, each in its own color.
"""

import json
import re

import numpy as np
import pandas as pd

from matplotlib.patches import Rectangle

from charts.frame import Frame
from charts.race import spread_labels

WEEKS_SHOWN = 16
SHOWN = 5


def display_names(folder):
    """Catalog names without the 'Company: ' prefix, keyed by canonical slug."""
    path = folder / "models.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))["data"]
    return {m["canonical_slug"]: m["name"].split(": ", 1)[-1].replace(" (free)", "")
            for m in data if m.get("name")}


def short_name(model_id, names):
    """Catalog name if the model is still listed, else a tidied slug
    ('x-ai/grok-4.1-fast' -> 'Grok 4.1 Fast')."""
    if model_id in names:
        return names[model_id].replace(" (batch)", "")
    slug = re.sub(r"-(20\d{6}|\d{4}-\d{2}-\d{2})$", "", model_id.split("/", 1)[-1])
    return " ".join(w[:1].upper() + w[1:] for w in slug.split("-"))


def launch_table(rows, models):
    """Share of all tokens for each model added inside the window, by weeks since launch."""
    weekly_total = rows.groupby("week")["tokens"].sum()
    named = rows[rows["model_id"] != "other"]
    per_model = named.groupby(["model_id", "week"])["tokens"].sum().reset_index()
    per_model["share"] = per_model["tokens"] / per_model["week"].map(weekly_total)
    release = models.set_index("model_id")["release_date"]
    first_week = pd.Timestamp(rows["week"].min())
    out = {}
    for model_id, group in per_model.groupby("model_id"):
        day = pd.Timestamp(release.get(model_id, "")) if release.get(model_id) else None
        if day is None or day < first_week:
            continue  # launched before the window: no clean week 0
        launch_week = day - pd.Timedelta(days=day.weekday())
        weeks = ((pd.to_datetime(group["week"]) - launch_week).dt.days // 7).to_numpy()
        series = pd.Series(group["share"].to_numpy(), index=weeks)
        series = series[(series.index >= 0) & (series.index < WEEKS_SHOWN)]
        if len(series):
            out[model_id] = series.reindex(range(int(series.index.max()) + 1), fill_value=0.0)
    return out


def available(data):
    return bool(launch_table(data["rows"], data["models"]))


def biggest_launches(table):
    peaks = {m: s.max() for m, s in table.items()}
    return sorted(peaks, key=lambda m: (-peaks[m], m))[:SHOWN]


def title(data, spec):
    table = launch_table(data["rows"], data["models"])
    names = display_names(data["folder"])
    top = biggest_launches(table)[0]
    series = table[top]
    weeks = int(series.idxmax())
    when = ("in its first week" if weeks == 0 else
            "one week after launch" if weeks == 1 else f"{weeks} weeks after launch")
    return spec["title"].format(name=short_name(top, names), peak=round(series.max() * 100),
                                when=when)


def render(data, footer_text, style, size, spec):
    colors = style["colors"]
    sizes = style["text_sizes"]
    table = launch_table(data["rows"], data["models"])
    names = display_names(data["folder"])
    shown = biggest_launches(table)

    frame = Frame(style, size)
    frame.title(title(data, spec))
    frame.subtitle(spec["subtitle"].format(n=len(shown), weeks=WEEKS_SHOWN))
    frame.units(style["layout"]["units"])
    frame.footer(footer_text)
    ax = frame.chart_area(left_px=44, right_px=270, below_px=70)

    top_share = max(table[m].max() for m in shown)
    ymax = max(0.05, np.ceil(top_share * 100 / 5) * 5 / 100)
    ax.set_xlim(0, WEEKS_SHOWN - 1)
    ax.set_ylim(0, ymax)
    step = 0.05 if ymax <= 0.3 else 0.1
    yticks = np.arange(0, ymax + 1e-9, step)
    ax.set_yticks(yticks, [f"{t * 100:.0f}" for t in yticks])
    ax.set_xticks(range(0, WEEKS_SHOWN, 2))
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontproperties(frame.font("regular", sizes["axis"]))
        label.set_color(colors["text_muted"])
    ax.tick_params(length=0, pad=10)
    ax.grid(axis="y", color=colors["grid"], linewidth=1)
    ax.set_axisbelow(True)
    ax.set_xlabel(spec["x_label"], color=colors["text_muted"], labelpad=12,
                  fontproperties=frame.font("regular", sizes["axis"]))

    ends = []
    for idx, model_id in enumerate(shown):
        series = table[model_id]
        color = colors["categorical"][idx]
        ax.plot(series.index, series.values, color=color, linewidth=3.5, zorder=5 - idx * 0.1,
                solid_capstyle="round")
        peak_week = int(series.idxmax())
        ax.scatter([peak_week], [series.max()], s=70, color=color, zorder=6,
                   edgecolors=colors["background"], linewidths=1.5)
        ends.append((series.values[-1], color, short_name(model_id, names), series.max()))

    # Key at the right: swatch, name and peak share, in order of each line's end
    gap = sizes["bar_value"] * 2.5 / ax.bbox.height * ymax
    placed = spread_labels([e[0] for e in ends], gap, 0, ymax)
    x0 = 1.0 + 16 / ax.bbox.width
    sw = 14 / ax.bbox.width
    for (_, color, label, peak), y in zip(ends, placed):
        y_ax = y / ymax
        ax.add_patch(Rectangle((x0, y_ax - 7 / ax.bbox.height), sw, 14 / ax.bbox.height,
                               transform=ax.transAxes, facecolor=color, edgecolor="none",
                               clip_on=False))
        ax.text(x0 + sw + 8 / ax.bbox.width, y_ax, f"{label}\npeak {peak * 100:.0f}%",
                transform=ax.transAxes, ha="left", va="center", color=colors["text"],
                linespacing=1.1, fontproperties=frame.font("regular", sizes["bar_value"]))
    return frame
