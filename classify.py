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
from pathlib import Path

import pandas as pd

REGISTRY_DIR = Path("registry")
RAW_DIR = Path("raw")
REQUIRED = ["company", "weights", "country", "family"]  # required dimensions (phases 1-2)
MODEL_COLUMNS = ["model_id", "company", "company_source", "weights", "weights_source",
                 "country", "country_source", "family", "family_source", "first_seen"]
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
