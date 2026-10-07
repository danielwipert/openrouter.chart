"""Pipeline step 5 (files): CSVs, captions, run report and meta.json for one week.

Nothing here depends on when the run happens, so rerunning on the same raw
data gives byte-identical files (spec accuracy rule: same input, same output).
"""

import json
from pathlib import Path

import pandas as pd

import checks
import classify
from charts import leaderboard, share

CAPTIONS_DIR = Path(__file__).resolve().parent / "captions"
LICENSE_LINE = ("# Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. "
                "Licensed under CC BY 4.0.\n")
CSV_COLUMNS = ["period", "label", "partial", "dimension", "value", "tokens",
               "share", "share_of_all"]


# --- CSVs ----------------------------------------------------------------------

def write_csv(table, path, as_of):
    out = table[CSV_COLUMNS].copy()
    for column in ("share", "share_of_all"):
        out[column] = out[column].round(6)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(LICENSE_LINE.format(as_of=as_of))
        out.to_csv(f, index=False, lineterminator="\n")


# --- Captions ------------------------------------------------------------------

def points(change):
    if pd.isna(change):
        return "new"
    if round(change, 1) == 0:
        return "unchanged"
    return f"{'up' if change > 0 else 'down'} {abs(change):.1f} points"


def join_names(names):
    names = list(names)
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def weights_caption(weekly, df, as_of_text):
    open_ = share.weekly_shares(weekly, "weights", ["open", "closed"])["open"]
    latest = weekly["period"].max()
    crossover = share.lasting_crossover(open_)
    stealth = weekly[(weekly["dimension"] == "weights") & (weekly["period"] == latest)
                     & (weekly["value"] == "stealth")]["share_of_all"].sum()
    latest_rows = df[(df["week"] == latest) & (df["weights"] == "open")]
    top_open = latest_rows.groupby("company")["tokens"].sum()
    top_open = top_open.reset_index().sort_values(["tokens", "company"],
                                                  ascending=[False, True])["company"].head(3)
    first, last = open_.index[0], open_.index[-1] + pd.Timedelta(days=6)
    template = (CAPTIONS_DIR / "weights_share.md").read_text(encoding="utf-8")
    return template.format(
        share=round(open_.iloc[-1] * 100),
        change=points((open_.iloc[-1] - open_.iloc[-2]) * 100) if len(open_) > 1 else "new",
        crossover_line=(f"Open-weight models passed 50% in the week of "
                        f"{crossover.strftime('%b %-d')} and have stayed above it since."
                        if crossover is not None else
                        "Open-weight models are not above 50% right now."),
        peak=round(open_.max() * 100),
        top_open=join_names(top_open),
        stealth=round(stealth * 100),
        first=first.strftime("%b %Y"), last=last.strftime("%b %Y"), as_of=as_of_text)


def company_caption(weekly, as_of_text):
    latest, table = leaderboard.latest_and_before(weekly, "company")
    top, stealth_on_top = leaderboard.leader(table)
    named = table[table["value"] != leaderboard.STEALTH].head(5).reset_index(drop=True)
    top5 = "\n".join(f"{i + 1}. {row['value']}: {row['share']:.1%} "
                     f"({points((row['share'] - row['before']) * 100)})"
                     for i, row in named.iterrows())
    stealth = table[table["value"] == leaderboard.STEALTH]
    stealth_line = (f"Stealth models (maker not yet revealed) took {stealth['share'].iloc[0]:.1%}"
                    + (", more than any named lab." if stealth_on_top else ".")
                    if len(stealth) else "")
    week_start = pd.Timestamp(latest)
    week = (f"{week_start.strftime('%b %-d')} to "
            f"{(week_start + pd.Timedelta(days=6)).strftime('%b %-d, %Y')}")
    template = (CAPTIONS_DIR / "company_leaderboard.md").read_text(encoding="utf-8")
    return template.format(leader=top["value"], leader_share=f"{top['share'] * 100:.1f}",
                           leader_change=points((top["share"] - top["before"]) * 100),
                           week=week, top5=top5, stealth_line=stealth_line, as_of=as_of_text)


def write_captions(weekly, df, as_of_text, path):
    parts = ["# Draft captions", "",
             "Templates are in captions/. Edit the wording before posting.", "",
             "## weights_share", "", weights_caption(weekly, df, as_of_text).strip(), "",
             "## company_leaderboard", "", company_caption(weekly, as_of_text).strip(), ""]
    path.write_text("\n".join(parts), encoding="utf-8")


# --- Run report ------------------------------------------------------------------

def new_models(models, week_start, week_end):
    """Models whose first day in the data falls in the latest week."""
    seen = models[(models["first_seen"] >= week_start) & (models["first_seen"] <= week_end)]
    return seen.sort_values("model_id")


def write_report(check_list, models, weekly, chart_paths, path):
    latest = weekly["period"].max()
    label = weekly.loc[weekly["period"] == latest, "label"].iloc[0]
    week_end = (pd.Timestamp(latest) + pd.Timedelta(days=6)).strftime("%Y-%m-%d")
    lines = checks.summary_lines(check_list)
    lines[0] = lines[0] + f" ({label})"
    lines += ["", "## New models this week", ""]
    fresh = new_models(models, latest, week_end)
    lines += ([f"- {r['model_id']}: {r['company'] or 'no company'}, "
               f"{r['weights'] or 'no weights'} ({r['weights_source'] or 'no source'})"
               for r in fresh.to_dict("records")] or ["- None"])
    lines += ["", "## Blank registry fields", ""]
    blanks = models[(models[classify.REQUIRED] == "").any(axis=1)]
    lines += ([f"- {r['model_id']}: " + ", ".join(c for c in classify.REQUIRED if not r[c])
               for r in blanks.to_dict("records")] or ["- None"])
    low = models[models["weights_source"].str.contains("low confidence")]
    lines += ["", "## Low-confidence labels to re-check monthly", ""]
    lines += [f"- {m}" for m in low["model_id"]] or ["- None"]
    lines += ["", "## Charts", ""] + [f"- charts/{p.name}" for p in chart_paths]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- meta.json -------------------------------------------------------------------

def write_meta(folder, metas, weekly, path):
    latest = weekly["period"].max()
    meta = {
        "data_week": weekly.loc[weekly["period"] == latest, "label"].iloc[0],
        "window": {"start": weekly["period"].min(),
                   "end": (pd.Timestamp(latest) + pd.Timedelta(days=6)).strftime("%Y-%m-%d")},
        "api_meta": metas,
        "raw_files": sorted(str(p) for p in folder.glob("*.json")),
    }
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def write_all(out_dir, folder, weekly, monthly, df, models, check_list, chart_paths,
              as_of, as_of_text):
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(weekly, out_dir / "weekly.csv", as_of)
    write_csv(monthly, out_dir / "monthly.csv", as_of)
    write_captions(weekly, df, as_of_text, out_dir / "caption.md")
    write_report(check_list, models, weekly, chart_paths, out_dir / "run_report.md")
    write_meta(folder, checks.load_metas(folder), weekly, out_dir / "meta.json")
