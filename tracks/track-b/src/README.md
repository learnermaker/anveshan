# Track B source: `track_b` package

Public API: `track_b.api` (docs/plans/service-api.md §3). Pipeline per attempt:

`intake` -> modality evaluator (`track_b.evaluators.<m>`, trajectory) -> `scoring` (bands -> status -> score_policy_v1)
-> `evaluate` (Evaluation, validator pass semantics) -> `divergence` (first divergence) -> `feedback` + `drill`
-> `session` state machine -> `compare` + `transmission` (TransmissionRecord + validated 9-key bundle).

| Module | Role |
|---|---|
| `api.py` | start / submit / complete / save / load session |
| `handoff.py` | loads approved-else-latest case artifacts; cross-file validation |
| `intake.py` | uploaded file -> `AttemptMedia` (sniffed MIME, limits, sha256) |
| `scoring.py` | the only place scores are produced |
| `evaluate.py` | Evaluation assembly; every required criterion must be SATISFIED to pass |
| `divergence.py` | first divergence (evaluation-core §2) |
| `feedback.py`, `drill.py` | grounded feedback (expert evidence from the criterion map), unscored drill |
| `compare.py`, `transmission.py` | transitions, targeted change, provenance hash, bundle validation |
| `session.py`, `clock.py` | serialisable session; injectable clock and ids |
| `trajectory.py`, `evaluators/` | modality evaluator interface and registry |

Track B never imports the Track A package. No `uuid4()` / `now()` outside `clock.py`.
