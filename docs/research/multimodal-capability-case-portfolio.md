# Multimodal Capability Case Portfolio

## Purpose

This document defines the current seven-case portfolio for Anveshan's multimodal and Generative UI validation.

These are **engineering/demo cases**, not seven separate product verticals. They are chosen because, together, they exercise materially different structures of human expertise while preserving the same domain-agnostic Anveshan transmission architecture.

The central idea is:

> **Different skills should produce different evidence structures and different interaction surfaces, while the same common transmission contracts remain stable underneath.**

The portfolio should therefore be treated as a **multimodal capability test matrix** and a source of bounded demo fixtures. It must not cause domain-specific assumptions to leak into the common contract seam.

---

## Design principle

Multimodal does **not** mean adding video, audio, text, and images to every case.

A modality should be present because it contributes evidence that materially affects understanding, teaching, comparison, or verification.

Examples:

- Kolam: spatial geometry matters; audio may be irrelevant.
- Tabla: audio and timing are central; visual gesture is supporting evidence.
- Micrometer: visual, temporal, acoustic, and numeric evidence may interact.
- Bicycle repair: visual state and diagnostic context matter more than decorative multimodality.

This is also the core GenUI principle:

> **The capability determines which evidence matters, and the evidence structure determines the appropriate workspace.**

---


---

# Transmission Modes

The seven cases are not required to use the same source type. The source may be a demonstration, a desired outcome, a learner attempt, or a combination of these.

| Mode | Direction | Example cases | Core question |
|---|---|---|---|
| **Forward** | Demonstration → capability | Bicycle, Micrometer, Tabla, Origami | How can the learner reproduce what the source demonstrates? |
| **Goal-conditioned** | Desired state → plausible capability path | **Kolam** | How can the learner reach the desired outcome? |
| **Corrective** | Learner attempt → divergence → capability | Knot, Origami, Bicycle, Micrometer | What must change for the next attempt to improve? |

**Important:** goal-conditioned reconstruction is a research hypothesis, not a validated capability. A final image can establish visible target properties but generally cannot establish the original artist's exact procedure, intent, or historical context.

The evidence states remain mandatory: SOURCE-DERIVED FACT, OBSERVED, INFERRED, UNVERIFIED, UNKNOWN.

# The 7 Multimodal Capability Tests

| # | Case | Primary multimodal signal | What Gemini should understand | Candidate generated workspace | Strategic role |
|---|---|---|---|---|---|
| 1 | **Kolam drawing** | Vision + spatial + temporal + text/context | Geometry, trajectory, symmetry, sequence | **Spatial Practice Canvas** | India/JAPAC relevance + GenUI showcase |
| 2 | **Bicycle puncture repair** | Vision + temporal + diagnostic + contextual | Observation -> diagnosis -> action -> outcome | **Diagnostic Workspace** | Practical impact + reasoning |
| 3 | **Micrometer zeroing / measurement** | Vision + audio + temporal + numeric | Visual state + sound cues + measurement + sequence | **Forensic Transmission Instrument** | Technical depth; preserves the current UI strength |
| 4 | **Handloom / paper weaving** | Vision + spatial + temporal + state | Over/under state, sequence, alignment, emerging pattern | **State Transition Workspace** | Domain generality + state reasoning |
| 5 | **Tabla basic stroke / rhythm** | **Audio + vision + temporal** | Gesture, sound, timing, and their alignment | **Rhythm Practice Instrument** | Proves true multimodal reasoning |
| 6 | **Origami / paper folding** | Vision + spatial + temporal | Fold state, orientation, order, divergence | **Spatial Sequence Workspace** | Simple, reliable control case |
| 7 | **Square knot / basic knot tying** | Vision + spatial + temporal | Crossings, orientation, sequence, final state | **First-Divergence Workspace** | Cleanest verification / retry demonstration |

---

# Case 1 — Kolam Drawing

## Capability archetype

**Spatial reconstruction / goal-conditioned transmission**

## Source pattern

Kolam is intentionally different from the video-first cases. A strong prototype path can begin with a **target Kolam image** rather than a demonstration video.

