# K9-P1 — Backend: library, creator publishing, insights, steward console, usage

Read `docs/kiro/specs/00-COMMON.md` (environment), then `K9-00-PRODUCT-UX.md` (product rules), then this file.

Your folder and branch are in `K9-ORCHESTRATOR.md` §2.

You build the service side of the three roles. You never touch `app/`; P2 and P3 build the UI against the JSON shapes in §4, which are already mirrored in `app/src/api/types-product.ts`. **Field names must match exactly.**

---

## 0. Ground rules for this task

- Python only. Use the venv: `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe` (below: `<py>`).
- No new dependencies. Use only the standard library, FastAPI and Pydantic, which are already installed.
- No live model calls. Tests use the fakes in `service/tests/conftest.py` and the patterns in `service/tests/test_public_demo.py`.
- Never change `tracks/common/schemas/*` (the frozen contracts).
- Keep every existing test green. If an existing test must change because a response gained a field, add the field to the test's expectation; never delete an assertion.
- Commit after every numbered step in §9: `feat(service): …`, `test(service): …`.

## 1. Files you own (only these)

**New:**
- `service/anveshan_service/library.py`
- `service/anveshan_service/steward.py`
- `service/anveshan_service/insights.py`
- `service/anveshan_service/metrics.py`
- `service/anveshan_service/access.py`
- `service/anveshan_service/routes/library.py`
- `service/anveshan_service/routes/steward.py`
- `service/anveshan_service/routes/insights.py`
- `service/tests/test_k9_library.py`
- `service/tests/test_k9_steward.py`
- `service/tests/test_k9_insights.py`
- `tools/apply_expert_review.py`

**Modify:**
- `service/anveshan_service/settings.py`
- `service/anveshan_service/main.py`
- `service/anveshan_service/limits.py`
- `service/anveshan_service/paths.py`
- `service/anveshan_service/errors.py` (metrics hook only)
- `service/anveshan_service/housekeeping.py`
- `service/anveshan_service/routes/cases.py`
- `service/anveshan_service/routes/sessions.py`
- `service/anveshan_service/routes/compose.py`
- `service/anveshan_service/routes/health.py`
- `tracks/common/models.py` (usage counters only, §3.8)
- `tracks/track-a/src/track_a/api.py` (only the function `_summary_composed`, §3.10)
- `docs/plans/service-api.md` (add §7)
- `service/tests/test_service_cases.py` (only if the health-shape test needs the new keys)

## 2. Concepts

| Term | Meaning |
|---|---|
| **Curated skill** | A case under `settings.cases_root` (id has no `~`). Shipped with the app. Collection `curated`. Library status `published` by default, or `unlisted` if a steward hid it. Its status is stored in an overlay file in `data_dir`, never in `cases_root`. |
| **Community skill** | A composed case under `<data_dir>/cases/<id>~<12hex>` that has `knowledge/case_profile.v*.json`. Collection `community`. It starts `private` and belongs to its creator (owners file `.owners.json`, see `visitors.py`). |
| **Hero-derived upload** | `<data_dir>/cases/kolam~<12hex>` etc. (no case profile). Private to its owner. **Cannot be published**: its blocker text is "Uploads made from a featured skill can't be published. Share your own skill instead." |
| **Synthetic showcase** | Cases whose list summary has `modality: None` (micrometer, bicycle-repair, handloom-weaving, square-knot). Collection `curated`, status `published`. **Excluded** from every steward list (queue, library, consent) and from insights. |
| **Steward request** | A request whose `X-Steward-Token` header matches `settings.steward_token` (`hmac.compare_digest`), or any request when `settings.steward_open` is true. |

## 3. Design

### 3.1 Settings (`settings.py`)

Add these fields to the `Settings` dataclass, all with defaults, so every existing `Settings(...)` call keeps working:

```python
    steward_token: Optional[str] = None     # ANVESHAN_STEWARD_TOKEN (falls back to ANVESHAN_REVIEW_TOKEN)
    steward_open: bool = False              # no code needed (local development only)
    insights_max_events: int = 5000         # per-skill event log cap
```

In `from_env`:

```python
        steward = (env.get("ANVESHAN_STEWARD_TOKEN") or "").strip() or token   # token = review token computed above
        ...
            steward_token=steward,
            steward_open=_flag(env, "ANVESHAN_STEWARD_OPEN", (not cloud) and steward is None),
            insights_max_events=int(_num(env, "ANVESHAN_INSIGHTS_MAX_EVENTS", 5000)),
```

Add the rate-limit class `"auth": 10` to `CLOUD_RATE_LIMITS`. The existing loop then reads `ANVESHAN_RATE_AUTH_PER_HOUR` automatically.

