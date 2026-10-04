"""Track B: Practice, Evaluation & Transmission Engine.

Owns learner practice attempt intake, criterion-level rubric evaluation,
evidence-linked feedback generation, retry comparison, and deterministic transmission measurement.
"""

from .evaluator import evaluate_attempt
from .feedback import generate_coaching_feedback
from .transmission import compute_transmission_record
from .pipeline import TransmissionPipeline
from .observer import GeminiObserver

__all__ = [
    "evaluate_attempt",
    "generate_coaching_feedback",
    "compute_transmission_record",
    "TransmissionPipeline",
    "GeminiObserver",
]
