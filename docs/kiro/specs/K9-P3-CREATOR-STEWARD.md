# K9-P3 — Creator and steward surfaces, navigation, composer wording

Read `00-COMMON.md`, then **`K9-00-PRODUCT-UX.md` in full** (sections 3, 4, 5 and 6.5–6.8 are your brief), then this file.

Your folder and branch are in `K9-ORCHESTRATOR.md` §2. Phase 0 is applied in your branch:
- `api/types-product.ts` (all view types);
- the client methods: `getLibraryRecord`, `submitToLibrary`, `withdrawFromLibrary`, `getInsights`, `stewardCheck`, `stewardOverview`, `stewardQueue`, `stewardLibrary`, `stewardDecide`, `stewardConsent`, `stewardUsage`, `stewardConsentExport`, `stewardReviewExport`;
- a working SYNTHETIC mock of all of them (`api/mock/library.ts`; mock steward code: `steward`);
- `api/steward.ts` (token store);
- `copy/plain.ts`;
- `api/debug.ts`;
- `AppView` now includes `'mine' | 'steward'`;
- the `ownerSlot` prop on both Learn views and `onOpenMine` on `DiscoveryView`.

**Build against the mock first** (`npm --prefix app run dev:mock`, port 5174). The real backend comes from P1 and meets you at integration (PC).

---

## 0. Ground rules

- You own:
  - `app/src/App.tsx`;
  - `app/src/components/Header.tsx`;
  - `app/src/components/composer/**`;
  - new `app/src/components/creator/**`, `app/src/components/steward/**` and `app/src/components/insights/**`;
  - `app/src/api/mock/library.ts` (you may enrich the mock; keep its exported function names).
- You must **not** edit:
  - `app/src/hero/**` and `app/src/components/DiscoveryView.tsx` / `HowItWorks.tsx` (P2);
  - `app/src/api/client.ts`, `api/types*.ts` and `api/mock.ts` (Phase 0 froze them);
  - `app/src/vite-env.d.ts`;
  - anything outside `app/`.

  If you need a change there, put it under "Requests for PC" in your report and work around it.
- You may import P2's components only by their existing names (`ReviewBadge`, `Badge`, `Panel`, `btn`, `ErrorNote`, `Spinner`, `ProgressBar` from `hero/ui.tsx`; `SourcePanel` from `hero/SourcePanels.tsx`). Do not rely on new P2 files (`TrustLine`, `StepsList`, `WhyThisFeedback`); they don't exist in your branch.
- Icons: only those declared in `vite-env.d.ts`. Phase 0 added Lightbulb, Users, BarChart3, Inbox, Library, FileDown, LogOut, Trash2, BookOpen, Share2, Gauge, HardDrive, ListChecks, Hourglass and Globe.
- Follow K9-00 §3 for every screen: one primary action, a one-sentence purpose, empty states, accessible dialogs, ≥ 11 px text, and a working layout at 375 px.
- Every API call uses `api.*` from `app/src/api/client.ts` and renders errors with `ErrorNote`. No silent catches.
- Commit after each numbered section: `feat(ui): … (K9-P3 §n)`.

## 1. Navigation (`App.tsx`, `Header.tsx`)

### 1.1 Views and URL

1. `readUrl()` accepts the views `'discovery' | 'source' | 'practice' | 'transmission' | 'composer' | 'mine' | 'steward'`.
2. **Case selection keys.** Today `CaseKey` (from `DiscoveryView`) is `hero | showcase | composer`. Keep it. For `mine` and `steward`, keep the current `selected` value and switch `currentView` only. The `case` URL param stays as is.
3. The URL effect writes `view`. For `mine` and `steward`, do not write `case`; delete it from the params.
4. **Scroll to top** on view change (exists).

### 1.2 Header (rewrite the layout; keep the props that still make sense)

**Left:**
- "Anveshan" wordmark button. Click → `onSelectView('discovery')`.
- Then primary nav buttons:
  - **Library** (active on `discovery`);
  - **My skills** (active on `mine`). Show a count badge when `ownedCount > 0`, using the new prop `ownedCount?: number`;
  - **Steward**: visible only when a steward token is present (`getStewardToken()`, subscribe with `subscribeStewardToken`) or `health.steward_open` is true. Active on `steward`.

**Right:** keep "How it works" and the AI key button (exist).

