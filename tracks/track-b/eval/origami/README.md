# Origami evaluation set

Evaluation material for the origami hero case. The design is in `docs/plans/evaluation-core.md` §4 and §7.

**Status:** the code and ground truth are ready. No model run has been recorded yet, because there is no API key. Nothing in this folder is a validation result.

## Contents

| Path | What it is | Committed |
|---|---|---|
| `labels/expert_window_labels.json` | Paper states R0–R6 with intervals in `OrigamiCrane.ogv`, window [0, 194] s | yes |
| `labels/learner_crane_window_labels.json` | The same states in `Crane.ogv` (see the caveat below) | yes |
| `labels/synthetic_ground_truth.json` | Edit lists, mapped state intervals and the expected outcome for each attempt | yes (generated) |
| `make_synthetic.py` | Renders the attempts (PyAV, mpeg4, 10 fps, no audio track) and writes the ground truth | yes |
| `run_eval.py` | Runs the evaluator on every attempt and scores agreement | yes |
| `var/eval/origami/*.mp4` | Rendered attempts | no (gitignored) |
| `var/eval/origami/results/` | Evaluator outputs and `agreement.json` | no (gitignored) |

All labels are **evaluation ground truth only** and are never system inputs. They were annotated by `claude (AI-assisted), pending human verification` from sampled frames, at about 1–2 s resolution.

### Attempts

| Variant | Edit (expert seconds) | Expected |
|---|---|---|
| `perfect` | [0, 194] | all states in order, final reached, no divergence |
| `missing_state` | [0, 33] + [65, 194] (R2 cut out) | R2 missing; first divergence = missing R2 at ~40 s |
| `swapped_order` | [0, 5.5] + [33, 65] + [5.5, 33] + [65, 194] | 1 order violation (R1 after R2); first divergence at ~10.5 s |
| `truncated` | [0, 131] | R5 and R6 missing; final not reached |
| `real_learner` | `Crane.ogv` [0, 194] | same as `perfect` |

Cuts fall at the midpoint between labelled states, so they land in transitions. The SYNTHETIC edits have limits. After the R2 cut, the later unfolded sheet still shows the diagonal creases. The swapped video jumps back to a flat sheet. Read results with these limits in mind.

**Caveat (observed):** `Crane.ogv` is the **same performance** as `OrigamiCrane.ogv` in a different encode and crop: the hand poses are identical at identical timestamps, and the best thumbnail correlation is at a lag of 0.0 s. It is a positive control under an encoding/crop domain shift. It is **not** an independent learner. A real independent attempt still has to be recorded.

## Running once a key exists

```bash
PY=.venv/Scripts/python
$PY tools/fetch_media.py origami                         # or --from-dir <local media dir>
$PY tracks/track-b/eval/origami/make_synthetic.py        # renders var/eval/origami/*.mp4, rewrites ground truth
# 1. build the goal (Track A; records the origami_states runs) — e.g. via track_a.api.build_case(case_dir, ctx)
#    with ctx = RunContext.create(case_dir, data_dir, "live"); this writes goal_model.vN.json and
#    knowledge/goal_assets/origami_state_<i>.jpg
# 2. evaluate every attempt live (records origami_match / origami_final runs under var/data/runs/origami)
$PY tracks/track-b/eval/origami/run_eval.py --mode live
# 3. re-score from recordings (exact replay; a miss is REPLAY_MISMATCH)
$PY tracks/track-b/eval/origami/run_eval.py --mode recorded
$PY -m pytest -m live tracks/track-a/tests/test_origami_goal.py tracks/track-b/tests/test_origami_eval.py
```

Model budget at 1 fps: the goal build makes about 17 calls of up to 12 frames each. Each attempt makes about 10 match calls (7 reference keyframes + 9 learner frames per call, at most 90 frames) plus 1 final check.

After a review, promote good runs into `tracks/cases/origami/runs/golden/` only from real live runs. Never put fake or hand-written runs there.

## Metrics reported (`agreement.json`)

Goal build vs the expert labels:
- state count (built vs labelled);
- IoU-matched label states and whether their order is preserved;
- median boundary error in seconds. The Track A target is ≤ 1.0 s.

Per attempt:
- `frame_state_accuracy`: filtered frame labels vs the labelled state on frames inside labelled state intervals;
- `missing_exact`: the missing-state set equals the ground truth;
- `order_violations_exact`: the order-violation count equals the ground truth;
- `final_agrees`: whether the final state was reached by the trajectory agrees with the ground truth;
- `first_divergence_kind_agrees` and `first_divergence_abs_error_sec`;
- `uncertain_states`: states reported as UNCERTAIN ("not visible") rather than missing.

Agreement against synthetic edits is exact by construction. Agreement against `real_learner` measures robustness to encode/crop differences only.
