# Anveshan — Seven-Case Data Source Matrix

> Research/reference note. The canonical seven-case definition remains in `docs/status/CANONICAL-SOURCES.md` and `docs/research/multimodal-capability-case-portfolio.md`.
>
> **Critical distinction:** a research dataset is not automatically a shippable prototype asset. Respect licensing, access, consent, attribution, and redistribution constraints.

## Seven-case matrix

| # | Case | Peculiar capability / reasoning | Key evidence | Preferred research/data sources | Prototype posture |
|---|---|---|---|---|---|
| 1 | **Kolam** | Goal-conditioned spatial reconstruction from a desired outcome | Image, geometry, topology, symmetry, target-vs-attempt | KolamNetV2; Kolam structural/one-stroke research; Pulli Kolam research | Prefer Anveshan-owned target image; research images for benchmarking/context |
| 2 | **Bicycle puncture repair** | Diagnosis / decision: observation → diagnosis → action → result | Ego/exo video, temporal state, objects, expert commentary, action descriptions | **Ego-Exo4D + ProSkill**; optionally Ego-EXTRA | Research/benchmark subset; prefer owned recording for unrestricted demo |
| 3 | **Micrometer zeroing / measurement** | Precision / forensic multimodal reasoning | Video, audio, temporal events, numeric readings, rubric | **Anveshan-controlled recording** | Primary owned case |
| 4 | **Handloom / paper weaving** | Material state transition | Over/under state, alignment, sequence, emerging pattern | **Anveshan-controlled recording** | Primary owned case |
| 5 | **Tabla basic stroke / rhythm** | Audio-visual temporal synchronization | Audio, timing, gesture/video, repeated rhythm | **IIT Bombay Tabla Bol Recitation Dataset** + owned recording | Research benchmark; owned recording preferred for public demo |
| 6 | **Origami / paper folding** | Sequential spatial transformation | Fold geometry, orientation, intermediate state, sequence | **EvoStruggle + FoldingAgent** | Research-backed case; verify rights before bundling media |
| 7 | **Square knot / basic knot tying** | First divergence / verification and retry | Crossings, orientation, hand/rope movement, sequence, final state | **EvoStruggle + procedural-skill research** | Research-backed case; owned recording safest for unrestricted demo |

## Key sources

### Ego-Exo4D
Large-scale multimodal/multiview procedural dataset. Particularly relevant to bicycle repair. Provides synchronized egocentric/exocentric video plus audio, IMU, gaze, 3D environment data, hand/body annotations, object segmentation, keysteps, atomic actions, narration and expert commentary.

**Use:** procedural reasoning, evidence localization, expert commentary, benchmark experiments.

**Constraint:** license/access and redistribution restrictions apply. Do not assume raw media can be bundled into the public prototype.

### ProSkill
WACV 2026 benchmark for segment-level skill assessment in procedural videos, including Ego-Exo4D bicycle-repair material.

**Use:** skill-assessment methodology, benchmark/evaluation design.

**Constraint:** ProSkill labels should not be presented as Anveshan's own authoritative evaluation.

### EvoStruggle
Manual-activity dataset covering origami and knot tying, with repeated attempts and annotated struggle segments.

**Use:** attempt progression, struggle/divergence localization, baseline-vs-retry experiments.

**Constraint:** CC BY-NC 4.0; treat as a research/source constraint rather than automatic permission for public/commercial redistribution.

### FoldingAgent
Research on reconstructing parametric origami procedures from demonstration videos, including geometric states and crease representations.

**Use:** origami intermediate-state representation and Spatial Sequence Workspace research.

### IIT Bombay Tabla Bol Recitation Dataset
Audio dataset with professional tabla performance, oral recitation, multiple microphone recordings, and time-aligned stroke/bol transcription.

**Use:** audio/timing experiments and gesture/sound alignment.

**Constraint:** non-commercial research access; contact the lab and use an owned recording for public demo where appropriate.

### Kolam research sources
KolamNetV2 and related work provide image/structural research material for Kolam analysis, digital preservation and computational generation.

**Use:** target-image analysis, spatial structure, symmetry, topology and benchmarking.

**Important evidence boundary:** a final Kolam image establishes visible target properties but generally does not establish the original artist's exact procedure, intent, or cultural/historical context.

## Supplemental candidate source

**Ego-EXTRA** is a potentially useful additional procedural source for bicycle/expert-feedback research: egocentric procedural video with expert–trainee dialogue and visual QA material.

Treat it as a supplemental research candidate, not a replacement for the current canonical source strategy.

## Source-selection principle

Anveshan should use a **source portfolio**, not force one dataset across all seven cases:

```text
CASE
  ↓
AVAILABLE SOURCE
  ↓
EVIDENCE MODALITIES
  ↓
REASONING ARCHETYPE
  ↓
TRANSMISSION MODE
  ↓
WORKSPACE
```

The preferred public posture is:

- use external datasets for research, benchmarking and methodology where permitted;
- use Anveshan-owned recordings/images when unrestricted prototype assets are required;
- preserve provenance and source/licensing status in the case pack;
- never turn synthetic/replay fixtures into claims of authentic expert evidence.

## References

- Ego-Exo4D: https://docs.ego-exo4d-data.org/
- ProSkill: https://fpv-iplab.github.io/ProSkill/
- EvoStruggle: https://github.com/FELIXFENG2019/EvoStruggle
- FoldingAgent: https://maya-moriya.github.io/origami-page/
- IIT Bombay Tabla Bol Dataset: https://www.ee.iitb.ac.in/student/~daplab/datasets/tabla_bol.html
- KolamNetV2: https://www.nature.com/articles/s40494-024-01167-8
- Ego-EXTRA: https://fpv-iplab.github.io/Ego-EXTRA/
