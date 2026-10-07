# Origami Hybrid Pipeline — Research Prototype

> **Status**: RESEARCH ONLY — do not merge into Track A without explicit authorization.  
> **Branch**: `feat/amal-kiro-origami` under `research/origami_hybrid/`.  
> **Full Spec**: See [`tracks/track-a/notes/origami-hybrid/RESEARCH.md`](../../tracks/track-a/notes/origami-hybrid/RESEARCH.md)  
> **Architecture**: See [`tracks/track-a/notes/origami-hybrid/ARCHITECTURE.md`](../../tracks/track-a/notes/origami-hybrid/ARCHITECTURE.md)

---

## Scope Disclaimer

This folder is **outside the Track A case pack boundary**. It does not import from `tracks/track-a/src/` and does not modify any files under:

- `tracks/track-a/src/`
- `tracks/cases/`
- `tracks/common/schemas/`

It exists purely as a research prototype to explore the feasibility of combining FoldingAgent's geometric reconstruction with Anveshan's knowledge structuring. Nothing here is production code. Nothing here should be referenced from the Anveshan Track A pipeline until an explicit integration decision is made and reviewed.

---

## What It Does

The hybrid pipeline takes a raw origami instruction video and produces valid Anveshan contracts (`KnowledgePackage`, `RubricDefinition`, `PracticeTask`) enriched with machine-verified fold geometry:

1. **KeyframeExtractor** — decodes the video with PyAV, probes FPS, writes frames to `NNNNNN.jpg` and records `video_meta.json` (fps, duration, resolution).

2. **FoldingAgentCore** (black box — MIT) — runs a ReAct loop with the FoldingAgentSimulator (MIT, installed from local clone) to reconstruct the full folding sequence from extracted keyframes. Each keyframe state is verified against the real photo by an LLM critic (4-panel grid). Produces `checkpoints.json` with vertices, faces, edges (M/V/F/B), layer stacking, and operation history per keyframe.

3. **FoldingAgentAdapter** — converts FoldingAgent output to Anveshan contract shapes. Timestamps derived as `frame_idx / fps` from `video_meta.json`. MATCH-verified states → `is_observed=True`, `verification_state=OBSERVED`. Comparator-selected states → `is_observed=False`, `verification_state=INFERRED`, `confidence≤0.5`.

4. **EvidenceGrounder** — adds the Anveshan epistemic layer via Gemini: produces a grounded natural-language `cue_excerpt` from each geometric state and rendered PNG.

5. **RubricSynthesizer** — synthesizes 5 geometry-grounded observable rubric criteria (IDs: `CRIT-HYB-1` through `CRIT-HYB-5`) from the fold sequence. Does NOT use the canonical `CRIT-CORNER-ALIGN` / `CRIT-VALLEY-FOLD` / `CRIT-BONE-CREASE` IDs.

6. **RunMetadataWriter** + **ExpertReviewExporter** — emits `run_metadata.json` and `expert_review_sheet.md` following the Anveshan Track A `run_pipeline.py` convention.

7. **Output** — `knowledge_package.json`, `rubric.json`, `practice_task.json`, `run_metadata.json`, `expert_review_sheet.md`, `fold_state_log.json`, `crease_evidence.json`.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. The file controls both API keys and model selection:

```
# API keys (only the one(s) you use need to be set)
GOOGLE_API_KEY=          # for gemini-* models
ANTHROPIC_API_KEY=       # for claude-* models (recommended for FoldingAgent)
OPENAI_API_KEY=          # for gpt-* / o-series models

# Model for the hybrid pipeline's LLM enrichment steps
HYBRID_MODEL=gemini-3.8-flash     # or claude-3-5-haiku-20241022, gpt-4o-mini, etc.
HYBRID_FALLBACK_MODEL=            # optional fallback if HYBRID_MODEL returns 404

# Reference model for FoldingAgent (must also set in FoldingAgent/src/foldingagent/config.py)
FOLDINGAGENT_MODEL=gemini-3.8-flash
```

**Which key do I need for FoldingAgent?**

