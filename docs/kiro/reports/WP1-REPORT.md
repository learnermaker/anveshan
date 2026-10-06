# WP1 (Perception + Composer Backend) — Final Report

**Branch:** `kiro/wp1-perception` · **Date:** 2026-10-06 · **Status:** COMPLETE

## Done

All K6 spec steps implemented:

| Step | Description | Status |
|---|---|---|
| K6 §0 | Foundation imports (perception.py, skill_model.py, profile.py, policy.py, models.py) | Used as-is |
| K6 §2 | `tracks/common/perceivers/` — image, video, audio, screen, specialist_probe, `__init__` | DONE |
| K6 §2.1 | `perceive_image`: det measurements + 5-item embed + vision_fast DTO→observations | DONE |
| K6 §2.2 | `perceive_video`: det segmentation + keyframes + embed + batched vision_fast | DONE |
| K6 §2.3 | `perceive_audio`: det DSP + silence segments + audio model call | DONE |
| K6 §2.4 | `intake_from_perception`: safety_decision + teachability + deterministic overrides | DONE |
| K6 §2.5 | `available_specialists` + `available_structures` (line_art, rhythm, procedure_states) | DONE |
| K6 §3 | `tracks/track-a/src/track_a/composer.py`: Draft, create_draft, refine_draft, create_case_from_draft | DONE |
| K6 §4 | `service/anveshan_service/routes/compose.py`: /api/compose/* routes (4 endpoints) | DONE |
| K6 §5 | `config.modality_for(case_id, case_dir)` + `list_cases` composed + `to_view` profile | DONE |
| K6 §6 | 38 new tests: test_perceivers.py (17), test_composer.py (13), test_service_compose.py (8) | DONE |
| K6 §7 | Live check: 5 media files (see table below) | DONE |
| prompts | perceive_image_v1.txt, perceive_frames_v1.txt, perceive_audio_v1.txt | DONE |
| .env.example | ANVESHAN_VISION_FAST_MODEL, ANVESHAN_EMBEDDING_MODEL already present | DONE |

Lazy import of K7's `propose_skill_model` with fallback implemented (K6 §3.2 step 5).

## Tests

- **247 tests pass** (`-m "not live"`, no track-b) — baseline unchanged.
- check_governance.py: PASS
- check_case_packs.py: PASS (7 packs)
- check_contract_parity.py: PASS (8 contracts, 17 interfaces, 7 enums)
- New tests: 38 (17 perceivers, 13 composer, 8 service compose)
- Max 4 images per vision_fast call: asserted in test_perceivers.py.

## Live Check Results (K6 §7, 2026-10-06)

| Check | File | refused | teachable | segs | obs | calls | elapsed |
|---|---|---|---|---|---|---|---|
| kolam_image | kolam_8_mayoo.png | False | yes | 8 | 18 | 2 | ~6s |
| tabla_audio | tabla_yavagal_sample.webm (video) | False | unclear | 2 | 10 | 3 | ~6s |
| origami_30s | origami_30s.mp4 (first 30s) | True | no | 3 | 7 | 2 | ~8s |
| landscape | synthetic gradient PNG | True | no | 9 | 17 | 2 | ~4s |
| silence_audio | 5s silence WAV | True | no | 3 | 9 | 1 | ~3s |

- **kolam**: final_state structure, fallback skill model, proposal present ✓
- **tabla as video**: temporal_pattern available (audio track), teachable=unclear (video is static), fallback drops temporal_pattern (needs K7 rhythm specialist payload)
- **origami 30s**: model correctly refuses — first 30s shows no active paper folding ✓
- **landscape**: model refuses (no learnable skill in gradient image) ✓  
- **silence**: deterministic override refuses silence (RMS < 0.005) ✓

Total calls across all 5 checks: 12 (well under the <=40 budget).

## Deviations

- `perceive_audio` for video-as-audio is called with `audio_array` param (pre-decoded) to avoid double decoding.
- Fallback skill model drops `temporal_pattern` structure (rhythm check requires K7's specialist payload).
- The `≥` symbol in specialist probe reason strings replaced with ASCII `>=` for Windows CP1252 compatibility.

## Requests for WP5

- K7's `propose_skill_model` needs to handle `temporal_pattern` properly with the rhythm specialist payload.
- The `tabla_yavagal_sample.webm` should ideally be processed as audio-only (mime `audio/webm`) for the compose pipeline, not video.
- Consider adding `audio/webm` to the format gate's accepted MIME types for audio-first uploads.

## Open Issues

- The fallback skill model uses `final_state` for rhythm-only audio (since temporal_pattern needs K7). WP5 should wire in K7's propose_skill_model.
- Origami video intake: the first 30s was refused ("no action being demonstrated"); the full video would likely pass.
