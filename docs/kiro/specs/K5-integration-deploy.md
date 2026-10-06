# K5: End-to-end smoke suite, validation write-up, and Cloud Run deploy

Read `docs/kiro/specs/00-COMMON.md` first. **Start only after Jim says K1, K2, K3 and K4 are merged into `m1/hero-cases`.** Folder `...\anveshan-wt\k5-integration`, branch `kiro/k5-integration`; create it from the latest `m1/hero-cases` at that point. **Needs the API key** (copy `.env`).

## Files you own
- `tools/e2e_smoke.py`
- `service/tests/test_e2e_real.py`
- `docs/validation/experiments.md`, `docs/validation/findings.md`
- `README.md`, the "Current status" and "Implementation Status" sections only
- `docs/deploy/cloud-run.md`
- `docs/kiro/reports/K5-*`

## Steps
1. **Smoke script** `tools/e2e_smoke.py [--base-url URL] [--mode recorded|live]`. Over HTTP it runs, for each hero case:
   - health;
   - list cases;
   - `GET /api/cases/{id}` (goal present);
   - one evidence query that should be answered and one that must be INSUFFICIENT (e.g. "Who originally drew this and what did they intend?" for kolam);
   - a review revise on one claim (see below);
   - a session with a flawed baseline and a better retry, using the eval media (Kolam traces, Tabla synthetic WAVs, Origami synthetic videos);
   - complete.

   It asserts the bundle validates, the gain is a number, and runtime labels are present, then prints a pass/fail table. The review action writes a new package version, so run the smoke test against a temporary copy of `tracks/cases` (pass `ANVESHAN_CASES_ROOT`) and never commit those writes.
2. **Recorded-mode pytest** `service/tests/test_e2e_real.py`: uses `TestClient` with the real tracks and committed golden runs (no key), covering Kolam and Tabla fully and Origami if its golden runs cover the eval attempts.
3. **Validation write-up.** Add dated experiment entries to `docs/validation/experiments.md`, using its template, for:
   - Kolam held-out path validation and synthetic eval;
   - Origami goal-state agreement and attempt eval;
   - Tabla synthetic eval;
   - the Gemma latency probe.

   Use the real numbers from each case's `RESULTS.md`, `KOLAM_PATH_VALIDATION.md` and `K4-latency.md`. Update `docs/validation/findings.md` honestly: these are **engineering and capability evidence on internet and synthetic data**, not human-learner validation. List exactly what remains unvalidated.
4. **README status:** update `README.md` "Current status" / "Implementation Status" to the real state: the three hero cases, how to run locally, the deployed URL once it exists, and what is synthetic.
5. **Cloud Run deploy, with Jim, via the web console.** Follow `docs/kiro/cloud-run-console-guide.md` (from the research session) and `docs/deploy/cloud-run.md`.
   - The branch that gets deployed must contain everything. Ask Jim whether to deploy `m1/hero-cases` or wait for `main`.
   - Build note: the Dockerfile runs `tools/fetch_media.py` during the build, which downloads from Wikimedia (rate-limited). If the Cloud Build step fails with HTTP 429, retry once later. If it fails repeatedly, report it, and propose committing the media to a GCS bucket and fetching from there. **Do not commit large media to git.**
   - After the deploy, run `tools/e2e_smoke.py --base-url https://<service-url> --mode recorded`, then one live Kolam session. Record the results.
   - Put the deployed URL in the README and the deploy doc.
6. **Report:** `docs/kiro/reports/K5-REPORT.md`, with the smoke results (local and deployed), the deploy details (no secrets), and the open issues.

## Acceptance
- The smoke test passes locally in recorded mode and against the deployed URL.
- Validation docs are updated with real numbers and honest scope.
- The README reflects the real state.
- The Definition of Done in 00-COMMON.md is met.
