# K3 App ↔ Real Service Integration — Implementation Plan

Worktree: `c:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan-wt\k3-app`
Branch: `kiro/k3-app`
Frozen file: `app/src/types/contracts.ts` — never touch.
No `.env` in worktree → skip all live Origami builds. Kolam and Tabla use `recorded` mode (deterministic).

---

## Shape Mismatch Analysis (sourced from reading actual Python + TypeScript code)

### Mismatch 1 — CaseHandoff.to_view() extra fields
**Confirmed from `track_a/api.py CaseHandoff.to_view()`.**
Real service returns four fields absent from the TypeScript `CaseView` interface:
`manifest` (raw manifest dict), `observers` (observer/band config), `versions` (artifact version map),
`lesson` (structured teaching outline). These are additive and don't crash the app (JSON extras are
silently ignored at runtime), but the TypeScript types are incomplete.

### Mismatch 2a — Kolam `ui_view.curves` — BREAKING
**Confirmed from `tracks/common/goals/kolam.py ui_view()`.**
Real service produces `curves` as **objects**:
```json
[{"id": "C1", "closed": true, "points": [[x,y],...], "stages": [{"id": "C1.S1", "start": 0, "end": 144}]}]
```
TypeScript `KolamUiView.curves` is typed `number[][][]` (plain array of point arrays).

**Crash sites:**
- `KolamCanvas.tsx` line ~26: `for (const c of ui.curves) { c.forEach((p,i) => ...) }` — iterates
  the object's string keys, not points → console error / blank canvas.
- `KolamFigure.tsx` line ~52: `pathOf(c)` where `pathOf` does `pts.map(...)` — same crash.

Real service also adds `curve_count: number` and `rotation_order: number` at top level and has
**no `symmetry` object**. The TypeScript `KolamUiView.symmetry` is an assumption that is absent
from the real output. `KolamFigure.tsx` accesses `ui.symmetry?.rotational_order` — returns
`undefined` with real service, so symmetry guide lines won't render (degraded, not crashing).

Real service has **no `target_source_id`**. `KolamCapture` does
`ui.target_source_id ?? view.goal.source_ids[0]` — falls back correctly. Not a crash.

### Mismatch 2b — Tabla `ui_view.beats` field names — BREAKING
**Confirmed from `tracks/common/goals/tabla.py ui_view()`.**
Real service:
```json
"beats": [{"i": 0, "t": 0.500, "bass": true}]
```
Mock / TypeScript `TablaBeat`: `{ index: number; time_sec: number; bass: boolean; strength?: number }`

**Crash sites in `BeatTimeline.tsx`:**
- `b.index % cycle` → `b.index` is `undefined` → `NaN`, no cycle markers drawn.
- `x(b.time_sec)` → `b.time_sec` is `undefined` → every beat drawn at x=0 (NaN).
- `focusBeat === b.index` → always false.

Real service also has:
- `stroke_pulse_sec` instead of `period_sec` (TypeScript `TablaUiView.period_sec`) — `TablaSourcePanel`
  shows `undefined` for period.
- `cycle_length_pulses` + `cycle_length_beats` instead of `cycle_length` — `BeatTimeline` gets
  `ui.cycle_length ?? 0 = 0`, disables cycle markers.
- `source_id` absent — `TablaSourcePanel` correctly falls back to `source_ids[0]`.
- New top-level fields not in TypeScript: `strokes`, `bols`, `bols_status`, `tolerances`,
  `strokes_per_min`, `beat_pulses`, `window_sec`.

### Mismatch 2c — Origami `ui_view.window` field name — minor type mismatch
**Confirmed from `tracks/common/goals/origami.py ui_view()`.**
Real service: `"window": [0, 240]`. TypeScript `OrigamiUiView`: `window_sec?: number[]`.
No consuming component reads `ui.window_sec`, so not a runtime crash. Also:
- Real service has `kind: "origami_video"`, `final_state_index`, `key_state_index` — additive.
- States have extra `label: "R0"` field — additive.
- `source_id` absent — `OrigamiSourcePanel` correctly falls back to `source_ids[0]`.

### Mismatch 3a — Kolam `trajectory.artifacts` shape — type mismatch
**Confirmed from `tracks/track-b/src/track_b/evaluators/kolam.py`.**
Real evaluator produces:
```json
{"per_stroke": [...], "stage_completion_order": {...}, "tau_px": 6.0}
```
Mock produces: `{ off_path_strokes: number[], per_curve_coverage: number[] }`.
TypeScript `TrajectoryArtifacts.off_path_strokes` is absent from real output.
No current UI component reads `artifacts.off_path_strokes` directly. Not immediately crashing but types
are wrong. The real divergence events (kind `"off_path_ink"`) are in `trajectory.events`, which the
`AttemptResultView` already renders correctly.

### Mismatch 3b — Tabla `trajectory.artifacts.alignment` field names — type mismatch
**Confirmed from `tracks/track-b/src/track_b/evaluators/tabla.py`.**
Real evaluator `artifacts.alignment` is **matched-pairs-only**:
```json
[{"goal": 0, "learner": 0, "goal_t": 0.50, "learner_t": 0.48, "dev_ms": -20.1,
  "bass_goal": true, "bass_learner": true, "bass_ok": true, "on_time": true}]
```
Missing and extra strokes are in separate `artifacts.missing` and `artifacts.extra` arrays.
TypeScript `TablaAlignmentRow` expects: `{goal_index, goal_time_sec, learner_time_sec, deviation_ms, status, bass_expected, bass_played}` — all field names differ.
**Not immediately crashing** because no current component passes `trajectory.artifacts.alignment` to `BeatTimeline`. The `BeatTimeline` alignment prop is wired up in neither `SourcePanels.tsx` nor `HeroPracticeView.tsx` yet.

