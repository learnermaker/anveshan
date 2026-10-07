# K9 Orchestrator: one Kiro session, one workflow, maximum parallel work

**What K9 is.** On 2026-10-07 Jim decided that Anveshan serves three roles:
- **learners**, with plain language and trust shown as useful explanations;
- **creators**, who check what the AI understood, publish their skill and see whether it is being learned;
- **stewards**, who run the review queue, library and moderation, consent and licences, insights and usage.

K9 builds that, plus **every remaining item of the technical-panel plan** that does not need humans (coverage in §6). The product definition is in `docs/product/product-vision.md` §9A and the decision in `docs/status/DECISIONS.md` (2026-10-07).

**How it runs:**
- **one** Kiro session, the parent chat, launches **one workflow**: `.kiro/workflows/k9-build.yaml`;
- the workflow runs Phase 0, then **7 parallel tasks** (Wave A), a merge, **2 parallel tasks** (Wave B), a merge, a verification gate and a finalize step;
- each parallel task works in its **own git worktree** inside this repo (`.worktrees/…`), so tasks never touch the same files.

**Division of labour.** Claude Code did the thinking and planning, so the specs are exhaustive. Kiro executes them literally and reports status continuously (§4). Jim and Claude Code can steer at any time through `.kiro/k9-run/INBOX.md` or the parent chat.

---

## 0. For Jim: how to start (5 minutes)

