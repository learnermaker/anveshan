# K9-P2 — Learner surface: plain language, trust layer, "Why this feedback?"

Read `00-COMMON.md`, then **`K9-00-PRODUCT-UX.md` in full** (sections 3, 5 and 6.1–6.4 are your brief), then this file.

Your folder and branch are in `K9-ORCHESTRATOR.md` §2. Phase 0 is already applied in your branch:
- `app/src/copy/plain.ts`;
- `app/src/api/debug.ts`;
- `app/src/api/types-product.ts`;
- the `ownerSlot` props on the Learn views and the `onOpenMine` prop on `DiscoveryView`.

You make the learner path a product: same flows and same data, plain words, and no audit tooling (it moves behind `DEBUG`). Trust is expressed as useful explanations.

---

## 0. Ground rules

- **UI only.** You may not edit `app/src/App.tsx`, `app/src/components/Header.tsx`, `app/src/components/composer/**`, `app/src/api/**` (except reading), `app/src/vite-env.d.ts` or anything outside `app/`. P3 owns those. If you need something there, write it in your report under "Requests for PC".
- Use only icons declared in `app/src/vite-env.d.ts` (Phase 0 added Lightbulb, Users, BarChart3, Inbox, Library, FileDown, LogOut, Trash2, BookOpen, Share2, Gauge, HardDrive, ListChecks, Hourglass, Globe).
- Keep every existing behaviour (sessions, attempts, uploads, the Kolam canvas, show-me animation, BYOK prompts, the retry flow, stepper callbacks). This task changes presentation, not flows.
- Every technical element you remove from the learner view must still render when `DEBUG` is true (`import { DEBUG } from '../api/debug'`, with the path adjusted per file). This is how the team keeps its diagnostics.
- Mark containers of person- or source-authored text with `data-plain-exempt`:
  - skill titles;
  - claim/step statements;
  - query answers;
  - task instruction items;
  - feedback finding text that quotes measurements;
  - drill instruction text.

  Do **not** mark labels, headings or buttons.
- Text sizes: in every file you edit, replace `text-[8px]`, `text-[9px]` and `text-[10px]` with `text-[11px]` (labels) or `text-xs` (body). Do not add new ones.
- Commit after each numbered section below: `feat(ui): … (K9-P2 §n)`.
- Verify often:
  - `npm --prefix app run build` (type check and build);
  - `npm --prefix app run build:mock`;
  - `npm --prefix app run dev:mock` (port 5174) and look at each screen.

## 1. Files you own

**Existing:**
- `app/src/hero/ui.tsx`
- `app/src/hero/Guidance.tsx`
- `app/src/hero/HeroSourceView.tsx`
- `app/src/hero/SourcePanels.tsx`
- `app/src/hero/HeroPracticeView.tsx`
- `app/src/hero/HeroTransmissionView.tsx`
- `app/src/hero/results/AttemptResultView.tsx`
- `app/src/hero/results/FirstDivergenceCard.tsx`
- `app/src/hero/results/ProgressCurve.tsx`
- `app/src/hero/universal/UniversalSourceView.tsx`
- `app/src/hero/universal/UniversalPracticeView.tsx`
- `app/src/hero/universal/ResultExtras.tsx`
- `app/src/hero/kolam/*`
- `app/src/hero/tabla/*`
- `app/src/hero/origami/*` (if present)
- `app/src/components/DiscoveryView.tsx`
- `app/src/components/HowItWorks.tsx`

**New:**
- `app/src/hero/WhyThisFeedback.tsx`
- `app/src/hero/TrustLine.tsx`
- `app/src/hero/StepsList.tsx`

## 2. Shared badges in `hero/ui.tsx`

Change the badge components so every existing call site becomes plain automatically:

| Component | Learner rendering (DEBUG false) | DEBUG true |
|---|---|---|
| `RuntimeClassBadge` | `return null` | unchanged |
| `MockBadge` | already returns null | unchanged |
| `SourceLabelBadge` | `Badge` with `SOURCE_LABEL[label]` (tone: SYNTHETIC crimson, INTERNET_REFERENCE cyan, others muted) | unchanged |
| `ReviewBadge` | `Badge` with `REVIEW_LABEL[status]` (emerald when approved/revised, amber otherwise). Add an optional prop `own?: boolean` that switches to `OWN_REVIEW_LABEL` | unchanged |
| `VerificationBadge` | observed → `null` (no badge needed when seen in the source); inferred → `Badge tone="amber"` "AI's reading"; unverified → muted "Not checked" | unchanged |
| `StatusBadge` | `STATUS_PLAIN[status]` with the same tones | unchanged |

Keep `STATUS_LABEL` exported (it is used elsewhere) and add `export { STATUS_PLAIN }` re-export convenience if useful. Do not change `Panel`, `btn`, `ErrorNote`, `Spinner` or `ProgressBar`.

## 3. New small components

### 3.1 `hero/TrustLine.tsx`

```tsx
export function TrustLine({ view, className }: { view: { runtime_label: string; review_status: string; access?: { credit_name: string | null; collection: string } }; className?: string })
```

- Renders a `<p>` with an `Info` icon (aria-hidden) and `trustLine({runtime_label, review_status, credit_name: view.access?.credit_name, collection: view.access?.collection})` in `text-sm text-on-surface-variant`.
- `SYNTHETIC` → the text is `text-divergence-crimson`.

### 3.2 `hero/StepsList.tsx` — "What you'll learn"

```tsx
export function StepsList({ claims, activeId, onShow }: { claims: KnowledgeClaim[]; activeId: string | null; onShow: (claimId: string) => void })
```

- An ordered list (numbers 1..n by position).
- Each item:
  - the statement, in a `data-plain-exempt` span;
  - when `claimVerification(claim) === 'inferred'`, a small "AI's reading" badge (use `VerificationBadge`);
  - when the claim has `evidence_refs[0]`, a secondary button "Show me" with an `Eye` icon (`aria-label={`Show step ${i+1} in the source`}`) that calls `onShow(claim_id)`;
  - the active item gets `border-cadmium-amber bg-cadmium-amber/10`;
  - when `evidence_refs[0]` has `start_sec`, show "at 0:12" (use `fmtTime` from `./locators`) in muted text.
- Claims without evidence get no button and no "no locatable evidence" text.
- Export a helper `pointNumber(claims, claimId) => number | null` (1-based position) for citations.

### 3.3 `hero/WhyThisFeedback.tsx`

```tsx
export function WhyThisFeedback({ view, claimIds, measured, aiWorded, onShowSource, defaultOpen = false }: {
  view: CaseView; claimIds: string[]; measured?: string | null; aiWorded?: boolean;
  onShowSource?: (claimId: string) => void; defaultOpen?: boolean })
```

A `<details>` with `<summary>` "Why this feedback?" (`text-xs text-caliper-cyan cursor-pointer`). The body follows K9-00 §5 exactly:
1. **"From the source"**: each cited claim's statement (`data-plain-exempt`) with its point number ("Point 3"). Show a "Show me" link only when `onShowSource` is given and the claim has evidence. If `claimIds` is empty, write "This check comes from the skill's goal rather than a single step."
2. **"What was measured"**: `measured`, when given (`data-plain-exempt`).
3. **"How it was scored"**: "Scored by fixed rules from what was measured; the AI never sets a score."
4. **When `aiWorded`**: "The advice was worded by AI from these findings."

## 4. Learn views

### 4.1 `HeroSourceView.tsx` (inner component for kolam, origami and tabla)

**Header block:**
- Keep the back button, with the label "All skills".
- Keep "Step 1 of 3 · Learn from the source", the title (wrap it in `data-plain-exempt`) and the "Start practising" primary button.
- **Learner mode:** replace the badge row with `<TrustLine view={view} />`. Keep `SourceLabelBadge`, `ReviewBadge`, the modality badge, "derived from" and the Reload button only when `DEBUG`.
- Replace the paragraph that starts "This page shows what Anveshan learned…" with: "Watch how the source does it. Each step below links to the moment in the source. When you are ready, press **Start practising**."
- The warnings list renders only when `DEBUG`.

