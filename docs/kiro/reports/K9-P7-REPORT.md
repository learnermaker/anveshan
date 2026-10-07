# K9-P7 Report — Verification tools

**Task:** K9-P7  **Branch:** kiro/k9-p7-tools  **Date:** 2026-10-07

---

## Done

- **§2 Friendly error titles** — added `STEWARD_REQUIRED`, `STEWARD_DISABLED`, `NOT_OWNER`, `INVALID_INPUT` with blockers array, and `INVALID_INPUT` for "Google rejected this key" to `app/src/api/errors.ts`.
- **§3 `tools/smoke_deployed.py`** — WS1 gate: checks health, cases, session flow (samples), isolation, key check, steward, and optional rate-limit hammer. Prints PASS/WARN/FAIL/SKIP table.
- **§4 `app/scripts/check_plain_language.mjs`** — reads `BANNED_LEARNER_TERMS` from `plain.ts` at runtime, walks 8 mock steps with Puppeteer, scans visible text skipping `data-plain-exempt` elements, saves screenshots to `var/k9-screens/`. `--self-test` mode validates matcher.
- **§5 `app/scripts/check_roles.mjs`** — two-context role walk (visitor A, B, steward). Runs mock-supported steps; marks real-service steps SKIP (needs P1/P3).
- **`app/package.json` scripts** — added `check:plain` and `check:roles`.
- **`app/scripts/fixtures/attempt.png`** — 64×64 white PNG fixture for upload steps.

---

## Tests / Builds

| Check | Result |
|---|---|
| `npm --prefix app run build` | PASS (tsc + vite, 25 s) |
| `node app/scripts/check_plain_language.mjs --self-test` | PASS — CLM-01 found, exempt "claim" not found |
| Plain-language walk (mock, http://localhost:5174) | Ran end-to-end; 56 findings (UI not yet plain — P2/P3 in progress); exit 1 as expected |
| Role walk (mock, http://localhost:5174) | 4 PASS, 0 FAIL, 14 SKIP; exit 0 |
| `python -m py_compile tools/smoke_deployed.py` | PASS |
| `smoke_deployed.py http://localhost:8080 --skip-live` | 8 PASS, 12 WARN, 0 FAIL, 1 SKIP; exit 0 |

### Smoke table (http://localhost:8080, recorded mode, --skip-live)

```
  [+] [PASS] health 200: HTTP 200
  [+] [PASS] health.ok
  [W] [WARN] health has steward_enabled+data_ttl_hours: needs P1: missing keys
  [+] [PASS] cases 200: HTTP 200
  [+] [PASS] cases includes kolam
  [+] [PASS] cases includes tabla
  [W] [WARN] cases includes origami-crane: needs K9-P5 to merge first
  [W] [WARN] case kolam has access: needs P1
  (5 more cases — same WARN)
  [W] [WARN] session/kolam samples endpoint: needs P4
  [W] [WARN] session/tabla samples endpoint: needs P4
  [+] [PASS] unknown case_id returns 404 for visitor B: HTTP 404
  [ ] [SKIP] draft isolation (--skip-live set)
  [+] [PASS] key/check returns 400: HTTP 400
  [+] [PASS] key not echoed in response
  [W] [WARN] steward/check without code: needs P1
  Result: 8 PASS, 12 WARN, 0 FAIL, 1 SKIP
```

---

## Deviations

- Plain-language scan exits 1 against mock (expected: P2/P3 UI not yet updated). Spec permits this — acceptance is that the script runs end-to-end and reports findings.
- Steward console assertion in `check_plain_language.mjs` warns "NO" because P3 hasn't built the steward UI yet. Does not affect scan exit code (scan exits 1 due to findings).
- Role walk step 4 (steward sign-in) SKIPped because P3 steward console is pending.
- Smoke test WARNs on `steward_enabled`, `data_ttl_hours`, case `access` fields, and sample endpoints — all pending P1 and P4.
- `smoke_deployed.py` uses ASCII `[+]`, `[!]`, `[W]`, `[ ]` markers instead of Unicode symbols, because cp1252 cannot encode them on Windows.

---

## Requests for PC

- None.

---

## Open issues

- After P1 merges: re-run smoke to verify `steward_enabled`, `data_ttl_hours`, steward routes, and `access` fields.
- After P4 merges: re-run smoke to verify `/api/cases/{id}/samples` and session-flow checks.
- After P2/P3 merge: re-run `check:plain` to confirm 0 findings; re-run `check:roles` to confirm steward console steps pass.

---

## Live calls used: 0