**Second row, only when inside a skill** (`currentView` is `source`, `practice` or `transmission` and `selected.kind !== 'composer'`):
- a breadcrumb "Library › {skill title}". Clicking "Library" goes to discovery; the title is plain text with `data-plain-exempt`.
- the existing stepper (1 Learn · 2 Practise · 3 Results with done/locked/hint).

**Case `<select>`:** render it only when `DEBUG` is true. Today it is always visible.

**Runtime chip, Settings and "Design ref":** keep today's `showRuntime` / `DEBUG` gating unchanged.

**New props to add:**
- `ownedCount?: number`;
- `stewardVisible?: boolean`;
- `skillTitle?: string | null` (for the breadcrumb).

App computes:
- `skillTitle`: from `caseView?.title` when `selected.kind === 'hero'`; from `capCase.title` for showcase;
- `ownedCount`: `heroCases?.filter(c => c.access?.owner).length ?? 0`.

**Mobile (< 640 px):**
- the nav collapses to icon + label buttons in one row (Library, My skills, Steward), with labels kept, `text-xs`;
- the breadcrumb truncates the title with `truncate`.

### 1.3 Footer (`App.tsx`)

- Learner text "Scores come from fixed rules, never from the AI" stays.
- The "VIEW PROVENANCE DAG" button (showcase) only when `DEBUG`.
- Add a link-button "Steward sign-in" that goes to `?view=steward`. Hide it when already on the steward view. Hide it when `health.steward_enabled === false`.
- "ANVESHAN PROTOTYPE | GOOGLE CLOUD AI BUILDER CUP 2026" stays.

### 1.4 Wiring

- `DiscoveryView`: pass `onOpenMine={() => setCurrentView('mine')}`.
- `HeroSourceView`: pass `ownerSlot={caseView?.access?.owner ? <CreatorPanel … /> : null}` (§2.2). `HeroSourceView` forwards the props to `UniversalSourceView`, so this covers composed skills too.
- **`currentView === 'mine'`:**

  ```tsx
  <MySkillsView
    cases={heroCases}
    loading={heroLoading}
    error={heroError}
    health={health}
    onRefresh={loadCases}
    onOpen={(id) => select({kind:'hero', id}, 'source')}
    onCreate={() => select({kind:'composer'})}
  />
  ```

- **`currentView === 'steward'`:**

  ```tsx
  <StewardConsole
    health={health}
    onOpenSkill={(id) => select({kind:'hero', id}, 'source')}
    onLibraryChanged={loadCases}
  />
  ```

- After any creator action that changes a case (`onViewChange` from `CreatorPanel`), call `setCaseView(nv)` and `void loadCases()`, exactly like `HeroSourceView`'s `onViewChange` does today.
- **Composer heading:** the mono label "Composer — Create a new skill" → `<h1 className="font-serif text-2xl">Share a skill you know</h1>`, plus one sentence: "Upload a photo, video or audio of something you know how to do. Anveshan proposes a practice task; you check it before anyone else sees it."

## 2. Creator

### 2.1 `components/creator/MySkillsView.tsx`

Props:

```ts
{ cases: CaseSummary[] | null; loading: boolean; error: unknown; health: HealthResponse | null;
  onRefresh: () => void; onOpen: (caseId: string) => void; onCreate: () => void }
```

Layout (K9-00 §6.5):
- **Header row:** `h1` "My skills" (`font-serif text-3xl`) + primary button "Share a new skill" (`Share2` icon) → `onCreate`.
- **Explanation paragraph:** "Skills you create are private to this browser until you publish them." When `health?.data_ttl_hours > 0`, append " Private skills are kept for about {h} hours on this demo."
- **Owned skills:** `cases.filter(c => c.access?.owner)`. Composed skills first, then hero-derived uploads (`c.derived_from`) under a sub-heading "Your uploads of featured skills". For those uploads, the card shows the status "Private" and the help line "Uploads made from a featured skill stay private."
- **Card** (`SkillStatusCard`, in the same file):
  - title (`data-plain-exempt`);
  - a status chip (`LIBRARY_STATUS_LABEL[access.library_status]`), with tones: private muted, submitted amber, published emerald, returned amber, rejected crimson, unlisted muted;
  - the help line `LIBRARY_STATUS_HELP[...]`;
  - the steward note (`access.steward_note`) in a quote box when present;
  - `ReviewBadge status={c.review_status} own` (P2 adds the `own` prop; in your branch it does not exist yet, so pass only `status` and add the `own` prop in PC);
  - the next-action button by status:

