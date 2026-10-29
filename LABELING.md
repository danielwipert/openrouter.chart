# Labeling playbook: fixing a NOT READY week

A scheduled Claude task follows this every Monday evening, after the Weekly run.
You can follow it by hand too. The task never merges anything: it opens a pull
request, and Dan reviews and merges it.

## 1. Look at this week's Weekly run

Open the newest **Weekly run** on `main` (Actions tab).

| What you see | What to do |
|---|---|
| No run today | Start one: **Actions** > **Weekly run** > **Run workflow** on `main`. Wait for it. |
| Green (READY TO POST) | Only do step 4 (re-check low-confidence labels). If nothing changed, stop: no pull request. |
| Red, run report says **NOT READY TO POST** | Steps 2 to 6. The report is `output/<week>/run_report.md`. |
| Red, a **hard check** stopped the run (log says "Run stopped" or "Fetch stopped") | Read the log. A rejected key, stale data or missing days are not labeling problems: report what the log says and stop. Fix only a clear bug in this repo's code. |

## 2. Fill in every blank label

The run report's **Blank registry fields** section lists each model and field.
Edit `registry/models.csv` (and `registry/families.csv` for a new family).

Every value needs a source that starts with `manual:`, `rule:` or `catalog:`.
A `manual:` source is a link plus a short reason in brackets.

**Where to look, in order:**

1. The full OpenRouter catalog: `https://openrouter.ai/api/v1/models?output_modalities=all`
   (match on `canonical_slug`), then `https://openrouter.ai/api/v1/models/<id>/endpoints`
   (the ID without the `-YYYYMMDD` date). These give the date added (`created`),
   pricing, `supported_parameters` and `input_modalities`.
2. The lab's own Hugging Face account (`hf_org` in `registry/labs.csv`).
3. The lab's own announcement or docs, then OpenRouter's announcement.
4. News coverage, only when 1 to 3 say nothing.

**Rules for each field:**

- **weights**
  - `open`: downloadable weights in the lab's official Hugging Face account, or
    an official download. Gated (accept-a-license) still counts as open.
  - `closed`: API only.
  - **Promised but not out yet** (for example "weights by Nov 4"): `closed` with
    `low confidence` in the source, and say what to switch to and when:
    `manual: <link> (low confidence: API-only for now; <lab> promised open weights by <date>; switch to open with size <tier> (<N> total parameters) once they are on Hugging Face)`.
  - A stranger's re-upload on Hugging Face never counts.
- **size** (open models only; closed ones get `n/a`): total parameters,
  mixture-of-experts counted in full. Small under 30B, Medium 30B to 200B,
  Large over 200B. Use the Hugging Face parameter count, else the lab's stated count.
- **family**: add a pattern to `registry/families.csv` when it's a new product line,
  next to the lab's other patterns. More specific patterns go first.
- **release_date**: the date the model was added to OpenRouter (`created`).
- **price_tier**: average of input and output price per million tokens. Budget
  under $0.50, Mid $0.50 to $5, Premium over $5. If output is free, use the input
  price alone.
- **reasoning**: `Yes` if `supported_parameters` has `reasoning` or `include_reasoning`.
- **input_type**: `Text only` if the only input is text, else `Multimodal`.

If a lab keeps coming up with the same answer (every model closed, say), add a
`default_weights` to `registry/labs.csv` with a source, so it fills itself next time.
If a lab has no `hf_org` but has an official Hugging Face account, add it.

**Judgment calls:** when the sources disagree or don't settle it, pick the
safer label (closed, with `low confidence`), and list the call in the pull
request so Dan can overrule it.

## 3. Don't touch filled labels

Only fill blanks, except in step 4. Never change a label that already has a
source unless a newer, better source shows it is wrong; say so in the pull request.

## 4. Re-check low-confidence labels

The run report lists **Low-confidence labels to re-check monthly**. For each one
whose source says "switch to ... once ...", check whether that has happened
(weights now in the lab's Hugging Face account, say). If it has, update the
label and its source.

## 5. Rebuild and test

```bash
pip install -r requirements.txt
```

```bash
python run_weekly.py --no-fetch
```

```bash
python -m pytest -q
```

The report's first line must say **READY TO POST** and every test must pass.
Commit everything the rebuild changed, chart images included: the charts show
the new labels.

## 6. Open a pull request

Branch from `main`, commit `registry/` and `output/`, push, and open a pull
request titled `Label N new models and rebuild <week> (now READY TO POST)`.
In the description, list each model with its labels in one line, then a
**Judgment calls** section, then any **Follow-ups** (dates to re-check).

After Dan merges it, the website republishes by itself.
