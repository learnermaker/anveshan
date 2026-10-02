# Anveshan — Opportunity Matrix & Adversarial Convergence Gate
## 2026-10-03

> Status: exploration artifact. No product thesis is locked.
>
> Principle: preserve breadth until evidence kills directions. Do not protect the existing Anveshan concept merely because it already has design work.

## 1. Strategic observation

The current Google capability surface creates three unusually strong primitives:

1. Temporal multimodal understanding — Gemini can inspect video, answer questions about specific moments, and use adaptive/agentic video processing on supported models.
2. Cross-modal representation — Gemini Embedding 2 maps text, images, video, audio, and documents into a shared embedding space.
3. Embodied reasoning — Gemini Robotics ER 2 is explicitly positioned around spatial/temporal reasoning, video progress understanding, success detection, pointing, instrument reading, and multi-step orchestration.

Google's world-model research adds a fourth signal: Genie 3 demonstrates real-time interactive generated environments, but it is a limited research preview and should not be treated as a dependable hackathon dependency.

The resulting opportunity space is broader than "knowledge transfer":

OBSERVE → REPRESENT STATE → MODEL ACTION → PREDICT/DETECT OUTCOME → INTERVENE → VERIFY CHANGE

This is the working abstraction for exploration, not a final product decision.

## 2. Candidate thesis families

### A. Human capability / skill

| ID | Thesis | Core user | Technical wedge | Measurable outcome | Main risk |
|---|---|---|---|---|---|
| A1 | Human Skill World Model | learner/coach | stateful skill representation | improvement after intervention | resembles AI coaching |
| A2 | Demonstration Compiler | expert/worker | video → executable procedure | fidelity to expert sequence | work-instruction competition |
| A3 | AI Apprentice | trainee | learns from demonstrations + attempts | time-to-competency | crowded tutoring |
| A4 | Skill Referee | evaluator | evidence-grounded criterion scoring | evaluator agreement | scoring is commoditized |
| A5 | Failure Intelligence | coach/operator | failure event → causal hypothesis | repeat-failure reduction | needs reliable labels |
| A6 | Counterfactual Coach | trainee/operator | "what if this action changed?" | decision quality | difficult causal validity |
| A7 | Skill Variant Engine | expert/manager | compare multiple successful demonstrations | robust invariant extraction | needs multiple examples |
| A8 | Skill Provenance / Git for Practice | regulated trainer | version skill + evidence + changes | traceability/change quality | enterprise workflow complexity |
| A9 | Living Procedural Encyclopedia | field worker | searchable procedural state/action/outcome memory | retrieval-to-resolution time | can collapse into RAG |
| A10 | AI-to-Human-to-AI Transfer | organization | transfer practical know-how through machine representation | transfer fidelity | too broad for MVP |

### B. Physical-world intelligence

| ID | Thesis | Core user | Technical wedge | Measurable outcome | Main risk |
|---|---|---|---|---|---|
| B1 | Physical-World Inspector | field operator | multimodal scene/state interpretation | missed-condition reduction | generic inspection |
| B2 | Repair Intelligence | technician | identify state + likely next action | repair time / first-pass success | safety/domain specificity |
| B3 | Maintenance Change Detector | plant/facility | before/after state transitions | anomaly detection precision | needs controlled footage |
| B4 | Field AI Partner | field worker | continuous scene + task context | task completion time | live inference cost |
| B5 | Multi-Human Physical Coordination | supervisor | detect coordination state | delay/error reduction | hard multi-person reasoning |
| B6 | Instrument/Panel Reasoner | technician | read instruments + infer process state | reading/diagnosis accuracy | narrow vertical |
| B7 | Physical Workflow Auditor | operations manager | observed process vs intended process | deviation detection | overlaps work-analysis vendors |
| B8 | Asset State Passport | maintenance/ops | asset lifecycle state graph | faster handoff/history reconstruction | data integration |

