# Wave 2 Master Spec — Universal Pipeline, Composer, Tabla Timbre, Integration (subagent execution)

**Date:** 2026-10-06 · **Status:** READY (reviewed; see §9) · **Owner:** Claude Code, orchestrating parallel subagents · **Deadline:** 2026-10-18

This single spec replaces running K2b, K5, K6, K7 and K8 as separate Kiro sessions. It defines **five work packages (WPs)** that Claude Code subagents execute: four in parallel, one integration pass after them. Every detail that already exists in a K-spec is **referenced, not repeated**; the K-specs are normative appendices. Where this spec and a K-spec disagree, **this spec wins** (§7 lists the overrides).

---

## 1. Baseline and preconditions

- **Base:** branch `m1/hero-cases` at the commit where this spec was created (K2, K3 merged; 291 tests green; the universal-pipeline shared schemas in place).
- **Running in Kiro, not part of this spec:** K1 (Kolam finish) and K4 (Origami live). Phase A does **not** depend on them. Phase B (WP5) starts only after both are merged.
- **Shared foundation (do not change field names; additive optional fields only, each reported):**
  - `tracks/common/perception.py`, `skill_model.py`, `profile.py` (v2), `policy.py`
  - `tracks/common/models.py` (`generate_json`, `embed`, registry keys `vision_fast`, `audio`, `embedding`, `text_image`)
  - `tracks/common/casedata.py` (GoalModality includes `universal`)
  - registries `track_a/goals/__init__.py` (`universal`) and `track_b/evaluators/__init__.py` (`universal`)
- **Architecture:** `docs/plans/universal-pipeline.md` (authoritative). The evaluation core is `docs/plans/evaluation-core.md`; the interfaces are `docs/plans/service-api.md`.
- **Models (measured 2026-10-06):**
  - `vision_fast` = gemini-3.5-flash-lite: 2.5 s per image, 4 images 8.9 s, ≈ $0.0003 per image;
  - `embedding` = gemini-embedding-2: 5 images 1.3 s;
  - `audio` = gemini-3.5-flash-lite: 12 s of audio in 2.7 s;
  - Gemma: 43 s per image (offline only).

## 2. Work packages

| WP | Scope | Normative detail | Phase | Depends on |
|---|---|---|---|---|
| **WP1** Perception + gates + composer API | Layer 1 perceivers (image / video / audio), intake screen (safety, teachability), specialist/structure availability, composer drafts (create / refine / create-case), `/api/compose/*` routes, `modality_for` + `list_cases` + `to_view` wiring | `docs/kiro/specs/K6-composer-backend.md` (all sections) | A | foundation only |
| **WP2** SkillModel builder + universal evaluator | Layer 2 `propose_skill_model` + `track_a/goals/universal.py` builder; Layer 3 `track_b/evaluators/universal.py` (+ `universal_align.py`); `api.build_case` passes the profile for `universal` | `docs/kiro/specs/K7-engines-generalise.md` §0–§5, §7 | A | foundation only (tests use fixture PerceptionRecords and a monkeypatched `perceive`) |
| **WP3** Composer UI | Wizard (upload → perceiving → refused / needs input / proposal → building → done), "Your skills", universal case views, relevance-refusal UX, mock scenarios | `docs/kiro/specs/K8-composer-ui.md` (all) | A | K3 (merged) |
| **WP4** Tabla timbre + rhythm specialist | MFCC/timbre classes, `CRIT-TABLA-STROKES`, Flash-Lite bol labels (INFERRED), v2 tabla artifacts + golden run, `payload_from_audio` refactor, neutral wording for generic percussion | `docs/kiro/specs/K2b-tabla-timbre.md` (all) | A | K2 (merged) |
| **WP5** Integration, live checks, validation, deploy prep | Merge WP1–WP4 + K1 + K4; wire WP2 to the real WP1 `perceive`; live checks for WP1 (K6 §7) and WP2 (K7 §6); end-to-end smoke suite; validation write-up; README; deploy readiness | §5 of this spec + `docs/kiro/specs/K5-integration-deploy.md` §1–§4, §6 | B | WP1–WP4, K1, K4 merged |

## 3. File ownership (Phase A is conflict-free by construction)

