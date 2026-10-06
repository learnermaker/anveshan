# K2-REPORT: Tabla Finish

Branch: `kiro/k2-tabla` — ready to merge into `m1/hero-cases`.

## Listening verdict (Step 1)

**Listener:** Jim Seelan (not a tabla expert)
**Clip:** `var/kiro/tabla_window_20-32s.wav` (12 s, 16 kHz mono; 3× slow version also provided)
**Source:** Wikimedia "A man playing tabla in village pranpur near Chanderi.webm" (CC BY-SA 4.0, by Manishontop02), window 20.0–32.0 s

**Verdict:** YES — clean tabla playing, steady pulse, bass pattern repeats. No rejection. K2 proceeds on this source.

---

## Steps completed

| Step | Description | Outcome |
|---|---|---|
| 1 | Listening clips for Jim | DONE — verdict recorded above |
| 2 | Absolute onset floor in `onsets.py` | DONE — `flux_floor=0.05` pre-normalization guard; pure-tone test added |
| 3 | Shared prompt location | DONE — `tracks/common/prompts/tabla_bols_v1.txt`; both tracks updated |
| 4 | TIMING p90 metric | DONE — `tabla.timing_p90_ms` reported-only; §5.2 updated |
| 5 | Real `build_case` | DONE — 6 v1 artifacts committed; deterministic (version/package_id only differ on rebuild) |
| 6 | Eval loads committed goal | DONE — bootstrap removed; labels + RESULTS.md regenerated |
| 7 | End-to-end session test | DONE — 2 tests (tempo-drift + dropped-strokes), both green |
| 8 | (optional) Video input | Already done pre-K2 (`test_video_is_ignored_with_note` in `test_tabla_eval.py`) |

---

## Test output summary

Full suite: **285 passed, 2 deselected, 0 failed** (53 s)
Command: `<py> -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"`

Governance:
- `check_case_packs.py`: **PASS** (7 packs)
- `check_governance.py`: **PASS**
- `check_contract_parity.py`: **PASS** (8 contracts, 17 interfaces, 7 enums)

---

## Eval numbers (RESULTS.md — against committed goal kp.tabla.1)

- Goal: `kp.tabla.1`, window [20.0, 32.0] s, 53 strokes, pulse 0.1893 s, cycle 12 pulses
- Onset F1 mean: **0.998** (min 0.991)
- First-divergence agreement: **6/6**
- Criterion status agreement: **36/36 (100.0%)**

| attempt | F1 | first divergence | statuses |
|---|---|---|---|
| perfect | 1.000 | none | all sat |
| jitter_mild | 1.000 | none | all sat |
| jitter_heavy | 1.000 | late_stroke@2.93 | STEADY=not |
| tempo_plus8 | 1.000 | tempo_off@1.55 | TEMPO=partial |
| dropped3 | 1.000 | missing_stroke@2.67 | COMPLETE=partial |
| bass_removed_mid | 0.991 | bass_missing@4.56 | BAYAN=partial |

---

## Decisions and notes for Claude Code

1. **Evidence modality fix (incidental):** The tabla source is `video/webm`, but the goal builder was emitting `Modality.AUDIO` evidence. This caused `build_case` to fail the grounding audit (`modality audio != source modality video`). Fixed by deriving evidence modality from source MIME type, consistent with the origami builder. Two Track A tests were updated to reflect the committed artifacts.

2. **Onset floor semantics:** The `flux_floor=0.05` parameter in `OnsetParams` is a **pre-normalization** guard (`peak < rms * flux_floor → return empty`), not a post-normalization threshold. The comment in `onsets.py` documents this. A pure 440 Hz tone at 0.8 amplitude has `peak/rms ≈ 0.011`, well below the 0.05 threshold. Real percussion has ratios in the thousands.

3. **STEADY bands widened:** The real source's IOI CV is 0.113, causing the builder to widen STEADY sat to 0.141 and partial to 0.226. This is expected and documented. A perfect synthetic attempt is still classified as `satisfied`.

4. **BOLS criterion absent from committed case:** The audio model is disabled (`ANVESHAN_AUDIO_MODEL` not set). CRIT-TABLA-BOLS is absent from the committed rubric/observers. Bol criterion is `uncertain` in all eval rows by design.

5. **Open for follow-up:** The bol prompt move (`common/prompts/`) is done, but no track actually calls the audio model in the current build. When the audio model is enabled (future scope), both tracks will use the shared prompt.

6. **`tabla_window_20-32s_3x_slow.wav`** uses nearest-neighbour time-stretch (no pitch preservation); pitch is not important for the listening check, and scipy/librosa are excluded from the environment.

---

## Commits on this branch (K2 work)

```
22ff429 fix(tabla): derive evidence modality from source MIME type; update tests for committed v1 artifacts
a8361d3 test(tabla): add end-to-end session test (tempo-drift + dropped-strokes baselines)
4ce2b51 fix(tabla): eval loads committed goal; remove builder bootstrap from make_synthetic.py
c3eb3b2 feat(tabla): commit real goal model and observers v1 artifacts (deterministic build)
2d4aec5 feat(tabla): add tabla.timing_p90_ms reported-only metric; document in evaluation-core §5.2
55e441f refactor(tabla): move bol prompt to tracks/common/prompts/
8872bbe fix(tabla): add absolute flux floor to onsets.py; add pure-tone test
bd80c8b feat(tabla): write listening clips for Step 1 review
```
