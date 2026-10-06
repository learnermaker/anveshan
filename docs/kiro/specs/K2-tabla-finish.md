# K2: Tabla finish (real build, eval on committed goal, DSP hardening, end-to-end session)

Read `docs/kiro/specs/00-COMMON.md` first. Folder `...\anveshan-wt\k2-tabla`, branch `kiro/k2-tabla`. No API key needed: the audio model stays disabled.

## Current state (merged)
- **Source:** Wikimedia "A man playing tabla in village pranpur near Chanderi.webm" (CC BY-SA 4.0, by Manishontop02), 34.6 s, window **20.0–32.0 s**, `src.tabla.demo.v1` (see `tracks/cases/tabla/source/source.json`).
- `tracks/common/tabla_dsp.py`: pulse, cycle, coarse alignment plus DTW, robust fit, bass threshold.
- `tracks/common/goals/tabla.py`: payload and `ui_view`.
- `tracks/track-a/src/track_a/goals/tabla.py`: `build()`.
- `tracks/track-b/src/track_b/evaluators/tabla.py`: `evaluate()`.
- Prompt: `tracks/track-a/prompts/tabla_bols_v1.txt`, used only if the audio model is enabled.
- **Goal numbers:**
  - 53 strokes, pulse 0.1893 s, shown as 158.5 BPM (2 pulses per beat, a display convention);
  - bass cycle 12 pulses (pattern `BBB--.B---B-`), bass on 21/53 strokes;
  - IOI CV 0.113, so the STEADY bands were widened to 0.141 / 0.226 with a warning.
- **Eval** (`tracks/track-b/eval/tabla/`): onset F1 0.998 on synthetic; first divergence 6/6; statuses 36/36.
- **Gaps:**
  - no committed goal (`make_synthetic.py` calls the Track A builder itself);
  - `onsets.py` normalises by its own peak, so it finds "onsets" in a pure tone;
  - the bol prompt is read across tracks;
  - TIMING uses only the median, which misses sparse large errors;
  - nobody has listened to the window.

## Files you own
- All Tabla files above.
- `tracks/common/onsets.py` and its tests in `tracks/common/tests/test_foundation.py` (only to add an absolute floor; keep the existing behaviour for normal audio).
- `tracks/cases/tabla/**`.
- `tracks/track-b/eval/tabla/**`.
- The Tabla tests.
- The Tabla table in `docs/plans/evaluation-core.md` §5.2.

## Steps
1. **Listening clip for Jim:** write `var/kiro/tabla_window_20-32s.wav`, plus a 3× slowed copy. Then ask Jim to listen and confirm it is clean tabla, roughly a steady repeating pattern. Record his answer in the report. If he rejects it, stop and report: don't pick a new source yourself; Claude Code decides.
2. **Absolute onset floor:** in `onsets.py`, add an absolute minimum spectral-flux energy (relative to RMS or a fixed dB floor) so a pure tone or near-silence yields no or very few onsets. Add a test (pure 440 Hz tone gives ≤ 1 onset) and keep the click-track tests passing. Re-run the Tabla eval to confirm the numbers don't regress. Then decide whether the evaluator's percussive-contrast workaround is still needed; keep it if it is harmless.
3. **Shared prompt location:** move the bol prompt to `tracks/common/prompts/tabla_bols_v1.txt` and update both tracks to read it from there. Track B must still never import `track_a`.
4. **TIMING robustness:** keep the median metric as the criterion, and add `tabla.timing_p90_ms` as a reported-only metric. Make sure heavy jitter is still visible through events and STEADY. Document the reasoning in §5.2.
5. **Real build:** `build_case(Path('tracks/cases/tabla'), RunContext.create(Path('tracks/cases/tabla'), Path('var'), 'recorded'))`. It is deterministic (no model call while audio is disabled). Commit `knowledge/*.v1.json` and `practice/*.v1.json`, and check that a rebuild is byte-identical, deleting the duplicate version before committing.
6. **Eval against the committed goal:** change `make_synthetic.py` / `run_eval.py` to load the committed goal model (`casedata.load_versioned`) instead of calling the builder. Re-run both and update `RESULTS.md` and the labels.
7. **End-to-end session test** `tracks/track-b/tests/test_tabla_session_e2e.py`: baseline = dropped-strokes or tempo-drift synthetic, retry = perfect copy, then `complete_session`. Assert the bundle validates, the gain is positive, and `targeted_change` improved. Generate the WAVs inside the test (tmp dir) so no media is committed.
8. **Optional video input:** confirm that an attempt with `extra={"video": path}` is accepted, ignored for scoring, and noted in the warnings (add a test).

## Acceptance
- v1 artifacts committed and reproducible.
- Eval runs on the committed goal, with updated numbers.
- Onset floor plus test added; prompt moved; p90 metric reported.
- e2e test passes.
- Jim's listening verdict recorded.
- The Definition of Done in 00-COMMON.md is met. Report: `docs/kiro/reports/K2-REPORT.md`.
