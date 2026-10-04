# Track B — Track-Local Data

Canonical capability case content lives in:

    tracks/cases/<case_id>/

Use the shared rules in `tracks/common/CASE-DATA-CONVENTIONS.md` and `tracks/common/MODEL-GATEWAY-CONVENTIONS.md`.

Track B `data/` is reserved for implementation-specific learner/evaluation fixtures, adapter outputs, and metadata that should not become part of the shared case pack.

Do not create a duplicate case manifest, rubric, practice task, or replay bundle here. Reference the canonical `case_id` under `tracks/cases/`.

Track B may work from frozen Track-A-compatible inputs before Track A implementation exists. Synthetic/replay evidence must remain explicitly labeled and must never be presented as real-world transmission validation.
