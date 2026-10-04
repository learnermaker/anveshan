# Anveshan — Source Strategy & Transmission Modes
## Research finding — 2026-10-04

## Status

**Research/design finding. Not validated.**

This document records the source strategy and transmission-mode finding that emerged while mapping credible source material to the seven-case multimodal capability portfolio.

The key conclusion is:

> **Anveshan does not need every capability to begin with a demonstration video. The source can be a demonstration, a desired outcome, a learner attempt, or a combination of these. The transmission mode should follow the evidence available and the reasoning problem.**

---

# 1. Three transmission directions

## A. Forward transmission

**Demonstration → capability**

The system starts with an expert or successful demonstration and helps a learner reproduce the capability.

~~~
SOURCE / DEMONSTRATION
        ↓
OBSERVE
        ↓
REPRESENT
        ↓
TEACH
        ↓
PRACTICE
        ↓
VERIFY
~~~

Strong examples: Bicycle repair, Micrometer, Origami, Tabla.

## B. Goal-conditioned transmission

**Desired outcome → plausible capability path**

The system starts with a target state rather than an observed procedure.

~~~
TARGET / DESIRED STATE
        ↓
STRUCTURE ANALYSIS
        ↓
CONSTRAINTS
        ↓
PLAUSIBLE INTERMEDIATE STATES
        ↓
PRACTICE PATH
        ↓
LEARNER ATTEMPT
        ↓
VERIFY AGAINST TARGET
~~~

**Kolam is the primary prototype candidate for this mode.**

This is deliberately framed as **goal-conditioned reconstruction**, not recovery of the original artist's exact procedure.

A final image can support claims about visible structure. It generally cannot, by itself, establish the exact historical stroke order, intent, or original construction process.

Therefore the system must distinguish:

- **OBSERVED:** properties visible in the target;
- **INFERRED:** a plausible construction strategy;
- **UNKNOWN:** the original procedure when the target image alone cannot establish it.

## C. Corrective transmission

**Learner attempt → divergence → capability**

~~~
LEARNER ATTEMPT
        ↓
EVIDENCE ANALYSIS
        ↓
FIRST MEANINGFUL DIVERGENCE
        ↓
TARGETED INTERVENTION
        ↓
RETRY
        ↓
VERIFY CHANGE
~~~

Strong examples: Square knot, Origami, Bicycle repair, Micrometer.

These modes can coexist in the same product.

---

# 2. Why Kolam is especially interesting

Kolam should not be reduced to another video-coaching case.

A target-image-first experience can ask:

> **“Given the desired Kolam, can Anveshan derive a defensible path for a learner to construct it?”**

The target image becomes the **desired state**.

Gemini can analyze visible structure such as:

- dot/pulli arrangement;
- symmetry;
- repeated motifs;
- line continuity;
- crossings;
- geometric relationships;
- candidate decomposition into substructures.

Research supports treating Kolam as a structured geometric system rather than only decorative imagery. Recent work describes Pulli Kolam in terms of dots, patterns, fills, lines, and color, while computational work has explored one-stroke Kolam generation and its underlying geometric constraints.

The product should then construct a **plausible practice path**.

It must not claim:

> “This is how the original artist drew this Kolam.”

unless an actual source demonstration establishes that.

The defensible claim is:

> “From the visible target structure, Anveshan derived this candidate construction path.”

That distinction is central to the product's evidence discipline.

---

# 3. Candidate Kolam workspace

## Spatial Reconstruction Workspace

~~~
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

Possible UI primitives:

- target image;
- detected/derived pulli grid;
- symmetry overlay;
- line topology view;
- candidate construction stages;
- interactive drawing canvas;
- target/current overlay;
- divergence marker;
- corrective micro-practice;
- uncertainty panel;
- provenance/evidence drawer.

This should be composed through the same bounded GenUI component catalog as the other workspaces.

---

# 4. Why this strengthens the GenUI thesis

The important demonstration is not that Gemini can describe a Kolam.

