import pandas as pd

import charts
from charts import leaderboard, share


def weekly_table():
    """26 weeks: open share climbs from 30% to 70%, with a brief blip over 50% in week 5."""
    rows = []
    for i, monday in enumerate(pd.date_range("2026-04-06", periods=26, freq="W-MON")):
        open_share = 0.55 if i == 5 else 0.3 + 0.4 * i / 25
        period = monday.strftime("%Y-%m-%d")
        for value, share_, of_all in [("open", open_share, open_share * 0.8),
                                      ("closed", 1 - open_share, (1 - open_share) * 0.8),
                                      ("stealth", None, 0.15), ("other", None, 0.05)]:
            rows.append({"period": period, "label": f"W{i}", "partial": False,
                         "dimension": "weights", "value": value, "tokens": 1,
                         "share": share_, "share_of_all": of_all})
        for value, share_ in [("Stealth (undisclosed)", 0.4), ("DeepSeek", 0.35 if i < 25 else 0.3),
                              ("OpenAI", 0.25 if i < 25 else 0.3)]:
            rows.append({"period": period, "label": f"W{i}", "partial": False,
                         "dimension": "company", "value": value, "tokens": 1,
                         "share": share_, "share_of_all": share_ * 0.95})
    return pd.DataFrame(rows)


def test_crossover_is_where_the_share_stays_above_half():
    weekly = weekly_table()
    open_ = share.weekly_shares(weekly, "weights", ["open", "closed"])["open"]
    # the week-5 blip doesn't count; the share stays above 50% from week 13
    assert share.lasting_crossover(open_) == open_[open_ > 0.5].index[1]
    assert share.lasting_crossover(pd.Series([0.6, 0.4], index=[1, 2])) is None


def test_leaderboard_change_and_headline():
    latest, table = leaderboard.latest_and_before(weekly_table(), "company")
    assert list(table["value"]) == ["Stealth (undisclosed)", "DeepSeek", "OpenAI"]
    # ties sort by name; stealth on top -> headline names the top named lab
    text = {"headline": "{company} leads", "headline_stealth_top": "{company} leads named labs"}
    assert leaderboard.headline(table, text) == "DeepSeek leads named labs"
    top, stealth_on_top = leaderboard.leader(table)
    assert (top["value"], top["share"], stealth_on_top) == ("DeepSeek", 0.3, True)
    assert leaderboard.change_text(-5.0) == "▼ 5.0"
    assert leaderboard.change_text(float("nan")) == "NEW"
    assert leaderboard.change_text(0.01) == "–"


def test_footer_text_has_source_coverage_and_stealth_note():
    style = charts.load_style()
    text = charts.footer_text(weekly_table(), "2026-10-07T02:44:49.638Z", style, stealth_note=True)
    assert "as of Oct 7, 2026" in text
    assert "Top-50 coverage 95%" in text
    assert "Excludes stealth models (15% of tokens in the latest week)" in text


def test_both_themes_render(tmp_path):
    for theme in ("dark", "light"):
        style = charts.load_style()
        style["theme"], style["colors"] = theme, style["themes"][theme]
        assert len(charts.render_all(weekly_table(), "2026-10-07T00:00:00Z", tmp_path / theme,
                                     style)) == 4


def test_render_all_writes_fixed_names_and_same_bytes_twice(tmp_path):
    weekly = weekly_table()
    first = charts.render_all(weekly, "2026-10-07T02:44:49.638Z", tmp_path / "a")
    second = charts.render_all(weekly, "2026-10-07T02:44:49.638Z", tmp_path / "b")
    assert sorted(p.name for p in first) == [
        "company_leaderboard_portrait.png", "company_leaderboard_square.png",
        "weights_share_portrait.png", "weights_share_square.png"]
    for a, b in zip(first, second):
        assert a.read_bytes() == b.read_bytes()
