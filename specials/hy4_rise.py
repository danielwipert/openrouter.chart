"""One-off LinkedIn chart: the rise of Tencent's Hy4 on OpenRouter.

Weekly tokens for Hy4 preview + Hy4 combined, as stacked bars, with each
week's rank among all models underneath. Same look as the weekly charts
(charts/frame.py and style.yaml).

Run from the repo root:  python specials/hy4_rise.py
"""

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import aggregate  # noqa: E402
import classify  # noqa: E402
from charts.frame import Frame, load_style  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

RAW = ROOT / "raw" / "2026-11-16"
OUT = ROOT / "specials" / "hy4_rise_square.png"
PREVIEW, FULL = "tencent/hy4-preview-20260827", "tencent/hy4-20261104"
FIRST_WEEK = pd.Timestamp("2026-08-24")


def weekly_table():
    classified, _, _ = classify.run(RAW, classify.REGISTRY_DIR)
    _, _, rows = aggregate.aggregate(classified, date.fromisoformat(RAW.name))
    rows["week"] = pd.to_datetime(rows["week"])
    rows = rows[rows["week"] >= FIRST_WEEK]
    per_model = rows.groupby(["week", "model_id"])["tokens"].sum().unstack(fill_value=0)
    named = per_model.drop(columns="other", errors="ignore")
    table = pd.DataFrame({
        "preview": per_model.get(PREVIEW, 0) / 1e12,
        "full": per_model.get(FULL, 0) / 1e12,
    })
    table["total"] = table["preview"] + table["full"]
    family = named[[PREVIEW, FULL]].sum(axis=1)
    table["share"] = family / per_model.sum(axis=1)
    # Rank of the combined Hy4 line against every other single model that week
    others = named.drop(columns=[PREVIEW, FULL])
    table["rank"] = [int((others.loc[w] > family.loc[w]).sum()) + 1 for w in table.index]
    return table


def main():
    style = load_style()
    c, sz = style["colors"], style["text_sizes"]
    t = weekly_table()
    n = len(t)
    x = np.arange(n)
    last = t.iloc[-1]
    settled = t.loc[pd.Timestamp("2026-10-26")]

    frame = Frame(style, "square")
    frame.title("Tencent's Hy4 doubled its OpenRouter traffic in two weeks")
    frame.subtitle("Weekly tokens for Hy4 preview and Hy4 combined, and rank among "
                   "all models, Aug 24 to Nov 15, 2026")
    key_y = frame.cursor
    frame.units("trillion tokens per week")
    frame.footer("Source: OpenRouter (openrouter.ai/rankings), as of Nov 16, 2026. Weeks start "
                 "Monday; the first week is partial (preview added Aug 27). Rank counts each "
                 "model version separately.")
    ax = frame.chart_area(left_px=40, below_px=150)

    # Key on the units line, left side
    kx = frame.margin["left"]
    for label, color in [("Hy4 preview (open weights)", c["open"]),
                         ("Hy4 (weights promised)", c["open_dark"])]:
        frame.fig.patches.append(Rectangle(
            (kx / frame.width, (key_y - 19) / frame.height), 16 / frame.width,
            16 / frame.height, transform=frame.fig.transFigure, facecolor=color,
            edgecolor="none"))
        txt = frame.text(kx + 24, key_y - 11, label, "regular", sz["units"], c["text"],
                         va="center")
        kx += 24 + frame.width_of(txt) + 28

    bw = 0.66
    ax.bar(x, t["preview"], bw, color=c["open"], edgecolor=c["background"], linewidth=2,
           zorder=3)
    ax.bar(x, t["full"], bw, bottom=t["preview"], color=c["open_dark"],
           edgecolor=c["background"], linewidth=2, zorder=3)

    ymax = 21
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(0, ymax)
    ax.set_yticks([0, 5, 10, 15, 20], ["0", "5", "10", "15", "20"])
    labels = [f"{w:%b}\n{w.day}" if (i == 0 or w.month != t.index[i - 1].month)
              else f"\n{w.day}" for i, w in enumerate(t.index)]
    ax.set_xticks(x, labels)
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontproperties(frame.font("regular", sz["axis"]))
        lab.set_color(c["text_muted"])
    ax.tick_params(length=0, pad=10)
    ax.grid(axis="y", color=c["grid"], linewidth=1, zorder=0)
    ax.set_axisbelow(True)

    # Rank row under the dates, with its own label; the top-2 weeks in bold
    ax.text(-0.6, -0.205 * ymax, "Rank among all models that week", ha="left",
            va="center", color=c["text_muted"], clip_on=False,
            fontproperties=frame.font("regular", sz["annotation"]))
    for xi, r in zip(x, t["rank"]):
        top = r <= 2
        ax.text(xi, -0.275 * ymax, f"#{r}", ha="center", va="center", clip_on=False,
                color=c["text"] if top else c["text_muted"],
                fontproperties=frame.font("bold" if top else "regular", sz["axis"]))

    def value(xi, total, weight="semibold"):
        ax.text(xi, total + 0.3, f"{total:.1f}", ha="center", va="bottom", color=c["text"],
                fontproperties=frame.font(weight, sz["bar_value"]), zorder=5)

    ann = frame.font("regular", sz["annotation"])
    ann_b = frame.font("semibold", sz["annotation"])
    lh = 1.05  # annotation line height in data units

    # Values on the bars the story is about
    peak_i = int(np.argmax(t["total"].iloc[:-3]))
    settled_i = list(t.index).index(pd.Timestamp("2026-10-26"))
    value(peak_i, t["total"].iloc[peak_i])
    value(settled_i, settled["total"])
    value(n - 1, last["total"], "bold")

    # Preview launch, beside the first peak
    tx, ty = peak_i + 0.55, 19.4
    ax.text(tx, ty, "Aug 27: open-weight preview", ha="left", va="center", color=c["text"],
            fontproperties=ann_b)
    ax.text(tx, ty - lh, "hits #1 on OpenRouter", ha="left", va="center",
            color=c["text_muted"], fontproperties=ann)
    ax.text(tx, ty - 2 * lh, "within a week", ha="left", va="center",
            color=c["text_muted"], fontproperties=ann)
    # Settles
    ax.text(6.6, 9.7, "then settles near 9T a week", ha="center", va="center",
            color=c["text_muted"], fontproperties=ann)
    # Full release, left of its bar
    tx, ty = n - 2.42, 14.4
    ax.text(tx, ty, "Nov 4: full Hy4", ha="right", va="center", color=c["accent"],
            fontproperties=ann_b)
    ax.text(tx, ty - lh, "adds vision and computer use,", ha="right", va="center",
            color=c["text_muted"], fontproperties=ann)
    ax.text(tx, ty - 2 * lh, "at a 50% launch discount", ha="right", va="center",
            color=c["text_muted"], fontproperties=ann)
    # Latest week: new high, to the left of its bar
    left = n - 1 - bw / 2 - 0.12
    ax.text(left, last["total"] + 0.55, "New high,", ha="right", va="center",
            color=c["text"], fontproperties=ann_b, zorder=5)
    ax.text(left, last["total"] - 0.5, f"{last['share'] * 100:.1f}% of all tokens",
            ha="right", va="center", color=c["text_muted"], fontproperties=ann, zorder=5)

    print(t.round(2).to_string())
    print("saved", frame.save(OUT))


if __name__ == "__main__":
    main()
