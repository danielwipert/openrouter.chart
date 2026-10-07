import json
from datetime import date

import pandas as pd
import pytest

import aggregate
import checks
import classify
import fetch

FETCH_DAY = date(2026, 10, 14)  # a Wednesday; window is Oct 13 2025 - Oct 11 2026
START, END = aggregate.data_window(FETCH_DAY)
DAYS = pd.date_range(START, END).strftime("%Y-%m-%d")


def make_classified(open_tokens=60, closed_tokens=40, unknown_model=False):
    rows = []
    for day in DAYS:
        rows.append({"date": day, "slug": "ds/v3", "model_id": "ds/v3", "tokens": open_tokens,
                     "is_free": False, "weights": "open", "company": "DeepSeek"})
        rows.append({"date": day, "slug": "oa/gpt", "model_id": "oa/gpt", "tokens": closed_tokens,
                     "is_free": False, "weights": "closed", "company": "OpenAI"})
        rows.append({"date": day, "slug": "other", "model_id": "other", "tokens": 10,
                     "is_free": False, "weights": "other", "company": "other"})
    if unknown_model:
        rows.append({"date": DAYS[-1], "slug": "new/model", "model_id": "new/model", "tokens": 5,
                     "is_free": False, "weights": "unknown", "company": "unknown"})
    return pd.DataFrame(rows)


def weekly_of(classified):
    return aggregate.aggregate(classified, FETCH_DAY)[0]


# --- Hard checks -------------------------------------------------------------

def test_wrong_key_stops_the_run_with_a_clear_message(monkeypatch, tmp_path):
    def rejected(*args, **kwargs):
        raise fetch.FetchError("OpenRouter rejected the API key. Check the OPENROUTER_API_KEY secret.")
    monkeypatch.setenv("OPENROUTER_API_KEY", "wrong")
    monkeypatch.setattr(fetch, "fetch_all", rejected)
    with pytest.raises(SystemExit) as stopped:
        fetch.main()
    assert "rejected the API key" in str(stopped.value)


def test_missing_key_stops_the_run(monkeypatch):
    monkeypatch.setattr(fetch, "load_dotenv", lambda: None)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(SystemExit) as stopped:
        fetch.main()
    assert "OPENROUTER_API_KEY is not set" in str(stopped.value)


def test_stale_data_stops_the_run():
    checks.check_fresh([{"end_date": "2026-10-13"}], FETCH_DAY)  # 1 day old: fine
    with pytest.raises(checks.HardCheckFailed, match="stale"):
        checks.check_fresh([{"end_date": "2026-10-10"}], FETCH_DAY)


def test_missing_day_stops_the_run():
    classified = make_classified()
    checks.check_no_missing_days(classified, START, END)
    gap = classified[classified["date"] != "2026-06-01"]
    with pytest.raises(checks.HardCheckFailed, match="2026-06-01"):
        checks.check_no_missing_days(gap, START, END)


# --- READY / NOT READY ----------------------------------------------------------

def test_clean_data_is_ready():
    classified = make_classified()
    models = pd.DataFrame([{"model_id": "ds/v3", "company": "DeepSeek", "company_source": "rule: x",
                            "weights": "open", "weights_source": "catalog: x"}])
    result = [checks.check_labels(classified), checks.check_sources(models)]
    assert checks.is_ready(result)


def test_blank_label_sets_not_ready():
    result = [checks.check_labels(make_classified(unknown_model=True))]
    assert not checks.is_ready(result)
    assert "new/model" in result[0].detail
    assert checks.summary_lines(result)[0] == "# NOT READY TO POST"


def test_blank_source_sets_not_ready():
    models = pd.DataFrame([{"model_id": "ds/v3", "company": "DeepSeek", "company_source": "",
                            "weights": "open", "weights_source": "catalog: x"}])
    result = [checks.check_sources(models)]
    assert not checks.is_ready(result)
    assert "ds/v3 (company)" in result[0].detail


def test_warnings_do_not_block_ready():
    result = [checks.Check("Coverage", "warning", False, "low")]
    assert checks.is_ready(result)
    assert "**WARN** Coverage" in "\n".join(checks.summary_lines(result))


# --- Soft warnings ----------------------------------------------------------------

def test_coverage_warns_under_80_percent():
    weekly = weekly_of(make_classified(open_tokens=5, closed_tokens=5))  # 10 of 20 tokens labeled
    assert not checks.check_coverage(weekly).passed
    assert checks.check_coverage(weekly_of(make_classified())).passed


def test_big_jump_warns_over_10_points():
    classified = make_classified()
    last_week = classified["date"] >= "2026-10-05"
    classified.loc[last_week & (classified["slug"] == "ds/v3"), "tokens"] = 300  # 60% -> 88%
    jump = checks.check_big_jump(weekly_of(classified))
    assert not jump.passed and "+28.2 points" in jump.detail
    assert checks.check_big_jump(weekly_of(make_classified())).passed


def test_history_restated_warns_when_a_past_week_moves():
    before = weekly_of(make_classified())
    changed = make_classified()
    changed.loc[(changed["date"] == "2026-03-02") & (changed["slug"] == "ds/v3"), "tokens"] = 200
    result = checks.check_history(weekly_of(changed), before)
    assert not result.passed and "2026-W10" in result.detail
    assert checks.check_history(before, before).passed
    assert checks.check_history(before, None).passed
