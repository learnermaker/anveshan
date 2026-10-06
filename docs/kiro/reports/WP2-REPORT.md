# WP2 Report — Universal Pipeline: Layer 2 + Layer 3

**Status:** DONE · **Date:** 2026-10-06 · **Branch:** kiro/wp2-universal

## Done

1. `tracks/common/goals/universal.py` — `PAYLOAD_MODEL = SkillModel`, `ui_view(payload)`.
2. `tracks/common/prompts/` — 4 prompt files: `structure_skill_v1.txt`, `judge_final_v1.txt`, `judge_step_v1.txt`, `relevance_v1.txt`.
3. `tracks/track-a/src/track_a/universal.py` — `propose_skill_model` (deterministic composition + optional wording call). Lazy import of `tracks.common.perceivers`.
4. `tracks/track-a/src/track_a/goals/universal.py` — `build()` builder. Requires confirmed `CaseProfile`. Loads source perception from `knowledge/perception_source.v1.json`. Produces valid grounded claims (observed with locators, inferred ≤ 0.5), criterion templates with `CRIT-U-*` ids.
5. `tracks/track-b/src/track_b/evaluators/universal_align.py` — `label_frames`, `mode_filter`, `needleman_wunsch`. All deterministic.
6. `tracks/track-b/src/track_b/evaluators/universal.py` — `evaluate()`: kind gate → perceive attempt (lazy) → quality gate → relevance gate → per-structure checks → specialists (prefixed metrics) → `TrajectoryResult`.
7. `tracks/track-a/src/track_a/api.py` — `build_case` extended for `modality="universal"`: loads `knowledge/case_profile.v*.json`, passes `profile=` via `inspect.signature`.
8. Tests (361 total, all pass): `test_universal_build.py` (9 tests), `test_universal_eval.py` (23 tests), `test_universal_session_e2e.py` (2 tests).

## Tests

```
153 passed, 1 skipped  (tracks/common + track-a)
143 passed, 1 skipped  (track-b)
 65 passed             (service)
----------------------------------
361 passed, 2 skipped  TOTAL
```

Governance, case-packs, contract parity: all PASS.

## Live results

Skipped per wave2-master-spec.md §4.3 (WP2 Phase A budget: none). Live checks move to WP5 step 3.

## Deviations

- Session e2e test monkeypatches `track_b.api.ACCEPTED_KINDS` to add `"universal"` — WP5 must add this to the real `track_b/api.py`.
- `tracks.common.perceivers` does not exist yet (WP1 creates it); all WP2 modules use lazy imports + injected fakes in tests.

## Requests for WP5

1. Add `"universal": ("trace", "image", "audio", "video")` to `ACCEPTED_KINDS` in `tracks/track-b/src/track_b/api.py`.
2. Wire WP2 to the real `tracks.common.perceivers.perceive` (per spec §5 step 2).
3. Run `test_universal_session_e2e.py::TestUniversalSessionE2E::test_baseline_then_perfect_retry` with real embeddings to verify the full bundle validation path.

## Open issues

- `_apply_wording` in `universal.py` uses `model_copy(update=...)` on SkillModel — this re-validates. If a wording call returns a check_id not in the model, it is silently ignored (correct per spec: "Apply only to existing check ids").
- Line-art specialist `payload_from_image` may fail on non-kolam images; failure is caught and a warning is added (no silent fallback).