| Status | Button | Action |
|---|---|---|
| private | "Open and check" | `onOpen(id)` |
| submitted | "Open" | `onOpen(id)` |
| returned | "Fix and send again" | `onOpen(id)` |
| published | "See how learners are doing" | opens `InsightsDialog` for the case |
| rejected or unlisted | "Open" | `onOpen(id)` |

- **Empty state:** the K9-00 §6.5 text plus the "Share a new skill" button.
- **Loading:** `Spinner` with "Loading your skills…". **Error:** `ErrorNote` plus a "Try again" button.

### 2.2 `components/creator/CreatorPanel.tsx` (the `ownerSlot`)

Props:

```ts
{ view: CaseView; onViewChange: (v: CaseView) => void; onPractise: () => void }
```

App passes `onPractise={() => setCurrentView('practice')}`.

- A `Panel` with kicker "Your skill", title = status chip + `LIBRARY_STATUS_LABEL`, and the help line under it.
- **Checklist** (K9-00 §6.6), each row with an icon (`CheckCircle2` emerald when done, else a hollow circle `div`):
  1. **"Check what the AI understood"**: done when `view.review_status` is approved or revised. Button "Check steps" (or "Review again" when done) opens `CheckStepsDialog`.
  2. **"Try it yourself (optional)"**: button "Practise" → `onPractise`.
  3. **"Publish to the library"**:
     - done when the status is submitted or published;
     - the button "Publish…" opens `PublishDialog` and is disabled with the `submit_blockers` list shown under it when `!view.access?.can_submit`;
     - for status returned, the button reads "Fix and send again".
- **Status-specific actions under the checklist:**

| Status | Actions |
|---|---|
| submitted | secondary "Withdraw" (confirm: "Withdraw from review? It becomes private again.") → `api.withdrawFromLibrary`, then reload the case (`api.getCase(view.case_id)` → `onViewChange`) |
| published | primary "See how learners are doing" → `InsightsDialog`; secondary "Make private" (confirm: "Remove it from the library? Learners who already started can finish.") → withdraw |
| returned or rejected | the steward note in a quote box |

- Keep the panel compact; it sits above "What you'll learn".

### 2.3 `components/creator/CheckStepsDialog.tsx`

Props:

```ts
{ view: CaseView; isOpen: boolean; onClose: () => void; onViewChange: (v: CaseView) => void }
```

- Accessible dialog (copy the structure of `components/ApiKeyModal.tsx`: overlay, `role="dialog"`, `aria-modal`, `aria-labelledby`, a labelled Close button, `useEscape`).
- Title "Check what the AI understood". Intro text exactly as K9-00 §6.6.
- **List `view.package.claims` in order.** Each row:
  - number;
  - statement (`data-plain-exempt`);
  - "AI's reading" badge when not observed (`claim.is_observed === false`; also use `claimVerification` from `hero/locators.ts` if available);
  - buttons "Edit" (`Pencil`) and "Remove" (`Trash2`), each with an `aria-label` naming the step number.
- **Edit:** turns the row into a textarea (prefilled) with "Save" / "Cancel". Save calls:

  ```ts
  api.reviewCase(view.case_id, { action: 'revise_claim', reviewer: 'creator', note: '', claim_id, new_statement })
  ```

  then `onViewChange(updated)`. Empty text cannot be saved.
- **Remove:** inline confirm ("Remove this step? Learners will no longer be checked on it." with "Remove" / "Keep"), then `reject_claim`.
- **Footer:** primary "Looks right" calls `api.reviewCase(view.case_id, { action: 'approve', reviewer: 'creator', note: '' })`, then `onViewChange` and closes. Secondary "Close". The text above the footer: "You can change these later. Each change creates a new version; learners always practise the latest one."
- **Busy states:** disable the buttons and show "Saving…". **Errors:** `ErrorNote` inside the dialog.

### 2.4 `components/creator/PublishDialog.tsx`

Props:

```ts
{ view: CaseView; isOpen: boolean; onClose: () => void; onSubmitted: (rec: LibraryRecord) => void }
```

