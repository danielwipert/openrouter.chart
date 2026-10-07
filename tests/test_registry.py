"""Checks on the real registry files (spec accuracy rule: every label has a source)."""

import classify

MODELS = classify.read_csv(classify.REGISTRY_DIR / "models.csv")
LABS = classify.read_csv(classify.REGISTRY_DIR / "labs.csv")
SOURCE_KINDS = ("catalog:", "rule:", "manual:")


def blank_sources(table, fields, key):
    problems = []
    for row in table.to_dict("records"):
        for field in fields:
            source = row[f"{field}_source"]
            if row[field] and not source.startswith(SOURCE_KINDS):
                problems.append(f"{row[key]}: {field} has no valid source")
    return problems


def test_every_model_label_has_a_source():
    assert blank_sources(MODELS, ["company", "weights"], "model_id") == []


def test_every_lab_field_has_a_source():
    assert blank_sources(LABS, ["company", "country", "default_weights"], "prefix") == []


def test_manual_sources_include_a_link():
    for table, fields in [(MODELS, ["company", "weights"]), (LABS, ["company", "country", "default_weights"])]:
        for field in fields:
            manual = table[table[f"{field}_source"].str.startswith("manual:")]
            assert manual[f"{field}_source"].str.contains("http").all(), field


def test_values_are_from_the_allowed_lists():
    assert set(MODELS["weights"]) <= {"open", "closed", "stealth", ""}
    assert set(LABS["default_weights"]) <= {"closed", "stealth", ""}


def test_one_row_per_model_and_per_prefix():
    assert MODELS["model_id"].is_unique
    assert LABS["prefix"].is_unique
