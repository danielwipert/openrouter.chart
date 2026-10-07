"""Draw the charts from the latest raw data: python -m charts

Writes to output/{week}/charts/, where {week} is the last complete data week.
Build step 7 replaces this with run_weekly.py.
"""

from datetime import date
from pathlib import Path

import aggregate
import checks
import classify
from charts import render_all


def main():
    folder = classify.latest_raw_folder()
    classified, _, _ = classify.run(folder)
    weekly, _, _ = aggregate.aggregate(classified, date.fromisoformat(folder.name))
    week_label = weekly.loc[weekly["period"] == weekly["period"].max(), "label"].iloc[0]
    out_dir = Path("output") / week_label / "charts"
    as_of = checks.load_metas(folder)[-1]["as_of"]
    for path in render_all(weekly, as_of, out_dir):
        print(f"  saved {path}")


if __name__ == "__main__":
    main()
