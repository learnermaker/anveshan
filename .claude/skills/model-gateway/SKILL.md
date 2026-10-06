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
| `audio` | unset (disabled) | Gemma 26B/31B have **no audio input**. If `ANVESHAN_AUDIO_MODEL` is set (e.g. a Gemini Flash-Lite id), audio criteria may use it; otherwise those criteria return `UNCERTAIN` with reason `audio_model_disabled`. Timing/onsets are always deterministic (`tracks/common/signal.py`). |

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
