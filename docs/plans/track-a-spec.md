# Track A Implementation Spec — Expert Intelligence & Grounding

**Owner:** Amal · **Date:** 2026-10-06 · **Status:** PROPOSED. Becomes binding once §8 of the [plan review](track-plan-review-2026-10-06.md) is signed off.
**Builds on:** `tracks/track-a/SUCCESS-CRITERIA.md`, `CODING-AGENT-GUIDE.md`, `tracks/common/*`. Where this spec is more specific, it refines those documents; it never relaxes them.
**Frozen:** the eight contracts in `tracks/common/schemas/`. Nothing in this spec changes them.

---

## 1. Mission and boundary

For each **hero case**, turn an authorised expert source into a reviewable, grounded teaching input that Track B can evaluate against without importing Track A code.

**Hero cases:**

| Case | Source modality | Mode |
|---|---|---|
| Kolam | image (+ expert canvas trace) | goal-conditioned (+ forward stretch) |
| Origami | video | forward |
| Tabla | audio | forward |

**Track A owns:**
- source registration;
- multimodal extraction;
- normalisation into `EvidenceRef` and `KnowledgePackage`;
- grounding checks;
- the candidate construction path (goal-conditioned mode);
- reference artifacts (reference trace, onsets, steps);
- rubric authoring support;
- `criterion_map`;
- `PracticeTask`;
- the evidence query;
- expert review and versioning;
- golden-run recording and replay.

**Track A does not own:**
- learner attempts or learner divergence detection (moved to Track B);
- scoring, feedback, gain, sessions;
- HTTP / UI;
- deployment.

Integration (Jim) calls the public API in §2.

---

## 2. Package layout and public API

```
tracks/track-a/
  requirements.txt              # UTF-8, minimal, pinned: google-genai, pydantic>=2,<3, numpy (for reference artifacts)
  src/track_a/
    __init__.py                 # re-exports the public API below
    api.py                      # public API (only module Integration imports)
    config.py                   # MODEL_REGISTRY, prompt versions, confidence policy constants
    sources.py                  # source registry load/verify (sha256)
    extraction/
      schemas.py                # Gemini response_schema DTOs (model-facing)
      providers.py              # GeminiProvider, RecordedRunProvider (no "replay from canonical" for extraction)
      prompts.py                # versioned prompt loading + sha256 of rendered prompt
    normalize.py                # DTO -> EvidenceRef/KnowledgeClaim/KnowledgePackage (pure, deterministic)
    grounding.py                # epistemic + locator audit
    references.py               # reference_trace / reference_onsets / reference_steps builders + validators
    rubric.py                   # rubric proposal + deterministic lint
    criterion_map.py            # build/validate criterion_map
    task.py                     # PracticeTask builder
    query.py                    # evidence query
    review.py                   # expert review -> new package version
    runs.py                     # golden-run record/load
    failures.py                 # FailureCategory, TrackAFailure (keep current implementation)
  prompts/                      # *_v2.txt (v1 kept for history)
  tests/
  tools/run_pipeline.py         # CLI wrapper over api.py (dev only)
```

- Integration puts `tracks/track-a/src` on `PYTHONPATH`.
- All internal imports are package-relative (`from track_a.normalize import …`). No `sys.path` manipulation inside the library.

### 2.1 Public API (`track_a/api.py`)

