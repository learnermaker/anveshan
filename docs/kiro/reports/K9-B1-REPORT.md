# K9-B1 Report

## Done

### §1 — "How we check results" page (`?view=evidence`)
- Created `app/src/components/EvidencePage.tsx` — plain-language page with 5-step explainer, AI does/doesn't list, reliability cards (from `/evidence.json`), not-yet section, back link.
- Added `'evidence'` to `AppView` in `app/src/types/workspace.ts`.
- Updated `app/src/App.tsx`: `readUrl()` includes `'evidence'`, renders `<EvidencePage>`, wires `anveshan:go-evidence` custom event, adds "How we check results" footer link.
- Added "How we check results →" link at the end of every `WhyThisFeedback` disclosure (via `anveshan:go-evidence` event).
- Added "How we check results →" link in `HowItWorks.tsx` guide (closes modal then navigates).
- Added `?view=evidence` as Step 9 in `check_plain_language.mjs`.

### §2 — Accessibility sweep

**Text sizes:** Replaced all `text-[8px]`, `text-[9px]`, `text-[10px]` with `text-[11px]` across 40 files (workspaces, components, hero, steward). Text-size grep is now empty.

**Contrast:** Changed `on-surface-variant` from `#9ba1a6` to `#a9afb4` in `app/tailwind.config.js`.
- Ratio on `surface-container` (`#14181a`): **8.06:1** ✓ (≥ 4.5:1)
- Ratio on `background` (`#08090a`): **8.99:1** ✓ (≥ 4.5:1)

**Icon-only buttons:** Fixed `X` cancel-edit button in `UniversalSourceView.tsx` (added `aria-label="Cancel edit"` and `aria-hidden` on icon).

**Dialogs — ARIA attributes added:**
- `FirstDivergenceModal.tsx`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="first-divergence-title"`.
- `LifecycleInspectorModal.tsx`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="lifecycle-inspector-title"`.
- `LineageDrawer.tsx`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="lineage-drawer-title"`.
- `MicroPracticeRetryModal.tsx`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="micro-practice-title"`.
- `SettingsModal.tsx`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="settings-runtime-title"`.
- `StitchModal.tsx`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby="stitch-modal-title"`.
- Already correct: `ApiKeyModal`, `GuideModal`, `CheckStepsDialog`, `PublishDialog`, `InsightsDialog`.

**Focus ring:** Added to `app/src/index.css`:
```css
:focus-visible { outline: 2px solid #00e5ff; outline-offset: 2px; }
```

**Mobile overflow:** Added `overflow-x-auto` wrapper around 5-column comparison table in `HeroTransmissionView.tsx`. Added `--mobile` flag to `check_plain_language.mjs` (375×812 viewport, asserts `scrollWidth ≤ 375` for Library, Learn, My skills, evidence page).

## Tests / Builds
- `build` (production): PASS
- `build:mock`: PASS
- Text-size grep: empty (PASS)
- `check_duplicates.py`: PASS (812 files)

## Deviations
- Mobile check script requires a running dev server; flag is in place but not run here (no live server in this environment). Views use standard Tailwind responsive classes; `overflow-x-auto` added to the one multi-column table identified.
- Added `--mobile` flag to `check_plain_language.mjs` (more than the spec's "one line" for `?view=evidence`); within the explicit spec permission for B1 Section 2.6.

## Requests for PC
- None.

## Open issues
- None.

## Live calls used
- 0

## Review fixes (applied after REVISE verdict)

Review `K9-B1.md` returned **REVISE** with 3 MUST and 1 SHOULD finding.

### MUST 1 — Template-literal syntax error (FIXED)
**File:** `app/scripts/check_plain_language.mjs` line 343  
**Fix:** Added missing backticks so `page.goto(${BASE_URL}?view=evidence, …)` became `` page.goto(`${BASE_URL}?view=evidence`, …) ``.  
`node --check` confirms no syntax errors.

### MUST 2 — `--mobile` flag never called (FIXED)
**File:** `app/scripts/check_plain_language.mjs` tail  
**Fix:** Replaced the unconditional `main().catch(…)` tail with a conditional:
```js
if (process.argv.includes('--mobile')) {
  runMobileCheck().catch(…);
} else {
  main().catch(…);
}
```
`node check_plain_language.mjs --mobile` now routes to `runMobileCheck()`.

### MUST 3 — Incomplete `MOBILE_VIEWS` list (FIXED)
**File:** `app/scripts/check_plain_language.mjs`  
**Fix:** Added three missing entries so all 7 spec-required views are covered:
```js
{ url: '?view=practice&case=kolam',     label: 'practise' },
{ url: '?view=transmission&case=kolam', label: 'results' },
{ url: '?view=steward',                 label: 'steward' },
```
`MOBILE_VIEWS` now has 7 entries (library, learn, practise, results, my-skills, steward, evidence).

### SHOULD — BOM bytes in 7 files (FIXED)
**Files:** `FirstDivergenceModal.tsx`, `LineageDrawer.tsx`, `LifecycleInspectorModal.tsx`, `StitchModal.tsx`, `SettingsModal.tsx`, `SourcePanels.tsx`, `check_plain_language.mjs`  
**Fix:** Stripped the UTF-8 BOM (`\xEF\xBB\xBF`) from the opening bytes of all 7 files. Builds continue to pass.

### Re-verify after fixes
- `npm --prefix app run build`: PASS (15.86 s)
- `npm --prefix app run build:mock`: PASS (17.10 s)
- `node --check check_plain_language.mjs`: PASS (exit 0)
- BOM check: 0 files with BOM remaining
