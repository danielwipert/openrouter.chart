# Spec: Weekly OpenRouter Usage Breakdown (v3, final)

Oct 6, 2026 · @Dan

## What changed from v2

This is the final spec: the v2 build plan stands, and seven gaps found in review are now closed. The six decisions at the end were signed off on Oct 7, 2026; see "Decision sign-off changes" below for what they changed.

| # | Gap in v2 | Resolution in v3 |
| --- | --- | --- |
| 1 | Accuracy standard said the run "stops"; checks table said "soft" | The run always finishes. Any failed accuracy rule marks it **NOT READY TO POST** at the top of `run_report.md`. Only the hard checks stop a run. |
| 2 | "Only complete weeks" conflicted with charting Jan 1–4 | Jan 1–4 (Thu–Sun) is charted and labeled "partial week." Shares are still valid for a partial week. The current unfinished week is always dropped. |
| 3 | One file name (`chart_square.png`) for many charts | Every chart file is named `{dimension}_{chart}_{size}.png`, e.g. `weights_share_square.png`. Names never change week to week. |
| 4 | Week folder could be named for the run date | Folder is named for the last complete data week, e.g. a run on Mon Oct 12 writes `output/2026-W41/`. |
| 5 | Merging `:free` into the base model would erase the Free variant dimension | Classify records `is_free` first, then strips the suffix. |
| 6 | One fetch call breaks once the window passes 366 days (January 2027) | Fetch splits any window into chunks of up to 366 days and joins them. |
| 7 | Title and subtitle were hard-coded | Spec retitled for the wider scope. Every headline, subtitle and date range is filled from the data. |

## Decision sign-off changes (Oct 7, 2026)

The time window decision changed from "2026 year to date" to **rolling 52 weeks**. That replaces two v3 resolutions:

- **Gap 2 (partial week):** every charted week is a full Monday–Sunday week, so the partial-week label is no longer used. It only comes back under the fallback below.
- **Gap 6 (chunking):** fetch downloads the 52 full weeks plus any days of the current week up to yesterday (needed for the freshness check). On a Monday that is 364 days and one call; later in the week it can pass 366 days, so fetch still splits the window into chunks.
- **Fallback (not needed):** step 2 confirmed the daily dataset starts on 2025-01-01, so the full rolling window is available. The fallback was: if the API has no daily data before 2026-01-01, the window starts at 2026-01-01 and grows each week until 52 full weeks exist (about January 2027), then rolls. While that holds, Jan 1–4 is charted and labeled "partial week."

## Goal and audience

One command, run every Monday, produces an accurate breakdown of OpenRouter token usage over the last 52 complete weeks (rolling window). It splits usage by open vs closed weights, company, model family, country and six more dimensions. Each dimension feeds its own LinkedIn-ready chart.

- **Audience:** AI and operations leaders scrolling LinkedIn on a phone. Most are not data scientists.
- **Success test:** a reader gets the main point in 3 seconds without reading the caption.
- **Stable means:** same look, same method and same file names every week. Only the data changes.
- **Out of scope:** automatic posting to LinkedIn. Dan reviews and posts by hand.

## Accuracy standard

A run is **READY TO POST** only when all five rules pass. The run always finishes; a failed rule puts **NOT READY TO POST** at the top of `run_report.md` with the reason.

| Rule | Target | How it's checked |
| --- | --- | --- |
| Every named model is labeled | 100% of top-50 tokens have a value on every required dimension; zero "unknown" | `checks.py`, every run |
| Long tail is disclosed | The "other" share is printed on every chart | Footer shows "Top-50 coverage: x%" |
| Matches OpenRouter | The week's top 5 models match openrouter.ai/rankings, token totals within 1% | Dan spot-checks the first Monday of each month and ticks it in the report. The run can't see the tick, so this rule doesn't change the READY status; on those Mondays, Dan ticks it before posting |
| Every label has a source | Each registry field says where it came from: catalog, rule, or manual with a link | Test fails if a source is blank |
| Same input, same output | Rerunning on saved raw data gives identical numbers | Automated test, plus a re-aggregation check in every run |

