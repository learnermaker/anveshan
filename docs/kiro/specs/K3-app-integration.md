# K3: App ↔ real service integration

Read `docs/kiro/specs/00-COMMON.md` first. Folder `...\anveshan-wt\k3-app`, branch `kiro/k3-app`. An API key is optional: only needed if you want to exercise Origami live. Kolam and Tabla work without it.

## Current state (merged)
- **Service:** `service/anveshan_service/` (FastAPI). Run it with
  ```
  <py> -m uvicorn anveshan_service.main:app --app-dir service --port 8080
  ```
  It implements `docs/plans/service-api.md` §5 and serves `app/dist` at `/`.
- **App:** `app/` (React/Vite).
  - `app/src/api/{client,types,runtime,mock}.ts` plus `mock/*`.
  - `npm --prefix app run dev` proxies `/api` to `:8080`; `npm --prefix app run dev:mock` serves canned SYNTHETIC data.
- **The app has only been tested against its own mock.** Its author listed six response shapes that are assumptions and must be checked against the real service (the details are in the original agent report, summarised here):
  1. the `CaseHandoff.to_view()` fields;
  2. `ui_view` for each modality (kolam `{canvas, dots[{x,y,r,relation}], curves, stroke_width, tau, symmetry, target_source_id}`, origami `{states[...], source_id}`, tabla `{beats[{index,time_sec,bass,strength}], period_sec, tempo_bpm, cycle_length, duration_sec, source_id}`);
  3. `trajectory.artifacts` (tabla `alignment[...]`, origami `frame_labels[{t,state}]`, kolam `off_path_strokes`);
  4. 1-based positions vs 0-based locator indices;
  5. the `drill`, `targeted_change` and transition-kind names (`observability_gain` vs `observability_gained`);
  6. exactly 2 attempts per session.

## Files you own
- `app/**` (keep `app/src/types/contracts.ts` unchanged).
- `service/anveshan_service/**` and `service/tests/**`, **only** for genuine API-shape bugs. Prefer fixing the app side.
- `docs/plans/service-api.md`: update it if you change any shape.

## Steps
1. **Build the cases locally (do not commit their artifacts).** Kolam and Tabla are owned by K1/K2, which commit them. In your worktree, run `build_case` for kolam and tabla in `recorded` mode (deterministic; Kolam's Gemma description becomes a warning) so the service has real goal models. Origami needs a key and a live build (about 10–20 calls). Do it only if K4 hasn't merged yet and Jim agrees; otherwise leave Origami for later.
2. **Run the service and the app** (`npm --prefix app run dev`). Walk through each hero case: discovery → source view → practice → results → retry → transmission. Use real inputs:
   - Kolam: draw on the canvas (a decent attempt and a sloppy one), and upload `tracks/track-b/eval/kolam/synthetic/*` rasters as photos.
   - Tabla: upload WAVs from `tracks/track-b/eval/tabla/make_synthetic.py` output (generated into `var/eval/tabla/`).
3. **For every shape mismatch:** fix `app/src/api/types.ts`, the consuming component, **and** the matching mock (`app/src/api/mock/*`) so mock and real stay identical. Fix the service only if it violates service-api.md. List every mismatch and fix in the report.
4. **Replace the hand-approximated Kolam mock geometry** with real `ui_view` output: dump the real `GET /api/cases/kolam` response into the mock fixture.
5. **Upload size guard:** Cloud Run caps request bodies at 32 MiB and the service limit is 30 MB. In the UI, reject larger files with a clear message (include a short hint on how to compress a video). Also catch the service's 413 nicely.
6. **Bundle hygiene:** load the mock backend via dynamic `import()` only when mock mode is on, so it isn't in the production chunk. Code-split the hero views if that's easy. The build must stay warning-free or under 500 kB per chunk.
7. **Honest labels everywhere:**
   - the runtime class from the server (LIVE / RECORDED_LIVE / DETERMINISTIC);
   - INTERNET REFERENCE / UPLOAD / SYNTHETIC source labels;
   - "package not expert-approved" warnings;
   - UNCERTAIN reasons.

   No copy may imply certification or validated learning.
8. **Screenshots:** run the dev server and capture the key screens for each hero case (source view, results with progress curve and first divergence, transmission). Save them under `screenshots/runs/<UTC timestamp>/` following `screenshots/README.md`, and update `screenshots/manifest.json` if that README requires it.

## Acceptance
- All three hero flows (Origami at least up to "evaluating" if there is no live build) work against the **real** service with no console errors.
- `npm --prefix app run build` passes; contract parity passes.
- Mock and real shapes are identical.
- Screenshots captured.
- The Definition of Done in 00-COMMON.md is met. Report: `docs/kiro/reports/K3-REPORT.md` (include the mismatch list).