1. `git pull` in `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan` (main must include this spec).
2. Open **that folder** in Kiro, as the workspace root. Worktrees must sit inside the workspace root, so do not open a parent or child folder.
3. Enable workflows: **Settings → Features → Workflows → on**. Restart the Kiro session.
4. Check the model is **Claude Sonnet 4.6** (the parent session's model is inherited by every step).
5. In a **new** chat, paste this prompt:

> Run the K9 build. First read `docs/kiro/specs/K9-ORCHESTRATOR.md` sections 0–4 and `.kiro/steering/k9-run-rules.md`. Validate the workflow `.kiro/workflows/k9-build.yaml` with validate_workflow. If validation reports an unknown agent name, replace it as described in K9-ORCHESTRATOR.md §5.6 and validate again. Then launch the `k9-build` workflow with no inputs. While it runs, stay in this chat as the orchestrator: every 20–30 minutes, and whenever a step reports, read `.kiro/k9-run/STATUS.md` and the `status/` files, relay any new `.kiro/k9-run/INBOX.md` entries to the affected steps, and answer the steps' questions using the defaults in §8 (never ask me unless a step is blocked by something only a human can do, such as a missing key or a failed push). If the workflow feature is unavailable, use the manual fallback in §10 instead. Finish with the final message from §9.

6. Watch progress:
   - in Kiro's **Workflows** panel;
   - or in `.kiro/k9-run/STATUS.md`, which Claude Code can also read.

   To steer, append an entry to `.kiro/k9-run/INBOX.md` (format in §4.4), or tell the parent chat.

---

## 1. Read, in order (every step reads only what its prompt says; this list is for the parent and Phase 0)

1. This file.
2. `.kiro/steering/k9-run-rules.md` (always included as steering).
3. `docs/kiro/specs/00-COMMON.md`: environment and non-negotiables only. **Ignore its folder table and waves**, which belong to older specs.
4. `docs/kiro/specs/K9-00-PRODUCT-UX.md`: the product brief every task follows.

## 2. Folders and branches

The repo root is `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan` (call it `ROOT`). It stays on `main`, and its tracked files are **never** edited by Kiro. Kiro writes only to `ROOT\.kiro\k9-run\` (gitignored) and `ROOT\.worktrees\` (gitignored).

| Task | Wave | Folder (under `ROOT\.worktrees\`) | Branch | Spec | Live calls |
|---|---|---|---|---|---|
| Integration | 0, merges, gate, finalize | `k9-integration` | `k9/integration` | this file §3, `K9-PC-INTEGRATION.md` | ≤ 10 (gate, only if needed) |
| K9-P1 backend: library, steward, insights, usage | A | `k9-p1-backend` | `kiro/k9-p1-backend` | `K9-P1-BACKEND.md` | 0 |
| K9-P2 learner surface | A | `k9-p2-learner` | `kiro/k9-p2-learner` | `K9-P2-LEARNER.md` | 0 |
| K9-P3 creator and steward UI, navigation | A | `k9-p3-creator-steward` | `kiro/k9-p3-creator-steward` | `K9-P3-CREATOR-STEWARD.md` | 0 |
| K9-P4 sample attempts and example sources | A | `k9-p4-samples` | `kiro/k9-p4-samples` | `K9-P4-SAMPLES.md` | 0 |
| K9-P5 Origami crane via the universal pipeline | A | `k9-p5-origami-universal` | `kiro/k9-p5-origami-universal` | `K9-P5-ORIGAMI-UNIVERSAL.md` | ≤ 40 |
| K9-P6 README, LICENSE, review status, E8/E9 | A | `k9-p6-docs` | `kiro/k9-p6-docs` | `K9-P6-DOCS.md` | 0 |
| K9-P7 smoke test, plain-language scan, role walk | A | `k9-p7-tools` | `kiro/k9-p7-tools` | `K9-P7-TOOLS.md` | 0 |
| K9-B1 "How we check" page and accessibility sweep | B | `k9-b1-evidence-a11y` | `kiro/k9-b1-evidence-a11y` | `K9-B1-EVIDENCE-A11Y.md` | 0 |
| K9-B2 stability numbers and evidence file | B | `k9-b2-stability` | `kiro/k9-b2-stability` | `K9-B2-STABILITY.md` | ≤ 60 |

- **Python:** `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe` (below: `<py>`). Worktrees have no `.venv`; always use this absolute path, and run pytest from the worktree root so its `conftest.py` is used.
- **Node:** each worktree that builds the app needs an `app\node_modules` **junction** to `ROOT\app\node_modules` (§3). Never run `npm install`.
- **`.env`:** only P5, B2 and the gate copy `ROOT\.env` into their worktree root (it is gitignored). Never print it.

## 3. Phase 0 (workflow step `phase0`)

Run from PowerShell. Every command must succeed; stop and report the exact error otherwise.

### 3.1 Integration worktree and foundation

```powershell
cd C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan
git fetch origin
git worktree add -b k9/integration .worktrees\k9-integration origin/main
cmd /c mklink /J ".worktrees\k9-integration\app\node_modules" "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\app\node_modules"
cd .worktrees\k9-integration
<py> docs\kiro\specs\K9-P0-files\apply_p0.py
npm --prefix app run build | Select-Object -Last 5
npm --prefix app run build:mock | Select-Object -Last 5
<py> -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live" | Select-Object -Last 5
git add -A
git commit -m "feat(ui): K9 phase 0 foundation (types, client, mock, plain copy, debug flag, seams)"
git push -u origin k9/integration
```

**What `apply_p0.py` does:** it copies 6 new files and applies 26 anchored edits. Claude Code verified it on 2026-10-07: tsc clean and the mock build passes. If an anchor is missing, the script writes nothing. Then open the named file, make the same edit by hand at the equivalent place, and log it in `docs/kiro/reports/K9-DECISIONS.md`.

**If `k9/integration` or a `.worktrees\k9-*` folder already exists** (a restarted run):
- inspect it with `git -C <folder> log --oneline -5`;
- keep it when it has commits beyond `origin/main` and log that;
- otherwise remove it (`git worktree remove --force <folder>`; `git branch -D <branch>`; also run `cmd /c rmdir <folder>\app\node_modules` **first**, so the junction is removed rather than the real node_modules).

### 3.2 Wave A worktrees

```powershell
cd C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan
foreach ($t in @("k9-p1-backend","k9-p2-learner","k9-p3-creator-steward","k9-p4-samples","k9-p5-origami-universal","k9-p6-docs","k9-p7-tools")) {
  git worktree add -b "kiro/$t" ".worktrees\$t" k9/integration
  cmd /c mklink /J ".worktrees\$t\app\node_modules" "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\app\node_modules"
}
```

### 3.3 Wave B worktrees (done by `merge-a`, after Wave A is merged and pushed)

```powershell
foreach ($t in @("k9-b1-evidence-a11y","k9-b2-stability")) {
  git worktree add -b "kiro/$t" ".worktrees\$t" k9/integration
  cmd /c mklink /J ".worktrees\$t\app\node_modules" "C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\app\node_modules"
}
```

### 3.4 Run files

Create `ROOT\.kiro\k9-run\` with:
- `STATUS.md` (§4.2);
- `INBOX.md`, containing the header from §4.4 and no entries;
- the empty folders `status\`, `verify\` and `reviews\`.

## 4. Status, verify and inbox protocol (how Claude Code and Jim follow and steer the run)

All of these files live in `ROOT\.kiro\k9-run\`, which is gitignored and outside every worktree, so every step can write and read them by absolute path.

### 4.1 Per-task status: `status\<TASK-ID>.md` (written only by that task's steps)

Overwrite the whole file each time:

```markdown
# <TASK-ID> status
- State: STARTED | IN_PROGRESS | VERIFYING | REVIEW_FIXES | DONE | BLOCKED
- Updated: <ISO time>
- Branch / last commit: kiro/<...> @ <short hash> (pushed: yes/no)
- Spec section now: <e.g. §3.5 insights>
- Done so far: <bullets, one per spec section>
- Tests/builds: <last result line>
- Inbox: handled <entry ids> | none
- Blockers: <none | exact error>
- Requests for PC: <none | list>
- Live calls used: <n>
```

Update it:
- at the start;
- after every numbered spec section;
- when blocked;
- at the end of the build, verify, review-fix and finalize steps.

### 4.2 Board: `STATUS.md` (written only by phase0, merge-a, merge-b, gate and finalize)

```markdown
# K9 run — overall status
Updated: <ISO>   Phase: PHASE0 | WAVE_A | MERGE_A | WAVE_B | MERGE_B | GATE | FINALIZE | DONE
| Task | State | Verify | Last commit | Notes |
|---|---|---|---|---|
| K9-P1 | ... | PASS/FAIL/- | ... | ... |
...
Integration branch: k9/integration @ <hash> (pushed)
Open inbox entries: <ids>
```

The board steps refresh it from the `status\` and `verify\` files at their start and end.

### 4.3 Verify results: `verify\<TASK-ID>.json`

Written by the verify step:

```json
{"verdict": "PASS", "commands": ["..."], "tail": "last lines of output", "at": "<ISO>"}
```

The workflow's loops stop on `verdict == "PASS"`, so write exactly `PASS` or `FAIL`.

### 4.4 Inbox: `INBOX.md` (appended by Claude Code or Jim; read by everyone)

The file header:

```markdown
# K9 inbox — instructions for running steps
Append entries at the bottom. Steps read this file at start and after each spec section, act on entries
addressed to their task id or ALL, and acknowledge in their own status file. Board steps mark entries DONE here.
```

Entry format:

```markdown
## IN-<n> · <ISO time> · to: <TASK-ID | ALL | PC> · from: Claude | Jim · type: INSTRUCTION | CHANGED-ON-MAIN | FYI
<what to do, concrete files and acceptance>
Status: OPEN
```

- `CHANGED-ON-MAIN` entries tell the integrator that Claude Code changed files on `main` (commit, files and intent). `K9-PC-INTEGRATION.md` §4 says how to merge them.
- Only the board steps change `Status: OPEN` to `Status: DONE (<step>, <commit>)`. The parent chat may also do it after relaying an instruction.

### 4.5 Pushing

- Each task pushes its branch after every numbered spec section: `git push -u origin <branch>`.
- The integrator pushes `k9/integration` after Phase 0, after merge-a, after merge-b, after each gate iteration and at finalize.
- **Nobody pushes `main`.**

## 5. The task contract (used by every Wave A and Wave B step)

### 5.1 File ownership (no two tasks share a file)

| Task | Owns (may edit) |
|---|---|
| P1 | `service/**` except P4's files; `tracks/common/models.py` (usage counters only); `tracks/track-a/src/track_a/api.py` function `_summary_composed` only; `tools/apply_expert_review.py`; `docs/plans/service-api.md`; `docs/deploy/DEPLOY-CHECKLIST.md` |
| P2 | `app/src/hero/**`; `app/src/components/DiscoveryView.tsx`; `app/src/components/HowItWorks.tsx` |
| P3 | `app/src/App.tsx`; `app/src/components/Header.tsx`; `app/src/components/composer/**`; new `app/src/components/{creator,steward,insights}/**`; `app/src/api/mock/library.ts` |
| P4 | `service/anveshan_service/samples.py`; `service/anveshan_service/routes/samples.py`; `service/tests/test_k9_samples.py`; `tools/make_samples.py`; `tracks/cases/kolam/samples/**`; `tracks/cases/tabla/samples/**`; `tracks/samples/**`; `.github/scripts/check_case_packs.py` |
| P5 | `tracks/cases/origami-crane/**`; `tracks/cases/index.json`; `tracks/track-a/src/track_a/config.py`; `track_a/api.py` functions `list_cases`, `_summary` and `CaseHandoff.to_view` only; `tracks/cases/origami/manifest.json` (title only); `tools/build_curated_composed.py`; `tools/fetch_media.py`; new `tracks/track-a/tests/test_origami_crane_pack.py`, plus listing expectations in existing tests |
| P6 | `README.md`; `LICENSE`; `docs/research/judges-panel-review-2026-10-07.md`; `docs/plans/NEXT-STEPS.md`; `docs/validation/experiments.md` (E8 and E9 only) |
| P7 | `tools/smoke_deployed.py`; `app/scripts/**`; `app/package.json` (`scripts` block only); `app/src/api/errors.ts` |
| B1 | All of `app/**` except `app/public/evidence.json` and `app/scripts/**`; one exception: adding `?view=evidence` to the walk in `check_plain_language.mjs` |
| B2 | `tools/stability_runs.py`; `app/public/evidence.json`; `docs/validation/experiments.md` (E10 only); `docs/validation/stability-2026-10.json` |
| Integration | Anything, for merge fixes, plus `.env.example` and the docs in `K9-PC-INTEGRATION.md` §7 |

**Frozen during Wave A** (only Phase 0 or the integrator changes them):
- `app/src/api/client.ts`, `types.ts`, `types-product.ts`, `mock.ts`, `mock/samples.ts`, `debug.ts`, `steward.ts`;
- `app/src/copy/plain.ts`;
- `app/src/vite-env.d.ts`;
- `app/src/types/workspace.ts`.

### 5.2 Task prompt (build step: "You are task {ID}…")

1. Work **only** in `{FOLDER}` (absolute: `ROOT\{FOLDER}`), on branch `{BRANCH}`. Run all commands from that folder.
2. Write your status file now (State: STARTED). Read `ROOT\.kiro\k9-run\INBOX.md`.
3. Read, in order:
   - `{FOLDER}\docs\kiro\specs\00-COMMON.md` (environment and non-negotiables only);
   - `{FOLDER}\docs\kiro\specs\K9-00-PRODUCT-UX.md`;
   - `{FOLDER}\docs\kiro\specs\{SPEC}`.
4. Follow your spec **section by section, in order**. After each numbered section:
   1. run the quick checks the spec names;
   2. commit (`type(scope): … ({ID} §n)`);
   3. push;
   4. update your status file;
   5. re-read the inbox.
5. Edit only the files in your row of §5.1. Need another file changed? Add it to "Requests for PC" and work around it.
6. Keep within your live-call budget (§2). No new dependencies. Never print secrets.
7. **When the spec's acceptance section is met:**
   - write `{FOLDER}\docs\kiro\reports\{ID}-REPORT.md` (≤ 60 lines: Done, Tests, Deviations, Requests for PC, Open issues, Live calls);
   - commit and push it;
   - set your status to VERIFYING;
   - finish with `send_message` (severity success, one line).

### 5.3 Verify step ("Verify task {ID}…"; runs up to 3 times)

1. In `{FOLDER}`, read `ROOT\.kiro\k9-run\verify\{ID}.json` if it exists. On a previous FAIL, fix those failures first, staying within §5.1, then commit and push.
2. Run the task's must-pass commands:

| Task | Must pass |
|---|---|
| P1, P4, P5 | `<py> -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"`; `<py> .github/scripts/check_governance.py`; `<py> .github/scripts/check_case_packs.py` (P5 only: a failure caused solely by the checker not knowing a curated universal pack is acceptable when it is listed under "Requests for PC"); `<py> .github/scripts/check_contract_parity.py` |
| P2, P3, B1 | `npm --prefix app run build`; `npm --prefix app run build:mock` |
| P6 | `<py> .github/scripts/check_governance.py`; `Select-String -Path README.md -Pattern "â€\|Ã" -Quiet` is false; `LICENSE` contains "Apache License" |
| P7 | `npm --prefix app run build`; `node app/scripts/check_plain_language.mjs --self-test`; `<py> -m py_compile tools/smoke_deployed.py` |
| B2 | `<py> -m py_compile tools/stability_runs.py`; `app/public/evidence.json` parses as JSON with the keys `generated_at`, `tests`, `skills` and `not_yet` |

3. Also check that `git status` is clean and the branch is pushed.
4. Write `ROOT\.kiro\k9-run\verify\{ID}.json` with `PASS` only when every command passed; otherwise `FAIL` and the failing output tail.
5. Update the status file.

### 5.4 Review step ("Review task {ID}…"; read-only)

- Do not edit code or commit.
- Compare the work in `{FOLDER}` (use `git -C {FOLDER} diff k9/integration...HEAD --stat`, then read the changed files) against:
  1. its spec's acceptance section and every numbered instruction;
  2. `K9-00-PRODUCT-UX.md` §3, §5 and §7 (UI tasks: plain language, honesty labels, one primary action, accessibility; backend: privacy, security, determinism);
  3. the ownership row in §5.1.
- Write `ROOT\.kiro\k9-run\reviews\{ID}.md` with findings labelled **MUST** (spec violation, broken behaviour, privacy or security issue, honesty violation) or **SHOULD** (quality). Each finding gives the file, the line and the exact fix. End with the verdict `APPROVED` (no MUST) or `REVISE`.

### 5.5 Fix step ("Apply the review for task {ID}…")

1. Read the review.
2. Fix every **MUST**, and **SHOULD** items that take under 10 minutes each, within §5.1.
3. Re-run the §5.3 must-pass commands, update `verify\{ID}.json`, commit and push.
4. Set the status to DONE, or BLOCKED with the reason.
5. Add a "Review fixes" section to the report.

### 5.6 Agent names in the recipe

The recipe uses Kiro's workflow agents:
- `wf-coder` for build, verify and fix;
- `semantic_reviewer` for reviews.

If `validate_workflow` reports either as unknown, replace `semantic_reviewer` with `wf-planner` (read-only planner) and `wf-coder` with the coding agent name that validation lists. Re-validate and log it in `K9-DECISIONS.md`. Do not change anything else in the recipe.

## 6. Coverage: technical-panel plan items (`docs/plans/technical-panel-plan-2026-10-07.md`)

| Plan item | Status before K9 | K9 task |
|---|---|---|
| WS1 deployment safety (WI-1.1–1.6) | DONE on main | P7 adds the WS1 gate `tools/smoke_deployed.py` |
| WI-2.1 Origami via the universal pipeline (D1); dedupe the properties; the experimental label | Open | **P5** |
| WI-2.2 chrome cleanup, WI-2.3 collapse the showcase | DONE on main | P2/P3 finish the plain-language and navigation side |
| WI-2.4 README rewrite | Open | **P6** |
| WI-3.1 sample attempts and example sources | Open | **P4** (backend and content), **P2** (practice picker), **P3** (composer examples), **P5** (Origami samples) |
| WI-3.2 live cache | DONE on main | — |
| WI-4.1 AI coaching wording | DONE on main | P6 adds evidence entry E8 |
| WI-4.2 drills, WI-4.3 show-me | DONE on main | P2 rewords the drill card |
| WI-5.1 pilot, WI-5.2 expert review | Humans (Jim) | P1 builds `tools/apply_expert_review.py`; the steward console supports the review |
| WI-5.3 evidence page | Open | **B1** ("How we check" page) |
| WI-5.4 stability numbers | Open | **B2** |
| WS6 universal robustness | Moved to NEXT (decision 2026-10-07) | — |
| WI-7.1 accessibility | Open | **B1** (sweep) plus P2 and P3 in their own files |
| WI-8.1 screenshots cleanup | Kept (D8, Jim) | — |
| WI-8.2 legacy synthetic UI | Kept (the showcase is collapsed, not removed) | — |
| WI-8.3 split `universal.py` | Deferred until after submission | — |
| WI-8.4 LICENSE and making the repo public | LICENSE open; making it public is Jim's job | **P6** (LICENSE) |
| WS9 three product roles | Decided | **P1, P2, P3** (+ P7 checks, PC gate) |
| Minor: friendly key-check error; verify retry → Results; mobile check | Open | **P7** (errors), **P7/PC** role walk and scan, **B1** (mobile) |
| BYOK note in the deploy checklist; E9 BYOK evidence | Open | **P1** (checklist), **P6** (E9) |
| Status of each J-finding; plan status | Open | **P6** (review doc), **PC** (plan status lines) |

## 7. Live-call and cost budget

Total ≤ 110 live calls: P5 ≤ 40, B2 ≤ 60, gate ≤ 10. All other steps make 0. Each task records its count in its status file and report. If a budget would be exceeded, stop that part, record what is missing, and continue with the rest.

## 8. Defaults when unsure (in priority order; log each use in `docs/kiro/reports/K9-DECISIONS.md`)

1. Keep the eight contracts frozen (`tracks/common/schemas/`, `app/src/types/contracts.ts`).
2. Plain language for learners and creators wins over completeness. With no plain translation, hide it from them (DEBUG only). Never drop an honesty label.
3. Deterministic over model-based; never add a model call beyond the budgets.
4. The smaller change that meets the acceptance criteria. No features that are not in the specs.
5. **Privacy first:** when unsure whether someone may see something, they may not. Insights never include names, raw session IDs or media.
6. Spec intent over the spec's literal text when the code has moved.
7. **Blocked:** finish everything else, mark BLOCKED with the exact error, and continue.
8. **An inbox instruction that conflicts with 1–5:** do not apply it; record why in the status file. The parent chat raises it with Jim.

## 9. Final message to Jim (≤ 60 lines; written by `finalize`)

- Phases done, with commit ranges (`git log --oneline origin/main..k9/integration`: count, first and last hash).
- Per task: verify verdict, review verdict, live calls.
- Test, check and build counts.
- Plain-language scan (mock and real), role walk, smoke results.
- Deviations and decisions (link `K9-DECISIONS.md`); blocked or open items.
- "Branch `k9/integration` is pushed. Ask Claude Code to review and merge it to main."
- **Reminders for Jim:**
  - set `ANVESHAN_STEWARD_TOKEN` as a Cloud Run secret before deploying;
  - register the team by 2026-10-11;
  - submission is due 2026-10-18;
  - the remote `kiro/k9-*` branches can be deleted after the merge.

## 10. Manual fallback (only if the workflow feature is unavailable)

The parent chat does exactly what the recipe does, using parallel sub-agent tasks:
1. Run §3 itself.
2. Start the 7 Wave A tasks **at the same time** as sub-agents. Each gets the §5.2 prompt with its row from §2; then a verify pass (§5.3, up to 3 times), a review pass (§5.4) and a fix pass (§5.5).
3. Run `K9-PC-INTEGRATION.md` §1–§4 itself.
4. Create the Wave B worktrees (§3.3) and run B1 and B2 in parallel the same way.
5. Run PC §5, §6 (repeat ≤ 4) and §7.

The status, verify and inbox files work exactly the same.
