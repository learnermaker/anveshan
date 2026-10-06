# Track B Implementation Spec — Practice, Evaluation & Transmission

**Owner:** Akarsh · **Date:** 2026-10-06 · **Status:** PROPOSED. Becomes binding once §8 of the [plan review](track-plan-review-2026-10-06.md) is signed off.
**Builds on:** `tracks/track-b/SUCCESS-CRITERIA.md`, `CODING-AGENT-GUIDE.md`, `tracks/common/*`. Refines, never relaxes.
**Frozen:** the eight contracts. **Pass semantics are the common validator's:** an attempt passes only if every required criterion is SATISFIED and `total_score ≥ passing_score` (when set).

---

## 1. Mission and boundary

For each hero case, take Track A's handoff artifacts and run the learner loop:

baseline → hybrid observation → deterministic scoring → first divergence → grounded feedback + micro-drill → full-task retry → comparison → `TransmissionRecord` → validated bundle

**Hero cases:**

| Case | Learner evidence | Observation |
|---|---|---|
| Kolam | canvas trace (+ PNG raster); photo upload is P2 | deterministic geometry + Gemini semantics |
| Tabla | microphone WAV | deterministic onsets/timing + Gemini bol/clap recognition |
| Origami | uploaded video | Gemini step events + deterministic sequence alignment |

**Track B owns:**
- attempt intake and validation;
- per-modality observers;
- `observers.v{N}.json`;
- the scoring policy;
- evaluation;
- first divergence (including learner divergence for "corrective" behaviour);
- feedback;
- the micro-drill view model;
- retry comparison and transition classes;
- `TransmissionRecord`;
- session state objects;
- golden runs for observation;
- evaluation agreement metrics.

**Track B does not own:** source extraction, rubric authoring, HTTP / UI / persistence, deployment.

**Track B never imports `track_a`.** It reads the handoff as case data from `tracks/cases/<id>/`.

---

## 2. Package layout and public API

```
tracks/track-b/
  requirements.txt                # UTF-8, minimal, pinned: google-genai, pydantic>=2,<3, numpy
  src/track_b/
    __init__.py
    api.py                        # public API (only module Integration imports)
    config.py                     # MODEL_REGISTRY, SCORE_POLICY, limits
    handoff.py                    # load package/rubric/task/criterion_map/observers/references from tracks/cases
    intake.py                     # media validation -> AttemptMedia, sha256, LearnerAttempt construction
    observers/
      base.py                     # Observer protocol, ObservationResult
      kolam_trace.py              # deterministic geometry
      tabla_audio.py              # deterministic timing (uses tracks/common/onsets.py)
      origami_video.py            # sequence alignment over Gemini events
      gemini.py                   # GeminiCriterionObserver (image/audio/video), recorded-run aware
    scoring.py                    # status -> score policy; band evaluation
    evaluate.py                   # assemble Evaluation (replaces evaluator.py)
    divergence.py                 # first divergence
    feedback.py                   # grounded FeedbackItems + optional constrained wording
    drill.py                      # micro-drill view model (not a contract)
    compare.py                    # transitions, criteria_improved
    transmission.py               # TransmissionRecord (keep current, with changes in §8)
    session.py                    # serialisable Session state machine
    runs.py                       # golden-run record/replay for observer calls
    clock.py                      # Clock + IdFactory (injectable; deterministic in tests)
    failures.py                   # import/mirror FailureCategory (same values as Track A)
  prompts/                        # kolam_semantic_v1.txt, tabla_bols_v1.txt, origami_steps_v1.txt, feedback_wording_v1.txt
  tests/
  eval/                           # labelled sets + agreement scripts
  tools/camera_demo.py            # moved from src/; dev-only, Windows-specific code allowed here
```

Shared helpers owned by Integration, which Track B uses: `tracks/common/locators.py` (fragment parse/format) and `tracks/common/onsets.py` (onset detector, also used by Track A for the reference onsets).

### 2.1 Public API (`track_b/api.py`)

