# Anveshan — Capability Experiment Protocol
## 2026-10-03

Purpose: determine whether the underlying AI phenomenon is strong enough to justify a product before selecting a vertical.

This document intentionally avoids product branding and UI design.

## 1. Experimental principle

Do not ask:

> "Can Gemini build our app?"

Ask:

> "Can a small amount of multimodal evidence produce a reliable state/action/outcome inference that a useful product can be built around?"

A successful experiment must produce evidence that can be independently checked.

## 2. Experiment ladder

### Level 0 — Deterministic baseline

Before using a model:
- manually annotate the ground truth;
- define timestamps;
- define state labels;
- define action labels;
- define expected outcome;
- define acceptable temporal tolerance.

Purpose:
- prevent model-generated labels from becoming the ground truth;
- establish how much of the task is solvable with deterministic rules.

### Level 1 — Text-only reasoning

Feed Gemini only:
- transcript;
- manually extracted action sequence;
- state metadata.

Question:
- can the model reason over the event sequence?

Purpose:
- isolate reasoning from video perception.

### Level 2 — Sparse video

Use short clips and static video processing.

Question:
- can the model identify the important states/actions/outcomes?

Purpose:
- establish whether multimodal input adds meaningful signal.

### Level 3 — Timestamped temporal reasoning

Ask targeted questions around candidate moments.

Question:
- can the model localize first divergence, recovery, or state change?

Purpose:
- test the most important temporal capability.

### Level 4 — Cross-attempt comparison

Give:
- successful reference;
- failed attempt.

Question:
- what differs, and when?

Purpose:
- test relational reasoning instead of single-video description.

### Level 5 — Closed-loop verification

Give:
- initial state;
- proposed action;
- post-action evidence.

Question:
- did the intervention actually change the state?

Purpose:
- test the complete product primitive.

## 3. X1 — First Divergence

### Hypothesis

A multimodal model can identify the earliest meaningful divergence between a successful and failed execution of the same procedure with useful temporal precision.

### Dataset

Minimum local fixture:
- 3 successful attempts;
- 3 failed attempts;
- same task;
- same or deliberately varied camera;
- failure introduced at a known step.

Preferred public benchmark candidates:
- Ego-Exo4D procedural tasks;
- ProSkill procedural clips;
- Assembly101 procedural sequences.

Ego-Exo4D contains synchronized ego/exo views and time-indexed expert commentary, atomic actions, procedural dependencies and proficiency annotations. ProSkill specifically targets action-level skill assessment in procedural tasks.

### Ground truth

For each failed attempt:
- first divergent action;
- first divergence timestamp;
- expected correct state;
- observed incorrect state;
- downstream consequence.

### Metrics

- temporal absolute error in seconds;
- action-label accuracy;
- state-label accuracy;
- evidence sufficiency;
- false causal attribution rate.

### Pass condition

A model response is only a pass if:
1. the timestamp is within the predeclared tolerance;
2. the action/state description matches ground truth;
3. cited evidence actually contains the claimed event;
4. the model does not invent a cause not visible in the evidence.

## 4. X2 — Recovery Intelligence

### Hypothesis

A model can reconstruct which action sequence restored a failed process to a desired state.

### Dataset

Minimum:
- 3 failure → recovery episodes;
- at least two corrective actions in each;
- observable return to normal.

### Ground truth

For each episode:
- failure state;
- corrective action 1;
- corrective action 2;
- recovery moment;
- recovered state.

### Metrics

- recovery-action precision;
- recovery timestamp error;
- before/after evidence validity;
- causal-claim calibration.

### Important constraint

The system must distinguish:
- "this happened before recovery";
from
- "this caused recovery."

Unless causal evidence exists, the UI should say "associated with recovery" or equivalent.

## 5. X3 — Demonstration Compiler

### Hypothesis

A demonstration can be transformed into a compact executable state/action/outcome representation that predicts whether a new attempt satisfies the procedure.

### Output schema

Procedure:
- task goal;
- states;
- actions;
- preconditions;
- transition conditions;
- observable success criteria;
- known failure modes;
- uncertainty.

### Evaluation

Use a held-out attempt.

Ask:
- which required transitions occurred?
- which were skipped?
- which were performed incorrectly?
- where is evidence?

### Baseline

Compare against:
- transcript-only representation;
- manually authored checklist;
- generic video summary.

The model must outperform the baseline on evidence-linked transition verification, not merely produce nicer prose.

## 6. X4 — Intervention Verifier

### Hypothesis

The model can verify whether a recommended physical action produced the intended observable state change.

### Workflow

1. observe state A;
2. identify issue;
3. recommend action;
4. record action;
5. observe state B;
6. determine whether intended transition A → B occurred.

### Metrics

- state-change precision;
- action-recognition accuracy;
- success/failure accuracy;
- evidence coverage;
- uncertainty calibration.

### Product significance

This is the most important closed-loop experiment.

A one-shot answer can be replaced by many existing systems.

A system that can observe, recommend, observe again and verify the outcome has a stronger claim to being an operational agent.

## 7. X5 — Skill Variant Mining

### Hypothesis

Given multiple successful demonstrations, the model can separate:
- invariant behavior;
- optional behavior;
- context-dependent behavior;
- irrelevant stylistic variation.

