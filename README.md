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

## Running locally (optional)

Not needed. If you ever want to: install Python 3.11+, run `pip install -r requirements.txt`, and copy `.env.example` to `.env` with your key in it.
