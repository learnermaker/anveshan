# Product Direction Exploration — Execution Gap / Closed-Loop Operations
## 2026-10-03

## Strategic premise

The team has strong coding-agent capacity. Therefore implementation complexity should not be the primary constraint. Product selection should instead find a real, expensive, recurring operational failure where several already-proven AI capabilities compose into a closed loop with tangible stakeholder value, while the core demo remains viable on free/eligible Gemini usage.

The product does not need to invent a new model capability. It needs to use existing capabilities in a workflow that produces a measurable outcome that existing point solutions do not close.

## Strongest pain signal: execution gap

Current 2026 research repeatedly points to an operational distinction: organizations often know what should happen; the expensive failure is inconsistent execution, broken handoffs, missing context, poor diagnosis, repeat work, and inability to verify that an intervention worked.

This suggests a product abstraction stronger than generic knowledge transfer:

**PROBLEM STATE → EVIDENCE → DIAGNOSIS → ACTION → NEW STATE → VERIFY → LEARN**

The critical product object is the **verified intervention event**, not the document, chatbot answer, or lesson.

## Candidate product families

### A. Repair / Field Service Recovery Intelligence

Problem: technicians arrive with incomplete context, diagnose imperfectly, perform interventions, and may still require repeat visits. Senior technician knowledge is difficult to transfer.

Product: use work-order context, manuals/history, technician video/audio/photos and outcome evidence to reconstruct the service episode, identify the first diagnostic divergence or missing evidence, recommend a bounded diagnostic/intervention step, then compare before/after evidence to verify whether the intervention restored the desired state.

Stakeholders: technician, dispatcher/service manager, OEM, customer.

Outcomes: first-time-fix, repeat visits, mean time to resolution, diagnostic time, unnecessary truck rolls, service-report quality.

Competition warning: ServiceNow already provides AI work-order summarization, parts agents, image-based form filling and work-order recommendations. PTC Vuforia already captures expert procedures and supports AI-enhanced visual inspection. Anveshan must not become another technician copilot or work-instruction generator.

Differentiation hypothesis: verify the outcome of the physical intervention and preserve the complete evidence chain, including what changed and what remains unresolved.

Free-tier fit: high for a controlled demo using short repair videos, a small manual, work-order text and a handful of Gemini calls.

### B. Maintenance Intervention Verifier

Problem: maintenance teams know the planned intervention but struggle to consistently execute and verify it.

Product: compare planned procedure + asset state before work + observed execution + asset state after work. Identify deviations and verify whether the intended state transition occurred.

Stakeholders: maintenance supervisor, technician, reliability engineer, plant manager.

Outcomes: planned-work completion, rework, repeat failures, inspection time, maintenance quality.

Competition warning: visual inspection and work-instruction platforms exist. Focus on state-transition verification, not checklist completion.

Free-tier fit: high for one bounded procedure and short clips.

### C. First-Divergence Process Investigator

Problem: after a failed process, teams spend time reconstructing what happened. Logs often tell what was recorded, not what physically changed first.

Product: compare a successful/reference run with a failed run and identify the earliest material divergence, downstream consequence, and evidence.

Stakeholders: quality engineer, operations manager, process engineer.

Outcomes: investigation time, time-to-root-cause hypothesis, recurrence prevention.

Competition warning: process mining and manufacturing analytics exist. The wedge must be multimodal physical evidence and temporal comparison, not another dashboard.

Free-tier fit: very high for a short controlled process and two videos.

### D. Recovery Intelligence

Problem: organizations record failures but often do not turn successful recovery episodes into reusable operational intelligence.

Product: given a failure episode, identify the sequence of observed state changes and corrective actions associated with recovery; retrieve analogous recovery cases for future incidents.

Stakeholders: operations manager, technician, support engineer, trainer.

Outcomes: recovery time, repeat failure, escalation rate, onboarding speed.

Guardrail: say 'associated with recovery' unless causal evidence is available.

Free-tier fit: very high.

### E. Retail Fresh Recovery / Execution Verifier

Problem: store-level execution creates avoidable shrink and availability problems, particularly where decisions depend on incomplete information.

Product: observe a store condition, identify the actionable exception, record an intervention, and verify that the shelf/stock state changed as intended.

Stakeholders: store manager, associate, regional operations, retailer.

Outcomes: waste, availability, execution compliance.

Competition warning: shelf intelligence is crowded. Generic object detection is not enough.

Free-tier fit: high.

## What should NOT be built

- expert video → SOP
- generic AI tutor
- generic technician copilot
- generic RAG over manuals
- generic skill scoring
- generic visual inspection
- generic shelf detection
- generic work-order summarizer
- generic knowledge graph
- generic AI apprentice

These are already productized or heavily researched.

## Product selection rule

Select a problem where:

1. The failure is expensive enough that a manager cares.
2. The failure can be demonstrated with phone/video/photo/text evidence.
3. AI can observe evidence conventional workflow software misses.
4. The system can identify or recommend one bounded action.
5. The system can observe the resulting state.
6. Success can be measured without a large user study.
7. The core demo works with short media and few model calls.
8. Existing competitors solve adjacent pieces but do not make the same verified intervention loop the primary object.
9. The product remains useful without frontier-only models.
10. The workflow can expand later from one procedure to many.

## Preferred technical composition

- Gemini multimodal video understanding for temporal/visual evidence.
- Gemini transcription for speech/work notes where useful.
- Structured outputs for state/action/outcome records.
- Embeddings/retrieval only where they improve evidence lookup.
- Deterministic comparison and rubric logic for measurable verification.
- ADK only for multi-step orchestration where it improves the workflow.
- Cloud Run for deployment.

## Free-tier-first design

The core product should not require continuous multimodal inference.

Prefer 30–180 second clips, preprocessed source files, small manual/context payloads, one or two multimodal calls per major step, cached transcripts/observations, deterministic comparison/scoring, and recorded-response replay.

Current Gemini documentation supports video timestamp reasoning and agentic video navigation on supported recent Flash models. Gemini 3.6 Flash is currently listed with free input/output pricing in the Developer API pricing table. Exact project quotas must still be checked in AI Studio before large runs.

## Recommended strategic direction

The broad product thesis worth building toward is:

> **Anveshan is a closed-loop operational intelligence system that reconstructs what happened, identifies what changed, guides a bounded intervention, and verifies whether reality actually changed as intended.**

Strong initial vertical hypotheses: field service/repair, industrial maintenance, and manufacturing process recovery/investigation.

The strongest product shape is not 'AI knows how to do the job.' It is:

> **AI can show what happened, what should happen next, and whether the intervention actually worked.**

## Sources consulted

- BCG, AI-First Field Service Operations, 2026.
- Salesforce, Field Service Growing Talent Crisis, 2026.
- Aquant, 2026 Field Service Benchmark.
- UpKeep, State of Maintenance 2026.
- ServiceNow Field Service Management / Now Assist 2026 documentation.
- PTC Vuforia Expert Capture / Step Check documentation.
- Google Gemini video understanding documentation.
- Google Gemini API pricing documentation.
- Google Cloud Cloud Run / ADK documentation.