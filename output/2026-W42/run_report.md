# READY TO POST (2026-W42)

- **PASS** Labels complete: Zero unknown values on company, weights, country, family, release_date, price_tier, reasoning, input_type, size
- **PASS** Sources complete: Every label has a source
- **PASS** Same input, same output: Re-aggregating the same data gave identical numbers
- **PASS** Long tail disclosed: Top-50 coverage for the footer: 93.0%
- **PASS** Coverage: Labeled tokens are 93.0% of all tokens in the latest week (warn under 80%)
- **PASS** Big jump: Open share moved +0.3 points in the latest week (warn over 10)
- **PASS** History restated: No past week's share moved more than 1 point
- [ ] Dan: on the first Monday of the month, the top 5 match openrouter.ai/rankings (token totals within 1%)

## New models this week

- deepseek/deepseek-v4.1-flash-20261017: DeepSeek, open (catalog: hugging_face_id deepseek-ai/DeepSeek-V4.1-Flash-1017)
- google/gemini-4-argon-20261013: Google, closed (rule: labs.csv default for google)
- meta/muse-wonder-20261012: Meta, closed (manual: https://betanews.com/article/muse-wonder-frontier-model-developers/ (API only; neither Wonder model ships downloadable weights))
- mistralai/mistral-large-4-0-20261006: Mistral AI, closed (manual: https://letsdatascience.com/news/mistral-debuts-large-4-open-weight-model-preview-cbf9e0b5 (low confidence: API-only preview; Mistral plans to release weights in late October 2026, about Oct 27; switch to open with size Large (1.05T total parameters) once they are on Hugging Face))
- nvidia/nemotron-3.5-super-vl-20261015: NVIDIA, open (catalog: hugging_face_id nvidia/NVIDIA-Nemotron-3.5-Super-VL)
- perplexity/pplx-decider-v1.1-27b-20261006: Perplexity, open (manual: https://huggingface.co/perplexity-ai/pplx-decider-v1.1-27b (Apache-2.0 weights on HF))
- typesafe/jev-1.14-20261014: TypeSafe AI, closed (manual: https://openrouter.ai/typesafe/jev-1.14 (API-only structured decision model; no weights on HF))
- xiaomi/mimo-v2.6-pro-ultraspeed-20260921: Xiaomi, open (manual: https://openrouter.ai/xiaomi/mimo-v2.6-pro-ultraspeed (fast serving of the same 1T MiMo-V2.6-Pro checkpoint, whose weights are at huggingface.co/XiaomiMiMo/MiMo-V2.6-Pro-RL))

## Blank registry fields

- None

## Low-confidence labels to re-check monthly

- inclusionai/ling-3.0-flash-sante-20260904
- inclusionai/ling-3.1-flash-20261002
- mistralai/mistral-large-4-0-20261006
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

Task snapshots saved so far: 3 (the task mix change column needs one from about 4 weeks earlier)
