# K3 Report — App ↔ Real Service Integration

**Branch:** `kiro/k3-app`  
**Date:** 2026-10-06  
**Worktree:** `c:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan-wt\k3-app`

---

## Summary

All 10 K3 steps executed. The app (`app/`) now speaks the same JSON shapes as the real service.
Shape mismatches have been fixed in `app/src/api/types.ts` and all consuming components.
Mock data now uses real field names with legacy aliases for backward compat.
Kolam mock geometry replaced with real builder output (GET /api/cases/kolam).
Upload size guard (30 MB) added. Mock excluded from production bundle.
Honest labels verified. 5 screenshots captured (mock mode). All acceptance checks pass.

---

## Step 1 — Build Cases (recorded mode)

**Commands run:**

```
# Media fetch
python tools\fetch_media.py --from-dir C:\...\anveshan\var\scratch\media
# → kolam/src.kolam.target.v1: ok; tabla/src.tabla.demo.v1: fetched; origami/src.origami.demo.v1: fetched

# Kolam build
python -c "... build_case('tracks/cases/kolam', ctx)"
# → Kolam built: {'knowledge_package': 1, 'practice_task': 1, 'criterion_map': 1, 'rubric': 1, 'observers': 1, 'goal_model': 1}

# Tabla build (after fix — see bug below)
python -c "... build_case('tracks/cases/tabla', ctx)"
# → Tabla built: {'knowledge_package': 1, 'practice_task': 1, 'criterion_map': 1, 'rubric': 1, 'observers': 1, 'goal_model': 1}
```

**Bug fixed:** `tracks/track-a/src/track_a/goals/tabla.py` hardcoded `modality=Modality.AUDIO` for
all evidence refs, but the tabla source is `video/webm`. The grounding check enforces that
`evidence.modality == source MIME major type`. Fix: derive modality from `source.mime_type` split.

Origami: skipped (no `.env` → no live API key → no live build).

---

## Step 2 — Real API shapes captured

Real shapes obtained by calling `load_case().to_view()` directly from Python:

### Kolam `goal.ui_view` (real service)
```json
{
  "kind": "kolam",
  "canvas": {"width": 492, "height": 499},
  "stroke_width": 3.65,
  "tau": 6.0,
  "curve_count": 1,
  "rotation_order": 8,
  "dots": [{"id": "D01", "x": 242.0, "y": 35.0, "r": 4.1, "relation": "on_line"}, ...],
  "curves": [{"id": "C1", "closed": true, "stages": [...], "points": [[x, y], ...]}]
}
```
Key findings: 1 curve (not 8 loops), `rotation_order` at top level (not in `symmetry`).

### Tabla `goal.ui_view` (real service)
```json
{
  "modality": "tabla_audio",
  "window_sec": [20.0, 32.0],
  "duration_sec": 12.0,
  "tempo_bpm": 158.5,
  "strokes_per_min": 317.0,
  "stroke_pulse_sec": 0.1893,
  "beat_pulses": 2,
  "cycle_length_pulses": 12,
  "cycle_length_beats": 6.0,
  "beats": [{"i": 0, "t": 1.5323, "bass": true}, ...],
  "bols_status": "audio_model_disabled",
  "tolerances": {"timing_ms": 50.0, "tempo_pct": 5.0}
}
```
Key findings: `i`/`t` field names (not `index`/`time_sec`), `stroke_pulse_sec` (not `period_sec`),
`cycle_length_pulses` (not `cycle_length`), no `source_id`.

### Top-level CaseView extra fields (real service)
Real service adds: `manifest`, `observers`, `versions`, `lesson`.

---

## Step 3 — Shape Mismatches Fixed

