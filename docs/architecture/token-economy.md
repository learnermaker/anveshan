# Token economy (Gemini calls)

Status: IMPLEMENTED (gateway, 2026-10-07). Live quality of `auto` media resolution: PROPOSED until a live A/B is recorded.

All model calls go through `tracks/common/models.py` (`ModelGateway`); rules are in the [model-gateway skill](../../.claude/skills/model-gateway/SKILL.md). This page records how calls are kept cheap and how to measure them.

## How Gemini 3 bills inputs

- **Images** are billed by media resolution, not pixels: 280 tokens (low), 560 (medium), 1120 (high, the default), 2240 (ultra high).
- **Video frames** cost 70 tokens at low or medium and 280 at high.
- **Thinking tokens** are billed as output. Flash-Lite defaults to minimal thinking.
- `max_output_tokens` caps thinking and answer together.

Consequence: shrinking an image below the size the resolution level needs saves nothing by itself. The image is sent at a matching resolution level.

## What the gateway does

| Practice | Where | Effect |
|---|---|---|
| Never call when a stored answer exists | live cache (`ANVESHAN_LIVE_CACHE`), recorded replay mode | Repeated uploads, demo and samples cost 0 |
| Shared daily call budget | `DailyBudget`, `ANVESHAN_DAILY_CALL_BUDGET` | Caps spend on the shared key; bring-your-own-key calls are exempt |
| Deterministic paths with no model | Kolam geometry, Tabla onsets, scoring | No calls for scoring at all |
| Downsize before sending | video perceiver 256 px (embeddings) / 384 px (keyframes); image perceiver 768 px; universal evaluator 512/320 px; `sample_frames` 384 px | Smaller uploads and the right resolution level |
| **Media resolution by size** | `media_resolution_for`, `ANVESHAN_MEDIA_RESOLUTION` | `auto`: up to 384 px → low (280), up to 768 px → medium (560), larger → high. Calls with ~20 frames drop from ~23k to ~6k image tokens. Only for `gemini-3*` models. If a model rejects the setting, the call is resent once without it (note `media_resolution_unsupported_retried_without`). |
| **Output cap** | `max_output_tokens()`, `ANVESHAN_MAX_OUTPUT_TOKENS` (default 4096, 0 = off) | Longest recorded answer is ~1.8k tokens; the cap stops runaway output and thinking |
| Batch frames and embeddings | frame batching; `embed(batch_size=16, dims=768)` | Fewer calls, small vectors |
| temperature 0, JSON mode | `generate_json` | No retries for unparsable output in the normal path |
| **Record usage** | `raw_response.json` → `usage` (prompt, output, thinking, cached, total) | Cost is measured, not guessed |

Recorded runs stay valid: the replay key hashes model, prompt version, system text and input bytes only. Resolution and output cap are config, not part of the key.

## Measuring

```bash
.venv/Scripts/python tools/token_report.py
```

The report groups runs by model and prompt and shows input, output, thinking and cached tokens per run. Runs recorded before 2026-10-07 show as "no usage".

## Future options (not done; each changes inputs, so golden runs must be re-recorded)

- Put stable content (system text, reference frames) first so implicit context caching can apply.
- `response_schema` instead of free JSON to shorten answers.
- Fewer frames for embeddings (59–73 per call today).

Do these only after the K9 merge, with re-recorded goldens and a quality check.