The important demonstration is:

> **Gemini determines that the problem is a spatial reconstruction problem, and the application therefore composes a spatial reconstruction interface.**

The stronger chain is:

~~~
EVIDENCE
   ↓
REASONING REQUIREMENT
   ↓
WORKSPACE COMPOSITION
   ↓
INTERACTION
   ↓
LEARNING / PRACTICE
~~~

Examples:

- Micrometer: precision + temporal + evidence comparison → **Forensic Transmission Instrument**
- Tabla: audio + temporal synchronization → **Rhythm Practice Instrument**
- Bicycle: observation + diagnosis + action + outcome → **Diagnostic Workspace**
- Kolam: target image + spatial structure + reconstruction → **Spatial Reconstruction Workspace**

This is stronger than seven differently themed dashboards.

---

# 5. Source strategy for the seven cases

The seven cases should use a **source portfolio**, not a single dataset.

| Case | Preferred source strategy | Primary evidence mode | Prototype role |
|---|---|---|---|
| Kolam | public/research image references + preferably Anveshan-owned target images | target image → spatial structure | goal-conditioned GenUI |
| Bicycle repair | Ego-Exo4D + ProSkill research sources; selected licensed/owned subset for demo | multimodal demonstration + skill assessment | primary external benchmark case |
| Micrometer | Anveshan-controlled recording | visual + temporal + audio + numeric | primary owned forensic case |
| Handloom/weaving | Anveshan-controlled recording | state transition | adaptive workspace breadth |
| Tabla | IIT Bombay Tabla Bol dataset for research; owned recording for public demo where needed | audio + timing + gesture | true audio multimodality |
| Origami | EvoStruggle + FoldingAgent research | spatial sequence + repeated attempts | primary spatial/sequence case |
| Square knot | EvoStruggle + supporting procedural-skill research | attempt + struggle/divergence + retry | clean verification case |

The distinction between **research source** and **shippable prototype asset** is mandatory.

A source may be excellent for benchmarking without being appropriate to redistribute in a public deployment.

---

# 6. Source notes

## 6.1 Ego-Exo4D

Ego-Exo4D V2 is a large-scale multimodal, multiview dataset with synchronized egocentric/exocentric video of skilled physical and procedural activities. It includes bike repair and provides video, audio, IMU, gaze, 3D environment data, hand/body annotations, object segmentation, keysteps, atomic action descriptions, participant narration, and expert commentary.

The expert commentary is particularly relevant because domain experts comment at specific video moments and may provide spatial drawings and proficiency assessments.

Relevant documentation:

- https://docs.ego-exo4d-data.org/
- https://docs.ego-exo4d-data.org/overview/
- https://docs.ego-exo4d-data.org/annotations/keystep/
- https://docs.ego-exo4d-data.org/annotations/expert_commentary/
- https://docs.ego-exo4d-data.org/annotations/atomic_descriptions/

**Prototype use:** benchmark/research evidence and source for selected bike-repair experiments.

**Asset constraint:** access requires acceptance of the dataset license agreement, and the documentation specifies restrictions on redistribution and other use. Prefer a small approved research subset and Anveshan-owned recordings for the public demo.

## 6.2 ProSkill

ProSkill is a WACV 2026 benchmark for segment-level skill assessment in procedural videos. Its study includes Ego-Exo4D bike repair and other procedural datasets, with absolute and pairwise skill assessment.

**Prototype use:** benchmark evidence and evaluation-design reference. Do not present ProSkill labels as Anveshan's own evaluation.

## 6.3 EvoStruggle

EvoStruggle contains manual-activity videos covering origami, knot tying, tangrams and card shuffling.

The repository reports:

- more than 60 hours of video;
- 2,793 videos;
- 5,385 annotated temporal struggle segments;
- 76 participants;
- five attempts/repetitions per task.

Origami tasks include Paper Plane, Fox, Helmet and Butterfly. Knot tasks include Ashley Bend, Blake's Hitch, Carrick Bend, Double Fisherman's Bend and Slim Beauty Knot.

