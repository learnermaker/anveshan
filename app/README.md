# Anveshan — Transmission Instrument (Frontend)

React + Vite + Tailwind UI for **Anveshan** (Google Cloud AI Builder Cup 2026).

- **Live hero cases** — `kolam` (final image only), `origami` (video), `tabla` (audio, optional video) — are served by the Anveshan service (`service/`, API in `docs/plans/service-api.md` §5). The learner draws or uploads; the service evaluates; the UI shows the progress-to-goal curve, the first divergence, criteria, feedback and an unscored drill, then a full retry and the transmission record.
- **Showcase cases** — micrometer, bicycle repair, handloom weaving, square knot — are **SYNTHETIC replay** fixtures (`src/data/cases/registry.ts`). They never call the service.
- **No model calls or keys in the browser.** All model work is server-side; the Runtime panel (header `MODE:` button) only reads `/api/health` and sets the requested `?mode=live|recorded`.

## Run

```bash
npm --prefix app install
```

### Against the real service

```bash
# terminal 1 (repo root): start the service on :8080
.venv/Scripts/python -m uvicorn anveshan_service.main:app --app-dir service --reload --port 8080
# terminal 2
npm --prefix app run dev        # http://localhost:5173 — /api is proxied to :8080
```

`VITE_API_BASE` (see `.env.example`, copy to `.env.local`):

| Value | Behaviour |
|---|---|
| empty (default) | same origin. In dev, Vite proxies `/api` to `http://localhost:8080` (override with `ANVESHAN_API_PROXY`). On Cloud Run the service serves `app/dist` and the API together. |
| `http://host:port` | call that service directly (it must allow CORS for the app origin). |
| `mock` | in-browser canned responses (below). |

### Mock mode (no backend)

```bash
npm --prefix app run dev:mock   # http://localhost:5174, `--mode mock` sets VITE_API_BASE=mock (vite.config.ts)
npm --prefix app run build:mock # static build with the mock baked in
```

Mock mode serves every endpoint from `src/api/mock.ts` + `src/api/mock/*.ts`. Everything it returns is **SYNTHETIC** and the UI shows a red **MOCK DATA** badge in the header, discovery, case and result screens.

- Kolam: real public-domain target image (`public/mock/kolam_target.jpg`, *Ithayakkamalam - 2.jpg* by Mayooranathan, via Wikimedia Commons) with **hand-approximated** dots/curves. Canvas traces are scored by a simplified browser re-implementation of evaluation-core §3.2, so drawing produces plausible feedback. Photo uploads return a canned final-state-only result (process criteria UNCERTAIN).
- Origami: canned frame labels/curves; keyframes are generated SVG diagrams; the expert video is not bundled.
- Tabla: a click/bass track synthesised in the browser from a 16-beat pattern; canned alignment with late, missing, extra and bass-mismatch beats.
- Uploading "your own source" creates an in-memory derived case (`<base>~<sha12>`, label UPLOAD) that reuses the base case's canned goal model.

## Build & checks

```bash
npm --prefix app run build                                  # tsc (strict) + vite build
.venv/Scripts/python .github/scripts/check_contract_parity.py  # contracts.ts must mirror tracks/common/schemas
```

## Code map

| Path | Role |
|---|---|
| `src/api/client.ts` | typed client for every service endpoint; `ApiError` from `{"error": {category, message, details}}`; XHR uploads with progress; `?mode=` |
| `src/api/types.ts` | CaseView, AttemptResult, SessionResult, trajectory, first_divergence… (imports the 8 contracts from `src/types/contracts.ts`, never re-declares them) |
| `src/api/runtime.ts` | `VITE_API_BASE`, mock switch, requested mode |
| `src/api/mock.ts`, `src/api/mock/` | SYNTHETIC mock backend |
| `src/hero/HeroSourceView.tsx` | 01 SOURCE: modality view, claims (OBSERVED/INFERRED/UNVERIFIED) with evidence highlight, evidence query, expert review |
| `src/hero/SourcePanels.tsx` | Kolam overlays (dots, inferred curves, symmetry), origami video + keyframe strip, tabla audio + beat timeline |
| `src/hero/HeroPracticeView.tsx` | 02 PRACTICE: session, Kolam canvas / uploads, progress + "Evaluating…", results, retry |
| `src/hero/kolam/KolamCanvas.tsx` | drawing in goal-image pixels; trace JSON (service-api §4) + PNG raster |
| `src/hero/results/*` | progress-to-goal curve (SVG), first-divergence card, criteria, feedback, unscored drill |
| `src/hero/HeroTransmissionView.tsx` | 03 TRANSMISSION: curve overlay, contract / targeted / observability-excluded gains, transitions, lineage |
| `src/components/`, `src/workspaces/` | V0 Transmission Instrument, used by the showcase cases |

## Contract authority

The eight shared contracts have one source of truth: `tracks/common/schemas/`. `src/types/contracts.ts` is a downstream mirror checked by CI. Service view shapes (`src/api/types.ts`) follow `docs/plans/service-api.md`; legacy showcase fixture shapes are normalised at `src/data/adapter.ts`.

Nothing in this UI certifies a learner or validates a source. Scores come from deterministic bands; runtime labels (LIVE / RECORDED LIVE / DETERMINISTIC) come from the server.
