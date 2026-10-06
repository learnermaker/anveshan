# Track B Source Boundary: Evaluation & Transmission Engine

This directory contains the production evaluation and transmission measurement engine for Track B.

## Modules

- `evaluator.py`: Deterministic criterion evaluation, score boundary enforcement ($0 \le \text{score} \le \text{weight}$), required criteria gating, and pass/fail state transitions.
- `feedback.py`: Evidence-grounded coaching generator linking learner observations to expert demonstration references and prioritizing retry focus areas.
- `transmission.py`: Deterministic gain calculation ($\Delta = \text{retry\_score} - \text{baseline\_score}$), criteria improvement detection, and cryptographic SHA-256 provenance hashing.
- `pipeline.py`: Unified `TransmissionPipeline` executing the complete end-to-end replay lifecycle.

## Replay Invariants Enforced

1. Rubric adherence: No unconstrained single-number scores; all judgments are mapped criterion-by-criterion.
2. Required criteria gate: If any mandatory criterion is `NOT_SATISFIED`, the overall evaluation `passed` flag is strictly `False`.
3. Deterministic gain: Gain arithmetic is strictly computed in Python, never hallucinated by model prose.
