# Hybrid Origami Pipeline — Architecture Summary

> **Status**: RESEARCH ONLY — not approved for merge into Track A.  
> **Scope**: `research/origami_hybrid/` only. No modifications to `tracks/track-a/src/`, `tracks/cases/`, or `tracks/common/schemas/`.

---

## Mission

The hybrid origami pipeline combines FoldingAgent's parametric geometric reconstruction (exact vertex positions, crease assignments, layer stacking) with Anveshan Track A's knowledge structuring (epistemic discipline, rubric criteria, provenance chain) to produce valid Anveshan contracts — `KnowledgePackage`, `RubricDefinition`, `PracticeTask` — enriched with machine-verified fold geometry. The goal is the best of both worlds: geometric fidelity for claim grounding, and semantic structure for teaching.

---

## Data Flow Diagram

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  INPUT: <origami_instruction_video>                                     │
  │  (placeholder — user will supply; e.g. a CC-licensed crane video)       │
  └──────────────────────────────┬──────────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  KeyframeExtractor       │
                    │  PyAV frame decode       │
                    │  FPS probed via PyAV     │
                    │  → keyframes.json        │
                    │  → frames/NNNNNN.jpg     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────────────────────────────────┐
                    │  FoldingAgentCore  (black box — do not modify)      │
                    │  ReAct loop: LLM ↔ OrigamiController ↔ Simulator   │
                    │  Simulator = FoldingAgentSimulator (MIT, cloned)    │
                    │  OrigamiCritic (4-panel grid, MATCH/MISMATCH)       │
                    │  OrigamiComparator (best-of-N on budget exhaust)    │
                    └────────────┬────────────────────────────────────────┘
                                 │  checkpoints.json
                                 │  logs/attempt_tree.json
                                 │  figs/attempt_*.png
                                 │  metadata.json
                                 │
                    ┌────────────▼────────────┐
                    │  FoldingAgentAdapter    │  ◄── adapter.py
                    │  load_checkpoints()     │
                    │  to_evidence_refs()     │  timestamp_sec = frame_idx / fps
                    │  to_knowledge_claims()  │  (fps probed by PyAV at extract step)
                    └────────────┬────────────┘
                                 │  raw KnowledgeClaim[], EvidenceRef[]
                                 │  (no LLM calls)
                    ┌────────────▼────────────┐
                    │  EvidenceGrounder       │  ◄── grounding.py
                    │  Gemini call per claim  │
                    │  + epistemic tagging    │
                    │  OBSERVED / INFERRED /  │
                    │  UNVERIFIED             │
                    └────────────┬────────────┘
                                 │
                     ┌───────────┴───────────┐
                     │                       │
          ┌──────────▼──────┐    ┌──────────▼──────────┐
          │ RubricSynthesizer│   │ PracticeTaskGenerator│
          │  rubric_synth.py │   │  (in adapter.py)     │
          │  5 synthesized   │   │  instructions from   │
          │  criteria from   │   │  claim statements    │
          │  geometric facts │   │                      │
          └──────────┬───────┘   └──────────┬───────────┘
                     └───────────┬───────────┘
                                 │
                    ┌────────────▼──────────────────────────────────────────┐
                    │  OUTPUT (research/origami_hybrid/output/)             │
                    │  ├── knowledge_package.json  (KnowledgePackage)       │
                    │  ├── rubric.json             (RubricDefinition)       │
                    │  ├── practice_task.json      (PracticeTask)           │
                    │  ├── run_metadata.json        (RunMetadataDTO)        │
                    │  ├── expert_review_sheet.md   (Markdown review sheet) │
                    │  ├── fold_state_log.json      (geometry sidecar)      │
                    │  └── crease_evidence.json     (crease pattern sidecar)│
                    └───────────────────────────────────────────────────────┘