Also add a property:

```python
    @property
    def steward_enabled(self) -> bool:
        return self.steward_open or bool(self.steward_token)
```

### 3.2 Steward identity (`steward.py`)

```python
current_steward: contextvars.ContextVar[bool]   # default False

def token_matches(settings, token: Optional[str]) -> bool
    # steward_open -> True; else steward_token and token and hmac.compare_digest(token, steward_token)

class StewardMiddleware:   # pure ASGI, like UserKeyMiddleware in userkey.py
    def __init__(self, app, settings): ...
    # reads header b"x-steward-token" (latin-1), sets current_steward to token_matches(...) for the request, resets after

def require_steward(settings: Settings = Depends(get_settings)) -> None:   # FastAPI dependency
    # not settings.steward_enabled -> ServiceError(403, "STEWARD_DISABLED", "The steward console isn't enabled on this server.")
    # not current_steward.get()   -> ServiceError(401, "STEWARD_REQUIRED", "Enter the steward access code to use the steward console.")
```

- Never log the header value. Add `"steward"` to `_SECRET_WORDS` in `errors.py` only if it is not already redacted by the "token" entry (it is: the header name contains "token"); do not otherwise touch the redaction.
- `main.py`: add `app.add_middleware(StewardMiddleware, settings=settings)` next to `UserKeyMiddleware`. Middleware is added in reverse order; place it so it runs **inside** `VisitorMiddleware`, which means adding it before the `VisitorMiddleware` line.
- Register the new routers: `library`, `steward`, `insights`.

### 3.3 Library records (`library.py`)

**Storage:**
- **community or derived:** `<case_dir>/.library.json`, next to `.owners.json`.
- **curated:** `<data_dir>/library/<case_id>.json`. Write this only when a steward unlists or republishes; absence means published.

```python
STATUSES = ("private", "submitted", "published", "returned", "rejected", "unlisted")
LICENCES = ("CC-BY-4.0", "CC-BY-SA-4.0", "CC0-1.0", "PRACTICE-ONLY")
CONSENT_SCOPES = ("public_practice",)
PUBLIC_STATUSES = {"published"}
HISTORY_MAX = 50

class HistoryEntry(BaseModel): at: str; actor: Literal["creator","steward","system"]; action: str; note: Optional[str] = None

class LibraryRecord(BaseModel):
    case_id: str
    status: str = "private"
    collection: Literal["curated", "community"] = "community"
    credit_name: Optional[str] = None
    licence: Optional[str] = None
    consent_scope: str = "public_practice"
    rights_confirmed: bool = False
    rights_confirmed_at: Optional[str] = None
    people_visible: bool = False
    people_consented: bool = False
    submitted_at: Optional[str] = None
    decided_at: Optional[str] = None
    steward_note: Optional[str] = None
    history: List[HistoryEntry] = []
```

**Functions** (all take `settings`; write atomically: write `*.tmp`, then `os.replace`):

| Function | Behaviour |
|---|---|
| `kind_of(settings, case_id) -> Literal["curated","community","derived"]` | Curated if no `~`. Community if the dir has `knowledge/case_profile.v*.json`. Otherwise derived. |
| `load(settings, case_id, case_dir) -> LibraryRecord` | **Curated:** from the overlay, else defaults (status `published`, collection `curated`). `credit_name` and `licence` come from the primary source in `case_dir/sources.json` (or `source/sources.json`): use the existing registry loader if easy, else read the JSON and take the first source whose `used_by_system` is not false and `role` is not `held_out_reference`. Consent scope is `public_practice`. **Community or derived:** from `.library.json`, else defaults (status `private`, collection `community`). |
| `save(settings, rec, case_dir)` | Writes to the correct location. |
| `create_initial(settings, case_dir, case_id)` | Called by compose create (§3.9). Writes status `private`, `rights_confirmed=True`, `rights_confirmed_at=now` (the composer already refuses uploads without the rights checkbox) and a history entry `created`. |
| `submit(settings, case_id, case_dir, body, review_status) -> LibraryRecord` | Creator only; see the transition table. |
| `withdraw(settings, case_id, case_dir) -> LibraryRecord` | Creator only. |
| `decide(settings, case_id, case_dir, decision, note) -> LibraryRecord` | Steward only. |
| `blockers(kind, rec, review_status) -> List[str]` | Plain-language reasons (below). |

**Creator transitions** (`actor="creator"`):