The fields are exactly K9-00 §6.6:

| Field | Behaviour |
|---|---|
| "Credit (shown to learners)" | Text, required, max 60, `autoComplete="name"`. Prefill from `view.access?.credit_name ?? ''`. |
| "Licence" | A radio group over `LICENCE_OPTIONS`; the label is bold, the help muted. Default `CC-BY-4.0`. Use a `fieldset` and `legend`. |
| "Who can practise it" | Static text "Anyone using Anveshan, once a steward publishes it." |
| "Are other people identifiable in your photo, video or audio?" | Radio No/Yes (default No). On Yes, show the required checkbox "They agreed to it being shared for practice." |
| Rights | Checkbox "I created this or have the right to share it.", required |
| "Note to the steward (optional)" | Textarea, max 500 |

- Primary "Send for review" (`Send` icon), disabled until the required fields are valid. On click, call `api.submitToLibrary(view.case_id, {...body, consent_scope: 'public_practice'})`, then `onSubmitted(rec)`. The caller reloads the case and closes. On a 400 with `details.blockers` (an array of strings), show them as a list above the button; otherwise `ErrorNote`.
- Under the button: "A steward checks every skill before it appears in the library. You can withdraw it at any time."

### 2.5 `components/insights/InsightsPanel.tsx` and `InsightsDialog.tsx`

**`InsightsPanel`:** `{ caseId: string; title?: string }`. It fetches `api.getInsights(caseId)` on mount and on `caseId` change. It renders K9-00 §6.7 exactly:
- **Empty** (`attempts === 0`): `Inbox` icon and the empty text.
- **Numbers row:** three stat tiles ("Learners", "Tries", "Finished both tries").
- **First vs second try:** `fmtPct(baseline.pass_rate)` → `fmtPct(retry.pass_rate)`, with `fmtPct = (r) => r == null ? '—' : `${Math.round(r*100)}%``.
- **Bars component** (local): rows of `name` (`data-plain-exempt`) + count/percent + a `div` bar with width `${Math.max(4, share*100)}%` in `bg-cadmium-amber/70`. Use it for "Where learners first go wrong" (share) and "Hardest checks" (miss_rate). Each section has its own empty line ("No first tries went off track yet.").
- **"Did the feedback help?"**: "In {improved} of {sessions} second tries, the check the feedback focused on improved." When sessions is 0: "Not enough second tries yet."
- **Suggestions:** a `Lightbulb` list, plus the footnote "Suggestions follow fixed rules from these numbers. They are not written by AI." When the list is empty: "No suggestions yet."
- When `!enough_data`, an amber note: "Fewer than 3 learners so far: treat these numbers as anecdotes."
- Always the footnote: "Counts since this demo server last started. No names or recordings are kept."

**`InsightsDialog`:** `{ caseId; title; isOpen; onClose }`. An accessible dialog wrapping `InsightsPanel` with the title "How learners are doing: {title}".

## 3. Steward console (`components/steward/`)

### 3.1 `StewardConsole.tsx`

Props:

```ts
{ health: HealthResponse | null; onOpenSkill: (caseId: string) => void; onLibraryChanged: () => void }
```

**State:**
- the token, from `getStewardToken()` and `subscribeStewardToken`;
- `signedIn` = `health?.steward_open === true || Boolean(token)`;
- `tab: 'overview' | 'queue' | 'library' | 'consent' | 'usage'`, remembered in `sessionStorage` key `anveshan.steward_tab` with try/catch;
- `reviewing: string | null` (the case_id open in the review detail).

**Gates:**

| Condition | Render |
|---|---|
| `health?.steward_enabled === false` | A card: "The steward console isn't enabled on this server." with a "Back to the library" link |
| Not signed in | `StewardSignIn` |
| Signed in | The console (below) |

**Console layout:**
- **Header:**
  - `h1` "Steward console" (`font-serif text-3xl`);
  - one sentence: "Look after the library: check skills before they are published, keep credit and consent records, and watch usage.";
  - the "Open on this local server" chip when `steward_open`;
  - "Sign out" (`LogOut` icon; clears the token, hidden when `steward_open`).
- **Banner** (amber subtle border, `Info` icon), the exact text from K9-00 §6.8.
- **Tabs:** a horizontal tab list (`role="tablist"`, buttons with `role="tab"` and `aria-selected`) that wraps on mobile:

| Tab | Icon | Extra |
|---|---|---|
| Overview | `Gauge` | — |
| Review queue | `Inbox` | count badge = `overview.waiting_review + curated unchecked count` |
| Library | `Library` | — |
| Consent & licences | `ShieldCheck` | — |
| Usage | `BarChart3` | — |

- **Tab panel:** `role="tabpanel"`.
- **401 handling:** if any steward call returns 401 (`ApiError.status === 401`), clear the token and show the sign-in with the message "Your steward session ended. Enter the code again."

### 3.2 `StewardSignIn.tsx`

- A card with the title "Steward access" and the explanation from K9-00 §6.8.
- A password input with the label "Access code" and `autoComplete="off"`.
- Primary "Sign in": `setStewardToken(code)`, then `api.stewardCheck()`.
  - Success: `onSignedIn()`.
  - 401: `clearStewardToken()` and show "That code is not right."
  - 429: show the `ErrorNote` (rate limited).
- Note under the form: "The code stays in this tab only and is sent only to this app's server."
- **Mock hint:** when `IS_MOCK`, show "Mock mode: the code is \"steward\"."

### 3.3 `OverviewTab.tsx`

- Fetch `api.stewardOverview()`.
- **KPI cards** (a grid of 2 columns on mobile, 3 on desktop). Each card: icon, label, big number, small caption.

| Card | Icon | Value and caption |
|---|---|---|
| Skills in the library | `Library` | `library_skills` |
| Waiting for review | `Inbox` | `waiting_review`; clicking switches to the queue |
| Learners today | `Users` | `learners_today` |
| Tries today | `ListChecks` | `attempts_today` |
| AI calls today | `Gauge` | `live_calls_today`; caption "of {daily_budget} allowed" or "no daily limit"; plus a `ProgressBar` when the budget > 0 |
| Storage used | `HardDrive` | `fmtBytes(storage_bytes)`; caption "of {fmtBytes(cap)}" or "no cap" |

- **"Needs your attention":** a list of `attention` items. Each item shows its text and a button:

| Item kind | Button | Action |
|---|---|---|
| submissions_waiting | "Open queue" | switch to the queue tab |
| curated_unchecked | "Review" | `setReviewing(case_id)` |
| budget_high or storage_high | — | — (text only) |

  Empty: "Nothing needs your attention right now." with a `CheckCircle2` icon.

### 3.4 `QueueTab.tsx` and `ReviewDetail.tsx`

**`QueueTab`:**
- Fetch `api.stewardQueue()`.
- A list of rows, each with:
  - title (`data-plain-exempt`);
  - kind chip ("Shared skill" / "Featured skill, not checked");
  - credit ("by {credit_name}");
  - "{steps} steps";
  - "submitted {relative time}" for submissions;
  - primary "Review" → `setReviewing(case_id)`.
- Empty: "The queue is empty. New shared skills will appear here."

**`ReviewDetail`** (replaces the tab content while `reviewing` is set; "← Back to the queue"):
- Fetch `api.getCase(caseId)`. The steward header lets the service return submitted community skills.
- **Header:**
  - title;
  - the collection chip (Featured / Community);
  - the library status chip;
  - `ReviewBadge`;
  - the credit, licence (`licenceLabel`) and submitted date;
  - "Open as a learner" → `onOpenSkill(caseId)`.
- **Left: source.**
  - Hero cases (`view.goal.modality !== 'universal'`): `<SourcePanel view={view} focus={focusEv} />` from `hero/SourcePanels.tsx`.
  - Composed skills: the first used source via `api.mediaUrl(view.case_id, source_id)` as `<img>`, `<video controls>` or `<audio controls>` by `mime_type`.
- **Right: "Steps and checks ({n})".**
  - Each claim row shows the number, the statement (`data-plain-exempt`) and a **Details** line in small muted text: `claim_id · claim_type · Seen in the source/AI's reading · confidence 0.82 · at 0:12`. This audit detail is allowed in the steward console.
  - Clicking a row with evidence sets `focusEv` (hero cases).
  - Edit and Remove per row, like `CheckStepsDialog`, but with `reviewer` = the reviewer name field (below) or "steward".
  - For curated cases, review calls succeed because the steward header is sent (P1 allows it).