```

---

## Component Table

| Component | Role | Input | Output |
|---|---|---|---|
| **KeyframeExtractor** | Decode video with PyAV; probe FPS; select representative frames | video file (path placeholder until user supplies source) | `keyframes.json`, JPEG frames in `NNNNNN.jpg` format, `video_meta.json` (fps, duration, resolution) |
| **FoldingAgentCore** | Run ReAct reconstruction loop; verify each state against photo via critic | `keyframes.json`, frame directory | `checkpoints.json`, `attempt_tree.json`, `metadata.json`, rendered PNGs in `figs/` |
| **FoldingAgentAdapter** | Convert FoldingAgent output to Anveshan contract shapes (no LLM) | `checkpoints.json`, `attempt_tree.json`, `frames.json`, `video_meta.json` (fps) | `list[FoldCheckpoint]`, raw `KnowledgeClaim[]`, `EvidenceRef[]` |
| **EvidenceGrounder** | Add Anveshan epistemic layer via Gemini call; assign `verification_state`, calibrate `confidence` | Raw claims, rendered PNGs, `critic_verdict` per frame | Epistemically-tagged `KnowledgeClaim[]`, enriched `cue_excerpt` on `EvidenceRef[]` |
| **RubricSynthesizer** | Synthesize 5 observable rubric criteria from geometric sequence | `list[FoldCheckpoint]`, claim sequence | `RubricDefinition` with geometry-grounded `observable_indicator` per criterion |
| **PracticeTaskGenerator** | Build learner instructions from claim statements and rubric | `KnowledgePackage`, `RubricDefinition` | `PracticeTask` with material constraints and `target_criteria_ids` |
| **RunMetadataWriter** | Emit `run_metadata.json` capturing model, provider, prompt version, runtime class | `RunMetadataDTO` (constructed by adapter) | `output/run_metadata.json` |
| **ExpertReviewExporter** | Emit `expert_review_sheet.md` for human inspection and correction | `KnowledgePackage`, manifest | `output/expert_review_sheet.md` (Markdown) |

---

## Key Design Decisions

### Video source placeholder
The input video is a **placeholder**. The pipeline accepts any instructional origami video supplied by the user. The `KeyframeExtractor` uses PyAV to probe FPS and decode frames, so no hard-coded source URL or file path is embedded in the pipeline code.

### FoldingAgentSimulator: cloned from source, not API
Both FoldingAgent (`https://github.com/maya-moriya/FoldingAgent`) and FoldingAgentSimulator (`https://github.com/maya-moriya/FoldingAgentSimulator`) are MIT-licensed public repos. The hybrid pipeline installs `foldingagent-simulator` from its local clone via `pip install -e .` rather than from a live Git dependency. This eliminates runtime network dependency on the upstream repo and allows local inspection/adaptation of the simulator if needed. FoldingAgent itself remains a black box — its internals are not modified, but its `origami` import resolves to the locally installed simulator.

### FPS source: PyAV probe
Timestamps for `EvidenceRef.start_sec` / `EvidenceRef.end_sec` are computed as `frame_idx / fps`. FPS is probed by PyAV at the `extract-frames` step and stored in `video_meta.json`. The adapter reads `fps` from `video_meta.json` — no hard-coding, no external parameter required.

### Rubric: synthesized criteria from geometry
The pipeline synthesizes 5 rubric criteria from the geometric sequence produced by FoldingAgent (vertex alignment, fold direction fidelity, layer count, crease sharpness proxy, final-state match). These are NOT the canonical `CRIT-CORNER-ALIGN` / `CRIT-VALLEY-FOLD` / `CRIT-BONE-CREASE` from the replay bundle. Synthesized criteria are geometry-grounded and specific to the actual video's reconstruction. Criterion IDs follow the pattern `CRIT-HYB-<N>`.

