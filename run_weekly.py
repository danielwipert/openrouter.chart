"""The one weekly command: python run_weekly.py

Runs every step in order and writes output/{data week}/:
  1-2. fetch     download today's data into raw/YYYY-MM-DD/ (skip with --no-fetch)
  3.   classify  label every model; new models are added to registry/models.csv
       checks    hard checks stop the run here with a plain-English message
  4.   aggregate weekly and monthly totals and shares
       checks    soft checks decide READY / NOT READY TO POST
  5.   render    charts, CSVs, captions, run report, meta.json

--no-fetch reuses the newest raw/ folder, so a rerun on the same data gives
identical files.
"""

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

import aggregate
import checks
import classify
import charts
import fetch
import write_outputs

OUTPUT_DIR = Path("output")


def run(folder, registry_dir=classify.REGISTRY_DIR, output_dir=OUTPUT_DIR, style=None):
    """Steps 3-5 for one raw folder. Returns (output folder, checks)."""
    fetch_day = date.fromisoformat(folder.name)
    classified, models, _ = classify.run(folder, registry_dir)
    checks.hard_checks(folder, classified, fetch_day)

    weekly, monthly, df = aggregate.aggregate(classified, fetch_day)
    check_list = checks.soft_checks(folder, classified, models, weekly, fetch_day)

    label = weekly.loc[weekly["period"] == weekly["period"].max(), "label"].iloc[0]
    out_dir = output_dir / label
    as_of = checks.load_metas(folder)[-1]["as_of"]
    as_of_text = datetime.fromisoformat(as_of.replace("Z", "+00:00")).strftime("%b %-d, %Y")
    chart_paths = charts.render_all(weekly, as_of, out_dir / "charts", style)
    write_outputs.write_all(out_dir, folder, weekly, monthly, df, models, check_list,
                            chart_paths, as_of, as_of_text)
    return out_dir, check_list


def main():
    parser = argparse.ArgumentParser(description="Weekly OpenRouter usage breakdown")
    parser.add_argument("--no-fetch", action="store_true",
                        help="reuse the newest raw/ folder instead of downloading")
    args = parser.parse_args()

    if not args.no_fetch:
        fetch.main()
    try:
        out_dir, check_list = run(classify.latest_raw_folder())
    except checks.HardCheckFailed as error:
        sys.exit(f"Run stopped: {error}")

    report = (out_dir / "run_report.md").read_text(encoding="utf-8")
    print(f"Wrote {out_dir}/")
    print(report)
    page = os.environ.get("GITHUB_STEP_SUMMARY")
    if page:
        with open(page, "a", encoding="utf-8") as f:
            f.write(report)


if __name__ == "__main__":
    main()
