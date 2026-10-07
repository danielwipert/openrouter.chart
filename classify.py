"""Pipeline step 3: label every model, using only the registry.

For each model in the rankings:
  1. Record is_free from the ':free' suffix, then strip any ':variant' suffix
     so variants count with their base model.
  2. Add models not yet in registry/models.csv, filling every field the rules can.
  3. Attach the registry's labels. A blank label becomes 'unknown'.

Country comes from labs.csv (headquarters). Family comes from the first
matching pattern in families.csv.

Weights rule, in order (spec, "Model registry and dimensions"):
  a manual label in models.csv wins; else a Hugging Face ID in the catalog means
  open; else the lab's default in labs.csv (closed, or stealth); else blank,
  which goes on the review list.

The run only fills blank registry fields. It never changes a filled one, so a
model's labels change only when Dan edits the CSV.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import sizes

REGISTRY_DIR = Path("registry")
RAW_DIR = Path("raw")
REQUIRED = ["company", "weights", "country", "family",  # required dimensions (phases 1-3)
            "release_date", "price_tier", "reasoning", "input_type", "size"]
MODEL_COLUMNS = (["model_id"] + [c for field in REQUIRED for c in (field, f"{field}_source")]
                 + ["first_seen"])
# Price tier cutoffs in $ per million tokens, input and output averaged (spec, Decisions)
BUDGET_UNDER = 0.50
MID_UP_TO = 5.00
UNDISCLOSED = "Undisclosed"  # stealth models: price, reasoning and input type unknown
OTHER = "other"  # the API's row for everything outside the daily top 50
UNKNOWN = "unknown"


# --- Reading ---------------------------------------------------------------

def read_csv(path):
    """Read a registry CSV with every cell as text and blanks as ''."""
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def latest_raw_folder(raw_dir=RAW_DIR):
    folders = sorted(p for p in raw_dir.iterdir() if p.is_dir())
    if not folders:
        sys.exit("No raw data found. Run fetch.py first.")
    return folders[-1]


def load_rankings(folder):
    """All rankings rows from one raw folder, as date / slug / tokens."""
    rows = []
    for part in sorted(folder.glob("rankings_daily_*.json")):
        rows += json.loads(part.read_text(encoding="utf-8"))["data"]
    df = pd.DataFrame(rows).rename(columns={"model_permaslug": "slug"})
    df["tokens"] = df.pop("total_tokens").astype("int64")
    return df[["date", "slug", "tokens"]]


def load_catalog(folder):
    """Catalog entries keyed by canonical_slug, which is what rankings rows use."""
    data = json.loads((folder / "models.json").read_text(encoding="utf-8"))["data"]
    return {m["canonical_slug"]: m for m in data}


# --- Step 3a: free flag and base model ---------------------------------------

def split_slug(slug):
    """'deepseek/v3:free' -> ('deepseek/v3', True). Any ':variant' is stripped."""
    return slug.split(":")[0], slug.endswith(":free")


# --- Step 3b: registry -------------------------------------------------------

def company_rule(model_id, labs):
    prefix = model_id.split("/")[0]
    lab = labs.get(prefix)
    if lab and lab["company"]:
        return lab["company"], f"rule: labs.csv prefix {prefix}"
    return "", ""


def weights_rule(model_id, catalog, labs):
    """Weights from the catalog or the lab default. Manual labels are already in models.csv."""
    hf_id = (catalog.get(model_id) or {}).get("hugging_face_id")
    if hf_id:
        return "open", f"catalog: hugging_face_id {hf_id}"
    prefix = model_id.split("/")[0]
    default = (labs.get(prefix) or {}).get("default_weights", "")
    if default in ("closed", "stealth"):
        return default, f"rule: labs.csv default for {prefix}"
    return "", ""


def country_rule(model_id, labs):
    prefix = model_id.split("/")[0]
    lab = labs.get(prefix)
    if lab and lab.get("country"):
        return lab["country"], f"rule: labs.csv prefix {prefix}"
    return "", ""


def family_rule(model_id, families):
    """First pattern in families.csv that matches the model ID wins."""
    for row in families:
        if re.search(row["pattern"], model_id):
            return row["family"], f"rule: families.csv pattern {row['pattern']}"
    return "", ""


def is_stealth(model_id, labs):
    return (labs.get(model_id.split("/")[0]) or {}).get("default_weights") == "stealth"


def release_rule(model_id, catalog, labs, first_seen):
    entry = catalog.get(model_id)
    if entry and entry.get("created"):
        day = datetime.fromtimestamp(entry["created"], timezone.utc).date().isoformat()
        return day, "catalog: created (date added to OpenRouter)"
    if is_stealth(model_id, labs) and first_seen:
        return first_seen, "rule: first day in OpenRouter data (stealth model)"
    return "", ""


def price_tier(average):
    """Budget under $0.50, Mid $0.50 to $5, Premium over $5 (per million tokens)."""
    if average < BUDGET_UNDER:
        return "Budget"
    return "Mid" if average <= MID_UP_TO else "Premium"


def price_rule(model_id, catalog, labs):
    entry = catalog.get(model_id)
    if entry and entry.get("pricing"):
        per_m_in = float(entry["pricing"].get("prompt", 0)) * 1e6
        per_m_out = float(entry["pricing"].get("completion", 0)) * 1e6
        # Embedding models have no output price: use the input price alone
        average = per_m_in if per_m_out == 0 else (per_m_in + per_m_out) / 2
        return price_tier(average), (f"catalog: pricing ${average:.2f}/M average "
                                     f"(in ${per_m_in:.2f}, out ${per_m_out:.2f})")
    if is_stealth(model_id, labs):
        return UNDISCLOSED, "rule: stealth model"
    return "", ""


def reasoning_rule(model_id, catalog, labs):
    entry = catalog.get(model_id)
    if entry and entry.get("supported_parameters") is not None:
        params = set(entry["supported_parameters"])
        found = bool(params & {"reasoning", "include_reasoning"})
        return ("Yes" if found else "No"), "catalog: supported_parameters"
    if is_stealth(model_id, labs):
        return UNDISCLOSED, "rule: stealth model"
    return "", ""


def input_rule(model_id, catalog, labs):
    entry = catalog.get(model_id)
    modalities = ((entry or {}).get("architecture") or {}).get("input_modalities")
    if modalities:
        value = "Text only" if set(modalities) == {"text"} else "Multimodal"
        return value, f"catalog: input_modalities {'+'.join(sorted(modalities))}"
    if is_stealth(model_id, labs):
        return UNDISCLOSED, "rule: stealth model"
    return "", ""


def update_registry(models, labs, catalog, first_seen, families=None):
    """Add new models and fill blank fields. Returns (models, list of new model IDs)."""
    labs = {row["prefix"]: row for row in labs.to_dict("records")}
    families = [] if families is None else families.to_dict("records")
    for column in MODEL_COLUMNS:  # registries from before a dimension existed
        if column not in models:
            models[column] = ""
    known = set(models["model_id"])
    new_ids = sorted(set(first_seen) - known)
    new_rows = pd.DataFrame([{"model_id": m, "first_seen": first_seen[m]} for m in new_ids],
                            columns=MODEL_COLUMNS).fillna("")
    models = pd.concat([models, new_rows], ignore_index=True)

    for i, row in models.iterrows():
        if not row["company"]:
            models.loc[i, ["company", "company_source"]] = company_rule(row["model_id"], labs)
        if not row["weights"]:
            models.loc[i, ["weights", "weights_source"]] = weights_rule(
                row["model_id"], catalog, labs)
        if not row["country"]:
            models.loc[i, ["country", "country_source"]] = country_rule(row["model_id"], labs)
        if not row["family"]:
            models.loc[i, ["family", "family_source"]] = family_rule(row["model_id"], families)
        model_id = row["model_id"]
        if not row["release_date"]:
            models.loc[i, ["release_date", "release_date_source"]] = release_rule(
                model_id, catalog, labs, row["first_seen"] or first_seen.get(model_id, ""))
        if not row["price_tier"]:
            models.loc[i, ["price_tier", "price_tier_source"]] = price_rule(model_id, catalog, labs)
        if not row["reasoning"]:
            models.loc[i, ["reasoning", "reasoning_source"]] = reasoning_rule(model_id, catalog, labs)
        if not row["input_type"]:
            models.loc[i, ["input_type", "input_type_source"]] = input_rule(model_id, catalog, labs)
    return models.sort_values("model_id", ignore_index=True), new_ids


def save_models(models, registry_dir=REGISTRY_DIR):
    models[MODEL_COLUMNS].to_csv(registry_dir / "models.csv", index=False, lineterminator="\n")


# --- Step 3c: attach labels --------------------------------------------------

def classify(rankings, models):
    """Rankings rows with is_free, base model_id and every required label."""
    df = rankings.copy()
    split = df["slug"].map(split_slug)
    df["model_id"] = split.str[0]
    df["is_free"] = split.str[1]
    df = df.merge(models[["model_id"] + REQUIRED], on="model_id", how="left")
    is_other = df["slug"] == OTHER
    for column in REQUIRED:
        df[column] = df[column].fillna("").replace("", UNKNOWN)
        df.loc[is_other, column] = OTHER
    # Free variant comes from the ':free' suffix on each row, not from the registry
    df["free"] = df["is_free"].map({True: "Free", False: "Paid"})
    df.loc[is_other, "free"] = OTHER
    return df


def unknown_report(classified):
    """Token share (of top-50 tokens) with an unknown value, per required dimension."""
    named = classified[classified["slug"] != OTHER]
    total = named["tokens"].sum()
    return {column: named.loc[named[column] == UNKNOWN, "tokens"].sum() / total
            for column in REQUIRED}


def first_seen_dates(rankings):
    named = rankings[rankings["slug"] != OTHER]
    ids = named["slug"].map(lambda s: split_slug(s)[0])
    return named.groupby(ids)["date"].min().to_dict()


def run(folder, registry_dir=REGISTRY_DIR):
    """Steps 3a-3c for one raw folder. Saves models.csv and returns the labeled rows."""
    rankings = load_rankings(folder)
    models = read_csv(registry_dir / "models.csv")
    labs = read_csv(registry_dir / "labs.csv")
    families = read_csv(registry_dir / "families.csv")
    models, new_ids = update_registry(models, labs, load_catalog(folder),
                                      first_seen_dates(rankings), families)
    models = sizes.fill_sizes(models, folder)
    save_models(models, registry_dir)
    return classify(rankings, models), models, new_ids


def main():
    folder = latest_raw_folder()
    classified, models, new_ids = run(folder)
    print(f"Classified {len(classified)} rows from {folder}")
    print(f"New models added to registry/models.csv: {len(new_ids)}")
    blanks = models[(models[REQUIRED] == "").any(axis=1)]
    print(f"Models with a blank required label: {len(blanks)}")
    for model_id in blanks["model_id"]:
        print(f"  {model_id}")
    for column, share in unknown_report(classified).items():
        print(f"Unknown {column}: {share:.2%} of top-50 tokens")


if __name__ == "__main__":
    main()
