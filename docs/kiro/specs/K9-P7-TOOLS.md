# K9-P7 — Verification tools: deployed smoke test, plain-language scan, role walk, friendly errors

Read `00-COMMON.md`, `K9-00-PRODUCT-UX.md`, then this file. Your folder, branch, status file and inbox protocol are in `K9-ORCHESTRATOR.md` §2 and §4.

**Goal.** Build the automated checks the integration phase and the deployment rely on:
- WS1 gate `tools/smoke_deployed.py`;
- the K9 acceptance scripts `check_plain_language.mjs` and `check_roles.mjs`;
- friendly titles for the new error categories.

You write and test the scripts against the **mock** app (Phase 0 mock, `npm --prefix app run dev:mock`) and against the current service. PC runs them against the merged result.

---

## 0. Ground rules

- No new dependencies:
  - Node: `puppeteer-core` (already a devDependency; Chrome at `C:\Program Files\Google\Chrome\Application\chrome.exe`, overridable with `CHROME_PATH`);
  - Python: `httpx` (installed).
- Screenshots go to `var/k9-screens/` (gitignored). **Never** write to `screenshots/`, which is committed.
- No live model calls.
- Selectors: prefer visible text and roles (`button` with text, `[role=tab]`, `input[type=file]`). Add a 10 s timeout per wait, and print which step failed.

## 1. Files you own

- `tools/smoke_deployed.py` (new);
- `app/scripts/check_plain_language.mjs` (new);
- `app/scripts/check_roles.mjs` (new);
- `app/scripts/fixtures/*` (new; tiny PNG/WAV fixtures ≤ 50 KB each);
- `app/package.json`: the `"scripts"` block only;
- `app/src/api/errors.ts` (the `friendlyError` switch only).

## 2. Friendly error titles (`app/src/api/errors.ts`)

Add these cases to `friendlyError` (keep the existing ones):

| Category | Title | Message |
|---|---|---|
| `STEWARD_REQUIRED` | "Steward access needed" | "Enter the steward access code to continue." |
| `STEWARD_DISABLED` | "Steward console not enabled" | "This server does not have a steward console." |
| `NOT_OWNER` | "Only the creator can do this" | the raw message |
| `INVALID_INPUT` with `details.blockers` (array) | "Not ready to publish yet" | the blockers joined with a space |
| `INVALID_INPUT` when the raw message starts with "Google rejected this key" | "That key did not work" | the raw message, with `suggestKey: false` |

## 3. `tools/smoke_deployed.py` (WS1 gate from the technical-panel plan §4)

```text
usage: smoke_deployed.py <base_url> [--steward-code-env ANVESHAN_SMOKE_STEWARD_CODE] [--skip-live]
```

- Uses `httpx` with two separate cookie jars (visitor A and visitor B); `verify=True`. On this Windows network you may need `--insecure` for local testing; add that flag, default off.
- Prints a PASS/FAIL table and exits 1 on any failure.
- **Never prints secrets.** The steward code is read from the env var named by `--steward-code-env`.

**Checks:**
1. `GET /api/health`:
   - `ok: true`;
   - the keys `steward_enabled` and `data_ttl_hours` are present;
   - **on a deployed URL** (not localhost), `mode_override` is false and `curated_review_open` is false.
2. `GET /api/cases`:
   - includes `kolam` and `tabla`;
   - includes `origami-crane` once K9-P5 has merged; tolerate its absence with a WARN;
   - each item has `access`.
3. For each featured case with samples (`GET /api/cases/{id}/samples` returns a non-empty list):
   1. start a session as A (`POST /api/sessions`, `{"case_id", "learner_name": "smoke"}`);
   2. submit the `good` sample (`POST /api/sessions/{sid}/attempts/sample/good`) → 200 with an `evaluation`;
   3. submit the `flawed` sample as the retry → 200;
   4. `POST /complete` → 200.

   Skip a case with a WARN when it has no samples.
4. **Isolation:** create nothing; check that `GET /api/cases/{fake id}~aaaaaaaaaaaa` gives 404 for B. When `--skip-live` is not set and the server is in live mode, also do this: `POST /api/compose/sample/kolam-photo` as A (1 analyse call), get the `draft_id`, then `GET /api/compose/{draft_id}` as B → 404.
5. **Key check:** `POST /api/key/check` with the header `X-Gemini-Api-Key: AIzaInvalidInvalidInvalidInvalid123` → 400. The body must not echo the key.
6. **Steward:**
   - `POST /api/steward/check` without a code → 401, or 403 when not enabled;
   - with the code (if the env var is set) → 200;
   - `GET /api/steward/usage` → 200 with `requests_by_class`.
7. **Rate limit (opt-in, `--check-429`):** hammer `POST /api/steward/check` with a wrong code until 429 (≤ 15 requests); the response has a `Retry-After` header.

Test it locally against `uvicorn` on port 8080 (recorded mode) and paste the table into your report.

## 4. Plain-language scan (`app/scripts/check_plain_language.mjs`)

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

## 5. Role walk (`app/scripts/check_roles.mjs`)

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


**Additions for P7 (you write these scripts now; PC runs them after the merges):**
- `check_plain_language.mjs` must also click **"Try a sample attempt"** when that button exists (P2 adds it) instead of uploading a fixture, so the walk works in recorded mode against the real service. Fall back to the fixture upload when the button is absent.
- While developing in your branch, the learner UI is not yet plain (P2 is changing it in parallel). Expect findings against the mock, and **do not fix UI files**. Your acceptance is that the script runs end to end, reports findings correctly, and exits 1 when there are findings. Prove the matcher with a unit check: a tiny `--self-test` mode that scans a static HTML string containing "CLM-01" and "satisfied" plus a `data-plain-exempt` "claim". It must report exactly "CLM-01" and nothing else.
- `check_roles.mjs` needs the K9 backend (P1) for the real run. In your branch, implement it fully, then run it against the **mock** app for the steps the mock supports (sign-in with code `steward`, queue, publish, My skills). Mark the real-service steps "not run (needs P1)" in your report.
- Add npm scripts to `app/package.json`:
  - `"check:plain": "node scripts/check_plain_language.mjs"`
  - `"check:roles": "node scripts/check_roles.mjs"`

## 6. Acceptance

- `npm --prefix app run build` passes; `errors.ts` compiles.
- `node app/scripts/check_plain_language.mjs --self-test` exits 0.
- The full walk against the mock runs to the end, with findings listed.
- `check_roles.mjs` runs its mock-supported steps.
- `tools/smoke_deployed.py http://localhost:8080` runs with every check PASS or WARN (no FAIL), except the checks that need P1 or P4 endpoints. Mark those "needs P1" or "needs P4".
- Report `docs/kiro/reports/K9-P7-REPORT.md` with the smoke table and the scan output summary.
