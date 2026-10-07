# K9-PC — Integration, end-to-end verification, plain-language scan, docs

This phase is run by the orchestrator, sequentially, in the integration folder (`K9-ORCHESTRATOR.md` §2), after P1, P2 and P3 are complete.

Read `K9-00-PRODUCT-UX.md` and the three reports `docs/kiro/reports/K9-P{1,2,3}-REPORT.md` first.

---

## 1. Merge (order matters)

In the integration folder, on branch `k9/integration`:

```powershell
git merge --no-ff kiro/k9-p1-backend -m "merge: K9-P1 backend (library, steward, insights, usage)"
# verify (§2), fix, commit
git merge --no-ff kiro/k9-p2-learner -m "merge: K9-P2 learner surface"
# verify, fix, commit
git merge --no-ff kiro/k9-p3-creator-steward -m "merge: K9-P3 creator and steward surfaces"
# verify, fix, commit
```

**Conflict rules:**
- P2 and P3 own disjoint files (see their §1), so conflicts should only appear in files that Phase 0 touched. For each conflict, keep both sides' additions.
- The Phase 0 seams (`ownerSlot`, `onOpenMine`) must survive.
- Never resolve a conflict by dropping a feature.

## 2. Verify after every merge

```powershell
.\.venv\Scripts\python.exe -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live" | Select-Object -Last 5
.\.venv\Scripts\python.exe .github/scripts/check_governance.py
.\.venv\Scripts\python.exe .github/scripts/check_case_packs.py
.\.venv\Scripts\python.exe .github/scripts/check_contract_parity.py
npm --prefix app run build | Select-Object -Last 5
npm --prefix app run build:mock | Select-Object -Last 5
```

Use `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe` when the integration folder has no `.venv`. All checks must pass. Fix failures in the integration folder with small commits (`fix(k9): …`). Never weaken a test or check.

## 3. Integration fixes you will almost certainly need

1. **`ReviewBadge own` prop** (P3 request): in `MySkillsView` and `CreatorPanel`, pass `own` now that P2's `ReviewBadge` supports it.
2. **Real-backend field check:**
   1. Start the service.
   2. `curl --ssl-no-revoke http://localhost:8080/api/cases` and compare one item's `access` object with `CaseAccess` in `app/src/api/types-product.ts`.
   3. Do the same for `/api/steward/overview`, `/queue`, `/library`, `/consent` and `/usage`. To exercise the token path, set `ANVESHAN_STEWARD_OPEN=0` and `ANVESHAN_STEWARD_TOKEN=local-test-code` in the process environment for this check only; never commit them.
   4. Fix mismatches on the **service side**: the TS file is the agreed contract from Phase 0. The exception is a TS type that is plainly wrong; then fix both and say so in the report.
3. **`.env` safety:** do not add steward variables to `.env.example` values. Add commented lines only:

   ```text
   # ANVESHAN_STEWARD_TOKEN=   (set a long random code; Cloud Run: secret)
   # ANVESHAN_STEWARD_OPEN=0
   ```

## 4. Plain-language scan (new script, required)

Create `app/scripts/check_plain_language.mjs`, using `puppeteer-core`, which is already a devDependency. Copy the Chrome path, launch and helper conventions from `app/scripts/check_devtools.js`.

**Behaviour:**
- Base URL from `ANVESHAN_URL` (default `http://localhost:5174`, the mock dev server).
- Load `BANNED_LEARNER_TERMS` by reading `app/src/copy/plain.ts` as text. Extract the string literals inside the `BANNED_LEARNER_TERMS` array with a regex, so the TS is not imported.
- **`scan(page, label)`:** in the page, collect visible text of `document.body`, excluding:
  - elements with `[data-plain-exempt]` (and their descendants);
  - elements not rendered (`offsetParent === null`, except `body`);
  - `<script>` and `<style>`.

  Use a TreeWalker over text nodes whose parent chain has no `data-plain-exempt`. Match the terms with the rule in `plain.ts`:
  - a term containing an upper-case letter matches case-sensitively;
  - otherwise case-insensitively;
  - word boundaries `\b` when the term starts and ends with a word character.

  Record `{label, term, snippet}`.
- **Walk (mock mode),** scanning after each numbered step:
  1. Library.
  2. Kolam → Learn.
  3. Practise (start practising; upload a PNG through the photo upload `input[type=file]`. Create a 64×64 PNG fixture at runtime with a canvas in the page, or ship `app/scripts/fixtures/attempt.png` ≤ 10 KB).
  4. The first-try result; open every "Why this feedback?" disclosure.
  5. The second try (upload again) → Results.
  6. Tabla → Learn.
  7. Composer: upload an image fixture → proposal → create → Learn page with the creator panel → open "Check steps" (scan the dialog) → close.
  8. My skills.
