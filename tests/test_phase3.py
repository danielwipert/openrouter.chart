"""Model size, launch curve and task mix."""

import json

import pandas as pd

import sizes
from charts import launch, tasks


# --- Size --------------------------------------------------------------------

def test_size_tiers_use_total_parameters():
    assert [sizes.size_tier(p) for p in (8e9, 29.9e9, 30e9, 200e9, 201e9)] == [
        "Small", "Small", "Medium", "Medium", "Large"]


def test_hf_repo_comes_from_the_weights_source():
    assert sizes.hf_repo("catalog: hugging_face_id deepseek-ai/DeepSeek-V3") == "deepseek-ai/DeepSeek-V3"
    assert sizes.hf_repo("manual: https://huggingface.co/BAAI/bge-m3 (card)") == "BAAI/bge-m3"
    assert sizes.hf_repo("rule: labs.csv default for openai") is None


def test_fill_sizes_caches_lookups_in_the_raw_folder(tmp_path):
    models = pd.DataFrame([
        {"model_id": "a/open", "weights": "open", "weights_source": "catalog: hugging_face_id a/Open",
         "size": "", "size_source": ""},
        {"model_id": "b/closed", "weights": "closed", "weights_source": "rule: x",
         "size": "", "size_source": ""}])
    calls = []
    out = sizes.fill_sizes(models.copy(), tmp_path, lambda repo: calls.append(repo) or 70e9)
    assert list(out["size"]) == ["Medium", "n/a"]
    assert "70.0B" in out.loc[0, "size_source"]
    # second run reads the saved answer: no new lookup
    sizes.fill_sizes(models.copy(), tmp_path, lambda repo: calls.append(repo) or 1)
    assert calls == ["a/Open"]
    assert json.loads((tmp_path / "hf_sizes.json").read_text()) == {"a/Open": 70e9}


# --- Launch curve ------------------------------------------------------------------

def test_launch_table_aligns_models_at_week_zero():
    rows = pd.DataFrame([
        {"week": "2026-01-05", "model_id": "old/m", "tokens": 90},
        {"week": "2026-01-05", "model_id": "new/m", "tokens": 10},
        {"week": "2026-01-12", "model_id": "old/m", "tokens": 50},
        {"week": "2026-01-12", "model_id": "new/m", "tokens": 50},
        {"week": "2026-01-12", "model_id": "other", "tokens": 0}])
    models = pd.DataFrame([{"model_id": "old/m", "release_date": "2025-06-01"},
                           {"model_id": "new/m", "release_date": "2026-01-07"}])
    table = launch.launch_table(rows, models)
    assert list(table) == ["new/m"]          # old/m launched before the window
    assert list(table["new/m"]) == [0.1, 0.5]
    assert launch.short_name("x-ai/grok-4.1-fast-20251119", {}) == "Grok 4.1 Fast"


# --- Task mix ------------------------------------------------------------------------

def write_snapshot(folder, share):
    folder.mkdir(parents=True)
    (folder / "task_classifications.json").write_text(json.dumps({"data": {
        "as_of": "2026-10-06", "window_days": 7,
        "classifications": [{"tag": "code:x", "display_name": "Coding", "macro_category": "code",
                             "token_share": share}],
        "macro_categories": [{"key": "code", "label": "Code", "token_share": 1.0}]}}))


def test_task_change_uses_the_snapshot_about_four_weeks_back(tmp_path):
    write_snapshot(tmp_path / "2026-09-07", 0.4)
    write_snapshot(tmp_path / "2026-09-28", 0.2)   # only 9 days back: too recent
    write_snapshot(tmp_path / "2026-10-07", 0.5)
    earlier = tasks.snapshot_four_weeks_before(tmp_path / "2026-10-07")
    assert earlier.name == "2026-09-07"
    assert tasks.snapshot_four_weeks_before(tmp_path / "2026-09-07") is None
    assert tasks.snapshot_count(tmp_path) == 3