**Required dimensions** for phase 1 are weights and company. Each later dimension becomes required in the phase that adds it.

**What this data can and can't say:** it covers public traffic on OpenRouter only. Private models, private endpoints and zero-data-retention traffic are excluded at the source, and consumer apps like ChatGPT aren't in it. Every post says "on OpenRouter," never "worldwide."

## Weekly outputs

Each run writes one folder named for the last complete data week (ISO week, Monday start, UTC), so past weeks are never overwritten. A run on Mon Oct 12 2026 writes `output/2026-W41/`. Rerunning the same week overwrites only that week's folder.

| File | What it is | Used for |
| --- | --- | --- |
| `charts/{dimension}_{chart}_square.png` | 1080 x 1080 px, one per chart in the content library, e.g. `weights_share_square.png` | Main LinkedIn image |
| `charts/{dimension}_{chart}_portrait.png` | 1080 x 1350 px version of each chart | Taller feed version |
| `weekly.csv` | Tokens and share per week, one row per dimension + value, plus the "other" row | Checking numbers, sharing data |
| `monthly.csv` | Same, per calendar month | Monthly recap posts |
| `caption.md` | One draft post per chart, this week's numbers filled in | Starting point for the post |
| `run_report.md` | READY / NOT READY, each accuracy rule, each check, coverage, new models, blank registry fields | Dan's review before posting |
| `meta.json` | The API `meta` block (`as_of`, start and end dates) and the list of raw files used | Proof and reruns |

Raw API responses are saved once in `raw/` by date (see Data pipeline) rather than copied into each week folder. Captions are templates with blanks filled from the data, such as the latest share and the change since last week; Dan edits the wording before posting.

## Data pipeline

The pipeline makes 4 OpenRouter calls and runs 5 steps, each in its own small Python file so one can be fixed without touching the others.

1. **Fetch.** Call `GET /api/v1/datasets/rankings-daily` for the rolling window: from the Monday 52 weeks before the last complete week through the last completed UTC day (see the fallback under Decision sign-off changes). If the window is longer than 366 days, split it into chunks of up to 366 days and join them. Save each raw response to `raw/YYYY-MM-DD/`.
2. **Catalog.** Call `GET /api/v1/models` for each model's details (such as `hugging_face_id`, `created`, pricing, supported parameters, input modalities). Also save this week's task-type snapshot (`/api/v1/classifications/task`) and top apps (`/api/v1/datasets/app-rankings`). All saved to `raw/YYYY-MM-DD/`.
3. **Classify.** For each model ID: record `is_free` from the `:free` suffix, then strip the suffix so variants count with their base model. Look up the base model in the registry and attach every dimension. Add new models to the registry and list blank fields for review.
4. **Aggregate.** For each dimension, sum tokens per value per week and per month. Share = a value's tokens / all labeled tokens.
5. **Render.** Build the charts, CSVs, captions, `meta.json` and run report from the aggregated tables.

**Confirmed in build step 2 (Oct 7, 2026), from the live docs and API:**

