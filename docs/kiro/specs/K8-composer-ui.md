# K8: Composer UI — "Create a new skill" wizard over the universal pipeline

Read `docs/kiro/specs/00-COMMON.md` first, then **`docs/plans/universal-pipeline.md`** (especially §2, §4, §5, §8) and the compose endpoints in `docs/kiro/specs/K6-composer-backend.md` §4. Folder `...\anveshan-wt\k8-composer-ui`, branch `kiro/k8-composer-ui`; created from `m1/hero-cases` **after K3 is merged** (K3 owns `app/` until then). K6/K7 may not be merged yet: **build against the mock first**, then test against the real service if available.

## 1. Files you own
`app/**`. Keep `app/src/types/contracts.ts` unchanged (CI parity).

## 2. Read first (in the worktree)
- `app/src/api/client.ts`, `types.ts`, `mock.ts`, `mock/*`, `runtime.ts`
- `app/src/App.tsx` and the hero views (`grep -rl "HeroSourceView\|HeroPracticeView" app/src`)
- `DESIGN.md`
- **Field names to mirror exactly in TypeScript** (case data, not contracts): `tracks/common/profile.py` (CaseProfile v2, ProbeFacts, IntakeResult), `tracks/common/skill_model.py` (SkillModel, TargetProperty, Step, Constraint, Check, Relevance), `tracks/common/perception.py` (Segment, Observation).

## 3. API client (`client.ts` + `types.ts`)
1. Add TypeScript interfaces mirroring the Python models above, one interface per class, same field names, optional where Python has a default or `Optional`.
2. Add `DraftView`:
   `{draft_id, probe, intake, proposal: CaseProfile | null, refused: boolean, refusal_message: string | null, warnings: string[], structure_labels: Record<string,string>, specialist_labels: Record<string,string>, perception: {segments: Segment[], observations: Observation[]}}`.
3. Add these functions:
   - `analyzeSource(file, {title?, description?, rightsConfirmed}, onProgress?) → DraftView` (multipart: `file`, `title`, `description`, `rights_confirmed` = "true"/"false"; endpoint `POST /api/compose/analyze`)
   - `getDraft(id) → DraftView` (`GET /api/compose/{id}`)
   - `refineDraft(id, {title, description}) → DraftView` (`POST /api/compose/{id}/refine`)
   - `createFromDraft(id, edits) → CaseView` (`POST /api/compose/{id}/create`). `edits = {title, skill_summary, domain, transmission_mode, learner_input_kinds, goal_hint, skill_model}`.
4. `CaseView` gains `profile?: CaseProfile | null`; list items gain `composed?: boolean`, `structures?: string[]`.

## 4. Mock backend (`app/src/api/mock/composer.ts`)
Canned responses, clearly SYNTHETIC, chosen by the upload's MIME type and file name:

| Upload | Response |
|---|---|
| image (normal) | proposal with structures `["final_state"]`, specialists `["line_art"]`, 4 properties, 2 suggested build steps, 1 constraint (keep=false), checks CHK-FS-SIM, CHK-FS-P01..P03, CHK-LA-* (3) |
| image named `*refuse*` | `refused: true`, message from the teachability refusal |
| video | `["procedure"]`, 5 steps (one critical), checks CHK-PR-COV/ORD/OFF/FIN/Q01, plus 5 segments with keyframes (use generated SVG data URLs) |
| audio named `*speech*` | `["utterance"]`, transcript "namaste, how are you", checks CHK-UT-TXT / CHK-UT-PACE |
| other audio | `["temporal_pattern"]` with rhythm checks |
| any file named `*unclear*` | `proposal: null` with the warning "Tell us what skill this is…" → `refineDraft` returns a proposal |

`createFromDraft` returns a CaseView whose `goal.modality === "universal"` and `goal.ui_view = {structures, steps, goal_state, checks, reference_assets}`, with `case_id` = `<slug>~<12 hex>`. Simulated latency: analyze 4 s, refine 2 s, create 3 s.

## 5. The wizard (`app/src/components/composer/`)
Entry points:
- a prominent **"Create a new skill"** card in Discovery;
- a **"Your skills"** section listing `composed: true` cases, with badges UPLOAD and the structures;
- route `?view=composer` (follow how `App.tsx` switches views).

**Step 1 — Upload.**
- Drop zone accepting `image/*,video/*,audio/*`.
- Optional "What is this skill?" (≤ 60) and "What should a learner achieve?" (≤ 300).
- Required rights checkbox.
- Client guards: ≤ 30 MB; video 8–120 s; audio 3–60 s (HTMLMediaElement `loadedmetadata`); image short side ≥ 64 px.
- Preview the file.