### Epistemic state derived from critic verdict
A checkpoint with `critic_verdict = "MATCH"` → `is_observed=True`, `verification_state=OBSERVED`, `confidence=1.0`.  
A comparator-selected checkpoint (budget exhausted) → `is_observed=False`, `verification_state=INFERRED`, `confidence≤0.5`.  
This is the only mapping that satisfies Anveshan's `GroundingService.enforce_epistemological_state()`.

### Geometry in sidecars, prose in contracts
The `fold_state_log.json` and `crease_evidence.json` sidecars hold full geometry dicts. Anveshan contracts carry only prose references (in `EvidenceRef.cue_excerpt`) and rendered PNG paths. The frozen seam is not modified.

### Two evidence refs per claim: IMAGE + VIDEO
Each `KnowledgeClaim` gets two `EvidenceRef` objects:
- `modality=IMAGE`: rendered PNG from FoldingAgent (`source_id="src-fa-checkpoint-<run_id>"`)
- `modality=VIDEO`: source video segment (`source_id` derived from user-supplied video attribution)

### run_metadata.json and expert_review_sheet.md are required outputs
Following the Anveshan Track A `run_pipeline.py` convention, the hybrid pipeline emits both:
- `run_metadata.json` — `RunMetadataDTO` capturing provider, model_id, prompt_id, prompt_version, runtime_class, run_id, case_id
- `expert_review_sheet.md` — Markdown inspection sheet (from `ExpertReviewService.export_markdown()`) so a human can review and correct the derived knowledge before any downstream use

These are not optional — they are required for the output to be auditable.

### Consent: research_prototype scope
The hybrid output uses `consent_scope="research_prototype"`. Attribution for the user-supplied video must be added to `ConsentMetadata.notes` by the user before the output can be used beyond the research folder. The pipeline emits a warning if attribution metadata is missing.

### Track B compatibility: deferred
The hybrid output uses IDs in the `kp.origami-hybrid.*` namespace, distinct from canonical case pack IDs. Track B integration is deferred — focus is entirely on the hybrid pipeline producing correct, auditable Anveshan contracts. If the hybrid is successful, a separate decision will be made about downstream Track B integration.

---

## What Stays Frozen (Anveshan Seam)

The following CANNOT be changed by the hybrid pipeline:

| Schema | Frozen fields | Why |
|---|---|---|
| `EvidenceRef` | `evidence_id`, `source_id`, `modality` (enum values), `start_sec`, `end_sec`, `verification_state` (enum values), `confidence` range | Track B uses these to extract video clips and route evidence |
| `KnowledgePackage` | `package_id`, `skill_id`, `claims[*].claim_id`, `claims[*].claim_type` (enum values), `claims[*].evidence_refs` min_length=1 | Downstream systems reference by ID and route by claim_type |
| `RubricDefinition` | `rubric_id`, `skill_id`, `criteria[*].criterion_id`, `criteria[*].weight`, `criteria[*].required`, `passing_score` semantics | Track B scoring engine relies on criterion IDs and weight/required flags |
| `PracticeTask` | `task_id`, `package_id`, `rubric_id`, `target_criteria_ids` must be valid criterion IDs | Track B cross-validates these at runtime |

---

## Open Questions (updated)

- **Video source**: User will supply the video. The pipeline uses a placeholder. KeyframeExtractor accepts any format PyAV can decode.
- **Canonical criteria vs. synthesized criteria**: **Decision: synthesized criteria** from the geometric sequence. Criterion IDs use `CRIT-HYB-<N>` namespace.
- **FoldingAgentSimulator availability**: **Decision: clone from source** (`pip install -e .` from local clone). Both repos are MIT-licensed.
- **Consent chain**: **Decision: `consent_scope="research_prototype"`**. User must supply video attribution before output can be used beyond research folder.
- **Track B compatibility**: **Decision: deferred**. Focus on hybrid pipeline correctness first.

---

*See `RESEARCH.md` for full technical detail on every component, all field mappings, prompt templates, sidecar schemas, and risk analysis.*