**Left column:**
- "Source evidence" panel: kicker "Source"; keep the title (`view.package.title` in `data-plain-exempt`) and `SourcePanel` unchanged.
- **Learner mode:** under it, a credit line built from the first used source: `Source: {attribution} · {license}` (muted `text-xs`).
- The "Provenance" panel only when `DEBUG`.

**Right column, top to bottom:**
1. `{ownerSlot}`. It is already there from Phase 0; keep it first.
2. **Learner mode:** `Panel` with kicker "What you'll learn" and title `{n} steps and checks`. Show `view.package.summary` as a muted paragraph (`data-plain-exempt`), then `<StepsList claims={claims} activeId={focus?.claimId ?? null} onShow={(id) => {...same as today's ClaimRow click: setFocus with the claim's first evidence...}} />`.
   - **DEBUG:** keep today's "Knowledge package · Claims" panel with `ClaimRow` (IDs, type, confidence).
3. `EvidenceQuery`:
   - kicker "Ask", title "Ask about this skill";
   - spinner text "Looking in the source…";
   - `INSUFFICIENT_EVIDENCE` badge → a sentence "The source does not say.";
   - "CITED:" → "From:";
   - each cited id renders as a button "point {pointNumber}" (fallback "a step") that focuses the claim;
   - the answer paragraph is `data-plain-exempt`.
4. `ExpertReviewPanel` only when `DEBUG`. The steward console (P3) is where curated review happens now.

### 4.2 `UniversalSourceView.tsx` (composed skills)

**Header:**
- Back button "All skills" (today it says "Portfolio").
- Keep the step label, title and primary button.
- Replace the badges and the amber "Composed skill · AI-perceived elements are INFERRED…" line with `<TrustLine view={view} />`.
- The UNIVERSAL badge, MockBadge and Reload are `DEBUG` only.
- Warnings are `DEBUG` only.

**`SourceMedia`:** the caption `{source_id} · {mime}` only when `DEBUG`.

**`GoalStateSection` labels:**

| Today | Change to |
|---|---|
| "Transcript (INFERRED)" | "What was said (AI transcript)" |
| "Goal properties" | "What the finished result should look like" |
| "Steps (INFERRED)" | "Steps" |
| per-step badge "AI-inferred until reviewed" (not reviewed) | `<VerificationBadge state="inferred" />`, which renders "AI's reading" |
| "(critical)" | " (key step)" |

- Times stay.
- `ui.structures` badges only when `DEBUG`.
- Step names and property statements get `data-plain-exempt`.

**Panels:**

| Panel | Learner mode | DEBUG |
|---|---|---|
| "Goal state" | kicker "What you'll learn" | unchanged |
| "Skill profile" | hidden | shown |
| "Provenance" | hidden; add the credit line as in §4.1 under the Source panel | shown |
| "Knowledge package · Claims" with inline edit | **removed**: the creator edits through P3's "Check steps" dialog in `ownerSlot`, and the steward uses the console | shown |
| "Query" | as §4.1 ("Ask about this skill") | as §4.1 |
| "Expert review" (`ReviewPanel`) | hidden | shown |

When the claims panel is removed in learner mode, `ownerSlot` must still render first in the right column.

**Fix the silent failure in `doRevise`:** today it swallows errors with `catch { // ignore }`. Store the error in state and render `<ErrorNote error={…} />` under the claims list (DEBUG path).

## 5. Practise views

`HeroPracticeView.tsx` and `UniversalPracticeView.tsx`:
- Badge row → `<TrustLine view={view} />`. The `DEBUG` path keeps the badges.
- Use `attemptLabel` throughout:
  - "Attempt 1 · baseline" → "First try";
  - "Attempt 2 · retry (full task)" → "Second try (the whole task again)";
  - "Attempt 2 · retry" → "Second try".
- "Start session" → "Start practising".
- The learner badge `Learner: {name}` keeps its text, but its `title` must not show the session id (title "Your name for this practice"). DEBUG keeps the id.
- Kolam photo note (HeroPracticeView ~line 319): "A photo shows only the final state: continuity and first-divergence-in-time become UNCERTAIN." → "A photo shows only the finished drawing, so we can't tell whether the line was continuous or where it first went off track. Drawing on screen gives fuller feedback."
- Any other occurrence of baseline, retry (as a noun label), session, criterion, trajectory or divergence in visible text → plain wording per K9-00 §5.

