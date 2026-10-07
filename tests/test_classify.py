import json

import pandas as pd

import classify

LABS = pd.DataFrame([
    {"prefix": "deepseek", "company": "DeepSeek", "company_source": "manual: x",
     "default_weights": "", "default_weights_source": ""},
    {"prefix": "openai", "company": "OpenAI", "company_source": "manual: x",
     "default_weights": "closed", "default_weights_source": "manual: x"},
    {"prefix": "stealth", "company": "Stealth (undisclosed)", "company_source": "manual: x",
     "default_weights": "stealth", "default_weights_source": "manual: x"},
])
CATALOG = {
    "deepseek/v3": {"hugging_face_id": "deepseek-ai/DeepSeek-V3"},
    "openai/gpt-oss": {"hugging_face_id": "openai/gpt-oss-120b"},
    "openai/gpt-5": {"hugging_face_id": None},
}
EMPTY = pd.DataFrame(columns=classify.MODEL_COLUMNS)


def test_split_slug_records_free_then_strips_suffix():
    assert classify.split_slug("deepseek/v3:free") == ("deepseek/v3", True)
    assert classify.split_slug("anthropic/claude:thinking") == ("anthropic/claude", False)
    assert classify.split_slug("openai/gpt-5") == ("openai/gpt-5", False)


def test_weights_rule_order():
    labs = {r["prefix"]: r for r in LABS.to_dict("records")}
    # Hugging Face ID beats the lab's closed default
    assert classify.weights_rule("openai/gpt-oss", CATALOG, labs)[0] == "open"
    assert classify.weights_rule("openai/gpt-5", CATALOG, labs)[0] == "closed"
    assert classify.weights_rule("stealth/x", CATALOG, labs)[0] == "stealth"
    # no HF ID and no lab default -> blank, for review
    assert classify.weights_rule("deepseek/r9", CATALOG, labs) == ("", "")


def test_update_registry_adds_new_models_with_sources():
    first_seen = {"deepseek/v3": "2026-01-01", "openai/gpt-5": "2026-02-01", "deepseek/r9": "2026-03-01"}
    models, new_ids = classify.update_registry(EMPTY, LABS, CATALOG, first_seen)
    row = models.set_index("model_id").loc["deepseek/v3"]
    assert (row["company"], row["weights"], row["first_seen"]) == ("DeepSeek", "open", "2026-01-01")
    assert row["weights_source"] == "catalog: hugging_face_id deepseek-ai/DeepSeek-V3"
    assert models.set_index("model_id").loc["deepseek/r9", "weights"] == ""
    assert new_ids == ["deepseek/r9", "deepseek/v3", "openai/gpt-5"]


def test_update_registry_never_overwrites_a_filled_label():
    manual = pd.DataFrame([{"model_id": "openai/gpt-oss", "company": "OpenAI",
                            "company_source": "manual: x", "weights": "closed",
                            "weights_source": "manual: https://example.com", "first_seen": "2025-12-01"}])
    models, new_ids = classify.update_registry(manual, LABS, CATALOG, {"openai/gpt-oss": "2026-01-01"})
    row = models.iloc[0]
    assert (row["weights"], row["weights_source"], row["first_seen"]) == (
        "closed", "manual: https://example.com", "2025-12-01")
    assert new_ids == []


def test_classify_joins_free_variants_to_base_and_flags_unknowns():
    rankings = pd.DataFrame([
        {"date": "2026-01-01", "slug": "deepseek/v3", "tokens": 60},
        {"date": "2026-01-01", "slug": "deepseek/v3:free", "tokens": 20},
        {"date": "2026-01-01", "slug": "deepseek/r9", "tokens": 20},
        {"date": "2026-01-01", "slug": "other", "tokens": 5},
    ])
    labs = LABS.assign(country=["China", "United States", "Undisclosed"],
                       country_source=["manual: x"] * 3)
    families = pd.DataFrame([{"pattern": "^deepseek/", "family": "DeepSeek"}])
    models, _ = classify.update_registry(EMPTY, labs, CATALOG, classify.first_seen_dates(rankings),
                                         families)
    out = classify.classify(rankings, models)
    assert list(out["model_id"]) == ["deepseek/v3", "deepseek/v3", "deepseek/r9", "other"]
    assert list(out["is_free"]) == [False, True, False, False]
    assert list(out["weights"]) == ["open", "open", "unknown", "other"]
    # 20 of the 100 top-50 tokens have unknown weights; 'other' is not counted
    assert classify.unknown_report(out) == {"company": 0.0, "weights": 0.2,
                                            "country": 0.0, "family": 0.0}


def test_run_reads_raw_folder_and_saves_registry(tmp_path):
    raw = tmp_path / "raw" / "2026-10-12"
    raw.mkdir(parents=True)
    (raw / "rankings_daily_01.json").write_text(json.dumps({"data": [
        {"date": "2026-10-05", "model_permaslug": "openai/gpt-5", "total_tokens": "7"}]}))
    (raw / "models.json").write_text(json.dumps({"data": [
        {"id": "openai/gpt-5", "canonical_slug": "openai/gpt-5", "hugging_face_id": None}]}))
    reg = tmp_path / "registry"
    reg.mkdir()
    LABS.to_csv(reg / "labs.csv", index=False)
    (reg / "families.csv").write_text("pattern,family\n^openai/,GPT\n")
    EMPTY.to_csv(reg / "models.csv", index=False)

    classified, _, new_ids = classify.run(raw, reg)
    assert new_ids == ["openai/gpt-5"]
    assert classified.loc[0, "weights"] == "closed"
    saved = classify.read_csv(reg / "models.csv")
    assert saved.loc[0, "weights_source"] == "rule: labs.csv default for openai"


def test_family_rule_first_match_wins():
    families = pd.DataFrame([{"pattern": "^openai/gpt-.*-mini", "family": "GPT Mini"},
                             {"pattern": "^openai/gpt-", "family": "GPT"}])
    rows = families.to_dict("records")
    assert classify.family_rule("openai/gpt-5-mini", rows)[0] == "GPT Mini"
    assert classify.family_rule("openai/gpt-5", rows) == ("GPT", "rule: families.csv pattern ^openai/gpt-")
    assert classify.family_rule("x/unknown", rows) == ("", "")


def test_old_registry_gets_new_columns_filled():
    old = pd.DataFrame([{"model_id": "openai/gpt-5", "company": "OpenAI", "company_source": "manual: x",
                         "weights": "closed", "weights_source": "manual: x", "first_seen": "2026-01-01"}])
    labs = LABS.assign(country=["China", "United States", "Undisclosed"],
                       country_source=["manual: x"] * 3)
    families = pd.DataFrame([{"pattern": "^openai/", "family": "GPT"}])
    models, _ = classify.update_registry(old, labs, CATALOG, {"openai/gpt-5": "2026-01-01"}, families)
    row = models.iloc[0]
    assert (row["country"], row["family"]) == ("United States", "GPT")
    assert row["country_source"] == "rule: labs.csv prefix openai"