| Path | Owner |
|---|---|
| `tracks/common/perceivers/**`, `tracks/common/prompts/perceive_*` | WP1 |
| `tracks/track-a/src/track_a/composer.py` | WP1 |
| `tracks/track-a/src/track_a/config.py` (`modality_for` only) | WP1 |
| `tracks/track-a/src/track_a/api.py`: `list_cases`, `CaseHandoff.to_view` | WP1 |
| `tracks/track-a/src/track_a/api.py`: `build_case` | **WP2** (a different function in the same file; keep diffs small and contained; WP5 resolves any textual conflict) |
| `service/anveshan_service/routes/compose.py`, `main.py` (router registration), `service/tests/test_service_compose.py`, `docs/plans/service-api.md` (compose section) | WP1 |
| `.env.example` | WP1 |
| `tracks/track-a/src/track_a/universal.py`, `track_a/goals/universal.py`, `tracks/common/goals/universal.py` | WP2 |
| `tracks/track-b/src/track_b/evaluators/universal*.py` | WP2 |
| `tracks/common/prompts/structure_skill_v1.txt`, `judge_final_v1.txt`, `judge_step_v1.txt`, `relevance_v1.txt` | WP2 |
| WP2 tests (`test_universal_*`) | WP2 |
| `app/**` | WP3 |
| `tracks/common/tabla_dsp.py`, `tracks/common/goals/tabla.py` | WP4 |
| `track_a/goals/tabla.py`, `track_b/evaluators/tabla.py` | WP4 |
| `tracks/common/prompts/tabla_bols_v*.txt`, `tracks/cases/tabla/**`, `tracks/track-b/eval/tabla/**`, tabla tests | WP4 |
| `docs/plans/evaluation-core.md` §5 | WP4 |
| Everything else, and every merge | WP5 / Claude Code |

**Read-only for all of Phase A:** the Kolam and Origami engines (K1 and K4 are still changing them in Kiro), `tracks/common/schemas/*` (frozen), and the shared foundation files listed in §1.

**Cross-WP calls in Phase A** (stable signatures; never edit the callee):
- WP2 calls `track_a.goals.kolam.build`, `track_a.goals.tabla.build`, `tracks.common.goals.kolam.payload_from_image`, `track_b.evaluators.kolam.evaluate`, `track_b.evaluators.tabla.evaluate`. If WP4's `payload_from_audio` is absent, use the `tabla.build` fallback (K7 §2.2).
- WP1 calls `track_a.universal.propose_skill_model` **if importable**, otherwise its own `_fallback_skill_model` (K6 §3.2 step 5).
- WP3 uses only HTTP shapes from K6 §4 / K8 §3 and the mock.

## 4. Subagent execution protocol (applies to WP1–WP4)

1. **Isolation:** each WP runs as one subagent with `isolation: "worktree"`. The worktree may start on an older commit; if `git log -1` doesn't show the spec's base commit, run `git merge --ff-only m1/hero-cases` or `git reset --hard m1/hero-cases` (only on a clean tree) before starting.
2. **Environment:**
   - Python: `C:/Users/JIMSEELAN/Desktop/Projects/hackathons/anveshan/.venv/Scripts/python`.
   - Media: `<py> tools/fetch_media.py --from-dir C:/Users/JIMSEELAN/Desktop/Projects/hackathons/anveshan/var/scratch/media`.
   - Node is available for WP3 (`npm --prefix app install`).
   - **API key:** WP1, WP2 and WP4 copy `C:/Users/JIMSEELAN/Desktop/Projects/hackathons/anveshan/.env` into their worktree root (gitignored; never print it).
3. **Live model calls only where a spec says so, within these budgets:**

| WP | Allowance |
|---|---|
| WP1 | its live check (K6 §7): ≤ 40 calls, ≤ $0.10 |
| WP2 | none in Phase A (its live check moves to WP5) |
| WP3 | none |
| WP4 | ≤ 5 audio calls |

   Tests never call the network.
