# K9-PC — Integration, verification gate, docs, hand-off

These steps run sequentially in the **integration folder** (`.worktrees\k9-integration`, branch `k9/integration`), at three points in the workflow:
- **merge-a**: after Wave A, the parallel tasks P1–P7;
- **merge-b**: after Wave B, the parallel tasks B1 and B2;
- **gate** and **finalize**: at the end.

Read `K9-00-PRODUCT-UX.md` and the task reports in each task folder's `docs/kiro/reports/` first.

**Status discipline (`K9-ORCHESTRATOR.md` §4) applies:**
- update `.kiro\k9-run\STATUS.md` at the start and end of every section below;
- read `.kiro\k9-run\INBOX.md` before each merge.

---

## 0. Paths

- **Main folder** (read-only for Kiro, except `.kiro\k9-run\`): `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan`.
- **Integration folder:** `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.worktrees\k9-integration`.
- **Python:** `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe` (below: `<py>`).

## 1. merge-a: merge Wave A (order matters; verify after each)

Merge only branches whose verify file `.kiro\k9-run\verify\<ID>.json` has `"verdict": "PASS"`. A task that did not pass is merged **last**, if at all: read its report and status, and merge it only if its failures are small and you can fix them here. Otherwise leave it out, mark it BLOCKED in STATUS.md, and continue.

| # | Branch | Why this order | After merging |
|---|---|---|---|
| 1 | `kiro/k9-p1-backend` | The backend that others build on | — |
| 2 | `kiro/k9-p5-origami-universal` | `track_a/api.py`: P5 owns `list_cases`, `to_view` and `_summary`; P1 owns `_summary_composed`. Different functions, so a textual conflict is unlikely; if one happens, keep both changes. | — |
| 3 | `kiro/k9-p4-samples` | — | Register the router in `service/anveshan_service/main.py`: add `samples` to the import list `from anveshan_service.routes import ...` and to the `for module in (...)` tuple, **before** `compose` (so `/api/compose/samples` is not shadowed by `/api/compose/{draft_id}`). Then run P4's tests through the normal `create_app` and remove the explicit `include_router` from P4's test fixture if it now double-registers. Remove P4's `find_spec` guard around the insights call (P1 is merged). |
| 4 | `kiro/k9-p6-docs` | — | — |
| 5 | `kiro/k9-p7-tools` | — | — |
| 6 | `kiro/k9-p2-learner` | — | — |
| 7 | `kiro/k9-p3-creator-steward` | — | — |

**Each merge:**

```powershell
git merge --no-ff <branch> -m "merge: <ID> <one-line summary>"
```

**Conflict rules:**
- The ownership tables make conflicts rare. For a conflict in a file touched by Phase 0, keep both sides' additions.
- Never drop a feature to resolve a conflict.
- Log every non-trivial resolution in `docs/kiro/reports/K9-DECISIONS.md`.

After all seven: run §2, apply §3, **sync with main** (§4), run §2 again, then commit and push:

```powershell
git push origin k9/integration
```

Write `.kiro\k9-run\verify\MERGE-A.json` as `{"verdict":"PASS"|"FAIL","notes":"..."}`.

## 2. Verify (after every merge and every fix batch)

```powershell
<py> -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live" | Select-Object -Last 5
<py> .github/scripts/check_governance.py
<py> .github/scripts/check_case_packs.py
<py> .github/scripts/check_contract_parity.py
npm --prefix app run build | Select-Object -Last 5
npm --prefix app run build:mock | Select-Object -Last 5
```

All must pass. Fix in the integration folder with small commits (`fix(k9): …`). Never weaken a test or a check.

## 3. Integration fixes (expected)

1. **`ReviewBadge own`:** in `MySkillsView` and `CreatorPanel`, pass `own` now that P2's `ReviewBadge` supports it.
2. **Real-backend field check:**
   1. Start the service in recorded mode:

      ```powershell
      $env:ANVESHAN_MODE="recorded"; <py> -m uvicorn anveshan_service.main:app --app-dir service --port 8080
      ```

      Run it as a background process and stop it afterwards.
   2. `curl.exe --ssl-no-revoke http://localhost:8080/api/cases` and compare one item's `access` object with `CaseAccess` in `app/src/api/types-product.ts`.
   3. Do the same for `/api/cases/kolam/samples` (against `SampleAttempt`), `/api/compose/samples` (against `SampleSource`), and the steward endpoints.
   4. For the steward endpoints, start the service with `ANVESHAN_STEWARD_OPEN=0` and `ANVESHAN_STEWARD_TOKEN=local-test-code` in the **process environment only**, and send the header.
   5. Fix mismatches on the service side; the TS types are the agreed contract.
3. **`.env.example`:** add commented lines only:

   ```text
   # ANVESHAN_STEWARD_TOKEN=   (long random code; on Cloud Run set it as a secret)
   # ANVESHAN_STEWARD_OPEN=0
   ```

4. **Featured skills:** in the mock and the real app, the Library shows Kolam, the Origami crane (origami-crane) and Tabla. The experimental `origami` is not listed. If P2's filter (`c.hero`) hides origami-crane, fix it: the service sets `hero: true` for it.
5. **Samples in the UI:** with the real service, Practise on Kolam shows three sample cards. "Use this as my first try" returns real feedback in recorded mode, and the second try with the flawed sample completes. Repeat on origami-crane, which uses P5's golden runs.
6. **The samples filter in insights:** check that sample tries do not count as learners in the creator and steward insights (P1 §3.5).
7. **Composer examples:** "Use this example" for `kolam-photo` either works (live mode, or recorded runs present) or shows the friendly "This needs live AI" error with the AI key prompt in recorded mode. Either is acceptable; log which.

## 4. Sync with `main` (Claude Code may change the UI on `main` while you work)

Jim reviews the UI with Claude Code during the run, so `main` may move. **Before finishing merge-a, merge-b and finalize:**

```powershell
git fetch origin
git merge origin/main -m "merge: sync main into k9/integration"
```

**Conflict policy for files Claude changed on `main`.** Claude announces these in `INBOX.md` as `CHANGED-ON-MAIN` entries, with the commit, files and intent.
1. Keep **both intents** when possible: Claude's layout or behaviour change plus K9's plain-language and role rules.
2. If they truly conflict:
   - **Claude's change wins** for visual and layout decisions Jim asked for;
   - **K9 wins** for the copy dictionary (K9-00 §5) and for hiding audit tooling from learners.
3. Log each resolution in `K9-DECISIONS.md` with both commit ids.
4. After the sync, run §2 and the plain-language scan (§6).

## 5. merge-b: merge Wave B

1. Merge order: `kiro/k9-b2-stability`, then `kiro/k9-b1-evidence-a11y`.
2. B1 renders `app/public/evidence.json` from B2. Check the page with real data in `dev:mock`; the file is static, so the mock serves it too.
3. Run §2, sync with main (§4), run §2 again, then push.
4. Write `.kiro\k9-run\verify\MERGE-B.json`.

## 6. Gate (repeat until it passes; at most 4 iterations)

**Each iteration:**
1. Mock app:

   ```powershell
   npm --prefix app run dev:mock
   ```

   Start it as a background process on port 5174, then run `npm --prefix app run check:plain`.
2. Real app:
   1. `npm --prefix app run build`;
   2. start the service on 8080 in recorded mode, with `ANVESHAN_STEWARD_OPEN=0` and `ANVESHAN_STEWARD_TOKEN=local-test-code` in the process env;
   3. `$env:ANVESHAN_URL="http://localhost:8080"; npm --prefix app run check:plain`;
   4. `npm --prefix app run check:roles` (P7 §5; uses the same service; steward code from `ANVESHAN_STEWARD_CODE=local-test-code`).
3. `<py> tools/smoke_deployed.py http://localhost:8080 --insecure`, with `ANVESHAN_SMOKE_STEWARD_CODE=local-test-code`.
4. Fix the findings in the owning files (ownership no longer matters at this stage), commit, and re-run §2.
5. Write `.kiro\k9-run\verify\PC.json`:
   - `{"verdict":"PASS"}` when the scans have 0 findings, the role walk passes and the smoke test has no FAIL;
   - otherwise `{"verdict":"FAIL","findings":[...]}`.

Stop the background servers at the end of each iteration.

## 7. Finalize: docs, final sync, report, push

1. **Docs:**

| Doc | Change |
|---|---|
| `docs/HANDOFF.md` | A dated entry "K9 product roles: shipped": what shipped, how to run `check:plain`, `check:roles` and `tools/smoke_deployed.py`, the steward env vars, and the remaining human tasks |
| `docs/status/NOW.md` | In "Product roles and surfaces", mark it IMPLEMENTED (branch `k9/integration`, pending merge to main) |
| `docs/validation/experiments.md` | Append **E-K9: plain-language scan and role walk**: date, mock and real runs, screens scanned, findings before → after, role-walk steps and results, smoke results. Engineering evidence only. |
| `docs/plans/technical-panel-plan-2026-10-07.md` | A status line under each WS/WI heading: DONE (K9-…) / NEXT / HUMAN. Use the coverage table in `K9-ORCHESTRATOR.md` §6. |
| `docs/research/judges-panel-review-2026-10-07.md` | Confirm P6's "DONE (K9)" statuses now that everything is merged; adjust any that did not land |
| `docs/deploy/DEPLOY-CHECKLIST.md` | Check that P1's rows are present: steward secret, `ANVESHAN_STEWARD_OPEN` unset, the auth rate limit |

2. **Final sync** with main (§4), §2 and the gate scans one last time.
3. **Report:** write `docs/kiro/reports/K9-REPORT.md` (≤ 80 lines):
   - phases with commit ranges;
   - test, check and build counts;
   - scan and role-walk and smoke results;
   - live calls used, per task;
   - deviations;
   - blocked items;
   - "What Claude Code should check before merging to main".
4. **Push:** commit, then `git push origin k9/integration`.
5. Update STATUS.md to `DONE` with the final commit hash.
6. **Never push to `main`.** Claude Code reviews and merges.
