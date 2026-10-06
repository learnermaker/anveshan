# Kiro Specs: Common Rules (read first, every session)

Project: **Anveshan**, Google Cloud AI Builder Cup 2026 (deadline **2026-10-18**). Three live "hero" cases: **Kolam** (final image only), **Origami** (video), **Tabla** (audio). The core capability is **Goal-Trajectory Verification**: build a goal model from the source, then judge a learner's attempt by progress toward the goal, first divergence, why it matters (grounded in source claims), and targeted improvement after retry.

## Your working folder (IMPORTANT)
Each spec runs in its **own git worktree folder on its own branch**, so parallel Kiro sessions never collide:

| Spec | Folder | Branch |
|---|---|---|
| K1 Kolam | `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan-wt\k1-kolam` | `kiro/k1-kolam` |
| K2 Tabla | `...\anveshan-wt\k2-tabla` | `kiro/k2-tabla` |
| K3 App UI | `...\anveshan-wt\k3-app` | `kiro/k3-app` |
| K4 Origami live | `...\anveshan-wt\k4-origami` | `kiro/k4-origami` |
| K5 Integration | `...\anveshan-wt\k5-integration` | `kiro/k5-integration` (start only after K1+K2 are merged) |

- Open **only your folder** in Kiro. Never edit the main folder `...\hackathons\anveshan` (Claude Code and Jim merge there).
- Commit often on your branch. **Never** merge, rebase, push, or switch branches. Jim/Claude Code merge finished branches into `m1/hero-cases`.
- Commit message format: `type(scope): summary` (e.g. `feat(kolam): …`, `fix(origami): …`, `test(tabla): …`).

## Environment
- Python venv (shared, already installed): `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe` — call it by this absolute path from your worktree root. Packages: numpy, pillow, av (PyAV, bundles ffmpeg), pydantic, google-genai, fastapi, uvicorn, httpx, pytest. **Do not install heavy deps** (no scipy, opencv, librosa, scikit-image). Ask Jim before adding any dependency.
- The root `conftest.py` puts `tracks/track-a/src`, `tracks/track-b/src`, `service/` on `sys.path`; run pytest from the worktree root.
- Media: run `<py> tools\fetch_media.py --from-dir C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\var\scratch\media` once in your worktree (copies licensed case media into the gitignored `tracks/cases/<case>/media/cache/`).
- API key: copy `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.env` to your worktree root as `.env` **only if your spec says you need live model calls**. Never print, log, or commit the key. `.env` is gitignored.
- Windows shell. `curl` needs `--ssl-no-revoke` on this network.

## Must-read docs (in every worktree)
- `CLAUDE.md`, `AGENTS.md` (governance: evidence discipline, observed vs inferred, no fabrication, explicit failures).
- `docs/plans/evaluation-core.md` (the design), `docs/plans/service-api.md` (interfaces — do not change without updating this file in the same commit).
- `.claude/skills/model-gateway/SKILL.md` (all model calls), `.claude/skills/case-media/SKILL.md` (media/licence rules), `.claude/skills/anveshan-verify/SKILL.md` (verification commands).

## Non-negotiables
1. The **8 contracts** in `tracks/common/schemas/` are frozen. Never change them; `app/src/types/contracts.ts` mirrors them (CI parity check).
2. **Model output never sets scores, observed/inferred state, rubric weights, pass/fail or gain.** Scores come from deterministic bands in `practice/observers.vN.json`.
3. **No silent fallbacks.** Model failure → explicit `ModelError`/`AnveshanFailure`. Never substitute mock data in a real path.
4. **Observed claims need locators** (image `#xywh=percent:` region with no times; audio/video `start_sec/end_sec`). Inferred claims ≤ 0.5 confidence. Never assert artist intent, history, meaning or original order from a final image.
5. All model calls go through `tracks.common.models.ModelGateway` (records runs; `recorded` mode replays). **Gemma facts (measured 2026-10-06):** `gemma-4-26b-a4b-it` — JSON + system instructions OK; text ≈4–7 s; one image ≈43 s; a 4-image call **timed out at 120 s (504)**. Keep image calls small (few images, ≤384 px, JPEG q≈75), raise timeouts deliberately, and retry 504s at most once. Gemma has **no audio**.
6. Licensed media only (PD/CC0/CC BY/CC BY-SA). Large media is never committed (fetched by sha256). Synthetic attempts are labelled SYNTHETIC.
7. Tests must not call live APIs (fake gateway/client; see `tracks/common/tests/test_foundation.py`). Real-API tests are `@pytest.mark.live`.

## Definition of done (every spec)
- Your spec's acceptance checks pass, plus: `<py> -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"` is green in your worktree, and `<py> .github/scripts/check_case_packs.py`, `check_governance.py`, `check_contract_parity.py` pass.
- Write `docs/kiro/reports/<spec-id>-REPORT.md` in your worktree (what you did, test output summary, numbers, open issues, anything Claude Code must decide), commit it, then tell Jim: **"<spec-id> complete — branch kiro/<…> ready to merge"**.