| From | Action | To | Conditions (else 400 `INVALID_INPUT` with `details.blockers`) |
|---|---|---|---|
| private, returned | submit | submitted | kind == community; review_status in {approved, revised}; credit_name non-blank and ≤ 60 chars; licence in LICENCES; consent_scope in CONSENT_SCOPES; rights_confirmed true; if people_visible then people_consented |
| submitted, returned, published, rejected | withdraw | private | — |
| anything else | — | — | 409 `INVALID_INPUT`: "This skill is already <status>." |

**Steward transitions** (`actor="steward"`; a note is required for return, reject and unlist, else 400):

| Decision | From | To |
|---|---|---|
| publish | submitted | published |
| return | submitted | returned |
| reject | submitted | rejected |
| unlist | published | unlisted (curated or community) |
| republish | unlisted | published |

Any other combination is 409 `INVALID_INPUT` "Cannot <decision> a skill that is <status>." Set `decided_at` and `steward_note` (the note, or None for publish/republish), and append to history. Keep the last 50 history entries.

**`blockers()` texts** (exact):
- derived: "Uploads made from a featured skill can't be published. Share your own skill instead."
- curated: "Featured skills are managed by stewards."
- review not done: "Check what the AI understood and confirm the steps first."
- status not private or returned: "This skill has already been sent to the library."

### 3.4 Access and visibility (`access.py`)

```python
def is_owner(case_dir: Path) -> bool
    # visitors._owners(case_dir) is None -> True   (legacy dirs created before isolation, and local dev)
    # else current_visitor in owners

def can_view(settings, case_id, case_dir) -> bool
    # curated -> True
    # owner -> True
    # library status in PUBLIC_STATUSES -> True
    # current_steward.get() and status != "private" -> True
    # else False

def access_view(settings, case_id, case_dir, review_status) -> dict
    # exactly the CaseAccess shape in app/src/api/types-product.ts:
    # {owner, steward, library_status, collection, credit_name, licence,
    #  can_edit, can_submit, submit_blockers, steward_note}
    # owner        = kind != curated and is_owner(case_dir)
    # steward      = current_steward.get()
    # can_edit     = owner or steward
    # submit_blockers = blockers(...) if owner else []
    # can_submit   = owner and not submit_blockers
```

**Wire it in:**
1. `paths.case_dir`: replace the current isolation check (`if "~" in case_id and settings.isolate_visitors and not visible(d)`) with `if "~" in case_id and settings.isolate_visitors and not access.can_view(settings, case_id, d)`. Import inside the function to avoid a circular import.
2. `routes/cases.list_cases`:
   - keep the existing behaviour when `isolate_visitors` is false;
   - otherwise filter with `can_view`;
   - additionally drop curated cases whose status is `unlisted` unless the request is a steward request;
   - then add `"access": access_view(...)` to every summary, using the summary's `review_status`.
3. `routes/cases.get_case`: after `to_view()`, add `view["access"] = access_view(settings, case_id, cdir, view.get("review_status", "pending"))`. If `to_view()` returns a non-dict (fakes), leave it unchanged.
4. `routes/cases.review_case`:
   - **community or derived case:** allowed for the owner or a steward; otherwise 403 `NOT_OWNER` "Only the creator or a steward can change these steps." Today any visitor who can see a case can review it. Now that published skills are visible to everyone, this check is required.
   - **curated case:** keep the existing token and open checks, and also allow a steward request.

### 3.5 Insights (`insights.py`)

**Event log.** Path: `<data_dir>/insights/<case_id>.jsonl`. Add `"insights"` and `"library"` to **neither** `SWEPT` nor any deletion path.

```python
def record_attempt(settings, case_id: str, session_id: str, result: dict, rubric_names: Dict[str, str], max_score: Optional[float], source: str = "learner") -> None
def record_completion(settings, case_id: str, session_id: str, session_result: dict) -> None
def compute(settings, case_id: str) -> dict          # InsightsView shape
def activity(settings, case_id: str) -> dict         # {"learners": int, "attempts": int, "last_activity": Optional[str]}
def today_totals(settings) -> dict                   # {"learners_today": int, "attempts_today": int} across all logs (UTC day)
```

**Attempt event** (one JSON object per line; never names, never media):

```json
{"v": 1, "at": "2026-10-08T10:00:00+00:00", "kind": "attempt",
 "s": "<sha256(session_id)[:12]>", "n": 1, "type": "baseline",
 "score": 3.0, "max": 5.0, "passed": false,
 "criteria": {"CRIT-1": {"name": "Stroke continuity", "status": "not_satisfied"}},
 "first": {"criterion_id": "CRIT-1", "name": "Stroke continuity"},
 "runtime": "RECORDED_LIVE", "source": "learner"}
```

