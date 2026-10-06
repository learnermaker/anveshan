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

Copy `.env.example` to `.env` and fill in your API key(s). The provider is selected by the model ID in `config.py`:

```
GOOGLE_API_KEY=<your key>        # for gemini-* models (default)
ANTHROPIC_API_KEY=<your key>     # for claude-* models
OPENAI_API_KEY=<your key>        # for gpt-* / o1 / o3 / o4-* models
```

Only the key for the model you use needs to be set. Set `GOOGLE_API_KEY` for the default Gemini model.

---

## Setup

```bash
# 1. Clone the FoldingAgentSimulator (MIT) and install locally
git clone https://github.com/maya-moriya/FoldingAgentSimulator.git
cd FoldingAgentSimulator
pip install -e .
cd ..

# 2. Install FoldingAgent (MIT, already cloned at ../../FoldingAgent/)
cd ../../FoldingAgent
pip install -e .
cd ../anveshan

# 3. Install hybrid pipeline dependencies
pip install pyav pillow pydantic matplotlib

# 4. Copy and fill .env
cp research/origami_hybrid/.env.example research/origami_hybrid/.env
# edit .env with your key(s)
```

---

## How to Run

> **Video source**: A placeholder is used until you supply a video. Place your video at `data/crane/input.mp4` (or any path) and pass it to the CLI.

```bash
# Step 1 — Extract keyframes (PyAV probes FPS automatically)
python research/origami_hybrid/pipeline.py extract-frames \
    --video data/crane/input.mp4 \
    --output data/crane/

# Step 2 — Review and edit data/crane/keyframes.json
#   (select the representative frame indices you want FoldingAgent to process)

# Step 3 — Run FoldingAgent reconstruction
python -m foldingagent.main data/crane/keyframes.json

# Step 4 — Run hybrid adapter → Anveshan contracts
python research/origami_hybrid/pipeline.py adapt \
    --fold-output out/run_<timestamp>_<model>_crane/ \
    --video-meta data/crane/video_meta.json \
    --output research/origami_hybrid/output/

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
  .env.example                     ← API key template
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