### Mismatch 3c — Origami `trajectory.artifacts.frame_labels` field name — type mismatch
**Confirmed from `tracks/track-b/src/track_b/evaluators/origami.py to_result()`.**
Real: `frame_labels[*] = {"t": ..., "raw": stateLabel, "filtered": stateLabel, "note": ""}`.
TypeScript `OrigamiFrameLabel`: `{ t: number; state: ...; note?: string }` — `state` vs `raw`/`filtered`.
No current UI component reads `frame_labels[*].state` directly. Not immediately crashing.

### Mismatch 4 — 1-based vs 0-based indices — VERIFIED NOT A MISMATCH
**Confirmed by reading all three evaluators.**
- Kolam: all positions are in seconds (float). No index-base issue.
- Origami: positions are seconds, state indices 0-based in both.
- Tabla: all divergence event positions are in seconds (`position_kind: "time"`); beat indices are
  0-based in the real service and in the mock's `TablaBeat.index`.

**One related issue:** Mock tabla uses `position_kind: 'beat'` for divergence events; real evaluator
uses `position_kind: 'time'`. This changes how `fmtPosition()` formats the position in
`AttemptResultView`. **Mark as "verify at runtime" during step 2.**

### Mismatch 5 — transition-kind names and targeted_change field names — BREAKING
**Confirmed from `tracks/track-b/src/track_b/compare.py` vs `app/src/api/mock/builders.ts`.**

**a. Transition names:**
Real `compare.py` uses `"observability_gain"` and `"observability_loss"` (no trailing 'd'/'d').
Mock `builders.ts transitionKind()` returns `"observability_gained"` and `"observability_lost"`.
`HeroTransmissionView.tsx TRANSITION_TONE` map keys contain `observability_gained`/`observability_lost`
→ real transitions fall through to `undefined` → Badge renders with `'muted'` tone (no colour).

**b. targeted_change field names:**
Real `compare_attempts()` returns:
```json
{"criterion_id": "...", "before": "not_satisfied", "after": "satisfied", "changed": true, "improved": true}
```
Mock `buildSessionResult` produces:
```json
{"criterion_id": "...", "baseline_status": "...", "retry_status": "...", "changed": true, "kind": "improved"}
```
`HeroTransmissionView.tsx` reads `tc.baseline_status`, `tc.retry_status`, `tc.kind` → all `undefined`
with real service → targeted-change panel shows no status badges and wrong text.

### Mismatch 6 — Exactly 2 attempts per session — VERIFIED NOT A MISMATCH
**Confirmed from `tracks/track-b/src/track_b/session.py` and `api.py`.**
- Real service allows more than 2 attempts (only blocks COMPLETED + BASELINE_EVALUATED state).
- `complete_session` requires `state == RETRY_EVALUATED and len >= 2`.
- After attempt 1 (baseline), state always becomes `FEEDBACK_READY` (feedback is always built for
  baseline).
- After attempt 2 (retry), state = `RETRY_EVALUATED`. App's `complete_session` call succeeds.
- App's `canSubmit = n < 2` hard-code is intentional and works correctly with the service.

---

## Implementation Plan

### Step 0 — Install and preflight
- [ ] 0. Run `npm --prefix app install` to restore node_modules.
      Verify the `app/package.json` scripts exist (`build`, `dev`, `dev:mock`).
      Files: none (install only)
      Verify: `npm --prefix app run build:mock` should produce `app/dist/` with no TypeScript errors
      (may have chunk-size warnings at this stage — acceptable; we fix that in step 7).

---

### Step 1 — Build Kolam and Tabla cases (recorded mode, no API key)
- [ ] 1. Fetch media, then build Kolam and Tabla using the Python venv. Skip Origami entirely.

      **Fetch media** (run once; copies licensed media into gitignored cache):
      ```
      C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe tools\fetch_media.py --from-dir C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\var\scratch\media
      ```
      (If the source dir is absent, ask Jim for the media location before proceeding.)

      **Build Kolam** (deterministic, no API key):
      ```
      C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe -c "
      import os, sys
      sys.path.insert(0, 'tracks/track-a/src'); sys.path.insert(0, 'tracks/track-b/src'); sys.path.insert(0, 'service')
      os.environ.setdefault('ANVESHAN_MODE', 'recorded')
      from pathlib import Path
      from tracks.common.runtime import RunContext
      from track_a.api import build_case
      cdir = Path('tracks/cases/kolam')
      ctx = RunContext.create(cdir, Path('var/data'), 'recorded')
      h = build_case(cdir, ctx)
      print('Kolam built:', h.versions)
      "
      ```
      Expected output: `Kolam built: {'knowledge_package': 1, ...}` (version numbers may vary).

      **Build Tabla** (deterministic, no API key):
      Same command substituting `tracks/cases/tabla`.

      **Do NOT run build_case for origami** — it requires live API calls. Skip and leave
      the origami case unbuilt. The app flow for Origami is accepted to reach "evaluating" state only.

      Files: none committed (artifacts go into `var/data/`, gitignored).
      Verify: `GET /api/cases/kolam` and `GET /api/cases/tabla` return `200` with a `goal.ui_view`
      containing real geometry.