4. **Rate-limit resilience:** commit after **every** completed numbered step (`type(scope): …` plus the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`). If the session is interrupted, the resumed agent continues from `git log`.
5. **No scope creep:** no edits outside §3 ownership. If a shared change is needed, describe it in the final report under "Requests for WP5"; do not make it.
6. **Definition of done per WP:**
   - (a) the WP's K-spec acceptance criteria are met, with the §7 overrides applied;
   - (b) `<py> -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"` is green in the worktree;
   - (c) `check_governance.py`, `check_case_packs.py` and `check_contract_parity.py` pass;
   - (d) WP3 also: `npm --prefix app run build` passes;
   - (e) a final report (≤ 60 lines) with sections: Done, Tests, Live results (if any), Deviations, Requests for WP5, Open issues.

   No report file in the repo is required; the subagent's final message is the report. WP4 still writes `RESULTS.md` updates as its spec requires.

## 5. WP5: Integration (Phase B), done by Claude Code with ≤ 2 helper subagents

Order of operations:
1. **Merge** into `m1/hero-cases`, in this order, resolving conflicts by ownership (§3):
   1. K1 (Kiro)
   2. K4 (Kiro)
   3. WP4
   4. WP1
   5. WP2
   6. WP3

   After each merge: full pytest, the three checks and the app build.
2. **Wire WP2 to the real perceivers:** remove the monkeypatch-only assumptions and run WP2's tests against the real `perceive` with recorded runs.
3. **Live checks, recording golden runs where useful:**
   - WP1 / K6 §7: Kolam PNG, tabla clip, origami cut, landscape (refusal expected), silence (refusal expected).
   - WP2 / K7 §6: a composed Kolam (same image / half-erased / unrelated photo → relevance refusal), a composed origami cut (different cut / same cut).
   - The universal path on **two genuinely new skills** sourced from `var/kiro/media/` or synthetic: (i) a Pillow-generated simple rangoli-like line drawing with a learner raster, and (ii) a synthetic hand-clap rhythm WAV with a jittered learner copy.

   Budget: ≤ 150 calls, ≤ $0.50 in total.
4. **End-to-end smoke suite** (`tools/e2e_smoke.py` + `service/tests/test_e2e_real.py`, per K5 §1–§2), extended with the composer: analyse → create → one practice attempt → one relevance-refused attempt, for an image skill.
5. **Calibration sanity:** review the default bands of the universal checks (K7 §3 table) against the live results. Adjust only with written justification in `docs/plans/universal-pipeline.md` (new §11 "Calibration log").
6. **Validation write-up** (K5 §3): add to `docs/validation/experiments.md` the Kolam path validation, the Kolam/Tabla/Origami synthetic evals, the Tabla timbre eval, the universal-pipeline live checks, and the model latency table. Update `findings.md` honestly: engineering/capability evidence on internet and synthetic data, **not** human-learner validation.
7. **README status** (K5 §4).
8. **Deploy readiness** (deployment itself is done by Jim in the GCP console per `docs/kiro/cloud-run-console-guide.md`):
   - check that the Dockerfile builds the app and installs the Python deps used by WP1–WP4 (numpy, pillow, av, google-genai);
   - check that `fetch_media.py` runs at build time;
   - make sure `.env.example` documents every key;
   - produce `docs/deploy/DEPLOY-CHECKLIST.md`: the exact env vars and secrets, `max-instances 1`, memory 2 GiB, timeout 300 s, and the smoke commands.
9. **PR:** open a PR `m1/hero-cases → main` using the repository template; validate the body with `check_pr_contract.py`. Merging is Jim's decision (GitHub Desktop).

## 6. Acceptance for the whole wave
- Composing works end to end for at least: one line-art image, one non-line-art image (property checklist), one procedure video, one rhythm audio and one speech audio. Each yields a validated bundle after baseline + retry, **or** a correct gate refusal (unteachable, unsafe or irrelevant).
- Hero cases are unchanged (their tests are green; byte-identity tests from WP4 pass).
- The `vision_fast` / `embedding` latency budgets hold: case build < 45 s, attempt < 30 s, measured in the WP5 live checks.
- All tests, checks and the app build are green on `m1/hero-cases`; the validation docs are updated; the PR is open.

## 7. Overrides to the K-specs (subagent mode)

1. **Folders/branches:** ignore the `anveshan-wt\…` folders and `kiro/…` branch names in `00-COMMON.md`. Subagents use their automatic worktree and branch; Claude Code merges.
2. **Reports:** ignore "write `docs/kiro/reports/<id>-REPORT.md` and tell Jim". The final message is the report (§4.6).
3. **K7 §0 "Parallelism":** ignore the instruction to ask Jim for a new branch after K6 merges. Integration happens in WP5 step 2.
4. **K7 §6 live check** → moves to WP5 step 3.
5. **K6 §3.2 step 5:** keep the fallback; WP5 removes nothing. Once WP2 is merged, the real `propose_skill_model` is used automatically.
6. **K5:** only §1–§4 and §6 apply, inside WP5. Its "Wave 3" precondition is replaced by §5 step 1 above. Cloud Run deployment is done by Jim; WP5 prepares the checklist.
7. **K2b §3:** "Rebuild the tabla case to v2 artifacts" is still required. Promote the Flash-Lite run to `tracks/cases/tabla/runs/golden/`.
8. **K8 §8 step 2:** real-service testing moves to WP5 step 3 if WP1 and WP2 are not merged when WP3 finishes.
9. **WP2 lazy imports (critical):** in Phase A, `tracks/common/perceivers/` does **not** exist in WP2's worktree (WP1 creates it). WP2 must therefore never import it at module level. Import inside the functions that need it (`perceivers = importlib.import_module("tracks.common.perceivers")`). In tests, inject a fake module with `monkeypatch.setitem(sys.modules, "tracks.common.perceivers", fake)`, where the fake provides `perceive`, `load_embeddings` and `load_record` with the K6 §2 signatures. WP1 likewise imports `track_a.universal` lazily (K6 §3.2 step 5).
10. **WP4 and the bol prompt:** K2 already moved `tabla_bols_v1.txt` to `tracks/common/prompts/`. WP4 adds `tabla_bols_v2.txt` there and must not recreate the old path.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `track_a/api.py` edited by WP1 and WP2 | Different functions; small diffs; WP5 merges WP1 first, then WP2, and reruns the tests |
| WP2 coded against a stubbed `perceive` mismatches the real one | Exact signatures frozen in K6 §2; WP5 step 2 reconciles, with tests |
| Flash-Lite judgements are noisy | Deterministic checks dominate the weights (coverage/order/specialists); AI-judged criteria are labelled; calibration log in WP5 |
| Embedding relevance threshold (0.72) is wrong for some media | Ambiguous band → yes/no model check; WP5 calibrates on live checks and documents the result |
| Session/rate limits interrupt subagents | Commit per step; resume from `git log` |
| Wikimedia rate limits during the Docker build | Fall back to fetching from a GCS bucket (documented in the deploy checklist); media is never committed |
| Cost overrun | Per-WP budgets (§4.3); the gateway records every call so nothing is re-run unnecessarily |

## 9. Review log (this spec was reviewed before release)

| # | Check | Finding | Resolution |
|---|---|---|---|
| R1 | Do the Phase A WPs touch the same files? | `track_a/api.py` is shared by WP1 and WP2 | Split by function, with a WP5 merge order (§3, §8) |
| R2 | Does any Phase A WP depend on K1/K4, which are still in Kiro? | WP2 calls the Kolam builder, which K1 is editing | The signature is stable; WP2 only calls it; behaviour changes from K1 arrive at WP5 merge; the hero tests catch regressions |
| R3 | Is WP2 blocked on WP1? | It would be if it needed the real perceivers | Fixture PerceptionRecords plus monkeypatched `perceive` in Phase A; real wiring in WP5 step 2 |
| R4 | Do the K-spec instructions conflict with subagent mode? | Folders, reports and the "ask Jim" steps | Overrides §7.1–§7.8 |
| R5 | Are live calls bounded? | The K-specs had no totals | Budgets in §4.3 and §5.3 |
| R6 | Is integration owned? | The Kiro plan had integration in K5 after all waves | WP5 owns merging, wiring, live checks, smoke, docs, deploy readiness and the PR |
| R7 | Is the acceptance measurable? | The wave-level outcome was undefined | §6 lists the modality coverage, latency budgets and green gates |
| R8 | Honesty constraints carried through? | Yes: observed/inferred, AI-judged labelling, relevance refusals not recorded, validation scope | Kept in WP1–WP3 specs and WP5 step 6 |
| R9 | Does the fresh-code rule (code after 2026-09-07) hold? | First repo commit 2026-10-02 | No action; don't import pre-existing code |
| R10 | Deploy blocked by tooling (no gcloud/Docker locally)? | Yes | Console-based deployment by Jim; WP5 prepares the checklist and verifies the Dockerfile statically |
| R11 | Would WP2 even import in Phase A? | **No:** a module-level import of the not-yet-existing `tracks.common.perceivers` would make every WP2 module and test fail | Override §7.9: lazy imports + an injected fake module in tests |
| R12 | Are K-spec file paths still valid after the K2/K3 merges? | The bol prompt moved; `.env.example` already has the vision/embedding keys | Override §7.10; WP1 only verifies `.env.example` and adds what is missing |
| R13 | Do the composer `create` endpoint tests depend on WP2? | They would call the `universal` builder | K6 tests monkeypatch `build_case`; real end-to-end coverage happens in WP5 step 4 |