The target becomes the desired state:

~~~text
TARGET IMAGE → STRUCTURE → PLAUSIBLE CONSTRUCTION PATH → PRACTICE → TARGET VERIFICATION
~~~

This is not a claim that the original artist's exact procedure can be recovered from the final image.

## Why it is useful

Kolam provides India/JAPAC relevance while testing a genuinely different transmission direction: the system starts from an outcome and reasons toward a candidate path to achieve it.

Research on Kolam treats the form as structured geometry. Recent work covers image-based digital preservation/classification, one-stroke generation, Pulli Kolam structure, and computational pattern systems.

## What Gemini should reason about

From the target image, the system may analyze:

1. pulli/dot-grid structure;
2. symmetry;
3. repeated motifs;
4. line continuity and crossings;
5. geometric relationships;
6. candidate intermediate states;
7. a plausible construction sequence.

The output must distinguish visible observations from inferred construction strategy.

### Evidence boundary

Valid:

> **OBSERVED:** the target exhibits bilateral symmetry.

Potentially valid:

> **INFERRED:** establishing the central symmetry before completing repeated motifs is a plausible construction strategy.

Not valid without source evidence:

> **The original artist first drew the left loop and mirrored it.**

The last statement requires an actual demonstration or other authoritative source.

## Candidate UI

### Spatial Reconstruction Workspace

~~~text
TARGET IMAGE
     ↓
STRUCTURE MAP
     ↓
CANDIDATE CONSTRUCTION
     ↓
INTERACTIVE PRACTICE
     ↓
CURRENT STATE
     ↓
TARGET COMPARISON
     ↓
DIVERGENCE
     ↓
CORRECTION
     ↓
RETRY
~~~

Useful primitives:

- target image;
- pulli/grid representation;
- symmetry overlay;
- line/topology view;
- candidate construction stages;
- interactive drawing canvas;
- target/current overlay;
- divergence marker;
- corrective micro-practice;
- uncertainty panel;
- provenance/evidence drawer.

This should be composed through the same bounded GenUI component catalog as the other workspaces.

## Strategic role

Kolam is the strongest demonstration that **the interface changes because the reasoning problem changes**.

It should not become another copy of the existing Transmission Instrument.

## Source guidance

Prefer an Anveshan-owned target image for the public prototype. Public/research Kolam datasets can support exploration and benchmarking, but they should not be treated as authoritative cultural/procedural sources without attribution and verification.

See docs/research/source-strategy-and-transmission-modes-2026-10-04.md for source and licensing notes.

# Case 2 — Bicycle Puncture Repair

## Capability archetype

**Diagnosis / decision**

## Why it is useful

This case expands Anveshan from motor imitation into practical reasoning.

The system can observe:

```text
OBSERVATION
    ↓
DIAGNOSIS
    ↓
ACTION
    ↓
RESULT
```

That structure is directly aligned with the Anveshan knowledge model.

## Evidence that can matter

- video of the repair;
- visual state of tyre/tube/valve/tools;
- temporal action sequence;
- inspection findings;
- textual repair context;
- optional audio where it genuinely contributes.

## What Gemini should reason about

Examples of useful reasoning tasks:

- identify the relevant component state;
- distinguish observation from diagnosis;
- infer the likely repair path from observed evidence;
- identify a missed or incorrect diagnostic/action step;
- explain why the selected action was insufficient;
- compare learner and reference decisions.

## Candidate UI

### Diagnostic Workspace

Rather than a simple step list:

```text
OBSERVE
   ↓
WHAT DO WE KNOW?
   ↓
POSSIBLE DIAGNOSIS
   ↓
ACTION
   ↓
VERIFY RESULT
```

The interface can adapt to expose only the evidence needed for the active decision.

## Important boundary

The model must not turn an unverified visual inference into an authoritative mechanical fact.

Use evidence states such as:

- OBSERVED
- INFERRED
- UNVERIFIED
- UNKNOWN

---

# Case 3 — Micrometer Zeroing / Measurement

## Capability archetype

