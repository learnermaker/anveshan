# Track Common — The 8 Shared Contracts

**Status:** DECIDED & IMPLEMENTED frozen contract seam  
**Scope:** Universal domain-agnostic transmission entities for parallel development.

---

## 1. Purpose

`tracks/common/` is the authoritative single source of truth for the data contracts shared between:
- **Track A (Track 1):** Expert Intelligence & Grounding (`tracks/track-a/`)
- **Track B (Track 2):** Practice, Evaluation & Transmission (`tracks/track-b/`)

It provides type-safe Pydantic v2 models directly compatible with the Google Gemini API (`google-genai`), deterministic validation logic, and automated tests.

---

## 2. The 8 Shared Contracts

```text
Track A (Expert Grounding)
-------------------------
Expert Demonstration
        ↓
1. EvidenceRef
        ↓
2. KnowledgePackage (with embedded consent & expert review)
        ↓
3. RubricDefinition (explicit observable criteria & scoring weights)
        ↓
4. PracticeTask (bounded learner exercise referencing package & rubric)
        │
        └──────────────────── shared seam ────────────────────┐
                                                              ↓
Track B (Practice & Evaluation)                         5. LearnerAttempt (baseline & retry)
------------------------------                                ↓
                                                        6. Evaluation (criterion-level scoring)
                                                              ↓
                                                        7. Feedback (evidence-grounded coaching)
                                                              ↓
                                                        Retry Attempt
                                                              ↓
                                                        8. TransmissionRecord (deterministic gain & lineage)
```

### Contract Summary

| # | Contract | Primary Producer | Key Role & Invariants |
|---|---|---|---|
| **1** | **`EvidenceRef`** | Track A / B | Multimodal locator (`video/audio/image/text/sensor`). Enforces `end_sec >= start_sec >= 0.0`. |
| **2** | **`KnowledgePackage`** | Track A | Structured claims, cues, conditions, and failure modes. Embeds `ConsentMetadata` and `ExpertReview`. |
| **3** | **`RubricDefinition`** | Track A / Expert | **The source of truth for scoring.** List of `RubricCriterion` with observable indicators and weights. |
| **4** | **`PracticeTask`** | Track A | Bounded learner assignment linking `package_id` and `rubric_id`. |
| **5** | **`LearnerAttempt`** | Track B Intake | Observable submission recording. Explicitly distinguishes `BASELINE` from `RETRY`. |
| **6** | **`Evaluation`** | Track B Engine | Criterion-level observations. Enforces `total_score == sum(criterion scores)`. Explicit `UNCERTAIN` status. |
| **7** | **`Feedback`** | Track B Coach | Actionable coaching contrasting learner attempt with expert evidence. |
| **8** | **`TransmissionRecord`** | Track B / Integration | Immutable proof event. Enforces deterministic math: `transmission_gain == retry_score - baseline_score`. |

---

## 3. How to Use in Track A

Track A generates structured knowledge, the target rubric, and the practice task:

```python
from tracks.common.schemas import (
    KnowledgePackage,
    KnowledgeClaim,
    ClaimType,
    EvidenceRef,
    Modality,
    ConsentMetadata,
    RubricDefinition,
    RubricCriterion,
    PracticeTask,
)

# Example: Validating a generated knowledge package
pkg = KnowledgePackage(
    package_id="PKG-001",
    skill_id="SKILL-SOLDER",
    title="SMD Soldering Prep",
    summary="Clean surface with isopropyl alcohol.",
    claims=[...],
    consent=ConsentMetadata(contributor_name="Jane Doe", consent_scope="demo"),
)
```

---

## 4. How to Use in Track B

Track B consumes the frozen `PracticeTask` and `RubricDefinition`, and emits learner evaluations and transmission records:

```python
from tracks.common.schemas import (
    PracticeTask,
    RubricDefinition,
    LearnerAttempt,
    AttemptType,
    Evaluation,
    CriterionResult,
    CriterionStatus,
    Feedback,
    TransmissionRecord,
)

# Deterministic transmission gain calculation
gain = round(retry_eval.total_score - baseline_eval.total_score, 4)

record = TransmissionRecord(
    transmission_id="TX-001",
    skill_id="SKILL-SOLDER",
    package_id=task.package_id,
    rubric_id=rubric.rubric_id,
    expert_id="Jane Doe",
    learner_id="Alice",
    baseline_attempt_id=baseline_attempt.attempt_id,
    retry_attempt_id=retry_attempt.attempt_id,
    baseline_score=baseline_eval.total_score,
    retry_score=retry_eval.total_score,
    transmission_gain=gain,
    criteria_improved=["CRIT-02"],
    lineage={"recorded_at": "2026-10-04T12:00:00Z"},
)
```

---

## 5. Offline Contract Validator CLI

Validate any mock JSON fixture or model response against the contracts:

```bash
# Validate against auto-detected contract type
python -m tracks.common.validator path/to/fixture.json

# Validate against a specific contract
python -m tracks.common.validator path/to/fixture.json --type KnowledgePackage
```

---

## 6. Running Tests

Run the deterministic test suite:

```bash
python -m pytest tracks/common/tests
```
