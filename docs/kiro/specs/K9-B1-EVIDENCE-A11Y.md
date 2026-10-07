# K9-B1 — "How we check" page and the accessibility sweep (technical-panel WI-5.3, WI-7.1; closes J-16, part of J-17)

**Wave B task:** it starts only after Wave A (P1–P7) has been merged into `k9/integration`. Read `00-COMMON.md`, `K9-00-PRODUCT-UX.md`, then this file. Your folder, branch, status file and inbox protocol are in `K9-ORCHESTRATOR.md` §2 and §4.

In Wave B you own **all of `app/`**, except `app/public/evidence.json` (B2 writes that file) and `app/scripts/**`.

---

## 1. "How we check" page (`?view=evidence`)

**Purpose (end-user framing, not a judges' page).** For anyone who wonders "can I trust this feedback?". It explains in plain words:
- how an attempt is checked;
- what the AI does and does not do;
- how reliable the checks have been in our own tests;
- what has not been tested yet.

**Entry points:**
- the footer link "How we check results" (next to "Steward sign-in");
- a link at the end of every "Why this feedback?" disclosure ("How we check results →");
- a link in the How-it-works guide.

**Files:**
- new `app/src/components/EvidencePage.tsx`;
- the route in `App.tsx` (`AppView` already allows string views; add `'evidence'` to the `readUrl` list and render the page);
- `types/workspace.ts` (add `'evidence'` to `AppView`).

**Content, top to bottom:**
1. `h1` "How we check results" and one sentence: "Every check is scored by fixed rules from what was measured. The AI helps perceive and word things; it never sets a score."
2. **"What happens to your attempt"**, five numbered steps with icons:
   1. We compare it with what the source shows (the goal).
   2. Each check is measured: met, partly met, not met, or "couldn't tell".
   3. We find where it first went off track.
   4. Feedback points to the step in the source it comes from.
   5. Your second try shows what changed.
3. **"What the AI does / does not do"**, a two-column list:
   - **Does:** perceives uploads, suggests the steps of a new skill, words advice, answers questions from the source.
   - **Does not:** score, pass or fail, decide what is published, or see names in insights.
4. **"How reliable has it been?"**
   - Read `/evidence.json` (`fetch('/evidence.json')`; written by B2, schema in §1.1).
   - Show:
     - one card per skill: name, number of repeated runs, "same result every time" rate, and "good sample passed / mistake sample caught / unrelated sample refused";
     - the test-suite size and date.
   - When the fetch fails, show "Reliability numbers are not available on this server."
5. **"What we have not tested yet"**, from `evidence.json` `not_yet` (strings). If absent, show: "No study with real learners or experts has been run yet." and "Internet sources are not verified experts."
6. A link-button "Back to the library".

Plain-language rules apply (K9-00 §5). The page **is** scanned by `check:plain`: add `?view=evidence` to the walk in `app/scripts/check_plain_language.mjs`. You may edit that one line, even though the scripts belong to P7, because P7 is merged by now.

### 1.1 `evidence.json` schema (B2 writes it; you render it)

```json
{
  "generated_at": "2026-10-09T10:00:00Z",
  "tests": {"count": 520, "date": "2026-10-09"},
  "skills": [
    {"case_id": "kolam", "title": "Kolam drawing", "runs_per_sample": 3,
     "consistency": 1.0,
     "samples": {"good": "passed", "flawed": "caught", "unrelated": "refused"},
     "notes": "Deterministic checks; identical results by design."}
  ],
  "not_yet": ["No study with real learners or experts has been run yet.", "Internet sources are not verified experts."]
}
```

Sample values are one of `passed`, `caught`, `refused`, `missed` or `failed`. Render them as:

| Value | Display |
|---|---|
| passed (good) | "Good attempt passed" |
| caught (flawed) | "Mistake caught" |
| refused (unrelated) | "Unrelated attempt refused" |
| missed | "Mistake missed" (amber) |
| failed | "Good attempt failed" (amber) |

## 2. Accessibility sweep (all of `app/src`)

1. **Text sizes:**
   - replace every remaining `text-[8px]`, `text-[9px]` and `text-[10px]` with `text-[11px]` (labels, chips) or `text-xs` (body);
   - check with `grep -rn "text-\[\(8\|9\|10\)px\]" app/src`, which must return nothing;
   - `workspaces/*` and the legacy synthetic components are included.
2. **Contrast:** in `app/tailwind.config.js`, change `on-surface-variant` from `#9ba1a6` to `#a9afb4`. That gives at least 4.5:1 on `#14181a` and on `#08090a`; check with the formula in a small node one-liner and record the ratios in the report. Check that the muted text still looks muted.
3. **Icon-only buttons:** `grep -rn "<button" app/src` and inspect those whose content is only an icon. Each needs `aria-label`.
4. **Dialogs:** every modal has `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, a visible "Close", and `useEscape`. This covers the modals in `components/` (LineageDrawer, FirstDivergenceModal, MicroPracticeRetryModal, StitchModal, SettingsModal, LifecycleInspectorModal, GuideModal, ApiKeyModal) and the P3 dialogs.
5. **Focus:** add a global focus style in `app/src/index.css` (or the main CSS file):

   ```css
   :focus-visible { outline: 2px solid #00e5ff; outline-offset: 2px; }
   ```

   Do not remove existing outlines.
6. **Mobile (375 px):** load each main view in `dev:mock` with a 375×812 viewport. Puppeteer is OK; reuse `check_plain_language.mjs` helpers in a small `--mobile` flag that asserts `document.documentElement.scrollWidth <= 375`. The views are Library, Learn, Practise, Results, My skills, the steward tabs and the evidence page. Fix any overflow (`min-w-0`, `flex-wrap`, `overflow-x-auto` on tables).
7. **axe-core is not installed; do not add it.** Rely on the checks above.

## 3. Acceptance

- Both builds (`build`, `build:mock`) pass.
- The text-size grep is empty.
- The contrast ratios are recorded.
- The mobile check passes for all listed views.
- `check:plain` (mock) still passes, including the evidence page.
- Report `docs/kiro/reports/K9-B1-REPORT.md`.
