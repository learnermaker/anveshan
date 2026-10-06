# Interfaces for Parallel Build — Track A API, Track B API, HTTP API

**Date:** 2026-10-06 · **Status:** DECIDED interface freeze for the hackathon build. Change it only by editing this file in the same commit as the code.

Shared foundation (already on the branch):

| Module | Provides |
|---|---|
| `tracks/common/media.py` | probe, decode_audio, sample_frames, sha256 |
| `tracks/common/onsets.py` | onset detector + 2-means threshold |
| `tracks/common/locators.py` | `#xywh` / `#stroke` / `#onset` / `#step` / `#frame` fragments |
| `tracks/common/models.py` | ModelGateway, RunStore, registry, failure taxonomy (`AnveshanFailure`, `FailureCategory`) |
| `tracks/common/casedata.py` | SourceRegistry, GoalModel, CriterionMap, Observers, versioned file helpers |
| `tracks/common/runtime.py` | RunContext |
| `track_a/goals/__init__.py` | GoalBuildResult, CriterionTemplate, builder registry |
| `track_b/trajectory.py` | AttemptMedia, MetricValue, DivergenceEvent, TrajectoryResult |
| `track_b/evaluators/__init__.py` | evaluator registry |

## 1. Modality plugins (one agent per modality writes both)

```python
# tracks/common/goals/<m>.py
PAYLOAD_MODEL: type[BaseModel]          # schema of GoalModel.payload for this modality
def ui_view(payload: dict) -> dict      # small JSON for the app (e.g. kolam dots+curves, origami keyframe ids, tabla beats)

# tracks/track-a/src/track_a/goals/<m>.py
def build(source_path: Path, source: SourceRecord, ctx: RunContext, *, case_id: str, version: int) -> GoalBuildResult

# tracks/track-b/src/track_b/evaluators/<m>.py
def evaluate(goal: GoalModel, attempt: AttemptMedia, ctx: RunContext) -> TrajectoryResult
```

`m ∈ {kolam, origami, tabla}`; modality ids are `kolam_image | origami_video | tabla_audio`.

Accepted `AttemptMedia.kind`:

| Modality | kinds |
|---|---|
| kolam | `trace` (canvas JSON, §4) or `image` (photo/raster) |
| origami | `video` |
| tabla | `audio` (an optional `extra["video"]` is ignored for scoring) |

## 2. Track A public API (`track_a/api.py`)

```python
@dataclass
class CaseHandoff:
    case_id: str; case_dir: Path; manifest: dict; sources: SourceRegistry
    goal: GoalModel; package: KnowledgePackage; rubric: RubricDefinition; task: PracticeTask
    criterion_map: CriterionMap; observers: Observers
    review_status: str                    # pending|approved|revised|rejected
    runtime_label: str                    # INTERNET_REFERENCE|UPLOAD|SYNTHETIC|OWNED_CONSENTED
    warnings: list[str]
    def to_view(self) -> dict             # JSON for GET /api/cases/{id} (includes goal ui_view)

def list_cases(cases_root: Path, data_dir: Path) -> list[dict]          # hero + derived upload cases + showcase
def load_case(case_dir: Path) -> CaseHandoff                            # latest approved-else-latest versions
def build_case(case_dir: Path, ctx: RunContext, source_id: str | None = None) -> CaseHandoff
    # runs the modality goal builder, writes NEXT versions of goal_model, knowledge_package, rubric,
    # practice_task, criterion_map, observers (status PENDING); validates via tracks.common.validator
def create_upload_case(cases_root: Path, data_dir: Path, base_case_id: str, file_path: Path, mime: str) -> Path
    # copies manifest to <data_dir>/cases/<base>~<sha12>/, writes source.json (runtime_label UPLOAD)
def answer_query(case_dir: Path, question: str, ctx: RunContext) -> dict
    # {answer, cited_claim_ids, evidence: [EvidenceRef], sufficient: bool, run: {...}}
def apply_review(case_dir: Path, action: dict) -> CaseHandoff
    # action = {action: approve|revise_claim|reject_claim|reject_package, reviewer, note, claim_id?, new_statement?}
```