```python
@dataclass
class AttemptMedia:
    kind: Literal["trace", "image", "audio", "video"]
    path: Path                      # primary file (trace JSON, PNG/JPEG, WAV, MP4/WebM)
    raster_path: Path | None = None # Kolam: PNG rendering of the trace
    mime_type: str = ""
    sha256: str = ""                # computed by intake

@dataclass
class AttemptResult:
    attempt: LearnerAttempt
    evaluation: Evaluation
    first_divergence: FirstDivergence | None     # view model, §6
    feedback: Feedback | None                    # produced for BASELINE (and for RETRY if not passed)
    drill: Drill | None                          # view model, §7.3
    observations: list[ObservationResult]        # raw per-criterion detail (metrics, model output refs)
    runs: list[RunMetadata]
    runtime_class: Literal["LIVE", "RECORDED_LIVE", "SYNTHETIC"]

def start_session(case_id: str, cases_root: Path, learner: ParticipantRef,
                  *, clock: Clock | None = None, ids: IdFactory | None = None) -> Session
def submit_attempt(session: Session, media: AttemptMedia, *, mode: Literal["live", "recorded"] = "live") -> AttemptResult
    # attempt_type is derived: first submission = BASELINE (n=1); after feedback exists = RETRY (n>=2)
def complete_session(session: Session) -> SessionResult   # validated bundle dict + TransmissionRecord + transitions
def session_to_json(session: Session) -> dict; def session_from_json(d: dict) -> Session   # Integration persists
```

- Errors raise `TrackBFailure(category, message, details)` using the shared taxonomy.
- `INVALID_INPUT` messages must be learner-readable (e.g. "Recording is 2 s; please record at least 8 s.").

---

## 3. Inputs and intake (`intake.py`, `handoff.py`)

### 3.1 Handoff (read-only case data)

`handoff.load(case_id)` reads, from the latest approved (else latest) version:

- `knowledge/knowledge_package.v{N}.json`
- `practice/rubric.v{N}.json`
- `practice/practice_task.v{N}.json`
- `knowledge/criterion_map.v{N}.json`
- `practice/observers.v{N}.json`
- `knowledge/reference/*`

Validate:
- the package, rubric and task through the common validator;
- every rubric criterion appears in both the criterion map and observers;
- the rubric IDs in the map and observers match.

Any mismatch raises `CONTRACT_VIOLATION`. If the package is not approved, add a warning to every result; the UI shows it.

### 3.2 Attempt media formats and limits

| Kind | Format produced by the app | Limits / checks |
|---|---|---|
| trace | JSON (§4.1) + PNG raster 800×800 | ≥ 1 stroke with ≥ 5 points; ≤ 2 MB; canvas size and grid must match the task |
| audio | WAV PCM16 mono 16 kHz (the browser resamples via Web Audio) | 8–40 s; RMS above the noise floor; clipping < 1% of samples, otherwise `INVALID_INPUT` "too loud" |
| video | MP4 (H.264) or WebM | ≤ 60 s, ≤ 50 MB; uploaded through the Gemini Files API, never inline |
| image (P2) | JPEG/PNG | ≤ 7 MB |

`LearnerAttempt`:
- `attempt_id = attempt.<case>.<session>.<baseline|retry>.<n>`
- `evidence = EvidenceRef(evidence_id=ev.<attempt_id>, source_id=src.attempt.<case>.<session>.<n>, modality=…)`
  - Trace attempts: primary evidence is the raster (`image`). The trace is a derived artifact at `…<n>.trace`, cited by criterion evidence with modality `sensor`.
  - Audio and video: `start_sec=0`, `end_sec=duration`.
- `submitted_at` comes from the injected clock.

---

## 4. Observation (per modality)

Every rubric criterion is bound in `practice/observers.v{N}.json` (schema at `tracks/cases/observers.schema.json`):

```json
{
  "rubric_id": "rubric.kolam.2",
  "score_policy": "score_policy_v1",
  "criteria": {
    "CRIT-KOLAM-CLEARANCE": {
      "method": "deterministic",
      "metric": "kolam.dot_clearance",
      "params": {"touch_threshold_units": 0.12},
      "direction": "lower_is_better",
      "bands": [{"status": "satisfied", "max": 0}, {"status": "partially_satisfied", "max": 2}],
      "otherwise": "not_satisfied"
    },
    "CRIT-KOLAM-LOOPSHAPE": {
      "method": "gemini",
      "prompt_id": "kolam_semantic_v1",
      "inputs": ["attempt_raster", "target_image"]
    }
  }
}
```

**Observation result (internal):**

```python
ObservationResult(criterion_id, status, finding: str, metrics: dict, evidence_ref: EvidenceRef | None,
                  position: float | None,   # time (s), stroke index, or onset index, for first divergence
                  method, run_id | None, uncertainty_reason | None)
```