- **Then the debug sanity check:**
  - open `?debug=1&view=source&case=kolam`;
  - assert the page **does** contain "CLM-" (proves the debug view still works);
  - do not scan it.
- **The steward console is exempt.** Do not scan it, but open it with code `steward` and assert the Overview renders "Steward console".
- **Output:** print a table of findings and save screenshots of each step to `var/k9-screens/<step>.png`, overwriting files. `var/` is gitignored; never write to `screenshots/`, which is committed. Exit 1 when there is any finding, else 0.
- Add an npm script: `"check:plain": "node scripts/check_plain_language.mjs"`.

**Run it:**
1. `npm --prefix app run dev:mock` in the background.
2. `npm --prefix app run check:plain`.
3. Fix the findings in the owning files. P2's and P3's ownership no longer matters at this stage.
4. Repeat until it passes.

**Also run it against the real service:**
1. `npm --prefix app run build`.
2. Start the service (it serves `app/dist`) on 8080, in recorded mode.
3. `set ANVESHAN_URL=http://localhost:8080` and run the scan.

Recorded mode can only replay recorded runs, so a real-service attempt may fail for an unrecorded upload. Then limit the real-service walk to steps 1, 2, 6 and 8, plus the composer only if recorded. Note this in the report.

## 5. End-to-end role walk (real service, local)

Run the service locally in recorded mode with `ANVESHAN_STEWARD_OPEN=0` and `ANVESHAN_STEWARD_TOKEN=local-test-code` (process env only). Use two browser contexts (puppeteer `browser.createBrowserContext()`) as visitor A and visitor B. Write the walk as `app/scripts/check_roles.mjs`, with the npm script `check:roles`.

1. **A creates a skill.** Use the composer on a small image fixture. If recorded mode cannot analyse a new file, skip creation: start the service in **live** mode only when `.env` exists, with ≤ 10 live calls; otherwise simulate by placing a composed case from the test fixtures, or use the API with the fake composer. **Log which one you used.**
2. A: Check steps → Looks right → Publish (credit "Test Creator", CC BY 4.0, rights) → the status is "Waiting for review".
3. B: the Library does **not** show the skill; a GET of the case returns 404.
4. Steward (context C, sign in with `local-test-code`): the queue shows it → Review → Publish.
5. B: the Library shows it under "Shared by the community", with "Shared by Test Creator". B can open Learn and Practise.
6. A: My skills shows "Published"; "See how learners are doing" opens (empty or with B's attempts).
7. Steward: Library → Hide (with a note) → B no longer sees it. Consent tab → Download works. Usage shows non-zero `requests_by_class`.
8. Wrong steward code → "That code is not right." After 10 tries in an hour → rate limited: test with `ANVESHAN_RATE_AUTH_PER_HOUR=3`.

Exit 1 on any failed assertion. Save screenshots to `var/k9-screens/roles-*.png`.

## 6. Docs (update in the same integration branch)

| Doc | Change |
|---|---|
| `README.md` | A short "Three ways to use Anveshan" section (learner, creator, steward) with one sentence each and how to reach them (`?view=mine`, footer "Steward sign-in"). Do not rewrite other sections. |
| `docs/HANDOFF.md` | A dated entry "2026-10-xx K9 product roles": what shipped, where the specs are, how to run `check:plain` and `check:roles`, the steward env vars. |
| `docs/status/NOW.md` | In the "Product roles and surfaces" paragraph, change "Build spec…" to state IMPLEMENTED with the merge commit. |
| `docs/validation/experiments.md` | A new entry, **E-K9 plain-language and role walk**: the date, mock and real runs, the number of screens scanned, findings before → after, and the role-walk results. This is engineering evidence, not user validation. |
| `docs/plans/technical-panel-plan-2026-10-07.md` | WS9 status → IMPLEMENTED (link the report). |
| `docs/deploy/DEPLOY-CHECKLIST.md` | Steward env vars (secret), `ANVESHAN_STEWARD_OPEN` unset on Cloud Run, the rate limit for auth. |

## 7. Final report and hand-off

- Write `docs/kiro/reports/K9-REPORT.md` (≤ 80 lines):
  - phases and commit ranges;
  - test, check and build counts;
  - plain-scan results (mock and real);
  - role-walk results;
  - deviations from the specs, and why;
  - open issues;
  - what Claude Code should verify before merging to `main`.
- Push the branch: `git push origin k9/integration`. Never push to `main`.
- Tell Jim: **"K9 complete — branch k9/integration ready for review and merge to main."**
