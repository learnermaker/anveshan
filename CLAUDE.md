@AGENTS.md

# Claude Code notes for this repository

## Current execution plan
- Plan and decisions: `docs/plans/track-plan-review-2026-10-06.md` (read §9 "Decisions 2026-10-06" first).
- Track specs: `docs/plans/track-a-spec.md`, `docs/plans/track-b-spec.md`.
- Evaluation core design: `docs/plans/evaluation-core.md`.
- **Universal pipeline (Perception → SkillModel → Evaluation) for any upload:** `docs/plans/universal-pipeline.md`; shared schemas `tracks/common/{perception,skill_model,profile,policy}.py`.
- Kiro parallel specs: `docs/kiro/specs/` (00-COMMON first; Kiro runs a weaker model — write exhaustive specs).
- Hero cases: `kolam` (final image only), `origami` (video), `tabla` (audio, optional video). Other four cases are SYNTHETIC replay showcase.

## Environment
- Python: use the project venv `.venv` (`.venv/Scripts/python` on Windows). Install from `requirements-dev.txt`.
- Secrets: copy `.env.example` → `.env` (never commit `.env`). Model calls are server-side only.
- Models: `vision_fast`/`audio` = gemini-3.5-flash-lite (fast, ~$0.0003/call), `embedding` = gemini-embedding-2, `text_image` = Gemma 4 26B (free but ~43 s/image; offline only). See the model-gateway skill.

## Common commands
- All checks: use the `anveshan-verify` skill (mirrors CI).
- Python tests: `.venv/Scripts/python -m pytest tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"`
- App: `cd app && npm run dev` (Vite) / `npm run build`
- Service: `.venv/Scripts/python -m uvicorn anveshan_service.main:app --app-dir service --reload --port 8080`

## Codebase map
- A graphify code graph can be built locally: `graphify extract . --code-only` → `graphify-out/graph.json` (gitignored). Query with `graphify query "<question>"`, `graphify explain "<symbol>"`, `graphify god-nodes`. Rebuild after large changes (`graphify update .`).

## Project skills
- `anveshan-verify` — run the full local verification suite before any commit/PR.
- `model-gateway` — rules and patterns for every Gemma/Gemini call (registry, recording, replay, no silent fallback).
- `case-media` — adding internet/uploaded media to a case pack with license, sha256 and size rules.