### 5.1 "Try a sample attempt" (WI-3.1; closes J-11)

Both practice views get a sample picker, so anyone can try a skill with no materials. The API is frozen from Phase 0:
- `api.listSamples(caseId)` returns `SampleAttempt[]`;
- `api.submitSampleAttempt(sessionId, sampleId)` returns `AttemptResult`.

The mock returns three samples. P4 builds the real ones; P5 builds them for origami-crane.

**Placement.** In the attempt panel, under the normal upload or draw controls for the current try (first and second try):
- a `<details>` with the summary "No materials? Try a sample attempt";
- open it by default when the visitor has not submitted anything yet.

**Content:**
- One card per sample: label, description, a "Synthetic sample" badge when `synthetic`, and the credit line when present (`data-plain-exempt`).
- An optional preview:
  - `<img>`, `<audio controls>` or `<video controls>` by `attempt_kind`, when `preview_url` is set;
  - prefix `API_BASE` the same way `api.mediaUrl` does: build `${API_BASE}${preview_url}`, importing `API_BASE` from `api/runtime`.
- A secondary button "Use this as my {first|second} try".

**Behaviour:**
- Clicking the button calls `api.submitSampleAttempt(session.sessionId, sample_id)` and then follows **exactly the same code path** as a successful upload: the same state updates, session attempts and result display.
- To do that, find the function in each view that handles the result of `api.submitAttempt`, and extract the shared "on result" part into a local function so both paths call it.
- When no session exists yet, start one first, the same way the "Start practising" button does (name "Guest").

**Copy rules:**
- Under the cards: "Samples let you see the feedback without your own materials. Your real practice counts more."
- Hide the whole section when `listSamples` returns an empty list.
- On error, show `ErrorNote`.

## 6. Guidance (`hero/Guidance.tsx`)

- `WithClaimRefs`:
  - **learner mode:** remove the `[CLM-..]` references from the text entirely. Strip the match and any whitespace before it so no double spaces remain;
  - **DEBUG:** today's chips.
- `TaskInstructions`:
  - the footnote "Blue tags such as CLM-01 …" only when `DEBUG`;
  - wrap each item's text in `data-plain-exempt`.
- `AttemptProgress`:
  - steps → `['First try', 'Second try', 'See what changed']`;
  - "using the feedback from attempt 1" → "using the feedback from your first try";
  - check the other strings in this component for baseline/retry wording.
- `ReviewNote`: replace its body with `trustLine(...)`-consistent wording. **Signature change:** `ReviewNote({ status, runtimeLabel })`. When `runtimeLabel` is omitted, default to `'INTERNET_REFERENCE'` and update both call sites. Text when not checked: "**Not yet checked by an expert.** You can practise normally. The steps come from an openly licensed source and the AI, so treat results as practice feedback, not a certificate."

## 7. Results

### 7.1 `AttemptResultView.tsx`

- `label` uses `attemptLabel(result.attempt.attempt_number)`.
- **Panel `right`:**
  - remove `RuntimeClassBadge` (it is null in learner mode anyway; keep the element);
  - "all required checks met" / "some required checks not met yet" stay;
  - the score "3.0 / 5.0" stays.
- **Panel title:**
  - "How your attempt progressed toward the goal" stays;
  - "Final result only (the process was not visible)" → "Finished result only (we could not see how you got there)".
- **Events list:**
  - `<code>{e.kind}</code>` only when `DEBUG`;
  - the position label stays;
  - `e.detail` is `data-plain-exempt`.
- **Checks table:**
  - header "Check · Result · Score · What we found";
  - the criterion **name** (bold) is shown;
  - the `criterion_id` and "· required" line becomes "Required" (muted) in learner mode, with the id only when `DEBUG`;
  - `OriginBadge` (universal) only when `DEBUG`;
  - the finding text is `data-plain-exempt`.
