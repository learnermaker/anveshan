# Anveshan — Competitive Red-Team Addendum
## 2026-10-03

This document updates the exploration after a fresh search of current products and research.

## 1. Important correction: Demonstration Compiler is crowded

The phrase "demonstration compiler" initially sounded differentiated. It is not enough.

DeepHow is explicitly positioned as Physical AI for skilled operations and describes a workflow that turns expert walkthroughs into segmented step-by-step instructions and verifies execution against them. citeturn1search5

Academic work is also moving toward demonstration-driven procedural video learning. Demo-ICL studies whether multimodal models can acquire procedural knowledge from demonstrations and transfer that knowledge to novel tasks. citeturn1search10

Therefore:

**Do not pitch:**
> "Upload expert video and AI creates instructions."

**Do not pitch:**
> "Upload a trainee video and AI checks whether they followed the instructions."

Those are already established product/research patterns.

A viable differentiation would need to be a harder primitive:
- first divergence;
- recovery reconstruction;
- invariant discovery across successful variants;
- evidence-linked intervention verification;
- state-transition representation usable across attempts.

## 2. Current industrial instruction market

Industrial video training is already mature enough that conventional providers describe video SOPs as a distinct service, including capturing actual deviation points and showing the correct sequence. citeturn1search4

Industrial equipment companies also publish procedural video training for:
- fault recovery;
- HMI confirmation;
- abort/restart sequences;
- recipe changes;
- return-to-automatic procedures. citeturn1search1turn1search11

This reinforces a strategic rule:

> Do not spend the hackathon proving that video is better than text instructions.

That problem is already well understood.

## 3. Research saturation signal

Procedural video understanding has been an established research area for years. A survey identifies procedure creation, procedure tracking, contextual assistance, AR/VR guidance, feedback and next-step guidance as major directions. citeturn1search7

Recent work also targets streaming real-time procedural understanding and asks what the user is doing now and what they should do next. citeturn1search48

Therefore:

> "Real-time AI that watches a procedure and tells you the next step" is not enough.

## 4. New defensible frontier

The strongest remaining gap is not procedural knowledge extraction.

It is **procedural state transition verification**.

Potential formulation:

> Given a reference process, an observed execution, and an outcome, identify the earliest state transition that materially changed the trajectory, distinguish observation from causal hypothesis, and verify whether a subsequent intervention restored the desired state.

This is deliberately narrower and harder.

## 5. Why First Divergence is different

Existing instruction systems answer:

> "What should the worker do?"

First Divergence asks:

> "Where did this execution first stop behaving like the successful execution?"

That changes the unit of value from:
- instruction;
to
- diagnosis.

A possible workflow:

REFERENCE RUN
→ expected state sequence

ATTEMPT RUN
→ observed state sequence

ALIGN
→ compare corresponding transitions

FIND FIRST DIVERGENCE
→ timestamp + action + evidence

TRACE
→ downstream consequences

SUGGEST
→ candidate corrective action

VERIFY
→ post-intervention state

This is a materially different product loop.

## 6. Why Recovery is different

Most training systems are optimized around correct execution.

Recovery Intelligence asks:

> "When the process went wrong, what actually restored it?"

This creates a dataset of successful recoveries rather than only successful demonstrations.

Potential knowledge object:

```
Failure state
    ↓
Observed intervention
    ↓
Intermediate state
    ↓
Observed recovery
    ↓
Evidence
```

Over time this could become a "recovery memory" for an organization.

However, the system must never claim causality merely because an action happened before recovery.

## 7. Why intervention verification is different

Generic AI advice ends at:

> "Do X."

A closed-loop system asks:

> "Did doing X actually change the observed state?"

That means the system needs:
- pre-action state;
- action evidence;
- post-action state;
- expected transition;
- observed transition;
- uncertainty.

This is much closer to an agent operating against reality than a chatbot answering a question.