- `type`: `result["attempt"]["attempt_type"]` ("baseline" or "retry").
- `n`: `result["attempt"]["attempt_number"]`.
- `score`: `result["evaluation"]["total_score"]`.
- `passed`: `result["evaluation"]["passed"]`.
- `criteria`: from `result["evaluation"]["criterion_results"]` (`criterion_id`, `status`). The name comes from `rubric_names`, else the first-divergence name when the ids match, else the id.
- `first`: from `result["first_divergence"]` (may be null).

**Completion event:**

```json
{"v": 1, "at": "...", "kind": "complete", "s": "<hash>",
 "gain": <comparison.skill_gain_excluding_observability>,
 "targeted": {"criterion_id": "...", "improved": true}}
```

`targeted` comes from `comparison.targeted_change` (`criterion_id` and `improved`), or null.

**Appending and caps:**
- Append under a module-level `threading.Lock`.
- When the file exceeds `insights_max_events + 1000` lines, rewrite it keeping the last `insights_max_events`.
- **Must never raise into the request.** Wrap each `record_*` in `try/except Exception` and log at warning level, without the event content. A failed insight must not fail an attempt.

**`compute()` (deterministic):**
- `attempts`: number of attempt events.
- `learners`: distinct `s` over all events.
- `completed`: distinct `s` with a complete event.
- `since`: the earliest `at`, or None.
- `baseline` and `retry`: over attempt events of that type:
  - `count`;
  - `pass_rate` = mean(passed), or None when count is 0;
  - `avg_pct` = mean(score/max) over events with max > 0, or None.
- `first_wrong`: over baseline events whose `first` is not null, count by criterion_id. `share` = count / that total. Sort by count desc, then name asc. Keep the top 5.
- `hardest`: over baseline events, per criterion. `miss_rate` = share of events whose status != "satisfied"; `n` = events containing the criterion. Keep `n ≥ 1`. Sort by miss_rate desc, then name asc. Keep the top 5.
- `feedback_helped`:
  - `sessions` = complete events with targeted not null;
  - `improved` = those with improved true;
  - `rate` = improved/sessions, or None.
- `enough_data` = learners ≥ 3.
- `suggestions`: apply these rules in order (constants at module top); each text is exact, with values formatted as integers with `%`:

| Rule | Condition | Text |
|---|---|---|
| R1 | the top `hardest` item has n ≥ 3 and miss_rate ≥ 0.5 | `About {pct}% of learners miss “{name}” on their first try. Consider showing this step more slowly or describing it more clearly.` |
| R2 | the top `first_wrong` item has count ≥ 3 and share ≥ 0.4 | `Most learners first go wrong at “{name}”. Make sure the source shows this moment clearly.` |
| R3 | feedback_helped.sessions ≥ 3 and rate < 0.3 | `Second tries rarely improve the check the feedback focuses on. The advice for it may need clearer wording.` (criterion_id null) |
| R4 | learners ≥ 5 and baseline.pass_rate ≥ 0.8 | `Most learners pass on their first try. Consider a harder variation.` (criterion_id null) |

Each suggestion is `{"criterion_id": ..., "text": ..., "rule": "R1"}`.

**Hook in `routes/sessions.py`:**
- In `submit_attempt`, after `api.save_session(...)` and still inside the lock, call `insights.record_attempt(...)` with:
  - `case_id = getattr(session, "case_id", None)` (skip when None);
  - `session_id`;
  - `result_json = adapters.to_json(result)` (compute it once and return the same object);
  - rubric names and max score computed defensively:

```python
def _rubric_facts(session):
    try:
        crit = session.handoff().rubric.criteria
        return {c.criterion_id: c.name for c in crit}, float(sum(c.weight for c in crit))
    except Exception:
        return {}, None
```

- In `complete_session`, after saving, call `record_completion` with `adapters.to_json(result)`.
- Also call `metrics.inc("attempts_day", today)` from §3.6 in `submit_attempt`.

### 3.6 Usage metrics (`metrics.py`)

```python
class Metrics:
    started_at: str (UTC ISO at import)
    def inc(self, group: str, key: str, n: int = 1) -> None   # thread-safe
    def get(self, group: str) -> Dict[str, int]                # copy
METRICS = Metrics()
```

**Groups and hooks:**

