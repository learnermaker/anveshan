# K9 Orchestrator — ONE Kiro session builds the three product roles (workflows with parallel tasks)

You are the single orchestrating Kiro session (Sonnet 4.6) for **K9: three product roles and end-user-centric surfaces**. Jim will not answer questions while you work. Decide using the defaults in §7 and log every decision in `docs/kiro/reports/K9-DECISIONS.md`.

**Why K9 exists (one paragraph).** The app showed evaluation machinery to learners: claim IDs, confidence numbers, "Approve package" and run classes. It looked like an evaluation tool, not a product. Jim decided on 2026-10-07 that Anveshan serves three roles:
- **learners**, with plain language and trust shown as useful explanations;
- **creators**, who publish their own skill, see whether it is being learned, and check what the AI understood;
- **stewards**, who curate the library: review queue, consent and licences, moderation, insights and usage.

Read the decision in `docs/status/DECISIONS.md` (2026-10-07) and the product definition in `docs/product/product-vision.md` §9A.

---

## Paste this into Kiro to start (Jim)

> You are the K9 orchestrator. Open and follow `docs/kiro/specs/K9-ORCHESTRATOR.md` exactly, from §1 to §8. Read the files it lists in the order given. Run Phase 0 yourself; run P1, P2 and P3 as three parallel tasks, each confined to its own folder; then run PC yourself. Do not ask me questions; use §7 defaults and log decisions. Finish with the final message in §8.

---

## 1. Read, in order (only these; use partial reads for big files)

1. This file.
2. `docs/kiro/specs/00-COMMON.md`: environment, venv path, non-negotiables. **Ignore its folder table and waves**, which belong to older specs; §2 below defines K9's folders.
3. `docs/kiro/specs/K9-00-PRODUCT-UX.md`: the product brief every task follows.
4. Skim the specs for the tasks you dispatch, so you can check their work: `K9-P1-BACKEND.md`, `K9-P2-LEARNER.md`, `K9-P3-CREATOR-STEWARD.md`, `K9-PC-INTEGRATION.md`.

**Token discipline:**
- Use `grep -n` and partial reads.
- Never open `package-lock.json`, `app/dist`, golden runs, `.npy`, media, JSON fixtures or `app/src/data/cases/registry.ts`.
- Pipe test output through `| Select-Object -Last 15`.

## 2. Folders and branches (golden rule: one folder per parallel task)