**Precision / forensic multimodal evidence**

## Why it is useful

This is the strongest technical expression of the current Transmission Instrument.

It can combine:

- video;
- temporal localization;
- visual state;
- audio cues;
- numeric measurement;
- rubric criteria;
- source/context;
- provenance.

This case should remain in the portfolio even as other generated workspaces are introduced.

## What Gemini should reason about

Potential responsibilities:

1. recover relevant state/action transitions;
2. identify meaningful evidence windows;
3. correlate visual and acoustic cues;
4. identify candidate divergence;
5. generate a targeted intervention;
6. compare retry against baseline.

## Evidence language

Do **not** imply that a camera directly measures a physical quantity it cannot establish.

Good pattern:

> **OBSERVED:** a repeated acoustic cue occurs in the identified time window.

> **INFERRED:** the cue is consistent with the expected engagement step.

> **UNKNOWN:** actual applied torque cannot be established from the recording alone.

This distinction is essential because Anveshan's differentiation depends on evidence and provenance.

## Current UI relationship

The existing **Transmission Instrument** should be treated as the canonical v0 forensic workspace, not discarded.

The longer-term product should demonstrate that this is **one generated workspace among several**, selected because this capability has a precision/temporal/evidence structure.

---

# Case 4 — Handloom / Paper Weaving

## Capability archetype

**State transition**

## Why it is useful

Weaving naturally expresses the Anveshan state/action/outcome model.

The important question is not only whether a step occurred, but how the material state changes:

```text
MATERIAL STATE
      ↓
    ACTION
      ↓
NEW STATE
      ↓
PATTERN / OUTCOME
```

Potential evidence includes:

- over/under relationships;
- thread or strip position;
- sequence;
- alignment;
- emerging pattern;
- learner/reference divergence.

## Candidate UI

### State Transition Workspace

Useful primitives:

- state snapshots;
- sequence markers;
- reference/learner comparison;
- over/under visualization;
- first divergence;
- current state;
- next required action.

## Strategic value

This case demonstrates that Anveshan can model **changing state**, not just classify a final image.

That is closer to transmission of expertise than generic visual assessment.

---

# Case 5 — Tabla Basic Stroke / Rhythm

## Capability archetype

**Audio-visual temporal synchronization**

## Why it is especially important

This is the deliberate addition that strengthens the portfolio's multimodal story.

Most of the original cases are primarily visual + temporal. Tabla provides a case where **audio is evidence, not decoration**.

Potential signals:

- hand gesture;
- stroke type;
- sound;
- rhythm/timing;
- repeated pattern;
- gesture/sound alignment.

Conceptually:

```text
HAND GESTURE ─────┐
                  ├──> MULTIMODAL ALIGNMENT
AUDIO ────────────┤
                  │
TIMING ───────────┘
```

## What Gemini should reason about

A useful benchmark is:

- recognize the relevant gesture;
- characterize the produced sound;
- compare timing with reference;
- locate temporal drift;
- connect the audible difference to a corrective action.

## Candidate UI

### Rhythm Practice Instrument

Potential primitives:

- synchronized expert/learner video;
- waveform or onset representation;
- beat/timing markers;
- gesture markers;
- first divergence;
- targeted retry exercise.

## Strategic value

This case helps establish that Anveshan is not merely:

> "video in, score out."

It demonstrates genuine cross-modal alignment.

---

# Case 6 — Origami / Paper Folding

## Capability archetype

**Sequential spatial transformation**

## Why it remains useful

Origami is intentionally simple.

We need a control case where the transmission loop can be tested without the diagnostic complexity of a repair task or the evidence complexity of a precision instrument.

Useful signals:

- fold geometry;
- edge/corner alignment;
- orientation;
- sequence;
- intermediate state;
- final state.

## What Gemini should reason about

The strongest product question is:

> **At what point did the learner's spatial state first diverge from the reference?**

The system should be able to distinguish:

- correct early state;
- first meaningful divergence;
- downstream consequences;
- targeted corrective practice.

## Candidate UI

### Spatial Sequence Workspace

Possible primitives:

- reference state sequence;
- learner state sequence;
- fold overlays;
- step navigator;
- divergence marker;
- micro-practice.

## Strategic value

Origami is also a useful **reliability/control benchmark**. A failure here should prevent us from making stronger multimodal claims elsewhere.

---

# Case 7 — Square Knot / Basic Knot Tying

## Capability archetype

**First divergence / verification**

## Why it is useful

This is the cleanest case for the core Anveshan loop:

```text
REFERENCE
   ↓
LEARNER ATTEMPT
   ↓
FIRST MEANINGFUL DIVERGENCE
   ↓
TARGETED INTERVENTION
   ↓
RETRY
   ↓
VERIFICATION
```

Useful signals:

- crossing relationships;
- rope orientation;
- hand movement;
- sequence;
- final knot structure.

## Candidate UI

### First-Divergence Workspace

The interface should make the causal chain obvious:

```text
reference state
      │
      ├── learner matches
      │
      ├── learner matches
      │
      └── FIRST DIVERGENCE
                ↓
          corrective action
                ↓
              retry
```

## Strategic value

The case is simple enough for a judge to understand almost immediately while still making the transmission thesis visible.

---

# Multimodal Reasoning Matrix

Internally, treat the seven cases as different multimodal reasoning archetypes rather than seven unrelated verticals.

| Archetype | Case |
|---|---|
| **Spatial transformation** | Kolam |
| **Diagnosis / decision** | Bicycle repair |
| **Precision / forensic evidence** | Micrometer |
| **State transition** | Handloom / paper weaving |
| **Audio-visual synchronization** | Tabla |
| **Sequential transformation** | Origami |
| **First divergence / verification** | Square knot |

The portfolio is stronger because each case stresses a different reasoning shape.

---

# Source Strategy

The seven cases should use a **source portfolio**, not one dataset.

| Case | Preferred source strategy | Public prototype posture |
|---|---|---|
| Kolam | research images + Anveshan-owned target | target-image / goal-conditioned |
| Bicycle repair | Ego-Exo4D + ProSkill research | selected approved subset or owned recording |
| Micrometer | Anveshan-controlled recording | primary owned case |
| Handloom / weaving | Anveshan-controlled recording | primary owned case |
| Tabla | IIT Bombay research source + owned recording | audio-temporal case |
| Origami | EvoStruggle + FoldingAgent research | research-backed spatial case |
| Square knot | EvoStruggle + procedural-skill research | verification/retry case |

Research source and shippable prototype asset are different categories. Do not redistribute restricted research media merely because it is useful for benchmarking.

# GenUI Relationship

The seven cases should also demonstrate the core Generative UI hypothesis:

> **The interface changes because the structure of the skill changes.**

Do not build seven copies of the same dashboard with different labels.

Preferred mapping:

| Case | Generated workspace |
|---|---|
| Kolam | **Spatial Practice Canvas** |
| Bicycle repair | **Diagnostic Workspace** |
| Micrometer | **Forensic Transmission Instrument** |
| Weaving | **State Transition Workspace** |
| Tabla | **Rhythm Practice Instrument** |
| Origami | **Spatial Sequence Workspace** |
| Knot | **First-Divergence Workspace** |

This should be implemented as bounded/adaptive composition over a trusted component catalog, not unconstrained model-generated frontend code.

---

# Do Not Force Every Modality Into Every Case

This is a hard design rule.

Bad approach:

```text
every case
  = video + audio + text + image + waveform + AI
```

Preferred approach:

```text
capability
   ↓
relevant evidence modalities
   ↓
appropriate reasoning strategy
   ↓
appropriate workspace
```

Examples:

- **Kolam:** spatial geometry is critical; audio may be irrelevant.
- **Tabla:** audio and timing are central; visual gesture supports interpretation.
- **Micrometer:** visual + temporal + numeric evidence may be central, with audio as an additional cue.
- **Bicycle repair:** visual state + diagnostic context are central; audio should only be used when genuinely informative.

This makes the multimodal claim more credible because the system is selecting modalities according to the task.

---

# Common Contract Boundary