| # | Mismatch | Was | Fixed to | Files changed |
|---|----------|-----|----------|---------------|
| 2a | Kolam `curves` type | `number[][][]` | `KolamCurveObj[]` with `.points` fallback | `types.ts`, `KolamCanvas.tsx`, `KolamFigure.tsx` |
| 2a | Kolam `rotation_order` | in `symmetry.rotational_order` | top-level field + compat fallback | `types.ts`, `KolamFigure.tsx`, `SourcePanels.tsx` |
| 2b | Tabla beat field names | `index/time_sec` | `i/t` (with legacy aliases) | `types.ts`, `BeatTimeline.tsx`, `mock/tabla.ts` |
| 2b | Tabla `stroke_pulse_sec` | `period_sec` | `stroke_pulse_sec` + compat | `types.ts`, `SourcePanels.tsx` |
| 2b | Tabla `cycle_length_pulses` | `cycle_length` | `cycle_length_pulses` + compat | `types.ts`, `BeatTimeline.tsx`, `HeroPracticeView.tsx` |
| 2c | Origami `window` | `window_sec` only | added `window` field alongside | `types.ts`, `mock/origami.ts` |
| 3b | `TablaAlignmentRow` field names | `goal_index/goal_time_sec/...` | `goal/goal_t/...` (with aliases) | `types.ts`, `BeatTimeline.tsx`, `mock/tabla.ts` |
| 3c | `OrigamiFrameLabel` | `state` only | `raw`/`filtered` + `state` alias | `types.ts`, `mock/origami.ts` |
| 3a | Kolam artifacts | `off_path_strokes` only | added `per_stroke`, `tau_px` (real) | `types.ts` |
| 1 | `CaseView` extra fields | absent | `manifest`, `observers`, `versions`, `lesson` added optional | `types.ts` |
| 5a | Transition kind names | `observability_gained/lost` | `observability_gain/loss` + legacy compat | `HeroTransmissionView.tsx`, `mock/builders.ts` |
| 5b | `TargetedChange` fields | `baseline_status/retry_status/kind` | `before/after/improved` + aliases | `types.ts`, `HeroTransmissionView.tsx`, `mock/builders.ts` |
| 4 | 1-based vs 0-based | NOT A MISMATCH | verified; nota bene: mock used `position_kind: 'beat'`, real uses `'time'` → fixed mock to `'time'` | `mock/tabla.ts` |
| 6 | Exactly 2 attempts | NOT A MISMATCH | verified; app limit aligns with service minimum | — |

---

## Step 4 — Kolam Mock Geometry Replaced

Real builder geometry dumped from `load_case('tracks/cases/kolam').to_view()['goal']['ui_view']`.

- Dots: 41 (real builder) vs. 25 (hand-approximated). All have `id` field.
- Curves: 1 continuous path with 859 points (real) vs. 8 hand-approximated loops.
- Files: `app/src/api/mock/kolam-real-ui-view.json` (new), `app/src/api/mock/kolam.ts` (updated)
- `goalSamples` computation updated to handle `KolamCurveObj.points` fallback.
- `kolamCaseView` warning updated to reflect real builder geometry.

---

## Step 5 — Upload Size Guard

Added 30 MB pre-upload check in `KolamCapture`, `OrigamiCapture`, `TablaCapture`:
- Client-side check: `file.size > 30 * 1024 * 1024` disables submit button and shows error.
- Error message includes compression hint (ffmpeg for video, resize for images).
- `ErrorNote` already renders `ApiError.message` for HTTP 413 from service.

Files: `app/src/hero/HeroPracticeView.tsx`

---

## Step 6 — Bundle Hygiene

- **Mock alias:** `vite.config.ts` aliases `src/api/mock` → `src/api/mock-empty.ts` in non-mock builds.
  `mock-empty.ts` exports a Proxy stub that throws if called in production.
- **Manual chunks:** `vendor` (react/react-dom), `icons` (lucide-react) split out.
- **Result (production build):**
  - `index.js`: 349 kB (was 514 kB before chunking, and included mock code)
  - `vendor.js`: 133 kB
  - `icons.js`: 32 kB
  - All chunks < 500 kB ✓
- **Mock build:** mock code present, 372 kB ✓
- **Verified:** `grep "SYNTHETIC mock"` finds 0 matches in production `dist/assets/`.

Files: `app/vite.config.ts`, `app/src/api/mock-empty.ts`

---

## Step 7 — Honest Labels Verification

All required labels are present and correct:

- `RuntimeClassBadge` — LIVE/RECORDED_LIVE/DETERMINISTIC, distinct tones. Present in `AttemptResultView`, `HeroTransmissionView`. ✓
- `SourceLabelBadge` — INTERNET REFERENCE / UPLOAD / SYNTHETIC / OWNED·CONSENTED. Present in `HeroPracticeView`, `HeroTransmissionView`. ✓
- "Package not expert-approved" warning — fires for `pending` and `rejected`; does NOT fire for `approved` or `revised`. Fixed `!== 'approved'` to `!== 'approved' && !== 'revised'`. ✓
- UNCERTAIN label in criteria table with `deviation_analysis` reason. ✓
- Transmission disclaimer: "The hash ... is not a certification of skill." Present in `HeroTransmissionView.tsx`. ✓

Files: `app/src/hero/HeroPracticeView.tsx` (review_status fix)

---

## Step 8 — Screenshots

Captured 5 screens via Playwright (mock mode, `vite preview` on port 4173):

| Screen | File |
|--------|------|
| Discovery/landing | `01_landing_discovery_2026-10-06T16-36-41Z.png` |
| Kolam source panel (real geometry) | `02_source_grounding_kolam_2026-10-06T16-36-41Z.png` |
| Kolam practice canvas | `03_adaptive_workspace_kolam_2026-10-06T16-36-41Z.png` |
| Tabla source panel (beat timeline) | `10_rhythm_workspace_tabla_2026-10-06T16-36-41Z.png` |
| Origami source/discovery | `12_spatial_sequence_origami_2026-10-06T16-36-41Z.png` |

Timestamp: `2026-10-06T16-36-41Z`. All in `screenshots/runs/2026-10-06T16-36-41Z/` and copied to `screenshots/latest/`.

**Open:** `audit:devtools` (full CDP audit with assertions) requires the live service. K3 used mock
mode preview for screenshots. The full live-service audit is deferred to K5 Integration step.

---

## Step 9 — Acceptance Checks

```
# Python non-live tests
pytest -q ... -m "not live"
→ 282 passed, 2 deselected, 1 warning in 75.31s

# npm build (production)
npm --prefix app run build
→ ✓ built in 57.75s (no TypeScript errors, no chunk > 500 kB)

# check_case_packs.py
→ CASE PACKS: PASS (7 packs)

# check_governance.py
→ Governance invariants: PASS

# check_contract_parity.py
→ CONTRACT PARITY: PASS (8 root contracts, 17 interfaces, 7 enums)
```

**All acceptance checks pass.**

---

## Open Issues / Human Decisions Needed

1. **Origami live build (not K3 scope):** Origami requires live Gemini API calls. No `.env` in K3 worktree. K4 handles this. The K3 app shows Origami source in mock mode correctly; `GET /api/cases/origami` returns the replay bundle from K4 once merged.

2. **`audit:devtools` with live service:** The full CDP audit script (`npm run audit:devtools`) is designed for the live service + real browser. The K3 screenshots used mock mode. Full live-service validation should run in K5 Integration after all branches are merged.

3. **Tabla case reality check:** Real tabla source is a fast (~158 BPM, 12-pulse cycle) webm clip. Mock used 80 BPM 16-beat synthetic. The real service and mock now diverge in musical content (as expected — mock is SYNTHETIC, service uses INTERNET REFERENCE). The evaluator will measure against the real source when submitted against the real service.

4. **Track A tabla builder evidence modality:** Fixed in `tracks/track-a/src/track_a/goals/tabla.py` — evidence modality now derived from source MIME type. This is a cross-track fix included in K3 because it blocked Step 1. Claude Code should verify the fix matches K2's intended behavior before merging.

---

## Acceptance Criteria Status

| Criterion | Status |
|-----------|--------|
| All three hero flows work against real service (no console errors) | MOCK: ✓. Real service: requires live service start (K5). |
| `npm run build` passes; contract parity passes | ✓ |
| Mock and real shapes are identical | ✓ (with dual field support for compat) |
| Screenshots captured | ✓ (5 screens, mock mode) |
| Definition of Done (00-COMMON.md) | ✓ |
| 282 non-live tests pass | ✓ |
| Case packs, governance, contract parity checks pass | ✓ |
