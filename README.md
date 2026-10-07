# Anveshan

> Working project name: Anveshan  
> Product name: TBD  
> Hackathon: Google Cloud AI Builder Cup 2026  
> Research checkpoint: 2026-10-03

## Product vision

Anveshan is a **living intelligence layer for human expertise, experience, and memory**.

Its long-term purpose is to make human knowledge **discoverable, preservable, transferable, verifiable, and continuously evolving** across people, generations, communities, and organizations.

The product is not defined by video, a chatbot, an LMS, a family archive, or an enterprise knowledge base. Those are possible applications and interfaces. The underlying system supports:

**CAPTURE â†’ UNDERSTAND â†’ GROUND â†’ TRANSMIT â†’ PRACTICE â†’ VERIFY â†’ EVOLVE**

### Core layers

**Memory** â€” What happened?  
**Expertise** â€” What does someone know, and how did they come to know it?  
**Capability** â€” Can another person actually use it?

### Product surfaces

- **Personal** â€” accumulated individual knowledge;
- **Social / Family / Elders** â€” intergenerational memory and living knowledge;
- **Community / Culture** â€” community-held practices, traditions, languages, and local knowledge;
- **Education / Apprenticeship** â€” teaching, practice, and skill transfer;
- **Enterprise** â€” institutional expertise, expert-to-worker transfer, and knowledge continuity;
- **Research** â€” exploration and synthesis of accumulated human experience.

### Multimodality

**Video is one modality, not the product.**

Anveshan can combine video, audio, text, images, documents, conversations, demonstrations, simulations, operational data, and learner attempts.

### Long-term vision

> **Anveshan makes human expertise discoverable, preservable, transferable, verifiable, and continuously evolving across people, generations, communities, and organizations.**

See `docs/product/product-vision.md` for the full product vision.

## Current competition thesis

For the Google Cloud AI Builder Cup 2026, the broad product vision is being narrowed into a single demonstrable use case.

The current working direction remains:

> **Anveshan helps an expert transmit a bounded piece of real-world expertise to another person, grounded in authentic evidence, with observable practice and verification of whether the knowledge transferred.**

This is a prototype wedge, not the definition of the company.

### Prototype loop

**SOURCE â†’ UNDERSTAND â†’ GROUND â†’ TRANSMIT â†’ PRACTICE â†’ VERIFY â†’ EVOLVE**

Source can be a demonstration, desired state, learner attempt, or combination. The transmission direction follows the capability and available evidence.

The exact domain/skill may still be refined as implementation and validation produce evidence; this does not block the current bounded development work.

## What is and is not novel

Anveshan does **not** claim novelty for AI interviews, tacit-knowledge extraction, knowledge graphs, multimodal RAG, AI tutoring, apprenticeship assistance, learner video assessment, expert cognition modeling, or agentic workflows. These are active product/research areas.

The current differentiation hypothesis is the **knowledge transmission event**:

**authentic expert source â†’ structured knowledge â†’ evidence â†’ teaching â†’ learner attempt â†’ evidence-based feedback â†’ measurable improvement â†’ lineage**

See docs/product/novelty-boundary.md.

## Current proof contract

The MVP must prove:

> **one accountable source + one bounded skill + one source-grounded knowledge representation + one learner + one practice task + one learner attempt + one evidence-grounded feedback loop + one retry + one measurable improvement + one transmission record + one lineage event**

For the original expert-transfer wedge, the accountable source should be a real expert. Goal-conditioned target-first cases are a documented research extension, not validated expert-procedure recovery.

See docs/product/mvp-contract.md.

## Current conceptual architecture

1. Capture or ingest an appropriate source and context.
2. Understand speech, actions, objects, sequence, conditions and cues.
3. Represent candidate knowledge and relationships.
4. Ground claims in source evidence.
5. Teach through a concise apprenticeship.
6. Practice a bounded task.
7. Verify against an explicit rubric/reference.
8. Record transmission.
9. Preserve evolution and lineage.

## Current AI architecture

### Knowledge Agent
Capture â†’ extract â†’ structure â†’ retrieve.

### Evidence Agent
Ground â†’ verify â†’ cite â†’ detect uncertainty and contradiction.

### Transmission Agent
Teach â†’ create practice â†’ evaluate attempts â†’ provide feedback â†’ update lineage.

These are logical responsibilities, not a requirement to create three autonomous agents. Deterministic services should handle ingestion, permissions, storage, indexing, auditability and evaluation.

## Current Google stack hypothesis

Current research supports a credible implementation using:

- Gemini 3.5 Transcribe;
- Gemini video understanding;
- Gemini Embedding 2;
- ADK;
- Cloud Run;
- agent evaluation.

Model names, feature compatibility, quotas, pricing and launch stages must be checked again immediately before implementation. See `docs/architecture/google-stack-integration.md` for the official Gemini model mapping, SDK patterns (`google-genai`), Pydantic structured outputs, and Google Cloud Run deployment standards.

