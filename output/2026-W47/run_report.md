# READY TO POST (2026-W47)

- **PASS** Labels complete: Zero unknown values on company, weights, country, family, release_date, price_tier, reasoning, input_type, size
- **PASS** Sources complete: Every label has a source
- **PASS** Same input, same output: Re-aggregating the same data gave identical numbers
- **PASS** Long tail disclosed: Top-50 coverage for the footer: 95.3%
- **PASS** Coverage: Labeled tokens are 95.3% of all tokens in the latest week (warn under 80%)
- **PASS** Big jump: Open share moved +6.3 points in the latest week (warn over 10)
- **PASS** History restated: No past week's share moved more than 1 point
- [ ] Dan: on the first Monday of the month, the top 5 match openrouter.ai/rankings (token totals within 1%)

## New models this week

- google/gemini-4-hydrogen-20261112: Google, closed (rule: labs.csv default for google)
- google/gemini-4-neon-20261118: Google, closed (rule: labs.csv default for google)
- openai/gpt-6.2-sol-20261117: OpenAI, closed (rule: labs.csv default for openai)
- qwen/qwen4-max-20261115: Alibaba, closed (manual: https://finance.yahoo.com/technology/ai/articles/alibaba-qwen4-max-won-t-000611623.html (API only; Alibaba says Qwen4-Max will not be open-weights; no Qwen4 repo under Qwen on Hugging Face as of Nov 23; only smaller Qwen4 models are promised as open))
- tencent/hy4-flash-20261116: Tencent, open (catalog: hugging_face_id tencent/Hy4-flash)
- thinkingmachines/inkling-2-mini-20261120: Thinking Machines Lab, open (catalog: hugging_face_id thinkingmachines/Inkling-2-Mini)

## Blank registry fields

- None

## Low-confidence labels to re-check monthly

- baidu/ernie-5.5-flash-preview-20261110
- inclusionai/ling-3.2-flash-20261113
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

Task snapshots saved so far: 9 (the task mix change column needs one from about 4 weeks earlier)