### C. Simulation / world-state

| ID | Thesis | Core user | Technical wedge | Measurable outcome | Main risk |
|---|---|---|---|---|---|
| C1 | Rare-Event Simulator | operator/trainer | generate/rehearse unusual states | response quality | Genie access/dependency |
| C2 | Counterfactual Workplace | manager/trainer | alter state and rehearse consequences | decision quality | simulation validity |
| C3 | Interactive Historical World | learner/media | explorable evidence-grounded environment | learning/engagement | Genie access + novelty |
| C4 | Simulation Apprenticeship | trainee | practice decisions before reality | error avoidance | hard to build robust simulator |
| C5 | Skill Evolution Simulator | expert | vary technique and inspect outcomes | technique discovery | causality problem |
| C6 | Agent Stress Lab | developer/operator | adversarial environmental changes | robustness | abstract product |

### D. Failure / anomaly intelligence

| ID | Thesis | Core user | Technical wedge | Measurable outcome | Main risk |
|---|---|---|---|---|---|
| D1 | Failure Replay Engine | operator | reconstruct exact failure timeline | investigation time | needs good event extraction |
| D2 | Near-Miss Memory | safety/quality | preserve near misses as reusable cases | recurrence reduction | sensitive data |
| D3 | Process Drift Detector | manufacturing/ops | compare current process to baseline | drift detection | incumbent overlap |
| D4 | Root-Cause Evidence Graph | analyst | event sequence + evidence graph | investigation accuracy | graph itself not novel |
| D5 | First Divergence Detector | operator | find earliest deviation before failure | time-to-diagnosis | technically interesting |
| D6 | Recovery Intelligence | operator | identify what restored normal state | recovery-time reduction | requires outcome labels |

### E. Retail / commerce

| ID | Thesis | Core user | Technical wedge | Measurable outcome | Main risk |
|---|---|---|---|---|---|
| E1 | Store State Engine | store manager | scene → current operational state | issue detection/action time | incumbents |
| E2 | Customer Journey State Reconstruction | retailer | sequence of physical interactions | conversion/abandonment insight | privacy |
| E3 | Merchandising Change Reasoner | brand | before/after + sales context | causal hypothesis quality | causal overclaim |
| E4 | Retail Recovery Agent | associate | identify issue + next physical action | recovery completion | workflow integration |
| E5 | Waste/Expiry Intervention | retailer | detect stock condition + intervention | waste reduction | camera/data access |

### F. Manufacturing / industrial

| ID | Thesis | Core user | Technical wedge | Measurable outcome | Main risk |
|---|---|---|---|---|---|
| F1 | Process State Twin | supervisor | current state + transition history | anomaly/decision latency | digital twin crowding |
| F2 | First-Divergence Manufacturing | quality engineer | earliest deviation from successful run | root-cause lead time | requires paired runs |
| F3 | Setup Verification | technician | verify setup sequence visually | setup errors | generic CV if shallow |
| F4 | Changeover Intelligence | plant operator | compare changeover attempts | changeover time/errors | data collection |
| F5 | Quality-by-Process | QA | infer quality risk before final inspection | early-warning precision | high-stakes |
| F6 | Human-Machine Handoff Monitor | supervisor | detect handoff readiness/state | handoff defects | multi-modal complexity |

### G. Sustainability / social impact

| ID | Thesis | Core user | Technical wedge | Measurable outcome | Main risk |
|---|---|---|---|---|---|
| G1 | Repairability Intelligence | consumer/technician | diagnose repair path from evidence | repair success | safety |
| G2 | Maintenance-for-Longevity Coach | owner/technician | maintenance state + next action | asset life / avoided replacement | long-term metric |
| G3 | Agricultural Practice Verifier | farmer/trainer | field practice → evidence → feedback | practice adherence | domain variability |
| G4 | Low-Resource Skill Transfer | learner/community | multimodal/local-language transmission | learning improvement | dataset/linguistic quality |
| G5 | Waste Sorting Coach | worker/community | observe material → classify action | sorting accuracy | crowded category |
| G6 | Disaster Preparedness Rehearsal | household/community | scenario → decision rehearsal | response quality | safety/simulation validity |

