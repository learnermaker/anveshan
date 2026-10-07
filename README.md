# Anveshan

Anveshan passes on skills of the physical world from one person to another: learned from a real demonstration, practised with real hands, and checked against a photo, video or recording of the learner's real attempt.

Folding, drawing, drumming, repairing: skills a chat tutor cannot see. Every tip points back to the moment in the real demonstration, and the app says plainly what a camera cannot sense. Why this matters and how it differs: [positioning](docs/product/novelty-boundary.md#skills-of-the-physical-world-positioning-decided-2026-10-07).

**Hackathon:** Google Cloud AI Builder Cup 2026

---

## Try it

Live URL: `https://<cloud-run-url>` (added at deployment)

**First-time visitor path:**

1. Open the **Kolam drawing** — a traditional Indian floor art skill, sourced from a real Wikimedia photo.
2. Press **Start practising** and use **Try a sample attempt**, or draw it yourself on the canvas.
3. Read the feedback and "Why this feedback?" for each criterion.
4. Do your second try and see what changed.

**Other paths:**
- **Share a skill you know** — upload a photo, short video, or audio clip; the system proposes a skill model; confirm the steps and publish.
- **My skills** — review and manage skills you have shared.
- **Steward console** — footer "Steward sign-in"; access code required.

---

## Three ways to use Anveshan

**Learner.** Anyone who wants to acquire a skill. Practise a bounded task, get feedback grounded in the source evidence, and see exactly what changed on your retry. Every feedback item links back to a specific step or claim in the original demonstration.

**Creator.** The expert, artisan or practitioner who shares a skill — or anyone sharing a source they hold the rights to. Upload a demonstration, confirm what the AI understood, and publish with clear credit and consent. See aggregated learner outcomes for each skill you share.

**Steward.** The body accountable for a collection of knowledge: a school, guild, heritage organisation, or company. Run the review queue, manage consent and licence records, and see usage and continuity insights. All insights are aggregate; no names or raw media are ever shown.

---

## How it works

Every skill flows through one lifecycle:

**CAPTURE → UNDERSTAND → GROUND → TRANSMIT → PRACTICE → VERIFY → EVOLVE**

**Evaluation core.** The system builds a goal model from the source: key steps, a rubric, and claims grounded in source evidence. When a learner submits an attempt, deterministic checks compare it to the goal model — no model decides whether a criterion passes or fails. The first place the attempt diverged from the model is identified, and targeted feedback is generated. On the retry, the same checks run and the change is measured.

See [`docs/plans/evaluation-core.md`](docs/plans/evaluation-core.md) and [`docs/plans/universal-pipeline.md`](docs/plans/universal-pipeline.md).

---

## Where Gen AI is used (and where it is not)

| Job | Model | Guard |
|---|---|---|
| Perceiving uploads | gemini-3.5-flash-lite; audio model configured separately (disabled by default; set `ANVESHAN_AUDIO_MODEL` to enable) | Recorded runs, explicit failures |
| Embeddings for alignment | gemini-embedding-2 | — |
| Answering questions about a skill | gemini-3.5-flash-lite, from cited claims only | Insufficient-evidence refusal |
| Wording coaching advice | gemini-3.5-flash-lite | Guard rejects new numbers or verdict words; template fallback |
| Scoring, pass/fail, permissions, insights | **no model** | Deterministic bands and rules |

**Cost control.** Identical calls are answered from stored runs, the shared key has a daily call budget, Kolam and Tabla scoring use no model, images are downsized and sent to Gemini 3 at a matching media resolution, and output is capped. Token use is recorded per run (`tools/token_report.py`). Details: [`docs/architecture/token-economy.md`](docs/architecture/token-economy.md).

**Your own key.** Visitors can add their own Gemini API key in the app (key button in the header, or the prompt next to any upload that needs AI). It stays in their browser, is sent only to this service in a request header, and their calls skip the shared budget.

---

## Evidence (engineering, not user validation)

All evidence to date is engineering and capability evidence on internet-licensed and synthetic data.

- Experiment log (E1-E9): [`docs/validation/experiments.md`](docs/validation/experiments.md)
- Non-live test suite: **566 tests** as of 2026-10-07 (`pytest -m "not live"`)
- Judges-panel review: [`docs/research/judges-panel-review-2026-10-07.md`](docs/research/judges-panel-review-2026-10-07.md)

**No study with real learners or experts has been run yet.**

---

## Limits

- **Recorded vs live mode.** The service runs in recorded mode by default; model responses are replayed deterministically from golden runs. Live mode requires a Gemini API key and may return different results between runs (see E6, E7).
- **Demo storage is temporary.** Uploaded media and composed skills are kept in memory; data is retained for about 6 hours; published skills persist until the service restarts.
- **No accounts.** Ownership is tracked per browser session.
- **Internet sources are not verified experts.** Hero case media comes from Wikimedia Commons under open licences. It is labelled INTERNET REFERENCE in the UI; the photographer or uploader is not an Anveshan expert.
- **Known weak spots (universal pipeline, from `docs/plans/universal-pipeline.md` §12.3):**
  - Global embeddings separate scenes, not fine-grained object states; step identity varies between live runs for low-resolution hand-held footage.
  - Composed steps are proposals until the creator confirms them.
  - An attempt that is visually similar to the source but unrelated can land in the ambiguous relevance band and FAIL instead of being REFUSED.
  - Crop to the work region is not yet implemented for real hand-held footage.

---

## Run locally

```bash
# Python environment
python -m venv .venv
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python tools/fetch_media.py       # downloads licensed media from Wikimedia Commons

# Service (recorded mode, no API key required)
.venv/Scripts/python -m uvicorn anveshan_service.main:app --app-dir service --reload --port 8080

# App dev server (separate terminal)
cd app && npm install && npm run dev
# Open http://localhost:5173
```

**Mock mode (no service required):** `cd app && npm run build:mock`

**Live model calls:** copy `.env.example` to `.env`, set `GEMINI_API_KEY`, and pass `?mode=live` or set `ANVESHAN_MODE=live`. Never commit `.env`.

---

## Deploy

See [`docs/deploy/DEPLOY-CHECKLIST.md`](docs/deploy/DEPLOY-CHECKLIST.md).
Set `ANVESHAN_STEWARD_TOKEN` as a Cloud Run secret before deploying.

---

## Repository map

```
app/              React + Vite frontend (TypeScript, strict)
service/          FastAPI service (Python)
tracks/common/    Shared contracts, models, and evaluation schemas (8 frozen contracts)
tracks/track-a/   Case ingestion, universal pipeline, and the Gemini model gateway
tracks/track-b/   Evaluators, feedback engine, and AI coach
tracks/cases/     Case packs: kolam, origami, origami-crane, tabla, and four synthetic showcase cases
docs/             Product vision, architecture, validation log, and plans
tools/            CLI tools: fetch media, smoke test, stability runs, sample generation, token report, repeated-text report
```

**Contributing.** Read [`AGENTS.md`](AGENTS.md) first. Each file and each rule has one canonical home; link to it instead of copying (`.github/scripts/check_duplicates.py` runs in CI).

---

## Licence

Code: Apache-2.0 ([LICENSE](LICENSE)).
Case media keep their own licences; see each pack's `source/source.json`.

---

## Team and competition

Google Cloud AI Builder Cup 2026. Submission due 2026-10-18.
