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

from .evidence import EvidenceRef, Modality, VerificationState
from .rubric import RubricDefinition, RubricCriterion
from .knowledge import (
    KnowledgePackage,
    KnowledgeClaim,
    ClaimType,
    ConsentMetadata,
    ExpertReview,
    ReviewStatus,
)
from .practice import PracticeTask, TaskConstraint
from .attempt import LearnerAttempt, AttemptType, ParticipantRef
from .evaluation import (
    Evaluation,
    CriterionResult,
    CriterionStatus,
    EvaluatorType,
)
from .feedback import Feedback, FeedbackItem
from .transmission import TransmissionRecord, LineageMetadata

__all__ = [
    # The 8 Root Contracts
    "EvidenceRef",
    "KnowledgePackage",
    "RubricDefinition",
    "PracticeTask",
    "LearnerAttempt",
    "Evaluation",
    "Feedback",
    "TransmissionRecord",
    # Supporting Types & Enums
    "Modality",
    "VerificationState",
    "RubricCriterion",
    "KnowledgeClaim",
    "ClaimType",
    "ConsentMetadata",
    "ExpertReview",
    "ReviewStatus",
    "TaskConstraint",
    "AttemptType",
    "ParticipantRef",
    "CriterionResult",
    "CriterionStatus",
    "EvaluatorType",
    "FeedbackItem",
    "LineageMetadata",
]
