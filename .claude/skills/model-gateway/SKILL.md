---
name: model-gateway
description: Rules and code patterns for any Gemma/Gemini model call in Anveshan (Track A extraction/query, Track B observation, service). Use before writing or changing code that calls google-genai, chooses a model, builds a prompt, parses model JSON, or records/replays model runs.
---

# Model gateway rules

## Models (cost-minimal by design)
| Registry key | Default | Notes |
|---|---|---|
| `text_image` | `gemma-4-26b-a4b-it` | Free on AI Studio. Text + images. System instructions OK. |
| `video_frames` | `gemma-4-26b-a4b-it` | Gemma rejects MP4s that carry an audio track. **Never send video files to Gemma**: decode frames with PyAV (`tracks/common/media.py`) and send JPEG frames as images with their timestamps in the prompt. |
| `vision_fast` | `gemini-3.5-flash-lite` | Interactive image/frame perception and checklist judgements (~2.5 s/image, 4 images ~9 s, ~$0.0003/image). Max 4 images per call. |
| `embedding` | `gemini-embedding-2` | `ModelGateway.embed()` — image/frame/text vectors (768-d, unit), recorded as float16 .npy. 5 images ~1.3 s. Video/audio embeddings are expensive: embed frames, not files. |
| `audio` | `gemini-3.5-flash-lite` (via env) | Gemma 26B/31B have **no audio input**. Enabled by default via `.env` (~$0.0003 per 12 s clip); if unset, audio criteria return `UNCERTAIN` with reason `audio_model_disabled`. Gemma 4 26B is slow on images (~43 s) — use it only for offline/batch work. Timing/onsets are always deterministic (`tracks/common/onsets.py`). |

Model ids come from env (`ANVESHAN_TEXT_IMAGE_MODEL`, `ANVESHAN_VIDEO_FRAMES_MODEL`, `ANVESHAN_AUDIO_MODEL`) via the shared registry in `tracks/common/models.py`. Never hard-code a model id elsewhere. Never add silent fallback lists.

## Call pattern
1. Build the prompt from a versioned file (`prompts/<name>_v<N>.txt`); compute `prompt_sha256` of the rendered text.
2. Call `tracks.common.models.generate_json(...)`: temperature 0, asks for JSON; if the model/API rejects `response_mime_type`, it retries once without it and extracts the first JSON object from text. Validate with the Pydantic DTO. Invalid → `MODEL_FAILURE` (never fabricate).
3. Record the run (`run_metadata.json` + `raw_response.json`) through the track's `runs.py`. Key recorded runs by `(prompt_sha256, input sha256s)` so replay is exact.
4. Normalize DTO → common contracts deterministically. Model output never sets scores, observed/inferred state, rubric weights, pass/fail, or gain.

## Modes
- `live`: real call, recorded.
- `recorded`: replay a recorded raw response; a miss raises `REPLAY_MISMATCH`.
- Tests always use `recorded` or pure deterministic code. Mark real-API tests `@pytest.mark.live`.

## Keys
`GEMINI_API_KEY` from `.env` (server only). The browser never sees a key and never calls a model.

## Token economy
Read `docs/architecture/token-economy.md` before adding images, frames or long outputs to a call. In short: downsize images first (the gateway picks the Gemini 3 media resolution from image size), keep the output cap, and check `tools/token_report.py` after live runs.