**Hard rules:**

1. Every rubric criterion yields exactly one result. A criterion is never dropped.
2. If a metric cannot be computed, or Gemini omits a criterion or returns invalid output, the status is **UNCERTAIN** with `uncertainty_reason`.
3. If Gemini cannot be reached in live mode, raise **MODEL_FAILURE**. Never fall back to mock data.
4. The model never sets a score.
5. Thresholds start with the defaults below and are **calibrated on the eval set** (§11). Each change bumps the observers version.

### 4.1 Kolam: deterministic geometry (`observers/kolam_trace.py`, numpy only)

Trace JSON from the app:

```json
{"canvas": {"width": 800, "height": 800},
 "grid": {"pattern": "1-3-5-3-1", "spacing_px": 90,
          "dots": [{"id": "r0c0", "x": 400, "y": 130}, "..."]},
 "strokes": [{"points": [[x, y, t_ms], "..."]}],
 "duration_ms": 74210}
```

- Normalise to grid units: `(p − grid_centroid) / spacing_px`.
- Resample each stroke at 0.05 units.
- Drop strokes shorter than 0.3 units (counted as `noise_strokes`, shown in the finding).

| Metric id | Computation | Default bands (status) |
|---|---|---|
| `kolam.dot_clearance` | for each dot, `d = min distance to any stroke`; violation if `d < 0.12`. Value = #violations | 0 → sat; ≤ 2 → partial; else not |
| `kolam.stroke_closure` | `n` strokes vs `L` loops in the reference trace; `gap = ‖start − end‖`. Value = (`n − L`, max gap) | `n = L` and gap ≤ 0.25 → sat; `n ≤ L + 2` and gap ≤ 0.5 → partial; else not |
| `kolam.enclosure_match` | close each stroke; winding number around each dot; compare the wrapped/not-wrapped vector to the reference trace. Value = match ratio | ≥ 0.95 → sat; ≥ 0.75 → partial; else not |
| `kolam.symmetry_error` | mean symmetric Chamfer distance between the point set P and T(P) for each symmetry transform of the target (from Track A properties; default: vertical and horizontal mirror plus 90° rotation); value = max over transforms | ≤ 0.15 → sat; ≤ 0.30 → partial; else not |
| `kolam.reference_similarity` | symmetric Chamfer distance learner ↔ expert reference trace (same grid, no rescale) | ≤ 0.20 → sat; ≤ 0.40 → partial; else not |

- **Evidence:** for the worst violation, `source_id = src.attempt.kolam.<sid>.<n>.trace#stroke=k`, plus a second ref on the raster with `#xywh=` around the offending dot, converted to percent. `position` = stroke index plus the point's `t_ms / 1000`.
- **Gemini semantics** (`kolam_semantic_v1`): inputs are the raster, the target image and the criterion text. Output per criterion: `{status, finding, regions[]}`. Status is limited to the four enum values; regions become `#xywh` on the raster.

### 4.2 Tabla padhant: timing plus bols (`observers/tabla_audio.py`)

**Onset detection** (in `tracks/common/onsets.py`, numpy only, deterministic):
- STFT with Hann window 1024, hop 256 at 16 kHz;
- spectral flux `Σ max(0, |X_t| − |X_{t−1}|)`, normalised to [0, 1];
- adaptive threshold = moving median over 0.5 s + 0.08;
- peak picking with a minimum gap of 90 ms.

Output `onsets_sec`. **Beat events** = onsets merged within 80 ms (a syllable and a clap on the same matra become one beat event).

**Expected structure** (from the PracticeTask and `reference_onsets.json`):
- Teentaal theka at 60 BPM, 2 cycles, so 32 matras;
- audible taali on matras 1, 5 and 13 of each cycle (khaali on 9 is a silent wave).