- Endpoint names match: `/datasets/rankings-daily`, `/models`, `/classifications/task`, `/datasets/app-rankings`. Limits are 30 calls per minute and 500 per day.
- Daily rankings start on 2025-01-01, cover the top 50 models per day plus one `other` row, and reject windows over 366 days.
- Rankings rows name models by `model_permaslug` (e.g. `openai/gpt-4o-2024-05-13`). This matches the catalog's `canonical_slug` field, not its `id`. Classify (step 3) joins on `canonical_slug`.
- Rankings rows do tell free traffic apart: free variants appear as `{permaslug}:free` (e.g. `deepseek/deepseek-r1-0528:free`). Classify records `is_free`, strips the suffix, then joins on `canonical_slug`. In the catalog, `:free` appears only in `id`.
- First real fetch (Oct 7, 2026): 366 days with exactly 51 rows each (top 50 + `other`), 278 distinct model slugs. `other` is 6.7% of tokens.
- After stripping `:free`, 66 slugs (9.8% of tokens) are not in today's catalog, so step 3 labels them by hand. 5.2% of tokens are stealth models (`stealth/...`, `openrouter/...-alpha`), whose company and weights are undisclosed; last week's #1 model was `stealth/space-bunny-alpha`. The other 4.6% are retired models such as `x-ai/grok-code-fast-1`.
- Rankings and app rankings need the API key; the model catalog is public.
- The data is licensed CC BY 4.0. Charts carry the citation line; files that republish the data itself (such as a shared `weekly.csv`) also add "Licensed under CC BY 4.0."

**Fixed method (never changes week to week):**

- Weeks run Monday to Sunday, UTC. The current unfinished week is always dropped.
- The window is the last 52 complete weeks. No partial weeks are charted, except Jan 1–4 2026 under the fallback, labeled "partial week."
- In `monthly.csv`, the first month is usually partial and is marked that way.
- Variants like `:free` count with their base model; the free flag is kept as its own dimension.
- Tokens are used as reported. Providers use different tokenizers, so posts compare shares and trends, not exact totals, and the footer says so.
- Labels come only from the registry, never guessed at run time.

**API limits:** the run uses 4 calls (5 when the window is split). OpenRouter allows 30 calls per minute and 500 per day, so reruns are safe. Endpoint names and limits are confirmed against the live API in build step 2.

## Model registry and dimensions

Every fact about every model lives in a permanent registry of three CSV files Dan can open in Excel. A model's labels change only when Dan changes them, which keeps history stable even after a model leaves the catalog.

| Dimension | Example values | Where it comes from | Phase |
| --- | --- | --- | --- |
| Weights | Open, closed, stealth | Manual label, else Hugging Face ID, else lab default (rules below) | 1 |
| Company | DeepSeek, Anthropic, Google | Model ID prefix (`deepseek/...`), cleaned in `labs.csv` | 1 |
| Country of company | China, US, France | `labs.csv`, entered once per company | 2 |
| Model family | Claude Sonnet, Gemini Flash, Qwen | Pattern rules in `families.csv` | 2 |
| Release date | 2026-03-02 | Catalog `created` field | 2 |
| Price tier | Budget, mid, premium | Catalog price per million tokens, fixed cutoffs (see Decisions) | 2 |
| Reasoning | Yes, no | Catalog supported parameters | 2 |
| Input type | Text only, multimodal | Catalog input modalities | 2 |
| Free variant | Yes, no | `:free` suffix, recorded before the suffix is stripped | 2 |
| Size (open models only) | Small, medium, large | Manual, from the model card | 3 |

**Registry files:**

- `models.csv`: one row per base model ID, a column per dimension, a `{field}_source` column for each (catalog, rule, or manual + link), and `first_seen`.
- `labs.csv`: one row per company: ID prefix, clean name, country, default weights (open, closed or blank).
- `families.csv`: one row per family: a text pattern (such as `claude-sonnet`) and the family name. Patterns are checked top to bottom; the first match wins.

**Weights rule, in order:** a manual label in `models.csv` wins; else a Hugging Face ID means open; else a lab default of closed (or stealth) in `labs.csv` applies; else unknown, which goes on the review list and marks the run NOT READY.

**Rules added in build step 3 (Oct 7, 2026):**

