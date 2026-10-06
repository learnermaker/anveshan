# Hybrid Origami Pipeline — Comprehensive Research Document

> **Status**: RESEARCH ONLY — no source files modified, no production code changed.  
> **Scope**: Exploratory design for combining FoldingAgent geometric reconstruction with Anveshan Track A knowledge structuring.  
> **Output directories**: `notes/origami-hybrid/` (this file) and `research/origami_hybrid/` (prototype skeleton).  
> **Date**: 2025  

---

## Table of Contents

1. [FoldingAgent Deep-Dive](#1-foldingagent-deep-dive)
2. [Anveshan Track A Deep-Dive](#2-anveshan-track-a-deep-dive)
3. [Complementarity Analysis](#3-complementarity-analysis)
4. [Hybrid Pipeline Architecture](#4-hybrid-pipeline-architecture)
5. [Schema / Contract Design](#5-schema--contract-design)
6. [FoldingAgentAdapter Design](#6-foldingagentadapter-design)
7. [Independent Pipeline Structure](#7-independent-pipeline-structure)
8. [Prompt Strategy](#8-prompt-strategy)
9. [Risks and Open Questions](#9-risks-and-open-questions)
10. [Next Steps for Implementation](#10-next-steps-for-implementation)

---

## 1. FoldingAgent Deep-Dive

### 1.1 Architecture Overview

FoldingAgent is a **ReAct-loop origami reconstruction agent**. Given a sequence of real-world origami photos (keyframes), it drives an LLM to interactively operate a 2D geometry simulator until the rendered mesh matches each photo.

```
keyframes.json
     │
     ▼
run_agent()
     ├── _prepare_run()
     │       ├── _load_keyframe_sequence()  → frame paths + colors
     │       ├── _build_backend()           → LLMBackend (Anthropic/Gemini/OpenAI)
     │       └── _build_reviewers()         → OrigamiCritic, OrigamiComparator,
     │                                         OrigamiOverviewCritic
     ▼
OrigamiController(frames, out_dir, paper_colors, critic, overview_critic)
     │
     ▼
ReAct loop (max MAX_ITERATIONS=300 turns)
     ├── backend.chat(messages, system_prompt)  → LLMResponse
     ├── For each ToolCallRequest in response.ordered_content:
     │       controller.dispatch(tool_name, **args) → ToolResult
     └── Loop until stop_reason="end_turn" AND all frames checkpointed
```

**Module roles:**

| Module | Role |
|---|---|
| `main.py` | Entry point, `run_agent()`, ReAct loop |
| `controller.py` | `OrigamiController` — dispatches all LLM tool calls to simulator methods |
| `simulator.py` | `OrigamiLibraryExecutionEngine` — wraps `origami.Origami`; `GeometryState` pydantic model |
| `tools.py` | `AGENT_TOOLS` — canonical tool schema in Anthropic tool-use format |
| `rendering.py` | `render_geometry_diagram()` — Origami → matplotlib → PNG |
| `critic.py` | `OrigamiCritic` — builds 2×2 grid, calls model, returns `CriticResponse` |
| `overview_critic.py` | `OrigamiOverviewCritic` — evaluates full checkpoint sequence at once |
| `comparator.py` | `OrigamiComparator` — picks best attempt when retry budget exhausted |
| `memory.py` | `HistoryLog`, `AttemptTree` — run-state persistence |
| `prompts.py` | Raw string constants for every prompt sent to any model |
| `backends/` | Provider adapters behind the `LLMBackend` ABC (`anthropic_backend.py`, `gemini_backend.py`, `openai_backend.py`) |

The controller exposes 14 tools: `view_frame`, `observe_movement`, `get_current_state`, `render_current`, `add_vertex`, `fold`, `unfold`, `rotate`, `flip`, `save_checkpoint`, `restore_checkpoint`, `get_checkpoint_state`, `generate_checkpoint_overview`, `ask_critic`. Every tool returns `ToolResult(data: dict, images: list[Path])`.

### 1.2 Data Structures: Simulator State and Per-Keyframe Output

#### `GeometryState` (pydantic BaseModel, `simulator.py`)

```python
class GeometryState(BaseModel):
    base_description: str = "square sheet"
    raw_representation: dict[str, Any] | None = None  # from Origami.export()
    operations: list[GeometryFunctionCall] = []         # history of applied ops
    paper_colors: PaperColors = PaperColors()
```

The `raw_representation` dict (from `Origami.export()`) has this exact shape:

```json
{
  "vertices": { "<id>": [x, y] },
  "faces": { "<id>": ["v1", "v2", ...] },
  "faces_orientations": { "<id>": 0 },
  "edges": [ [u, v, "B|F|M|V"] ],
  "layers": [ [ ["face_id", ...] ] ]
}
```

| Field | Type | Semantics |
|---|---|---|
| `vertices` | `dict[str, [float, float]]` | 2D coords, X right, Y up, origin bottom-left. Fresh square: IDs `"1"`–`"4"`. |
| `faces` | `dict[str, list[str]]` | CCW vertex ID lists per face |
| `faces_orientations` | `dict[str, int]` | `0` = front side up, `1` = back side up |
| `edges` | `list[[int, int, str]]` | Each `[u, v, kind]`; kind ∈ `B` boundary, `F` flat, `M` mountain, `V` valley |
| `layers` | `list[list[list[str]]]` | Layer stack bottom→top; each sub-list is a plane of face IDs at the same altitude |

#### `GeometryFunctionCall` (operations history)

```python
class GeometryFunctionCall(BaseModel):
    name: str        # serialized as "function" in checkpoints.json
    parameters: dict # serialized as "params" in checkpoints.json
    assign_to: str | None = None
```

#### Per-keyframe output: `checkpoints.json`

`run_agent()` returns `controller.checkpoints: dict[int, GeometryState]`. This is also persisted to `checkpoints.json`:

```json
{
  "<frame_n>": {
    "raw_representation": { ...geometry dict... },
    "paper_colors": { "front_color": "white", "back_color": "red" },
    "operations": [
      { "function": "fold", "params": {"edge": [1,3], "direction": 1}, "assign_to": null }
    ]
  }
}
```

Keys are frame indices as strings. `raw_representation` is the canonical geometry at that keyframe. `operations` is the FULL history of fold operations applied to reach that state.

### 1.3 Action Space

| Tool | Parameters | Simulator Mutation |
|---|---|---|
| `add_vertex` | `edge: [int,int]`, `position: float (0.0–1.0)` | Subdivides edge, inserts new vertex. New ID = next integer after highest existing. |
| `fold` | `edge: [int,int]`, `direction: int (+1/-1)` | Rotates faces 180° about crease. Edge kind → `M` or `V`. `layers[]` updated. |
| `unfold` | `edge: [int,int]` OR `target: "last"` | Reverses fold geometry. Edge kind → crease marker. `layers[]` reverts. |
| `rotate` | `angle: float` (degrees, positive=CW) | Rotates entire mesh 2D. Vertex coords updated. No topological change. |
| `flip` | `axis: "x"` \| `"y"` \| `"y=x"` \| `"y=-x"` | Reflects all vertex coords. `faces_orientations` flip (0 ↔ 1). |

**Important distinction**: FoldingAgent does NOT use the FOLD file format spec. Its geometry uses `vertices`/`faces` (not `vertices_coords`/`faces_vertices`), binary fold state in `layers` (not fold angle floats), and 2D coordinates only.

### 1.4 Critic Protocol

#### 4-Image Grid Assembly (`critic.py` → `create_critic_grid()`)

```
┌───────┬───────┐
│   A   │   B   │
│source │target │
│ photo │ photo │
├───────┼───────┤
│   C   │   D   │
│source │result │
│diagram│diagram│
└───────┴───────┘
```

- **A** = real photo of frame `n-1` (source)
- **B** = real photo of frame `n` (target / goal)
- **C** = rendered diagram of checkpointed source geometry
- **D** = rendered diagram of current simulator state (should match B)

Cells are resized to max 512px wide, separated by 5-px black borders, labeled A/B/C/D in 24–48px DejaVuSans font.

#### Verdict Schema (`CriticResponse`)

```python
@dataclass
class CriticResponse:
    verdict: CriticVerdict           # Enum: MATCH | MISMATCH | EXTREME_DIVERGANCE
    analysis: str                    # 2-4 sentences
    raw_verdict: str = ""
    anchor_check: str = "no anchor provided"
    discrepancies: list[str] = []
    raw_response: str = ""
```

The LLM returns JSON: `{"verdict": "MATCH"|"MISMATCH"|"EXTREME DIVERGANCE", "analysis": "...", "anchor_check": "...", "discrepancies": [...]}`.

A `MATCH` verdict is automatically downgraded to `MISMATCH` if the analysis simultaneously mentions visible gaps in photo B and claims D shows closed/touching edges (sanity check in `_apply_match_sanity_checks()`).

#### Controller Response to Verdict

| Verdict | Controller Action |
|---|---|
| `MATCH` | `save_checkpoint(frame_n)` and advance |
| `MISMATCH` | Increment `transition_attempt`; `restore_checkpoint(n-1)` and retry |
| `EXTREME DIVERGANCE` | `generate_checkpoint_overview()` + deep rollback |

When `restore_count >= MAX_ATTEMPTS_PER_FRAME` (default 5), the comparator fires: it assembles all attempt renders, sends to `OrigamiComparator.select_best()`, picks the best attempt, rebuilds checkpoints, and locks the frame floor.

### 1.5 Memory / Checkpoint Schema

Three persistence files in the run output directory:

**`checkpoints.json`** — primary geometric truth (shape above in §1.2)

**`history_log.json`** — attempt events and verdicts:
```json
{
  "current_frame": 5,
  "checkpoints": [{"frame_index": 1, "status": "Resolved", "geometry": {...}, "notes": null}],
  "history": [
    {"event": "attempt", "frame": 2, "attempt": 1, "operations": [...], "verdict": "MISMATCH", "reasoning": "..."},
    {"event": "rollback", "from_frame": 3, "to_frame": 2},
    {"event": "attempt", "frame": 2, "attempt": 2, "operations": [...], "verdict": "MATCH", "reasoning": "..."}
  ]
}
```

**`attempt_tree.json`** — branching tree of all attempts:
```json
{
  "root": "n0",
  "current_parent": "n3",
  "nodes": {
    "n0": {
      "id": "n0", "frame_index": 1, "parent": null, "children": ["n1","n2"],
      "actions": ["fold({\"edge\":[1,3],\"direction\":1})"],
      "reasoning": "...",
      "geometry": {...},
      "render_path": "path/to/render.png",
      "critic_grid_path": "path/to/grid.png",
      "critic_verdict": "MATCH",
      "critic_analysis": "..."
    }
  },
  "_checkpoint_node": {"1": "n0", "2": "n3"}
}
```

Full run output layout:
```
out/run_<timestamp>_<model>_<sequence>/
├── metadata.json        # sequence, model, frames_solved, tokens, config
├── frames.json          # resolved absolute paths to keyframe images
├── checkpoints.json     # per-frame geometry states (main output)
├── figs/                # rendered attempt diagrams for comparator
├── logs/
│   ├── agent_log.jsonl
│   ├── history_log.json
│   └── attempt_tree.json
└── llm_calls/           # individual LLM request/response pairs
```

### 1.6 Prompt Strategy

#### Agent System Prompt (`prompts.py` → `SYSTEM_PROMPT` + `SYSTEM_PROMPT_FOOTER`)

Filled at runtime via `prompt_assembler.build_system_prompt()` with `{front_color}`, `{back_color}`, `{num_frames}`. Key sections:

- `═══ YOUR GOAL ═══` — origami reconstruction agent brief
- `═══ SIMULATOR STATE ═══` — full field documentation (`vertices`, `faces`, `edges`, `layers`, `faces_orientations`)
- `═══ AVAILABLE TOOLS ═══` — reference card for all 14 tools
- `═══ CRITIC CONTEXT ═══` — critic's role and authority
- `═══ PRECISION OVER CONVENIENCE ═══` — anti-hallucination: never use 0.5 midpoints lazily
- `═══ THE 2-ATTEMPT RULE ═══` — forces rollback instead of parameter tweaking after 2 mismatches
- `═══ SESSION PARAMETERS ═══` — frame count and goal

#### Critic System Prompt (`prompts.py` → `CRITIC_PROMPT`)

Describes the 4-panel grid (A=source photo, B=target photo, C=source diagram, D=result diagram) and mandates JSON-only output with `verdict`, `analysis`, `anchor_check`, `discrepancies`.

#### Overview Critic System Prompt (`OVERVIEW_CRITIC_PROMPT`)

Receives multi-column PNG. Returns `last_correct_frame`, `first_suspicious_frame`, `analysis`, `per_frame_notes[]`.

#### Opening Task Message

**Fresh run (`TASK_MESSAGE`)**: instructs the agent to start with `save_checkpoint(1)` for the initial flat square, then view frames 1 and 2.

**Resumed run (`RESUME_TASK_MESSAGE`)**: tells the agent which frames are already solved and where to resume.

### 1.7 Dataset: PurelandFold and `keyframes.json`

```json
{
  "name":       "heart",
  "frames":     "frames",
  "front_color": "white",
  "back_color":  "red",
  "keyframes": [4, 10, 38, 50, 89, 99, 122, ...]
}
```

`keyframes` is a list of 1-based global frame indices. The `frames/` subdirectory contains selected keyframes named `NNNNNN.jpg` (zero-padded 6 digits). The `all_frames/` subdirectory contains every video frame for `observe_movement()` filmstrips.

The sequence `name` is slugified and used in the run output directory: `run_<timestamp>_<model>_<sequence>`.

---

## 2. Anveshan Track A Deep-Dive

### 2.1 Pipeline Architecture

```
TrackAPipeline.run(case_id)
  ├── REPLAY mode:
  │     load_manifest() + load_replay_bundle()
  │     KnowledgePackage.model_validate(pkg_raw)
  │     RubricDefinition.model_validate(rubric_raw)
  │     PracticeTask.model_validate(task_raw)
  │     GroundingService.validate_package_grounding()
  │     → TrackAOutputBundle
  │
  └── LIVE mode:
        ModelGateway.extract_knowledge(case_id)
          └── GeminiProviderAdapter:
                MediaService.discover_media() → upload_to_gemini()
                PromptEngine.load_extraction_prompt(manifest, "v1")
                client.models.generate_content(..., response_schema=GeminiExtractionResponse)
                _map_to_dto() → ExtractionResponseDTO
        normalize_dto_to_knowledge_package() → KnowledgePackage
        GroundingService.validate_package_grounding()
        TaskGenerator.generate_rubric()
        TaskGenerator.generate_practice_task()
        → TrackAOutputBundle
```

`ModelGateway` is a thin router: wraps either `ReplayProviderAdapter` (offline) or `GeminiProviderAdapter` (live). Both implement `BaseProviderAdapter` with `extract_knowledge()` and `query_evidence()` methods.

### 2.2 Contract Schemas (Verified from `tracks/common/schemas/`)

#### `KnowledgePackage` (`knowledge.py`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `package_id` | `str` | **Yes** | e.g. `kp.origami.1` |
| `skill_id` | `str` | **Yes** | e.g. `skill-origami-crane` |
| `title` | `str` | **Yes** | |
| `summary` | `str` | **Yes** | |
| `claims` | `List[KnowledgeClaim]` | **Yes** | `min_length=1`; model_validator checks for duplicate `claim_id` |
| `consent` | `ConsentMetadata` | **Yes** | |
| `expert_review` | `Optional[ExpertReview]` | No | `None` allowed; `enforce_approved=True` requires `APPROVED` status |

#### `KnowledgeClaim` (`knowledge.py`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `claim_id` | `str` | **Yes** | Unique; pattern `CLM-01` or canonical IDs like `claim-prelim-square` |
| `claim_type` | `ClaimType` | **Yes** | `step` \| `cue` \| `condition` \| `exception` \| `failure_mode` |
| `statement` | `str` | **Yes** | Free text |
| `is_observed` | `bool` | **Yes** (default `True`) | `True` = directly observed; `False` = model inference |
| `evidence_refs` | `List[EvidenceRef]` | **Yes** | `min_length=1` |

#### `EvidenceRef` (`evidence.py`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `evidence_id` | `str` | **Yes** | Pattern: `ev.<case_id>.<prefix>.<seq:02d>` |
| `source_id` | `str` | **Yes** | e.g. `src-origami-tavin-2010` |
| `modality` | `Modality` | **Yes** | `video` \| `audio` \| `image` \| `text` \| `sensor` |
| `start_sec` | `Optional[float]` | No | `ge=0.0` |
| `end_sec` | `Optional[float]` | No | `ge=0.0`; model_validator enforces `end_sec >= start_sec` |
| `cue_excerpt` | `Optional[str]` | No | Observable description |
| `verification_state` | `VerificationState` | **Yes** (default `OBSERVED`) | `observed` \| `inferred` \| `unverified` |
| `confidence` | `float` | **Yes** (default `1.0`) | `ge=0.0, le=1.0` |

#### `RubricDefinition` / `RubricCriterion` (`rubric.py`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `rubric_id` | `str` | **Yes** | e.g. `rubric.origami.1` |
| `skill_id` | `str` | **Yes** | Must match `KnowledgePackage.skill_id` |
| `title` | `str` | **Yes** | |
| `description` | `Optional[str]` | No | |
| `criteria` | `List[RubricCriterion]` | **Yes** | `min_length=1`; no duplicate `criterion_id` |
| `passing_score` | `Optional[float]` | No | `ge=0.0`; ≤ sum of all `criterion.weight` |

Per `RubricCriterion`: `criterion_id` (str, required), `name` (str, required), `description` (str, required), `observable_indicator` (str, required), `weight` (float, `gt=0.0`, default `1.0`), `required` (bool, default `True`).

#### `PracticeTask` / `TaskConstraint` (`practice.py`)

| Field | Type | Required |
|---|---|---|
| `task_id` | `str` | **Yes** |
| `package_id` | `str` | **Yes** |
| `rubric_id` | `str` | **Yes** |
| `title` | `str` | **Yes** |
| `instructions` | `str` | **Yes** |
| `constraints` | `List[TaskConstraint]` | No (default `[]`) |
| `target_criteria_ids` | `List[str]` | No (default `[]`) |

`TaskConstraint` fields: `constraint_type` (str, required), `description` (str, required), `value` (Optional[str]).

### 2.3 Epistemic Discipline: OBSERVED / INFERRED / UNVERIFIED

Three `VerificationState` values govern every `EvidenceRef`:

| State | Meaning | Confidence Constraint |
|---|---|---|
| `OBSERVED` | Directly seen/heard in source media | 0.0–1.0 (typically 1.0) |
| `INFERRED` | Model interpretation, not directly visible | ≤ 0.5 in goal-conditioned mode; capped at 0.5 by normalizer |
| `UNVERIFIED` | No supporting evidence | Reserved for future use |

`KnowledgeClaim.is_observed` is the boolean complement: `True` ↔ `OBSERVED` on evidence refs.

`GroundingService.enforce_epistemological_state()` raises `CONTRACT_VIOLATION` if:
- Forward/corrective mode: `is_observed == False` but any `ev.verification_state == OBSERVED`
- Goal-conditioned: same, plus `ev.confidence > 0.5` for inferred claims

`GroundingService.validate_package_grounding()` returns `uncertainty_flags: List[str]` — claim IDs of all INFERRED or `is_observed=False` claims.

### 2.4 Frozen Seam: What Cannot Change

From `tracks/common/schemas/__init__.py`, the 8 frozen cross-track contracts are:
1. `EvidenceRef`
2. `KnowledgePackage`
3. `RubricDefinition`
4. `PracticeTask`
5. `LearnerAttempt`
6. `Evaluation`
7. `Feedback`
8. `TransmissionRecord`

Track B consumes `KnowledgePackage`, `RubricDefinition`, and `PracticeTask` produced by Track A. **These field names, enum values, required/optional semantics, and validation rules CANNOT be changed without breaking Track B.** The `AGENTS.md` Single-Source Rule: exactly one authoritative source at `tracks/common/schemas/`.

### 2.5 Origami Case: FORWARD Mode, ENGINEERING_FIXTURE, 5-Criterion Rubric

- `case_id`: `origami`, `transmission_mode`: `forward`, `status`: `ENGINEERING_FIXTURE`, `runtime_class`: `REPLAY`
- Source: `https://upload.wikimedia.org/.../OrigamiCrane.ogv.480p.webm` (Tavin, CC BY 3.0, 335s)
- Stable source ID: `src-origami-tavin-2010` (use this, NOT `src-origami-01`)
- 2 replay claims: `claim-prelim-square` (step, t=10–22s SYNTHETIC) and `claim-petal-inversion` (step, t=25–38s SYNTHETIC)
- 3 rubric criteria: `CRIT-CORNER-ALIGN` (weight=3, required), `CRIT-VALLEY-FOLD` (weight=4, required), `CRIT-BONE-CREASE` (weight=3, not required); `passing_score=7`
- The k4 branch adds 5 richer criteria: `CRIT-ORI-ORDER`, `CRIT-ORI-COMPLETE`, `CRIT-ORI-CLEAN`, `CRIT-ORI-KEYSTEP`, `CRIT-ORI-FINAL`

---

## 3. Complementarity Analysis

For each dimension, a winner is identified along with rationale:

### Geometric Fidelity → **FoldingAgent wins**

FoldingAgent produces exact 2D parametric state at every keyframe: vertex coordinates, face topology, edge crease assignments (M/V/F/B), layer stacking order. This is machine-verifiable and supports replaying the fold sequence. Anveshan has zero geometry fields in its schemas — `statement` and `cue_excerpt` are free text with no structured geometry type.

### Epistemic Discipline → **Anveshan wins**

Anveshan's OBSERVED/INFERRED/UNVERIFIED trinary, confidence calibration, and `GroundingService` enforcement provide a rigorous epistemic framework. FoldingAgent has no equivalent — a MATCH verdict from the critic means geometric correspondence, not provenance. A comparator-selected state ("best of 5 attempts") is INFERRED in epistemic terms, but FoldingAgent makes no such distinction.

### Knowledge Structuring → **Anveshan wins**

Anveshan packages knowledge into typed `KnowledgeClaim` objects (step / cue / condition / exception / failure_mode), with a consent chain, expert review gate, and cross-validated `RubricDefinition`. FoldingAgent produces raw geometry + operations lists with no semantic typing, no provenance, and no teaching-oriented structure.

### Teaching Utility → **Anveshan wins**

`RubricCriterion.observable_indicator` gives human-evaluable criteria with weights and required flags. `PracticeTask` provides structured learner instructions and material constraints. `TransmissionRecord` measures `transmission_gain`. FoldingAgent produces nothing oriented toward learner feedback.

### Visual Grounding → **FoldingAgent wins**

FoldingAgent renders a PNG diagram at every keyframe, assembles a 2×2 critic grid for visual comparison, and saves both source photos and rendered diagrams. The critic analysis is grounded in these visuals. Anveshan's evidence refs point to video segments but produce no rendered diagrams; the extracted `cue_excerpt` is prose, not a visual artifact.

### Provenance → **Anveshan wins**

Anveshan tracks `ConsentMetadata` (contributor, scope, revocability), `ExpertReview` lifecycle (PENDING → APPROVED/REVISED/REJECTED), and `LineageMetadata` (SHA-256 provenance hash, adaptation notes, parent transmission chain). FoldingAgent has no provenance chain — there is no consent model and no attribution linking geometric output back to the source video's license.

### Rollback / Replanning → **FoldingAgent wins**

FoldingAgent's `AttemptTree` records every branch of the exploration, the comparator selects the best attempt when the budget is exhausted, and `restore_checkpoint()` enables arbitrary rollback. The `_locked_checkpoints` and `_min_restore_frame` mechanism prevents regressing past stable frames. Anveshan has no equivalent — it runs a single-pass extraction.

### Overlap

Both systems use VLMs (Vision-Language Models) to analyze video frames and produce per-step structured output. Both have a concept of "source frame" and "output at frame N." Both process temporal sequences.

### Conflict

FoldingAgent produces raw geometry (vertex coordinates, edge assignments) — machine-readable but not inherently natural-language claims. Anveshan needs grounded natural-language claims backed by observable source evidence. The bridge must convert geometric facts into claim statements while assigning correct epistemic states: a MATCH-verified state is `OBSERVED`; a comparator-selected state is `INFERRED`.

---

## 4. Hybrid Pipeline Architecture

### ASCII Architecture Diagram

```
                        VIDEO INPUT
                  (<origami_instruction_video>)
                  (placeholder — user will supply)
                             │
                             ▼
              ┌──────────────────────────────┐
              │  KeyframeExtractor           │
              │  (FoldingAgent preprocessing)│
              │  keyframes.json extraction   │
              │  → frame paths + colors      │
              └──────────────┬───────────────┘
                             │ frame_paths[], keyframes.json
                             ▼
              ┌──────────────────────────────────────────┐
              │  FoldingAgentCore                        │
              │  ReAct loop (MAX_ITERATIONS=300)         │
              │    ├── LLMBackend (Anthropic/Gemini)     │
              │    ├── OrigamiController                 │
              │    │     └── OrigamiLibraryExecution     │
              │    │           Engine (simulator)        │
              │    └── OrigamiCritic / Comparator        │
              └──────────────────────────────────────────┘
                             │ checkpoints: dict[int, GeometryState]
                             │ attempt_tree.json, history_log.json
                             ▼
              ┌──────────────────────────────────────────┐
              │  GeometricStateLog                       │
              │  checkpoints.json (per-keyframe)         │
              │  ├── raw_representation (vertices,       │
              │  │   faces, edges, layers)               │
              │  ├── operations[] (fold/unfold history)  │
              │  └── rendered PNGs (figs/)               │
              └──────────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────────────┐
              │  FoldingAgentAdapter  [NEW MODULE]       │
              │  (research/origami_hybrid/adapter.py)    │
              │  ├── load_checkpoints()                  │
              │  ├── to_knowledge_claims()               │
              │  ├── to_evidence_refs()                  │
              │  ├── to_rubric_definition()              │
              │  ├── to_practice_tasks()                 │
              │  └── to_knowledge_package()              │
              └──────────────────────────────────────────┘
                             │ raw KnowledgeClaim[], EvidenceRef[]
                             │ (geometric facts, not yet epistemically tagged)
                             ▼
              ┌──────────────────────────────────────────┐
              │  EvidenceGrounder  [NEW MODULE]          │
              │  (research/origami_hybrid/grounding.py)  │
              │  ├── Anveshan-style LLM call             │
              │  ├── Assigns verification_state          │
              │  │   (OBSERVED for MATCH-verified;       │
              │  │    INFERRED for comparator-selected)  │
              │  └── Calibrates confidence per claim     │
              └──────────────────────────────────────────┘
                             │ epistemically-tagged claims
                             ▼
              ┌──────────────────────────────────────────┐
              │  KnowledgePackage Builder                │
              │  ├── RubricSynthesizer                  │
              │  │   (rubric_synth.py)                  │
              │  │   geometric state → 5 observable      │
              │  │   rubric criteria                    │
              │  └── PracticeTaskGenerator              │
              │       fold state + rubric → task         │
              └──────────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────────────────┐
              │  OUTPUT: valid Anveshan contracts        │
              │  ├── KnowledgePackage (JSON)             │
              │  ├── RubricDefinition (JSON)             │
              │  ├── PracticeTask (JSON)                 │
              │  ├── run_metadata.json   (RunMetadataDTO)│
              │  ├── expert_review_sheet.md (Markdown)   │
              │  └── fold_state_log.json (sidecar)       │
              │      crease_evidence.json (sidecar)      │
              └──────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Inputs | Outputs | Responsibilities |
|---|---|---|---|
| **KeyframeExtractor** | Raw video file (placeholder — user supplies) | `keyframes.json`, extracted frame JPEGs, `video_meta.json` (fps, duration, resolution) | Decode video via PyAV; probe FPS; select representative frames; build `keyframes.json` |
| **FoldingAgentCore** | `keyframes.json`, frame images | `checkpoints.json`, `attempt_tree.json`, `history_log.json`, `metadata.json`, rendered PNGs | Run the ReAct loop (simulator from local FoldingAgentSimulator clone, MIT); produce verified geometric state per keyframe |
| **GeometricStateLog** | `checkpoints.json` + rendered PNGs | In-memory `dict[int, GeometryState]` | Persist and load geometric states; surface render paths and critic verdicts |
| **FoldingAgentAdapter** | `GeometricStateLog`, `keyframes.json`, `video_meta.json` (fps from PyAV probe) | Raw `KnowledgeClaim[]`, `EvidenceRef[]`, prototype `RubricDefinition`, `PracticeTask` | Convert FoldingAgent output to Anveshan contract shapes; no epistemic assignment yet; timestamps = `frame_idx / fps` |
| **EvidenceGrounder** | Raw claims, rendered PNGs, `attempt_tree.json` | Epistemically-tagged `KnowledgeClaim[]`, `EvidenceRef[]` | Assign `verification_state` (OBSERVED / INFERRED), calibrate `confidence`, enforce grounding rules |
| **RubricSynthesizer** | Full `GeometryState` sequence, critic analyses | `RubricDefinition` with 5 synthesized observable criteria (`CRIT-HYB-1` – `CRIT-HYB-5`) | Translate geometric facts (edge assignments, layer counts) into human-evaluable observable indicators. **Decision: synthesized criteria only — do NOT use canonical CRIT-CORNER-ALIGN etc.** |
| **PracticeTaskGenerator** | `KnowledgePackage`, `RubricDefinition` | `PracticeTask` | Generate learner instructions and constraints referencing the synthesized rubric criteria |
| **RunMetadataWriter** | `RunMetadataDTO` (constructed by adapter) | `output/run_metadata.json` | Emit model/provider/prompt/runtime metadata following Track A `run_pipeline.py` convention |
| **ExpertReviewExporter** | `KnowledgePackage`, case manifest | `output/expert_review_sheet.md` | Emit Markdown inspection sheet for human review and correction before downstream use |

---

## 5. Schema / Contract Design

### 5.1 Can We Stay Within the Frozen Seam?

**Yes, for the primary contracts.** The Anveshan frozen seam (`EvidenceRef`, `KnowledgePackage`, `RubricDefinition`, `PracticeTask`) has enough flexibility to carry fold-geometry information without any schema changes:

- `EvidenceRef.cue_excerpt` (Optional[str]) can hold geometry-prose or a reference to a sidecar file
- `EvidenceRef.modality` = `Modality.IMAGE` for rendered PNGs
- `EvidenceRef.source_id` = `"src-fa-checkpoint-<run_id>"` for geometry artifacts
- `KnowledgeClaim.statement` can embed geometric notation
- `RubricCriterion.observable_indicator` can reference geometric predicates

**Two sidecar JSON files** carry the rich geometric data without touching the seam.

### 5.2 Embedding Fold Geometry as Evidence

For each keyframe `n`, create an `EvidenceRef` pointing to the rendered PNG:

```json
{
  "evidence_id": "ev.origami.frame.01",
  "source_id": "src-fa-checkpoint-<run_id>",
  "modality": "image",
  "start_sec": null,
  "end_sec": null,
  "cue_excerpt": "Rendered diagram: mountain fold edge [1,3]; valley fold edge [2,5]; faces_orientations={'1':0,'2':0}; 3 layer planes.",
  "verification_state": "observed",
  "confidence": 1.0
}
```

For video-backed evidence at the same keyframe (using the actual Tavin video), add a SECOND `EvidenceRef`:

```json
{
  "evidence_id": "ev.origami.video.01",
  "source_id": "src-origami-tavin-2010",
  "modality": "video",
  "start_sec": 22.0,
  "end_sec": 28.0,
  "cue_excerpt": "Agent verified geometric state MATCH against video frame 000038.jpg; critic analysis: symmetric diamond base with two triangular flaps.",
  "verification_state": "observed",
  "confidence": 1.0
}
```

The sidecar file `crease_evidence.json` (below) holds the full geometry dict for downstream tooling, linked from `cue_excerpt` by a path reference.

### 5.3 Mapping FoldingAgent Keyframe States to KnowledgeClaims

Each verified keyframe checkpoint becomes one `KnowledgeClaim`:

| FoldingAgent field | → Anveshan field | Notes |
|---|---|---|
| `frame_n` (int) | `claim_id = f"CLM-{frame_n:02d}"` | Sequential |
| `operations_delta[*].name` | `claim_type = ClaimType.STEP` | All transitions are steps |
| `critic_analysis` (from `attempt_tree.nodes[checkpoint_node].critic_analysis`) | `statement` | Natural-language description of the geometric state reached |
| `critic_verdict == "MATCH"` | `is_observed = True` | MATCH = directly verified against photo |
| comparator-selected (no MATCH) | `is_observed = False` | Comparator selection = INFERRED |
| `[ev.origami.frame.{n:02d}, ev.origami.video.{n:02d}]` | `evidence_refs` | Both rendered PNG and video segment |

Example for frame 3:

```python
KnowledgeClaim(
    claim_id="CLM-03",
    claim_type=ClaimType.STEP,
    statement="Bird base preliminary fold: diagonal creases on both axes; all four corners meet at center; faces_orientations all 0 (front side up).",
    is_observed=True,   # critic returned MATCH
    evidence_refs=[
        EvidenceRef(evidence_id="ev.origami.frame.03", source_id="src-fa-checkpoint-run001",
                    modality=Modality.IMAGE, cue_excerpt="...", verification_state=VerificationState.OBSERVED, confidence=1.0),
        EvidenceRef(evidence_id="ev.origami.video.03", source_id="src-origami-tavin-2010",
                    modality=Modality.VIDEO, start_sec=38.0, end_sec=48.0,
                    cue_excerpt="Fold verified against frame 000099.jpg; both diagonal creases visible.",
                    verification_state=VerificationState.OBSERVED, confidence=0.95),
    ]
)
```

### 5.4 Mapping Mountain/Valley Assignment to RubricCriterion observable_indicator

For each edge with crease assignment from `raw_representation["edges"]`:

- Edge `[u, v, "M"]` → mountain fold indicator: `f"Edge [{u},{v}] is a mountain fold (convex ridge when viewed from front face)."`
- Edge `[u, v, "V"]` → valley fold indicator: `f"Edge [{u},{v}] is a valley fold (concave trough when viewed from front face)."`

The `RubricCriterion` becomes:

```python
RubricCriterion(
    criterion_id="CRIT-VALLEY-FOLD",
    name="Valley Fold Crease Fidelity",
    description="Learner correctly inverts lateral crease to valley fold orientation.",
    observable_indicator="Edge [2,5] assigned valley (V) in simulator state at keyframe 3; "
                         "no mountain (M) edges on symmetry axis; "
                         "crease polarity matches diagram: convex ridge vs concave trough.",
    weight=4.0,
    required=True,
)
```

The canonical origami criteria (`CRIT-CORNER-ALIGN`, `CRIT-VALLEY-FOLD`, `CRIT-BONE-CREASE`) from the replay bundle are **not used** in the hybrid pipeline. Instead the `RubricSynthesizer` derives 5 geometry-grounded criteria (`CRIT-HYB-1` through `CRIT-HYB-5`) from the actual edge assignments and layer structure of the FoldingAgent reconstruction. See §8b for the RubricSynthesizer prompt strategy.

### 5.5 New JSON Sidecar Schemas

These files live in the `research/origami_hybrid/` output directory and do NOT modify the frozen seam.

#### `fold_state_log.json` — Geometric sidecar per run

```json
{
  "$schema": "fold_state_log_v1",
  "run_id": "run_20250101_120000_gemini_crane",
  "video_path": "data/crane/frames/",
  "keyframes_json": "data/crane/keyframes.json",
  "fps": 24.0,
  "total_frames": 509,
  "states": [
    {
      "frame_index": 1,
      "keyframe_global_index": 4,
      "timestamp_sec": 0.167,
      "critic_verdict": "MATCH",
      "transition_attempt_count": 1,
      "selected_by_comparator": false,
      "raw_representation": {
        "vertices": { "1": [0.0, 0.0], "2": [1.0, 0.0], "3": [1.0, 1.0], "4": [0.0, 1.0] },
        "faces": { "1": ["1","2","3","4"] },
        "faces_orientations": { "1": 0 },
        "edges": [[1,2,"B"],[2,3,"B"],[3,4,"B"],[4,1,"B"]],
        "layers": [[["1"]]]
      },
      "operations_delta": [],
      "render_png_path": "figs/attempt_n0_render.png",
      "critic_analysis": "Initial flat square, all boundary edges, single face."
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `run_id` | str | Matches FoldingAgent run directory name |
| `fps` | float | Video FPS, used for timestamp conversion |
| `states[*].frame_index` | int | 1-based index within the agent's keyframe sequence |
| `states[*].keyframe_global_index` | int | Global video frame index from `keyframes.json` |
| `states[*].timestamp_sec` | float | `keyframe_global_index / fps` |
| `states[*].critic_verdict` | str | `"MATCH"` \| `"MISMATCH"` \| `"EXTREME DIVERGANCE"` \| `"COMPARATOR"` |
| `states[*].selected_by_comparator` | bool | If `true`, `verification_state=INFERRED`, `confidence<=0.5` |
| `states[*].raw_representation` | dict | Full geometry dict from `GeometryState.raw_representation` |
| `states[*].operations_delta` | list | `GeometryFunctionCall` list since previous checkpoint |
| `states[*].render_png_path` | str | Relative path to rendered PNG |
| `states[*].critic_analysis` | str | Prose from `CriticResponse.analysis` |

#### `crease_evidence.json` — Per-edge crease grounding

```json
{
  "$schema": "crease_evidence_v1",
  "run_id": "run_20250101_120000_gemini_crane",
  "keyframe_crease_maps": [
    {
      "frame_index": 3,
      "mountain_edges": [[1, 3]],
      "valley_edges": [[2, 5], [4, 6]],
      "boundary_edges": [[1,2],[2,3],[3,4],[4,1]],
      "flat_edges": [],
      "layer_count": 4,
      "face_count": 8,
      "faces_with_back_up": ["3", "7"],
      "evidence_id": "ev.origami.frame.03",
      "render_png_path": "figs/attempt_n3_render.png"
    }
  ]
}
```

This sidecar provides structured lookup for the `RubricSynthesizer` without embedding raw geometry in the Anveshan contracts.

---

## 6. FoldingAgentAdapter Design

The adapter lives at `research/origami_hybrid/adapter.py`. It converts FoldingAgent's output directory into Anveshan contract objects. Field mappings use actual field names from both codebases as verified above.

```python
from pathlib import Path
from dataclasses import dataclass
import json
from typing import Any

# Anveshan frozen seam imports (read-only)
# NOTE: the adapter does NOT import from tracks/track-a/src/
# It reconstructs the schema objects directly or uses the common schemas path.

@dataclass
class FoldCheckpoint:
    """Internal representation of one parsed checkpoint entry."""
    frame_index: int                        # int key from checkpoints.json
    raw_representation: dict[str, Any]      # GeometryState.raw_representation
    operations: list[dict]                  # list of {"function": str, "params": dict, "assign_to": str|None}
    paper_colors: dict                      # {"front_color": str, "back_color": str}
    critic_verdict: str                     # from attempt_tree._checkpoint_node → node.critic_verdict
    critic_analysis: str                    # from attempt_tree node.critic_analysis
    selected_by_comparator: bool            # True if no MATCH verdict (critic_verdict != "MATCH")
    render_png_path: Path | None            # absolute path to rendered PNG
    timestamp_sec: float | None             # keyframe_global_index / fps


class FoldingAgentAdapter:
    """
    Converts FoldingAgent output directory to Anveshan contract objects.

    Does NOT call any LLM. Pure data transformation.
    Epistemic assignment (OBSERVED vs INFERRED) is done here based on
    critic_verdict: MATCH → OBSERVED, comparator-selected → INFERRED.
    """

    def __init__(self, fold_output_dir: Path, video_path: Path):
        """
        Parameters
        ----------
        fold_output_dir : Path
            Path to a FoldingAgent run directory, e.g.
            out/run_20250101_120000_gemini_crane/
            Must contain: checkpoints.json, logs/attempt_tree.json,
            logs/history_log.json, frames.json
        video_path : Path
            Path to the source video, used only for source_id derivation
            and timestamp grounding.
        """
        self.fold_output_dir = fold_output_dir
        self.video_path = video_path
        self._checkpoints: list[FoldCheckpoint] | None = None
        self._keyframes_data: dict | None = None

    def load_checkpoints(self) -> list[FoldCheckpoint]:
        """
        Parse checkpoints.json and attempt_tree.json into FoldCheckpoint list.

        Field mappings:
          checkpoints.json key (str)        → FoldCheckpoint.frame_index (int)
          checkpoints.json[n].raw_representation → FoldCheckpoint.raw_representation
          checkpoints.json[n].operations[]  → FoldCheckpoint.operations
            each {"function": str, "params": dict, "assign_to": str|None}
            (GeometryFunctionCall serialized: name→"function", parameters→"params")
          checkpoints.json[n].paper_colors  → FoldCheckpoint.paper_colors
            {"front_color": str, "back_color": str}  (PaperColors.model_dump)

          attempt_tree.json._checkpoint_node[str(n)] → node_id
          attempt_tree.json.nodes[node_id].critic_verdict → FoldCheckpoint.critic_verdict
          attempt_tree.json.nodes[node_id].critic_analysis → FoldCheckpoint.critic_analysis
          attempt_tree.json.nodes[node_id].render_path → FoldCheckpoint.render_png_path

        Comparator detection: selected_by_comparator = (critic_verdict != "MATCH")
        Timestamp: derived from frames.json keyframe global index ÷ fps
        """
        checkpoints_path = self.fold_output_dir / "checkpoints.json"
        attempt_tree_path = self.fold_output_dir / "logs" / "attempt_tree.json"
        frames_path = self.fold_output_dir / "frames.json"

        with open(checkpoints_path) as f:
            raw_checkpoints: dict[str, dict] = json.load(f)
        with open(attempt_tree_path) as f:
            attempt_tree: dict = json.load(f)
        with open(frames_path) as f:
            frames_data: list[str] = json.load(f)  # list of absolute paths

        checkpoint_node_map: dict[str, str] = attempt_tree.get("_checkpoint_node", {})
        nodes: dict[str, dict] = attempt_tree.get("nodes", {})

        result = []
        for frame_str, ckpt in raw_checkpoints.items():
            frame_n = int(frame_str)
            node_id = checkpoint_node_map.get(frame_str)
            node = nodes.get(node_id, {}) if node_id else {}

            critic_verdict = node.get("critic_verdict", "UNKNOWN")
            critic_analysis = node.get("critic_analysis", "")
            render_path_str = node.get("render_path")
            render_png = Path(render_path_str) if render_path_str else None
            selected_by_comparator = critic_verdict != "MATCH"

            # Timestamp from frame index (frame_n-1 is 0-based index into frames list)
            timestamp_sec = None
            # frames_data is list of paths; global frame index is embedded in filename
            # e.g. "000038.jpg" → global_idx=38; timestamp = 38 / fps
            # fps is NOT stored by FoldingAgent; caller must pass it or read from video

            result.append(FoldCheckpoint(
                frame_index=frame_n,
                raw_representation=ckpt["raw_representation"],
                operations=ckpt.get("operations", []),
                paper_colors=ckpt.get("paper_colors", {"front_color": "white", "back_color": "lightblue"}),
                critic_verdict=critic_verdict,
                critic_analysis=critic_analysis,
                selected_by_comparator=selected_by_comparator,
                render_png_path=render_png,
                timestamp_sec=timestamp_sec,
            ))

        self._checkpoints = sorted(result, key=lambda c: c.frame_index)
        return self._checkpoints

    def to_evidence_refs(self) -> list:
        """
        Produce one EvidenceRef per checkpoint: modality=IMAGE, pointing to rendered PNG.
        A second EvidenceRef (modality=VIDEO) is added if timestamp is available.

        Field mappings:
          FoldCheckpoint.frame_index      → evidence_id suffix: f"ev.origami.frame.{n:02d}"
          "src-fa-checkpoint-<run_dir>"   → EvidenceRef.source_id  (image evidence)
          "src-origami-tavin-2010"        → EvidenceRef.source_id  (video evidence)
          Modality.IMAGE                  → EvidenceRef.modality    (for render PNG)
          Modality.VIDEO                  → EvidenceRef.modality    (for video segment)
          FoldCheckpoint.critic_analysis  → EvidenceRef.cue_excerpt
          OBSERVED if not selected_by_comparator; INFERRED otherwise
            → EvidenceRef.verification_state
          1.0 if MATCH; 0.5 if comparator-selected
            → EvidenceRef.confidence
          FoldCheckpoint.timestamp_sec    → EvidenceRef.start_sec
          next checkpoint timestamp_sec   → EvidenceRef.end_sec
        """
        ...

    def to_knowledge_claims(self) -> list:
        """
        Produce one KnowledgeClaim per checkpoint (excluding frame 1 if it is the
        initial flat square with no transitions).

        Field mappings:
          f"CLM-{frame_n:02d}"                → KnowledgeClaim.claim_id
          ClaimType.STEP                       → KnowledgeClaim.claim_type
          FoldCheckpoint.critic_analysis       → KnowledgeClaim.statement
            (enriched by joining operations_delta descriptions)
          not FoldCheckpoint.selected_by_comparator → KnowledgeClaim.is_observed
          [image_ev_ref, video_ev_ref]         → KnowledgeClaim.evidence_refs
        """
        ...

    def to_rubric_definition(self) -> object:
        """
        Produce a RubricDefinition from the geometric state sequence.

        Strategy: synthesize 5 criteria from fold geometry (CRIT-HYB-1 through CRIT-HYB-5).
        Criteria are derived from edge M/V assignments, layer counts, vertex alignment,
        and final-state match across the keyframe sequence.
        Canonical origami criteria (CRIT-CORNER-ALIGN etc.) are NOT used here.

        Field mappings:
          "rubric.origami-hybrid.1"            → RubricDefinition.rubric_id
          "skill-origami-crane"                → RubricDefinition.skill_id
          Mountain/valley edge assignments from raw_representation["edges"]
            → RubricCriterion.observable_indicator
            e.g.: "Edge [1,3] is assigned mountain (M) at keyframe 3; visible as convex
                   ridge on front face."
          FoldCheckpoint.operations[-1].name  → informs criterion name
            (fold → crease criterion; rotate/flip → orientation criterion)
        """
        ...

    def to_practice_tasks(self) -> list:
        """
        Produce one PracticeTask for the full fold sequence.

        Field mappings:
          "task.origami-hybrid.1"              → PracticeTask.task_id
          KnowledgePackage.package_id          → PracticeTask.package_id
          RubricDefinition.rubric_id           → PracticeTask.rubric_id
          "Fold Origami Crane — Hybrid Pipeline" → PracticeTask.title
          Summary of all KnowledgeClaim.statement (steps 1..N) → PracticeTask.instructions
          [{"constraint_type": "material", "description": "Standard 150mm square kami paper",
             "value": "150mm"}]                → PracticeTask.constraints
          All RubricCriterion.criterion_id      → PracticeTask.target_criteria_ids
        """
        ...

    def to_knowledge_package(self) -> object:
        """
        Compose the full KnowledgePackage from the other to_* methods.

        Field mappings:
          "kp.origami-hybrid.1"                → KnowledgePackage.package_id
          "skill-origami-crane"                → KnowledgePackage.skill_id
          "Origami Crane — Hybrid Geometric Reconstruction" → KnowledgePackage.title
          Summary built from operations across all checkpoints → KnowledgePackage.summary
          self.to_knowledge_claims()           → KnowledgePackage.claims
          ConsentMetadata(
            contributor_name="FoldingAgent Hybrid Pipeline",
            consent_scope="research_prototype",
            notes="User-supplied origami video. Add attribution here before use beyond research folder."
          )                                    → KnowledgePackage.consent
          ExpertReview(
            reviewer_name="Pending — hybrid prototype",
            status=ReviewStatus.PENDING
          )                                    → KnowledgePackage.expert_review
        """
        ...
```

**Critical notes on field mapping precision:**
- `checkpoints.json` stores `GeometryFunctionCall.name` as key `"function"` (not `"name"`) and `GeometryFunctionCall.parameters` as key `"params"` (not `"parameters"`) — the Pydantic model serializes with aliased keys.
- The `attempt_tree.json` structure has `_checkpoint_node: dict[str, str]` mapping frame index strings to node IDs, then `nodes: dict[str, node]` where each node has `critic_verdict`, `critic_analysis`, and `render_path`.
- `frames.json` contains absolute paths. Frame filenames encode global frame indices as `NNNNNN.jpg`. FPS is NOT stored by FoldingAgent; it must be derived from the source video (e.g., via PyAV or hard-coded from `keyframes.json` metadata if available).

---

## 7. Independent Pipeline Structure

```
research/origami_hybrid/
  README.md                   # scope disclaimer + usage
  pipeline.py                 # entry point
  adapter.py                  # FoldingAgentAdapter
  grounding.py                # EvidenceGrounder
  rubric_synth.py             # RubricSynthesizer
  schemas/
    fold_state_log.json        # sidecar schema for geometric data
    crease_evidence.json       # sidecar schema for crease pattern evidence
  tests/
    test_adapter.py
    fixtures/
      sample_checkpoint.json
      sample_attempt_tree.json
```

### Module Descriptions

**`pipeline.py`** — Entry point

```python
def run_hybrid_pipeline(
    video_path: Path,
    keyframes_json: Path,
    fold_output_dir: Path | None,  # if None, run FoldingAgent first
    output_dir: Path,
    fps: float = 24.0,
) -> dict:
    """
    Orchestrates the full hybrid pipeline:
    1. If fold_output_dir is None: invoke FoldingAgent (requires FOLDINGAGENT env config)
    2. FoldingAgentAdapter.load_checkpoints()
    3. FoldingAgentAdapter.to_evidence_refs() + to_knowledge_claims()
    4. EvidenceGrounder.enrich_claims(claims, evidence_refs, output_dir)
    5. RubricSynthesizer.synthesize(checkpoints, claims)
    6. FoldingAgentAdapter.to_practice_tasks()
    7. FoldingAgentAdapter.to_knowledge_package()
    8. Write fold_state_log.json and crease_evidence.json sidecars
    9. Return {"package": ..., "rubric": ..., "practice_task": ..., "sidecars": [...]}
    """
```

**`adapter.py`** — `FoldingAgentAdapter` (fully specified in §6)

**`grounding.py`** — `EvidenceGrounder`

Calls an Anveshan-style LLM to add the epistemic layer:
- `enrich_claims(claims, evidence_refs, rendered_pngs, output_dir) -> list[KnowledgeClaim]`
  - For each claim, loads the rendered PNG as a base64 image
  - Sends the fold state JSON + rendered PNG to Gemini with the EvidenceGrounder prompt (§8)
  - Receives a structured description and sets `cue_excerpt` on the evidence ref
  - Validates `verification_state` consistency (MATCH → OBSERVED; comparator → INFERRED)
  - Caps `confidence` at 0.5 for INFERRED claims (matches Anveshan normalizer behavior)

**`rubric_synth.py`** — `RubricSynthesizer`

Converts geometric state sequence to rubric criteria:
- `synthesize(checkpoints: list[FoldCheckpoint], claims: list[KnowledgeClaim]) -> RubricDefinition`
  - Extracts all unique mountain/valley edge assignments across all checkpoints
  - Identifies key transitions (folds that change `faces_orientations`, large layer count increases)
  - Sends state sequence to Gemini with the RubricSynthesizer prompt (§8)
  - Produces exactly 5 `RubricCriterion` objects grounded to specific frame indices and edge IDs

**`schemas/fold_state_log.json`** — JSON Schema (draft-07) for the fold state sidecar (structure in §5.5)

**`schemas/crease_evidence.json`** — JSON Schema (draft-07) for the crease evidence sidecar (structure in §5.5)

**`tests/test_adapter.py`** — Unit tests for `FoldingAgentAdapter`:
- `test_load_checkpoints_from_fixture()` — loads `sample_checkpoint.json` and `sample_attempt_tree.json`, asserts correct `FoldCheckpoint` fields
- `test_verdict_to_is_observed()` — MATCH → `is_observed=True`, non-MATCH → `is_observed=False`
- `test_evidence_ref_fields()` — correct `evidence_id` pattern, `source_id`, `modality`
- `test_operations_delta_parsing()` — `"function"` key in JSON maps to `operations[*].name` in `FoldCheckpoint`

**`tests/fixtures/sample_checkpoint.json`** — Minimal 2-frame fixture (flat square + one fold)
**`tests/fixtures/sample_attempt_tree.json`** — Matching attempt tree with MATCH verdict for frame 2

---

## 8. Prompt Strategy

### 8.1 FoldingAgent Prompts: Keep As-Is

The FoldingAgent system prompt (`SYSTEM_PROMPT`), critic prompt (`CRITIC_PROMPT`), and comparator prompt are not modified. They are reproduced verbatim in FoldingAgent's `prompts.py`. The hybrid pipeline calls FoldingAgent as a black box and consumes its output directory.

### 8.2 New Prompts from the Anveshan Side

#### (a) EvidenceGrounder Prompt

**File**: `research/origami_hybrid/prompts/evidence_grounder_v1.txt`

**Purpose**: Given a FoldingAgent geometric state (JSON) and its rendered PNG diagram, extract a precise natural-language description suitable for `KnowledgeClaim.statement` and `EvidenceRef.cue_excerpt`.

```
You are an origami knowledge extraction assistant analyzing geometric reconstruction output.

You will receive:
1. A JSON object describing the current geometric state of a folded paper model (vertices, faces, edges with crease assignments M/V/F/B, layer stacking).
2. A rendered PNG diagram of that geometric state.
3. The critic's analysis text that verified this state against a real photo.
4. Whether this state was verified by critic MATCH (directly observed) or selected by comparator (best estimate).

Your task: produce a structured claim description grounded in OBSERVABLE geometric facts.

Rules:
- ONLY describe what is directly visible in the geometry JSON and the rendered diagram.
- Do NOT speculate about folding technique, hand position, or intent.
- Reference specific edge IDs and vertex IDs when describing crease assignments.
- Use origami vocabulary: mountain fold (convex ridge, front-face), valley fold (concave trough, front-face), boundary edge, flat crease.
- If the state was comparator-selected (not MATCH-verified), preface with "ESTIMATED: " — this marks it INFERRED.

Geometric state JSON:
{{fold_state_json}}

Critic analysis:
{{critic_analysis}}

Verified by: {{verification_method}}  (MATCH | COMPARATOR)

Rendered diagram: [attached image]

Respond with JSON:
{
  "statement": "<2-3 sentence KnowledgeClaim.statement describing this fold state>",
  "cue_excerpt": "<1-2 sentence EvidenceRef.cue_excerpt describing observable geometric indicators>",
  "key_crease_edges": [{"edge": [u, v], "assignment": "M|V|F|B"}, ...],
  "layer_count": <int>,
  "verification_state": "observed" | "inferred"
}
```

#### (b) RubricSynthesizer Prompt

**File**: `research/origami_hybrid/prompts/rubric_synth_v1.txt`

**Purpose**: Given the full fold state sequence (all checkpoints), generate exactly 5 observable rubric criteria grounded to specific geometric facts.

```
You are an origami rubric design expert. You will receive a sequence of geometric fold states representing a complete origami construction procedure.

Each state has:
- frame_index: step number (1-based)
- mountain_edges: edges with M assignment [[u,v], ...]
- valley_edges: edges with V assignment [[u,v], ...]
- layer_count: number of layer planes
- critic_analysis: prose description of the state
- operations_delta: list of fold operations applied since previous state (as {"function": ..., "params": ...})

Your task: design EXACTLY 5 rubric criteria. Each criterion must:
1. Be directly evaluable by a human observer or a geometric predicate
2. Reference specific frame indices, edge IDs, or measurable tolerances
3. Use the format of the Anveshan observable_indicator: a concrete, observable cue or physical indicator
4. Have a weight (1.0–4.0) and a required flag (true/false)
5. Map to one of these types: alignment, crease_polarity, layer_count, orientation, sequence_order

Fold state sequence:
{{fold_state_sequence_json}}

Respond with JSON:
{
  "criteria": [
    {
      "criterion_id": "CRIT-GEO-01",
      "name": "<short name>",
      "description": "<what learner must demonstrate>",
      "observable_indicator": "<concrete geometric or physical indicator>",
      "weight": <float>,
      "required": <bool>
    }
  ]
}
```

#### (c) PracticeTask Prompt

**File**: `research/origami_hybrid/prompts/practice_task_v1.txt`

**Purpose**: Given a KnowledgePackage and RubricDefinition, generate a PracticeTask with pedagogically clear instructions.

```
You are a practice task designer for origami skill development.

You will receive:
1. A KnowledgePackage containing ordered STEP claims describing a fold procedure.
2. A RubricDefinition containing observable criteria with weights.

Your task: generate ONE PracticeTask that:
- States the material clearly (paper size, type)
- Lists the fold steps in order, using the KnowledgeClaim.statement fields
- References each rubric criterion by name in the instructions
- Specifies constraints: material type, size, time limit if appropriate
- Targets all required criteria and at least one non-required criterion

Knowledge package:
{{knowledge_package_json}}

Rubric definition:
{{rubric_definition_json}}

Respond with JSON:
{
  "title": "<practice task title>",
  "instructions": "<full step-by-step instructions for the learner>",
  "constraints": [
    {"constraint_type": "material", "description": "...", "value": "..."}
  ],
  "target_criteria_ids": ["CRIT-GEO-01", ...]
}
```

---

## 9. Risks and Open Questions

> **Decisions recorded (2026-10-07):**
>
> | Question | Decision |
> |---|---|
> | Video source | **Placeholder** — pipeline accepts any video the user supplies via CLI |
> | FPS source | **PyAV probe** — stored in `video_meta.json` at extract step; no hard-coding |
> | FoldingAgentSimulator availability | **Clone from source** — both repos are MIT; install with `pip install -e .` from local clone; eliminates live Git dependency at runtime |
> | Consent chain | **`consent_scope="research_prototype"`** — pipeline warns if attribution metadata is missing |
> | Track B compatibility | **Deferred** — focus entirely on hybrid pipeline; downstream Track B integration decided separately if hybrid succeeds |
> | Canonical vs synthesized criteria | **Synthesized criteria** — `CRIT-HYB-1` through `CRIT-HYB-5` from geometric sequence |
> | `run_metadata.json` and `expert_review_sheet.md` | **Required outputs** — following Track A `run_pipeline.py` convention |

### Model Availability

FoldingAgent uses `gemini` as its default backend if the model string does not start with `"claude"` or `"gpt"`. The system prompt, tool schema, and image handling are all tested against Anthropic Claude format. The `GeminiBackend` translates `AGENT_TOOLS` to Gemini `FunctionDeclaration` format via `_anthropic_to_gemini_schema()`, but this translation may not preserve all schema semantics. Separately, Anveshan's `GeminiProviderAdapter` uses `google-genai` SDK; FoldingAgent uses the same SDK (`google-genai>=0.3`). **Risk**: version pinning conflicts if both are installed in the same environment. Model IDs like `gemini-2.0-flash` (Anveshan) vs. whatever FoldingAgent defaults to may require explicit coordination.

### Dataset Licensing

PurelandFold dataset: **CC-BY-4.0** — commercial and derivative use allowed with attribution. Compatible with the hybrid pipeline.

Any user-supplied video must be attributed by the user. The pipeline emits a warning if `ConsentMetadata.notes` is empty. EvoStruggle dataset: **CC BY-NC 4.0** — non-commercial only; do not use without license compliance.

### FoldingAgentSimulator: MIT, clone from source

**Decision:** Both `FoldingAgent` and `FoldingAgentSimulator` are MIT-licensed public repos. Install `foldingagent-simulator` from a local clone (`pip install -e .`). This eliminates any live Git dependency at runtime and allows local inspection. FoldingAgent source is not modified — it remains a black box; only its `origami` import resolves to the locally installed simulator.

### FPS Source: PyAV

**Decision:** FoldingAgent does not store video FPS. The `KeyframeExtractor` uses PyAV to probe FPS at frame extraction time and writes it to `video_meta.json`. The `FoldingAgentAdapter` reads `fps` from `video_meta.json` to compute `timestamp_sec = keyframe_global_index / fps`. No hard-coding, no CLI parameter.

### Geometric Fidelity vs. Epistemic Humility

FoldingAgent may produce geometrically plausible but incorrect states — particularly for comparator-selected frames where no MATCH verdict was achieved. The hybrid pipeline MUST mark these as `is_observed=False`, `verification_state=VerificationState.INFERRED`, `confidence<=0.5`. Failing to do so violates `GroundingService.enforce_epistemological_state()`. A MATCH verdict verifies 2D projection correspondence, not 3D fold correctness (layer ordering can be ambiguous in 2D projection).

### Latency

The FoldingAgent ReAct loop runs up to `MAX_ITERATIONS=300` turns. For a 17-keyframe sequence this could take 30–90 minutes. The hybrid pipeline is an offline batch job. FoldingAgent supports resume via `--resume`.

### Video Format

FoldingAgent's `_load_keyframe_sequence()` reads pre-extracted JPEG frames — it does NOT decode video. The `KeyframeExtractor` (PyAV) handles any format PyAV can decode (WebM, MP4, OGV, AVI, etc.) and produces frames in `NNNNNN.jpg` naming convention.

### Layer State Explosion

For complex models (100+ fold operations), `layers` becomes deeply nested. `RubricSynthesizer` should use `layer_count` (total planes) as a simpler proxy for later keyframes rather than full topology.

### No Test Harness Yet for the Adapter

`FoldingAgentAdapter` is designed but not yet implemented. Test fixtures must be created from a minimal 2-frame FoldingAgent run. Until fixtures exist, the adapter cannot be validated.

### `attempt_tree.json` Node vs. Checkpoint Alignment

The `_checkpoint_node` map in `attempt_tree.json` may reference a comparator-selected node. The adapter must check `node.critic_verdict` rather than assuming all checkpoint nodes have `"MATCH"` verdicts.

---

## 10. Next Steps for Implementation

Recommended build order:

1. **Create test fixtures** — Run FoldingAgent on a minimal 2-frame sequence (flat square → one fold). Save `checkpoints.json`, `attempt_tree.json`, `history_log.json`, `frames.json`, `metadata.json`. Add `video_meta.json` with probed fps. These become the adapter unit test fixtures.

2. **Implement `KeyframeExtractor`** — PyAV decode + FPS probe → `video_meta.json` + frames. This unblocks all downstream steps.

3. **Implement `FoldingAgentAdapter.load_checkpoints()`** — Parse real output files using field mappings in §6. Run `test_load_checkpoints_from_fixture()`.

4. **Implement `FoldingAgentAdapter.to_evidence_refs()` and `to_knowledge_claims()`** — Pure data transformation, no LLM calls. Field mappings are deterministic from fixture data.

5. **Write sidecar writers** — `fold_state_log.json` and `crease_evidence.json` per §5.5.

6. **Implement `EvidenceGrounder.enrich_claims()` v1** — Skip LLM, use `critic_analysis` directly as `cue_excerpt`, assign `verification_state` from `selected_by_comparator`. Produces valid Anveshan contracts without any new LLM calls.

7. **Implement `RubricSynthesizer.synthesize()`** — **Synthesized criteria only** (`CRIT-HYB-1` through `CRIT-HYB-5`). First version: derive from edge M/V assignments and layer counts in the geometric sequence. Second version: use the RubricSynthesizer prompt (§8) for fully dynamic criteria.

8. **Emit `run_metadata.json` and `expert_review_sheet.md`** — Following Track A `run_pipeline.py` convention: `RunMetadataDTO` serialized to `run_metadata.json`; `ExpertReviewService.export_markdown()` output to `expert_review_sheet.md`. Both required before the pipeline output is considered complete.

9. **Implement `FoldingAgentAdapter.to_practice_tasks()` and `to_knowledge_package()`** — Wire together all outputs. Validate against Pydantic schemas.

10. **Wire `run_hybrid_pipeline()` in `pipeline.py`** — Connect all steps end-to-end. Verify `GroundingService.validate_package_grounding()` passes.

11. **Add LLM enrichment to `EvidenceGrounder`** — Replace direct `critic_analysis` passthrough with the full EvidenceGrounder prompt (§8a) for richer claim statements.

12. **Add `RubricSynthesizer` LLM call** — Replace geometry-only heuristics with the prompt-driven synthesis (§8b).

13. **Integration test with real FoldingAgent run** — Run the full hybrid pipeline on the user-supplied video, validate that `KnowledgePackage` passes both `validate_package_grounding()` and `validate_practice_task_against_knowledge_and_rubric()`.

**Note:** Track B integration is deferred until step 13 succeeds. If the hybrid produces valid, auditable Anveshan contracts, a separate decision will be made about downstream integration.

---

*End of RESEARCH.md — all field names verified against: `tracks/common/schemas/knowledge.py`, `tracks/common/schemas/evidence.py`, `tracks/common/schemas/rubric.py`, `tracks/common/schemas/practice.py`, `FOLDING_AGENT_DEEP_DIVE.md`, `ANVESHAN_DEEP_DIVE.md`, and `origami-deep-dive-2026-10-07.md`.*