### H. BFSI / information-heavy but stateful

| ID | Thesis | Core user | Technical wedge | Measurable outcome | Main risk |
|---|---|---|---|---|---|
| H1 | Financial Event Reconstruction | analyst/customer support | reconstruct events across documents/messages | resolution time | integration |
| H2 | Fraud Journey Replay | investigator | transaction timeline + evidence | investigation speed | incumbent fraud platforms |
| H3 | Case-State Engine | operations | current case state + next transition | SLA/rework | generic workflow |
| H4 | Evidence Conflict Resolver | analyst | identify contradictory records | contradiction detection | RAG-adjacent |
| H5 | Customer Financial Incident Explainer | support | evidence-grounded event narrative | support resolution quality | privacy/regulation |

### I. Media / knowledge / culture

| ID | Thesis | Core user | Technical wedge | Measurable outcome | Main risk |
|---|---|---|---|---|---|
| I1 | Interactive Evidence Documentary | audience/student | source evidence → explorable world | comprehension | Genie availability |
| I2 | Living Cultural Practice Model | community/learner | practice + variants + lineage | transmission fidelity | can resemble archive |
| I3 | Aeneas-like Multimodal Research Assistant | historian | evidence reconstruction | researcher time | Google already has adjacent research |
| I4 | Procedural Media Index | producer/researcher | action/outcome indexing across video | retrieval accuracy | search product |
| I5 | Media Fact-to-Scene Mapper | journalist/educator | claims mapped to visual evidence | verification time | fact-checking crowd |

## 3. First adversarial filter

### Directions that currently look weak as standalone hackathon theses

**Generic AI coach**
- Sports, dance, music and other performance coaching already have multiple products.
- Sports AI Coach markets frame-by-frame biomechanics, scoring and personalized drills; Danzu markets six-axis dance scoring; Pickup Music offers AI video analysis and practice plans.
- A new wrapper around "upload video → score → feedback" is insufficient.

**Generic shelf intelligence**
- ShelfView/Focal and multiple retail CV vendors already solve shelf visibility, availability and action.
- A demo that merely detects products, stockouts or planogram violations is unlikely to demonstrate a distinctive research/engineering thesis.

**Generic construction safety**
- PPE/hazard/progress monitoring is already a standard VLM/CV pattern.
- A stronger direction would need a state-transition or intervention loop beyond detection.

**Generic work-instruction generation**
- SHOWHOW already turns shop-floor video into reviewed work instructions and change proposals.
- Demonstration Compiler must therefore solve something materially harder than "video → SOP."

**Generic RAG / knowledge graph**
- Google itself now offers multimodal embeddings and managed retrieval primitives.
- The product must depend on temporal/state reasoning or intervention, not retrieval alone.

## 4. What survives the first filter

The following patterns are more interesting because the model must infer a transition, not merely label a frame.

### P1 — First Divergence
Given a successful reference run and a failed run, identify the earliest meaningful divergence and connect it to downstream consequences.

Why interesting:
- temporal reasoning is essential;
- the output can be evidence-linked;
- evaluation can be objective;
- it naturally creates a before/after comparison;
- it can apply to manufacturing, repair, training, operations and finance.

### P2 — Recovery Intelligence
Given a process that went wrong and eventually recovered, identify the sequence of corrective actions that restored the desired state.

Why interesting:
- most systems focus on detecting failures;
- recovery is directly actionable;
- produces a reusable state-transition case;
- potentially valuable for human training.

### P3 — Demonstration Compiler
Convert an expert demonstration into a machine-readable state/action/outcome model, then test whether a learner/operator can execute it.