## 8. Why skill assessment alone is weak

Ego-Exo4D already has an explicit proficiency benchmark:
- novice;
- early expert;
- intermediate expert;
- late expert;
and fine-grained temporal identification of good actions / tips for improvement. citeturn0search7turn0search0

ProSkill is specifically an action-level skill assessment benchmark and reports that current methods remain challenging. citeturn0search2

Therefore:
- "AI scores your skill" is a valid technical experiment;
- it is not a sufficient product thesis.

Skill assessment becomes more interesting when attached to:
- why performance diverged;
- what intervention should change;
- whether the intervention worked.

## 9. Competitive moat hypothesis

A possible moat is not the model.

It is the **transition corpus**.

Each verified episode could become:

```
context
→ state
→ action
→ outcome
→ evidence
→ intervention
→ verified result
```

An organization accumulating hundreds of verified transitions would possess a structured operational memory that is harder to replace than a library of AI-generated SOPs.

But this is only a hypothesis. Do not use "data moat" as a claim until a useful accumulation mechanism is demonstrated.

## 10. Product candidates after red-team

### Candidate R1 — First Divergence

Core promise:
> Find where a real execution first diverged from a successful process.

Killer demo:
- show two synchronized timelines;
- AI highlights the first meaningful divergence;
- jump directly to both moments;
- explain the observable difference;
- show later consequence.

### Candidate R2 — Recovery Memory

Core promise:
> Turn successful recovery episodes into reusable operational intelligence.

Killer demo:
- show failure;
- show several actions;
- identify the recovery transition;
- extract the reusable recovery pattern;
- retrieve it for a new similar failure.

### Candidate R3 — Closed-Loop Intervention Verifier

Core promise:
> Observe whether an intervention actually restored the desired state.

Killer demo:
- before state;
- issue;
- recommended action;
- user action;
- after state;
- verified transition.

### Candidate R4 — Variant/Invariance Miner

Core promise:
> Compare multiple successful experts and identify what is essential versus stylistic.

Killer demo:
- 3–5 expert videos;
- aligned steps;
- invariant actions;
- acceptable alternatives;
- context-dependent variants.

### Candidate R5 — Evidence-Grounded Skill Diagnosis

Core promise:
> Explain exactly where a learner's execution diverged and which observable behavior should change.

This remains closer to the original Anveshan thesis, but with a stronger diagnostic core.

## 11. Current kill list

Unless experiments reveal a genuinely new technical property, do not build:

- AI-generated SOPs;
- generic AI apprentice;
- generic video coach;
- generic skill score;
- generic shelf monitor;
- generic PPE monitor;
- generic construction progress monitor;
- generic RAG over expert videos;
- generic procedural video search;
- generic "next step" assistant;
- generic expert digital twin.

## 12. New strategic question

The key question is no longer:

> "What knowledge should Anveshan preserve?"

It is:

> **"Can Anveshan explain how reality changed during a human process, and verify whether an intervention changed it back?"**

That question is sufficiently broad to support manufacturing, repair, field service, sustainability, education and other domains without prematurely selecting one.

## 13. Next red-team test

For each candidate R1–R5, ask:

1. Can a human create ground truth in under 15 minutes per case?
2. Can Gemini recover the ground truth from video?
3. Can the output be falsified?
4. Can a deterministic baseline solve it?
5. Is the result visually obvious?
6. Does the result require multimodal temporal reasoning?
7. Does it survive without Robotics ER?
8. Can it be tested with <= 10 short clips on free/eligible usage?
9. Is the closest competitor solving the same transition?
10. Can a 3-minute demo show the result without explanation-heavy narration?

Any candidate failing multiple tests is demoted.

## 14. Bottom line

The competitive evidence strengthens the case for **state-transition intelligence** while weakening the case for **instruction generation** and **generic skill assessment**.

The product should not be selected until the state-transition experiments produce a reproducible technical result.
