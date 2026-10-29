# READY TO POST (2026-W43)

- **PASS** Labels complete: Zero unknown values on company, weights, country, family, release_date, price_tier, reasoning, input_type, size
- **PASS** Sources complete: Every label has a source
- **PASS** Same input, same output: Re-aggregating the same data gave identical numbers
- **PASS** Long tail disclosed: Top-50 coverage for the footer: 93.8%
- **PASS** Coverage: Labeled tokens are 93.8% of all tokens in the latest week (warn under 80%)
- **PASS** Big jump: Open share moved +0.0 points in the latest week (warn over 10)
- **PASS** History restated: No past week's share moved more than 1 point
- [ ] Dan: on the first Monday of the month, the top 5 match openrouter.ai/rankings (token totals within 1%)

## New models this week

- minimax/minimax-m3.1-flash-20261019: MiniMax, open (catalog: hugging_face_id MiniMaxAI/MiniMax-M3.1-Flash)
- moonshotai/kimi-k3.1-pro-20261023: Moonshot AI, closed (manual: https://www.marktechpost.com/2026/10/23/moonshot-ai-kimi-k3-1-pro-open-weight-model/ (low confidence: API-only for now; Moonshot promised open weights by Nov 4, 2026; switch to open with size Large (2.8T total parameters) once they are on Hugging Face under moonshotai))
- openai/gpt-6-luna-decisions-20261006: OpenAI, closed (rule: labs.csv default for openai)

## Blank registry fields

- None

## Low-confidence labels to re-check monthly

- inclusionai/ling-3.0-flash-sante-20260904
- inclusionai/ling-3.1-flash-20261002
- moonshotai/kimi-k3.1-pro-20261023
- qwen/qwen3-coder-plus
- qwen/qwen3.5-flash-20260224
- qwen/qwen3.5-plus-20260216
- qwen/qwen3.6-flash
- qwen/qwen3.8-max-20260803
- qwen/qwen3.8-max-20260902
- z-ai/glm-5.3-flashx-20260918

## Charts

- charts/weights_share_square.png
- charts/weights_share_portrait.png
- charts/price_tier_share_square.png
- charts/price_tier_share_portrait.png
- charts/free_share_square.png
- charts/free_share_portrait.png
- charts/input_type_share_square.png
- charts/input_type_share_portrait.png
- charts/reasoning_share_square.png
- charts/reasoning_share_portrait.png
- charts/size_share_square.png
- charts/size_share_portrait.png
- charts/company_leaderboard_square.png
- charts/company_leaderboard_portrait.png
- charts/country_leaderboard_square.png
- charts/country_leaderboard_portrait.png
- charts/company_race_square.png
- charts/company_race_portrait.png
- charts/family_race_square.png
- charts/family_race_portrait.png
- charts/company_ranks_square.png
- charts/company_ranks_portrait.png
- charts/family_ranks_square.png
- charts/family_ranks_portrait.png
- charts/launch_curve_square.png
- charts/launch_curve_portrait.png
- charts/task_mix_square.png
- charts/task_mix_portrait.png

Task snapshots saved so far: 5 (the task mix change column needs one from about 4 weeks earlier)
