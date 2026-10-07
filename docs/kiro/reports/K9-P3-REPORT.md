# K9-P3 Report

## Done

- **§1 Navigation**: Header rewrote layout (Anveshan wordmark + Library/My skills/Steward nav, breadcrumb + stepper row on skill pages, case select only when `DEBUG`). App.tsx wired mine/steward views, `readUrl()` accepts all 7 views, URL effect removes `case` for mine/steward.
- **§2.1 MySkillsView**: Skills grid with status chips, steward notes, derived-upload sub-heading, empty state.
- **§2.2 CreatorPanel**: Checklist (check/practise/publish), withdraw/make-private confirm dialogs, insights shortcut. Renders as `ownerSlot` in `HeroSourceView`.
- **§2.3 CheckStepsDialog**: Accessible modal; edit/remove claims with inline confirm; "Looks right" approves.
- **§2.4 PublishDialog**: Credit, licence fieldset, people-consent conditional, rights checkbox, steward note; 400-blocker list.
- **§2.5 InsightsPanel + InsightsDialog**: Fetches insights, renders stats, bar rows, suggestions with Lightbulb list, enough-data note.
- **§3.1 StewardConsole**: Gate (disabled / not signed in / console); tab list with queue badge; sessionStorage tab persistence; 401 auto-sign-out.
- **§3.2 StewardSignIn**: Password field, mock-code hint, 401/429 handling.
- **§3.3 OverviewTab**: KPI grid (6 cards), attention list.
- **§3.4 QueueTab + ReviewDetail**: Queue list; review detail with claim edit/remove; publish/return/reject decisions; featured approve/download/hide.
- **§3.5 LibraryTab**: Filter chips (all/featured/community/hidden); table + mobile cards; hide with note, show, review, insights.
- **§3.6 ConsentTab**: Table with expand-to-history; download export.
- **§3.7 UsageTab + format.ts**: 9 stat cards, 3 small tables; `fmtBytes`, `fmtDuration`, `fmtRelative`, `fmtDate`, `fmtPct`.
- **§4a StepUpload sample sources**: Fetches `listSampleSources()` on mount; cards with "Use this example" buttons wired via new `onAnalyzeSample` prop on `StepUpload` / `ComposerWizard`.
- **§4 Composer wording**: StepUpload intro/timing text updated; StepProposal column headers (Measured/What the AI understood), badges (Measured/AI's reading), transcript label, banner text; StepBuilding progress text.
- **Footer**: "Steward sign-in" button added (hidden on steward view, hidden when steward_enabled false); "VIEW PROVENANCE DAG" now only shows when `debug`.

## Tests

- `npm run build`: PASS (tsc clean)
- `npm run build:mock`: PASS

## Deviations

- The `DEBUG` constant is imported from `api/debug.ts` (not from URL params inline) to respect the existing pattern.
- Footer "VIEW PROVENANCE DAG" gated on `debug` (local var from `window.location`) rather than `DEBUG` import to match original scope.

## Requests for PC

- `ReviewBadge` `own` prop: P2 adds it. K9-P3 calls `<ReviewBadge status={...} />` only (no `own` prop); pass it in integration when P2 lands.

## Open issues

None.

## Live calls used

0
