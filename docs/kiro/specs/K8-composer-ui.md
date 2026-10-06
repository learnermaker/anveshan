# K8: Case Composer UI wizard + "Your skills"

Read `docs/kiro/specs/00-COMMON.md` first, then **`docs/plans/case-composer.md` in full** and the compose endpoints table there (§8). Folder `...\anveshan-wt\k8-composer-ui`, branch `kiro/k8-composer-ui`; created from `m1/hero-cases` **after K3 is merged** (K3 owns `app/` until then). Runs in parallel with K6 and K7: their backend may not be merged yet, so **build against the mock first**.

## 1. Files you own
`app/**` (keep `app/src/types/contracts.ts` unchanged; CI parity).

## 2. Read first (in the worktree)
- `app/src/api/client.ts`, `app/src/api/types.ts`, `app/src/api/mock.ts`, `app/src/api/mock/*`, `app/src/api/runtime.ts`
- `app/src/App.tsx` and the hero views under `app/src/components/` (find them with `grep -rl "HeroSourceView\|HeroPracticeView" app/src`)
- `DESIGN.md` (the design system: dark instrument aesthetic, Playfair Display + Plus Jakarta Sans, colours)
- `tracks/common/profile.py`: field names for `CaseProfile`, `ProbeFacts`, `CriterionSuggestion`. Mirror them exactly in TypeScript; this is case data, not one of the 8 contracts.

## 3. API client additions (`app/src/api/client.ts` + `types.ts`)
```ts
export type Family = 'image_target' | 'video_states' | 'audio_rhythm' | 'rubric_vlm';
export interface ProbeFacts { modality: 'image'|'video'|'audio'; mime_type: string; bytes: number; sha256: string;
  width?: number|null; height?: number|null; duration_sec?: number|null; has_audio?: boolean|null;
  metrics: Record<string, number>; allowed_families: Family[]; family_reasons: Record<string, string>; }
export interface CriterionSuggestion { criterion_id: string; name: string; observable_indicator: string;
  weight: number; required: boolean; method: 'engine_default'|'vlm_status'; }
export interface CaseProfile { schema_version: '1.0'; case_id: string; title: string; skill_summary: string; domain: string;
  family: Family; transmission_mode: 'forward'|'goal-conditioned'|'corrective';
  learner_input_kinds: ('trace'|'image'|'audio'|'video')[]; vocabulary: Record<string,string>; goal_hint?: string|null;
  criteria: CriterionSuggestion[]; probe: ProbeFacts; model_proposal: Record<string, unknown>; model_run_keys: string[];
  confirmed_by_user: boolean; confirmed_at?: string|null; warnings: string[]; }
export interface DraftView { draft_id: string; probe: ProbeFacts; proposal: CaseProfile; warnings: string[];
  family_labels: Record<Family, string>; }
analyzeSource(file: File, opts: {title?: string; description?: string; rightsConfirmed: boolean}, onProgress?): Promise<DraftView>
getDraft(draftId: string): Promise<DraftView>
createFromDraft(draftId: string, edits: Pick<CaseProfile,'title'|'skill_summary'|'domain'|'family'|'transmission_mode'|'learner_input_kinds'|'vocabulary'|'goal_hint'|'criteria'>): Promise<CaseView>
```
- `analyzeSource` sends multipart fields `file`, `title`, `description`, and `rights_confirmed` as "true"/"false".
- Reuse the existing error normalisation and upload progress helpers.
- `CaseView` gains `profile?: CaseProfile | null`. List items gain `composed?: boolean`, `family?: Family`.

## 4. Mock backend
Add `app/src/api/mock/composer.ts`, returning realistic canned responses that are clearly SYNTHETIC:
- for an image upload: allowed `[image_target, rubric_vlm]`, title "Lotus line drawing", 3 criteria;
- for a video: allowed `[video_states, rubric_vlm]`;
- for audio: allowed `[audio_rhythm]`.

Choose by the file's MIME type. `createFromDraft` returns a CaseView built by reusing the kolam/origami/tabla mock builders with the profile attached and `case_id` = `<slug>~<12 hex>`. Simulate latency: analyze 3 s, create 4 s.