## 3. Track B public API (`track_b/api.py`)

```python
def start_session(case_dir: Path, learner_name: str, data_dir: Path, *, clock=None, ids=None) -> Session
def submit_attempt(session: Session, media: AttemptMedia, ctx: RunContext) -> AttemptResult
def complete_session(session: Session) -> SessionResult
def save_session(session: Session, data_dir: Path) -> None; def load_session(session_id: str, data_dir: Path) -> Session

AttemptResult.to_json() -> {
  "attempt": LearnerAttempt, "evaluation": Evaluation,
  "trajectory": {"curve": [[pos, progress]], "curve_kind": str, "events": [DivergenceEvent...],
                 "process_observable": bool, "artifacts": {...}, "final_state": {...}},
  "metrics": {metric_id: {value, finding, uncertain_reason}},
  "first_divergence": {criterion_id, criterion_name, status, position, position_kind, learner_evidence,
                       expert_evidence, observed_finding, why_it_matters, source_claim_ids, drill_hint} | null,
  "feedback": Feedback | null, "drill": {...} | null,
  "runtime_class": "LIVE"|"RECORDED_LIVE"|"DETERMINISTIC", "warnings": [str], "run_keys": [str] }
SessionResult.to_json() -> { "bundle": {9 canonical keys}, "transmission_record": TransmissionRecord,
  "comparison": {"transitions": {criterion_id: kind}, "targeted_change": {...},
                 "skill_gain_excluding_observability": float, "curves": {"baseline": [...], "retry": [...]}} }
```

Track B reads case artifacts from files. It never imports `track_a`.

## 4. Kolam canvas trace JSON (produced by the app)

```json
{"canvas": {"width": 492, "height": 499}, "goal_case_id": "kolam", "goal_version": 1,
 "strokes": [{"points": [[x, y, t_ms], ...]}], "duration_ms": 74210}
```

Coordinates are in **goal image pixels** (the app scales the canvas to the goal image size from `ui_view`).

## 5. HTTP API (`service/anveshan_service`, FastAPI)

All JSON. Errors: `{"error": {"category", "message", "details"}}`.

| Category | HTTP status |
|---|---|
| INVALID_INPUT | 400 |
| MISSING_EVIDENCE | 404 |
| REPLAY_MISMATCH | 409 |
| HUMAN_REVIEW_REQUIRED | 422 |
| MODEL_FAILURE, MODEL_TIMEOUT | 502 |
| CONTRACT_VIOLATION | 500 |

Optional `?mode=live|recorded`; the default is `ANVESHAN_MODE`.

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/api/health` | — | `{ok, mode, models: {text_image, video_frames, audio_enabled}}` |
| GET | `/api/cases` | — | `[ {case_id, title, modality, hero, runtime_label, review_status, derived_from?} ]` |
| GET | `/api/cases/{case_id}` | — | `CaseHandoff.to_view()` |
| POST | `/api/cases/{case_id}/sources` | multipart `file` | `{case_id: "<base>~<sha12>"}` (new derived case; then build) |
| POST | `/api/cases/{case_id}/build` | `{source_id?}` | `CaseHandoff.to_view()` |
| POST | `/api/cases/{case_id}/query` | `{question}` | answer dict |
| POST | `/api/cases/{case_id}/review` | review action | `CaseHandoff.to_view()` |
| POST | `/api/sessions` | `{case_id, learner_name}` | `{session_id, state}` |
| GET | `/api/sessions/{sid}` | — | session JSON (attempt results so far) |
| POST | `/api/sessions/{sid}/attempts` | multipart `kind`, `file`, optional `raster`, optional `video` | `AttemptResult.to_json()` |
| POST | `/api/sessions/{sid}/complete` | — | `SessionResult.to_json()` |
| GET | `/api/media/{case_id}/{source_id}` | — | media bytes (committed/cached source; uploads under the derived case) |
| GET | `/api/media/{case_id}/goal/{asset}` | — | goal assets (e.g. origami keyframe JPEGs) |
| GET | `/` | — | built React app (`app/dist`) |
