# OpenRouter Weekly Usage Breakdown

Weekly LinkedIn-ready charts of OpenRouter token usage (open vs closed weights, company, and more).
The full plan is in [`planning/Spec_Weekly_OpenRouter_Usage_Breakdown_v3_final.md`](planning/Spec_Weekly_OpenRouter_Usage_Breakdown_v3_final.md).

## One-time setup

You need Python 3.11 or newer. Check with `python --version` (Windows) or `python3 --version` (Mac).

### 1. Get the code

```bash
git clone https://github.com/danielwipert/openrouter.chart.git
cd openrouter.chart
```

### 2. Make a virtual environment

A virtual environment is a private folder of libraries just for this project, so it can't clash with other Python projects.

Mac:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

You'll see `(.venv)` at the start of your prompt when it's active. Activate it again each time you open a new terminal.

### 3. Install the libraries

```bash
pip install -r requirements.txt
```

### 4. Add your API key

1. Copy `.env.example` to a new file named `.env`.
2. Get a key at https://openrouter.ai/settings/keys.
3. Paste it after `OPENROUTER_API_KEY=` in `.env`, then save.

`.env` is listed in `.gitignore`, so git never uploads it.

### 5. Check it works

```bash
python -c "import pandas, matplotlib; print('OK')"
```

If it prints `OK`, setup is done.
