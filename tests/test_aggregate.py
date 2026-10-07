from datetime import date

import pandas as pd
import pytest

import aggregate


def rows(day, **tokens_by_label):
    """One classified row per (weights, company) label for a day."""
    out = []
    for key, tokens in tokens_by_label.items():
        weights, company = key.split("_")
        model_id = "other" if weights == "other" else f"{company}/{weights}"
        out.append({"date": day, "slug": model_id, "model_id": model_id, "tokens": tokens,
                    "is_free": False, "weights": weights, "company": company,
                    "country": company, "family": company, "price_tier": "Mid",
                    "reasoning": "No", "input_type": "Text only", "free": "Paid",
                    "size": "n/a" if weights != "open" else "Large"})
    return out


# Mon Oct 5 - Sun Oct 11 2026 is ISO week 2026-W41; Oct 12 is the next Monday
CLASSIFIED = pd.DataFrame(
    rows("2026-10-05", open_ds=60, closed_oa=30, stealth_stealth=10, other_other=100)
    + rows("2026-10-11", open_ds=40, closed_oa=70)
    + rows("2026-10-12", open_ds=999))  # the unfinished week: must be dropped
START, END = date(2025, 10, 13), date(2026, 10, 11)


def week_table():
    df = aggregate.add_periods(CLASSIFIED, START, END)
    return aggregate.totals(df, "week", START, END).set_index(["dimension", "value"])


def test_unfinished_week_is_dropped():
    df = aggregate.add_periods(CLASSIFIED, START, END)
    assert df["date"].max() == "2026-10-11"
    assert set(df["week"]) == {"2026-10-05"}


def test_weights_share_leaves_out_stealth_and_other():
    w = week_table().loc["weights"]
    # open 100, closed 100 -> 50/50; stealth and other have no share
    assert w.loc["open", "share"] == pytest.approx(0.5)
    assert w.loc["closed", "share"] == pytest.approx(0.5)
    assert pd.isna(w.loc["stealth", "share"]) and pd.isna(w.loc["other", "share"])
    # share_of_all uses every token: 100 / 310
    assert w.loc["open", "share_of_all"] == pytest.approx(100 / 310)
    assert w.loc["other", "share_of_all"] == pytest.approx(100 / 310)


def test_company_share_includes_stealth_as_a_company():
    c = week_table().loc["company"]
    assert c.loc["stealth", "share"] == pytest.approx(10 / 210)
    assert c.loc[["ds", "oa", "stealth"], "share"].sum() == pytest.approx(1.0)


def test_week_label_and_partial_flag():
    t = week_table()
    assert set(t["label"]) == {"2026-W41"}
    assert not t["partial"].any()


def test_months_cut_by_the_window_are_partial():
    df = aggregate.add_periods(CLASSIFIED, START, END)
    m = aggregate.totals(df, "month", START, END)
    assert set(m["label"]) == {"2026-10"}
    assert m["partial"].all()  # October runs past Oct 11
    assert aggregate.period_info("month", "2026-09-01", START, END) == ("2026-09", False)
    assert aggregate.period_info("month", "2025-10-01", START, END) == ("2025-10", True)


def test_data_window_is_52_weeks_ending_last_sunday():
    assert aggregate.data_window(date(2026, 10, 14)) == (date(2025, 10, 13), date(2026, 10, 11))


def test_same_input_same_output():
    a, b = week_table(), week_table()
    pd.testing.assert_frame_equal(a, b)


def test_top_models_merges_variants_and_skips_other():
    df = aggregate.add_periods(CLASSIFIED, START, END)
    top = aggregate.top_models(df, "2026-10-05", n=2)
    assert list(top.index) == ["ds/open", "oa/closed"]  # tie: alphabetical
    assert list(top) == [100, 100]