The repository states that the dataset is **CC BY-NC 4.0**.

**Prototype use:** repeated-attempt reasoning, struggle localization, baseline/retry experiments, spatial procedural cases, and knot/origami source research.

Treat the license as a research/source constraint rather than automatic permission to bundle raw media into a public/commercial product.

## 6.4 FoldingAgent

FoldingAgent is research on reconstructing parametric origami procedures from demonstration videos. Its representation includes source keyframes, 3D geometric states, layer-count maps, and crease patterns.

**Prototype use:** research support for the Spatial Sequence Workspace and intermediate-state representation. Do not imply that Anveshan reproduces the research system unless it actually implements and evaluates that capability.

## 6.5 Tabla

The IIT Bombay Digital Audio Processing Lab's Tabla Bol Recitation Dataset contains approximately 12 minutes of audio across 20 traditional compositions performed by a professional tabla artist. It includes oral recitation, tabla playing, two microphone recordings, and time-aligned stroke/bol transcription with start time, end time and label.

The dataset is made available for non-commercial research purposes and requires contacting the lab for access.

**Prototype use:** audio/timing experiment design and research benchmarking. For the public hackathon prototype, prefer an Anveshan-controlled recording unless permission clearly allows the intended use.

## 6.6 Kolam

The Kolam source landscape is different.

A 2024 open-access Heritage Science paper, **KolamNetV2**, documents a Kolam image dataset used for classification and digital heritage preservation. It describes 13 common categories and notes challenges from varied backgrounds, viewpoints, colors and image conditions.

A 2026 Heritage Science paper, **An algorithm for one-stroke kolam generation using a gating structure**, explores computational generation of one-stroke dotted Pulli Kolam and its underlying mathematical structure.

A 2026 paper, **Pulli Kolam: A Traditional South Indian Craft Practice for Representing Data**, treats Pulli Kolam as a structured practice with mapping strategies involving dots, patterns, fills, lines and color.

There are also smaller public image datasets, such as a 360-row Hugging Face Kolam image/text dataset. These are useful for exploration but are not authoritative cultural or procedural sources.

**Prototype use:** target-image / desired-state input rather than a requirement for a public demonstration video.

Ideally use an Anveshan-owned target image and, if cultural/process claims are made, an attributed authoritative source.

---

# 7. Goal-conditioned reconstruction: evidence boundary

A target image can establish **visible target properties**.

It cannot necessarily establish:

- original artist;
- original intent;
- original construction order;
- original hand motion;
- historical context;
- culturally specific meaning;
- exact material technique.

Therefore:

### Valid

> “The target exhibits bilateral symmetry.”

### Potentially valid inference

> “A plausible construction strategy is to establish the central symmetry before completing repeated motifs.”

### Invalid without source evidence

> “The artist first drew the left loop and then mirrored it.”

The last statement requires a demonstration or other source evidence.

This distinction should be encoded into both the prototype UX and agent guidance.

---

# 8. Source → evidence → workspace decision

Every case should define:

~~~
SOURCE TYPE
   ↓
AVAILABLE EVIDENCE
   ↓
REASONING ARCHETYPE
   ↓
TRANSMISSION MODE
   ↓
WORKSPACE
~~~

Examples:

### Kolam

target image → visible spatial structure → spatial reconstruction → goal-conditioned → Spatial Reconstruction Workspace

### Bicycle

expert/learner video + annotations → state/action/outcome evidence → diagnosis → forward + corrective → Diagnostic Workspace

### Tabla

audio + time alignment + optional video → stroke/sound/timing evidence → temporal synchronization → forward + corrective → Rhythm Practice Instrument

---

# 9. Common-contract implication

No common-contract change is required by this finding.

A target-image Kolam case can still produce:

