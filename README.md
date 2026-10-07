# OpenRouter Weekly Usage Breakdown

Weekly LinkedIn-ready charts of OpenRouter token usage (open vs closed weights, company, and more).
The full plan is in [`planning/Spec_Weekly_OpenRouter_Usage_Breakdown_v3_final.md`](planning/Spec_Weekly_OpenRouter_Usage_Breakdown_v3_final.md).

Everything runs in the cloud on GitHub Actions. Nothing needs to be installed on your computer.

## One-time setup: add the API key

The code reads your OpenRouter key from a GitHub secret. A secret is stored encrypted, never shown in logs, and never saved in the code.

1. Get a key at https://openrouter.ai/settings/keys.
2. On GitHub, open this repo, then **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret**.
4. Name: `OPENROUTER_API_KEY`. Secret: paste your key. Click **Add secret**.

## Checking it works

1. Open the **Actions** tab of this repo.
2. Click **Setup check** on the left.
3. Click **Run workflow**, then the green **Run workflow** button.
4. After about a minute, a green tick means it worked. A red cross means something failed: click the run to see which step and why.

The setup check also runs on its own after every code change.

## Every Monday

The **Weekly run** starts by itself every Monday at 13:07 UTC (8:07 a.m. Central in summer, 7:07 a.m. in winter). You can also start it any time: **Actions** tab, **Weekly run**, **Run workflow**.

- **Green tick:** READY TO POST.
- **Red cross:** GitHub emails you. Either a hard check stopped the run (the log says why, e.g. a rejected API key), or the results were saved but are NOT READY TO POST (the run report says why).

Then:

1. Pull up `output/<week>/` in the repo (e.g. `output/2026-W41/`):
   - `run_report.md`: check it says **READY TO POST**. On the first Monday of the month, compare the top 5 with openrouter.ai/rankings and tick the box.
   - `charts/`: the LinkedIn images, square and portrait. Look at them on your phone.
   - `caption.md`: draft posts with this week's numbers. Edit before posting.
   - `weekly.csv`, `monthly.csv`: the numbers behind the charts.
   - `meta.json`: which data was used.
2. If the report lists a new model with a blank label, fill it in `registry/models.csv` (with a source link) and run again by hand.

## Running locally (optional)

Not needed. If you ever want to: install Python 3.11+, run `pip install -r requirements.txt`, copy `.env.example` to `.env` with your key in it, then run `python run_weekly.py` (or `python run_weekly.py --no-fetch` to rebuild from the newest saved data).