### Dataset

Minimum:
- 3 performers;
- same task;
- multiple successful executions.

Preferred:
- 5+ performers.

### Evaluation

Have a human expert independently label:
- must-do steps;
- acceptable alternatives;
- forbidden deviations.

Compare model extraction against expert labels.

### Why this matters

This could become a major differentiator from "copy the expert."

The system would learn what is essential rather than imitate one demonstration.

## 8. Public benchmark route

### Ego-Exo4D

Useful because it includes:
- skilled physical and procedural activities;
- synchronized ego/exo views;
- audio;
- expert commentary;
- atomic actions;
- procedural dependencies;
- proficiency ratings.

Potential use:
- validate action localization;
- validate expert commentary grounding;
- validate procedural representation.

Source:
https://docs.ego-exo4d-data.org/

### ProSkill

Useful because it is specifically about segment-level skill assessment in procedural activities and reports that existing methods remain challenging.

Potential use:
- validate skill comparison;
- compare model-derived observations against human-derived rankings;
- stress-test skill assessment claims.

Source:
https://openaccess.thecvf.com/content/WACV2026/html/Mazzamuto_ProSkill_Segment-Level_Skill_Assessment_in_Procedural_Videos_WACV_2026_paper.html

### Assembly101

Useful for:
- fine-grained procedural action segmentation;
- multi-view hand-object interactions;
- controlled procedural activities.

Important license constraint:
- dataset is CC BY-NC 4.0; check permitted use before any public/commercial deployment.

Source:
https://assembly-101.github.io/

## 9. Google capability mapping

### Gemini video understanding

Use for:
- temporal localization;
- visual + audio reasoning;
- timestamped questions;
- cross-attempt comparison.

Current docs state Gemini can process video, answer questions about video content, and refer to specific timestamps. Recent Flash models support an agentic mode that dynamically navigates a video rather than uniformly processing the entire timeline.

### Gemini Embedding 2

Use only where justified:
- cross-modal retrieval;
- matching video segments to textual criteria;
- clustering demonstrations;
- retrieving visually similar prior events.

Do not make embeddings the product thesis.

### Gemini Robotics ER 2

Use experimentally for:
- spatial reasoning;
- progress understanding;
- success detection;
- pointing/instrument interpretation;
- multi-step physical reasoning.

Do not make this preview dependency mandatory until availability and quotas are verified for the actual project account.

### Genie 3

Treat as research inspiration / optional experiment only.

Do not build the core product around Genie 3 availability.

## 10. Free-tier experiment budget

Default experiment budget:

- 6–12 short clips;
- 3–5 questions per clip;
- 2–3 model variants maximum;
- cache every response;
- never re-upload the same media unnecessarily;
- keep deterministic ground truth local;
- run expensive/preview tests only after a baseline succeeds.

The goal is not to maximize model calls.

The goal is to maximize information gained per model call.

## 11. Experiment ledger

For every model call record:

- experiment ID;
- model;
- timestamp;
- media identifier;
- media duration;
- prompt version;
- output schema version;
- raw response;
- extracted claims;
- timestamps claimed;
- ground-truth labels;
- pass/fail;
- failure category;
- token/usage metadata where available.

Never overwrite raw model responses.

## 12. Failure taxonomy

Use fixed categories:

1. PERCEPTION_ERROR
2. TEMPORAL_LOCALIZATION_ERROR
3. ACTION_CLASSIFICATION_ERROR
4. STATE_INFERENCE_ERROR
5. OUTCOME_INFERENCE_ERROR
6. CAUSAL_OVERCLAIM
7. MISSING_EVIDENCE
8. HALLUCINATED_EVIDENCE
9. UNCERTAINTY_FAILURE
10. FORMAT_FAILURE
11. QUOTA_FAILURE
12. LATENCY_FAILURE

This lets us identify whether a product problem is actually a model problem.

## 13. Decision gates

### Gate A — perception

Can the model reliably identify relevant events?

If no:
- kill the concept or redesign around a stronger observable signal.

### Gate B — temporal reasoning

Can it locate the important transition?

If no:
- a state-transition product is premature.

### Gate C — relational reasoning

Can it compare two executions or states?

If no:
- avoid products whose value depends on reference-vs-attempt comparison.

### Gate D — intervention verification

Can it detect whether the world changed after an action?

If no:
- do not claim closed-loop intelligence.

### Gate E — productization

Can a narrow workflow produce:
- obvious user value;
- objective evaluation;
- compelling demo;
- manageable data requirements;
- free-tier-first feasibility?

If no:
- keep the technical result as research and continue exploration.

## 14. Expected outcome

The experiments are allowed to kill the entire current Anveshan direction.

Possible outcomes:

A. State-transition reasoning works strongly.
→ explore First Divergence / Recovery / Intervention products.

B. Demonstration representation works, but verification does not.
→ explore knowledge/procedure products without closed-loop claims.

C. Skill comparison works, but causal reasoning does not.
→ explore evaluation/coaching with strict evidence grounding.

D. Video reasoning is weak, but document/event reasoning is strong.
→ pivot away from physical video.

E. Everything is mediocre.
→ discard the current thesis family and restart exploration.

That last outcome is acceptable and preferable to building a weak product around an attractive narrative.