| Metric id | Computation | Default bands |
|---|---|---|
| `tabla.event_count` | \|beat events − 32\| | ≤ 1 → sat; ≤ 3 → partial; else not |
| `tabla.tempo_error` | `bpm = 60 / median(IOI)`; `\|bpm − 60\| / 60` | ≤ 5% → sat; ≤ 10% → partial; else not |
| `tabla.ioi_stability` | coefficient of variation of the IOIs | ≤ 0.08 → sat; ≤ 0.15 → partial; else not |
| `tabla.grid_alignment` | best-offset ideal grid at the measured tempo; median \|deviation\| (ms) | ≤ 60 → sat; ≤ 120 → partial; else not |
| `tabla.bol_accuracy` | **Gemini transcribes** the bol sequence and clap times (`tabla_bols_v1`, given the expected cycle as context, told to transcribe what is heard rather than what is expected). Accuracy is computed **deterministically** as `1 − edit_distance / 32` against the expected sequence | ≥ 0.85 → sat; ≥ 0.60 → partial; else not |
| `tabla.taali_placement` | Gemini clap events matched to beat events (±80 ms) → matra index; correct if on {1, 5, 13} | all correct → sat; ≥ 2/3 correct → partial; else not |

- **Evidence:** `source_id = src.attempt.tabla.<sid>.<n>`, `start_sec/end_sec` = the worst segment. For onset-level items, also `…<n>.onsets#onset=i`.
- `position` = the beat index where the first local failure occurs: largest timing deviation > 120 ms, first bol mismatch, or first misplaced clap.
- The observation `metrics` include the onset list. Integration's rhythm view plots it against the reference.

### 4.3 Origami: Gemini events plus deterministic alignment (`observers/origami_video.py`)

**Gemini call** (`origami_steps_v1`):
- inputs: the learner video (Files API), `reference_steps.json` (labels and `state_after`) and the expert keyframe images from `knowledge/reference/keyframes/`, which Track A prepares offline;
- output:

  ```python
  events: [{reference_step_index: int | None, label, start_sec, end_sec,
            execution: "satisfied|partially_satisfied|not_satisfied|uncertain", finding}]
  final_state: {status, finding, time_sec}
  ```

**Deterministic processing:**
- Validate the times against the duration.
- Align the observed `reference_step_index` sequence to `[0 … n−1]` with Needleman–Wunsch (match 0, substitution 1, insertion/deletion 1). The alignment gives `missing`, `extra` and `swapped` steps.

| Metric id | Computation | Default bands |
|---|---|---|
| `origami.step_order` | number of swaps / out-of-order steps | 0 → sat; 1 → partial; else not |
| `origami.step_completeness` | number of missing reference steps | 0 → sat; 1 → partial; else not |
| `origami.step_execution:<k>` | Gemini `execution` for reference step `k` (only for steps the rubric names; others are informational) | status as returned; a missing event → not_satisfied if completeness flagged it, else uncertain |
| `origami.final_state` | Gemini `final_state.status` | as returned |

- **Evidence:** learner video interval for the event, plus the expert reference `ref.origami.steps.v1#step=k` taken from the criterion map.
- `position` = learner `start_sec` of the divergent step (or the expected position of a missing step, interpolated from its neighbours).

### 4.4 Gemini observer (`observers/gemini.py`)

- One call per attempt per modality, with all Gemini-method criteria batched. Temperature 0. Structured output.
- The prompt includes, for each criterion: `observable_indicator` plus `why_it_matters` from the criterion map.
- The prompt says: "Report what you observe; if you cannot see or hear it clearly, return `uncertain`. Do not score."
- Raw response recorded (§9).
- Validation:
  - unknown criterion IDs are rejected and logged in warnings;
  - missing criterion → UNCERTAIN;
  - regions and times are validated (in range) and dropped if invalid, with a warning.

---

## 5. Scoring (`scoring.py`)

`SCORE_POLICY = "score_policy_v1"`:

| Status | Fraction of weight |
|---|---|
| satisfied | 1.0 |
| partially_satisfied | 0.5 |
| not_satisfied | 0.0 |
| uncertain | 0.0 |

- `score = round(weight × fraction, 4)`. Bands map metric values to a status exactly as configured.
- This is the **only** place scores are produced. The policy ID is recorded in the evaluation run metadata and in `adaptation_notes` on the record.

---

## 6. Evaluation and first divergence

### 6.1 Evaluation (`evaluate.py`)

- `criterion_results` come from the observations; `total_score` is the sum.
- `uncertainty_flags` = the UNCERTAIN criterion IDs.
- `evaluator_type`: `DETERMINISTIC` if every criterion used a deterministic method, otherwise `MODEL_ASSISTED`.
- **`passed`** = (`passing_score` is None or `total ≥ passing_score`) **and** every required criterion is SATISFIED. This is exactly the common validator's rule; the branch's current logic violates it.
- If a required criterion is UNCERTAIN, also add `HUMAN_REVIEW_REQUIRED` to the result warnings, and the UI offers "re-record".
- Run `validate_evaluation_against_rubric` before returning. Errors raise `CONTRACT_VIOLATION`.

