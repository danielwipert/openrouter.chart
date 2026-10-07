# READY TO POST (2026-W40)

- **PASS** Labels complete: Zero unknown values on company, weights, country, family
- **PASS** Sources complete: Every label has a source
- **PASS** Same input, same output: Re-aggregating the same data gave identical numbers
- **PASS** Long tail disclosed: Top-50 coverage for the footer: 93.9%
- **PASS** Coverage: Labeled tokens are 93.9% of all tokens in the latest week (warn under 80%)
- **PASS** Big jump: Open share moved -1.7 points in the latest week (warn over 10)
- **PASS** History restated: No previous run to compare with
- [ ] Dan: on the first Monday of the month, the top 5 match openrouter.ai/rankings (token totals within 1%)

## New models this week

- anthropic/claude-sonnet-5.5-20260928: Anthropic, closed (rule: labs.csv default for anthropic)
- inclusionai/ling-3.1-flash-20261002: inclusionAI (Ant Group), closed (manual: https://openrouter.ai/inclusionai/ling-3.1-flash (low confidence; not on HF yet; open weights reportedly planned after free trial))
- openai/gpt-6.1-sol-20260929: OpenAI, closed (rule: labs.csv default for openai)
- upstage/solar-mini4-20260922: Upstage, closed (manual: https://openrouter.ai/upstage/solar-mini4 (no weights on HF under upstage (only tokenizers and Solar Open)))

## Blank registry fields

- None

## Low-confidence labels to re-check monthly

- inclusionai/ling-3.0-flash-sante-20260904
- inclusionai/ling-3.1-flash-20261002
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
- charts/company_leaderboard_square.png
- charts/company_leaderboard_portrait.png
