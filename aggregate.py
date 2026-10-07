"""Pipeline step 4: weekly and monthly token totals and shares per dimension.

Output is one table with a row per period + dimension + value:
  period       week start (Monday) or first day of the month, as YYYY-MM-DD
  label        2026-W41 or 2026-10
  partial      True if the window doesn't cover the whole week or month
  dimension    weights, company, ...
  value        open, closed, DeepSeek, ... plus 'other' (outside the daily top 50)
  tokens       total tokens
  share        value tokens / labeled tokens, the number the charts show.
               Blank for 'other', 'unknown' and excluded values (e.g. stealth on
               the weights chart), which are not part of the split.
  share_of_all value tokens / all tokens, including 'other' (used for footers)
"""

import os
from datetime import date, timedelta

import pandas as pd

import classify
import fetch

DIMENSIONS = ["weights", "company", "country", "family",  # live dimensions
              "price_tier", "reasoning", "input_type", "free", "size"]
# Values counted in a dimension's tokens but left out of its share split
EXCLUDED_FROM_SHARE = {"weights": {"stealth"}, "price_tier": {"Undisclosed"},
                       "reasoning": {"Undisclosed"}, "input_type": {"Undisclosed"},
                       "size": {"n/a"}}  # size splits open-weight tokens only
NOT_LABELED = {classify.OTHER, classify.UNKNOWN}


def data_window(fetch_day):
    """First and last day to aggregate: the 52 full weeks before the fetch day."""
    _, last_sunday = fetch.last_complete_week(fetch_day)
    start, _ = fetch.fetch_window(fetch_day)
    return start, last_sunday


def add_periods(classified, start, end):
    """Keep rows inside the window and add week and month columns."""
    df = classified.copy()
    days = pd.to_datetime(df["date"])
    keep = (days >= pd.Timestamp(start)) & (days <= pd.Timestamp(end))
    df, days = df[keep].copy(), days[keep]
    monday = days - pd.to_timedelta(days.dt.weekday, unit="D")
    df["week"] = monday.dt.strftime("%Y-%m-%d")
    df["month"] = days.dt.strftime("%Y-%m-01")
    return df


def period_info(kind, period, start, end):
    """Label and partial flag for one week or month."""
    first = date.fromisoformat(period)
    if kind == "week":
        year, week, _ = first.isocalendar()
        last = first + timedelta(days=6)
        label = f"{year}-W{week:02d}"
    else:
        next_month = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
        last = next_month - timedelta(days=1)
        label = first.strftime("%Y-%m")
    return label, first < start or last > end


def totals(df, kind, start, end, dimensions=DIMENSIONS):
    """Token totals and shares per period (kind = 'week' or 'month') and dimension value."""
    tables = []
    for dimension in dimensions:
        t = (df.groupby([kind, dimension])["tokens"].sum().reset_index()
               .rename(columns={kind: "period", dimension: "value"}))
        t.insert(1, "dimension", dimension)
        all_tokens = t.groupby("period")["tokens"].transform("sum")
        in_split = ~t["value"].isin(NOT_LABELED | EXCLUDED_FROM_SHARE.get(dimension, set()))
        split_tokens = t["tokens"].where(in_split, 0).groupby(t["period"]).transform("sum")
        t["share"] = (t["tokens"] / split_tokens).where(in_split)
        t["share_of_all"] = t["tokens"] / all_tokens
        tables.append(t)
    out = pd.concat(tables, ignore_index=True)
    info = out["period"].map(lambda p: period_info(kind, p, start, end))
    out.insert(1, "label", info.str[0])
    out.insert(2, "partial", info.str[1])
    return out.sort_values(["dimension", "period", "tokens", "value"],
                           ascending=[True, True, False, True], ignore_index=True)


def top_models(df, week, n=5):
    """The week's top n models by tokens (variants such as :free count with their base)."""
    named = df[(df["week"] == week) & (df["model_id"] != classify.OTHER)]
    sums = named.groupby("model_id")["tokens"].sum().reset_index()
    sums = sums.sort_values(["tokens", "model_id"], ascending=[False, True])  # ties: by name
    return sums.head(n).set_index("model_id")["tokens"]


def aggregate(classified, fetch_day):
    """Weekly and monthly tables, plus the rows inside the window (for top models)."""
    start, end = data_window(fetch_day)
    df = add_periods(classified, start, end)
    return totals(df, "week", start, end), totals(df, "month", start, end), df


def sanity_summary(weekly, df):
    """Plain-text lines for the step 4 check."""
    weights = weekly[(weekly["dimension"] == "weights") & (weekly["value"] == "open")]
    open_share = weights.set_index("period")["share"]
    lines = ["## Aggregate summary", ""]
    mid_march = open_share.loc["2026-03-09":"2026-03-22"]
    if len(mid_march):
        lines.append(f"- **Open share, mid-March 2026:** "
                     + ", ".join(f"{p}: {s:.1%}" for p, s in mid_march.items()))
    over_half = open_share[open_share > 0.5]
    lasting = [p for p in over_half.index if (open_share.loc[p:] > 0.5).all()]
    if lasting:
        lines.append(f"- **Open share above 50% every week since:** {lasting[0]}")
    latest = weekly["period"].max()
    lines.append(f"- **Latest week:** {latest}, open share {open_share.get(latest, float('nan')):.1%}")
    other = weekly[(weekly["dimension"] == "weights") & (weekly["period"] == latest)
                   & (weekly["value"] == classify.OTHER)]["share_of_all"].sum()
    lines.append(f"- **Top-50 coverage, latest week:** {1 - other:.1%}")
    lines.append("- **Top 5 models, latest week:**")
    for model_id, tokens in top_models(df, latest).items():
        lines.append(f"  - {model_id}: {tokens / 1e9:,.0f}B tokens")
    return lines


def main():
    folder = classify.latest_raw_folder()
    classified, _, _ = classify.run(folder)
    weekly, monthly, df = aggregate(classified, date.fromisoformat(folder.name))
    print(f"Weekly rows: {len(weekly)}, monthly rows: {len(monthly)}")
    lines = sanity_summary(weekly, df)
    print("\n".join(lines))
    page = os.environ.get("GITHUB_STEP_SUMMARY")
    if page:
        with open(page, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