- **Decision bar** (sticky at the bottom on desktop):

| Case | Controls |
|---|---|
| Submission (`access.library_status === 'submitted'`) | Primary "Publish" (confirm: "Publish to the library? Anyone will be able to practise it."); secondary "Send back to creator"; danger-styled secondary "Reject". The last two open a small note form (required; ≤ 500 chars; with the placeholder "What should the creator change?" or "Why is it not accepted?"). Each calls `api.stewardDecide(id, {decision, note})`, then `onLibraryChanged()`, then returns to the queue with a success toast line ("Published.", "Sent back to the creator.", "Rejected."). |
| Featured skill (curated) | A "Reviewer name (shown in the record)" input (required for approve); primary "Mark as checked by an expert" → `reviewCase(id, {action:'approve', reviewer: name, note})`; secondary "Download decisions" (`FileDown`) → `api.stewardReviewExport(id)`, saved via a temporary object URL `<a download="anveshan-review-{id}.json">` and revoked afterwards; secondary "Hide from library" / "Show in library" by status → `stewardDecide` with `unlist` (note required) or `republish`. |

- The text under "Download decisions": "The demo server forgets changes when it restarts. Download the decisions and commit them with tools/apply_expert_review.py to keep them."

### 3.5 `LibraryTab.tsx`

- Fetch `api.stewardLibrary()`.
- A table with the columns Skill, Collection, Status (chip), Checked (`ReviewBadge`), Learners, Last activity and Actions.
  - Actions: "Insights" (opens `InsightsDialog`), "Hide" / "Show" (as in §3.4, with a note prompt for Hide), "Review" (`setReviewing`).
- On mobile (< 640 px), render each row as a card instead of a table row.
- A filter chip row: All · Featured · Community · Hidden.
- Empty: "No skills in the library yet."

### 3.6 `ConsentTab.tsx`

- Fetch `api.stewardConsent()`.
- A table (cards on mobile) with the columns:
  - Skill;
  - Credit;
  - Licence (`licenceLabel`);
  - Consent ("Anyone may practise");
  - Rights confirmed (a date, or "Not recorded");
  - People in media ("No" / "Yes, they agreed" / "Yes, NOT confirmed" in crimson);
  - Sources (attribution · licence, joined by "; ", `data-plain-exempt`).
- A row expands to show its history (time, actor, action, note).
- Primary "Download record (JSON)" (`FileDown`) → `api.stewardConsentExport()` → save as `anveshan-consent-{yyyymmdd}.json`.

### 3.7 `UsageTab.tsx`

- Fetch `api.stewardUsage()`, with a refresh button.
- Cards:
  - "AI calls today" (+ a `ProgressBar` against `daily_budget`, or "no daily limit");
  - "Calls with visitors' own keys" (`own_key_calls`);
  - "Repeat calls answered from the cache" (`cache_hits`);
  - "Tries today";
  - "New skills analysed today" (`compose_today`);
  - "Storage" (used of cap, + a `ProgressBar`);
  - "Private data kept for" (`{data_ttl_hours} hours` or "kept until restart");
  - "Server mode" ("Live AI" when the mode is live, "Recorded results" when recorded);
  - "Running for" (uptime formatted as "3 h 12 min").
- Two small tables, each shown only when it has rows:
  - "Requests by type": friendly names for the classes: compose "Analyse an upload", compose_step "Edit a skill", attempt "Submit a try", query "Ask a question", auth "Steward sign-in";
  - "Blocked by rate limits".
- A "Problems by type" table from `errors_by_category`, using friendly names where known (`INVALID_INPUT` "Rejected input", `MODEL_FAILURE` "AI service problem", `MODEL_TIMEOUT` "AI took too long", `RATE_LIMITED` "Rate limited", `STEWARD_REQUIRED` "Steward code missing"; otherwise the raw category).
- Shared formatters go in `components/steward/format.ts`: `fmtBytes`, `fmtPct`, `fmtDuration`, `fmtRelative` (e.g. "5 min ago") and `fmtDate`.

## 4a. "Try with an example" in the composer (WI-3.1)

In `StepUpload.tsx`, under the drop zone, add a section "No file to hand? Try with an example".