These seven cases **must not change the eight-contract common seam merely because the UI or modality is different**.

The eight frozen common contracts are:

1. `EvidenceRef`
2. `KnowledgePackage`
3. `RubricDefinition`
4. `PracticeTask`
5. `LearnerAttempt`
6. `Evaluation`
7. `Feedback`
8. `TransmissionRecord`

Domain-specific differences belong above the seam:

- modality adapters;
- extraction prompts;
- domain terminology;
- local evidence representations;
- task details;
- rubric criteria;
- evaluation heuristics;
- generated workspace configuration;
- UI/view-model state.

The invariant is:

> **Different skills, different evidence structures, different workspaces; same validated transmission contracts.**

---

# Evidence and Trust Rules

These cases are intended to strengthen the evidence-grounded nature of Anveshan.

Agents must preserve the distinction between:

- **SOURCE-DERIVED FACT**
- **OBSERVED**
- **INFERRED**
- **UNVERIFIED**
- **UNKNOWN**

Never manufacture:

- a locator;
- an observation;
- a measurement;
- an expert statement;
- a confidence value;
- a certification;
- a peer-review result;
- a provenance record.

For synthetic/replay fixtures, say so explicitly.

A fixture can prove:

> "the execution seam works."

It cannot by itself prove:

> "this is authoritative real-world domain knowledge."

---

# Demo Portfolio vs Source Catalogue

The seven cases are **executable/demo archetypes**.

A broader source/case catalogue can still exist for:

- authentic source discovery;
- research benchmarking;
- future case selection;
- source attribution;
- modality coverage analysis.

That catalogue should not be confused with the seven cases themselves.

A catalogue entry is not evidence that a case is validated.

---

# Recommended Demo Priority

For a short judge-facing experience, the seven cases do not need equal screen time.

Recommended primary showcase:

### 1. Kolam
Best for:
- India/JAPAC relevance;
- visual differentiation;
- spatial GenUI.

### 2. Bicycle repair
Best for:
- diagnosis;
- practical impact;
- observation -> decision -> action -> outcome.

### 3. Micrometer
Best for:
- multimodal forensic depth;
- evidence/rubric/provenance;
- continuity with the existing Transmission Instrument.

### 4. Tabla
Best for:
- proving audio is a first-class evidence modality;
- gesture/sound/timing alignment.

The remaining three can serve as supporting cases in the case library and capability stress test.

---

# What Success Looks Like

A successful implementation should make a judge able to observe:

1. the user selects a materially different capability;
2. Anveshan identifies the evidence structure that matters;
3. Gemini performs meaningful multimodal interpretation;
4. the interface adapts to the capability;
5. the learner practices;
6. the system identifies meaningful divergence;
7. feedback is grounded in evidence and rubric;
8. the learner retries;
9. deterministic evaluation measures the change;
10. the result is represented as a provenance-aware transmission record.

The strongest product-level statement supported by this portfolio is:

> **Anveshan does not merely generate an explanation for a skill. It adapts the transmission environment to the structure of the expertise being transferred, while preserving a deterministic evidence-and-verification boundary.**

---

# Implementation Guidance for Agents

Before creating a new case:

1. Identify the **capability archetype**.
2. Define which modalities are genuinely relevant.
3. Define the observable/interpretable evidence.
4. Define the first meaningful divergence, where applicable.
5. Define the learner intervention and retry path.
6. Define how deterministic evaluation will operate.
7. Define which generated workspace primitives are needed.
8. Keep all domain assumptions outside the common eight-contract seam.
9. Mark synthetic/demo-only data honestly.
10. Add replay fixtures and negative tests before UI integration.

Do not add a case merely because it is culturally interesting or visually attractive. The case must test a meaningful multimodal reasoning pattern or strengthen the end-to-end transmission story.

---

# Status

**Portfolio status:** proposed engineering/demo matrix.

The existence of a case in this document does **not** mean its multimodal inference, evidence extraction, or domain correctness has been empirically validated.

Validation status must continue to follow `docs/validation/findings.md` and the relevant experiment plans.
