# WP3 Composer UI — Report

**Spec:** K8-composer-ui.md | **Branch:** kiro/wp3-composer-ui | **Date:** 2026-10-06

---

## Done

**K8 §3 — API client + types (steps 1–4)**
- Added TypeScript interfaces mirroring Python models (same field names):
  `Segment`, `Observation`, `ProbeFacts`, `IntakeResult`, `TargetProperty`, `SkillStep`,
  `SkillConstraint`, `SkillRelevance`, `SkillCheck`, `SkillModel`, `CaseProfile`, `DraftView`,
  `CreateFromDraftEdits`, `UniversalUiView`.
- Extended `CaseSummary` with `composed?: boolean`, `structures?: string[]`.
- Extended `CaseView` with `profile?: CaseProfile | null`.
- Added `GoalModality.universal`. Added `UniversalUiView` to `GoalUiView`.
- Added `analyzeSource`, `getDraft`, `refineDraft`, `createFromDraft` to `httpApi` + `Api`.

**K8 §4 — Mock backend** (`app/src/api/mock/composer.ts`)
- All 6 scenarios implemented: image (line-art proposal), `*refuse*` (safety refused),
  `*unclear*` → refine path, video (procedure), `*speech*` audio (utterance), other audio (rhythm).
- `createFromDraft` returns a `CaseView` with `goal.modality === 'universal'`.
- Simulated latencies: analyze 4 s, refine 2 s, create 3 s.
- `mockApi` extended with `analyzeSource`, `getDraft`, `refineDraft`, `createFromDraft`.
- `listCases` populates `composed` and `structures` for universal cases.
- `evaluateUniversal` provides mock attempt results for universal practice.
- Keyframe assets return synthetic SVG data-URLs.

**K8 §5 — Composer wizard** (`app/src/components/composer/`)
- `ComposerWizard.tsx` — state machine: upload → perceiving → refused | needs_input | proposal → building → done.
- `StepUpload.tsx` — drop zone; client guards (≤ 30 MB, video 8–120 s, audio 3–60 s, image ≥ 64 px); rights checkbox; file preview.
- `StepPerceiving.tsx` — stage text ("Measuring → Looking → Structuring") + elapsed time.
- `StepRefused.tsx` — refusal message + probe facts + "Try another file".
- `StepNeedsInput.tsx` — required title/description → calls `refineDraft`.
- `StepProposal.tsx` — three-column layout: OBSERVED, INFERRED, editable SkillModel. Checks table with MEASURED/SPECIALIST/AI-JUDGED badges. Learner kinds checkboxes. Validation.
- `StepBuilding.tsx` — animated progress bar.

**K8 §5 entry points**
- "Create a new skill" card in `DiscoveryView` with `CaseKey { kind: 'composer' }`.
- "Your skills" section listing `composed: true` cases with structure badges.
- `?view=composer` route in `App.tsx`; `AppView` extended with `'composer'`.

**K8 §6 — Universal case views**
- `hero/universal/UniversalSourceView.tsx` — reference media placeholder, property boxes, step strip with synthetic keyframes, transcript, claims list, review panel, INFERRED banner.
- `hero/universal/UniversalPracticeView.tsx` — upload controls per allowed learner kind; reuses `KolamCanvas` when `trace` + `line_art` available; relevance refusal shown inline (not counted as attempt).
- `HeroSourceView` and `HeroPracticeView` dispatch to universal views when `goal.modality === 'universal'`.

**Pre-existing fix**
- `lucide-react` 0.475.0 was installed without a root `.d.ts`; added a complete ambient module declaration to `vite-env.d.ts` covering all 70+ icons used in the project.

---

## Tests

- `npm run build`: **PASS** (tsc + vite; no chunk > 500 kB; index-BO8LM1PM.js 402 kB)
- `check_contract_parity.py`: **PASS** (8 root contracts, 17 interfaces, 7 enums)
- `check_governance.py`: **PASS**
- `check_case_packs.py`: **PASS** (7 packs)
- No Python tests in scope (WP3 owns `app/**` only).

---

## Live results

None — K8 spec §8 step 2 moves real-service testing to WP5 step 3 (override §7.8). WP1 and WP2 are not yet merged.

---

## Deviations

- `DESIGN.md` was missing from the worktree; referenced default patterns from existing hero views.
- `KolamCanvas` in universal practice view uses a placeholder `KolamUiView` (no dots/curves). The real line_art specialist payload from WP1/WP2 will provide the actual geometry at WP5 integration.

---

## Requests for WP5

1. Wire the real `profile.skill_model.specialists.line_art` payload into the `UniversalPracticeView` `KolamCanvas` after WP2 merges.
2. Wire `api.mediaUrl(caseId, sourceId)` to the actual uploaded source in `UniversalSourceView` (currently shows placeholder text).
3. Add `CRIT-U-<check_id>` MEASURED vs AI-JUDGED badges to `AttemptResultView` for universal results (step-alignment strip from `trajectory.artifacts`).

---

## Open issues

None blocking. Build, parity and governance all green.