---

### Step 2 — Run service and app, confirm real JSON shapes
- [ ] 2. Start the service, start the dev-proxy app, and capture real API responses to compare with mocks.

      **Start service** (in a separate terminal, keep running throughout K3):
      ```
      C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe -m uvicorn anveshan_service.main:app --app-dir service --port 8080
      ```
      **Start app with real service proxy:**
      ```
      npm --prefix app run dev
      ```
      Then in a browser or curl, capture:
      - `GET http://localhost:5173/api/cases/kolam` → save full JSON to a scratch file
      - `GET http://localhost:5173/api/cases/tabla` → save full JSON
      - `GET http://localhost:5173/api/health` → verify service mode

      Cross-check the real `goal.ui_view` shapes against the analysis in this plan's mismatch
      section. Specifically confirm:
      - Kolam: `curves` are objects `{id, closed, points, stages}` ✓
      - Tabla: `beats` use `i`/`t` keys ✓
      - Tabla: `cycle_length_pulses` present, no `cycle_length` ✓
      - All mismatches 2a–5 above are confirmed (or note any surprises)

      Also record (for step 4's mock replacement):
      - The full `goal.ui_view` JSON for kolam (the real builder geometry replaces the hand-approx mock)

      Files: none (this is investigation).
      Verify: No step verification — this is an investigation step. Record findings before proceeding.

---

### Step 3 — Fix shape mismatches: types, components, mocks

All fixes are applied together in dependency order. `app/src/types/contracts.ts` is NEVER touched.

- [ ] 3a. **Fix Kolam curves type and consumption** (BREAKING — fix first)

      **`app/src/api/types.ts`:**
      - Add new interfaces:
        ```typescript
        export interface KolamCurveStage { id: string; start: number; end: number; }
        export interface KolamCurveObj {
          id: string;
          closed: boolean;
          points: number[][];  // [x, y] pairs in goal-image pixels
          stages: KolamCurveStage[];
        }
        ```
      - Change `KolamUiView.curves` from `number[][][]` to `KolamCurveObj[]`.
      - Add fields present in real service but absent from the type:
        ```typescript
        curve_count?: number;
        rotation_order?: number;  // at top level (real service); replaces symmetry.rotational_order
        kind?: string;            // "kolam"
        ```
      - Keep `symmetry?: {...}` optional for backward compat with mock until mock is updated in step 4.
      - Keep `target_source_id?: string` optional (falls back to source_ids[0]).
      - Add `id?: string` to `KolamDot` (real service includes it; additive).

      **`app/src/hero/kolam/KolamCanvas.tsx`:**
      - Change the curve drawing loop from:
        ```typescript
        for (const c of ui.curves) {
          ctx.beginPath();
          c.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
          ctx.stroke();
        }
        ```
        to:
        ```typescript
        for (const c of ui.curves) {
          const pts = (c as KolamCurveObj).points ?? (c as unknown as number[][]);
          ctx.beginPath();
          pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
          ctx.stroke();
        }
        ```
        (The `?? (c as unknown as number[][])` fallback handles any remaining legacy shapes safely
        during the transition period.)

      **`app/src/hero/kolam/KolamFigure.tsx`:**
      - Update the `showCurves` map from:
        ```typescript
        ui.curves.map((c, k) => (
          <path key={k} d={pathOf(c)} .../>
        ))
        ```
        to:
        ```typescript
        ui.curves.map((c, k) => {
          const pts = (c as KolamCurveObj).points ?? (c as unknown as number[][]);
          return <path key={k} d={pathOf(pts)} .../>;
        })
        ```
      - Update `center` fallback to use `ui.symmetry?.center ?? [W/2, H/2]` (unchanged — keep
        working with both old and new symmetry shapes).
      - Add `rotation_order` reading: where `order` is set, change to:
        ```typescript
        const order = ui.rotation_order ?? ui.symmetry?.rotational_order ?? 0;
        ```

      Files: `app/src/api/types.ts`, `app/src/hero/kolam/KolamCanvas.tsx`, `app/src/hero/kolam/KolamFigure.tsx`
      Verify: `npm --prefix app run build:mock` passes. With mock, canvas draws 8 loops. With real
      service, canvas draws curves from real geometry.

- [ ] 3b. **Fix Tabla beat field names** (BREAKING)

      **`app/src/api/types.ts`:**
      - Update `TablaBeat` interface to match real service:
        ```typescript
        export interface TablaBeat {
          i: number;           // was: index
          t: number;           // was: time_sec
          bass: boolean;
          strength?: number;   // present in strokes, not in beats
          // Legacy aliases (kept optional for mock transition; remove after step 4)
          index?: number;
          time_sec?: number;
        }
        ```
      - Update `TablaUiView`:
        - Remove `period_sec` (not in real service); add `stroke_pulse_sec?: number`
        - Remove `cycle_length` (not in real service); add `cycle_length_pulses?: number; cycle_length_beats?: number`
        - Remove `source_id` (not in real service; consuming code already falls back to `source_ids[0]`)
        - Add new real-service fields:
          ```typescript
          modality?: string;
          window_sec?: number[];
          strokes_per_min?: number;
          stroke_pulse_sec?: number;
          beat_pulses?: number;
          cycle_length_pulses?: number;
          cycle_length_beats?: number;
          strokes?: Array<{ i: number; t: number; bass: boolean; strength: number }>;
          bols?: unknown;
          bols_status?: string;
          tolerances?: { timing_ms: number; tempo_pct: number };
          ```

      **`app/src/hero/tabla/BeatTimeline.tsx`:**
      - Replace all `b.index` with `b.i ?? b.index ?? 0`
      - Replace all `b.time_sec` with `b.t ?? b.time_sec ?? 0`
      - Replace `ui.cycle_length ?? 0` with `(ui.cycle_length_pulses ?? (ui as {cycle_length?: number}).cycle_length ?? 0)`
      - Replace `(ui.duration_sec ?? ...)` — no change needed, field exists in both

      **`app/src/hero/SourcePanels.tsx TablaSourcePanel`:**
      - Replace `{ui.period_sec && <span>period <b>{Math.round(ui.period_sec * 1000)} ms</b></span>}` 
        with `{(ui.stroke_pulse_sec ?? (ui as {period_sec?: number}).period_sec) && ...}`
      - Replace `{ui.cycle_length && ...}` with `{(ui.cycle_length_pulses ?? (ui as {cycle_length?: number}).cycle_length) && ...}`

      **`app/src/hero/HeroPracticeView.tsx TablaCapture`:**
      - The footer text `Source: {ui.tempo_bpm ?? '?'} BPM · {ui.cycle_length ?? '?'}-beat cycle · ...`
        → replace `ui.cycle_length` with `ui.cycle_length_pulses ?? (ui as {cycle_length?: number}).cycle_length`

      Files: `app/src/api/types.ts`, `app/src/hero/tabla/BeatTimeline.tsx`,
             `app/src/hero/SourcePanels.tsx`, `app/src/hero/HeroPracticeView.tsx`
      Verify: `npm --prefix app run build:mock` passes. Source beat timeline displays in mock mode.

- [ ] 3c. **Fix targeted_change and transition-kind names** (BREAKING for transmission view)

      **`app/src/api/types.ts`:**
      - Update `TargetedChange` interface:
        ```typescript
        export interface TargetedChange {
          criterion_id?: string | null;
          before?: CriterionStatus | string | null;    // real service field (was: baseline_status)
          after?: CriterionStatus | string | null;     // real service field (was: retry_status)
          changed?: boolean;
          improved?: boolean;                          // real service field (was: kind string)
          // Legacy aliases — optional for mock transition
          baseline_status?: CriterionStatus | null;
          retry_status?: CriterionStatus | null;
          kind?: string;
          [key: string]: unknown;
        }
        ```

      **`app/src/hero/HeroTransmissionView.tsx`:**
      - Fix `TRANSITION_TONE` map keys:
        ```typescript
        const TRANSITION_TONE: Record<string, ...> = {
          improved: 'emerald',
          regressed: 'crimson',
          observability_gain: 'cyan',    // was: observability_gained
          observability_gained: 'cyan',  // keep legacy for mock compat until step 4 mock fix
          observability_loss: 'amber',   // was: observability_lost
          observability_lost: 'amber',   // keep legacy
          unchanged: 'muted',
        };
        ```
      - Update targeted-change panel to read both old and new field names:
        ```typescript
        const bStatus = tc.before ?? tc.baseline_status;
        const aStatus = tc.after ?? tc.retry_status;
        const tcKind = tc.improved !== undefined
          ? (tc.improved ? 'improved' : 'unchanged')
          : (tc.kind ?? 'changed');
        ```
        Replace all `tc.baseline_status`, `tc.retry_status`, `tc.kind` usages with these vars.

      **`app/src/api/mock/builders.ts`:**
      - Fix `transitionKind()` return values:
        ```typescript
        if (a === 'uncertain' && b !== 'uncertain') return 'observability_gain';   // was: observability_gained
        if (a !== 'uncertain' && b === 'uncertain') return 'observability_loss';   // was: observability_lost
        ```
      - Fix `buildSessionResult targetedChange`:
        ```typescript
        targeted_change: {
          criterion_id: targetId,
          before: tb,              // was: baseline_status
          after: tr,               // was: retry_status
          changed: tb !== tr,
          improved: targetId ? (RANK[tr!] > RANK[tb!]) : false,  // was: kind
          // keep legacy aliases for any existing code
          baseline_status: tb,
          retry_status: tr,
          kind: targetId ? transitionKind(tb ?? undefined, tr ?? undefined) : 'none',
        }
        ```

      Files: `app/src/api/types.ts`, `app/src/hero/HeroTransmissionView.tsx`, `app/src/api/mock/builders.ts`
      Verify: `npm --prefix app run build:mock` passes.

- [ ] 3d. **Fix remaining type mismatches** (not currently crashing, correctness)

      **`app/src/api/types.ts`:**
      - Update `CaseView` to add optional extra fields from real service:
        ```typescript
        manifest?: Record<string, unknown>;
        observers?: Record<string, unknown>;
        versions?: Record<string, number>;
        lesson?: Record<string, unknown>;
        ```
      - Update `OrigamiUiView`:
        - Rename `window_sec?: number[]` to `window?: number[]` (real field is `window`)
        - Keep both for compat: add `window?: number[]; window_sec?: number[];`
        - Add `kind?: string; final_state_index?: number; key_state_index?: number | null`
      - Update `OrigamiState`: add `label?: string`
      - Update `TablaAlignmentRow` to reflect real service field names (field names in real service
        artifacts differ from TypeScript type; update for type correctness even though not yet consumed):
        ```typescript
        export interface TablaAlignmentRow {
          // Real service fields (from track_b/evaluators/tabla.py):
          goal?: number | null;           // matched goal stroke index (0-based)
          learner?: number | null;        // matched learner stroke index (0-based)
          goal_t?: number | null;         // goal stroke time (window-relative seconds)
          learner_t?: number | null;      // learner stroke time (seconds)
          dev_ms?: number | null;         // deviation in ms
          bass_goal?: boolean | null;     // bass flag in goal
          bass_learner?: boolean | null;  // bass flag in learner
          bass_ok?: boolean | null;       // bass match
          on_time?: boolean | null;       // within tolerance
          // Legacy mock fields (kept optional):
          goal_index?: number | null;
          goal_time_sec?: number | null;
          learner_time_sec?: number | null;
          deviation_ms?: number | null;
          status?: 'ok' | 'late' | 'early' | 'missing' | 'extra' | string;
          bass_expected?: boolean | null;
          bass_played?: boolean | null;
        }
        ```
      - Update `OrigamiFrameLabel` to reflect real service:
        ```typescript
        export interface OrigamiFrameLabel {
          t: number;
          raw?: Label;        // real service field (was: state)
          filtered?: Label;   // real service field
          state?: Label;      // legacy mock field
          note?: string;
        }
        ```
      - Update `TrajectoryArtifacts`:
        - Add real Kolam artifact fields: `per_stroke?: unknown[]; stage_completion_order?: unknown; tau_px?: number`
        - Keep `off_path_strokes?: number[]` optional (present in mock, absent in real)

      Files: `app/src/api/types.ts`
      Verify: `npm --prefix app run build:mock` passes with zero TypeScript errors.

- [ ] 3e. **Update mock data to use real field names** (aligns mock with real shapes)

      **`app/src/api/mock/tabla.ts`:**
      - Update `TablaBeat` construction to use `i:` and `t:` (real names):
        ```typescript
        const beats: TablaBeat[] = Array.from({ length: 32 }, (_, i) => ({
          i,                                            // was: index
          t: Number((OFFSET + i * PERIOD).toFixed(3)), // was: time_sec
          bass: BASS16[i % 16] === 1,
          strength: i % 16 === 0 ? 1 : 0.7,
          // Keep legacy aliases for any remaining old code paths:
          index: i,
          time_sec: Number((OFFSET + i * PERIOD).toFixed(3)),
        }));
        ```
      - Update `tablaUiView`:
        ```typescript
        export const tablaUiView: TablaUiView = {
          beats,
          stroke_pulse_sec: PERIOD,    // was: period_sec
          tempo_bpm: 80,
          cycle_length_pulses: 16,     // was: cycle_length
          cycle_length_beats: 16,
          duration_sec: ...,
          // source_id removed (not in real service)
          // keep legacy aliases optional:
          period_sec: PERIOD,
          cycle_length: 16,
        };
        ```
      - Update `evaluateTabla` to emit `position_kind: 'time'` (real service) instead of `'beat'`
        for divergence events; use `b.t` for positions.
      - Update the `alignment` artifact to use real field names:
        ```typescript
        rows.push({
          goal: i, goal_t: b.t, learner_t: learnerT,
          dev_ms: status === 'missing' ? null : dev,
          bass_goal: b.bass, bass_learner: bassPlayed,
          bass_ok: bassPlayed === b.bass,
          on_time: status === 'ok',
          // keep legacy aliases:
          goal_index: i, goal_time_sec: b.t, learner_time_sec: learnerT,
          deviation_ms: ..., status, bass_expected: b.bass, bass_played: bassPlayed,
        });
        ```

      **`app/src/api/mock/origami.ts`:**
      - Update `frame_labels` in `evaluateOrigami` to use `raw`/`filtered` (real service field names):
        ```typescript
        labels.push({ t, raw: s, filtered: s, state: s, note: '' });
        ```
      - Update `origamiUiView` to add `window` field alongside legacy `window_sec`:
        ```typescript
        window: [0, 240],
        window_sec: [0, 240],  // keep for compat
        ```

      Files: `app/src/api/mock/tabla.ts`, `app/src/api/mock/origami.ts`
      Verify: `npm --prefix app run build:mock` passes; mock mode beat timeline still works.

---

### Step 4 — Replace hand-approximated Kolam mock geometry with real service output
- [ ] 4. Dump the real `GET /api/cases/kolam` response (captured in step 2) and replace the
      hand-approximated `kolamUiView` in `app/src/api/mock/kolam.ts` with the real builder output.

      **Procedure:**
      1. With service running, curl or fetch: `GET http://localhost:8080/api/cases/kolam`
      2. Extract `response.goal.ui_view` JSON — this is the real geometry (real dots, real curves
         as objects, real tau, real rotation_order).
      3. In `app/src/api/mock/kolam.ts`:
         - Replace the `kolamUiView` const with the real service output. Format it as a TypeScript
           object literal matching the now-corrected `KolamUiView` type (from step 3a).
         - Remove all hand-computation code (the `loop()`, `dots` derivation, `curves` derivation
           loops) ONLY if the real-service geometry fully replaces it.
         - Keep `KOLAM_TARGET_SOURCE` and `KOLAM_TARGET_URL` (still needed for media URL lookup).
         - Keep `evaluateKolamTrace` and `evaluateKolamImage` functions (still used for mock evaluation).
         - Update the `kolamCaseView()` function to embed the real `ui_view` data.
      4. Verify that the mock canvas and figure still render. The curves are now objects
         `{id, closed, points, stages}` — the fixes in step 3a make both mock and real work.

      Also dump `GET /api/cases/tabla` and update `tablaUiView` in `app/src/api/mock/tabla.ts`
      with the real beat/onset data (real `i`/`t` field names, real `cycle_length_pulses`, etc.).
      Do NOT replace the synthesised WAV — that is mock-mode specific.

      Files: `app/src/api/mock/kolam.ts`, `app/src/api/mock/tabla.ts`
      Verify: `npm --prefix app run dev:mock` — kolam source panel shows real dots and curves overlay.
      `npm --prefix app run build:mock` passes with zero TypeScript errors.

---

### Step 5 — Upload size guard (30 MB per file, 413 handling)
- [ ] 5. Add a client-side file size check before upload, and handle the server's 413 response.

      Cloud Run / service limit is 30 MB per request body (settings: `max_upload_bytes`).
      The service uses `BodyLimitMiddleware` and returns `{"error": {"category": "INVALID_INPUT", ...}}` on 413.

      **In `app/src/hero/HeroPracticeView.tsx`:**
      Add a size guard in the `submit` function before calling `api.submitAttempt`:
      ```typescript
      const MAX_UPLOAD_MB = 30;
      const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024;
      if (upload.file.size > MAX_UPLOAD_BYTES) {
        setErr(new Error(
          `File is ${(upload.file.size / 1e6).toFixed(1)} MB — limit is ${MAX_UPLOAD_MB} MB. ` +
          `For video, re-encode at a lower bitrate (e.g. ffmpeg -i input.mp4 -crf 28 out.mp4).`
        ));
        return;
      }
      ```
      Apply this guard in `KolamCapture` (photo upload), `OrigamiCapture` (video upload),
      and `TablaCapture` (audio upload) — add to the submit handler in each function.

      **In `app/src/api/client.ts` (or the error display component):**
      The `upload()` function already calls `toApiError` on non-2xx responses.
      The `ApiError` will carry category `INVALID_INPUT` and HTTP status 413.
      In the `ErrorNote` component (wherever it renders errors), ensure 413s display
      the server's error message, which includes the limit in bytes.

      Verify that the `ErrorNote` component in `HeroPracticeView.tsx` already calls
      `.message` on the `ApiError` (it does; `ApiError` extends Error). No further change needed
      for 413 display.

      Files: `app/src/hero/HeroPracticeView.tsx`
      Verify: Manually test uploading a file > 30 MB (or mock a size rejection). UI should show
      the error message without crashing. `npm --prefix app run build` must pass.

---

### Step 6 — Bundle hygiene: dynamic import for mock backend
- [ ] 6. Ensure the mock backend is loaded via dynamic `import()` only in mock mode, so it is
      excluded from the production chunk.

      Currently `app/src/api/client.ts` has:
      ```typescript
      import { mockApi } from './mock';  // static import — always in bundle
      ```
      This pulls all of `./mock/*.ts` into the production build.

      **Fix:**
      In `app/src/api/client.ts`, replace the static import with a lazy runtime assignment.
      Create a small helper that returns the mock API asynchronously:
      ```typescript
      // Remove: import { mockApi } from './mock';
      
      // Add at the top of client.ts:
      let _mockApi: typeof import('./mock').mockApi | null = null;
      async function getMockApi() {
        if (!_mockApi) {
          const m = await import('./mock');
          _mockApi = m.mockApi;
        }
        return _mockApi;
      }
      ```
      
      Since `client.ts` currently exports `const api = IS_MOCK ? mockApi : httpApi` as a
      synchronous constant, the mock API needs to be available synchronously on first access.
      The cleanest solution is to move mock routing to a Vite virtual module pattern or use
      `?mock` tree-shaking.

      **Simpler approach** (preferred for the hackathon): Move mock entirely to a separate
      entry that Vite only imports in mock mode. In `vite.config.ts` (or the equivalent
      config), use `define` or aliasing so that in non-mock builds, `./mock` resolves to a
      stub that throws. Check the existing Vite config first:

      Read `app/vite.config.ts` to see if there is already a mock-mode alias or if the
      `VITE_API_BASE` env drives this. If `VITE_API_BASE=mock` is the gate, a conditional
      `import.meta.env.VITE_API_BASE === 'mock'` in client.ts with a dynamic import
      may be sufficient. Implement the smallest approach that removes mock code from the
      production chunk.

      **Target:** Production build chunk for `client.ts` must not include mock file imports.
      Run `npm --prefix app run build` and verify:
      - No TypeScript errors.
      - No chunk larger than 500 kB (warn if any approach fails this).
      - Mock files are absent from the production `dist/assets/*.js` (check with `grep -l "SYNTHETIC" app/dist/assets/`).

      Files: `app/src/api/client.ts` (and possibly `app/src/api/runtime.ts`, Vite config)
      Verify: `npm --prefix app run build` succeeds; production bundle contains no mock strings.
      `npm --prefix app run build:mock` still works (mock mode is still functional).

---

### Step 7 — Honest labels: runtime class, source labels, package warnings
- [ ] 7. Verify all required labels are displayed; add any that are missing.

      **Runtime class label (LIVE / RECORDED_LIVE / DETERMINISTIC):**
      `AttemptResultView.tsx` already renders `<RuntimeClassBadge value={result.runtime_class} />`.
      Verify the `RuntimeClassBadge` component in `hero/ui.tsx` maps all three values to
      distinct visual treatments. No code change needed if already present.

      **Source / runtime label (INTERNET_REFERENCE / UPLOAD / SYNTHETIC):**
      `HeroPracticeView.tsx` already renders `<SourceLabelBadge label={view.runtime_label} />`.
      Verify it renders for cases with `runtime_label: 'UPLOAD'` and `'SYNTHETIC'`.

      **"Package not expert-approved" warning:**
      `HeroPracticeView.tsx` already shows:
      ```tsx
      {view.review_status !== 'approved' && <div>⚠ The knowledge package is "..."</div>}
      ```
      Verify this warning correctly fires for `review_status: 'pending'` (Kolam and Tabla
      after a first build). Add `'revised'` to the non-approved check if not already there.

      **UNCERTAIN reasons:**
      `AttemptResultView.tsx` already renders `r.deviation_analysis` when `status === 'uncertain'`.
      Real service returns this in `criterion_results[*].deviation_analysis`. Verify field name
      matches — the real `build_evaluation` sets this from scored results. If the field name differs
      between mock and real (`deviation_analysis` vs another name), fix `AttemptResultView.tsx`.

      **No copy may imply certification.** Scan the UI for any text that implies certification,
      validated learning, or expert approval beyond what the data says. Fix any such copy.
      The current "The transmission records that an attempt was evaluated; it is not a certification
      of skill" text is already present in `HeroTransmissionView.tsx` — verify it is displayed.

      Files: `app/src/hero/ui.tsx` (verify), `app/src/hero/HeroPracticeView.tsx` (verify),
             `app/src/hero/results/AttemptResultView.tsx` (verify)
      Verify: Walk through a full kolam or tabla hero flow in dev mode. Check all warning badges
      appear. `npm --prefix app run build` passes.

---

### Step 8 — Full integration walk-through against the real service
- [ ] 8. Run the full hero case flow with the real service (no mock). Fix any runtime errors found.

      **Kolam flow:**
      1. `GET /api/cases/kolam` loads, source panel shows real dots and curves.
      2. Start session, draw on the canvas (a decent and a sloppy attempt).
      3. Verify baseline result: trajectory curve, events, criteria, first divergence display.
      4. Verify retry result and transmission view.
      5. Also test photo upload for kolam.
      6. Check browser console: zero uncaught errors.

      **Tabla flow:**
      1. `GET /api/cases/tabla` loads, beat timeline shows real beats.
      2. Upload a WAV (generate with `tracks/track-b/eval/tabla/make_synthetic.py` into `var/eval/tabla/`).
      3. Verify baseline result and retry flow.
      4. Check console: zero uncaught errors.

      **Origami flow (up to "evaluating" only — no live build):**
      1. `GET /api/cases/origami` — this will fail or return an unbuilt case.
         If the case returns a replay bundle (SYNTHETIC), verify the UI handles missing `goal` gracefully.
         If it 404s, verify the error is shown without crashing.
      2. No video upload attempt is needed — Origami without a live build cannot be fully evaluated.

      For every console error or shape mismatch found during walk-through, fix it in this step.
      Document each fix in the report.

      Also verify:
      - Position display: tabla divergence events show `position_kind: 'time'` formatted as seconds
        (e.g. "at 3.42s"), not as "beat 6". Confirm `fmtPosition()` in `hero/locators.ts` handles this.
      - `targeted_change`: the "Targeted change" panel in transmission view shows status badges correctly.
      - `observability_gain`/`observability_loss` transitions show `'cyan'`/`'amber'` badges, not `'muted'`.

      Files: Various — fix any runtime errors discovered.
      Verify: All hero flows work with no console errors. Walk-through confirms all 6 mismatches
      are resolved.

---

### Step 9 — Acceptance checks
- [ ] 9. Run all acceptance checks and fix any failures.

      **TypeScript + Vite build:**
      ```
      npm --prefix app run build
      ```
      Must pass with zero TypeScript errors. No chunk > 500 kB (check output).

      **Contract parity check:**
      ```
      C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe .github/scripts/check_contract_parity.py
      ```
      Must pass. This verifies `app/src/types/contracts.ts` matches `tracks/common/schemas/`.

      **Case pack and governance checks:**
      ```
      C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe .github/scripts/check_case_packs.py
      C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe .github/scripts/check_governance.py
      ```
      Both must pass.

      **Python test suite (non-live):**
      ```
      C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"
      ```
      Must be green (0 failures). Fix any failures before proceeding.

      Files: whatever tests reveal as broken.
      Verify: All commands above exit 0.

---

### Step 10 — Screenshots
- [ ] 10. Capture canonical screenshots using the automated audit script.

      With service running (`--port 8080`) and `npm --prefix app run dev` running:
      ```
      npm --prefix app run audit:devtools
      ```
      This captures the 15 canonical screens to `screenshots/runs/<UTC>/` and copies to
      `screenshots/latest/`, and appends to `screenshots/manifest.json`.

      The audit exits with code 0 only if:
      - Console errors = 0
      - Uncaught exceptions = 0
      - Failed network requests (404/500) = 0

      If it exits 1, inspect `screenshots/runs/<TIMESTAMP>/audit_report.json`, fix the
      reported issue, and re-run.

      Prioritise capturing at minimum:
      - `01_landing_discovery` — case list page
      - `02_source_grounding_kolam` — kolam source panel with real geometry
      - `03_adaptive_workspace_kolam` — kolam canvas
      - `04_first_divergence_modal` — result after a kolam attempt
      - `06_transmission_complete_kolam` — after completing a kolam session
      - `10_rhythm_workspace_tabla` — tabla source panel with real beats

      Files: `screenshots/runs/<TIMESTAMP>/`, `screenshots/latest/`, `screenshots/manifest.json`
      Verify: `npm --prefix app run audit:devtools` exits 0; manifest.json is updated.

---

### Step 11 — Write K3-REPORT.md and commit
- [ ] 11. Write the K3 report and create the final commit on `kiro/k3-app`.

      Write `docs/kiro/reports/K3-REPORT.md` covering:
      - List of all 6 candidate mismatches, their confirmed status, and the fix applied (or "verified not a mismatch").
      - Any additional mismatches discovered during step 2 or step 8 walk-through.
      - Test output summary (paste the pytest -q output, tsc output, build output).
      - Numbers: chunk sizes, test counts.
      - Open issues / decisions for Claude Code (e.g. Origami requires live build, any product decisions needed).
      - Screenshot run timestamp.

      Commit all changes:
      ```
      git -C c:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan-wt\k3-app add -A
      git -C c:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan-wt\k3-app commit -m "feat(k3): app-to-real-service integration — shape mismatches fixed, mock aligned"
      ```

      Then tell Jim: **"K3 complete — branch kiro/k3-app ready to merge"**

      Files: `docs/kiro/reports/K3-REPORT.md`
      Verify: `git -C c:\...\k3-app log --oneline -3` shows the new commit on `kiro/k3-app`.
      `git -C c:\...\k3-app status` shows a clean working tree.

---

## Summary Table of All Fixes

| # | Mismatch | Severity | Files Changed | Status |
|---|----------|----------|---------------|--------|
| 2a | Kolam `curves` type: objects vs `number[][][]` | **BREAKING** | `types.ts`, `KolamCanvas.tsx`, `KolamFigure.tsx`, `mock/kolam.ts` | Fix in step 3a + 4 |
| 2a | Kolam `rotation_order` vs `symmetry` object | Degraded | `types.ts`, `KolamFigure.tsx` | Fix in step 3a |
| 2b | Tabla `beats.i`/`t` vs `index`/`time_sec` | **BREAKING** | `types.ts`, `BeatTimeline.tsx`, `mock/tabla.ts` | Fix in step 3b |
| 2b | Tabla `stroke_pulse_sec` vs `period_sec` | Degraded | `types.ts`, `SourcePanels.tsx` | Fix in step 3b |
| 2b | Tabla `cycle_length_pulses` vs `cycle_length` | Degraded | `types.ts`, `BeatTimeline.tsx`, `HeroPracticeView.tsx` | Fix in step 3b |
| 2c | Origami `window` vs `window_sec` | Type only | `types.ts`, `mock/origami.ts` | Fix in step 3d |
| 3b | Tabla `TablaAlignmentRow` field names | Type only | `types.ts`, `mock/tabla.ts` | Fix in step 3d + 3e |
| 3c | Origami `OrigamiFrameLabel.raw` vs `state` | Type only | `types.ts`, `mock/origami.ts` | Fix in step 3d + 3e |
| 3a | Kolam artifacts `off_path_strokes` absent | Type only | `types.ts` | Fix in step 3d |
| 5a | `observability_gain` vs `observability_gained` | **BREAKING** | `HeroTransmissionView.tsx`, `mock/builders.ts` | Fix in step 3c |
| 5b | `targeted_change` field names (`before`/`after`/`improved`) | **BREAKING** | `types.ts`, `HeroTransmissionView.tsx`, `mock/builders.ts` | Fix in step 3c |
| 1 | `CaseView` missing `manifest`/`observers`/`versions`/`lesson` | Type only | `types.ts` | Fix in step 3d |
| 4 | 1-based vs 0-based indices | **NOT A MISMATCH** | — | Verified; note position_kind mismatch for runtime check |
| 6 | Exactly 2 attempts | **NOT A MISMATCH** | — | Verified; app limit aligns with service minimum |
| — | Hand-approx Kolam mock geometry | Quality | `mock/kolam.ts` | Replace in step 4 |
| — | Upload size guard (30 MB) | Feature | `HeroPracticeView.tsx` | Step 5 |
| — | Mock backend in production bundle | Quality | `client.ts` | Step 6 |
| — | Honest labels verification | Feature | `hero/ui.tsx` | Step 7 |
