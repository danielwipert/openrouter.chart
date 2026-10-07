"""Pipeline steps 1-2: download OpenRouter data and save it to raw/YYYY-MM-DD/.

Saves four things, exactly as the API returned them:
  rankings_daily_01.json  daily token use per model (more parts if the window is split)
  models.json             the model catalog
  task_classifications.json  last 7 days of task types
  app_rankings.json       top apps for the last complete week
"""

import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_URL = "https://openrouter.ai/api/v1"
DATASET_START = date(2025, 1, 1)  # earliest day the API has
WINDOW_WEEKS = 52
MAX_SPAN_DAYS = 366  # the API refuses longer windows
RETRIES = 3
RETRY_WAIT_SECONDS = 10
RAW_DIR = Path("raw")


class FetchError(Exception):
    """A problem that stops the run, with a plain-English message."""


def last_complete_week(today):
    """Monday and Sunday of the most recent full week that ended before today (UTC)."""
    yesterday = today - timedelta(days=1)
    sunday = yesterday - timedelta(days=(yesterday.weekday() - 6) % 7)
    return sunday - timedelta(days=6), sunday


def fetch_window(today):
    """First and last day to download: 52 full weeks, through yesterday."""
    _, last_sunday = last_complete_week(today)
    start = last_sunday - timedelta(days=WINDOW_WEEKS * 7 - 1)
    return max(start, DATASET_START), today - timedelta(days=1)


def date_chunks(start, end, max_days=MAX_SPAN_DAYS):
    """Split start..end (inclusive) into pieces of at most max_days."""
    chunks = []
    while start <= end:
        chunk_end = min(start + timedelta(days=max_days - 1), end)
        chunks.append((start, chunk_end))
        start = chunk_end + timedelta(days=1)
    return chunks


def get(session, path, params=None):
    """GET one endpoint, retrying up to 3 times on errors or 429s. Returns the response."""
    url = BASE_URL + path
    for attempt in range(RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=60)
        except requests.RequestException as error:
            problem = f"could not connect ({error})"
        else:
            if response.status_code == 200:
                return response
            if response.status_code in (401, 403):
                raise FetchError(
                    "OpenRouter rejected the API key. Check the OPENROUTER_API_KEY secret."
                )
            problem = f"status {response.status_code}: {response.text[:200]}"
            if response.status_code != 429 and response.status_code < 500:
                raise FetchError(f"{path} failed with {problem}")
        if attempt < RETRIES:
            print(f"  {path} {problem}. Retrying in {RETRY_WAIT_SECONDS} seconds...")
            time.sleep(RETRY_WAIT_SECONDS)
    raise FetchError(f"{path} still failing after {RETRIES} retries: {problem}")


def save(folder, name, response):
    folder.mkdir(parents=True, exist_ok=True)  # only once there is something to save
    (folder / name).write_text(response.text, encoding="utf-8")
    print(f"  saved {folder / name}")
    return response.json()


def fetch_all(api_key, today, raw_dir=RAW_DIR, session=None):
    """Download everything for one run. Returns a short summary dict."""
    session = session or requests.Session()
    session.headers["Authorization"] = f"Bearer {api_key}"
    folder = raw_dir / today.isoformat()

    start, end = fetch_window(today)
    rows, metas = [], []
    for i, (chunk_start, chunk_end) in enumerate(date_chunks(start, end), start=1):
        params = {"start_date": chunk_start.isoformat(), "end_date": chunk_end.isoformat()}
        body = save(folder, f"rankings_daily_{i:02d}.json",
                    get(session, "/datasets/rankings-daily", params))
        rows += body["data"]
        metas.append(body["meta"])

    save(folder, "models.json", get(session, "/models"))
    save(folder, "task_classifications.json", get(session, "/classifications/task"))
    week_start, week_end = last_complete_week(today)
    save(folder, "app_rankings.json", get(session, "/datasets/app-rankings", {
        "start_date": week_start.isoformat(), "end_date": week_end.isoformat()}))

    days = sorted({row["date"] for row in rows})
    return {
        "folder": str(folder),
        "requested": f"{start} to {end}",
        "rows": len(rows),
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "days_with_data": len(days),
        "days_requested": (end - start).days + 1,
        "as_of": metas[-1]["as_of"] if metas else None,
    }


def write_summary(summary):
    """Print the summary, and show it on the GitHub Actions run page too."""
    lines = ["## Fetch summary", ""] + [f"- **{k}:** {v}" for k, v in summary.items()]
    print("\n".join(lines))
    page = os.environ.get("GITHUB_STEP_SUMMARY")
    if page:
        with open(page, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main():
    load_dotenv()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("OPENROUTER_API_KEY is not set. Add it as a GitHub secret (or to .env locally).")
    today = datetime.now(timezone.utc).date()
    print(f"Fetching OpenRouter data on {today} (UTC)")
    try:
        summary = fetch_all(api_key, today)
    except FetchError as error:
        sys.exit(f"Fetch stopped: {error}")
    write_summary(summary)
    (Path(summary["folder"]) / "fetch_summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
