"""Weights from the lab's own Hugging Face account (spec, "Model registry and dimensions").

When a model's weights are still blank after the catalog and labs.csv rules, look
in the lab's official Hugging Face account (hf_org in labs.csv) for a repo with
exactly the model's name, ignoring case, dashes and dots:

  stepfun/step-5-preview-20261008  ->  stepfun-ai/Step-5-Preview  ->  open

A near miss (zai-org/GLM-5.3-Flash for z-ai/glm-5.3-flashx) is not a match: those
stay blank for a person to decide. Only the lab's own account counts, so a
stranger's re-upload never makes a model open.

Lookups are saved in the raw folder (hf_weights.json), so a rerun on the same
raw data makes no network calls and gives the same answer.
"""

import json
import re

import requests

HF_SEARCH = "https://huggingface.co/api/models"
CACHE_FILE = "hf_weights.json"


def simple_name(name):
    """'Step-5-Preview' and 'step-5-preview' both become 'step5preview'."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def model_name(model_id):
    """'stepfun/step-5-preview-20261008' -> 'step-5-preview' (no lab, no date)."""
    return re.sub(r"-\d{8}$", "", model_id.split("/", 1)[1])


def hf_search(org, name):
    """Repo IDs in this Hugging Face account whose name contains `name`, or None on error."""
    try:
        response = requests.get(HF_SEARCH, params={"author": org, "search": name, "limit": 100},
                                timeout=30)
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    return [m["id"] for m in response.json()]


def find_repo(model_id, org, search=None):
    """The repo in `org` with exactly this model's name, or None."""
    name = model_name(model_id)
    for repo in (search or hf_search)(org, name) or []:
        if simple_name(repo.split("/", 1)[1]) == simple_name(name):
            return repo
    return None


def fill_weights(models, labs, folder, search=None):
    """Mark blank-weights models open when the lab's account has a repo with their name."""
    orgs = {row["prefix"]: row.get("hf_org", "") for row in labs.to_dict("records")}
    todo = {i: orgs.get(model_id.split("/")[0], "")
            for i, model_id in models.loc[models["weights"] == "", "model_id"].items()}
    todo = {i: org for i, org in todo.items() if org}
    if not todo:
        return models

    path = folder / CACHE_FILE
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    missing = [i for i in todo if models.loc[i, "model_id"] not in cache]
    for i in missing:
        cache[models.loc[i, "model_id"]] = find_repo(models.loc[i, "model_id"], todo[i], search)
    if missing:
        path.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    for i in todo:
        repo = cache.get(models.loc[i, "model_id"])
        if repo:
            models.loc[i, "weights"] = "open"
            models.loc[i, "weights_source"] = (f"rule: lab's Hugging Face account has "
                                               f"https://huggingface.co/{repo} (same name)")
    return models