Important caveat:
- generic SOP generation is already occupied;
- differentiation must be executable/evaluable state transitions, not formatted instructions.

### P4 — Counterfactual Rehearsal
Represent a real process and let a user alter one action/condition to inspect the predicted consequence.

Important caveat:
- prediction must be framed as a hypothesis unless validated;
- generated simulation cannot be treated as ground truth.

### P5 — Evidence-Linked Intervention
Detect a state, recommend a concrete action, observe the next state, and determine whether the intervention actually worked.

This creates a closed loop:

OBSERVE → DIAGNOSE → INTERVENE → OBSERVE → VERIFY

This is stronger than a one-shot classifier because success is measurable.

### P6 — Skill Variant Mining
Given several demonstrations that all succeed, discover:
- invariant actions;
- optional actions;
- order constraints;
- context-dependent choices;
- failure-prone variations.

This moves from "copy the expert" toward "understand what actually matters."

## 5. Candidate verticals for these patterns

| Vertical | First Divergence | Recovery | Demonstration Compiler | Counterfactual | Intervention Verification |
|---|---:|---:|---:|---:|---:|
| Manufacturing | very strong | very strong | strong | strong | very strong |
| Repair/maintenance | strong | very strong | strong | strong | very strong |
| Retail operations | strong | strong | medium | medium | strong |
| Field service | very strong | very strong | strong | medium | very strong |
| Construction | strong | strong | medium | medium | strong |
| Agriculture | medium | strong | strong | medium | strong |
| Sports | strong | medium | medium | medium | strong |
| Music/dance | strong | medium | medium | medium | strong |
| Finance | very strong | strong | weak | medium | strong |
| Cultural practice | medium | medium | very strong | strong | medium |
| Enterprise digital work | very strong | strong | strong | strong | strong |

These are opportunity hypotheses, not claims of market size.

## 6. Hackathon feasibility filter

A thesis gets a GO for prototyping only if it can satisfy all of these:

1. One narrow workflow can be demonstrated end-to-end.
2. The core AI capability is visibly necessary.
3. At least one difficult multimodal inference is observable in the demo.
4. There is a measurable outcome rather than a subjective "looks useful."
5. A small synthetic or self-recorded dataset can prove the hypothesis.
6. No proprietary customer data is required.
7. The prototype can survive mostly on free/eligible Gemini API usage during exploration.
8. Specialized preview models are optional or isolated.
9. The 3-minute demo can show the before → reasoning → action → after loop.
10. The product remains meaningful if the most exotic Google research model is unavailable.

## 7. Free-tier-first architecture implications

The free-tier constraint changes what we should prototype first.

### Prefer
- short clips;
- repeated queries over cached/reused artifacts;
- structured outputs;
- small evaluation sets;
- local deterministic preprocessing;
- fixture/replay mode;
- one-shot multimodal calls followed by local analysis;
- targeted high-value model calls;
- text-first reasoning after media extraction;
- model gateway abstraction.

### Avoid as core dependency
- continuous real-time multimodal streaming;
- long-running video analysis on every user interaction;
- high-volume embedding of large corpora;
- always-on cameras;
- massive generated simulations;
- high-frequency agent loops;
- product concepts whose only differentiator is access to a preview model.

Current Gemini video tooling supports large files and timestamp queries, and some recent Flash models support agentic video navigation. However, media processing remains a resource that should be deliberately budgeted. Gemini Embedding 2 supports multimodal representations, but quota/pricing must be verified against the exact model/account configuration before treating it as a free-tier primitive.

## 8. Five experiment families to run before choosing a product

### X1 — Can Gemini find the first meaningful divergence?
Dataset:
- 3 successful demonstrations
- 3 intentionally failed demonstrations
- same task, controlled camera

Question:
"What changed first, and at what moment did the failed attempt become observably different from the successful reference?"

Success criterion:
- temporal localization within a small tolerance;
- correct action/state description;
- evidence timestamp.