| Group | Hook |
|---|---|
| `requests` (key = route class) | `RateLimitMiddleware.__call__`, whenever `route_class(...)` returns a class. Count it **even when that class has no bucket**: move the `route_class` call so the counting happens before the bucket check. **When rate limiting is off**, `main.py` does not install the middleware, so also add a tiny `RouteCountMiddleware` in `metrics.py` and install it when `settings.rate_limits` is empty. Never install both, or requests are counted twice. |
| `rate_limited` (key = route class) | When a 429 is returned. |
| `errors` (key = category) | In `errors.error_response`, before building the response, call `METRICS.inc("errors", category)`. Import inside the function to avoid a circular import. |
| `attempts_day` (key = UTC date) | `submit_attempt` success. |
| `compose_day` (key = UTC date) | `compose.analyze_upload` success. |

### 3.7 Steward routes (`routes/steward.py`)

Every route depends on `require_steward`; router prefix `/api/steward`.

| Method and path | Response |
|---|---|
| `POST /check` | `{"ok": true}`. It is just the dependency; the rate limit class is `auth` (add `("POST", re.compile(r"^/api/steward/check$"), "auth")` to `limits._ROUTES` and `"auth": "Too many sign-in attempts. Please wait a little."` to `_MESSAGES`). |
| `GET /overview` | `StewardOverview` (below) |
| `GET /queue` | `StewardQueueItem[]` |
| `GET /library` | `StewardLibraryRow[]` |
| `POST /library/{case_id}/decide` | Body `{"decision": str, "note": Optional[str]}` (Pydantic, `extra="forbid"`, note ≤ 500). Calls `library.decide` under `adapters.resource_lock("case", case_id)`. Returns the `LibraryRecord` (`model_dump`). 404 if the case does not exist; `case_dir()` already raises it. |
| `GET /consent` | `ConsentRow[]` |
| `GET /consent/export` | The same rows wrapped as `{"exported_at": iso, "skills": rows}`, returned as `Response(json, media_type="application/json", headers={"Content-Disposition": 'attachment; filename="anveshan-consent-<YYYYMMDD>.json"'})` |
| `GET /usage` | `UsageView` |
| `GET /review-export/{case_id}` | `{"case_id", "exported_at", "review_status", "knowledge_package": <the case view's "package">, "expert_review": package.expert_review}` as an attachment named `anveshan-review-<case_id>-<YYYYMMDD>.json`. Get the view via `adapters.track_a().load_case(cdir).to_view()` inside `adapters.translated()`. |

**Building the lists:**
1. Call `adapters.track_a().list_cases(settings.cases_root, settings.data_dir)` and keep summaries whose `modality` is not None.
2. For each, resolve its dir: curated → `settings.cases_root/<id>`, else `settings.data_dir/"cases"/<id>`.
3. Load its library record.
4. **Never include a community or derived skill whose status is `private`.**

**Item shapes** (exactly as in `types-product.ts`):

- **queue:**
  - submissions: status == submitted, `kind: "submission"`;
  - featured: curated with status published and `review_status` not in {approved, revised}, `kind: "curated_unchecked"`.
  - `steps` = `len(view["package"]["claims"])` when cheap. Load the view lazily only for queue items; on any error use 0.
  - Order: submissions oldest `submitted_at` first, then curated by title.
- **library rows:** `learners`, `attempts` and `last_activity` come from `insights.activity()`.
- **overview:**
  - `library_skills` = count with status published;
  - `waiting_review` = count of submissions;
  - `learners_today` and `attempts_today` from `insights.today_totals`;
  - `live_calls_today` = `DAILY_BUDGET.used` if `DAILY_BUDGET._day` is today, else 0;
  - `daily_budget` = `DailyBudget.limit()`;
  - `storage_bytes`: from `housekeeping._size(settings.data_dir)`, cached for 30 s in a module global;
  - `storage_cap_bytes` = `int(settings.data_cap_mb * 1024 * 1024)`;
  - `ephemeral: true`.
  - `attention`, in this order:
    - `submissions_waiting` when > 0: "{n} shared skill(s) waiting for review" (singular "skill is", plural "skills are");
    - one `curated_unchecked` per unchecked featured skill: "“{title}” has not been checked by an expert yet";
    - `budget_high` when the budget is > 0 and used/limit ≥ 0.8: "{pct}% of today's AI budget is used";
    - `storage_high` when the cap is > 0 and storage/cap ≥ 0.8: "Storage is {pct}% full; old private data will be removed soon".
- **consent rows:**
  - `sources` = the public sources from the case view's `sources` (each `source_id`, `attribution`, `license` and `url` or null);
  - wrap the view load per case in try/except, using an empty list on failure.
