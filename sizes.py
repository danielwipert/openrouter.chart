"""Size of open-weight models: total parameters from Hugging Face (spec, phase 3).

Small under 30B, Medium 30B to 200B, Large over 200B total parameters (Dan's
decision, Oct 7 2026; mixture-of-experts models count all their parameters).

Lookups are saved in the raw folder (hf_sizes.json), so a rerun on the same
raw data makes no network calls and gives the same answer.
"""

import json
import re

import requests

HF_API = "https://huggingface.co/api/models/{repo}?expand[]=safetensors"
SMALL_UNDER = 30e9
MEDIUM_UP_TO = 200e9
NOT_APPLICABLE = "n/a"
CACHE_FILE = "hf_sizes.json"


def size_tier(params):
    if params < SMALL_UNDER:
        return "Small"
    return "Medium" if params <= MEDIUM_UP_TO else "Large"


def hf_repo(weights_source):
    """The Hugging Face repo named in a model's weights source, if any."""
    match = (re.search(r"hugging_face_id (\S+)", weights_source)
             or re.search(r"huggingface\.co/([\w.-]+/[\w.-]+)", weights_source))
    return match.group(1) if match else None


def hf_lookup(repo):
    """Total parameter count from Hugging Face, or None if it isn't listed."""
    try:
        response = requests.get(HF_API.format(repo=repo), timeout=30)
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None
    return (response.json().get("safetensors") or {}).get("total")


def lookup_sizes(repos, folder, lookup=None):
    """Parameter counts for these repos, using and extending the raw folder's cache."""
    lookup = lookup or hf_lookup
    path = folder / CACHE_FILE
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    missing = [r for r in sorted(set(repos)) if r not in cache]
    for repo in missing:
        cache[repo] = lookup(repo)
    if missing:
        path.write_text(json.dumps(cache, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return cache


def fill_sizes(models, folder, lookup=None):
    """Fill blank sizes: n/a for closed and stealth models, a tier for open ones."""
    blank = models["size"] == ""
    not_open = blank & (models["weights"] != "open") & (models["weights"] != "")
    models.loc[not_open, "size"] = NOT_APPLICABLE
    models.loc[not_open, "size_source"] = "rule: sizes apply to open-weight models only"
    todo = models[blank & (models["weights"] == "open")]
    repos = {i: hf_repo(src) for i, src in todo["weights_source"].items()}
    counts = lookup_sizes([r for r in repos.values() if r], folder, lookup)
    for i, repo in repos.items():
        params = counts.get(repo) if repo else None
        if params:
            models.loc[i, "size"] = size_tier(params)
            models.loc[i, "size_source"] = (f"catalog: Hugging Face {repo} safetensors total "
                                            f"{params / 1e9:.1f}B parameters")
    return models
