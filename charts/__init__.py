"""Pipeline step 5 (charts): build every live chart at both LinkedIn sizes.

Files are named {dimension}_{chart}_{size}.png and never change week to week.
"""

from datetime import datetime

from charts import leaderboard, share
from charts.frame import load_style

CHARTS = {  # file name prefix -> (chart module, adds the stealth note to the footer)
    "weights_share": (share, True),
    "company_leaderboard": (leaderboard, False),
}
SIZES = ["square", "portrait"]


def latest_rows(weekly, dimension="weights"):
    latest = weekly["period"].max()
    rows = weekly[(weekly["dimension"] == dimension) & (weekly["period"] == latest)]
    return rows.set_index("value")["share_of_all"]


def footer_text(weekly, as_of, style, stealth_note):
    share_of_all = latest_rows(weekly)
    coverage = 1 - share_of_all.get("other", 0) - share_of_all.get("unknown", 0)
    as_of_text = datetime.fromisoformat(as_of.replace("Z", "+00:00")).strftime("%b %-d, %Y")
    text = style["text"]["footer_source"].format(as_of=as_of_text,
                                                 coverage=f"{coverage * 100:.0f}")
    if stealth_note:
        stealth = share_of_all.get("stealth", 0)
        text += " " + style["text"]["footer_stealth"].format(stealth=f"{stealth * 100:.0f}")
    return text


def render_all(weekly, as_of, out_dir, style=None):
    """Draw every chart at every size into out_dir. Returns the file paths."""
    style = style or load_style()
    paths = []
    for name, (module, stealth_note) in CHARTS.items():
        footer = footer_text(weekly, as_of, style, stealth_note)
        for size in SIZES:
            frame = module.render(weekly, footer, style, size)
            paths.append(frame.save(out_dir / f"{name}_{size}.png"))
    return paths
