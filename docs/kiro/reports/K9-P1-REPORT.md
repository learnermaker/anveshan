# K9-P1 Report

## Done

**Settings (§3.1):** Added `steward_token`, `steward_open`, `insights_max_events`, `steward_enabled` property, and `"auth": 10` to `CLOUD_RATE_LIMITS`.

**Steward identity (§3.2):** Created `steward.py` with `current_steward` ContextVar, `StewardMiddleware` (pure ASGI), `token_matches` (hmac.compare_digest) and `require_steward` dependency.

**Library (§3.3):** Created `library.py` with `LibraryRecord`, `HistoryEntry`, `kind_of`, `load`, `save`, `create_initial`, `submit`, `withdraw`, `decide`, `blockers`.

**Access (§3.4):** Created `access.py` with `is_owner`, `can_view`, `access_view`. Updated `paths.case_dir` to use `can_view`. Updated `routes/cases.py` to add `access` to every list item and case view, enforce review gating for community cases, and filter unlisted curated cases.

**Insights (§3.5):** Created `insights.py` with event recording (attempt/completion), `compute`, `activity`, `today_totals`. Never stores names or raw session IDs (sha256 hashed). Best-effort recording (never raises into request).

**Metrics (§3.6):** Created `metrics.py` with `Metrics` class and `RouteCountMiddleware`. Updated `limits.py` `RateLimitMiddleware` to count requests. Updated `errors.py` to count error categories.

**Usage counters (§3.8):** Added `UsageCounters` and `USAGE` to `tracks/common/models.py`. Incremented at cache hits and live/own-key calls in `generate_json` and `embed`.

**Steward routes (§3.7):** Created `routes/steward.py` with `/check`, `/overview`, `/queue`, `/library`, `/library/{id}/decide`, `/consent`, `/consent/export`, `/usage`, `/review-export/{id}`.

**Library routes (§3.13):** Created `routes/library.py` with `GET/{id}`, `POST/{id}/submit`, `POST/{id}/withdraw`.

**Insights routes (§3.13):** Created `routes/insights.py` with `GET /api/insights/{id}`.

**Housekeeping (§3.11):** Added `_protected()` to `housekeeping.py`; skip protected (non-private) cases in TTL and cap passes.

**Health (§3.12):** Added `steward_enabled`, `steward_open`, `data_ttl_hours` to `/api/health`.

**Compose hooks (§3.9):** Added `library.create_initial` call in `create_case` and `METRICS.inc("compose_day")` in `analyze_upload`.

**Sessions hooks (§3.5):** Added `insights.record_attempt`, `insights.record_completion`, and `METRICS.inc("attempts_day")` to `routes/sessions.py`.

**Track A fix (§3.10):** Updated `_summary_composed` to compute real `review_status` from the knowledge package using `select_package_version` + `_status`.

**Expert review tool (§3.14):** Created `tools/apply_expert_review.py` with export-form diff and hand-written actions. `--dry-run` flag.

**Docs (§3.15):** Added `## 7. Product roles (K9)` to `docs/plans/service-api.md`. Updated `docs/deploy/DEPLOY-CHECKLIST.md` with new env vars and BYOK note.

## Tests

- `service/tests/test_k9_library.py`: 16 tests — PASS
- `service/tests/test_k9_steward.py`: 14 tests — PASS
- `service/tests/test_k9_insights.py`: 9 tests — PASS
- `service/tests` (all): 146 passed
- `tracks/common/tests` + `tracks/track-a/tests`: 207 passed
- `tracks/track-b/tests`: 166 passed
- `check_governance.py`: PASS
- `check_case_packs.py`: PASS (7 packs)
- `check_contract_parity.py`: PASS (8 contracts)

## Deviations

- `access_view` for missing case directories (fake test cases) returns defaults rather than raising, to keep existing public-demo tests green (see `access.py` comment). Logged per §8.6.
- `test_steward_can_access_insights` uses a submitted (non-private) case, since stewards can only bypass isolation for non-private cases per `can_view` spec. Logged per §8.6.

## Requests for PC

None.

## Open issues

None. All spec acceptance criteria met.

## Review fixes (commit d7cd9d2)

All 4 MUST findings and all 5 SHOULD findings from `.kiro/k9-run/reviews/K9-P1.md` were applied.

**MUST-1 (`library.py` `withdraw`):** Added `WITHDRAWABLE = {"submitted", "returned", "published", "rejected"}` guard. A creator can no longer withdraw a skill from the "unlisted" state, preserving the steward moderation decision.

**MUST-2 (`library.py` `submit`):** Added `if not body.get("rights_confirmed", False): extra_bl.append(...)` check before accepting a submission. A submit with `rights_confirmed=False` now returns 400.

**MUST-3 (`docs/plans/service-api.md`):** Truncated the file to remove the entire duplicate second `## 7. Product roles (K9)` section (chars 12013–14528) which had stripped backticks and garbled identifiers (`pp/src/api`, `ccess: CaseAccess`, `	rue locally`).

**MUST-4 (`routes/compose.py` `create_case`):** Removed the `try/except Exception: pass` wrapper around `library.create_initial`. A failure now surfaces as a request error rather than silently leaving the case without a `.library.json`.

**SHOULD-5 (`docs/deploy/DEPLOY-CHECKLIST.md`):** Merged the orphaned `ANVESHAN_STEWARD_TOKEN` and `ANVESHAN_INSIGHTS_MAX_EVENTS` rows into the existing environment-variable table by removing the blank-line separator.

**SHOULD-6 (`service/tests/test_k9_steward.py`):** Added `test_apply_expert_review_non_dry_run` which uses `unittest.mock.patch("track_a.api.apply_review", ...)` to assert that `apply_review` is called exactly twice (once per action) and with the correct action types when `--dry-run` is omitted.

**SHOULD-7 (`tracks/common/models.py`, `routes/steward.py`):** Added `DailyBudget.today_used()` public helper that returns today's call count without exposing `_day`. Updated both `steward_overview` and `steward_usage` to call `today_used()` instead of `DAILY_BUDGET._day`.

**SHOULD-8 (`routes/compose.py` `analyze_upload`):** Moved the `METRICS.inc("compose_day", ...)` call to inside a `if not (isinstance(view, dict) and view.get("refused")):` guard. Refused uploads no longer inflate the compose metric.

**SHOULD-9 (`routes/cases.py` `list_cases`):** Extended the unlisted curated-case filter into the `isolate_visitors=False` branch so that a steward-unlisted case is hidden for all non-steward visitors regardless of the isolation mode.

**Tests after fixes:** 354 passed, 1 deselected (full service + common + track-a suite, not live).

## Live calls used

0