FoldingAgent infers the provider from the model ID it's configured with. The keys map as:
- `gemini-*` → `GOOGLE_API_KEY`
- `claude-*` → `ANTHROPIC_API_KEY` ← recommended for FoldingAgent
- `gpt-*` / `o-series` → `OPENAI_API_KEY`

FoldingAgent runs a multi-turn ReAct loop — 50–200+ model calls per origami sequence. The Gemini free tier (20 req/day) is almost certainly insufficient for a full run. **Recommended: use Anthropic Claude with a separate API key**, or a paid Gemini key. The hybrid pipeline's enrichment steps (EvidenceGrounder, RubricSynthesizer) are separate and use only 2–10 calls per run.

**FoldingAgent reads from environment variables directly**, not from our `.env` file. Export the key in your shell before running FoldingAgent:

```powershell
# PowerShell
$env:ANTHROPIC_API_KEY = "your-key-here"
# then run FoldingAgent from its repo root
python -m foldingagent.main data/origami/keyframes.json
```

Or add the key to `FoldingAgent/.env` (FoldingAgent also loads `.env` from its own repo root).

---

## Setup

```bash
# Clone anveshan and initialise submodules in one go:
git clone --recurse-submodules https://github.com/<your-org>/anveshan.git

# Or if you already have a clone:
git submodule update --init --recursive research/origami_hybrid/vendor/
```

Then run the one-shot setup script — it installs both vendored packages and all dependencies:

```powershell
# Windows (PowerShell) — run from the anveshan repo root:
.\research\origami_hybrid\setup.ps1
```

```bash
# macOS / Linux — run from the anveshan repo root:
bash research/origami_hybrid/setup.sh
```

The setup script installs:
- `FoldingAgentSimulator` (editable, from `vendor/FoldingAgentSimulator/`)
- `FoldingAgent` (editable, from `vendor/FoldingAgent/`, resolves simulator from above)
- `av`, `pillow`, `numpy`, `pydantic`, `python-dotenv`, `google-genai`

**For teammates:** `git clone --recurse-submodules` is all that's needed to get both vendored repos. No separate manual clone step.

---

## How to Run

> **Video source**: Supply any instructional origami video — any subject, not just cranes. Place it at any path and pass it to the CLI. The sequence name in `keyframes.json` is derived from the video filename automatically.

```bash
# Step 1 — Extract keyframes (PyAV probes FPS automatically)
#   Replace "data/origami/input.mp4" with your actual video path.
python research/origami_hybrid/pipeline.py extract-frames \
    --video data/origami/input.mp4 \
    --output data/origami/

# Step 2 — Review and trim data/origami/keyframes.json
#   Keep only the ~10-20 representative frame indices for FoldingAgent.

# Step 3 — Run FoldingAgent reconstruction
#   Export your API key first (see Environment Variables above).
#   FoldingAgent runs from its own repo root:
python -m foldingagent.main data/origami/keyframes.json

# Step 4 — Run hybrid adapter → Anveshan contracts
python research/origami_hybrid/pipeline.py adapt \
    --fold-output out/run_<timestamp>_<model>_<sequence>/ \
    --video-meta data/origami/video_meta.json \
    --output research/origami_hybrid/output/ \
    --attribution "Video creator name, license, source URL"

# Output files:
#   output/knowledge_package.json
#   output/rubric.json
#   output/practice_task.json
#   output/run_metadata.json
#   output/expert_review_sheet.md
#   output/fold_state_log.json
#   output/crease_evidence.json
```

