# Track A — Expert Intelligence & Grounding

## Current build (2026-10-06)

Specs: `docs/plans/service-api.md` §2 (public API), `docs/plans/track-a-spec.md`, `docs/plans/evaluation-core.md`.

- Code: `src/track_a/` (`api.py` is the public entry point). Modality goal builders live in `src/track_a/goals/`.
- Hero cases `kolam` (image), `origami` (video), `tabla` (audio) and derived upload cases `<base>~<sha12>` are built
  by `build_case` into versioned `knowledge/*.vN.json` / `practice/*.vN.json` files. The four other cases are
  SYNTHETIC replay showcase (loaded from `replay/bundle.json`).
- Install: `pip install -r tracks/track-a/requirements.txt` (dev/CI: root `requirements-dev.txt`).
- Tests (no network): `.venv/Scripts/python -m pytest -q tracks/track-a/tests`
- CLI: `python tracks/track-a/tools/run_pipeline.py build|show|query|review tracks/cases/<id> ...`
  (`--mode live` needs `GEMINI_API_KEY` in `.env`; `recorded` replays committed golden runs).

**Owner boundary:** source understanding, structured knowledge, evidence grounding, and generation of bounded teaching/practice inputs.

## Start here
Read CODING-AGENT-GUIDE.md, SUCCESS-CRITERIA.md, tracks/common/README.md, tracks/common/CONTRACT-USAGE.md, tracks/common/schemas/, tracks/common/validator.py, docs/architecture/parallel-work-contract.md, and docs/architecture/google-stack-integration.md before coding.

The domain/skill is intentionally **not fixed yet**. Keep implementation domain-agnostic until M0 selects the bounded authentic case.

## Objective
Prove that an appropriate source can become a source-grounded knowledge representation and bounded teaching/practice input without material invention.

Source modes include demonstration-first, goal-conditioned target-first, and corrective attempt-first. The selected case determines which mode is valid.

## Boundary
Own source/media representation, multimodal understanding, structured steps/cues/conditions/exceptions/failure modes, claim→evidence links, grounded teaching, rubric/practice-task generation, expert review, replay, and deterministic validation.

Do not own learner scoring, feedback/retry, transmission-gain calculation, production learner runtime, or generalized platform infrastructure.

## Authoritative outputs
Track A produces EvidenceRef, KnowledgePackage, RubricDefinition, and PracticeTask. The authoritative models are in tracks/common/schemas/. Internal DTOs and Gemini response shapes are adapters only; normalize them into the common contracts.

## Domain-agnostic rule
Do not hard-code a profession, skill, tool, vocabulary, camera setup, or evaluation method into reusable Track A infrastructure. Domain-specific behavior belongs in the selected case, fixture, prompt, or adapter.

## Starter validation
Use synthetic-but-structurally-realistic replay fixtures that distinguish observed/source-backed content, derived interpretation, uncertainty, and missing evidence. Fixtures are engineering scaffolding, not product validation.

## Worktree
tracks/track-a/ contains README.md, CODING-AGENT-GUIDE.md, SUCCESS-CRITERIA.md, fixtures/, prompts/, src/, tests/, and notes/. Create implementation files only through bounded issues.

## Operational conventions

Before creating case-local artifacts, read:
- `tracks/common/CASE-DATA-CONVENTIONS.md`
- `tracks/common/MODEL-GATEWAY-CONVENTIONS.md`
- `tracks/cases/README.md`

Use `tracks/cases/<case_id>/manifest.json` as the entry point for implementation-ready cases. Do not infer validation status from folder presence.

## Worktree

`tracks/track-a/` contains README.md, CODING-AGENT-GUIDE.md, SUCCESS-CRITERIA.md, IMPLEMENTATION-READINESS.md, fixtures/, data/, prompts/, src/, tests/, and notes/. Create implementation files only through bounded issues.