### X2 — Can Gemini infer recovery sequences?
Dataset:
- one process with injected fault;
- one or more corrective actions;
- return to successful state.

Question:
"What action restored the desired state, and what evidence shows that recovery occurred?"

Success criterion:
- correct recovery action;
- correct before/after evidence;
- no invented causal claims.

### X3 — Can a demonstration become an executable state model?
Input:
- expert video.

Output:
- states;
- actions;
- preconditions;
- observable success criteria;
- failure conditions.

Then:
- give a new attempt video;
- ask whether the transition sequence satisfies the model.

Success criterion:
- agreement with human rubric.

### X4 — Can the system verify an intervention?
Loop:
1. detect problem;
2. recommend one action;
3. user performs action;
4. analyze post-action state.

Success criterion:
- state change detection;
- action-success classification;
- evidence-linked explanation.

### X5 — Can multiple experts reveal invariants?
Input:
- 3–5 successful demonstrations from different people.

Output:
- invariant steps;
- acceptable variants;
- context-dependent choices.

Success criterion:
- expert agreement on extracted invariants.

## 9. Strongest technical abstraction currently

The most reusable abstraction discovered so far is:

STATE → ACTION → OUTCOME

A richer event object is:

State_t
- observed evidence
- hidden-state hypothesis
- uncertainty

Action_t
- actor
- action
- timing
- intent hypothesis

Outcome_t+1
- observed change
- success/failure
- evidence
- uncertainty

Transition
- preconditions
- action constraints
- expected effects
- observed effects

This is more defensible as a technical contribution than:
- "we built a chatbot";
- "we built a RAG system";
- "we summarize videos";
- "we score skills."

## 10. Convergence rule

Do NOT choose a vertical yet.

Choose the best validated technical phenomenon first, then bind it to a vertical where:
- the phenomenon is valuable;
- the evaluation is objective;
- the data is obtainable;
- the demo is visually obvious;
- the Google stack is central;
- the free-tier path is credible.

The first convergence gate should therefore be:

"Which of X1–X5 produces a convincing result with a tiny self-generated dataset?"

Only after that should we decide whether the product is manufacturing, repair, field service, sustainability, education, retail, BFSI, media, or something else.

## 11. Current working shortlist — not a ranking

These are the five concepts worth experimental validation because they represent genuinely different product shapes:

1. First Divergence Engine — find the earliest meaningful deviation between successful and failed real-world processes.
2. Recovery Intelligence — learn which interventions actually restore a process after failure.
3. Demonstration Compiler — compile human demonstrations into executable state/action/outcome models.
4. Intervention Verifier — close the loop from observation → recommended action → observed post-action result.
5. Counterfactual Rehearsal — let people explore how changing a state/action might alter an outcome, with explicit uncertainty.

The existing "expert → learner → transmission" product remains alive as a possible application of these primitives, but it is no longer the assumed product.

## 12. Kill criteria

Immediately demote a direction if experiments show:
- the model only produces plausible prose;
- temporal localization is unreliable;
- state transitions are hallucinated;
- evaluation depends entirely on model self-scoring;
- a deterministic CV rule solves the same problem;
- the product is indistinguishable from an existing video coach;
- the product requires unavailable Google research access;
- free-tier exploration cannot produce enough evidence to validate the thesis;
- the "AI moment" is not visually compelling in a 3-minute demo;
- success cannot be measured without recruiting a large user population.

## 13. Next autonomous phase

The next phase should be experimental rather than architectural:

1. Build a tiny local fixture dataset.
2. Test X1–X5 against current Gemini video capabilities.
3. Record raw outputs and timestamps.
4. Score against human-written ground truth.
5. Estimate model-call and media-token budget.
6. Search competitors specifically for whichever experiments succeed.
7. Kill weak phenomena.
8. Produce 3–5 product theses from surviving phenomena.
9. Only then freeze MVP scope.

No production architecture should be frozen before this gate.