### 6.2 First divergence (`divergence.py`, deterministic)

```python
FirstDivergence(criterion_id, criterion_name, status, position, position_kind: "time|stroke|onset|step",
                learner_evidence: EvidenceRef, expert_evidence: EvidenceRef | None,
                observed_finding, why_it_matters, source_claim_ids, uncertainty_note | None)
```

Algorithm:
1. Candidates are criteria with status NOT_SATISFIED or PARTIALLY_SATISFIED. UNCERTAIN criteria never qualify.
2. Sort by `criterion_map.order_index`, then required before optional, then `position` ascending.
3. Pick the first.
4. If there are no candidates but some criterion is UNCERTAIN, return `None`, and the drill becomes "re-record so X is visible/audible".

This view model maps one to one onto the app's existing `FirstDivergenceDetail`. The learner `observation` comes from the finding, the expert `interpretation` from `why_it_matters`, and `consequence` from the rubric weight and required flag. `unknownFactors` comes from the uncertainty reasons.

---

## 7. Feedback and micro-drill

### 7.1 FeedbackItem composition (`feedback.py`)

One item per criterion that is not SATISFIED, with the first divergence first.

| Field | Source |
|---|---|
| `criterion_id` | the result |
| `what_was_observed` | the observation finding with the measured values ("Line touches 3 pulli: r1c0, r2c2, r3c1 (min gap 0.04 units)") |
| `what_differed` | the rubric `observable_indicator`, plus the reference ("Expert line keeps ≥ 0.2 units from every pulli") |
| `corrective_advice` | `criterion_map.drill_hint` + the specific location + `why_it_matters` (cites `CLM-xx`) |
| `expert_evidence_ref` | the **resolved `reference_evidence_ids[0]`** from the criterion map in the package; `None` if there is none. **Never round-robin.** |
| `learner_evidence_ref` | the result's `evidence_ref` |

- UNCERTAIN items: `what_was_observed` = the uncertainty reason; `corrective_advice` = how to make it observable (framing, lighting, volume). These are **evidence-quality** items, not skill items.
- `recommended_retry_focus` = the first divergence, then the other non-satisfied criteria in order.
- `summary` is factual: "2 of 5 criteria met (4.5 / 10). First divergence: dot clearance at stroke 2 [CLM-06]." Add encouragement only after the facts.
- **Optional wording pass** (`feedback_wording_v1`, P2): Gemini rewrites the advice for warmth. A deterministic guard keeps the output only if every number, criterion ID and claim ID from the input facts is still present and no new numbers appear. Otherwise the template text is kept. The rewrite is recorded as a run.
- Feedback is validated by `validate_feedback_against_evaluation` before it is returned.

### 7.2 Comparability rule

The retry is always the **full PracticeTask under the same rubric**. The micro-drill is practice only. It never produces a `LearnerAttempt` or `Evaluation` and never awards points. Integration must remove the app's simulated drill scoring.

### 7.3 Micro-drill view model (`drill.py`)

```python
Drill(criterion_id, title, instruction=drill_hint, focus_region | focus_interval, expert_evidence, success_hint)
```

- Kolam: highlight the offending dot region and replay the expert stroke segment.
- Tabla: loop the expert 4-beat segment around the divergent matra with a metronome.
- Origami: play the expert clip for step k.

Unscored.

---

## 8. Comparison and TransmissionRecord

### 8.1 Transitions (`compare.py`)

For each criterion: `improved | regressed | unchanged | observability_gain (uncertain → known) | observability_loss (known → uncertain)`.

- `criteria_improved` = criteria with `retry_score > baseline_score` **and** baseline status ≠ UNCERTAIN. This is compatible with the validator.
- Check that every `recommended_retry_focus` criterion is present in the retry evaluation. It always will be, because the full rubric is evaluated, but assert it.
- The view model also reports `skill_gain_excluding_observability` = Σ score deltas over non-observability criteria. **`transmission_gain` stays the contract formula.** The UI shows both, with the contract value as the headline.

### 8.2 Record (`transmission.py`, keep the existing validation, plus the following)