All folders are under `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\`. The main repo folder `anveshan` stays on `main` and is **read-only for you**, except for running `git worktree add` from it.

| Task | Folder | Branch | Created from |
|---|---|---|---|
| Integration (you: Phase 0 and PC) | `anveshan-wt\k9-integration` | `k9/integration` | `main` |
| P1 backend | `anveshan-wt\k9-p1-backend` | `kiro/k9-p1-backend` | `k9/integration` after Phase 0 |
| P2 learner UI | `anveshan-wt\k9-p2-learner` | `kiro/k9-p2-learner` | `k9/integration` after Phase 0 |
| P3 creator and steward UI | `anveshan-wt\k9-p3-creator-steward` | `kiro/k9-p3-creator-steward` | `k9/integration` after Phase 0 |

**Python:** `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe` (below: `<py>`). Worktrees have no `.venv`; always use this absolute path.

**Node:** each worktree needs `app/node_modules`. Do not run `npm install`, because the lockfile must not change. Create a directory junction to the main folder's `node_modules`:

```powershell
cmd /c mklink /J "<worktree>\app\node_modules" "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\app\node_modules"
```

**Media:** P1 does not need case media. If a test needs it, run `<py> tools\fetch_media.py --from-dir C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\var\scratch\media` in that worktree.

**API key:** not needed for K9. Do not copy `.env` into worktrees, except for the optional live step in PC §5 (≤ 10 live calls). Never print it.

## 3. Phase 0: shared foundation (you, sequential, about 10 minutes)

```powershell
cd C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan
git fetch origin
git worktree add -b k9/integration ..\anveshan-wt\k9-integration origin/main
cmd /c mklink /J "..\anveshan-wt\k9-integration\app\node_modules" "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\app\node_modules"
cd ..\anveshan-wt\k9-integration
<py> docs\kiro\specs\K9-P0-files\apply_p0.py
npm --prefix app run build | Select-Object -Last 5
npm --prefix app run build:mock | Select-Object -Last 5
<py> -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live" | Select-Object -Last 5
git add -A
git commit -m "feat(ui): K9 phase 0 foundation (types, client, mock, plain copy, debug flag, seams)"
```

**What `apply_p0.py` does:** it copies 5 new files and applies 26 anchored edits. It refuses to write anything if an anchor is missing.

**If it reports a missing anchor:** a file changed after the spec was written. Open that file, find the equivalent location, make the edit by hand exactly as the script's replacement text says, and log it.

**Do not continue until both builds and the tests pass.**

Then create the three task worktrees from the committed foundation:

```powershell
cd C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan
git worktree add -b kiro/k9-p1-backend ..\anveshan-wt\k9-p1-backend k9/integration
git worktree add -b kiro/k9-p2-learner ..\anveshan-wt\k9-p2-learner k9/integration
git worktree add -b kiro/k9-p3-creator-steward ..\anveshan-wt\k9-p3-creator-steward k9/integration
cmd /c mklink /J "..\anveshan-wt\k9-p2-learner\app\node_modules" "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\app\node_modules"
cmd /c mklink /J "..\anveshan-wt\k9-p3-creator-steward\app\node_modules" "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\app\node_modules"
```

If any `anveshan-wt\k9-*` folder or branch already exists from an earlier attempt, inspect it first:
- with unmerged commits, keep it and log it;
- if it is empty, remove it with `git worktree remove <folder>` and `git branch -D <branch>`.

## 4. Phase A: three parallel tasks

Start all three at once as parallel tasks (sub-agents). Give each task exactly the prompt below, with its row filled in. **The tasks must never edit outside their folder.**

### Task prompt template

> You are task **{ID}** of the K9 build. Work **only** in the folder `{FOLDER}` (git branch `{BRANCH}`). Never edit files in any other folder, never merge, rebase, push or switch branches, and never edit files outside your spec's §1 ownership list.
> Read, in order: `{FOLDER}\docs\kiro\specs\00-COMMON.md` (environment and non-negotiables only; ignore its folder table), `{FOLDER}\docs\kiro\specs\K9-00-PRODUCT-UX.md`, then your spec `{FOLDER}\docs\kiro\specs\{SPEC}`. Follow your spec section by section. Commit after every numbered section with the message format it gives.
> Python: `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe`. Node: run npm with `--prefix app` from your folder (`app/node_modules` is a junction; never run `npm install`).
> No live model calls. No new dependencies. Never print secrets.
> When done, write `docs/kiro/reports/{ID}-REPORT.md` (≤ 60 lines: Done, Tests, Deviations, Requests for PC, Open issues), commit it, and reply "{ID} complete".

| ID | FOLDER | BRANCH | SPEC | Must pass before reporting |
|---|---|---|---|---|
| K9-P1 | `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan-wt\k9-p1-backend` | `kiro/k9-p1-backend` | `K9-P1-BACKEND.md` | the full non-live pytest suite; the governance, case-pack and contract-parity checks |
| K9-P2 | `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan-wt\k9-p2-learner` | `kiro/k9-p2-learner` | `K9-P2-LEARNER.md` | `npm --prefix app run build` and `build:mock` |
| K9-P3 | `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan-wt\k9-p3-creator-steward` | `kiro/k9-p3-creator-steward` | `K9-P3-CREATOR-STEWARD.md` | `npm --prefix app run build` and `build:mock` |

**Ownership summary** (no two tasks share a file):
- **P1:** `service/**`, `tracks/common/models.py` (counters only), `tracks/track-a/src/track_a/api.py` (`_summary_composed` only), `tools/apply_expert_review.py`, `docs/plans/service-api.md`, `docs/deploy/DEPLOY-CHECKLIST.md`.
- **P2:**
  - `app/src/hero/**`;
  - `app/src/components/DiscoveryView.tsx`;
  - `app/src/components/HowItWorks.tsx`.
- **P3:**
  - `app/src/App.tsx`;
  - `app/src/components/Header.tsx`;
  - `app/src/components/composer/**`;
  - new `app/src/components/{creator,steward,insights}/**`;
  - `app/src/api/mock/library.ts`.
- **Frozen after Phase 0** (nobody edits them in Phase A):
  - `app/src/api/client.ts`;
  - `app/src/api/types.ts` and `types-product.ts`;
  - `app/src/api/mock.ts`;
  - `app/src/vite-env.d.ts`;
  - `app/src/copy/plain.ts`;
  - `app/src/api/debug.ts`;
  - `app/src/api/steward.ts`.

  A task that needs a change there writes it under "Requests for PC" and works around it.

**While the tasks run,** you may do read-only work: reading their commits with `git -C <folder> log --oneline`, and preparing the PC scripts in your integration folder. You may write `app/scripts/check_plain_language.mjs` and `check_roles.mjs` in the integration folder now, because no task owns `app/scripts/`.

**When a task reports complete:**
1. Check its folder: `git -C <folder> status` must be clean; read its report.
2. Run its "must pass" commands yourself in its folder.
3. If something fails, send the task back with the exact failure, or fix trivial issues yourself **in that task's folder**, committed on its branch.

## 5. Phase C: integration (you, sequential)

Follow `K9-PC-INTEGRATION.md` §1–§7 in the integration folder: merge P1 → P2 → P3, verifying after each merge, then:
- the integration fixes;
- the plain-language scan (mock, then the real service);
- the end-to-end role walk;
- the docs updates;
- the final report.

**Push only `k9/integration`.**

## 6. Live-call and cost budget

| Phase | Live model calls allowed |
|---|---|
| Phase 0, Phase A | 0 |
| PC §5 role walk | ≤ 10, only if recorded mode cannot exercise the composer |

Record the number used in the report.

## 7. Defaults when unsure (in priority order; log each use)

1. Keep the eight contracts frozen (`tracks/common/schemas/`, `app/src/types/contracts.ts`).
2. Plain language for learners and creators wins over completeness. If a technical detail has no plain translation, hide it from them (DEBUG only), and never drop an honesty label.
3. Prefer deterministic logic; never add a model call.
4. Prefer the smaller change that meets the acceptance criteria. Do not add features that are not in the specs.
5. **Privacy first:**
   - when unsure whether a steward or another visitor may see something, they may not;
   - insights never include names, raw session IDs or media.
6. **If a spec instruction conflicts with the code as it is now** (renamed function, moved line), follow the spec's intent at the new location and log it.
7. If something is blocked (a tool failure, Chrome missing for puppeteer), finish everything else, mark the item BLOCKED in the report with the exact error, and continue.

## 8. Final message to Jim (≤ 60 lines)

- Phases done, with commit ranges (`git log --oneline origin/main..k9/integration | Measure-Object -Line` and the first and last hashes).
- Test, check and build results (counts).
- The plain-language scan: screens scanned and findings (mock, real).
- The role walk: each step pass/fail.
- Live calls used.
- Deviations and decisions (link `K9-DECISIONS.md`).
- Blocked or open items.
- "Branch `k9/integration` is pushed. Ask Claude Code to review and merge it to `main`."
- Reminders:
  - set `ANVESHAN_STEWARD_TOKEN` as a Cloud Run secret before deploying;
  - register the team by 2026-10-11;
  - submission is due 2026-10-18.
