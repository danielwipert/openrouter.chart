"""Hard checks, soft checks and the accuracy standard (spec, "Stability and quality checks").

Hard checks stop the run with a plain-English message (HardCheckFailed).
Every other check lets the run finish. Checks of kind "ready" decide
READY TO POST: if any of them fails, the run is NOT READY TO POST.
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import date

import pandas as pd

import aggregate
import classify

FRESH_DAYS = 2
MIN_COVERAGE = 0.80
BIG_JUMP = 0.10  # 10 points
RESTATED = 0.01  # 1 point
SOURCE_KINDS = ("catalog:", "rule:", "manual:")


class HardCheckFailed(Exception):
    """Stops the run. The message says what is wrong in plain English."""


@dataclass
class Check:
    name: str
    kind: str  # "ready" (failing sets NOT READY TO POST) or "warning"
    passed: bool
    detail: str


# --- Hard checks -------------------------------------------------------------

def load_metas(folder):
    return [json.loads(p.read_text(encoding="utf-8"))["meta"]
            for p in sorted(folder.glob("rankings_daily_*.json"))]


def check_fresh(metas, fetch_day):
    end = date.fromisoformat(metas[-1]["end_date"])
    if (fetch_day - end).days > FRESH_DAYS:
        raise HardCheckFailed(
            f"Data is stale: OpenRouter's latest day is {end}, more than {FRESH_DAYS} days "
            f"before {fetch_day}. Try again later; if it lasts, check openrouter.ai/rankings.")


def check_no_missing_days(rankings, start, end):
    have = set(rankings["date"])
    days = pd.date_range(start, end).strftime("%Y-%m-%d")
    missing = [d for d in days if d not in have]
    if missing:
        shown = ", ".join(missing[:5]) + (" ..." if len(missing) > 5 else "")
        raise HardCheckFailed(f"{len(missing)} day(s) have no data: {shown}")


def hard_checks(folder, rankings, fetch_day):
    """Raise HardCheckFailed if the raw data can't be trusted."""
    start, end = aggregate.data_window(fetch_day)
    check_fresh(load_metas(folder), fetch_day)
    check_no_missing_days(rankings, start, end)


# --- Soft checks -------------------------------------------------------------

def check_labels(classified):
    shares = classify.unknown_report(classified)
    bad = {dim: share for dim, share in shares.items() if share > 0}
    named = classified[classified["slug"] != classify.OTHER]
    models = sorted(set(named.loc[(named[classify.REQUIRED] == classify.UNKNOWN).any(axis=1),
                                  "model_id"]))
    detail = ("Zero unknown values on " + ", ".join(classify.REQUIRED) if not bad else
              "Unknown " + ", ".join(f"{d}: {s:.2%} of top-50 tokens" for d, s in bad.items())
              + ". Fill in registry/models.csv for: " + ", ".join(models))
    return Check("Labels complete", "ready", not bad, detail)


def check_sources(models):
    blank = [f"{row['model_id']} ({field})"
             for row in models.to_dict("records") for field in classify.REQUIRED
             if row[field] and not row[f"{field}_source"].startswith(SOURCE_KINDS)]
    detail = ("Every label has a source" if not blank else
              "Missing or invalid source in registry/models.csv: " + ", ".join(blank))
    return Check("Sources complete", "ready", not blank, detail)


def latest_coverage(weekly):
    latest = weekly["period"].max()
    rows = weekly[(weekly["dimension"] == "weights") & (weekly["period"] == latest)]
    unlabeled = rows[rows["value"].isin(aggregate.NOT_LABELED)]["share_of_all"].sum()
    return 1 - unlabeled


def check_coverage(weekly):
    coverage = latest_coverage(weekly)
    return Check("Coverage", "warning", coverage >= MIN_COVERAGE,
                 f"Labeled tokens are {coverage:.1%} of all tokens in the latest week "
                 f"(warn under {MIN_COVERAGE:.0%})")


def two_way_open_share(weekly):
    rows = weekly[(weekly["dimension"] == "weights") & (weekly["value"] == "open")]
    return rows.set_index("period")["share"].sort_index()


