# Track A — Track-Local Data

Canonical capability case content lives in:

    tracks/cases/<case_id>/

Use the shared rules in `tracks/common/CASE-DATA-CONVENTIONS.md` and `tracks/common/MODEL-GATEWAY-CONVENTIONS.md`.

Track A `data/` is reserved for implementation-specific intermediate fixtures, adapter outputs, and metadata that should not become part of the shared case pack.

Do not create a duplicate case manifest, rubric, practice task, or replay bundle here. Reference the canonical `case_id` under `tracks/cases/`.

No bounded domain is authorized merely by creating local fixture files. Synthetic/replay fixtures are engineering scaffolding and must be labeled accordingly.
