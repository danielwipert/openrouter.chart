"""Weights from the lab's own Hugging Face account."""

import json

import pandas as pd

import hf_weights

LABS = pd.DataFrame([{"prefix": "stepfun", "hf_org": "stepfun-ai"},
                     {"prefix": "typesafe", "hf_org": ""}])


def models(*rows):
    return pd.DataFrame([{"model_id": m, "weights": w, "weights_source": s} for m, w, s in rows])


def test_model_name_drops_lab_and_date():
    assert hf_weights.model_name("stepfun/step-5-preview-20261008") == "step-5-preview"
    assert hf_weights.model_name("qwen/qwen3-embedding-8b") == "qwen3-embedding-8b"


def test_only_an_exact_name_matches():
    search = lambda org, name: ["zai-org/GLM-5.3-Flash", "zai-org/GLM-5.3-FlashX-FP8"]
    assert hf_weights.find_repo("z-ai/glm-5.3-flashx-20260918", "zai-org", search) is None
    search = lambda org, name: ["XiaomiMiMo/MiMo-V2-Flash-Base", "XiaomiMiMo/MiMo-V2-Flash"]
    assert (hf_weights.find_repo("xiaomi/mimo-v2-flash-20251210", "XiaomiMiMo", search)
            == "XiaomiMiMo/MiMo-V2-Flash")


def test_fill_weights_marks_a_match_open_and_caches_it(tmp_path):
    rows = models(("stepfun/step-5-preview-20261008", "", ""),
                  ("stepfun/step-4", "closed", "manual: x"),         # filled: never touched
                  ("typesafe/jev-1.14-20261014", "", ""))            # lab has no account
    calls = []
    search = lambda org, name: calls.append((org, name)) or ["stepfun-ai/Step-5-Preview"]
    out = hf_weights.fill_weights(rows.copy(), LABS, tmp_path, search)
    assert list(out["weights"]) == ["open", "closed", ""]
    assert "https://huggingface.co/stepfun-ai/Step-5-Preview" in out.loc[0, "weights_source"]
    assert out.loc[1, "weights_source"] == "manual: x"
    assert calls == [("stepfun-ai", "step-5-preview")]
    # second run reads the saved answer: no new lookup
    hf_weights.fill_weights(rows.copy(), LABS, tmp_path, search)
    assert len(calls) == 1
    assert json.loads((tmp_path / "hf_weights.json").read_text()) == {
        "stepfun/step-5-preview-20261008": "stepfun-ai/Step-5-Preview"}


def test_no_match_stays_blank_for_review(tmp_path):
    rows = models(("stepfun/step-6-20261101", "", ""))
    out = hf_weights.fill_weights(rows, LABS, tmp_path, lambda org, name: [])
    assert out.loc[0, "weights"] == ""