## Governance principle

The product must not turn human knowledge into unreviewed machine-generated authority.

Source statement, observed evidence, AI interpretation, community interpretation and unknown remain distinct.

Do not claim "community-owned" unless the relevant community actually governs the data and its use.

## Current status

**Branch:** `m1/hero-cases` (Wave 2 integration complete)  
**Last updated:** 2026-10-06

### What works

Three hero cases are running end-to-end in recorded mode:

| Case | Source | What the system does |
|---|---|---|
| **Kolam** | Real photo (Wikimedia CC) | Detects dot grid, measures coverage/precision/continuity of learner trace. Deterministic, no API key needed. |
| **Tabla** | Real audio (Wikimedia CC) | Measures tempo, timing, and bass stroke accuracy. One Flash-Lite audio call for bol labels (INFERRED). |
| **Origami** | Real video (Wikimedia CC, ~25 MB) | Flash-Lite extracts 5 states from a 194 s crane-folding video. |

The **universal composer** works for novel image and video skills:

- Upload any image or short video â†’ the system perceives it, proposes a skill model, and builds a case.
- Evaluates learner attempts using embedding similarity + AI property judgements.
- Tested on: kolam photograph, synthetic rangoli, tabla chanderi video.

The **React frontend** (Vite + TypeScript) connects to the FastAPI service. All three hero cases
have full UI flows (source view, practice, attempt feedback). The composer wizard lets users
upload new source media and build composed cases.

### How to run locally

```bash
# Python environment
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements-dev.txt
python tools/fetch_media.py     # downloads licensed media from Wikimedia

# Run the service (recorded mode â€” no API key needed)
uvicorn anveshan_service.main:app --app-dir service --reload

# Run the frontend (in a separate terminal)
cd app && npm install && npm run dev
# Open http://localhost:5173
```

To run with live model calls (Flash-Lite), set `GEMINI_API_KEY` in `.env` and use `?mode=live`
in requests or set `ANVESHAN_MODE=live`.

### Testing

```bash
# All non-live tests (no API key required)
.venv\Scripts\python -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"
# Expected: ~423 passed

# Governance checks
python .github/scripts/check_governance.py
python .github/scripts/check_case_packs.py
python .github/scripts/check_contract_parity.py

# Frontend build
npm --prefix app run build
```

### Validation scope

All validation evidence to date is **engineering/capability evidence on internet-licensed and synthetic data**. No real learner sessions have been run. See `docs/validation/findings.md` for the honest scope.

### Deployed URL

Not yet deployed. Jim will deploy via the GCP Cloud Run console using `docs/deploy/DEPLOY-CHECKLIST.md` after branch review.

## Documentation

See docs/README.md for the complete map. The repository separates EXPLORED, DECIDED, VALIDATED and IMPLEMENTED material so research does not silently become product scope. See `AGENTS.md` for the source-of-truth hierarchy used by coding agents. Third-party media and their licences: `docs/MEDIA-ATTRIBUTION.md`.

### Parallel implementation workspaces

Two developers can now work independently under `tracks/track-a/` and `tracks/track-b/`, using the contract and replay-fixture boundary documented in `docs/architecture/parallel-work-contract.md`, with current execution gates in `docs/status/NOW.md`.

## Implementation Status

**Wave 2 integration complete (2026-10-06, branch `m1/hero-cases`)**

| Component | Status | Notes |
|---|---|---|
| Kolam evaluator | IMPLEMENTED | 50/50 synthetic eval, photo-path registration |
| Tabla evaluator | IMPLEMENTED | 49/49 synthetic eval, timbre classes |
| Origami evaluator | IMPLEMENTED | 5-state goal (R5/R6 missing) |
| Universal composer backend | IMPLEMENTED | Composer API, perceivers, SkillModel builder |
| Universal evaluator | IMPLEMENTED | embedding relevance, AI property judgement, specialist delegation |
| Composer UI | IMPLEMENTED | Wizard, discovery view, universal case views |
| Tabla timbre (K2b) | IMPLEMENTED | MFCC classes, bol labels INFERRED |
| FastAPI service | IMPLEMENTED | All routes, recorded + live modes |
| React frontend | IMPLEMENTED | All hero flows, composer wizard |
| CI / governance scripts | IMPLEMENTED | check_governance, check_case_packs, check_contract_parity |
| Cloud Run deploy | PENDING | Jim deploys via console; checklist at docs/deploy/DEPLOY-CHECKLIST.md |
| Expert review | NOT STARTED | All packages status: pending |
| Real learner sessions | NOT STARTED | No real learner data |

For contributors, treat:
- `docs/research/` as exploration and competitive/technical evidence;
- `docs/validation/` as experiment protocol and results;
- `docs/product/` as hypotheses and scope contracts pending validation;
- `docs/hackathon/` as submission/readiness material.
