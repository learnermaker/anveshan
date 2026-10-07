# K9 build report

**Date:** 2026-10-08  
**Branch:** `k9/integration`  
**Commit range:** `b9876db..bc61137` (48 commits, 10 tasks + integrator)

---

## Phases and commit ranges

| Phase | Commits | Notes |
|---|---|---|
| Phase 0 foundation | b9876db | P0 applied: types, client, mock, plain copy, debug flag, seams |
| Wave A (P1–P7) | individual branches | 7 parallel tasks; merged in order P1→P4→P6→P7→P2→P3→P5 |
| Merge A + integration fixes | 268f85b..8f1d8aa | 4 main syncs; P4 router, P5 packs, ReviewBadge, mock origami-crane |
| Wave B (B1–B2) | individual branches | 2 parallel tasks; merged B2 first, then B1 |
| Merge B | a36b57e..81e1e05 | No conflicts; B1 used B2's evidence.json as expected |
| Gate (1 iteration) | bc61137 | 5 plain-language fixes; 0 findings after |

---

## Per-task results

| Task | Verify | Review | Live calls | Notes |
|---|---|---|---|---|
| K9-P1 backend | PASS | REVISE→fixed | 0 | Steward middleware, library, insights, usage, apply_expert_review |
| K9-P2 learner | PASS | REVISE→fixed | 0 | Plain language, practice picker, sample UI, accessibility |
| K9-P3 creator+steward | PASS | REVISE→fixed | 0 | Navigation, creator panel, steward console, insights UI |
| K9-P4 samples | PASS | APPROVED | 0 | Sample routes, content, check_case_packs extension |
| K9-P5 origami-crane | FAIL→PC fixed | REVISE→fixed | 32 | Universal pipeline for origami-crane; PC fixed 2 integration issues |
| K9-P6 docs | PASS | REVISE→fixed | 0 | README, LICENSE Apache-2.0, judges review status, E8/E9 |
| K9-P7 tools | PASS | REVISE→fixed | 0 | smoke_deployed.py, check_plain_language.mjs, check_roles.mjs, errors.ts |
| K9-B1 evidence+a11y | PASS | REVISE→fixed | 0 | EvidencePage, accessibility sweep, mobile views |
| K9-B2 stability | PASS | APPROVED | 40 | stability_runs.py, evidence.json, E10 |
| PC integration | PASS | — | 0 | merge-a, merge-b, gate (1 iter), finalize |

Total live calls: **72** (P5: 32, B2: 40, PC: 0) — within 110-call budget.

---

## Test, check and build counts

- **Tests:** 560 passed (264 common+service, 130 track-a, 166 track-b); 0 failures; `not live` marker
- **Governance:** PASS
- **Case packs:** PASS (8 packs)
- **Contract parity:** PASS (8 contracts, 17 interfaces, 7 enums)
- **Duplicates:** PASS (982 tracked files)
- **App build:** PASS
- **Mock build:** PASS

---

## Scan and role-walk results (gate, 1 iteration)

- **Mock check:plain:** 0 findings (5 fixes applied: MOCK DATA exempt ×2, copy tweak, archetype exempt, steward-code env var)
- **Real check:plain:** 0 findings
- **check:roles (real service):** 8 PASS, 0 FAIL, 10 SKIP
- **smoke (recorded):** 37 PASS, 1 WARN (steward/usage GET without auth — known P1 limit), 0 FAIL, 1 SKIP (draft isolation, live only)

---

## Deviations and decisions

See `docs/kiro/reports/K9-DECISIONS.md` for the full log. Key items:
- P5 initial verify FAIL (golden-run file missing); PC fixed during merge-a integration.
- P3's K9-P3 status file missing `Live calls` line — assumed 0 (no model calls in spec).
- `ANVESHAN_STEWARD_OPEN` not in original DEPLOY-CHECKLIST; added by PC at finalize.
- Smoke test WARN on `steward/usage` (GET accessible without auth) logged as a known P1 limit.

---

## Blocked / open items

- **WI-5.1 mini pilot (E8):** HUMAN — Jim runs with 3–5 colleagues.
- **WI-5.2 expert review:** HUMAN — Jim arranges.
- **WI-8.1 screenshots cleanup:** Jim's decision D8.
- **WI-8.4 make repo public:** Jim, after merge.
- **steward/usage auth gap:** WARN in smoke; needs a follow-up fix before deploy.

---

## What Claude Code should check before merging to main

1. `git diff main..k9/integration --stat` — confirm no file outside ownership tables was changed.
2. `npm --prefix app run build` and `build:mock` in the integration folder — confirm both still pass.
3. The smoke WARN on `steward/usage`: decide whether to fix before deploy or document.
4. Delete `kiro/k9-*` branches after merge (not `k9/integration` until confirmed on main).

---

Branch `k9/integration` is pushed. Ask Claude Code to review and merge it to main.