## 5. The wizard (`app/src/components/composer/`)
A new route/view `composer` (follow how `App.tsx` switches views; add `?view=composer`). Entry point: a prominent "Create a new skill" card in Discovery, plus a "Your skills" section listing `composed: true` cases.

**Step 1 — Upload**
- Drag-and-drop or file picker accepting `image/*,video/*,audio/*`.
- Optional "What is this skill?" (title) and "What should a learner achieve?" (description, 300 chars).
- Required checkbox: "I have the right to use this file for teaching and evaluation."
- Client-side guards: ≤ 30 MB (message with a compression tip); video ≤ 120 s and audio ≤ 60 s (check with an HTMLMediaElement `loadedmetadata`).
- Preview the file: image, `<video>` or `<audio>`.

**Step 2 — Analyzing**
A progress state with an honest message: "Measuring the file, then asking the AI for a proposal (≈10–60 s)". Show elapsed time.

**Step 3 — Proposal (the key screen)**
Two clearly separated panels:
- **"What we measured" (OBSERVED):** probe facts (duration, size, has audio) and metrics, with each `family_reasons` line showing pass/fail ticks.
- **"What the AI suggests" (INFERRED):** title, summary, domain, transmission mode, vocabulary, criteria, concerns (from `model_proposal.concerns`), warnings.

Engine selector: radio cards for **all four** families.
- Families not in `allowed_families` are disabled, with their reason shown.
- The recommended family (the proposal's) is pre-selected.
- `rubric_vlm` shows a "lower confidence" badge.

Editable fields: title (required, ≤ 60), summary, domain, transmission mode (select), goal hint. Learner input kinds: checkboxes limited to that family's kinds:

| Family | Kinds |
|---|---|
| image_target | trace, image |
| video_states | video |
| audio_rhythm | audio |
| rubric_vlm | the source modality only |

**Criteria editor:** a list with name, observable indicator, weight (1–5 stepper), required toggle and remove; plus "Add criterion".
- For non-`rubric_vlm` families, show a hint: "These map onto the engine's measurable checks (coverage, order, timing…). Unmatched criteria are dropped with a warning."
- Prevent saving with an empty name or indicator.

Buttons: "Create skill" / "Start over".

**Step 4 — Building**
Call `createFromDraft`, with a progress state; video can take a while, so show elapsed time. On error, show the error category and message, and stay on step 3 with the edits intact.

**Step 5 — Done**
Navigate to the existing hero source view for the new `case_id` (the generic views already render by modality). Show the badges `UPLOAD` and the family label, plus "General rubric review — lower confidence" for `rubric_vlm`. The existing review panel and practice flow are reused.

## 6. Rendering `rubric_vlm` cases
`goal.modality === 'rubric_vlm'`:
- **Source view:** reference images from `/api/media/{case_id}/goal/{asset}` for each `ui_view.reference_assets`, the criteria list, the INFERRED reference description, and the lower-confidence notice.
- **Practice:** upload of the source modality kind.
- **Results:** reuse the criterion table and feedback. The progress curve has only 2 points, so show it as a simple "criteria met" bar instead.

## 7. Quality bar
- Keyboard accessible: labels on every input, focus states.
- Mobile width 375 px works.
- No console errors.
- `npm --prefix app run build` passes, with the mock still lazily loaded (K3 set that up; keep it).
- **Honesty copy:** no "verified", "certified" or "expert-approved" wording for composed cases.

## 8. Verification
1. Mock mode (`npm --prefix app run dev:mock`): run the full wizard for an image, a video and an audio file (use small local files, e.g. from `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\var\kiro\media\`).
2. If K6 is merged by the time you finish, also run against the real service (`uvicorn` + `npm --prefix app run dev`) for one image upload. Otherwise state that real-service testing is pending.
3. Take screenshots of steps 1, 3 and 5 for each modality into `screenshots/runs/<UTC timestamp>/`, following `screenshots/README.md`.
4. Run `<py> .github/scripts/check_contract_parity.py`.

## 9. Acceptance
- The wizard works in mock mode for all three modalities, and against the real service if K6 is available.
- The build passes; parity passes.
- Screenshots captured. Report: `docs/kiro/reports/K8-REPORT.md`.