```python
RuntimeClass = Literal["LIVE", "RECORDED_LIVE", "SYNTHETIC"]   # view-level labels; never written into contracts

@dataclass(frozen=True)
class TrackAHandoff:
    case_id: str
    package: KnowledgePackage
    rubric: RubricDefinition
    practice_task: PracticeTask
    criterion_map: CriterionMap          # see §6.2 (pydantic model, case data, not a contract)
    references: dict[str, Path]          # e.g. {"reference_trace": ..., "reference_onsets": ...}
    source: SourceRecord                 # see §4.1
    run: RunMetadata                     # see §8
    runtime_class: RuntimeClass
    uncertainty: list[str]               # claim_ids that are INFERRED/UNVERIFIED, with reason
    warnings: list[str]

def load_handoff(case_id: str, cases_root: Path) -> TrackAHandoff
    """Load the latest APPROVED (else latest) versioned artifacts from tracks/cases/<case_id>/. No model call."""

def run_extraction(case_id: str, cases_root: Path, *, mode: Literal["live", "recorded"],
                   run_id: str | None = None, model_key: str = "extract_default") -> TrackAHandoff
    """live: call Gemini, record the golden run, normalise, ground, build artifacts (version N+1, status PENDING).
       recorded: re-run normalisation from a recorded raw response (run_id required)."""

def answer_query(case_id: str, cases_root: Path, question: str, *, mode: Literal["live", "recorded"]) -> QueryAnswer

def apply_review(case_id: str, cases_root: Path, action: ReviewAction) -> TrackAHandoff
    """approve | revise_claim | reject_claim | reject_package. Writes package v{N+1}; never mutates v{N}."""

def build_lesson_outline(handoff: TrackAHandoff) -> LessonOutline
    """Deterministic ordering of claims/candidate steps by criterion_map.order_index with reference evidence,
       for the teaching screen. View helper only; not a contract."""
```

- All functions raise `TrackAFailure(category, message, details)` using the existing taxonomy.
- None returns fabricated content on failure.

---

## 3. Mode responsibilities

| Mode | Track A produces | Track A does not produce |
|---|---|---|
| Forward (Origami, Tabla) | steps, cues, conditions, exceptions, failure modes with locators; reference steps or onsets | learner divergences |
| Goal-conditioned (Kolam) | OBSERVED target properties with regions; INFERRED candidate construction path (≤ 0.5 confidence); reference trace **if** an expert trace exists (a separate source) | any claim about creator intent, history or meaning, or the original stroke order, unless backed by the expert trace |
| Corrective | nothing new. Supplies failure modes, cues and reference evidence that Track B's feedback cites. | **Remove** `corrective_extraction_v1` from the extraction path; keep the file for history. |

---

## 4. Evidence rules

### 4.1 Source registry: `tracks/cases/<id>/source/source.json`

```json
{
  "sources": [
    {
      "source_id": "src.kolam.target.v1",
      "role": "target_image",                       // target_image | expert_demonstration | expert_trace | expert_audio
      "path": "source/target.jpg",                  // or "gcs://bucket/..." when deployed
      "mime_type": "image/jpeg",
      "sha256": "…",
      "dimensions": [1080, 1080],                   // images
      "duration_sec": null,                         // audio/video
      "creator": "<expert display name>",
      "license": "owned-consented | CC-BY-3.0 | …",
      "attribution": "…",
      "consent_ref": "source/CONSENT.md#kolam-expert",
      "access_level": "public | approved_learners | research_only",
      "captured_at": "2026-10-09"
    }
  ]
}
```

