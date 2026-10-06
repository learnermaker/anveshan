# Track A source

The only code here is the importable `track_a` package (`tracks/track-a/src` on `PYTHONPATH`).

- `track_a/api.py` — public API (docs/plans/service-api.md §2). Integration imports only this.
- `track_a/authoring.py` — GoalBuildResult → versioned GoalModel, KnowledgePackage, rubric, task, criterion map, observers.
- `track_a/grounding.py` — deterministic locator / observation / confidence / creator-intent audit.
- `track_a/query.py` — evidence query (Gemma via `tracks.common.models.ModelGateway`; no fallback).
- `track_a/review.py` — expert review → new package version.
- `track_a/config.py` — case→modality map, confidence policy, phrase lists.
- `track_a/goals/` — modality goal builders (kolam / origami / tabla).