**Step 2 — Perceiving.** Progress with stage text: "Measuring the file → Looking and listening (AI) → Structuring the skill". Show elapsed time and "usually 10–40 s".

**Step 3a — Refused.** If `refused`: show `refusal_message`, the intake reasons, and "Try another file". No way to continue.

**Step 3b — Needs your input.** If `proposal === null`: show the warning, the teachability reason and what the AI thinks it is (`intake.skill_kind`). Title and description fields are required, then call `refineDraft`.

**Step 3c — Proposal (the key screen).** Three columns, or stacked on mobile:
1. **"What we measured" (OBSERVED).** Probe facts and metrics; the structures/specialists availability list with ✓/✗ and `probe.reasons`; the intake safety decision and notices (e.g. the identifiable-faces notice).
2. **"What the AI perceived" (INFERRED).**
   - Image: the source with property regions drawn as boxes (from `goal_state[].region` or the observation segment regions).
   - Video: a strip of segment keyframes with each step's name and times.
   - Audio: an onset timeline (if any) and the transcript.

   Every item is labelled INFERRED.
3. **"How we'll teach and check it" (editable SkillModel).**
   - Title, summary, domain.
   - Structures as read-only chips with their labels.
   - **Goal properties:** each with a keep toggle and editable text.
   - **Steps:** editable names, a "critical" toggle, and a "suggested (inferred)" vs "demonstrated" badge from `source_established`.
   - **Constraints:** keep toggles.
   - **Checks table:** enabled toggle, name, observable indicator, weight (1–5), required toggle, method badge (MEASURED for deterministic/specialist, AI-JUDGED for model_status).
   - Learner input kinds: checkboxes limited to the allowed kinds (union of the structures' kinds; "trace" only if `specialists` has `line_art`).

   Validation: at least one enabled check; at least one learner kind; no empty names. Buttons: "Create skill" and "Start over".

**Step 4 — Building.** Call `createFromDraft` with progress. On error, show the category and message and return to 3c with the edits kept.

**Step 5 — Done.** Navigate to the source view for the new case.

## 6. Rendering `universal` cases (generic views)
`goal.modality === 'universal'` (use `goal.ui_view` and `profile.skill_model`):
- **Source view:**
  - the reference media: `/api/media/{case_id}/{source_id}` for the source, `/api/media/{case_id}/goal/{asset}` for keyframes;
  - property boxes / step strip / transcript;
  - the claims list with certainty badges;
  - the review panel (existing);
  - the banner "Composed skill · AI-perceived elements are inferred until reviewed".
- **Practice:** upload controls for each allowed learner kind. If "trace" is allowed, reuse the existing `KolamCanvas` with the line_art `ui_view` (the dots/curves come from `profile.skill_model.specialists.line_art`).
- **Results:**
  - reuse the criterion table, feedback and progress curve;
  - for a procedure: a step-alignment strip (expected steps vs observed, from `trajectory.artifacts.frame_labels`);
  - for final_state image attempts: side-by-side source vs attempt with regions;
  - badges MEASURED vs AI-JUDGED per criterion, by matching the criterion id `CRIT-U-<check_id>` to the check's method.
- **Relevance refusals:** an attempt upload rejected with INVALID_INPUT "doesn't look like an attempt…" is shown as a friendly inline message on the practice screen. Don't treat it as a crash, and don't count it as an attempt.

## 7. Quality bar
- Accessible labels, keyboard navigation, focus states.
- 375 px width works.
- No console errors.
- The mock stays lazily loaded (the K3 setup).
- `npm --prefix app run build` passes; no chunk over 500 kB.
- Honest copy only: no "verified" or "certified" wording.

## 8. Verification
1. Mock mode: run all mock scenarios from §4 (image, refuse, unclear → refine, video, speech audio, rhythm audio) end to end, through practice on at least the image case.
2. Real service, if K6 and K7 are merged: one image upload end to end. Otherwise state that it's pending.
3. Screenshots of steps 1, 3a, 3b, 3c and 5, plus a universal results screen, into `screenshots/runs/<UTC timestamp>/`, following `screenshots/README.md`.
4. `<py> .github/scripts/check_contract_parity.py` passes.

## 9. Acceptance
- All mock scenarios work; real-service status reported.
- Build and parity pass; screenshots captured.
- Report: `docs/kiro/reports/K8-REPORT.md`.
