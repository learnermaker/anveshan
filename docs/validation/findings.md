# Validation Findings

**Review checkpoint:** 2026-10-06

## Scope notice

All findings below are **engineering and capability evidence** on internet-licensed and synthetic data.
No real learner sessions have been run. No human-learner improvement has been measured.
These findings establish that the system can receive, structure, and evaluate demonstration media
at a level sufficient to demonstrate the capability to the AI Builder Cup 2026 judges.
They do **not** establish that real learners improve using the system.

---

## Partially Validated

### Hero case pipeline (Kolam, Tabla, Origami)

The three hero cases demonstrate end-to-end processing of real (internet-licensed) source media:
goal extraction, rubric generation, and deterministic evaluation of synthetic attempts.

**What is validated (engineering evidence):**
- Kolam evaluator: 50/50 criterion status agreement, 10/10 first-divergence agreement on SYNTHETIC attempts. Photo-path registration works for rotated and scaled rasters. (E1)
- Tabla evaluator: 49/49 criterion status, 7/7 first-divergence, onset F1=0.999 on SYNTHETIC attempts. Timbre MFCC classes computed correctly. (E2)
- Origami evaluator: goal build extracts 5 valid states (R0–R4) from a 194-second video using Flash-Lite; evaluator functional. (E3)

**What is NOT validated:**
- Real learner improvement or skill transfer.
- Human-judged evaluation quality (no blind human evaluation has been run).
- Whether the Origami goal model captures the critical petal fold (R5, R6 missing).
- Whether feedback causes learners to improve.

### Universal composition pipeline

The universal composer can process novel image and video skills without skill-specific code.

**What is validated (capability evidence):**
- Image compose: perceive → propose → build → evaluate works on a real Kolam image and a synthetic rangoli. (E4)
- Similarity gate: same image = 1.00; half-erased = 0.96; gradient (blank/uniform) correctly refused. (E4)
- Video compose: tabla_chanderi video correctly classified as procedure + temporal_pattern. (E4)

**What is NOT validated:**
- Quality of the AI-judged property checks (marked lower confidence than deterministic checks).
- Universal pipeline on real learner attempts.
- Whether composed cases generalise to genuinely new skill domains not seen in testing.

### Model latency budget

Flash-Lite (`gemini-3.5-flash-lite`) meets the per-call target (~2–6 s per image, ~2.3 s per 12 s audio clip). Case builds within 45 s for hero cases using recorded mode. (E5)

---

## Unvalidated (PROPOSED or IMPLEMENTED but no evidence)

### Knowledge fidelity (expert review)

No expert has reviewed any of the three hero case knowledge packages. All packages carry the status
`review_status: pending` and the warning "package not expert-approved". Claims marked OBSERVED are
grounded deterministically; claims marked INFERRED carry confidence ≤ 0.5. No expert review gate
has been passed.

### Evidence-grounded feedback to learners

Feedback generation is IMPLEMENTED (drift message + drill hint from the criterion map). It has
not been evaluated against a rubric or confirmed helpful by real learners.

### Learner retry and measurable improvement

No end-to-end learner session with real media has been run. The transmission bundle is validated
structurally (schema pass) in recorded mode but gain values come from synthetic data.

### Human-learner skill transfer

No human learner has used the system. No before/after skill measurement exists.

---

## Invalidated / Strategically Downgraded

### AI interviews as novelty
Downgraded. Current products already provide AI-guided expert interviews and memory capture.

### Tacit-knowledge capture as novelty
Downgraded. Current products including Tacivo, Tacit/getAbstract and Accrete explicitly target expert/tacit knowledge capture.

### AI apprenticeship as novelty
Downgraded. 2026 research demonstrates active AI-assisted apprenticeship work.

### Learner video assessment as novelty
Downgraded. 2026 research and ProSkill/ProSkill++ show active procedural skill-assessment research.

---

## Newly Documented Research Hypotheses

### Goal-conditioned transmission

A desired visual outcome may be sufficient to initiate a transmission workflow when the capability
can be represented through observable target structure and plausible intermediate states.

**Current status:** unvalidated hypothesis. Kolam demonstrates the technical flow; no human
learner outcome data exists.

### Adaptive source-to-workspace composition

Anveshan may need to choose a transmission mode based on source type:

- demonstration → forward transmission;
- desired state → goal-conditioned reconstruction;
- learner attempt → corrective transmission.

**Current status:** unvalidated product/GenUI hypothesis.

---

## Rule

No prototype capability is marked validated until an experiment produces evidence.
Engineering evidence on synthetic data is recorded as "engineering validation" (not "validated").
Human-learner evidence requires a real session with a real learner and a measurable outcome.
