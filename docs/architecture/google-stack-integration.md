# Google Ecosystem & Gemini Integration Guide — Anveshan

**Checkpoint:** 2026-10-04  
**Status:** PROPOSED architecture integration playbook  
**Context:** Hackathon (Google Cloud AI Builder Cup 2026) and platform engineering standard.

---

## 1. Purpose

This document provides a durable, reusable specification for how Anveshan integrates with the **Google Cloud and Gemini ecosystem**. It guides coding agents and human engineers on model selection, SDK usage patterns, media ingestion, temporal grounding, structured output schemas, and cloud deployment.

---

## 2. Model Selection & Workload Mapping

Anveshan separates logical responsibilities across specialized Gemini models to optimize reasoning quality, latency, token consumption, and auditability:

| Workload | Recommended Model | Capability Justification | Configuration Key Points |
|---|---|---|---|
| **Demonstration Understanding & Step Extraction** | `gemini-3.8-flash` / `gemini-3.7-flash` | **Agentic Video Understanding** dynamically explores the timeline, selectively inspects transcripts, and adaptively adjusts FPS/resolution. Up to 88% more token-efficient than static 1 FPS sampling. | File API URI input; agentic mode enabled; structured JSON output. |
| **Temporal Evidence Grounding & Localization** | `gemini-3.8-flash` | Fast temporal reasoning; locates exact start/end seconds `[start_sec, end_sec]` for cues and actions. | Strict timestamp formatting prompt; uncertainty handling (`UNKNOWN` valid). |
| **Learner Attempt Evaluation & Cross-Attempt Diff** | `gemini-3.8-pro` | High-reasoning model capable of side-by-side comparative analysis of expert demonstration vs. learner baseline/retry without collapsing into generic feedback. | Rubric-constrained prompts; explicit observable criteria; no single scalar score. |
| **Speech & Narration Transcription** | `gemini-3.5-transcribe` | Verbatim multi-speaker transcription with word/phrase-level timestamp alignment. | Audio channel separation; speaker diarization enabled where needed. |
| **Cross-Modal Retrieval** | `gemini-embedding-2` | Unified multimodal vector space across text, images, video frames, and audio. | Segment-level embeddings; cosine similarity retrieval. |

---

## 3. Official SDK Patterns (`google-genai`)

The project standardizes on the official unified Python SDK: `google-genai`.

### 3.1 Installation & Initialization
```bash
pip install -U google-genai pydantic
```

```python
import os
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
```

### 3.2 Media Upload via Gemini File API
For video/audio demonstrations, large media must be uploaded via the File API rather than base64 encoding inline:

```python
# Upload authentic video demonstration
video_file = client.files.upload(file="path/to/demonstration.mp4")

# Wait for processing if large video
import time
while video_file.state.name == "PROCESSING":
    time.sleep(2)
    video_file = client.files.get(name=video_file.name)

if video_file.state.name == "FAILED":
    raise RuntimeError("Video processing failed in Gemini File API")
```

### 3.3 Strict Structured Output with Pydantic
All model responses matching the 7 core contract entities MUST use Gemini's structured output enforcement to guarantee schema conformity:

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class EvidenceLocator(BaseModel):
    start_sec: float = Field(description="Start time in seconds")
    end_sec: float = Field(description="End time in seconds")
    modality: str = Field(description="video, audio, or text")
    description: str = Field(description="Specific visual or audible cue observed")

class ExtractedStep(BaseModel):
    step_number: int
    action_label: str
    condition: Optional[str] = Field(None, description="Pre-condition or trigger")
    cues: List[str] = Field(description="Subtle or non-obvious sensory cues")
    evidence: EvidenceLocator

class KnowledgePackageOutput(BaseModel):
    skill_name: str
    steps: List[ExtractedStep]
    failure_modes: List[str]
    uncertainty_notes: Optional[str] = None

# Enforce schema at the inference boundary
response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=[video_file, "Extract the structured knowledge, steps, cues, and exact timestamps from this demonstration."],
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=KnowledgePackageOutput,
        temperature=0.2,
    ),
)

parsed_knowledge: KnowledgePackageOutput = response.parsed
```

---

## 4. Google Cloud Platform Deployment & Architecture

In accordance with official hackathon guidelines (Google Cloud AI Builder Cup 2026), the application deploys on Google Cloud infrastructure:

```
[ Client / Web UI (FastAPI/React) ]
             |
             v
   [ Google Cloud Run ]  <--- Managed serverless container
        |          |
        |          +---> [ Google Cloud Storage ] (Raw video / audio uploads)
        |          +---> [ Google Firestore ] (Domain-agnostic transmission & lineage graph)
        |
        v
[ Google Gemini API / Vertex AI ]
   - Gemini 3.8 Flash (Agentic Video Understanding & Grounding)
   - Gemini 3.8 Pro (Rubric Comparison & Evaluation)
   - Gemini 3.5 Transcribe (Audio Transcription)
```

### 4.1 Cloud Run (Compute)
- Stateless FastAPI / Python container.
- Configured with environment secret `GEMINI_API_KEY` via Google Secret Manager.
- Auto-scales based on incoming evaluation requests.

### 4.2 Cloud Storage (Blob Store)
- Bucket stores raw authentic demonstration videos, learner baseline videos, and retry attempts.
- Video references are passed directly or proxied to the Gemini File API.

### 4.3 Firestore (State & Lineage)
- Stores domain-agnostic entities: `KnowledgePackage`, `EvidenceRef`, `PracticeTask`, `LearnerAttempt`, `Evaluation`, `Feedback`, `TransmissionRecord`.
- Preserves lineage graph connecting expert, demonstration, learner, attempt, and verified gain.

---

## 5. Development Tooling & MCP Integration

This repository is equipped with specific agentic plugins and Model Context Protocol (MCP) servers:

1. **`gemini-api-docs` MCP Server** (`https://gemini-api-docs-mcp.dev`)
   - Tools: `gemini_search_docs`, `gemini_get_doc`
   - Purpose: Query live official documentation, SDK references, breaking changes, and migration guides before modifying API calls.
2. **`cloudrun` MCP Server**
   - Tools: `deploy_local_folder`, `deploy_container_image`, `list_services`, `get_service_log`
   - Purpose: Build and deploy the prototype directly to Google Cloud Run.
3. **`firebase-mcp-server`**
   - Purpose: Direct integration with Firestore and Firebase Auth / Storage.
4. **`generative_ui` Skill**
   - Purpose: Renders rich, interactive UI components inline (e.g. side-by-side video diffs, rubric evaluations, transmission gain graphs).

---

## 6. Guardrails & Deterministic Boundaries

To satisfy `AGENTS.md` and prevent model hallucinations from corrupting records:

1. **Deterministic Scoring:** The final `Transmission Gain` metric ($\text{Score}_{\text{retry}} - \text{Score}_{\text{baseline}}$) is computed deterministically from criterion-level checks, not generated as free-form model text.
2. **Provenance Distinction:** Ground truth must clearly delineate `observed` (physically seen/heard at timestamp) vs. `inferred` (logical deduction by model).
3. **Uncertainty Calibration:** If video quality, angle, or lighting prevents clear verification of a rubric criterion, the output must be marked `UNCERTAIN` or `INSUFFICIENT_EVIDENCE` rather than guessing.
4. **Offline Replay Mode:** Every model interaction must support a recorded/mock fixture replay mode so CI tests run reliably without incurring API costs or nondeterminism.