def check_big_jump(weekly):
    share = two_way_open_share(weekly)
    if len(share) < 2:
        return Check("Big jump", "warning", True, "Not enough weeks to compare")
    move = share.iloc[-1] - share.iloc[-2]
    return Check("Big jump", "warning", abs(move) <= BIG_JUMP,
                 f"Open share moved {move * 100:+.1f} points in the latest week "
                 f"(warn over {BIG_JUMP * 100:.0f})")


def check_history(weekly, previous_weekly):
    """Compare past weeks' shares with the previous run's figures for the same weeks."""
    if previous_weekly is None:
        return Check("History restated", "warning", True, "No previous run to compare with")
    keys = ["period", "dimension", "value"]
    both = weekly.merge(previous_weekly, on=keys, suffixes=("", "_before"))
    both = both[both["period"] < weekly["period"].max()].dropna(subset=["share", "share_before"])
    both["moved"] = (both["share"] - both["share_before"]).abs()
    moved = both[both["moved"] > RESTATED].sort_values("moved", ascending=False)
    if moved.empty:
        return Check("History restated", "warning", True,
                     f"No past week's share moved more than {RESTATED * 100:.0f} point")
    top = moved.iloc[0]
    return Check("History restated", "warning", False,
                 f"{len(moved)} past share(s) moved more than {RESTATED * 100:.0f} point since the "
                 f"previous run; largest: {top['dimension']} {top['value']} in week "
                 f"{top['label']}, {top['share_before']:.1%} -> {top['share']:.1%}")


def check_repeatable(classified, fetch_day, weekly):
    again, _, _ = aggregate.aggregate(classified, fetch_day)
    same = again.equals(weekly)
    return Check("Same input, same output", "ready", same,
                 "Re-aggregating the same data gave identical numbers" if same else
                 "Re-aggregating the same data gave different numbers")


# --- All together --------------------------------------------------------------

def previous_weekly(folder, models):
    """The previous run's weekly table, rebuilt from its raw folder with today's registry."""
    earlier = sorted(p for p in folder.parent.iterdir() if p.is_dir() and p.name < folder.name)
    if not earlier:
        return None
    prev = earlier[-1]
    classified = classify.classify(classify.load_rankings(prev), models)
    weekly, _, _ = aggregate.aggregate(classified, date.fromisoformat(prev.name))
    return weekly


def soft_checks(folder, classified, models, weekly, fetch_day):
    return [
        check_labels(classified),
        check_sources(models),
        check_repeatable(classified, fetch_day, weekly),
        Check("Long tail disclosed", "ready", True,
              f"Top-50 coverage for the footer: {latest_coverage(weekly):.1%}"),
        check_coverage(weekly),
        check_big_jump(weekly),
        check_history(weekly, previous_weekly(folder, models)),
    ]


def is_ready(checks):
    return all(c.passed for c in checks if c.kind == "ready")


def summary_lines(checks):
    status = "READY TO POST" if is_ready(checks) else "NOT READY TO POST"
    lines = [f"# {status}", ""]
    for c in checks:
        mark = "PASS" if c.passed else ("FAIL" if c.kind == "ready" else "WARN")
        lines.append(f"- **{mark}** {c.name}: {c.detail}")
    lines.append("- [ ] Dan: on the first Monday of the month, the top 5 match "
                 "openrouter.ai/rankings (token totals within 1%)")
    return lines


def main():
    folder = classify.latest_raw_folder()
    fetch_day = date.fromisoformat(folder.name)
    classified, models, _ = classify.run(folder)
    try:
        hard_checks(folder, classified, fetch_day)
    except HardCheckFailed as error:
        sys.exit(f"Run stopped: {error}")
    weekly, _, _ = aggregate.aggregate(classified, fetch_day)
    lines = summary_lines(soft_checks(folder, classified, models, weekly, fetch_day))
    print("\n".join(lines))
    page = os.environ.get("GITHUB_STEP_SUMMARY")
    if page:
        with open(page, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