- **EvidenceRef** — target image and derived evidence regions;
- **KnowledgePackage** — claims about target structure and explicitly marked inferred construction strategies;
- **RubricDefinition** — observable target criteria;
- **PracticeTask** — bounded construction task;
- **LearnerAttempt** — learner drawing/output;
- **Evaluation** — criterion-level comparison;
- **Feedback** — evidence-linked correction;
- **TransmissionRecord** — final transmission event.

The **source modality is not the contract boundary**. Evidence and transmission semantics are.

---

# 10. Experiments to run

## G1 — Target structure extraction

Input: target Kolam image.

Output:

- spatial structure;
- symmetry;
- grid;
- motifs;
- continuity constraints;
- uncertainty.

## G2 — Candidate construction path

Input: target structure.

Output:

- candidate intermediate states;
- candidate sequence;
- explicit uncertainty;
- explanation of which parts are inferred.

Success criterion: expert agreement that the proposed path is plausible and reaches the target.

## G3 — Target-to-attempt verification

Input: target image + learner attempt image or interactive trace.

Output:

- criterion-level comparison;
- first meaningful divergence;
- evidence region;
- corrective action.

Success criterion: agreement with a human rubric.

## G4 — Retry improvement

Input: target + baseline + intervention + retry.

Output:

- deterministic criterion scores;
- measurable gain.

Success criterion: retry improvement is reconstructable from stored evaluations.

---

# 11. What this does not prove

This finding does **not** prove that Gemini can:

- recover an original procedure from a final image;
- infer culturally correct meanings;
- infer historical intent;
- generate an optimal construction sequence;
- guarantee that a generated procedure is physically correct;
- replace an expert for all skills.

Those remain hypotheses.

The prototype should make uncertainty visible rather than hiding it.

---

# 12. Recommended prototype source portfolio

### Deep implementations

1. **Kolam — target-image / goal-conditioned**
2. **Bicycle repair — multimodal procedural**
3. **Micrometer — controlled forensic**
4. **Tabla — audio-temporal**

### Supporting cases

5. **Origami — spatial sequence**
6. **Square knot — first divergence / retry**
7. **Handloom — state transition**

This gives the prototype four materially different source/interaction patterns while preserving the seven-case capability matrix.

---

# 13. Working principle

Adopt:

> **Anveshan should not assume that knowledge always arrives as a demonstration. It should identify whether the available source describes an expert process, a desired state, or a learner attempt, and compose the transmission experience accordingly.**

This extends the existing Anveshan thesis; it does not replace it.

The north-star question remains:

> **Can Anveshan help one human successfully pass a meaningful piece of real-world understanding or capability to another human, while preserving the evidence, context, provenance, and lineage that make that knowledge trustworthy?**

---

# References

- Ego-Exo4D: https://docs.ego-exo4d-data.org/
- Ego-Exo4D overview: https://docs.ego-exo4d-data.org/overview/
- Ego-Exo4D keysteps: https://docs.ego-exo4d-data.org/annotations/keystep/
- Ego-Exo4D expert commentary: https://docs.ego-exo4d-data.org/annotations/expert_commentary/
- Ego-Exo4D atomic actions: https://docs.ego-exo4d-data.org/annotations/atomic_descriptions/
- ProSkill WACV 2026: https://openaccess.thecvf.com/content/WACV2026/html/Mazzamuto_ProSkill_Segment-Level_Skill_Assessment_in_Procedural_Videos_WACV_2026_paper.html
- EvoStruggle: https://github.com/FELIXFENG2019/EvoStruggle
- FoldingAgent: https://maya-moriya.github.io/origami-page/
- IIT Bombay Tabla Bol Dataset: https://www.ee.iitb.ac.in/student/~daplab/datasets/tabla_bol.html
- KolamNetV2: https://www.nature.com/articles/s40494-024-01167-8
- One-stroke Kolam generation: https://www.nature.com/articles/s40494-026-02310-3
- Pulli Kolam: https://arxiv.org/abs/2603.02343
- Example public Kolam image dataset: https://huggingface.co/datasets/sumit-06/kolam-text-to-image