- `transmission_id = tx.<case>.<session>`.
- `expert_id` = `package.consent.contributor_name` (or the source `creator`). Remove the `"expert-source"` default.
- `lineage.recorded_at` comes from the injected clock.
- `lineage.provenance_hash = "sha256:" + hex` (full 64 hex digits) over canonical JSON (sorted keys, compact separators) of: `package_id`, rubric, task, both attempts (including media sha256), both evaluations, feedback, `score_policy` and the observers version.
- `lineage.adaptation_notes`: `"score_policy_v1; observers v2; drill: CRIT-…; observability transitions: CRIT-X uncertain→satisfied; not expert-approved"`, with each part only if it applies.
- `lineage.parent_transmission_id`: `None` for the hackathon. The stretch is to chain "expert → learner A → learner B".
- `complete_session` builds the 9-key bundle (the common validator's keys) and runs `validate_transmission_bundle`. Errors raise `CONTRACT_VIOLATION`.

### 8.3 Determinism

- `Clock` and `IdFactory` are injectable. Tests use a fixed clock and sequential IDs. No `uuid4()` or `datetime.now()` inside the logic modules.
- Same inputs plus recorded model responses → byte-identical bundle JSON.

---

## 9. Golden runs and model configuration (`runs.py`, `config.py`)

- Every Gemini call records `tracks/cases/<id>/runs/golden/<run_id>/` (when promoted) or `tracks/track-b/data/runs/` (ad hoc, gitignored):
  - `run_metadata.json`: provider, model_id, model_key, prompt_id, prompt_version, prompt_sha256, input media sha256, runtime_class, run_id, latency_ms;
  - `raw_response.json`.
- `run_id = run.<case>.b.<UTC>.<6 hex>`.
- `mode="recorded"` looks up the response by `(prompt_sha256, media_sha256)`. A miss raises `REPLAY_MISMATCH`; there is never a silent live call or mock.
- `MODEL_REGISTRY = {"observe_image": …, "observe_audio": …, "observe_video": …, "feedback_wording": …}`. Integration verifies the IDs (Oct 7, Oct 17). No fallback lists. An explicit configured fallback is recorded in `model_id`.
- The `runtime_class` returned to Integration is `LIVE` (fresh call), `RECORDED_LIVE` (replayed golden run) or `SYNTHETIC` (non-hero fixture). It is never written into contracts.

---

## 10. Session flow and spoken mentor

### 10.1 Session state machine (`session.py`)

`CREATED → BASELINE_EVALUATED → FEEDBACK_READY → (DRILL_VIEWED)* → RETRY_EVALUATED → COMPLETED`

- A retry before feedback raises `INVALID_INPUT`.
- A second retry is allowed (attempt_number 3) but the MVP uses one.
- The first `submit_attempt` is BASELINE.
- `complete_session` uses the baseline and the **last** retry.
- `Session` is plain serialisable data. Integration stores it; Track B has no global state and no disk writes outside `runs/`.

### 10.2 Spoken mentor (port of `camera_demo.py`, P2)

- `compose_spoken_coaching(feedback, first_divergence) -> str` is deterministic: two or three sentences built **only** from the Feedback summary and the first item. No new claims.
- Integration's `/api/tts` turns that text into audio. The web app plays it after each evaluation.
- `camera_demo.py` moves to `tracks/track-b/tools/` unchanged in spirit. It must call `api.submit_attempt`, must not read Track A's `data/runs`, and is never deployed.

---

## 11. Evaluation agreement (evidence for judges)

`tracks/track-b/eval/` holds the labelled sets. Learner media stays in owned storage; only labels and sha256 values are committed.

| Case | Set | Labels | Metrics |
|---|---|---|---|
| Kolam | 8 traces (mix of good and flawed, owned) | per-criterion status by the expert or lead | % agreement and Cohen's κ per criterion; first-divergence agreement |
| Tabla | 6 WAVs | hand-marked onsets, bols, clap matras | onset F1 at ±50 ms (`research/benchmarks/scripts/score_events.py` style), tempo error, bol accuracy vs human |
| Origami | 4 videos | step boundaries + per-step status | step-order agreement, median boundary error (s) (`score_temporal.py`), first-divergence agreement |

- `python -m track_b.eval.run --case kolam` writes `eval/results/<case>.<date>.json` and a markdown summary.
- Band thresholds may be tuned **only** on a calibration split; report on the rest.
- Results go into `docs/validation/experiments.md` with model, prompt and observers versions.

---

## 12. Tests and acceptance

No network. The `live` marker is excluded in CI.

| Area | Must test |
|---|---|
| Pass semantics | required PARTIAL / UNCERTAIN → `passed=False`; the output always passes `validate_evaluation_against_rubric` (regression test for the branch bug) |
| No silent fallback | a Gemini exception → `MODEL_FAILURE`; a recorded-mode miss → `REPLAY_MISMATCH`; never mock data |
| Score authority | scores equal the policy × weight whatever the model returns (inject a model response containing a "score" field → ignored) |
| Kolam metrics | synthetic traces: perfect reference copy → all sat; one touching dot → clearance partial; two loops vs one → closure partial; mirrored half → symmetry fail |
| Tabla metrics | synthetic click tracks: 60 BPM exact → sat; 66 BPM → tempo partial; jitter σ = 100 ms → stability/grid fail; edit distance arithmetic |
| Origami alignment | swap, missing and extra step cases → correct metric values and first divergence |
| First divergence | ordering by `order_index`; UNCERTAIN excluded; ties |
| Feedback | `expert_evidence_ref` comes from the criterion map; `None` when unmapped; wording guard rejects altered numbers |
| Transitions | uncertain→satisfied excluded from `criteria_improved`; gain formula unchanged |
| Determinism | fixed clock / IDs + recorded runs → byte-identical bundle |
| Bundle | `complete_session` output passes `validate_transmission_bundle` for every hero case golden session |
| Intake | each format limit raises `INVALID_INPUT` with a readable message |

**Track B is ready for integration (per hero case) when:**

1. observers are configured and calibrated on the eval set;
2. one golden baseline+retry session is recorded and its bundle passes the validator;
3. recorded replay is deterministic;
4. first divergence and feedback cite the correct expert evidence;
5. eval agreement metrics are recorded;
6. there are no Track A imports;
7. no Windows-only code exists in `src/`.

---

## 13. Fix list from the branch review (mapped to sections)

| Sev | Item | Spec § |
|---|---|---|
| P0 | Pass semantics: required must be SATISFIED | 6.1 |
| P0 | Remove the silent mock fallback; explicit `MODEL_FAILURE` / recorded replay | 4 (rule 3), 9 |
| P0 | Model never sets scores; deterministic policy | 5 |
| P0 | Feedback expert evidence from the criterion map, not round-robin | 7.1 |
| P1 | Per-modality observers: audio (WAV, onsets), video (Files API, alignment), trace | 4.1–4.4 |
| P1 | Run metadata, versioned prompts, model registry, no fallback list | 9 |
| P1 | Delete the conflicting Kolam fixture (invented people, fake hash) in `fixtures/replay/case-001`; test against canonical packs + synthetic-labelled test inputs | 12 |
| P1 | Injectable clock and IDs | 8.3 |
| P1 | Transitions; `expert_id` from consent; full provenance hash | 8 |
| P1 | Move `camera_demo.py` to `tools/`; mentor via `/api/tts` | 10.2 |
| P2 | Rename package `src` → `track_b`; temp files outside the package | 2 |
| P2 | Factual summary; constrained wording pass | 7.1 |
| P2 | First divergence, drill, session | 6.2, 7.3, 10.1 |

**Branch hygiene:** after PR #40 merges, rebase `feat/akarsh-track-b` onto `main`. The Track A commits then disappear from the diff. Open one PR per bounded issue, starting with the P0 fixes.

---

## 14. Milestones (aligned with the plan review §6.2)

| Date | Done when |
|---|---|
| Oct 7 | P0 fixes + `track_b` package + clock/IDs; Track B tests in CI |
| Oct 8 | Kolam trace observer + scoring + evaluation |
| Oct 9 | Session API, first divergence, grounded feedback, drill; Kolam golden session |
| Oct 10 | Tabla onset observer + Gemini bol observer |
| Oct 11 | Origami Gemini events + alignment |
| Oct 12 | Golden sessions for Tabla and Origami; bundles validate |
| Oct 13 | Eval sets run; thresholds calibrated; agreement metrics recorded |
| Oct 16 | Code freeze |

## 15. Out of scope (hackathon)

Multi-learner cohorts and score distributions beyond the eval set, adaptive multi-retry curricula, Firestore persistence, OpenCV / pose estimation, live streaming evaluation (Gemini Live API), certification language, the four non-hero cases' live observation.
