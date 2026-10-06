# FoldingAgent Deep Dive — Technical Research Report

> **Purpose**: Complete reference for the hybrid FoldingAgent × Anveshan Track A integration.
> **Status**: Research only — no source files modified.
> **Date**: 2025

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Simulator State Model](#2-simulator-state-model)
3. [Action Space](#3-action-space)
4. [FOLD / Geometry Format](#4-fold--geometry-format)
5. [Critic Protocol](#5-critic-protocol)
6. [Memory & Checkpoint Format](#6-memory--checkpoint-format)
7. [Comparator](#7-comparator)
8. [Prompt Content (verbatim)](#8-prompt-content-verbatim)
9. [Backend Abstraction](#9-backend-abstraction)
10. [PurelandFold / keyframes.json Dataset](#10-purelandfold--keyframesjson-dataset)
11. [Dependencies (pyproject.toml)](#11-dependencies-pyprojecttoml)
12. [Anveshan Track A Architecture](#12-anveshan-track-a-architecture)
13. [Integration Q&A](#13-integration-qa)
14. [Hybrid Integration Blueprint](#14-hybrid-integration-blueprint)

---

## 1. Architecture Overview

FoldingAgent is a **ReAct-loop origami reconstruction agent**: given a sequence of real-world origami photos (keyframes), it drives an LLM to interactively operate a geometry simulator until the rendered 2-D mesh matches every photo.

```
keyframes.json
     │
     ▼
run_agent()  ─── _prepare_run()
     │              ├── _load_keyframe_sequence()  → frame paths + colors
     │              ├── _build_backend()            → LLMBackend (Anthropic/Gemini/OpenAI)
     │              ├── _build_reviewers()          → OrigamiCritic, OrigamiComparator, OrigamiOverviewCritic
     │              └── OrigamiController(frames, out_dir, paper_colors, critic, overview_critic)
     │
     ▼
ReAct loop (max MAX_ITERATIONS=300 turns)
     ├── backend.chat(messages, system_prompt)  → LLMResponse
     ├── For each ToolCallRequest in response.ordered_content:
     │       controller.dispatch(tool_name, **args) → ToolResult
     │       _TurnExecutor._record(call, result)    → bookkeeping
     │       backend.append_turn(messages, response, executed_results)
     └── Loop until stop_reason == "end_turn" and all frames checkpointed
           OR max iterations / backend error
```

### Module Roles

| Module | Role |
|---|---|
| `main.py` | Entry point, ReAct loop, `run_agent()` function |
| `controller.py` | `OrigamiController` — each tool becomes a method; dispatches all LLM tool calls |
| `simulator.py` | `OrigamiLibraryExecutionEngine` — wraps `origami.Origami` library; `GeometryState` pydantic model |
| `tools.py` | `AGENT_TOOLS` — the canonical tool schema in Anthropic tool-use format |
| `rendering.py` | `render_geometry_diagram()` — Origami → matplotlib → PNG |
| `critic.py` | `OrigamiCritic` — builds 2×2 grid, calls model, returns `CriticResponse` |
| `overview_critic.py` | `OrigamiOverviewCritic` — evaluates full checkpoint sequence at once |
| `comparator.py` | `OrigamiComparator` — picks best attempt when retry budget exhausted |
| `memory.py` | `HistoryLog`, `AttemptTree` — run-state persistence; `_save_checkpoints` / `_load_checkpoints` |
| `logger.py` | `AgentLogger` — JSONL event log + human-readable terminal trace |
| `prompt_assembler.py` | Fills `{placeholder}` markers in prompt templates |
| `prompts.py` | Raw string constants for every prompt sent to any model |
| `config.py` | Single file for all tunables |
| `backends/` | Provider adapters behind the `LLMBackend` ABC |

### Controller Dispatch

`OrigamiController.dispatch()` (not shown verbatim but called from `_TurnExecutor.execute()`) routes tool call names to methods:

```
view_frame          → controller.view_frame(n)
observe_movement    → controller.observe_movement(t)
get_current_state   → controller.get_current_state()
render_current      → controller.render_current()
add_vertex          → controller.add_vertex(edge, position)
fold                → controller.fold(edge, direction)
unfold              → controller.unfold(edge|target)
rotate              → controller.rotate(angle)
flip                → controller.flip(axis)
save_checkpoint     → controller.save_checkpoint(frame_n, notes)
restore_checkpoint  → controller.restore_checkpoint(frame_n)
get_checkpoint_state→ controller.get_checkpoint_state(frame_n)
generate_checkpoint_overview → controller.generate_checkpoint_overview()
ask_critic          → controller.ask_critic(frame_n, action_classes, fold_anchor)
```

Every method returns a `ToolResult(data: dict, images: list[Path])`. The `data` dict is JSON-serialized (minus local path keys) before being fed back to the model.

---

## 2. Simulator State Model

### `GeometryState` (pydantic BaseModel, `simulator.py`)

```python
class GeometryState(BaseModel):
    base_description: str = "square sheet"
    raw_representation: dict[str, Any] | None = None   # from Origami.export()
    operations: list[GeometryFunctionCall] = []         # history of applied ops
    paper_colors: PaperColors = PaperColors()           # front/back color strings
```

`raw_representation` is the live geometry — a dict produced by `Origami.export()`. Its fields (from the system prompt and state JSON returned to the LLM) are:

```json
{
  "vertices": {
    "<id>": [x, y]
  },
  "faces": {
    "<id>": [v1, v2, v3, ...]
  },
  "faces_orientations": {
    "<id>": 0
  },
  "edges": [
    [u, v, "kind"]
  ],
  "layers": [
    [
      ["face_id", ...]
    ]
  ]
}
```

### Field Semantics

| Field | Type | Description |
|---|---|---|
| `vertices` | `dict[str, list[float, float]]` | 2D coords. X rightward, Y upward, origin bottom-left. Ids start at `"1"`. Initial square: `"1"` `"2"` `"3"` `"4"`. |
| `faces` | `dict[str, list[str]]` | Counter-clockwise ordered list of vertex IDs per face. |
| `faces_orientations` | `dict[str, int]` | `0` = front side up, `1` = back side up |
| `edges` | `list[list[int|str]]` | Each element `[u, v, kind]`. `kind` ∈ `{"B"` boundary, `"F"` flat, `"M"` mountain, `"V"` valley`}` |
| `layers` | `list[list[list[str]]]` | Layer stack from bottom to top. Each layer contains one or more _planes_ (sets of face IDs joined by flat edges, representing a continuous sheet at the same altitude). |

### `PaperColors` (`rendering.py`)

```python
class PaperColors(BaseModel):
    front_color: str = "white"    # DEFAULT_FRONT_COLOR from config
    back_color: str = "lightblue" # DEFAULT_BACK_COLOR from config
```

### `GeometryFunctionCall` (`simulator.py`)

```python
class GeometryFunctionCall(BaseModel):
    name: str           # serialized as "function"
    parameters: dict    # serialized as "params"
    assign_to: str | None = None  # for symbol binding ($V1, mid_14, etc.)
```

---

## 3. Action Space

All geometric tools are validated and applied in `OrigamiLibraryExecutionEngine._validate()` and `._apply()`. They ultimately call methods on `origami.Origami`.

### `add_vertex`

```
Parameters:
  edge      : [int, int]   — pair of vertex IDs defining the edge to subdivide
  position  : float (0.0–1.0) — fractional position along edge

Returns:
  new_vertex_id : int — next unused vertex ID (initial square has 1–4, first added = 5)

Simulator mutation:
  Splits the named edge at the given fraction, inserting a new vertex.
  The edge becomes two edges sharing the new vertex.
```

### `fold`

```
Parameters:
  edge      : [int, int]   — vertex IDs of the crease line
  direction : int (+1 or -1)
              Non-vertical crease: +1 = upper side moves, -1 = lower side moves
              Vertical crease:     +1 = right side moves,  -1 = left side moves

Simulator mutation:
  Rotates all faces on the selected side 180° about the crease line.
  Edge kind changes from "F"/"B" to "M" or "V".
  layers[] is updated to reflect new stacking order.
```

### `unfold`

```
Parameters (one of):
  edge   : [int, int]  — specific crease to unfold
  target : "last"      — unfold the most recent fold operation

Simulator mutation:
  Reverses the fold geometry.
  Edge kind changes to crease marker (dashed in diagrams).
  layers[] reverts.
```

### `rotate`

```
Parameters:
  angle : float — degrees, positive = clockwise

Simulator mutation:
  Rotates the entire mesh in 2D. All vertex coordinates updated.
  No topological change.
```

### `flip`

```
Parameters:
  axis : str — one of "x", "y", "y=x", "y=-x"
    "x"    → left/right swap (x → -x)
    "y"    → top/bottom swap (y → -y)
    "y=x"  → reflect across main diagonal
    "y=-x" → reflect across anti-diagonal

Simulator mutation:
  Reflects all vertex coordinates across the named axis.
  faces_orientations flip (0 ↔ 1) because the paper is turned over.
```

### Validation Rules (from `_validate()`)

| Tool | Required params | Additional rule |
|---|---|---|
| `fold` | `edge` | requires `direction` OR `side` |
| `add_vertex` | `edge`, `position` | — |
| `unfold` | — | requires `edge` OR `target` |
| `rotate` | — | `angle` OR `degrees` |
| `flip` | `axis` | axis ∈ `{"x","y","y=x","y=-x"}` |

---

## 4. FOLD / Geometry Format

FoldingAgent does not use the FOLD file format. It uses a **custom JSON geometry format** produced by `Origami.export()` (from the external `foldingagent-simulator` library). The format is described above in Section 2.

Key distinctions from the FOLD spec:
- No `vertices_coords` / `faces_vertices` naming — uses `vertices`, `faces`
- No fold angle floats per edge — fold state is binary (folded/unfolded) encoded in `layers`
- No 3D coordinates — all vertices are 2D `[x, y]`
- Edge assignments use single-letter codes: `B` (boundary), `F` (flat), `M` (mountain), `V` (valley), consistent with FOLD spec but applied to a flat projection
- Layer stacking order expressed as nested lists in `layers`, not as face z-order arrays

### Example skeleton (fresh flat square)

```json
{
  "vertices": {
    "1": [0.0, 0.0],
    "2": [1.0, 0.0],
    "3": [1.0, 1.0],
    "4": [0.0, 1.0]
  },
  "faces": {
    "1": ["1", "2", "3", "4"]
  },
  "faces_orientations": {
    "1": 0
  },
  "edges": [
    [1, 2, "B"],
    [2, 3, "B"],
    [3, 4, "B"],
    [4, 1, "B"]
  ],
  "layers": [
    [["1"]]
  ]
}
```

After a fold along edge `[1,3]` with direction `+1`, the face splits into two faces, one is rotated, edge `[1,3]` becomes `"M"` (mountain) or `"V"` (valley), and `layers` reflects the new stacking.

---

## 5. Critic Protocol

### Grid Assembly (`critic.py` → `create_critic_grid()`)

The critic receives **four images** arranged in a 2×2 labeled composite PNG:

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

- **A** = real-world photo of frame `(n-1)` — the source state
- **B** = real-world photo of frame `n` — the target state (goal)
- **C** = rendered diagram of the checkpointed source geometry (matches A)
- **D** = rendered diagram of the current simulator state (should match B)

Grid is composed by `create_critic_grid()`:
- Each cell is resized to the same width (max 512px per cell to keep total ≤ 1024px)
- Black 5-px borders separate cells
- Labels A/B/C/D drawn in the top-left of each cell (24–48px DejaVuSans font)

### Critic Request Structure

Beyond the grid, the critic LLM also receives:
- `action_classes` list (e.g. `["fold"]`, `["rotate", "flip"]`)
- `source_state_json` (full geometry dict of C)
- `result_state_json` (full geometry dict of D)
- `fold_anchor` (optional) — `{moving_element, static_reference, relationship}`

### Verdict Logic

The critic model returns JSON:

```json
{
  "verdict": "MATCH" | "MISMATCH" | "EXTREME DIVERGANCE",
  "analysis": "<2-4 sentences comparing D to B>",
  "anchor_check": "<one sentence on anchor, or 'no anchor provided'>",
  "discrepancies": ["<list of specific geometric issues>"]
}
```

**Parsed to `CriticResponse`:**

```python
@dataclass
class CriticResponse:
    verdict: CriticVerdict           # Enum: MATCH | MISMATCH | EXTREME_DIVERGANCE
    analysis: str
    raw_verdict: str = ""
    anchor_check: str = "no anchor provided"
    discrepancies: list[str] = []
    raw_response: str = ""
```

### Sanity Check — Automatic Downgrade

`OrigamiCritic._apply_match_sanity_checks()` will **downgrade MATCH → MISMATCH** if both:
1. The analysis mentions a gap/separation/offset in photo B (`"small gap"`, `"visible gap"`, `"not touching"`, etc.)
2. The analysis claims D shows closed/touching edges (`"coincident"`, `"touching"`, `"perfectly aligned"`, etc.)

This guards against the model accepting an idealised diagram that ignores real-world gaps.

### Controller Response to Verdict

| Verdict | `transition_attempt` | `verdict_instructions` | Controller action |
|---|---|---|---|
| `MATCH` | reset to 0 | `VERDICT_MATCH` | → `save_checkpoint()` and advance |
| `MISMATCH` | incremented | `VERDICT_MISMATCH` or `VERDICT_MISMATCH_REPEATED` (≥3 failures) | → `restore_checkpoint(n-1)` and retry |
| `EXTREME DIVERGANCE` | incremented | `VERDICT_EXTREME_DIVERGANCE` | → `generate_checkpoint_overview()` + deep rollback |

### Gating Continuation

`ask_critic()` enforces preconditions:
1. `frame_n` must be within range `1..len(frames)`
2. `frame_n` must be `> self._min_restore_frame` (not already comparator-locked)
3. `source_frame_n = frame_n - 1` must already be in `self.checkpoints`
4. If `"fold"` in `action_classes` → `fold_anchor` is **mandatory** (returns error otherwise)

---

## 6. Memory & Checkpoint Format

### `checkpoints.json` (persistent, `memory.py`)

Written by `_save_checkpoints()`, read by `_load_checkpoints()`.

```json
{
  "<frame_n>": {
    "raw_representation": { ...geometry dict... },
    "paper_colors": {
      "front_color": "white",
      "back_color": "red"
    },
    "operations": [
      {
        "function": "fold",
        "params": {"edge": [1, 3], "direction": 1},
        "assign_to": null
      }
    ]
  }
}
```

- Keys are frame indices as strings (`"1"`, `"2"`, etc.)
- `raw_representation`: full geometry dict from `Origami.export()` (the canonical source of truth)
- `paper_colors`: `PaperColors.model_dump(mode="json")`
- `operations`: list of `GeometryFunctionCall.model_dump(mode="json")` — historical fold operations applied to reach this state

### Rollback Mechanics

1. `restore_checkpoint(frame_n)` → `controller.current_geometry = checkpoints[frame_n].model_copy(deep=True)`
2. `_restore_counts[frame_n]` incremented (tracked per-frame)
3. `_rollback_events` appended with `(max_checkpoint, frame_n)` tuple
4. If `restore_count >= MAX_ATTEMPTS_PER_FRAME` AND ≥1 attempt exists → `_maybe_select_best()` triggers comparator

**Locks and floors:**
- `_locked_checkpoints: set[int]` — frames the model cannot roll back past (set by comparator)
- `_min_restore_frame: int` — floor below which `ask_critic`, `save_checkpoint`, and `restore_checkpoint` refuse to operate

### `history_log.json` (`memory.py` → `HistoryLog`)

```json
{
  "current_frame": 5,
  "checkpoints": [
    {
      "frame_index": 1,
      "status": "Resolved",
      "geometry": { ...raw_representation dict... },
      "notes": null
    }
  ],
  "history": [
    {"event": "attempt", "frame": 2, "attempt": 1, "operations": [...], "verdict": "MISMATCH", "reasoning": "..."},
    {"event": "rollback", "from_frame": 3, "to_frame": 2},
    {"event": "attempt", "frame": 2, "attempt": 2, "operations": [...], "verdict": "MATCH", "reasoning": "..."}
  ]
}
```

### `attempt_tree.json` (`memory.py` → `AttemptTree`)

Records the full branching tree of fold attempts as a graph of nodes:

```json
{
  "root": "n0",
  "current_parent": "n3",
  "nodes": {
    "n0": {
      "id": "n0",
      "frame_index": 1,
      "parent": null,
      "children": ["n1", "n2"],
      "actions": ["fold({\"edge\":[1,3],\"direction\":1})"],
      "reasoning": "...",
      "geometry": { ...raw_representation... },
      "render_path": "path/to/render.png",
      "critic_grid_path": "path/to/grid.png",
      "critic_query": null,
      "critic_verdict": "MATCH",
      "critic_analysis": "...",
      "critic_discrepancies": null
    }
  },
  "_checkpoint_node": {"1": "n0", "2": "n3"}
}
```

---

## 7. Comparator

### When it fires

When `_maybe_select_best()` determines:
- `len(attempts) >= MAX_ATTEMPTS_PER_FRAME` (default 5)  
- OR `restore_count >= MAX_ATTEMPTS_PER_FRAME` AND at least 1 attempt exists

### What it does (`comparator.py` → `_comparator_select_best()`)

1. Gathers all attempt node IDs for `frame_index` from `attempt_tree`
2. Filters to nodes that have a `render_path`
3. Assembles `CriticRequest` with:
   - Image A: the real target photo
   - Images B1, B2, … Bn: the rendered diagrams of each attempt
4. Sends to `OrigamiComparator.select_best()` — a single-turn LLM call
5. Model replies with **just** the label (e.g. `"B2"`)
6. Finds the chosen node's path to root via `attempt_tree.get_path_to_root()`
7. **Rebuilds `controller.checkpoints`** by walking the root-to-chosen path and reconstructing geometry states
8. Locks the source frame: `controller._locked_checkpoints.add(rolled_back_to)`
9. Sets floor: `controller._min_restore_frame = max(floor, next_frame)`
10. Saves rebuilt checkpoints to disk

### System Prompt

```
You are an origami diagram comparator. You will be shown a target photo (A) of an origami
state and several candidate diagrams (B1, B2, …). Your task is to select the candidate whose
shape, folds, and proportions best match the target photo A.

Reply with ONLY the label of the best candidate (e.g. B2). Do not include any other text.
```

---

## 8. Prompt Content (verbatim)

### Agent System Prompt (`prompts.py` → `SYSTEM_PROMPT` + `SYSTEM_PROMPT_FOOTER`)

> Note: `{front_color}` / `{back_color}` / `{num_frames}` are filled at runtime by `prompt_assembler.build_system_prompt()`.

See `prompts.py` lines 1–210 for the full verbatim text. Key sections:

- `═══ YOUR GOAL ═══` — origami reconstruction agent brief
- `═══ SIMULATOR STATE ═══` — full field documentation for the model
- `═══ AVAILABLE TOOLS ═══` — tool reference card for every tool
- `═══ CRITIC CONTEXT ═══` — explains the critic's role and authority
- `═══ PRECISION OVER CONVENIENCE ═══` — anti-hallucination heuristics (never use 0.5 midpoints lazily)
- `═══ THE 2-ATTEMPT RULE ═══` — forces rollback instead of parameter tweaking after 2 mismatches
- `═══ SESSION PARAMETERS ═══` — frame count, goal

### Critic System Prompt (`prompts.py` → `CRITIC_PROMPT`)

```
You are an expert origami visual critic.
...
You will receive four images in this order:
  1. A — Real photo of SOURCE state
  2. B — Real photo of TARGET state ← the goal
  3. C — Rendered diagram of source geometry
  4. D — Rendered diagram of current result

...
OUTPUT FORMAT (JSON only, no other text):
{
  "verdict": "MATCH" | "MISMATCH" | "EXTREME DIVERGANCE",
  "analysis": "<2-4 sentences comparing D to B>",
  "anchor_check": "<one sentence on anchor satisfaction, or 'no anchor provided'>",
  "discrepancies": [<list of specific geometric issues, empty for MATCH>]
}
```

Full text in `prompts.py` lines ~215–290.

### Overview Critic System Prompt (`prompts.py` → `OVERVIEW_CRITIC_PROMPT`)

Receives a multi-column PNG (frame labels / real photos / diagrams). Returns:

```json
{
  "last_correct_frame": <int or null>,
  "first_suspicious_frame": <int or null>,
  "analysis": "<2-4 sentences>",
  "per_frame_notes": ["<one note per column>"]
}
```

### Task / Opening Message

**Fresh run (`TASK_MESSAGE`):**
```
You are solving an origami folding sequence with {num_frames} frames.
Frame 1 is the initial flat square (already loaded in the simulator).
Work through each transition (1→2, 2→3, …, {penultimate_frame}→{num_frames}) to reconstruct the full sequence.

Start by calling save_checkpoint(1) to record the initial state, then view frames 1 and 2 to begin.
```

**Resumed run (`RESUME_TASK_MESSAGE`):**
```
You are resuming an origami folding sequence with {num_frames} frames.
Frames {solved} have already been solved and checkpointed. The simulator is currently at the state of frame {last_solved}.
...
```

---

## 9. Backend Abstraction

### `LLMBackend` ABC (`backends/base.py`)

```python
class LLMBackend(ABC):
    log_dir: Path | None = None
    log_label: str | None = None

    @abstractmethod
    def chat(self, messages: list, system_prompt: str) -> LLMResponse: ...
    
    @abstractmethod
    def init_messages(self, task_description: str) -> list: ...

    @abstractmethod
    def append_turn(self, messages, response, results) -> list: ...

    @abstractmethod
    def append_user_text(self, messages, response, text) -> list: ...
```

### `LLMResponse` (normalised across all providers)

```python
@dataclass
class LLMResponse:
    raw: Any                         # original SDK response object
    text: str | None                 # concatenated text blocks
    tool_calls: list[ToolCallRequest]
    stop_reason: str                 # "end_turn" | "tool_use"
    ordered_content: list[TextContentBlock | ToolCallRequest]
    llm_call_id: str | None = None
    thinking: str | None = None      # reasoning/thinking tokens
```

### `ToolCallRequest`

```python
@dataclass
class ToolCallRequest:
    id: str
    name: str
    input: dict[str, Any]
```

### Provider Selection (`_provider_for_model()`)

```python
def _provider_for_model(model: str) -> str:
    normalized = model.strip().lower()
    if normalized.startswith("claude"):   return "anthropic"
    if normalized.startswith(("gpt","o1","o3","o4")): return "openai"
    return "gemini"  # default
```

### `AnthropicBackend` (`backends/anthropic_backend.py`)

- Uses `anthropic.Anthropic.messages.create()` with `tools=AGENT_TOOLS` (verbatim Anthropic format)
- Images attached in `append_turn()` as `base64` blocks in `tool_result` content
- `stop_reason` passed through from `response.stop_reason`

### `GeminiBackend` (`backends/gemini_backend.py`)

- Converts `AGENT_TOOLS` JSON Schema to Gemini `FunctionDeclaration` objects via `_anthropic_to_gemini_schema()`
- Uses `ThinkingConfig(thinking_budget=THINKING_BUDGET)` (default 8192 tokens)
- Images returned in function responses as `Part.from_bytes()` inline data
- `stop_reason` inferred from `finish_reason` — set to `"tool_use"` if any function calls present

### `OpenAIBackend` (`backends/openai_backend.py`)

- Similar structure; uses `chat.completions.create()` with tool schema translated from Anthropic format

### Tool Schema Translation

AGENT_TOOLS is the canonical definition in Anthropic format. GeminiBackend translates:
- JSON Schema type names: `"object"` → `"OBJECT"`, `"array"` → `"ARRAY"`, etc.
- `enum` arrays → Gemini-compatible string enums
- Wraps all declarations in `gtypes.Tool(function_declarations=[...])`

---

## 10. PurelandFold / keyframes.json Dataset

### `keyframes.json` Schema

```json
{
  "name":       "heart",         // sequence identifier (used in run dir naming)
  "frames":     "frames",        // subdirectory name containing the keyframe images
  "front_color": "white",        // CSS color for paper front side
  "back_color":  "red",          // CSS color for paper back side
  "keyframes": [4, 10, 38, 50, 89, 99, 122, 147, 192, 242, 287, 307, 345, 392, 470, 490, 509]
              // global frame indices (1-based) to use as selected keyframes
}
```

### Directory Layout

```
data/heart/
├── keyframes.json
├── frames/           ← selected keyframe images (named by global index)
│   ├── 000004.jpg
│   ├── 000010.jpg
│   └── ...
└── all_frames/       ← full video frames for observe_movement() filmstrips
    ├── 000001.jpg
    ├── 000002.jpg
    └── ...
```

### Frame Naming Convention

Frame files are named by their **global frame index**: `NNNNNN.jpg` (zero-padded 6 digits), e.g. `000004.jpg`. This is matched by the regex:

```python
FRAME_NAME_RE = re.compile(r"^(?P<index>\d+)\.(?:png|jpe?g)$", re.IGNORECASE)
```

### Sequence Naming

The `"name"` field is slugified (non-alphanumeric → `-`) and used in the run output directory name: `run_<timestamp>_<model>_<sequence>`.

### `_load_keyframe_sequence()` Resolution

Reads `keyframes.json`, resolves `frames` to absolute paths by joining with the manifest's parent directory. Converts each global index `n` in `keyframes` to `frames_dir / f"{n:06d}.jpg"` (or `.png`). The first frame (`keyframes[0]`) corresponds to frame 1 in the agent's 1-based numbering.

---

## 11. Dependencies (pyproject.toml)

```toml
[project]
name = "foldingagent"
version = "0.1.0"
requires-python = ">=3.11"
license = "MIT"

dependencies = [
    "anthropic>=0.40",           # Anthropic Claude SDK
    "google-genai>=0.3",         # Google Gemini SDK
    "openai>=1.40",              # OpenAI GPT SDK
    "matplotlib>=3.7",           # For rendering origami diagrams
    "pillow>=10.0",              # For image manipulation (grids, filmstrips)
    "pydantic>=2.0",             # For all data models
    "foldingagent-simulator",    # External origami physics engine (from GitHub)
]

[tool.uv.sources]
foldingagent-simulator = { git = "https://github.com/maya-moriya/FoldingAgentSimulator.git" }
```

The core simulator (`origami.origami.Origami`) is a separate Git package — source not included in this repo. It exposes:
- `Origami(**paper_colors)` — creates fresh flat square
- `Origami(dict, **paper_colors)` — loads from geometry dict
- `origami.add_vertex(edge, position)` → new vertex id (int)
- `origami.fold(edge, direction)` → return value unused
- `origami.unfold(edge)` → return value unused
- `origami.rotate(angle)` → return value unused
- `origami.flip(axis)` → return value unused
- `origami.export()` → geometry dict
- `origami.plot(show, save_path, debug)` → saves PNG via matplotlib

---

## 12. Anveshan Track A Architecture

### Pipeline Overview

```
Case ID
  │
  ▼
TrackAPipeline.run(case_id)
  ├── load_manifest()          → CaseManifest (transmission_mode, domain, etc.)
  ├── REPLAY mode:
  │     load_replay_bundle()   → {knowledge_package, rubric, practice_task}
  │     KnowledgePackage.model_validate()
  │     RubricDefinition.model_validate()
  │     PracticeTask.model_validate()
  │     grounding.validate_package_grounding()
  └── LIVE mode:
        ModelGateway.extract_knowledge() → ExtractionResponseDTO
        normalize_dto_to_knowledge_package() → KnowledgePackage
        grounding.validate_package_grounding()
        TaskGenerator.generate_rubric()
        TaskGenerator.generate_practice_task()
  │
  ├── validate_practice_task_against_knowledge_and_rubric() → cross-contract check
  └── TrackAOutputBundle(package, rubric, practice_task, run_metadata, ...)
```

### Transmission Modes

| Mode | Input | Extraction approach |
|---|---|---|
| `forward` | Expert demonstration video | Temporal step/cue extraction with timestamps |
| `goal-conditioned` | Target artifact image | Reverse-engineering visible geometric properties |
| `corrective` | Learner attempt vs expert reference | Divergence identification against rubric criteria |

### Core Schemas (Pydantic, `tracks/common/schemas/`)

**`KnowledgePackage`** — the primary output of Track A:
```python
KnowledgePackage:
  package_id: str              # e.g. "kp.origami_heart.1"
  skill_id: str
  title: str
  summary: str
  claims: list[KnowledgeClaim] # min 1
  consent: ConsentMetadata
  expert_review: ExpertReview | None
```

**`KnowledgeClaim`**:
```python
KnowledgeClaim:
  claim_id: str                # "CLM-01", "CLM-02", ...
  claim_type: ClaimType        # step | cue | condition | exception | failure_mode
  statement: str
  is_observed: bool
  evidence_refs: list[EvidenceRef]  # min 1
```

**`EvidenceRef`** — temporal/spatial locator:
```python
EvidenceRef:
  evidence_id: str
  source_id: str
  modality: Modality           # video | audio | image | text | sensor
  start_sec: float | None
  end_sec: float | None
  cue_excerpt: str | None
  verification_state: VerificationState  # observed | inferred | unverified
  confidence: float (0.0–1.0)
```

**`ExtractionResponseDTO`** — intermediate LLM output (before normalization):
```python
ExtractionResponseDTO:
  case_id, skill_id, title, summary, source_media_id
  transmission_mode: "forward" | "goal-conditioned" | "corrective"
  steps: list[ExtractedStepDTO]
  cues: list[ExtractedCueDTO]
  conditions: list[ExtractedConditionDTO]
  exceptions: list[ExtractedExceptionDTO]
  failure_modes: list[ExtractedFailureModeDTO]
  target_properties: list[ExtractedTargetPropertyDTO]  # goal-conditioned mode
  divergences: list[ExtractedDivergenceDTO]             # corrective mode
  run_metadata: RunMetadataDTO
```

### Track A Prompts

| Prompt file | Mode | Key extractions |
|---|---|---|
| `expert_extraction_v1.txt` | `forward` | Steps (index, title, description, timestamps), sensory cues, preconditions, exceptions, failure modes |
| `goal_conditioned_extraction_v1.txt` | `goal-conditioned` | Observable target properties (property_id, description, measurement), candidate procedures |
| `corrective_extraction_v1.txt` | `corrective` | Divergences (criterion_id, observed vs expected behavior, timestamp) |
| `rubric_synthesis_v1.txt` | all modes | Rubric criterion generation |

---

## 13. Integration Q&A

### Q1: What is the EXACT Python dict/object FoldingAgent produces per keyframe after the agent finishes?

`run_agent()` returns `controller.checkpoints: dict[int, GeometryState]`.

Per keyframe `n`, the value is a `GeometryState` object:

```python
GeometryState(
    base_description="square sheet",        # str
    raw_representation={                    # dict[str, Any] — FULL geometry
        "vertices": {"1": [x,y], ...},
        "faces": {"1": [v1,v2,...], ...},
        "faces_orientations": {"1": 0|1, ...},
        "edges": [[u,v,"B|F|M|V"], ...],
        "layers": [[[face_ids,...], ...], ...]
    },
    operations=[                            # list[GeometryFunctionCall]
        GeometryFunctionCall(
            name="fold",               # serialized key: "function"
            parameters={"edge":[1,3],"direction":1},  # key: "params"
            assign_to=None
        ),
        ...
    ],
    paper_colors=PaperColors(
        front_color="white",
        back_color="red"
    )
)
```

The `description` computed property assembles a human-readable text from `raw_representation` + `operations`.

### Q2: Where does FoldingAgent write its output? What files?

All output goes under `config.OUT_DIR` (default `"out"`) in a timestamped run directory:

```
out/run_<timestamp>_<model>_<sequence>/
├── metadata.json          # Run summary: sequence, model, frames_solved, tokens, config
├── frames.json            # Resolved absolute paths to all keyframe images
├── checkpoints.json       # Per-frame geometry states (THE main output — see Section 6)
├── figs/                  # Rendered attempt diagrams for comparator
│   ├── attempt_n0_render.png
│   └── ...
├── logs/
│   ├── agent_log.jsonl    # Full JSONL event log (tool calls, text, usage, finish)
│   ├── history_log.json   # Structured checkpoint + attempt history
│   └── attempt_tree.json  # Branching tree of all attempts
└── llm_calls/             # Individual LLM request/response pairs
    ├── <timestamp>_<label>_<uuid>.json
    └── ...
```

Intermediate artifacts per iteration (rendered diagrams, critic grids, filmstrips) are written to the run root with sequential names like `render_current_0042.png`, `ask_critic_grid_0057.png`.

### Q3: What does the critic return — exact dict shape?

The `ask_critic` tool returns a `ToolResult.data` dict:

```python
{
    "success": True,
    "grid_path": str,              # path to the 2×2 PNG (stripped from model-facing output)
    "legend": {                    # labels for the 4 panels
        "A": "Real photo — frame N (source)",
        "B": "Real photo — frame M (target, match this)",
        "C": "Diagram — frame N geometry (matches A)",
        "D": "Diagram — your current simulator state (should match B)"
    },
    "action_classes": ["fold"],    # normalized lowercase list
    "source_state_json": {...},    # geometry dict of source (frame n-1)
    "result_state_json": {...},    # geometry dict of current state

    # When critic is available:
    "critic_verdict": "MATCH" | "MISMATCH" | "EXTREME DIVERGANCE",
    "critic_analysis": "str",      # 2-4 sentence prose
    "critic_anchor_check": "str",  # one sentence on anchor
    "critic_discrepancies": ["str", ...],  # empty for MATCH
    "transition_attempt": int,     # retry count (0 for MATCH, 1+ for failures)
    "verdict_instructions": "str", # what the agent should do next
}
```

### Q4: What is the checkpoint schema — exact fields?

From `checkpoints.json` (written by `_save_checkpoints()`):

```json
{
  "<frame_n_str>": {
    "raw_representation": {
      "vertices": {"<id>": [float, float]},
      "faces": {"<id>": ["<vertex_id>", ...]},
      "faces_orientations": {"<id>": 0 | 1},
      "edges": [[int, int, "B|F|M|V"]],
      "layers": [[[" face_ids"]]
    },
    "paper_colors": {
      "front_color": "str",
      "back_color": "str"
    },
    "operations": [
      {
        "function": "fold|unfold|rotate|flip|add_vertex",
        "params": {"...": "..."},
        "assign_to": null | "str"
      }
    ]
  }
}
```

### Q5: How does the controller know a keyframe transition is 'done'?

**A transition is done when `save_checkpoint(frame_n)` is called by the agent.**

The agent is expected to call `save_checkpoint()` only after:
1. `ask_critic()` returned `critic_verdict = "MATCH"` for `frame_n`
2. The `verdict_instructions` field in the result says `"MATCH: call save_checkpoint(frame_n) and advance"`

The ReAct loop in `run_agent()` does NOT automatically advance on critic MATCH — it relies entirely on the LLM following the instruction. The only forced advancement is via the **comparator**: when `restore_count >= MAX_ATTEMPTS_PER_FRAME`, `_maybe_select_best()` calls the comparator, picks the best attempt, and directly writes `controller.checkpoints[next_frame]` (bypassing the LLM's `save_checkpoint` call).

The overall run terminates when:
- `stop_reason == "end_turn"` AND `max(checkpoints) == len(frames)` — all frames solved
- OR `iteration >= MAX_ITERATIONS` 
- OR backend error

---

## 14. Hybrid Integration Blueprint

This section outlines how FoldingAgent's geometric reconstruction pipeline can be integrated with Anveshan Track A's knowledge extraction to produce a combined output.

### Core Thesis

**FoldingAgent is better at**: geometric reconstruction precision — exact vertex positions, fold topology, layer ordering. It produces a verifiable, machine-executable sequence of fold operations.

**Anveshan Track A is better at**: semantic knowledge extraction — step descriptions, sensory cues, failure modes, preconditions, temporal evidence grounding. It produces structured human-readable procedural knowledge with provenance.

### Integration Data Flow

```
Video / Keyframe sequence
        │
        ├──► FoldingAgent.run_agent()
        │         └──► checkpoints.json: dict[frame_n → GeometryState]
        │                                  • vertices, faces, edges, layers
        │                                  • operations list (fold/unfold/rotate/flip)
        │
        └──► Anveshan Track A (live mode)
                  └──► KnowledgePackage
                         • steps with timestamps
                         • sensory cues
                         • failure modes
                         • conditions
```

### Proposed Hybrid Output Schema

Each keyframe entry in the hybrid output would combine:

```python
@dataclass
class HybridKeyframeRecord:
    # --- FoldingAgent geometry (exact) ---
    frame_index: int
    geometry: dict             # raw_representation from GeometryState
    operations_delta: list[GeometryFunctionCall]  # ops since previous frame
    paper_colors: PaperColors

    # --- Anveshan Track A semantics ---
    claim: KnowledgeClaim | None      # closest matching step/cue claim
    evidence_refs: list[EvidenceRef]  # temporal locators to source video

    # --- Cross-grounding ---
    critic_verdict: str        # MATCH from the FoldingAgent critic
    critic_analysis: str       # prose description of the geometric state
    transition_type: list[str] # action_classes from ask_critic
    fold_anchor: dict | None   # moving_element, static_reference, relationship
```

### Bridging Points

1. **Timestamp alignment**: Anveshan `ExtractedStepDTO.start_sec / end_sec` can be matched to FoldingAgent frame indices via the `keyframes` array (each index corresponds to a video timestamp).

2. **Operation → claim mapping**: Each `operations_delta` between checkpoints maps to one Anveshan step. The geometric fold operation (`fold(edge=[2,5], direction=-1)`) and the semantic description (`"Fold the upper right corner to the center"`) can be co-indexed by frame number.

3. **Critic analysis → cue grounding**: The `critic_analysis` prose from `CriticResponse` describes the geometric state in natural language — this can be inserted as an additional `KnowledgeClaim` with `claim_type=ClaimType.CUE` and `verification_state=VerificationState.OBSERVED`.

4. **`fold_anchor` → failure mode detection**: The fold anchor (`moving_element`, `static_reference`, `relationship`) encodes the precision constraint at each fold. Mismatched anchors can generate `FailureMode` claims.

5. **FOLD format bridge**: FoldingAgent's geometry dict can be converted to canonical FOLD v1.1 format for external mesh tools by mapping:
   - `vertices` → `vertices_coords`
   - `faces` → `faces_vertices`  
   - `edges` (with kind) → `edges_assignment` (M/V/F/B/C)
   - `layers` → `faceOrders` or `faces_layer`

### Recommended Implementation Steps

1. Create `IndependentPipeline` in a new directory (e.g. `anveshan/tracks/track-a/pipelines/origami_hybrid/`)
2. Run FoldingAgent on the origami video's keyframe sequence
3. Run Track A `pipeline.py` in `live` mode on the same video
4. Merge outputs frame-by-frame using the timestamp → keyframe index mapping
5. Emit `HybridKeyframeRecord` list as a new JSON schema (`hybrid_keyframes.json`)
6. Use `normalize_dto_to_knowledge_package()` to wrap the hybrid in a `KnowledgePackage` with geometry-backed evidence refs

---

*End of FOLDING_AGENT_DEEP_DIVE.md — all content sourced directly from code, no source files were modified.*