**Content:**
- Call `api.listSampleSources()` (frozen from Phase 0; the mock returns 2).
- Show one small card per source: label, description, a credit and licence line (`data-plain-exempt`), and a secondary button "Use this example".

**Behaviour:**
- The button calls `api.analyzeSampleSource(sample_id)` instead of `analyzeSource`. Everything after that is identical:
  - the wizard shows "perceiving";
  - it then branches to refused, needs-input or proposal exactly as for an upload.
- Implement this by adding an `onAnalyzeSample(sampleId)` prop or callback from `ComposerWizard`, reusing its existing state machine. Do not duplicate the branching logic.
- The rights checkbox is not needed for examples: the server sets `rights_confirmed` for committed examples. Show "Example provided with Anveshan ({licence})" instead.
- Hide the section when the list is empty. On error, show `ErrorNote`.

## 4. Composer wording (`components/composer/**`; creator surface)

Apply K9-00 §5 to the wizard's visible text. Keep its logic.

| File | Change |
|---|---|
| `StepUpload.tsx` | Intro → "Upload a photo, video or audio of something you know how to do. The AI looks at it and proposes a practice task. You check everything before anyone else sees it." The timing note keeps its numbers in plain words: "This usually takes 10–30 seconds for photos and audio, and up to about 90 seconds for videos." The rights checkbox stays required. |
| `StepProposal.tsx` | Column headings: "What we measured" stays; "What the AI perceived" → "What the AI understood" with the badge "AI's reading" instead of INFERRED; kicker "Observed" → "Measured"; "Inferred (AI-perceived)" → "AI's reading"; "How we'll teach and check it" stays. "Transcript (INFERRED)" → "What was said (AI transcript)". "OBSERVED" / "INFERRED" badge components render "Measured" / "AI's reading". The banner "Composed skill · AI-perceived elements are INFERRED until reviewed by an expert." → "Next you'll check these steps. Nothing is shared until you publish." Technical labels such as check method ids or `CHK-…` ids render only when `DEBUG`. |
| `StepBuilding.tsx` | "Generating rubric, knowledge package and goal model." → "Building the practice task and its checks…" |
| `StepNeedsInput.tsx`, `ComposerWizard.tsx` | Same treatment for any jargon. |
| Final step, `onDone` in `App.tsx` | After create, open the Learn page of the new skill (exists). `CreatorPanel` then guides the creator to "Check what the AI understood". |

## 5. Self-check

1. `npm --prefix app run build` and `npm --prefix app run build:mock` pass.
2. In `dev:mock`:
   1. Library → "Share a skill you know" → upload any small image → proposal → create → the Learn page shows the "Your skill" panel.
   2. Check steps → edit one, remove one → "Looks right" → Publish → fill in the form → Send for review → status "Waiting for review".
   3. Footer "Steward sign-in" → code `steward` → Overview shows the attention item → Queue → Review → Publish.
   4. My skills shows "Published" → "See how learners are doing" (the mock returns empty insights for composed skills; open Kolam insights from the steward Library tab to see the populated view).
   5. Consent tab → Download (a file downloads). Usage tab renders.
   6. Sign out → the Steward nav item disappears.
3. Keyboard: tab through the steward tabs and the dialogs; Esc closes dialogs; focus stays visible.
4. Width 375 px: no horizontal scroll on My skills, the console tabs, Review detail or the dialogs.
5. Report `docs/kiro/reports/K9-P3-REPORT.md` (≤ 60 lines): screens built, decisions taken, anything stubbed, requests for PC (e.g. the `ReviewBadge own` prop).

## 6. Pitfalls

- **`App.tsx` is large.** Edit surgically. Don't reformat the file, and don't rename existing state or handlers that P2's views receive.
- **`heroCases` is the list for everything** (curated, composed, derived). Filter by `access` fields, never by guessing from ids.
- **Downloads:** `api.stewardConsentExport()` returns a `Blob`. Create the object URL, click a temporary anchor, then `URL.revokeObjectURL`. Never put the token in a URL.
- **401 vs 403:**
  - 401 `STEWARD_REQUIRED` → back to sign-in;
  - 403 `STEWARD_DISABLED` → the "not enabled" card;
  - 403 `NOT_OWNER` on creator actions → `ErrorNote` (should not happen in the UI because the panel only shows for owners).
- **The mock steward code is `steward` in mock mode only.** Never hard-code a code for the real service.