- **Footnote under the table** ("Scores come from measured metrics…"):
  - learner mode: "Each check is scored by fixed rules from what was measured. The AI never sets a score; when we couldn't tell, the check scores zero and says so.";
  - DEBUG keeps the original.
- **Feedback panel:**
  - kicker "What to change next time";
  - badge "AI-WORDED ADVICE" → `Badge tone="cyan"` "Advice worded by AI", with a plain title "Worded by AI from the measured findings; scores are not affected.";
  - toggle labels "Show plain version" / "Show AI wording";
  - "fixed wording" → nothing in learner mode.
- **Each feedback item:**
  - remove the `criterion_id` code and the "cites CLM-.." spans in learner mode (keep them under `DEBUG`);
  - put the check name as the item's first line: `view.rubric.criteria.find(c => c.criterion_id === it.criterion_id)?.name`, bold;
  - row labels: "Observed" → "What we saw", "Gap" stays "Gap", "Try" → "Try this";
  - at the end, `<WhyThisFeedback view={view} claimIds={map?.source_claim_ids ?? []} measured={it.what_was_observed} aiWorded={aiWorded} />`.
- **`DrillCard`:**
  - kicker "Practice exercise";
  - badge "UNSCORED · guidance only" → "Not scored";
  - "You have it when" stays;
  - "Grounded in CLM-.." → `<WhyThisFeedback view={view} claimIds={drill.source_claim_ids ?? []} />` in learner mode (DEBUG keeps the ids);
  - "The drill awards nothing. Only the full retry below is evaluated." → "This exercise is not scored. Only your second try of the whole task is checked."

### 7.2 `FirstDivergenceCard.tsx`

- Title or kicker wording → "Where you first went off track".
- "Observed" → "What we saw".
- "Why it matters (source)" → "Why it matters".
- The claim-id spans are `DEBUG` only. Add `<WhyThisFeedback view={view} claimIds={fd.source_claim_ids} measured={fd.observed_finding} />` at the bottom.
- Any visible "divergence" wording → "went off track".

### 7.3 `ProgressCurve.tsx`

- "No trajectory points returned." → "No progress points to show for this try."
- "material divergence" in the legend → "went off track".
- Keep the chart logic.

### 7.4 `HeroTransmissionView.tsx` (Results)

- Header badges:
  - `SourceLabelBadge` → `TrustLine` (learner);
  - remove the "attempt 1/2" spans and `RuntimeClassBadge` in learner mode (`DEBUG` keeps them).
- "Score change" stays.
- The text "Attempt 1 never clearly left the path, so no single fix is claimed." → "Your first try never clearly went off track, so there was no single thing to fix."
- "Change on criteria checked both times" → "Change on checks we could judge both times".
- "Leaves out criteria that were UNCERTAIN in one attempt…" → "Leaves out checks we couldn't judge in one of the tries, so clearer recordings alone don't count as improvement."
- Panel "Attempt 1 vs attempt 2" → "First try vs second try"; the series labels use `attemptLabel(1)` and `attemptLabel(2)`.
- The table header uses "Check" for the criterion column and "First try" / "Second try" for the statuses.
- **"Transmission record" panel:** only when `DEBUG`. In learner mode, show nothing in its place; the WhatNext panel already ends the page.
- Empty state text (~line 41) "You have done attempt 1 (the baseline)…" → "You have done your first try. Read its feedback, then do the whole task once more."

### 7.5 `universal/ResultExtras.tsx`

Any visible text mentioning metric_id or CRIT-U- is `DEBUG` only. Learner mode shows the plain finding only.

## 8. Library (`components/DiscoveryView.tsx`)

Restructure per K9-00 §6.1. Use `heroCases` (`CaseSummary[]`, which now carries `access`).

**Hero section:**
- Keep the headline.
- Primary CTA "Start with the Kolam drawing (about 2 minutes)" (exists).
- Add a secondary button "Share a skill you know" that calls `onSelect({ kind: 'composer' })`.

**"How it works":** keep.