- `sources.verify(case_id)` recomputes sha256 and raises `INVALID_INPUT` on a mismatch.
- **Consent gate:** `run_extraction(mode="live")` raises `HUMAN_REVIEW_REQUIRED` if `consent_ref` is missing or `license` is unknown.
- Media with `access_level == "research_only"` must never be the hero-case source for a public deploy. Raise `INVALID_INPUT`.
- `source_media` in `manifest.json` (added in PR #40) points to the primary source. `source.json` is the authoritative registry.

### 4.2 Locator convention (shared with Track B; helper in `tracks/common/locators.py`, owned by Integration)

| Evidence | `source_id` | `start_sec` / `end_sec` | `modality` |
|---|---|---|---|
| Video moment | `src.origami.demo.v1` | interval (required) | `video` |
| Audio moment | `src.tabla.padhant.v1` | interval (required) | `audio` |
| Image region | `src.kolam.target.v1#xywh=percent:31.5,40.0,12.0,10.5` | `None`, `None` | `image` |
| Whole image | `src.kolam.target.v1` | `None`, `None` | `image` |
| Expert trace strokes | `src.kolam.expert_trace.v1#stroke=2-3` | `None` or trace time (s) | `sensor` |
| Reference step | `ref.origami.steps.v1#step=4` | interval from the expert video | `video` |

- Never write `0.0`/`0.0` as a placeholder locator.
- A claim with no locator for its source has no locator; it does **not** get a fake one.

### 4.3 Confidence and observation policy (constants in `config.py`)

| Situation | `is_observed` | `verification_state` | `confidence` |
|---|---|---|---|
| Model says OBSERVED **and** a valid locator exists for the right modality | `True` | `observed` | `0.8` |
| Model says PARTIAL | `False` | `inferred` | `0.5` |
| Model says UNKNOWN, or no locator possible | `False` | `unverified` | `0.3` |
| Candidate construction step (goal-conditioned) | `False` | `inferred` | `≤ 0.5` (use `0.4`) |
| Derived deterministically from an owned artifact (e.g. dot count computed from the expert trace) | `True` | `observed` | `1.0` |
| After expert approval | unchanged in evidence; recorded in `ExpertReview`, never by raising confidence | — | — |

These numbers are a **documented policy**, not a calibration claim. They are stored in `config.CONFIDENCE_POLICY` and quoted in the PR.

### 4.4 Modality

`EvidenceRef.modality` comes from the source's MIME type, not from the claim type.

- Audio sources → `audio`. This fixes the current "steps are always video" bug.
- A cue's modality may differ from the source modality only if the model gives it **and** it is one of `video | audio | image | text | sensor`.
- `tactile` maps to `video` (seen) or `audio` (heard), with the original word kept in `cue_excerpt`. Never silently default to `video`.

---

## 5. Extraction (per modality)

Every live extraction:

1. loads the source and verifies sha256;
2. renders a prompt `v2` and computes `prompt_sha256`;
3. calls Gemini with `response_schema`, `temperature=0`;
4. **records** the raw response (§8);
5. normalises (§5.4);
6. runs grounding (§5.5).

Media goes through the Gemini Files API (image inline bytes are acceptable when ≤ 7 MB).

### 5.1 Kolam: `goal_image_extraction_v2.txt`

Model-facing schema additions (`extraction/schemas.py`):

```python
class Region(BaseModel):            # percent of image width/height, origin top-left
    x: float; y: float; w: float; h: float

class TargetProperty(BaseModel):
    property_id: str                 # snake_case, e.g. "dot_grid", "rotational_symmetry", "loop_count"
    description: str
    measurement: str | None          # e.g. "13 dots, 1-3-5-3-1 diamond"
    evidence_sufficiency: Literal["OBSERVED", "PARTIAL", "UNKNOWN"]
    regions: list[Region]            # where it is visible; [] means whole image

class CandidateStep(BaseModel):
    index: int                       # proposed order
    instruction: str                 # learner-facing, e.g. "Start at the left apex, loop clockwise around dot (3,1)"
    produces: str                    # which target feature this stage builds
    regions: list[Region]            # where in the target the stage's result appears
    rationale: str                   # why this order is plausible (explicitly inferential)

class GoalImageExtraction(BaseModel):
    title: str; summary: str
    target_properties: list[TargetProperty]
    candidate_steps: list[CandidateStep]           # REQUIRED for goal-conditioned
    unknowns: list[str]                            # e.g. "original stroke order", "material", "regional variant name"
```

Prompt rules (must appear verbatim in the prompt):
- "Do not state who drew it, why, its cultural meaning, or the original order."
- "Every candidate step is a hypothesis."
- "List what cannot be known from the image in `unknowns`."

**Deterministic cross-check:** when `knowledge/reference/reference_trace.json` exists (the expert drew on the canvas), `references.trace_properties()` computes dot count, loop count, closure and symmetry axes. If a model OBSERVED property contradicts the computed value, the claim is downgraded to `unverified` and a warning is added.

The **variants** artifact is a stretch goal. `references.compare_paths(candidate_steps, expert_trace)` produces stage-level agreement, saved as `knowledge/path_comparison.v{N}.json`. The app shows "AI-inferred path vs expert's recorded path".

### 5.2 Origami: `forward_video_extraction_v2.txt`

- Schema: the existing steps, cues, conditions, exceptions and failure modes, plus `evidence_sufficiency` on **steps**. The model must say whether each step is clearly visible.
- Each step must also carry a `state_after` field (e.g. "square folded into preliminary base").
- `references.build_reference_steps()` produces `knowledge/reference/reference_steps.json`:

  ```json
  [{"index": 0, "label": "fold diagonal valley", "state_after": "...", "start_sec": 3.1, "end_sec": 6.8,
    "evidence_id": "ev.origami.step.00", "keyframe_sec": 6.5}]
  ```

- Timestamps must stay within `[0, duration_sec]`; otherwise `CONTRACT_VIOLATION`.
- Steps shorter than 0.3 s or overlapping by more than 50% are flagged `AMBIGUOUS_EVIDENCE` in warnings.

### 5.3 Tabla: `forward_audio_extraction_v2.txt`

Schema:

```python
class AudioEvent(BaseModel):
    index: int
    label: str                      # bol syllable ("Dha", "Dhin", "Ta", "Tin") or "taali"/"khaali" clap
    start_sec: float; end_sec: float
    evidence_sufficiency: Literal["OBSERVED","PARTIAL","UNKNOWN"]
class AudioExtraction(BaseModel):
    title: str; summary: str
    tempo_bpm_estimate: float | None
    cycle: list[str]                # the bol cycle as recited, e.g. 16 bols of Teentaal theka
    events: list[AudioEvent]
    cues: list[...]; failure_modes: list[...]
    unknowns: list[str]
```

**Deterministic reference** (`references.build_reference_onsets()`): Track A computes onsets from the expert WAV with the **same numpy onset detector Track B uses**. That detector lives in `tracks/common/onsets.py`, a helper owned by Integration so both tracks share one implementation. Track A then aligns the model's `events` to the detected onsets, matching each event to the nearest onset within ±80 ms. This produces `knowledge/reference/reference_onsets.json`:

```json
{"sample_rate": 16000, "tempo_bpm": 60.2, "onsets_sec": [...], "labels": ["Dha","Dhin",...],
 "label_source": "gemini (matched to detected onsets)", "unmatched_events": [...]}
```

- Claims for model events that match no detected onset become `unverified`.
- Bol labels are model interpretations: `inferred` unless the expert confirms them in review. After confirmation they stay `inferred` in the evidence, and the review records approval.

### 5.4 Normalisation (`normalize.py`, pure, deterministic)

- Input: DTO, `SourceRecord`, `RunMetadata`, version `N`. Output: `KnowledgePackage`.
- Claim IDs are `CLM-01…`, assigned in a deterministic order:
  1. target properties or steps;
  2. candidate steps;
  3. cues;
  4. conditions;
  5. exceptions;
  6. failure modes.
- Evidence IDs are `ev.<case>.<kind>.<nn>`.
- Apply §4.2–§4.4 exactly.
- Conditions, exceptions and failure modes without a locator: `is_observed=False`, `unverified`, `cue_excerpt` holds the model text, `source_id` is the source (no fragment).
- `package_id = kp.<case>.<N>`. `skill_id` comes from `manifest.skill` (or `skill.<case>`), and the same value is used in replay and live.
- `consent` comes from `source.json` (contributor name, scope from CONSENT.md). Never a placeholder for hero cases.
- `expert_review` starts as `PENDING`.

### 5.5 Grounding audit (`grounding.py`)

Keep the existing checks, and add:

- locator presence matches `is_observed`;
- image evidence has no times;
- audio and video evidence has times within the duration;
- `#xywh` values lie in [0, 100];
- a goal-conditioned package has **at least one** inferred `STEP` (raise `UNSUPPORTED_CLAIM` if not, because there is nothing to teach);
- no claim text contains creator-intent phrases ("the artist intended", "originally drawn") unless backed by an expert source. This is a regex list in `config.py`; a hit means `HUMAN_REVIEW_REQUIRED`.

---

## 6. Rubric and criterion map

### 6.1 Rubric authoring (`rubric.py`)

1. **Propose:** Gemini (`rubric_synthesis_v2.txt`) gets the package plus the modality's **observable-signal catalogue** (§6.3) and proposes 4–7 criteria. Each criterion has `name`, `observable_indicator` (must name a measurable or visible signal), weight 1–5, `required`, `source_claim_ids`, and `suggested_method`.
2. **Lint** (deterministic):
   - unique IDs;
   - every `source_claim_id` exists;
   - `observable_indicator` mentions a catalogue signal or a concrete visual property;
   - no "understands", "knows" or "masters";
   - total weight 10 (normalise);
   - 1–3 required criteria;
   - `passing_score` set explicitly (default 70% of max, editable).
3. **Approve:** the human (expert or lead) edits in a JSON file or the review screen. The rubric is saved as `practice/rubric.v{N}.json`. **Only approved rubrics are used in hero demos.** For hero cases, a hand-written rubric is acceptable and preferred.

Criterion IDs are semantic and stable: `CRIT-KOLAM-CLEARANCE`, `CRIT-TABLA-TEMPO`, etc.

### 6.2 `knowledge/criterion_map.v{N}.json` (case data; schema in `tracks/cases/criterion_map.schema.json`)

```json
{
  "rubric_id": "rubric.kolam.2",
  "package_id": "kp.kolam.2",
  "criteria": {
    "CRIT-KOLAM-CLEARANCE": {
      "order_index": 2,
      "source_claim_ids": ["CLM-06"],
      "reference_evidence_ids": ["ev.kolam.target.06"],
      "reference_artifact": "knowledge/reference/reference_trace.json#stroke=0",
      "why_it_matters": "In Sikku kolam the line weaves around every pulli without touching it; touching breaks the pattern's rule (CLM-06).",
      "drill_hint": "Trace one loop slowly around the centre dot keeping a finger-width gap."
    }
  }
}
```

- `order_index` follows procedure order: Origami steps, Kolam candidate stages, Tabla cycle position. Track B uses it for first divergence.
- `why_it_matters` must quote or paraphrase a claim in `source_claim_ids`. Lint checks that the claim ID appears in the text.
- Every rubric criterion must appear in the map, and every `reference_evidence_id` must exist in the package.

### 6.3 Observable-signal catalogue (what Track B can measure; keep in sync with the Track B spec §4)

| Modality | Deterministic signals | Gemini-judged signals |
|---|---|---|
| Kolam trace | dot clearance, stroke count, closure, dot enclosure, symmetry error, reference similarity | loop shape (petal, teardrop), aesthetic regularity |
| Tabla audio | onset count, tempo error, IOI stability, grid alignment, clap position | bol identity per onset, bol clarity |
| Origami video | step order, completeness (after alignment) | per-step execution (alignment of edges, crease placement), final shape |

---

## 7. PracticeTask (`task.py`)

- `task_id = task.<case>.<N>`; references `package_id` and `rubric_id`.
- `target_criteria_ids` = all rubric criteria (the full task).
- `instructions`: numbered, learner-facing, built from `criterion_map` order. Each line ends with `[CLM-xx]` citations. Kolam uses the candidate steps and explicitly says "one suggested way". No generic "demonstrate mastery".
- Constraints per case:

| Case | Constraints |
|---|---|
| Kolam | `grid: 1-3-5-3-1 (13 dots), rendered by app`; `single continuous line preferred`; `time_limit: 180s` |
| Tabla | `tempo: 60 BPM (metronome optional)`; `cycle: Teentaal theka x2`; `max_duration: 40s`; `quiet room` |
| Origami | `paper: 15 cm square`; `stop at bird base`; `video: ≤60s, hands and paper in frame, top-down` |

---

## 8. Golden runs, recording and replay (`runs.py`)

Layout: `tracks/cases/<id>/runs/golden/<run_id>/`

| File | Contents |
|---|---|
| `run_metadata.json` | provider, model_id (as returned), model_key, prompt_id, prompt_version, prompt_sha256, input source_id + sha256, runtime_class=LIVE, run_id, started_at, latency_ms, expected_behavior, evaluation_reference |
| `raw_response.json` | exact model JSON |
| `normalized/` | knowledge_package / references / warnings as produced |

- `run_id = run.<case>.a.<UTC yyyymmddThhmmss>.<6 hex>`.
- `RecordedRunProvider` returns the recorded raw response, so **normalisation, grounding, rubric lint and the criterion map are re-run deterministically**. This is the CI replay path.
- The existing "replay from canonical bundle" path stays only as a loader (`load_handoff`) for non-hero showcase cases. It must be labelled SYNTHETIC.
- Only promoted golden runs are committed. Ad-hoc runs go to `tracks/track-a/data/runs/` (gitignored).
- Golden runs must be small. Media is never copied into a run.

### Model registry (`config.py`)

```python
MODEL_REGISTRY = {"extract_default": "<verified model id>", "query_default": "<verified model id>"}
```

- Integration verifies model IDs against the live API on Oct 7 and Oct 17.
- No silent fallback. A fallback model can be used only if it is configured explicitly, and it is then recorded in `run_metadata.model_id`.

---

## 9. Versioning and review (`review.py`)

- Artifacts are versioned files `*.v{N}.json`. A new extraction, revision or rubric edit writes N+1. Earlier versions are never edited.
- `apply_review` actions:

| Action | Effect |
|---|---|
| `approve` | ExpertReview(status=APPROVED, reviewer_name, reviewed_at, notes) |
| `revise_claim(claim_id, new_statement, note)` | creates package N+1 with the claim's statement replaced; the original statement is kept in the review notes ("CLM-04 revised: '<old>' → '<new>'"); ExpertReview(status=REVISED) |
| `reject_claim(claim_id, note)` | removes the claim in N+1 and records the removal in notes; dependent criterion_map entries are flagged |
| `reject_package` | status REJECTED; `load_handoff` will not return it |

- `load_handoff` prefers the latest APPROVED/REVISED version and otherwise returns the latest, adding a warning `"package not expert-approved"`, which the UI must show.

---

## 10. Evidence query (`query.py`)

- Input: question plus the approved package. Output:

  ```python
  QueryAnswer(answer: str, cited_claim_ids: list[str], evidence: list[EvidenceRef], sufficient: bool, run: RunMetadata)
  ```

- Gemini (`adversarial_query_v2.txt`) answers **only** from the claims given. Cited IDs are validated against the package.
- **No keyword fallback.** No valid citations → `sufficient=False` with the INSUFFICIENT_EVIDENCE text.
- Answers are recorded like runs, so each demo question has a recorded answer.
- Deterministic pre-check: if the question asks about intent, history or meaning for a goal-conditioned case, return INSUFFICIENT without a model call.

---

## 11. Tests and acceptance

Tests run with no network. `@pytest.mark.live` is registered and excluded in CI.

| Area | Must test |
|---|---|
| Normalisation | modality from source; image → `None` times + valid `#xywh`; no locator → not observed; candidate steps → inferred `STEP` with confidence ≤ 0.5; claim ID order stable |
| Grounding | rejects fake `0.0` locators, out-of-range times, goal-conditioned with zero inferred steps, intent phrases |
| Sources | sha256 mismatch → `INVALID_INPUT`; missing consent → `HUMAN_REVIEW_REQUIRED` on live |
| References | Kolam trace properties (dot count, closure) on a fixture trace; Tabla onset matching ±80 ms; Origami step timestamp bounds |
| Rubric | lint rejects unknown claim IDs, vague indicators, missing `passing_score`; criterion map covers all criteria |
| Recorded replay | each golden run → identical package / rubric / task / map (byte-stable JSON) |
| Query | invalid citations → insufficient; intent question → insufficient |
| Review | revise creates N+1 and keeps N unchanged |
| Contracts | every output passes `tracks.common.validator` (single + `validate_practice_task_against_knowledge_and_rubric`) |

**Track A is ready for integration (per hero case) when:**

1. an owned, consented source is registered;
2. one golden live run is committed;
3. the recorded replay is deterministic;
4. the package has ≥ 1 OBSERVED claim with a correct locator for the modality and (Kolam) ≥ 3 inferred candidate steps;
5. the rubric is approved;
6. the criterion map is complete;
7. the PracticeTask is case-specific;
8. there are 10 recorded query answers (≥ 2 deliberately unanswerable, correctly refused);
9. the expert has reviewed it (≥ 1 revise or approve recorded).

---

## 12. Quality evaluation (evidence for judges, recorded in `docs/validation/experiments.md`)

| Metric | Method | Target (not a claim until measured) |
|---|---|---|
| Extraction fidelity | Expert rates each claim: correct / incomplete / incorrect / invented | ≥ 80% correct, 0 invented among material claims |
| Grounding | 10 adversarial questions per case; pass if citation correct or correctly refused | ≥ 8/10 |
| Timestamp accuracy | Origami steps vs hand-labelled boundaries; Tabla events vs detected onsets | median ≤ 1.0 s (video), ≤ 80 ms (audio) |
| Path plausibility (Kolam) | Expert rates the candidate path; `compare_paths` agreement with the expert trace | expert "plausible" yes/no + agreement % |

Each result records model, prompt version, run IDs and sample size. Use `research/benchmarks/scripts/score_temporal.py` and `score_events.py` where they fit.

---

## 13. Fix list from the branch review (mapped to sections)

| Sev | Item | Spec § |
|---|---|---|
| P0 | Add candidate path to schemas, normaliser and grounding | 5.1, 5.4, 5.5 |
| P0 | Stop manufacturing observation, locators and video modality | 4.2–4.4, 5.4 |
| P1 | Replace UTF-16 root `requirements.txt` with UTF-8 `tracks/track-a/requirements.txt` | 2 |
| P1 | Golden-run recorder plus `RecordedRunProvider`; normaliser on the replay path | 8 |
| P1 | Rubric proposal, lint and approval; criterion map | 6 |
| P1 | Case-specific PracticeTask | 7 |
| P1 | Remove corrective divergence extraction | 3 |
| P1 | Query: no keyword fallback; validate citations | 10 |
| P1 | Source registry with sha256; stable versioned IDs | 4.1, 5.4, 9 |
| P1 | Tabla audio extraction + reference onsets | 5.3 |
| P1 | Replace `kolam.png` with an owned, consented target | 4.1 |
| P2 | `track_a` package; register live marker; CLI to `tools/` | 2 |
| P2 | Model registry; no hard-coded model | 8 |

---

## 14. Milestones (aligned with the plan review §6.2)

| Date | Done when |
|---|---|
| Oct 7 | P0 fixes merged in PR #40; `track_a` package; CI runs Track A tests |
| Oct 8–9 | Kolam: source registry, v2 extraction, golden run, approved rubric, criterion map, task |
| Oct 10 | Origami: extraction, reference steps, rubric, map, task, golden run |
| Oct 11 | Tabla: extraction, reference onsets, rubric, map, task, golden run |
| Oct 12 | Query answers recorded (10 per case); review flow used once per case |
| Oct 13 | Fidelity, grounding and timestamp metrics recorded |
| Oct 16 | Code freeze |

## 15. Out of scope (hackathon)

Embeddings / semantic search, multi-source contradiction mining (beyond the Kolam path comparison), Transcribe model integration (padhant is handled by multimodal audio understanding), Firestore, community governance workflows, the four non-hero cases' live extraction.
