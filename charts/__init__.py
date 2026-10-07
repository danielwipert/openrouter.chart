"""Pipeline step 5 (charts): build every chart in style.yaml at both LinkedIn sizes.

Files are named {chart}_{size}.png (e.g. weights_share_square.png) and never
change week to week.
"""

from datetime import datetime

from charts import launch, leaderboard, race, ranks, share, tasks
from charts.frame import load_style

KINDS = {"share": share, "leaderboard": leaderboard, "race": race, "ranks": ranks,
         "launch": launch, "tasks": tasks}
SIZES = ["square", "portrait"]


def latest_rows(weekly, dimension="weights"):
    latest = weekly["period"].max()
    rows = weekly[(weekly["dimension"] == dimension) & (weekly["period"] == latest)]
    return rows.set_index("value")["share_of_all"]


def footer_text(weekly, as_of, style, stealth_note, extra_note=""):
    share_of_all = latest_rows(weekly)
    coverage = 1 - share_of_all.get("other", 0) - share_of_all.get("unknown", 0)
    as_of_text = datetime.fromisoformat(as_of.replace("Z", "+00:00")).strftime("%b %-d, %Y")
    text = style["text"]["footer_source"].format(as_of=as_of_text,
                                                 coverage=f"{coverage * 100:.0f}")
    if stealth_note:
        stealth = share_of_all.get("stealth", 0)
        text += " " + style["text"]["footer_stealth"].format(stealth=f"{stealth * 100:.0f}")
    if extra_note:
        text = extra_note + " " + text
    return text


def has_data(module, data, spec):
    """False when a chart has nothing to draw this week (it is then skipped)."""
    if "dimension" in spec and spec["kind"] in ("share", "leaderboard", "race"):
        rows = data["weekly"]
        if not (rows["dimension"].eq(spec["dimension"]) & rows["share"].notna()).any():
            return False
    return getattr(module, "available", lambda d: True)(data)


def render_all(data, as_of, out_dir, style=None):
    """Draw every chart at every size into out_dir. Returns the file paths.

    data holds weekly, monthly, rows (per-model rows in the window), models
    (the registry) and folder (the raw folder), as each chart needs."""
    style = style or load_style()
    weekly = data["weekly"]
    paths = []
    for name, spec in style["charts"].items():
        module = KINDS[spec["kind"]]
        if not has_data(module, data, spec):
            continue  # no data for this chart this week; the run report lists it
        footer = footer_text(weekly, as_of, style, spec.get("stealth_note", False),
                             spec.get("extra_note", ""))
        for size in SIZES:
            frame = module.render(data, footer, style, size, spec)
            paths.append(frame.save(out_dir / f"{name}_{size}.png"))
    return paths
