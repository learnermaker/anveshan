# Anveshan Track A — Deep Dive Technical Report

> **Purpose**: Authoritative source-code reference for the Anveshan Track A pipeline,
> all frozen schema contracts, and integration surface for the FoldingAgent hybrid.
> **Status**: Read-only research. No source files were modified.
> **Date**: 2025

---

## Table of Contents

1. [TrackAPipeline — Constructor and run() Method](#1-trackapipeline--constructor-and-run-method)
2. [ModelGateway and GeminiProviderAdapter](#2-modelgateway-and-geminiproviderapapter)
3. [KnowledgePackage Schema — Every Field](#3-knowledgepackage-schema--every-field)
4. [EvidenceRef Schema — Every Field](#4-evidenceref-schema--every-field)
5. [RubricDefinition Schema — Criteria Structure](#5-rubricdefinition-schema--criteria-structure)
6. [PracticeTask Schema — Every Field](#6-practicetask-schema--every-field)
7. [Epistemic Discipline — OBSERVED / INFERRED / UNVERIFIED](#7-epistemic-discipline--observed--inferred--unverified)
8. [Expert Review State](#8-expert-review-state)
9. [Consent / Provenance Chain](#9-consent--provenance-chain)
10. [Lineage / Transmission Record](#10-lineage--transmission-record)
11. [Prompt Templates — Variables and Rendered Form](#11-prompt-templates--variables-and-rendered-form)
12. [Fixture / Replay Mechanism — ENGINEERING_FIXTURE](#12-fixture--replay-mechanism--engineering_fixture)
13. [Case Pack Structure — Origami Case Files and Schemas](#13-case-pack-structure--origami-case-files-and-schemas)
14. [Frozen Seam Contracts — Track B Handoff](#14-frozen-seam-contracts--track-b-handoff)
15. [Q&A — Integration Answers](#15-qa--integration-answers)

---

## 1. TrackAPipeline — Constructor and run() Method

### File: `tracks/track-a/src/pipeline.py`

### Constructor

```python
class TrackAPipeline:
    def __init__(
        self,
        cases_root: Path,
        mode: Literal["replay", "live"] = "replay",
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
```

| Parameter | Type | Purpose |
|---|---|---|
| `cases_root` | `Path` | Root directory for all case packs (e.g. `tracks/cases/`) |
| `mode` | `"replay"` \| `"live"` | Determines which provider adapter is wired |
| `model_id` | `str \| None` | Passed through to `ModelGateway` for live Gemini model selection |
| `api_key` | `str \| None` | Passed through for live API key; falls back to `GEMINI_API_KEY` env var |

On construction, four collaborating objects are created:

```python
self.gateway             = ModelGateway(cases_root, mode, model_id, api_key)
self.grounding           = GroundingService()
self.expert_review_service = ExpertReviewService()
self.task_generator      = TaskGenerator()
```

`ModelGateway` itself immediately wires either a `ReplayProviderAdapter` or `GeminiProviderAdapter` (see §2). The grounding, review, and task-generator objects are stateless helpers.

### run() Method

```python
def run(
    self,
    case_id: str,
    enforce_approved: bool = False,
) -> TrackAOutputBundle:
```

**REPLAY PATH** (activated when `mode == "replay"`):

1. `load_manifest(cases_root, case_id)` → `CaseManifest`
2. `load_replay_bundle(cases_root, case_id)` → raw Python dict from `cases/<case_id>/replay/bundle.json`
3. Extract `pkg_raw`, `rubric_raw`, `task_raw` — raises `MISSING_EVIDENCE` if any are absent
4. `KnowledgePackage.model_validate(pkg_raw)` — Pydantic validation; preserves canonical IDs
5. `RubricDefinition.model_validate(rubric_raw)`
6. `PracticeTask.model_validate(task_raw)`
7. `GroundingService.validate_package_grounding(package, transmission_mode)` → returns `uncertainty_flags: List[str]`
8. Build `RunMetadataDTO(runtime_class="REPLAY", provider="replay", ...)`
9. Shared review gate (if `enforce_approved`) → raises `HUMAN_REVIEW_REQUIRED`
10. `validate_practice_task_against_knowledge_and_rubric(practice_task, package, rubric)` → raises `CONTRACT_VIOLATION` on cross-contract errors
11. Return `TrackAOutputBundle`

**LIVE PATH** (activated when `mode == "live"`):

1. `load_manifest(cases_root, case_id)` → `CaseManifest`
2. `ModelGateway.extract_knowledge(case_id)` → `ExtractionResponseDTO`
3. Build placeholder `ConsentMetadata(consent_scope="placeholder_no_real_consent")`
4. `normalize_dto_to_knowledge_package(dto, consent)` → `KnowledgePackage`
5. `GroundingService.validate_package_grounding(package, transmission_mode)`
6. `TaskGenerator.generate_rubric(package, case_id=case_id)`
7. `TaskGenerator.generate_practice_task(package, rubric, case_id=case_id)`
8. Shared review gate + cross-contract validation
9. Return `TrackAOutputBundle`

### TrackAOutputBundle Fields

```python
@dataclass
class TrackAOutputBundle:
    package:          KnowledgePackage
    rubric:           RubricDefinition
    practice_task:    PracticeTask
    run_metadata:     RunMetadataDTO
    manifest:         CaseManifest
    consent_summary:  ConsentMetadata   # alias for package.consent
    uncertainty_summary: List[str]      # INFERRED claim IDs from grounding
    replay_command:   str               # CLI replay command string
```

---

## 2. ModelGateway and GeminiProviderAdapter

### File: `tracks/track-a/src/gateway.py` + `providers.py`

### ModelGateway

`ModelGateway` is a **thin router** with two public methods:

```python
def extract_knowledge(case_id, prompt_version="v1") -> ExtractionResponseDTO
def query_evidence(package, question) -> Tuple[str, List[EvidenceRef]]
```

It adds:
- Telemetry: `start_t = time.perf_counter()` wrapper
- Run ID assignment if the DTO's `run_metadata.run_id` is empty
- Error wrapping: any non-`TrackAFailure` exception is re-raised as `FailureCategory.MODEL_FAILURE`

### GeminiProviderAdapter.extract_knowledge()

The live adapter executes a precise 5-step sequence:

**Step 1 — Media discovery and upload:**
```python
media_service = MediaService(cases_root, client)
media_descriptor = media_service.discover_media(case_id)       # reads manifest.source_media
local_path = media_service.resolve_media_path(case_id, desc)   # downloads URL if needed
gemini_file = media_service.upload_to_gemini(local_path, mime_type)  # polls until ACTIVE
```

**Step 2 — Prompt rendering:**
```python
prompt_engine = PromptEngine()
rendered_prompt = prompt_engine.load_extraction_prompt(manifest, version=prompt_version)
```
Variables filled: `{case_domain}`, `{case_title}`, `{transmission_mode}`.
Template chosen by `manifest.transmission_mode`: `forward` → `expert_extraction_v1.txt`,
`goal-conditioned` → `goal_conditioned_extraction_v1.txt`, `corrective` → `corrective_extraction_v1.txt`.

**Step 3 — Gemini API call:**
```python
client.models.generate_content(
    model=self.model_id,
    contents=[gemini_file, rendered_prompt],
    config=GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=GeminiExtractionResponse,
        temperature=0.1,
    ),
)
```
Wrapped in `with_gemini_retry(fn, max_retries=3, backoff_base=2.0)`.

**Step 4 — Parse response:**
`response.parsed` must be a `GeminiExtractionResponse` instance, otherwise
raises `MODEL_FAILURE`.

**Step 5 — Map to DTO:**
`_map_to_dto(extracted, case_id, manifest, prompt_version)` converts
every field from the Gemini-facing schema to the internal `ExtractionResponseDTO`.
The `run_id` pattern is: `f"run_live_{case_id}_{int(time.time())}_{uuid4().hex[:8]}"`.

**Cleanup (always runs in `finally`):**
`media_service.cleanup(gemini_file.name)` — deletes the uploaded file from Gemini Files API.

### GeminiProviderAdapter.query_evidence()

1. Renders all `package.claims` as a flat text block with claim IDs and timestamps
2. Loads `adversarial_query_v1.txt` prompt
3. Calls Gemini with `GeminiQueryResponse` schema, `temperature=0.0`
4. If `has_sufficient_evidence == False` → raises `MISSING_EVIDENCE`
5. Resolves `cited_claim_ids` → real `EvidenceRef` objects from the package
6. Returns `(answer, evidence_refs)` tuple

### GeminiExtractionResponse (model-facing schema)

```python
class GeminiExtractionResponse(BaseModel):
    title: str
    summary: str
    steps: List[GeminiStepSchema]              # forward mode
    cues: List[GeminiCueSchema]                # all modes
    conditions: List[GeminiConditionSchema]    # all modes
    exceptions: List[GeminiExceptionSchema]    # all modes
    failure_modes: List[GeminiFailureModeSchema]  # all modes
    target_properties: List[GeminiTargetPropertySchema]  # goal-conditioned
    divergences: List[GeminiDivergenceSchema]    # corrective
```

This schema is intentionally lean — it does NOT contain `case_id`, `skill_id`,
`run_metadata`, or `source_media_id`. Those are all injected by `_map_to_dto()` to
prevent hallucination and token waste.

---

## 3. KnowledgePackage Schema — Every Field

### File: `tracks/common/schemas/knowledge.py`

### KnowledgePackage

| Field | Type | Required | Constraints / Notes |
|---|---|---|---|
| `package_id` | `str` | **Required** | Unique identifier. Canonical pattern: `kp.<case_id>.<version>` (e.g. `kp.origami.1`). Set by `generate_package_id()`. |
| `skill_id` | `str` | **Required** | Target skill (e.g. `skill-origami-crane`). Must match rubric `skill_id`. |
| `title` | `str` | **Required** | Descriptive title (e.g. `"Bird Base Petal Fold Crease Inversion Sequence"`). |
| `summary` | `str` | **Required** | Concise synopsis of the demonstrated procedure. |
| `claims` | `List[KnowledgeClaim]` | **Required** | `min_length=1`. Structured claims with provenance. Model validator checks for duplicate `claim_id` values. |
| `consent` | `ConsentMetadata` | **Required** | Contributor consent record. See §9. |
| `expert_review` | `Optional[ExpertReview]` | Optional | Human-in-the-loop review gate. `None` is allowed; `enforce_approved=True` in `run()` requires it to be `APPROVED`. |

### KnowledgeClaim

| Field | Type | Required | Constraints |
|---|---|---|---|
| `claim_id` | `str` | **Required** | Unique within package. Pattern: `CLM-01`, `CLM-02`, etc. (or canonical IDs from bundle like `claim-prelim-square`). |
| `claim_type` | `ClaimType` | **Required** | Enum: `step` \| `cue` \| `condition` \| `exception` \| `failure_mode` |
| `statement` | `str` | **Required** | Verbatim or concise description of extracted knowledge. |
| `is_observed` | `bool` | **Required** (default `True`) | `True` = directly observed in source media; `False` = model inference. Must be consistent with `evidence_refs[*].verification_state`. |
| `evidence_refs` | `List[EvidenceRef]` | **Required** | `min_length=1`. At least one EvidenceRef backing the claim. |

### ClaimType Enum

```python
class ClaimType(str, Enum):
    STEP         = "step"
    CUE          = "cue"
    CONDITION    = "condition"
    EXCEPTION    = "exception"
    FAILURE_MODE = "failure_mode"
```

---

## 4. EvidenceRef Schema — Every Field

### File: `tracks/common/schemas/evidence.py`

| Field | Type | Required | Constraints / Notes |
|---|---|---|---|
| `evidence_id` | `str` | **Required** | Unique locator ID. Pattern: `ev.<case_id>.<prefix>.<seq:02d>` (e.g. `ev.origami.step.01`). For origami: canonical stable IDs are `ev-origami-base`, `ev-origami-petal` in replay bundle. |
| `source_id` | `str` | **Required** | Identifier of the source media or file (e.g. URI, file hash). For origami: stable ID is `src-origami-tavin-2010`. |
| `modality` | `Modality` | **Required** | Enum: `video` \| `audio` \| `image` \| `text` \| `sensor` |
| `start_sec` | `Optional[float]` | Optional | Start timestamp in seconds from beginning of media. `ge=0.0`. |
| `end_sec` | `Optional[float]` | Optional | End timestamp in seconds. `ge=0.0`. Model validator enforces `end_sec >= start_sec`. |
| `cue_excerpt` | `Optional[str]` | Optional | Observable transcript excerpt or visual description (e.g. `"Crease polarity matches diagram: convex ridge vs concave trough"`). |
| `verification_state` | `VerificationState` | **Required** (default `OBSERVED`) | Enum: `observed` \| `inferred` \| `unverified`. Must be consistent with parent claim's `is_observed`. |
| `confidence` | `float` | **Required** (default `1.0`) | Calibration score. `ge=0.0`, `le=1.0`. Inferred claims: capped at `0.5` by `GroundingService`. |

### VerificationState Enum

```python
class VerificationState(str, Enum):
    OBSERVED   = "observed"
    INFERRED   = "inferred"
    UNVERIFIED = "unverified"
```

### Modality Enum

```python
class Modality(str, Enum):
    VIDEO  = "video"
    AUDIO  = "audio"
    IMAGE  = "image"
    TEXT   = "text"
    SENSOR = "sensor"
```

### Temporal Validation Rule

The `@model_validator(mode="after")` in `EvidenceRef` enforces:

```python
if start_sec is not None and end_sec is not None:
    if end_sec < start_sec:
        raise ValueError(...)
```

`GroundingService.validate_intervals()` adds a runtime check:
negative `start_sec` raises `CONTRACT_VIOLATION`.

---

## 5. RubricDefinition Schema — Criteria Structure

### File: `tracks/common/schemas/rubric.py`

### RubricDefinition

| Field | Type | Required | Constraints |
|---|---|---|---|
| `rubric_id` | `str` | **Required** | Unique rubric ID. Pattern: `rubric.<case_id>.<version>`. |
| `skill_id` | `str` | **Required** | Must match `KnowledgePackage.skill_id`. |
| `title` | `str` | **Required** | Human-readable title. |
| `description` | `Optional[str]` | Optional | Context, scope, or evaluation instructions. |
| `criteria` | `List[RubricCriterion]` | **Required** | `min_length=1`. Model validator checks for duplicate `criterion_id`. |
| `passing_score` | `Optional[float]` | Optional | `ge=0.0`. Must not exceed `sum(criterion.weight for c in criteria)`. If `None`, pass requires all required criteria satisfied. |

### RubricCriterion

| Field | Type | Required | Constraints |
|---|---|---|---|
| `criterion_id` | `str` | **Required** | Unique within rubric. Free-form but conventionally uppercase with hyphens (e.g. `CRIT-VALLEY-FOLD`). |
| `name` | `str` | **Required** | Short descriptive name. |
| `description` | `str` | **Required** | What the learner is expected to demonstrate. |
| `observable_indicator` | `str` | **Required** | **Concrete, observable cue or physical indicator to verify.** This is the key field for measurable assessment. See §5.1 for origami examples. |
| `weight` | `float` | **Required** (default `1.0`) | `gt=0.0`. Maximum points achievable. Acts as criterion scale. |
| `required` | `bool` | **Required** (default `True`) | If `True`, must be `SATISFIED` for overall pass even if `passing_score` threshold is met. |

### 5.1 Origami observable_indicator Examples (from canonical bundle)

The origami bundle (`replay/bundle.json`) has three criteria:

| criterion_id | observable_indicator |
|---|---|
| `CRIT-CORNER-ALIGN` | `"Visible gap between overlaying paper corners <= 1.0mm."` |
| `CRIT-VALLEY-FOLD` | `"Crease polarity matches diagram: convex ridge vs concave trough."` |
| `CRIT-BONE-CREASE` | `"Flap thickness profile compressed; zero springback."` |

These are **measurement-grounded indicators** — each describes something physically observable or measurable, not a subjective judgment.

### 5.2 TaskGenerator — Synthetic Criteria (live mode only)

When the `TaskGenerator` synthesizes criteria in live mode, it generates generic IDs (`CRIT-01`, `CRIT-02`, etc.) and sets `observable_indicator` to the claim's `cue_excerpt` from the first `EvidenceRef`. This does NOT produce the canonical origami criteria — those come only from the replay bundle.

---

## 6. PracticeTask Schema — Every Field

### File: `tracks/common/schemas/practice.py`

| Field | Type | Required | Constraints |
|---|---|---|---|
| `task_id` | `str` | **Required** | Unique ID. Pattern: `task.<case_id>.<version>`. |
| `package_id` | `str` | **Required** | ID of `KnowledgePackage` being practiced. Cross-validated against rubric and package. |
| `rubric_id` | `str` | **Required** | ID of `RubricDefinition` used for evaluation. Must match rubric. |
| `title` | `str` | **Required** | Title of the practice assignment. |
| `instructions` | `str` | **Required** | Clear step-by-step instructions for the learner. |
| `constraints` | `List[TaskConstraint]` | Optional (default `[]`) | Physical, temporal, or material constraints. |
| `target_criteria_ids` | `List[str]` | Optional (default `[]`) | Optional list of specific rubric `criterion_id`s targeted. Cross-validated against rubric — unknown IDs raise `CONTRACT_VIOLATION`. |

### TaskConstraint

| Field | Type | Required | Notes |
|---|---|---|---|
| `constraint_type` | `str` | **Required** | e.g. `"time_limit"`, `"tool_spec"`, `"material_spec"`, `"safety"`, `"material"` |
| `description` | `str` | **Required** | Explanation of the constraint. |
| `value` | `Optional[str]` | Optional | Quantified value if applicable (e.g. `"60s"`, `"150mm"`). |

### Origami Practice Task (from canonical bundle)

```json
{
  "task_id": "task-origami-crane",
  "package_id": "pkg-origami-006",
  "rubric_id": "rubric-origami-006",
  "title": "Fold Perfect Crane Bird Base",
  "instructions": "Using 15cm kami paper, fold preliminary square, pre-crease side wings, and open into diamond bird base with symmetrical petal flaps.",
  "constraints": [{"constraint_type": "material", "description": "Standard 150mm square kami paper"}],
  "target_criteria_ids": ["CRIT-CORNER-ALIGN", "CRIT-VALLEY-FOLD", "CRIT-BONE-CREASE"]
}
```

---

## 7. Epistemic Discipline — OBSERVED / INFERRED / UNVERIFIED

### File: `tracks/track-a/src/grounding.py` + `tracks/common/schemas/evidence.py`

### The Three States

| Value | Meaning | Confidence Constraint | When Used |
|---|---|---|---|
| `OBSERVED` (`observed`) | Directly observed in source media — visible action, audible cue, or readable text | `0.0–1.0` (usually `1.0`) | Step events with clear timestamps; physical indicators visible in video |
| `INFERRED` (`inferred`) | Model's interpretation — not directly visible/audible | Must be `≤ 0.5` in goal-conditioned mode; enforced at `0.5` in normalizer | Exceptions, failure modes, unobserved procedures |
| `UNVERIFIED` (`unverified`) | Not established — no supporting evidence | — | Not currently generated by the pipeline automatically; reserved for future use |

### Where They Appear

1. **`EvidenceRef.verification_state`** — on every evidence locator
2. **`KnowledgeClaim.is_observed`** — boolean on every claim (`True` ↔ OBSERVED, `False` ↔ INFERRED)

### How They Are Enforced

**Normalizer (`models.py::normalize_dto_to_knowledge_package`):**

| Source DTO type | `is_observed` | `verification_state` | `confidence` |
|---|---|---|---|
| Step | `True` | `OBSERVED` | `1.0` |
| Cue (sufficiency=OBSERVED) | `True` | `OBSERVED` | `1.0` |
| Cue (sufficiency=PARTIAL/UNKNOWN) | `False` | `INFERRED` | `0.5` |
| Target property (goal-conditioned, OBSERVED) | `True` | `OBSERVED` | `1.0` |
| Target property (PARTIAL/UNKNOWN) | `False` | `INFERRED` | `0.5` |
| Condition | `True` | `OBSERVED` | `1.0` |
| Exception | `False` | `INFERRED` | `0.5` |
| Failure mode | `False` | `INFERRED` | `0.5` |
| Divergence (OBSERVED) | `True` | `OBSERVED` | `1.0` |
| Divergence (PARTIAL/UNKNOWN) | `False` | `INFERRED` | `0.5` |

**GroundingService (`grounding.py::enforce_epistemological_state`):**

For **forward and corrective** mode:
- If `claim.is_observed == False` but `ev.verification_state == OBSERVED` → `CONTRACT_VIOLATION`

For **goal-conditioned** mode:
- If `claim.is_observed == False`:
  - `ev.verification_state == OBSERVED` → `CONTRACT_VIOLATION`
  - `ev.confidence > 0.5` → `CONTRACT_VIOLATION`

**Uncertainty summary:**
`validate_package_grounding()` returns a list of strings for every claim where either
`is_observed == False` or any evidence ref has `verification_state == INFERRED`.
These appear in `TrackAOutputBundle.uncertainty_summary`.

---

## 8. Expert Review State

### File: `tracks/common/schemas/knowledge.py` + `tracks/track-a/src/expert_review.py`

### ExpertReview Model

| Field | Type | Required | Notes |
|---|---|---|---|
| `reviewer_name` | `str` | **Required** | Name of reviewing domain expert. |
| `status` | `ReviewStatus` | **Required** (default `PENDING`) | See table below. |
| `reviewed_at` | `Optional[str]` | Optional | ISO timestamp of review. |
| `notes` | `Optional[str]` | Optional | Feedback, required corrections, or approval rationale. |

### ReviewStatus Enum

```python
class ReviewStatus(str, Enum):
    PENDING  = "pending"   # Submitted, awaiting expert inspection
    APPROVED = "approved"  # Expert confirmed extraction fidelity
    REVISED  = "revised"   # Expert corrected one or more claims
    REJECTED = "rejected"  # Expert rejected extraction — fundamental error
```

### Lifecycle Transitions (ExpertReviewService)

| Method | Sets status to | Notes |
|---|---|---|
| `submit_for_review(pkg, reviewer_name)` | `PENDING` | Entry point |
| `approve_package(pkg, reviewer_name)` | `APPROVED` | Confirms fidelity |
| `revise_claim(pkg, claim_id, new_statement, reviewer_name)` | `REVISED` | Mutates claim statement + review |
| `reject_package(pkg, reviewer_name, reason)` | `REJECTED` | Records failure reason |

### Production Gate

In `TrackAPipeline.run(enforce_approved=True)`:
- If `package.expert_review is None` OR `status != APPROVED` → raises `HUMAN_REVIEW_REQUIRED`
- Default is `enforce_approved=False` — production-ready handoff requires explicit opt-in

### Current Origami State

The canonical origami bundle has:
```json
"expert_review": {
  "reviewer_name": "Replay Fixture Reviewer",
  "status": "pending",
  "reviewed_at": "2026-09-16T12:00:00Z"
}
```
This is an **ENGINEERING_FIXTURE** — not authentic validation. The replay passes grounding checks but cannot be promoted to `AUTHENTIC_SOURCE_READY` without a real expert approval.

### Markdown Export

`ExpertReviewService.export_markdown(package, manifest)` produces a human-readable inspection sheet with:
- Package metadata, domain, archetype, transmission mode
- Contributor consent summary
- Review status header
- Full claims table: `claim_id | claim_type | OBSERVED/INFERRED | statement | evidence locators with timestamps`
- Signature checkboxes: `[ ] APPROVE  [ ] REVISE  [ ] REJECT`

---

## 9. Consent / Provenance Chain

### File: `tracks/common/schemas/knowledge.py`

### ConsentMetadata

| Field | Type | Required | Notes |
|---|---|---|---|
| `contributor_name` | `str` | **Required** | Name or identifier of the knowledge contributor/expert. |
| `consent_scope` | `str` | **Required** | Agreed scope of use. Values in practice: `"hackathon_prototype"`, `"educational_research"`, `"engineering_replay_only"`, `"placeholder_no_real_consent"` |
| `revocable` | `bool` | Optional (default `True`) | Whether contributor retains right of withdrawal. |
| `granted_at` | `Optional[str]` | Optional | ISO timestamp of consent confirmation. |
| `notes` | `Optional[str]` | Optional | Specific restrictions, community caveats, or notes. |

### Origami Consent

The origami fixture has:
```json
"consent": {
  "contributor_name": "Synthetic Fixture Contributor",
  "consent_scope": "engineering_replay_only",
  "revocable": true,
  "granted_at": "2026-09-08T11:00:00Z"
}
```

### Live Mode Consent Gap

The live path (`pipeline.py`) creates:
```python
consent = ConsentMetadata(
    contributor_name=f"Expert for {case_id}",
    consent_scope="placeholder_no_real_consent",
)
```
This is acknowledged as a placeholder and must be replaced before `status=AUTHENTIC_SOURCE_READY`.

### Provenance Chain in Practice

The full provenance chain flows through:
1. **Source**: `manifest.json::source_media.attribution` → `"Tavin, CC BY 3.0, ..."`
2. **Evidence**: `EvidenceRef.source_id` → `"src-origami-tavin-2010"` (canonical stable ID)
3. **Consent**: `KnowledgePackage.consent.contributor_name` + `consent_scope`
4. **Review**: `KnowledgePackage.expert_review.reviewer_name` + `status`
5. **Transmission**: `TransmissionRecord.lineage.provenance_hash` → SHA-256 of artifacts
6. **Lineage notes**: `TransmissionRecord.lineage.adaptation_notes`

---

## 10. Lineage / Transmission Record

### File: `tracks/common/schemas/transmission.py`

### TransmissionRecord (immutable proof artifact)

| Field | Type | Required | Notes |
|---|---|---|---|
| `transmission_id` | `str` | **Required** | Unique event ID (e.g. `tx-origami-006`). |
| `skill_id` | `str` | **Required** | Target skill. Must match `RubricDefinition.skill_id`. |
| `package_id` | `str` | **Required** | `KnowledgePackage` ID used. |
| `rubric_id` | `str` | **Required** | `RubricDefinition` ID applied. |
| `expert_id` | `str` | **Required** | Expert source identity. |
| `learner_id` | `str` | **Required** | Learner identity. |
| `baseline_attempt_id` | `str` | **Required** | `LearnerAttempt` ID for pre-training. |
| `retry_attempt_id` | `str` | **Required** | `LearnerAttempt` ID for post-feedback. |
| `baseline_score` | `float` | **Required** | `ge=0.0`. Must match `baseline_eval.total_score`. |
| `retry_score` | `float` | **Required** | `ge=0.0`. Must match `retry_eval.total_score`. |
| `transmission_gain` | `float` | **Required** | Must equal `retry_score - baseline_score` (±1e-4). Enforced by `@model_validator`. |
| `criteria_improved` | `List[str]` | Optional (default `[]`) | Criterion IDs with `retry_score > baseline_score`. Validated against rubric. |
| `lineage` | `LineageMetadata` | **Required** | Provenance and evolution metadata. |

### LineageMetadata

| Field | Type | Required | Notes |
|---|---|---|---|
| `parent_transmission_id` | `Optional[str]` | Optional | For evolutionary lineage chains. |
| `recorded_at` | `str` | **Required** | ISO timestamp. |
| `provenance_hash` | `Optional[str]` | Optional | SHA-256 or content hash. Origami: `"sha256-origami-merkle-6f5e4d3c"` |
| `adaptation_notes` | `Optional[str]` | Optional | Technique adaptation notes. Origami: `"Sequential step-by-step 3D origami vector state sequence prevented fold crinkling."` |

### Deterministic Gain Rule

`transmission_gain` is computed as `retry_score - baseline_score`, NOT produced by a model.
The `@model_validator` enforces this with a tolerance of `1e-4`. Any deviation raises a `ValueError` at parse time.

---

## 11. Prompt Templates — Variables and Rendered Form

### File: `tracks/track-a/src/prompt_engine.py` + `tracks/track-a/prompts/*.txt`

### PromptEngine Dispatch Logic

```python
def load_extraction_prompt(manifest, version="v1") -> str:
    mode = manifest.transmission_mode
    if mode == "goal-conditioned":
        filename = f"goal_conditioned_extraction_{version}.txt"
    elif mode == "corrective":
        filename = f"corrective_extraction_{version}.txt"
    else:
        filename = f"expert_extraction_{version}.txt"
    # Falls back to expert_extraction_v1.txt if target file missing
```

### render() — Variable Substitution

Three variables are substituted in every template:

```python
template.replace("{case_domain}", manifest.domain)
        .replace("{case_title}",  manifest.title)
        .replace("{transmission_mode}", manifest.transmission_mode)
```

### 11.1 expert_extraction_v1.txt (used for origami)

**Template variables** → rendered for origami:
- `{case_domain}` → `"Mathematical Origami & Computational Paper Geometry"`
- `{case_title}` → `"Origami Crane Petal Folding"`
- `{transmission_mode}` → `"forward"`

**Rendered opening:**
```
You are an expert knowledge extraction agent analyzing a multimodal physical demonstration.
Domain context: Mathematical Origami & Computational Paper Geometry — Origami Crane Petal Folding
Transmission mode: forward
```

**What it extracts:**
- Steps: `index`, `title`, `description`, `start_sec`, `end_sec` (0.1s resolution)
- Cues: `modality`, `statement`, `observable_indicator`, `start_sec`, `end_sec`, `evidence_sufficiency`
- Conditions: `statement`, `tools_or_materials`
- Exceptions: `condition_trigger`, `alternative_action`
- Failure modes: `symptom`, `mistake_description`, `severity`

**Strict rules in template:**
1. Never guess or infer without directly observable action
2. Mark non-obvious procedures with `evidence_sufficiency="PARTIAL"` or `"UNKNOWN"`
3. Cite timestamps at 0.1s resolution
4. Response must conform to provided JSON schema

**Gap for origami:** This generic prompt does NOT request origami-specific vocabulary — no mountain/valley fold distinction, no crease geometry, no paper state names (flat square → preliminary base → bird base), no bone-folder technique. An `origami_extraction_v1.txt` would be needed for high-quality live extraction.

### 11.2 goal_conditioned_extraction_v1.txt

Used for Kolam case. Extracts:
- `target_properties`: `property_id`, `description`, `evidence_sufficiency=OBSERVED`, `measurement`
- Candidate procedures: tagged `PARTIAL` or `UNKNOWN`, confidence ≤ 0.5

**Strict rules:** Never assert expert intention from a static artifact. Maintain OBSERVED vs PARTIAL/UNKNOWN boundary.

### 11.3 corrective_extraction_v1.txt

Used for corrective mode cases. Extracts:
- `divergences`: `criterion_id`, `observed_behavior`, `expected_behavior`, `timestamp_sec`, `evidence_sufficiency`

**Strict rules:** Link every divergence to a rubric criterion ID.

### 11.4 adversarial_query_v1.txt

**Used by:** `GeminiProviderAdapter.query_evidence()` and `EvidenceQueryService`.

Content:
```
You are an evidence retrieval assistant answering a technical question about an expert demonstration.
...
Strict Rules:
- If the question asks about a condition NOT documented in the claims:
  set has_sufficient_evidence=false and respond:
  "INSUFFICIENT_EVIDENCE: The expert demonstration does not show or document this condition."
- Do not use pre-trained general world knowledge to fill in gaps.
```

No template variables — it is loaded as-is and receives the claims context injected programmatically.

---

## 12. Fixture / Replay Mechanism — ENGINEERING_FIXTURE

### Files: `case_registry.py`, `pipeline.py`, `providers.py`

### ENGINEERING_FIXTURE Semantics

A case with `manifest.status = "ENGINEERING_FIXTURE"` is a **synthetic deterministic fixture**:
- `runtime_class = "REPLAY"` — never calls live APIs
- `source_posture = "synthetic_replay"` or `"external_reference"` — not authenticated expert footage
- `epistemic_status = "EXTERNAL_SOURCE_AVAILABLE_REPLAY_NOT_AUTHENTIC_VALIDATION"` — for origami

### What Data it Reads

1. `tracks/cases/<case_id>/manifest.json` → loaded by `load_manifest()`
2. `tracks/cases/<case_id>/replay/bundle.json` → loaded by `load_replay_bundle()`

The bundle is a **single JSON file** containing all 8 contracts (or a subset for Track A use):
- `knowledge_package` → directly `model_validate()`d into `KnowledgePackage`
- `rubric` → directly `model_validate()`d into `RubricDefinition`
- `practice_task` → directly `model_validate()`d into `PracticeTask`
- Plus (not loaded by Track A pipeline, but present for Track B / validator): `baseline_attempt`, `baseline_evaluation`, `feedback`, `retry_attempt`, `retry_evaluation`, `transmission_record`

### Semantic Validation Rules on Manifest (validate_manifest_semantics)

Four rules enforced by `case_registry.py`:

1. `runtime_class=REPLAY` cannot have `status=AUTHENTIC_SOURCE_READY`
2. `status=AUTHENTIC_SOURCE_READY` requires `source_posture=authentic_expert` AND `runtime_class=AUTHENTIC`
3. `runtime_class=AUTHENTIC` cannot have `status=ENGINEERING_FIXTURE`
4. `source_posture=synthetic_replay` requires `runtime_class=REPLAY` AND `status=ENGINEERING_FIXTURE`

### ReplayProviderAdapter vs Direct Load

In REPLAY mode, `TrackAPipeline.run()` **bypasses the ModelGateway entirely** and directly
calls `load_replay_bundle()`. The `ReplayProviderAdapter.extract_knowledge()` path (going
through `ExtractionResponseDTO` → `normalize_dto_to_knowledge_package()`) is used only if
`ModelGateway.extract_knowledge()` is called in REPLAY mode externally — the pipeline does
NOT use this path; it validates the canonical contracts directly to preserve canonical IDs.

### RunMetadata for REPLAY

```python
RunMetadataDTO(
    provider="replay",
    model_id="canonical-replay-fixture",
    runtime_class="REPLAY",
    run_id=f"run_replay_{case_id}",
    expected_behavior="Authoritative canonical contract preservation",
    evaluation_reference=f"tracks/cases/{case_id}/replay/bundle.json",
)
```

---

## 13. Case Pack Structure — Origami Case Files and Schemas

### Directory: `tracks/cases/origami/`

```
tracks/cases/origami/
├── manifest.json            ← CaseManifest (entry point)
├── README.md
├── knowledge/
│   └── README.md            ← Notes only; knowledge is in replay bundle
├── media/
│   └── README.md            ← No media committed; URL in manifest
├── practice/
│   └── README.md            ← Notes only; practice task in replay bundle
├── replay/
│   └── bundle.json          ← ALL 8 contracts as one document
└── source/
    └── README.md            ← Canonical source conventions and stable IDs
```

### manifest.json Fields (Origami)

```json
{
  "schema_version": "1.0",
  "case_id": "origami",
  "bundle_case_id": "origami_case_006",
  "title": "Origami Crane Petal Folding",
  "domain": "Mathematical Origami & Computational Paper Geometry",
  "archetype": "sequential-spatial-transformation",
  "workspace_type": "fold_sequence",
  "transmission_mode": "forward",
  "source_posture": "external_reference",
  "epistemic_status": "EXTERNAL_SOURCE_AVAILABLE_REPLAY_NOT_AUTHENTIC_VALIDATION",
  "data_status": "external_source_catalogued_replay_bundle",
  "pack_version": "1.1",
  "case_version": "1.1",
  "status": "ENGINEERING_FIXTURE",
  "source_mode": "FORWARD",
  "runtime_class": "REPLAY",
  "source_media": {
    "type": "url",
    "url": "https://upload.wikimedia.org/...OrigamiCrane.ogv.480p.webm",
    "mime_type": "video/webm",
    "attribution": "Tavin, CC BY 3.0, ..."
  }
}
```

### replay/bundle.json — Complete Contents

The origami bundle contains:

**knowledge_package** (`pkg-origami-006`):
- 2 claims: `claim-prelim-square` (step, t=10–22s) and `claim-petal-inversion` (step, t=25–38s)
- Source ID (synthetic): `src-origami-01` — **NOT** the stable ID `src-origami-tavin-2010`
- Consent: `engineering_replay_only`
- Expert review: `status: pending`

**rubric** (`rubric-origami-006`):
- 3 criteria: `CRIT-CORNER-ALIGN` (weight=3, required), `CRIT-VALLEY-FOLD` (weight=4, required), `CRIT-BONE-CREASE` (weight=3, not required)
- `passing_score: 7` out of max 10

**practice_task** (`task-origami-crane`):
- 150mm kami paper constraint
- Targets all 3 criteria

**baseline_attempt** (`attempt-origami-base`):
- `attempt_type: baseline`, `attempt_number: 1`
- Evidence: `src-chloe-origami-01`, t=0–45s

**baseline_evaluation** (`eval-origami-base`):
- `total_score: 5`, `passed: false`
- `CRIT-CORNER-ALIGN`: 2/3 (partially), `CRIT-VALLEY-FOLD`: 1/4 (not_satisfied), `CRIT-BONE-CREASE`: 2/3

**feedback** (`fb-origami-001`):
- Single item targeting `CRIT-VALLEY-FOLD`
- Advice: `"Pinch the side edges inward while pressing index finger behind paper to invert the mountain ridge into an inward valley."`

**retry_attempt** (`attempt-origami-retry`):
- `attempt_type: retry`, `attempt_number: 2`

**retry_evaluation** (`eval-origami-retry`):
- `total_score: 9.8`, `passed: true`

**transmission_record** (`tx-origami-006`):
- `transmission_gain: 4.8`
- `provenance_hash: "sha256-origami-merkle-6f5e4d3c"`
- `adaptation_notes: "Sequential step-by-step 3D origami vector state sequence prevented fold crinkling."`

### Stable Source IDs (from source/README.md)

| ID | Purpose | Constraint |
|---|---|---|
| `src-origami-tavin-2010` | Canonical ID for the Wikimedia demonstration video | Required for live extraction (NOT `src-origami-01` which is synthetic) |
| `ev-origami-demo` | Whole-video evidence ref | Use when no segment inspection has been done |
| `ev-origami-step-XX` | Per-segment evidence | **Only after actual video frame inspection** — no fabrication |

---

## 14. Frozen Seam Contracts — Track B Handoff

### File: `tracks/common/schemas/__init__.py`

The `__init__.py` explicitly lists the **8 root contracts** as the frozen cross-track seam:

```python
"""The 8 authoritative shared contracts for Anveshan parallel tracks.
Frozen cross-track contract seam:
1. EvidenceRef
2. KnowledgePackage
3. RubricDefinition
4. PracticeTask
5. LearnerAttempt
6. Evaluation
7. Feedback
8. TransmissionRecord
"""
```

### What Track A Produces and Track B Consumes

Track A **produces** (handoff bundle):
- `KnowledgePackage` — with canonical `package_id`, `skill_id`, `claims[]`, `consent`, `expert_review`
- `RubricDefinition` — with canonical `rubric_id`, `skill_id`, `criteria[]`, `passing_score`
- `PracticeTask` — bound to both via `package_id` and `rubric_id`

Track B **consumes** all three and additionally produces:
- `LearnerAttempt` (baseline + retry)
- `Evaluation` (baseline + retry)
- `Feedback`
- `TransmissionRecord`

### Fields / Types That CANNOT Change Without Breaking Track B Handoff

#### EvidenceRef (frozen fields)
- `evidence_id` — Track B uses to reference specific locators in feedback
- `source_id` — used in `FeedbackItem.expert_evidence_ref` for clip matching
- `modality` enum values — B evaluator type-switches on these
- `start_sec` / `end_sec` — B uses for video clip extraction
- `verification_state` enum values (`observed`/`inferred`/`unverified`)
- `confidence` range `[0.0, 1.0]`

#### KnowledgePackage (frozen fields)
- `package_id` — referenced by `PracticeTask.package_id` and `TransmissionRecord.package_id`
- `skill_id` — must match `RubricDefinition.skill_id` and `TransmissionRecord.skill_id`
- `claims[*].claim_id` — referenced by `EvidenceRef.evidence_id` patterns
- `claims[*].claim_type` enum values — B evaluator routes on `step`, `cue`, etc.
- `claims[*].evidence_refs` — `min_length=1` constraint cannot be weakened

#### RubricDefinition (frozen fields)
- `rubric_id` — referenced by `PracticeTask.rubric_id`, `Evaluation.rubric_id`, `TransmissionRecord.rubric_id`
- `skill_id` — must match `KnowledgePackage.skill_id`
- `criteria[*].criterion_id` — referenced by `Evaluation.criterion_results[*].criterion_id`, `Feedback.items[*].criterion_id`, `PracticeTask.target_criteria_ids`, `TransmissionRecord.criteria_improved`
- `criteria[*].weight` — `Evaluation.CriterionResult.score` must be ≤ weight
- `criteria[*].required` — determines pass/fail logic in `Evaluation`
- `passing_score` semantics — Track B scoring aggregation relies on this

#### PracticeTask (frozen fields)
- `task_id` — referenced by `LearnerAttempt.task_id`
- `package_id` — cross-validated against KnowledgePackage
- `rubric_id` — cross-validated against RubricDefinition
- `target_criteria_ids` — must be a subset of `rubric.criteria[*].criterion_id`

#### TransmissionRecord (frozen invariants)
- `transmission_gain = retry_score - baseline_score` (deterministic, not model-generated)
- Score provenance chain: `transmission_record.baseline_score` must equal `baseline_eval.total_score`

### AGENTS.md Single-Source Rule

From `AGENTS.md`:
> The eight shared contracts have exactly one authoritative source: `tracks/common/schemas/`.
> This includes field names, enum values, required/optional semantics, and validation meaning.
> UI/TypeScript must not invent, rename, broaden, or narrow the eight contract shapes.
> Contract changes require an explicit common-seam issue and must not be hidden inside a UI task.

---

## 15. Q&A — Integration Answers

### Q1: What is the minimum set of fields a KnowledgePackage MUST have to pass schema validation?

The minimum valid `KnowledgePackage` requires:

```python
KnowledgePackage(
    package_id  = "kp.demo.1",      # str, required
    skill_id    = "skill-demo",      # str, required
    title       = "Demo Skill",      # str, required
    summary     = "A summary.",      # str, required
    claims      = [                  # min_length=1, must be non-empty
        KnowledgeClaim(
            claim_id    = "CLM-01",          # str, required, unique
            claim_type  = ClaimType.STEP,    # required
            statement   = "Do something.",   # str, required
            is_observed = True,
            evidence_refs = [
                EvidenceRef(
                    evidence_id       = "ev.demo.step.01",  # required
                    source_id         = "src-demo",          # required
                    modality          = Modality.VIDEO,      # required
                    verification_state= VerificationState.OBSERVED,
                    confidence        = 1.0,
                )
            ]
        )
    ],
    consent = ConsentMetadata(
        contributor_name = "Expert A",    # str, required
        consent_scope    = "research",    # str, required
    ),
    # expert_review is Optional — may be omitted
)
```

**Summary of required fields:**
- `package_id`, `skill_id`, `title`, `summary` — all non-empty strings
- `claims` — list with ≥ 1 `KnowledgeClaim`, each with `claim_id` (unique), `claim_type`, `statement`, `evidence_refs` (≥ 1 `EvidenceRef`)
- Each `EvidenceRef` must have: `evidence_id`, `source_id`, `modality`
- `consent` with: `contributor_name`, `consent_scope`
- `expert_review` is Optional (defaults to `None`)

---

### Q2: What is the minimum valid EvidenceRef?

```python
EvidenceRef(
    evidence_id       = "ev.demo.01",        # required str
    source_id         = "src-demo",           # required str
    modality          = Modality.VIDEO,       # required Modality enum
    # start_sec, end_sec — Optional[float], may be None
    # cue_excerpt — Optional[str], may be None
    # verification_state defaults to VerificationState.OBSERVED
    # confidence defaults to 1.0
)
```

The three **required** fields are: `evidence_id`, `source_id`, `modality`.
All other fields have defaults or are optional. If both `start_sec` and `end_sec` are provided,
the validator enforces `end_sec >= start_sec`.

---

### Q3: What does a RubricCriterion's observable_indicator look like for origami?

Three examples from the canonical origami bundle:

```
CRIT-CORNER-ALIGN:
  observable_indicator: "Visible gap between overlaying paper corners <= 1.0mm."

CRIT-VALLEY-FOLD:
  observable_indicator: "Crease polarity matches diagram: convex ridge vs concave trough."

CRIT-BONE-CREASE:
  observable_indicator: "Flap thickness profile compressed; zero springback."
```

Pattern: each indicator is **a single observable, measurable physical state** — a gap measurement, a spatial polarity comparison, or a deformation property. It is NOT a procedure description. It describes what you can see, measure, or feel at the moment of evaluation.

For FoldingAgent integration, a geometry-grounded indicator could look like:
```
CRIT-VALLEY-FOLD:
  observable_indicator: "Edge [2,5] assigned valley (V) in simulator state; no mountain (M) edges 
                          on symmetry axis; faces_orientations[target_face] == 0."
```

---

### Q4: Which fields in EvidenceRef could be populated from FoldingAgent geometric output?

| EvidenceRef Field | FoldingAgent Source | How to Populate |
|---|---|---|
| `evidence_id` | Derived from frame index | `f"ev.origami.frame.{frame_n:02d}"` |
| `source_id` | From keyframes.json + video attribution | `"src-origami-tavin-2010"` for the video; `"src-fa-checkpoint"` for geometry artifacts |
| `modality` | `Modality.IMAGE` for rendered diagrams; `Modality.VIDEO` for video segments | Based on source type |
| `start_sec` | **YES** — via keyframe index → video timestamp mapping. `keyframes[frame_n]` is the global frame index; multiply by video FPS to get seconds. | `keyframes[frame_n] / fps` |
| `end_sec` | **YES** — same mapping; use next keyframe's timestamp as end | `keyframes[frame_n+1] / fps` |
| `cue_excerpt` | **YES** — directly from `CriticResponse.critic_analysis` (2-4 sentence geometric description) | The prose analysis describes the geometric state: e.g. `"The paper shows a symmetric bird base with two triangular flaps pointing upward; both lateral creases are concave valley folds."` |
| `verification_state` | **YES** — `OBSERVED` for `critic_verdict == "MATCH"` states; `INFERRED` for comparator-selected states | `OBSERVED` if verified by critic MATCH; `INFERRED` if selected by comparator |
| `confidence` | **YES** — from critic verdict: MATCH → 1.0; MISMATCH (comparator-selected) → 0.5–0.7 | Can be set from `transition_attempt` count |

**Fields that cannot be populated from FoldingAgent** (require human/model text extraction):
- The `cue_excerpt` describing folding technique in procedural terms (FoldingAgent gives geometric descriptions, not instructional cues)

---

### Q5: Is there anything in the Track A contracts that explicitly references fold geometry, crease patterns, or 3D state?

**No** — at the schema level, the current `tracks/common/schemas/` contracts have **zero explicit references** to fold geometry, crease patterns, or 3D state.

**Evidence:**

1. `EvidenceRef` — no geometry fields. Contains only temporal locators (`start_sec`, `end_sec`), `modality`, `cue_excerpt` (free-text), and `verification_state`.

2. `KnowledgeClaim` — `statement` is a free-text field. No geometry-typed fields.

3. `KnowledgePackage` — no geometry fields of any kind.

4. `RubricCriterion.observable_indicator` — free-text `str`. No structured geometry type.

5. `EvidenceRef.modality` enum — includes `sensor` which COULD carry geometric sensor data, but the enum value has no geometry schema attached.

6. `GeminiExtractionResponse` / extraction DTOs — no geometry fields. The closest is `GeminiTargetPropertySchema.measurement: Optional[str]` which can hold a quantitative string like `"8-fold rotational symmetry"` but this is text, not a geometry object.

**However**, geometry data CAN be carried in the existing contracts via free-text fields:

- `EvidenceRef.cue_excerpt` can hold a geometry-prose description: `"Edge [1,3] is a valley fold; vertices [2,4] are aligned on the symmetry axis."`
- `KnowledgeClaim.statement` can embed geometry notation
- `RubricCriterion.observable_indicator` can reference geometric predicates (as shown in the Q3 examples above)
- `TransmissionRecord.lineage.adaptation_notes` carries `"3D origami vector state sequence"` in the origami bundle — an informal geometry reference

**Conclusion:** The contracts are **geometry-agnostic by design** — they use free-text fields to remain domain-universal. Fold geometry from FoldingAgent must be serialized to JSON and stored as a separate artifact (e.g. `hybrid_keyframes.json`), with summaries or references embedded in `cue_excerpt` fields for grounding.

---

## Appendix A — Source File Index

| File | Role |
|---|---|
| `tracks/track-a/src/pipeline.py` | `TrackAPipeline` orchestrator |
| `tracks/track-a/src/gateway.py` | `ModelGateway` router |
| `tracks/track-a/src/providers.py` | `ReplayProviderAdapter`, `GeminiProviderAdapter` |
| `tracks/track-a/src/models.py` | All extraction DTOs, `normalize_dto_to_knowledge_package()` |
| `tracks/track-a/src/grounding.py` | `GroundingService` — epistemic validation |
| `tracks/track-a/src/task_generator.py` | `TaskGenerator` — rubric + task synthesis |
| `tracks/track-a/src/prompt_engine.py` | `PromptEngine` — template loading and rendering |
| `tracks/track-a/src/gemini_schemas.py` | `GeminiExtractionResponse`, `GeminiQueryResponse` |
| `tracks/track-a/src/media_service.py` | `MediaService` — URL download + Gemini Files API |
| `tracks/track-a/src/gemini_retry.py` | Exponential backoff wrapper |
| `tracks/track-a/src/expert_review.py` | `ExpertReviewService` — review lifecycle + markdown export |
| `tracks/track-a/src/case_registry.py` | `CaseManifest`, `load_manifest()`, `load_replay_bundle()` |
| `tracks/track-a/src/query_service.py` | `EvidenceQueryService` — adversarial query |
| `tracks/track-a/src/run_pipeline.py` | CLI runner |
| `tracks/track-a/src/__init__.py` | Package init |
| `tracks/common/schemas/evidence.py` | `EvidenceRef`, `Modality`, `VerificationState` |
| `tracks/common/schemas/knowledge.py` | `KnowledgePackage`, `KnowledgeClaim`, `ConsentMetadata`, `ExpertReview` |
| `tracks/common/schemas/rubric.py` | `RubricDefinition`, `RubricCriterion` |
| `tracks/common/schemas/practice.py` | `PracticeTask`, `TaskConstraint` |
| `tracks/common/schemas/attempt.py` | `LearnerAttempt`, `AttemptType` |
| `tracks/common/schemas/evaluation.py` | `Evaluation`, `CriterionResult`, `CriterionStatus` |
| `tracks/common/schemas/feedback.py` | `Feedback`, `FeedbackItem` |
| `tracks/common/schemas/transmission.py` | `TransmissionRecord`, `LineageMetadata` |
| `tracks/common/validator.py` | Cross-contract validators + bundle validator |
| `tracks/cases/origami/manifest.json` | Origami case entry point |
| `tracks/cases/origami/replay/bundle.json` | All 8 contracts for origami engineering fixture |
| `tracks/track-a/prompts/expert_extraction_v1.txt` | Forward extraction prompt |
| `tracks/track-a/prompts/goal_conditioned_extraction_v1.txt` | Goal-conditioned extraction prompt |
| `tracks/track-a/prompts/corrective_extraction_v1.txt` | Corrective extraction prompt |
| `tracks/track-a/prompts/adversarial_query_v1.txt` | Evidence query prompt |

---

## Appendix B — Origami-Specific Evidence Boundary Rules

From `tracks/cases/origami/source/README.md` (summarized from prior research):

1. **Stable source ID**: Use `src-origami-tavin-2010` for the Wikimedia video — NOT `src-origami-01` (that is the synthetic replay ID only)
2. **Attribution required**: "Tavin, CC BY 3.0, https://commons.wikimedia.org/wiki/File:OrigamiCrane.ogv"
3. **No timestamp fabrication**: `ev-origami-step-XX` IDs require actual inspection of the 335-second video before use
4. **Synthetic bundle timestamps**: t=10–22s and t=25–38s in `replay/bundle.json` are SYNTHETIC — they have NOT been verified against the actual video
5. **ENGINEERING_FIXTURE scope**: The replay bundle is scoped to `engineering_replay_only` consent — must not be presented as authentic expert validation

---

*End of ANVESHAN_DEEP_DIVE.md — all content sourced directly from source files, no modifications made.*