- **Stealth models** (`stealth/...` and OpenRouter's cloaked `openrouter/...-alpha` models) get company "Stealth (undisclosed)" and weights "stealth". These count as labeled, so they don't make a run NOT READY. The open vs closed chart leaves them out and its footer says so, e.g. "Excludes stealth models (x%)". The company leaderboard shows "Stealth (undisclosed)" as its own bar. When a stealth model's maker is revealed, Dan updates its row once and its whole history re-labels.
- **Hosted versions of open weights count as open.** An API model that its maker describes as a hosted version of an open-weight model (e.g. Qwen3.5 Plus = Qwen3.5-397B with serving extras) is labeled open, with the open model's Hugging Face page as its source.
- **Open means the weights for that model are downloadable.** An open sibling (another size or version) doesn't make a model open.
- Any `:variant` suffix (e.g. `:free`, `:thinking`) is stripped so variants count with their base model; only `:free` sets `is_free`.
- Manual labels marked "low confidence" in their source are re-checked monthly. `inclusionai/ling-3.1-flash` (closed; open weights reportedly planned) is due for a re-check around Oct 20, 2026.

New models found each week are added to `models.csv` automatically with every field the catalog can fill. The run report lists the blanks for Dan.

**Kept separate:** task types (coding, web search, etc.) and top apps don't split by model per day, so they are saved weekly in `raw/` and charted on their own. Task data covers only the last 7 days, so saving starts in phase 1 to build history.

## Chart design

The main chart is a 100% stacked area of weekly token share: open-weight on the bottom, closed-weight on top, with a dashed 50% line. Every other chart in the library uses the same frame, fonts and colors.

| Element | Content | Style |
| --- | --- | --- |
| Headline | The finding, written from the data, e.g. "Open-weight models now carry {share}% of OpenRouter tokens" | Bold, 44 px, left-aligned |
| Subtitle | "Weekly share of tokens, {dimension}, {first month} {year} to {last month} {year}" | Regular, 24 px, grey |
| Chart area | x = week, y = 0 to 100% | About 65% of the image height |
| 50% line | Dashed reference line (two-way splits only) | Thin, dark grey |
| Crossover marker | Dot and short label on the week a band passed 50% and stayed above it ("Above 50% since Apr 27"). A short blip over 50% that falls back (Feb 2026) isn't marked | Only if the band is above 50% now |
| Partial week | Only under the fallback: Jan 1–4 point marked with a light hatch and "partial week" note | Small, grey |
| End labels | Latest share of each band at its right edge | Bold, in a darker shade of the band color so the text stays readable (blue `#006F90`, grey `#6B675F`) |
| Footer left | "Source: OpenRouter (openrouter.ai/rankings), as of {as\_of}. Top-50 coverage {x}%. Shares, not exact token counts." The open vs closed chart adds "Excludes stealth models ({x}%)." | 16 px, grey |
| Footer right | "Created by Daniel Wipert \| Chorus AI Systems" | 16 px, charcoal |

**Style rules:**

- Brand colors are Chorus AI Systems: blue `#0088B0`, magenta `#D5006C`, yellow `#F2C400`, charcoal `#1F1E1C`.
- Two colors for two-way splits: Chorus blue `#0088B0` (open) and soft warm grey `#BDB7AC` (closed, picked in step 6; color-blind separation ΔE 18 against the blue). Magenta is the accent for the crossover marker. All text is charcoal. Yellow is never used for text on white (contrast 1.7:1).
- Blue and magenta are never used as a two-way pair, because they look alike to people with red-blindness (protanopia). Multi-value charts use a fixed palette of 7 (top 6 + "all others" in grey). All colors pass a color-blind check.
- No legend box; end labels name the bands.
- Light horizontal gridlines at 25%, 50%, 75%. No vertical gridlines, no border.
- X-axis labeled by month (Jan, Feb, Mar), not by week.
- Font: Inter, stored in `fonts/` so it renders the same on any computer.
- White background, exported at 1080 x 1080 and 1080 x 1350 px.
- Every size, color and text string lives in `style.yaml`, so the look changes without touching code.

**Redesign (Oct 7, 2026, step 6):** Dan asked for a bolder, magazine-style look (Bloomberg Businessweek as the reference). This replaces the plain header and colors above:

- Chorus color stripe (blue, magenta, yellow) across the top edge.
- Small all-caps kicker (e.g. "OPEN VS CLOSED · OPENROUTER") in yellow (dark theme) or magenta (light theme).
- A huge hero number (Inter Display Black, 200 px) with the headline set beside it, e.g. "72%" + "of tokens now run on open-weight models".
- Callouts with thin leader lines on the chart: the 50% crossover (magenta dot) and the peak.
- Minimal axes: no y-axis; a labeled dashed 50% line; month labels only.
- Footer: source line on the left; the Chorus ring mark with "Daniel Wipert / Chorus AI Systems" on the right.
- Two themes in `style.yaml`: **dark** (charcoal background, cream text) and **light** (cream background with a charcoal header block). The `theme:` line picks one.

**Color pass (Oct 7, 2026):** Dan asked for more color, still sleek and very clear. This replaces "one strong, one muted":

- Open band: Chorus blue as a vertical gradient (dark at the bottom, bright at the top). Closed band: Chorus yellow `#F2C400` (dark theme) or deeper gold `#DDA600` (light theme; brand yellow is too pale on cream). Blue vs yellow is the most color-blind-safe pair (ΔE 24-30 in every color-blindness simulation).
- End values sit in pills filled with their band color; the kicker is a magenta (dark) or yellow (light) pill.
- Notes on the chart, the 50% line and its label are charcoal, so they read on the yellow band.
- Leaderboard bars use a blue-to-magenta gradient across the full width (longer bars reach further into magenta). The stealth bar is hatched grey. The leading named company's value sits in a yellow (dark) or charcoal (light) pill. Up/down arrows are blue/pink and always carry the ▲/▼ symbol, so the color is never the only cue.
- Leaderboard: top 8, rank numbers, the name above each thick bar, the value at the bar's end, the change at the right; the leading named company is highlighted.

**Company leaderboard (step 6):** top companies for the latest week, largest first, with the change in share points vs 4 weeks earlier ("new" if the company had no share then). "Stealth (undisclosed)" is a grey bar. If stealth is #1, the headline names the top named lab instead ("DeepSeek leads named labs on OpenRouter with 23.5% of tokens"). Headline numbers match the bar labels.

**Built with:** matplotlib. It is stable, needs no browser, and gives exact control over every element.

## Content library

Every run builds every chart whose dimension is live, so Dan can post on news as it happens.

| Chart | Used for | Shape | Phase |
| --- | --- | --- | --- |
| Share over time | Weights, reasoning, free variant, input type | 100% stacked area, as designed above | 1 (weights), 2 (rest) |
| Leaderboard | Company, family, country | Ranked horizontal bars for the latest week, change vs 4 weeks earlier | 1 (company), 2 (rest) |
| Share race | Company, family | Top 6 + "all others" as a 100% stacked area | 2 |
| Rank changes | Company, family | Bump chart of weekly rank, top 8 | 2 |
| Launch curve | Release date | Each new model's share by weeks since launch, aligned at week 0 | 3 |
| Task mix | Task types | Bars of token share by task, latest week | 3 |

**Posting rotation (4 weeks):** week 1 open vs closed, week 2 company leaderboard, week 3 country share, week 4 a rotating topic (family race, launch curve or task mix).

## Stability and quality checks

A hard check stops the run with a plain-English message. A soft check lets the run finish but is listed in `run_report.md`; any failed accuracy rule also sets NOT READY TO POST.

| Check | Type | Rule |
| --- | --- | --- |
| API key present | Hard | `OPENROUTER_API_KEY` is set (GitHub secret in Actions, or `.env` if run locally) |
| API responds | Hard | Status 200; retry up to 3 times, 10 seconds apart, on errors or 429s |
| Data is fresh | Hard | `meta.end_date` is within 2 days of today |
| No missing days | Hard | Every day from the window start to the end date has rows |
| Labels complete | Soft + NOT READY | Zero unknown values on required dimensions |
| Sources complete | Soft + NOT READY | No blank `_source` field for a filled value |
| Coverage | Soft | Warn if labeled tokens are under 80% of all tokens |
| Big jump | Soft | Warn if any two-way share moves more than 10 points in the latest week |
| History restated | Soft | Warn if any past week's share moved more than 1 point since the previous run (OpenRouter may restate figures). The previous run's figures are rebuilt from its `raw/` folder with today's registry, so a label change doesn't look like a restatement |

**Code stability rules:**

- Exact library versions pinned in `requirements.txt`.
- API key only in the `OPENROUTER_API_KEY` GitHub secret (or `.env` for a local run), never in code; `.env` listed in `.gitignore`.
- The `meta` block saved with every output, as OpenRouter asks.
- Tests check classify and aggregate against saved sample data, so changes can't quietly break the math.

## Running it weekly

Everything runs on GitHub Actions; nothing is installed on Dan's computer (changed Oct 7, 2026). Until there are 4 clean weeks, Dan starts each Monday run by hand with the **Run workflow** button; after that, it runs on a schedule. Monday is used because the previous Monday-to-Sunday week is complete by then.

**Phase 1 and 2, started by hand:** on GitHub, open **Actions**, pick the weekly workflow, and click **Run workflow**. It runs `python run_weekly.py` in the cloud.

Then: open `run_report.md` in the repo, confirm READY TO POST, look at the charts on a phone, edit `caption.md`, post.

**Phase 3, automatic (optional):**

| Option | How it works | Good | Watch out |
| --- | --- | --- | --- |
| Scheduled task | cron (Mac) or Task Scheduler (Windows) runs Mondays 8 a.m. Central | Simple, nothing new to learn | Runs only if the computer is on |
| GitHub Actions | Free scheduled cloud job saves outputs to the repo | Runs with the laptop off | Needs a repo and the key stored as a secret |

## Project folder structure

One folder holds everything; each pipeline step is its own small file.

```text
openrouter-usage/
  run_weekly.py        runs all steps in order
  fetch.py             steps 1-2: API calls, chunking, retries, saves raw files
  classify.py          step 3: free flag, joins to registry, adds new models
  aggregate.py         step 4: weekly and monthly totals per dimension
  charts/              step 5: one file per chart type (share, leaderboard, race, bump, launch, tasks)
  write_outputs.py     step 5: CSVs, captions, meta.json, run report
  checks.py            hard checks, soft checks, accuracy standard
  registry/
    models.csv         one row per base model, every dimension + sources
    labs.csv           one row per company: name, country, default weights
    families.csv       family name patterns, first match wins
  style.yaml           colors, fonts, sizes, text
  captions/            one post template per chart type
  fonts/               Inter font files
  tests/               sample data and tests
  raw/YYYY-MM-DD/      every API response and catalog, by fetch date
  output/2026-W41/     one folder per data week
  .env                 API key (never shared)
  .gitignore           keeps .env out of git
  requirements.txt     pinned libraries
```

## Build plan

The build runs in three phases after a sign-off gate, so Dan can post from phase 1 while later dimensions are added. Every step ends with a check Dan can run and see; a step is done only when its check passes.

**Gate: spec sign-off**

- [x] **0. Approve the six decisions** in the table below. Check: every row says Approved or Changed. Done Oct 7, 2026.

**Phase 1: accurate open vs closed and company charts**

- [x] **1. Set up the folder.** `requirements.txt`, `.gitignore`, the `OPENROUTER_API_KEY` GitHub secret, and a **Setup check** GitHub Actions workflow. Check: the Setup check run is green (it runs `python -c "import pandas, matplotlib"` and confirms the secret exists). Done Oct 7, 2026.
- [x] **2. Fetch.** `fetch.py` for all four endpoints, with chunking and retries. Check: raw files appear in `raw/` with today's date, endpoint names and limits match the live docs, and we know how far back daily data goes (this decides the rolling window or the fallback). Done Oct 7, 2026.
- [x] **3. Registry.** `classify.py`; fill `labs.csv` and weights for every company in 2026's top 50. Check: zero unknown weights or companies. Done Oct 7, 2026: 254 models (194 by rule or catalog, 60 by hand with source links), 0% unknown.
- [x] **4. Aggregate.** `aggregate.py`. Check: open share is roughly 41% in mid-March and past 50% by early June, and the latest top 5 match openrouter.ai/rankings. Done Oct 7, 2026: 42.4% open in the week of Mar 16, above 50% every week since Apr 27; Dan confirmed the top 5 match.
- [x] **5. Checks.** `checks.py`. Check: a wrong key stops the run with a clear message, and a blank label sets NOT READY. Done Oct 7, 2026: a wrong key against the live API stops with "OpenRouter rejected the API key"; tests cover every hard check, NOT READY on a blank label or source, and each warning.
- [ ] **6. First charts.** Weights share over time and company leaderboard. Check: Dan approves both on a phone.
- [ ] **7. One command.** `run_weekly.py`, captions, run report, `meta.json`, tests. Check: running twice on the same raw data gives identical files.

**Phase 2: more dimensions**

- [ ] **8. Country and family.** Fill country in `labs.csv`; write `families.csv`. Check: zero blanks.
- [ ] **9. Catalog dimensions.** Release date, price tier, reasoning, input type, free variant. Check: every value has a source.
- [ ] **10. More charts.** Share race, rank changes, country leaderboard, extra share-over-time charts. Check: Dan approves each.

**Phase 3: extra content and automation**

- [ ] **11. Size, launch curve, task mix.** Check: at least 4 weekly task snapshots exist.
- [ ] **12. Schedule it.** GitHub Actions, with the API key stored as a repo secret. Check: 2 unattended runs in a row are READY TO POST.

The March and June figures in step 4 come from [an analysis of OpenRouter daily data](https://capitalandcompute.net/blog/open-source-llms-overtake-2026/); they are a sanity check, not a target.

## Decisions

Six choices need Dan's sign-off before build step 1. Each has a proposed default; set Status to Approved, or to Changed and edit the default cell.

| Decision | Proposed default | Other options | Status |
| --- | --- | --- | --- |
| Branding in footer | "Created by Daniel Wipert \| Chorus AI Systems" | Leucothea Consulting, Chorus AI, or a newsletter name | Changed |
| Brand colors | Chorus AI Systems palette: open = blue `#0088B0`, closed = soft warm grey (hex picked in step 6), accent = magenta `#D5006C`, text = charcoal `#1F1E1C` | Neutral pair picked in step 6 | Changed |
| Time window | Rolling 52 weeks; if the API has no data before 2026-01-01, start there and roll once 52 weeks exist | 2026 year to date, or from Jan 2025 | Changed |
| Price tier cutoffs | Budget under $0.50, mid $0.50–$5, premium over $5 per million tokens (input and output averaged) | Dan's own cutoffs, fixed once set | Approved |
| Country of a company | Headquarters | Where it was founded, or the parent company's country | Approved |
| Run location | GitHub Actions for every run: started by hand with the Run workflow button until 4 clean weeks, then scheduled | Manual on Dan's computer, or scheduled task | Changed |

Once all six rows are Approved or Changed, this spec is final and build step 1 starts.

## Sources

- [OpenRouter Data API documentation](https://openrouter.ai/docs/cookbook/administration/data-api)
- [Open-Source LLMs Overtook Proprietary in 2026, Capital and Compute](https://capitalandcompute.net/blog/open-source-llms-overtake-2026/)
- Spec v2 (Oct 6, 2026), `Spec_Weekly_OpenRouter_Open_vs_Closed_Chart.md`