# Output files:
#   output/knowledge_package.json
#   output/rubric.json
#   output/practice_task.json
#   output/run_metadata.json
#   output/expert_review_sheet.md
#   output/fold_state_log.json
#   output/crease_evidence.json
```

---

## Dependencies

| Dependency | Source | License | Notes |
|---|---|---|---|
| `foldingagent` | `FoldingAgent/` (local clone) | MIT | Geometric reconstruction engine (black box — not modified) |
| `foldingagent-simulator` | `FoldingAgentSimulator/` (local clone) | MIT | Origami physics / simulator; installed with `pip install -e .` |
| `pyav>=13.0` | PyPI | BSD | Video decoding + FPS probe |
| `google-genai>=0.3` | PyPI | Apache 2.0 | EvidenceGrounder (Gemini) |
| `anthropic>=0.40` or `openai>=1.40` | PyPI | MIT | Alternative LLM backends for FoldingAgent |
| `pydantic>=2.0` | PyPI | MIT | Anveshan contract schema validation |
| `pillow>=10.0` | PyPI | MIT | Image handling for critic grids |
| `matplotlib>=3.7` | PyPI | PSF | Geometry diagram rendering (via FoldingAgent) |

Anveshan schemas (`tracks/common/schemas/`) are used as **read-only imports** — validated against but not modified.

---

## Consent

The hybrid pipeline uses `consent_scope="research_prototype"`. Before using any output beyond this research folder:

1. Supply video attribution in `ConsentMetadata.notes` — name the creator, license, and source URL.
2. The pipeline emits a warning if attribution metadata is missing.

---

## Folder Structure

```
research/origami_hybrid/
  README.md                        ← this file
  .env.example                     ← API key + model config template
  config.py                        ← HybridConfig: loads model names + keys from .env
  pipeline.py                      ← entry point: extract-frames + adapt subcommands
  adapter.py                       ← FoldingAgentAdapter: checkpoints.json → Anveshan contracts
  grounding.py                     ← EvidenceGrounder: epistemic tagging via Gemini
  rubric_synth.py                  ← RubricSynthesizer: geometric sequence → 5 synthesized criteria
  expert_review.py                 ← ExpertReviewExporter: emit expert_review_sheet.md
  prompts/
    evidence_grounder_v1.txt       ← prompt for EvidenceGrounder
    rubric_synth_v1.txt            ← prompt for RubricSynthesizer
    practice_task_v1.txt           ← prompt for PracticeTaskGenerator
  schemas/
    fold_state_log.schema.json     ← JSON Schema for geometry sidecar
    crease_evidence.schema.json    ← JSON Schema for crease pattern sidecar
  tests/
    test_adapter.py                ← unit tests for FoldingAgentAdapter
    fixtures/
      sample_checkpoint.json       ← 2-frame minimal fixture
      sample_attempt_tree.json     ← matching attempt tree fixture
      video_meta.json              ← sample fps/duration fixture
  output/                          ← generated files (gitignored)
```

---

## Key Constraints (summary)

- Does not import from `tracks/track-a/src/` — contracts from `tracks/common/schemas/` only.
- Geometry in sidecars; prose references in Anveshan contracts (frozen seam unchanged).
- MATCH critic verdict → `OBSERVED`. Comparator-selected → `INFERRED`, `confidence≤0.5`.
- Rubric uses synthesized `CRIT-HYB-<N>` IDs, not canonical origami criteria.
- FPS from PyAV probe stored in `video_meta.json` — no hard-coding.
- FoldingAgentSimulator installed from local clone — no live Git dependency at runtime.
- Track B integration deferred until hybrid pipeline is validated.

---

## Contact / Full Documentation

- **Full research document**: [`tracks/track-a/notes/origami-hybrid/RESEARCH.md`](../../tracks/track-a/notes/origami-hybrid/RESEARCH.md)
- **Architecture summary**: [`tracks/track-a/notes/origami-hybrid/ARCHITECTURE.md`](../../tracks/track-a/notes/origami-hybrid/ARCHITECTURE.md)
- **FoldingAgent deep-dive**: [`tracks/track-a/notes/origami-hybrid/FOLDING_AGENT_DEEP_DIVE.md`](../../tracks/track-a/notes/origami-hybrid/FOLDING_AGENT_DEEP_DIVE.md)
- **Anveshan Track A deep-dive**: [`tracks/track-a/notes/origami-hybrid/ANVESHAN_DEEP_DIVE.md`](../../tracks/track-a/notes/origami-hybrid/ANVESHAN_DEEP_DIVE.md)