- **usage:**
  - `started_at` and `uptime_s` from METRICS;
  - `mode` = settings.mode;
  - live calls and budget as in the overview;
  - `own_key_calls` and `cache_hits` from `USAGE` (§3.8);
  - `requests_by_class`, `rate_limited` and `errors_by_category` from METRICS;
  - `attempts_today` and `compose_today` from METRICS (today's key);
  - storage;
  - `data_ttl_hours` = settings.data_ttl_hours.

### 3.8 Usage counters in the model gateway (`tracks/common/models.py`, minimal)

Add after `DAILY_BUDGET = DailyBudget()`:

```python
class UsageCounters:
    """Process-wide counts for the steward usage view (never affects behaviour)."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.cache_hits = 0
        self.own_key_calls = 0
        self.live_calls = 0
    def inc(self, name: str) -> None:
        with self._lock:
            setattr(self, name, getattr(self, name) + 1)

USAGE = UsageCounters()
```

**Increment points:**
- At both places where `"live_cache_hit"` is appended to notes: `USAGE.inc("cache_hits")`. In `embed`, only inside the `if self.mode == "live":` branch.
- At both places with `if not self.own_key: DAILY_BUDGET.take()`, change to:

```python
        if not self.own_key:
            DAILY_BUDGET.take()
            USAGE.inc("live_calls")
        else:
            USAGE.inc("own_key_calls")
```

### 3.9 Compose create (`routes/compose.py`)

In `create_case`, right after `add_owner(case_dir)`, call `library.create_initial(settings, case_dir, case_dir.name)`. In `analyze_upload`, after success, call `METRICS.inc("compose_day", <UTC date>)`.

### 3.10 Track A list fix (`tracks/track-a/src/track_a/api.py`, `_summary_composed` only)

Today it always returns `review_status: "pending"`, so a creator's "Looks right" never shows in lists. After reading the profile, compute the real status:

```python
    version, _ = select_package_version(case_dir)
    if version is not None:
        pkg = load_versioned(authoring.artifact_dir(case_dir, "knowledge_package"), "knowledge_package", KnowledgePackage, version)
        review_status = _status(pkg)
```

Wrap it in `try/except Exception: pass`, like the profile read. Run the track-a tests afterwards.

### 3.11 Housekeeping (`housekeeping.py`)

Entries under `cases/` whose `.library.json` status is not `private` (submitted, published, returned, rejected, unlisted) are **protected**: skip them in both the TTL pass and the cap pass. Implement a helper `_protected(p: Path) -> bool` that reads `p/".library.json"` safely (False on any error) and filter entries before both passes. Add a test.

### 3.12 Health (`routes/health.py`)

Add these keys:
- `"steward_enabled": settings.steward_enabled`;
- `"steward_open": settings.steward_open`;
- `"data_ttl_hours": settings.data_ttl_hours`.

Update the health-shape test in `service/tests/test_service_cases.py` if it compares an exact key set.

### 3.13 Library and insights routes

**`routes/library.py`** (prefix `/api/library`):

| Route | Access |
|---|---|
| `GET /{case_id}` | `case_dir()` (visibility), then owner or steward. Others get 404 `MISSING_EVIDENCE` "unknown case", so private records do not leak. Returns `LibraryRecord.model_dump()`. |
| `POST /{case_id}/submit` | Owner only (403 `NOT_OWNER` "Only the creator can publish this skill."). The body is a Pydantic model mirroring `SubmitBody` (`extra="forbid"`; `credit_name` ≤ 60, `note` ≤ 500). Get `review_status` from `track_a.load_case(cdir).to_view()["review_status"]` inside `translated()`; use "pending" if the view is not a dict. Runs under `resource_lock("case", id)`. |
| `POST /{case_id}/withdraw` | Owner only. |

Add to the rate-limit table: `("POST", re.compile(r"^/api/library/[^/]+/(submit|withdraw)$"), "compose_step")`.

**`routes/insights.py`:** `GET /api/insights/{case_id}` resolves `case_dir()`, then allows the owner (community or derived) or a steward; otherwise 403 `NOT_OWNER` "Only the creator or a steward can see how learners are doing." Returns `insights.compute(...)`.

### 3.14 Offline expert review tool (`tools/apply_expert_review.py`)

```text
usage: apply_expert_review.py <case_id> <review.json> [--cases-root tracks/cases] [--dry-run]
```

- `review.json` is either:
  - the file downloaded from `GET /api/steward/review-export/{case_id}`: take `knowledge_package.expert_review` and the claims;
  - or a hand-written list: `{"reviewer": "Name", "actions": [{"action": "revise_claim", "claim_id": "...", "new_statement": "..."}, {"action": "approve", "note": "..."}]}`.
- For the export form:
  1. diff the exported claims against the current package and emit a `revise_claim` for each changed statement and a `reject_claim` for each claim missing from the export;
  2. then emit `approve` when the export's `review_status` is approved (or revised with no remaining changes), with `reviewer` = `expert_review.reviewer_name`.
- Apply each action in order with `track_a.api.apply_review(case_dir, action)`. Add `tracks/track-a/src` and the repo root to `sys.path`, as other `tools/*.py` do.
- Print each new package version.
- `--dry-run` prints the actions only.
- Afterwards tell the user to run `.github/scripts/check_case_packs.py` and commit.
- **Test:** `service/tests/test_k9_steward.py::test_apply_expert_review_dry_run` with a fake `track_a.api` module (monkeypatch `sys.modules`) that records the actions.

### 3.15 Docs

Add `## 7. Product roles (K9)` to `docs/plans/service-api.md`:
- one table listing every new endpoint, its auth (public, owner, steward) and its response type name, pointing to `app/src/api/types-product.ts`;
- the settings and env vars: `ANVESHAN_STEWARD_TOKEN`, `ANVESHAN_STEWARD_OPEN`, `ANVESHAN_INSIGHTS_MAX_EVENTS`, `ANVESHAN_RATE_AUTH_PER_HOUR`;
- the file locations: `.library.json`, `data_dir/library/`, `data_dir/insights/`.

Add one row each for the new env vars to `docs/deploy/DEPLOY-CHECKLIST.md`'s env table, if one exists. Set `ANVESHAN_STEWARD_TOKEN` as a Cloud Run secret; never put it in the Dockerfile.

## 4. JSON shapes

The UI mirror is `app/src/api/types-product.ts`, created in Phase 0. Open that file and match every field name and type. Summary:

| Endpoint | Shape |
|---|---|
| `access` on case summaries and views | `CaseAccess` |
| `GET /api/library/{id}`, submit, withdraw, decide | `LibraryRecord` |
| `GET /api/insights/{id}` | `InsightsView` |
| `/api/steward/overview` | `StewardOverview` |
| `/api/steward/queue` | `StewardQueueItem[]` |
| `/api/steward/library` | `StewardLibraryRow[]` |
| `/api/steward/consent` | `ConsentRow[]` |
| `/api/steward/usage` | `UsageView` |

Error categories added (HTTP status):
- `STEWARD_DISABLED` (403);
- `STEWARD_REQUIRED` (401);
- `NOT_OWNER` (403).

All are raised with `ServiceError(status, category, message)`.

## 5. Tests (write them; all must pass with `-m "not live"`)

Use `_settings(tmp_path, **kw)` and `_fake_track_a(monkeypatch, cases)` patterns from `test_public_demo.py`.
- Create community case dirs under `tmp_path/"data"/"cases"/"my-skill~aabbccddeeff"`, with an empty `knowledge/case_profile.v1.json` so `kind_of` returns community.
- Two visitors are two `TestClient`s with different `anv_vid` cookies (see the existing isolation tests).
- Use `TestClient(create_app(settings), headers={"X-Steward-Token": "s3cret"})` for steward requests, with `steward_token="s3cret"`, `steward_open=False`.

`test_k9_library.py`:
1. A new community case: `access.owner` is true for its creator, `library_status` "private", `can_submit` false with the blocker "Check what the AI understood…" (the fake view returns `review_status` "pending").
2. Submit with review approved (make the fake `load_case(...).to_view()` return `{"case_id": cid, "review_status": "approved"}`) → status submitted, history has `submitted`, and `rights_confirmed_at` is set.
3. Submit errors:
   - a missing credit gives 400 with `details.blockers`;
   - `people_visible` without consent gives 400;
   - a bad licence gives 422 (Pydantic) or 400; assert ≥ 400;
   - a second visitor submitting gives 404 while private, because `case_dir` hides it.
4. Withdraw: submitted → private, and withdraw again → 409.
5. Visibility:
   - a private skill is invisible to visitor B (list and GET 404);
   - a published skill is visible to B (list and GET 200) with `access.owner` false;
   - a submitted skill is visible to a steward but not to B.
6. A curated case list item has `access.collection` "curated" and status "published".
7. Review gating: visitor B gets 403 `NOT_OWNER` when reviewing a published community skill; the owner gets 200.
8. Housekeeping protects a published case dir from TTL removal and still removes an old private one.

`test_k9_steward.py`:
1. Steward disabled (no token, not open): `/api/steward/overview` gives 403 `STEWARD_DISABLED`.
2. Wrong or missing token: 401 `STEWARD_REQUIRED`; the response body never contains the token value.
3. With `rate_limits={"auth": 2}`, the third `/api/steward/check` gives 429.
4. Queue lists a submitted community skill and an unchecked curated one; never a private one; never a synthetic showcase (modality None).
5. Decide:
   - publish → published;
   - return without a note → 400;
   - return with a note → returned, and the creator's `access.steward_note` equals the note;
   - unlist on curated "kolam" → the list for a normal visitor no longer includes kolam, a steward still sees it, and republish restores it.
6. Consent export has a `Content-Disposition` attachment, and its JSON has `skills`.
7. Usage has every `UsageView` key; overview has every `StewardOverview` key.
8. `test_apply_expert_review_dry_run` (§3.14).

`test_k9_insights.py`:
1. `compute()` on no events gives zeros, None rates, `enough_data` false, and empty suggestions.
2. Write synthetic events directly with `record_attempt`/`record_completion` for 5 sessions (a baseline for each, retries for 4, completions for 4). Check:
   - learners = 5;
   - baseline count and pass rate;
   - `first_wrong` order and shares;
   - `hardest` miss rates;
   - `feedback_helped`;
   - R1 and R2 fire with the exact texts.
3. The event file never contains the learner name or the raw session id. Pass a result whose attempt `learner.name` is "Alice"; the file text must not contain "Alice" or the session id.
4. `record_attempt` with a malformed result does not raise.
5. Cap: with `insights_max_events=10`, writing 1,100 events keeps at most 1,010 lines after the rewrite threshold, and `compute` still works.
6. Owner and steward access to `/api/insights/{id}` (200), and another visitor gets 403/404.
7. End to end through the fake Track B: start a session, submit 2 attempts and complete. The insights file for the case then has 2 attempt events and 1 complete event. The `FakeResult` payload in `conftest.py` may lack fields; make `record_attempt` tolerate missing keys, and extend the fake payload minimally if needed.

## 6. Acceptance (P1 is done when)

- All new tests pass.
- The full suite passes: `<py> -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"`.
- `check_governance.py`, `check_case_packs.py` and `check_contract_parity.py` pass.
- `docs/plans/service-api.md` §7 is written.
- A manual smoke test against the real service locally works:
  1. start it with `<py> -m uvicorn anveshan_service.main:app --app-dir service --port 8080`;
  2. `curl --ssl-no-revoke http://localhost:8080/api/health` shows the `steward_*` keys;
  3. `GET /api/cases` items have `access`;
  4. `POST /api/steward/check` returns ok (local is open by default).
- Report `docs/kiro/reports/K9-P1-REPORT.md` (≤ 60 lines): done, tests (counts), deviations, notes for PC.

## 7. Pitfalls (read before coding)

- `paths.case_dir` is used by every route, including media. A visibility bug there breaks sessions and media for published skills. Test the media route for a published community skill.
- **Circular imports:**
  - `paths.py` imports `visitors`;
  - `access.py` imports `library`, `visitors` and `steward`;
  - import `access` inside the function in `paths.py`.
- **ContextVars and threads:** FastAPI runs sync endpoints in a threadpool. ContextVars set in ASGI middleware do propagate (the existing `current_visitor` and `current_key` rely on this). Do the same.
- **Atomic writes:** two requests may submit or decide at once. Always hold `adapters.resource_lock("case", case_id)` around read-modify-write of a library record.
- **No silent failures,** with one exception: insights recording is deliberately best-effort. Log a warning (without content) and continue.
- **Windows:** use `Path` everywhere and `encoding="utf-8"` on every open.
- **Fakes may return summaries whose directories do not exist** (`test_public_demo.py` builds lists in memory). `access_view`, `load` and `can_view` must tolerate a missing directory and fall back to defaults: curated → published; `~` ids → private, not owner. The existing public-demo tests must keep passing unchanged.

## 8. Order of work

1. Settings, steward identity and middleware, and health; tests 1–3 of steward.
2. `library.py` and `access.py`; wire `paths`, `cases` and `compose`; library tests 1–7.
3. Library routes; submit, withdraw and decide tests.
4. Housekeeping protection, with its test.
5. `metrics.py`, `USAGE` counters and hooks.
6. `insights.py`, the sessions hooks and the insights routes; insights tests.
7. Steward routes (overview, queue, library, consent and export, usage, review-export); remaining steward tests.
8. The Track A `_summary_composed` fix and the track-a tests.
9. `tools/apply_expert_review.py`, with its test.
10. Docs (`service-api.md` §7, deploy checklist rows), the full verification and the report.

## 9. Commit plan

Commit at the end of each step in §8, with messages such as `feat(service): steward identity and health flags (K9-P1 step 1)`.
