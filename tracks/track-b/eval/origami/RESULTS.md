# Origami Evaluator Live Results

Evaluation date: 2026-10-06. Mode: live (4/5 variants) + recorded replay.
Goal model: `goal_model.v1.json` (version 1). Evaluator: `track_b.evaluators.origami`.
Source: `OrigamiCrane.ogv` expert window [0, 194] s.

---

## 1. Goal-State Agreement

Goal builder produced **5 states** (R0–R4) vs **7 expert-labelled states** (label indices 0–6).

| Metric | Value |
|--------|-------|
| Goal states built | 5 |
| Expert label states | 7 |
| Matched label states | 0, 2, 2, 4, 5 (label 2 matched twice; labels 1, 3, 6 not captured) |
| Order preserved | True |
| Median boundary error | 11.01 s |

Goal R1 (book-folded rectangle, 40–42 s) is a 2-second state window — consistently flagged
as "seen only briefly" by the evaluator's stable-run filter. Labels 1, 3, and 6 were not
captured in the goal build, reducing discriminative power for some synthetic edits.

---

## 2. Per-Attempt Results

### 2.1 perfect (positive control — full expert window)

| Criterion | Metric | Value | Status |
|-----------|--------|-------|--------|
| CRIT-ORI-ORDER | order_violations | 2.0 | not_satisfied |
| CRIT-ORI-COMPLETE | missing_states | null (uncertain) | uncertain |
| CRIT-ORI-CLEAN | off_path_events | 0.0 | **satisfied** |
| CRIT-ORI-KEYSTEP | keystep_ok | null (uncertain) | uncertain |
| CRIT-ORI-FINAL | final_match | 0.5 | partially_satisfied |

- Frame-label accuracy: **10.5%** (8/76 labelled frames correct)
- Uncertain state: R1 (book-folded rectangle) seen only 2 s — below stable-run minimum
- First divergence: goal reports 2 order violations (R4 seen at 28 s before R1 at 72 s and R3 at 46 s)
- vs. ground truth (no divergence expected): `first_divergence_kind_agrees = false`
- `final_agrees = true` (trajectory and ground truth both say final state reached)
- **Honest failure**: positive control does not score well. R4 is seen at 28 s in the expert video
  before R1/R2 appear stably — the model labels the kite form early and this propagates as order violations.

### 2.2 missing_state (label-R2 segment [33–65 s] removed)

| Criterion | Metric | Value | Status |
|-----------|--------|-------|--------|
| CRIT-ORI-ORDER | order_violations | 1.0 | partially_satisfied |
| CRIT-ORI-COMPLETE | missing_states | 0.0 | **satisfied** (incorrect) |
| CRIT-ORI-CLEAN | off_path_events | 4.0 | not_satisfied |
| CRIT-ORI-KEYSTEP | keystep_ok | 1.0 | satisfied |
| CRIT-ORI-FINAL | final_match | 0.5 | partially_satisfied |

- Frame-label accuracy: **11.1%**
- Expected missing_states: [2] (label) — actual: `[]` (all 5 goal states found)
- Root cause: goal R1 (14–16 s output) is a **false positive** — model mislabels a transition
  frame as "book-folded rectangle" before the true R1 location (which is cut). All 5 goal states
  are therefore reported as present.
- `missing_exact = false`, `first_divergence_kind_agrees = false`
- **Honest failure**: evaluator cannot detect the missing label-R2 segment.

### 2.3 swapped_order (label-R1 and label-R2 segments exchanged)

| Criterion | Metric | Value | Status |
|-----------|--------|-------|--------|
| CRIT-ORI-ORDER | order_violations | 0.0 | **satisfied** (incorrect) |
| CRIT-ORI-COMPLETE | missing_states | 0.0 | satisfied |
| CRIT-ORI-CLEAN | off_path_events | 1.0 | partially_satisfied |
| CRIT-ORI-KEYSTEP | keystep_ok | 1.0 | satisfied |
| CRIT-ORI-FINAL | final_match | 0.5 | partially_satisfied |

- Frame-label accuracy: **7.7%**
- Expected order_violations: ≥ 1 — actual: `0`
- Root cause: the swap of label R1↔R2 moves the R1 content (~18 s) to after R2 content (~47–65 s).
  Goal R1 (book-folded rectangle at 52 s output) and R2 (diagonal triangle spanning ~11–47 s output)
  are first-reached in the correct goal order by coincidence, so no order violation is triggered.
- `order_violations_exact = false`
- **Honest failure**: evaluator cannot detect the swap because the goal-state numbering does not
  align well enough with the label-based swap boundaries.

### 2.4 truncated (stops at boundary b[5] = 131 s; label states 5–6 absent)

| Criterion | Metric | Value | Status |
|-----------|--------|-------|--------|
| CRIT-ORI-ORDER | order_violations | 1.0 | partially_satisfied |
| CRIT-ORI-COMPLETE | missing_states | 0.0 | **satisfied** (incorrect) |
| CRIT-ORI-CLEAN | off_path_events | 3.0 | not_satisfied |
| CRIT-ORI-KEYSTEP | keystep_ok | 1.0 | satisfied |
| CRIT-ORI-FINAL | final_match | 0.5 | partially_satisfied |

- Frame-label accuracy: **14.3%**
- Expected final_reached: false — actual: `true` (goal R4 = kite form IS reached before cutoff)
- Root cause: goal model's final state R4 (kite form) maps to **label state 5**, not label state 6.
  The truncated video cuts before label state 5 boundary (b[5]=131 s) but goal R4 (kite form at
  130–188 s) IS present in the truncated window. So the goal model considers the attempt complete.
- `final_agrees = false`, `missing_exact = false`
- **Honest failure**: the goal model's 5-state scope cannot distinguish truncation at the label-5/6
  boundary.

### 2.5 real_learner (Crane.ogv re-encode — positive control)

**FAILED**: 429 RESOURCE_EXHAUSTED (Gemini free-tier daily quota exhausted during evaluation session).
No run recorded. Results not available for this variant.

---

## 3. Summary Table

| Variant | frame_acc | missing_exact | order_exact | final_agrees | fd_kind_ok |
|---------|-----------|---------------|-------------|--------------|------------|
| perfect | 0.105 | true | false | true | false |
| missing_state | 0.111 | false | false | true | false |
| swapped_order | 0.077 | true | false | true | false |
| truncated | 0.143 | false | false | false | false |
| real_learner | — | — | — | — | — |

---

## 4. Key Findings

1. **Goal model scope**: builder produced 5 states vs 7 labelled; label states 1, 3, 6 not captured.
   R1 (book-fold) has a 2 s keyframe window that consistently triggers the "seen only briefly" filter.

2. **Low frame-label accuracy (8–14%)**: reflects two distinct issues — (a) the goal-state index space
   (0–4) does not align with the label space (0–6); (b) high proportion of "transition" model outputs
   where ground-truth has a clear state.

3. **order_violations_exact never true**: the evaluator detects order anomalies in the perfect video
   (goal R4 at 28 s before R1/R2), which are false positives. Conversely, the swapped_order variant
   produces 0 violations because the swap does not break goal-state first-occurrence order.

4. **final_match always 0.5**: the pairwise final-state check (`origami_final_v1` prompt) consistently
   returns "no match" (partial score) even for the positive control. This is a model reliability issue
   with the pairwise image comparison prompt, not a band calibration issue.

5. **Observer bands are logically correct**: no band adjustment is warranted. The quality issues lie
   in goal model scope, R1 keyframe brevity, and pairwise final-check reliability. Adjusting bands to
   accommodate current model output would make criteria insensitive.
