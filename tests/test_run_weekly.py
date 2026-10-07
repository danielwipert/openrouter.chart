"""End to end: the whole pipeline on made-up raw data, run twice."""

import json
from datetime import date, timedelta

import pandas as pd

import run_weekly

FETCH_DAY = date(2026, 10, 14)


def make_raw(root):
    """52+ weeks of rankings for three models plus 'other', and a tiny catalog."""
    folder = root / "raw" / FETCH_DAY.isoformat()
    folder.mkdir(parents=True)
    start, end = date(2025, 10, 6), FETCH_DAY - timedelta(days=1)
    rows, day, i = [], start, 0
    while day <= end:
        rows += [
            {"date": day.isoformat(), "model_permaslug": "ds/v3", "total_tokens": str(100 + i)},
            {"date": day.isoformat(), "model_permaslug": "ds/v3:free", "total_tokens": "20"},
            {"date": day.isoformat(), "model_permaslug": "oa/gpt", "total_tokens": str(300 - i // 2)},
            {"date": day.isoformat(), "model_permaslug": "stealth/x", "total_tokens": "30"},
            {"date": day.isoformat(), "model_permaslug": "other", "total_tokens": "25"},
        ]
        day, i = day + timedelta(days=1), i + 1
    meta = {"as_of": f"{FETCH_DAY}T02:00:00.000Z", "version": "v1",
            "start_date": start.isoformat(), "end_date": end.isoformat()}
    (folder / "rankings_daily_01.json").write_text(json.dumps({"data": rows, "meta": meta}))
    (folder / "models.json").write_text(json.dumps({"data": [
        {"id": "ds/v3", "canonical_slug": "ds/v3", "hugging_face_id": "ds/V3"},
        {"id": "oa/gpt", "canonical_slug": "oa/gpt", "hugging_face_id": None}]}))
    return folder


def make_registry(root):
    reg = root / "registry"
    reg.mkdir()
    pd.DataFrame([
        {"prefix": "ds", "company": "DS Lab", "company_source": "manual: https://x",
         "country": "China", "country_source": "manual: https://x", "default_weights": "", "default_weights_source": ""},
        {"prefix": "oa", "company": "OA Lab", "company_source": "manual: https://x",
         "country": "United States", "country_source": "manual: https://x", "default_weights": "closed",
         "default_weights_source": "manual: https://x"},
        {"prefix": "stealth", "company": "Stealth (undisclosed)", "company_source": "manual: https://x",
         "country": "Undisclosed", "country_source": "manual: https://x", "default_weights": "stealth",
         "default_weights_source": "manual: https://x"},
    ]).to_csv(reg / "labs.csv", index=False)
    (reg / "families.csv").write_text("pattern,family\n^stealth/,Stealth (undisclosed)\n"
                                      "^ds/,DS\n^oa/,OA GPT\n")
    (reg / "models.csv").write_text(
        "model_id,company,company_source,weights,weights_source,first_seen\n")
    return reg


def test_same_raw_data_gives_identical_files(tmp_path):
    folder, reg = make_raw(tmp_path), make_registry(tmp_path)
    out_a, checks_a = run_weekly.run(folder, reg, tmp_path / "a")
    out_b, _ = run_weekly.run(folder, reg, tmp_path / "b")

    assert out_a.name == "2026-W41"  # Oct 5-11, the last complete week before Oct 14
    files = sorted(p.relative_to(out_a) for p in out_a.rglob("*") if p.is_file())
    assert [str(f) for f in files] == [
        "caption.md", "charts/company_leaderboard_portrait.png",
        "charts/company_leaderboard_square.png", "charts/weights_share_portrait.png",
        "charts/weights_share_square.png", "meta.json", "monthly.csv", "run_report.md",
        "weekly.csv"]
    for f in files:
        assert (out_a / f).read_bytes() == (out_b / f).read_bytes(), f

    report = (out_a / "run_report.md").read_text()
    assert report.startswith("# READY TO POST (2026-W41)")
    caption = (out_a / "caption.md").read_text()
    assert "on OpenRouter" in caption and "worldwide" not in caption
    assert (out_a / "weekly.csv").read_text().startswith("# Source: OpenRouter")