**"Featured skills"** (replaces "Ready-made skills"):
- Cases with `c.hero && (c.access?.library_status ?? 'published') === 'published'`.
- Each card (rewrite `HeroCard`):
  - icon;
  - title (`data-plain-exempt`);
  - "What you'll do: {MODALITY_PHRASE[c.modality]}";
  - one muted line with `SOURCE_LABEL[c.runtime_label]`;
  - `ReviewBadge`;
  - primary "Start" that opens the skill (`onSelect({kind:'hero', id})`).
- Remove the `MockBadge`.

**"Shared by the community":**
- Cases with `c.composed && c.access?.library_status === 'published' && !c.access?.owner`.
- Card: title, "Shared by {credit_name ?? 'a creator'}", `ReviewBadge`, "Start".
- Empty state per K9-00 §6.1, with the "Share a skill you know" button.

**Your skills:**
- Remove today's "Your own skill" section listing composed and derived cases.
- If `heroCases.some(c => c.access?.owner)`, show one line: "You have {n} skill(s) in **My skills**", a link-button calling `onOpenMine?.()`.
- Keep the composer explanation card ("Upload a demonstration, get a practice task") as a short teaser with the "Share a skill you know" button. Remove its upload-own-source file input from this page; the composer handles uploads.
- If hero-derived uploads exist (`c.derived_from`), they now appear only in My skills (P3).

**"Synthetic examples":** keep collapsed (`<details>`).

**Loading and error states:**
- keep `Spinner` and `ErrorNote`;
- the "Refresh" button on error stays.

## 9. How it works (`components/HowItWorks.tsx`)

- Update the labels glossary in `GuideModal` to the new plain labels:
  - "Checked by an expert";
  - "Not yet checked by an expert";
  - "AI's reading";
  - "Synthetic example";
  - "Advice worded by AI";
  - "Not scored";
  - "Met / Partly met / Not met / Couldn't tell".
- Remove entries for labels that no longer appear (RECORDED LIVE, DETERMINISTIC, INFERRED, OBSERVED, REVIEW: …).
- Add a short "Three ways to use Anveshan" section:
  - **Learn:** practise a skill and get feedback;
  - **Share:** turn something you know into a practice task;
  - **Steward:** look after a library of skills, with an access code.
- `AiRoleNote`: keep its meaning (the AI perceives and words advice; fixed rules score), in plain words.

## 10. Self-check before you finish

1. `npm --prefix app run build` and `npm --prefix app run build:mock` both pass.
2. In `dev:mock` (http://localhost:5174), walk Library → Kolam → Learn → Practise:
   - upload a photo attempt (any PNG; the mock evaluates it);
   - read the feedback, open "Why this feedback?";
   - do the second try, then Results.
   - Repeat for Tabla and for a composed skill created in the composer (mock).
   - Note anything technical you still see, and fix it.
3. Add `?debug=1` and confirm the technical panels are back (claims panel with IDs, provenance, run class, transmission record, review panel).
4. Grep your files: `grep -rn "CLM-\|INFERRED\|DETERMINISTIC\|RECORDED\|baseline\|Start session" app/src/hero app/src/components/DiscoveryView.tsx`. Every hit must be in code, in a `DEBUG` branch, or in a type/value rather than visible text.
5. Report `docs/kiro/reports/K9-P2-REPORT.md` (≤ 60 lines):
   - what changed per screen;
   - before and after wording for the top 10 strings;
   - what is DEBUG-only now;
   - requests for PC.

## 11. Pitfalls

- `HeroSourceView` also exports the universal switch (`if modality === 'universal' return <UniversalSourceView {...props} />`). Keep it, and keep passing `ownerSlot` through (`{...props}` already does).
- `claimVerification` is in `hero/locators.ts`; reuse it, don't reimplement it.
- Don't break the `focus` mechanism that drives `SourcePanel` highlighting. "Show me" must set the same state as clicking a claim row today.
- Keep component exports and prop names that `App.tsx` uses (`HeroSourceView`, `HeroPracticeView`, `HeroTransmissionView`, `DiscoveryView` and their props), or P3's App wiring breaks.
- Mock data is SYNTHETIC; don't "fix" mock strings to hide that. Mock mode is a developer tool, and `MockBadge` already returns null.
