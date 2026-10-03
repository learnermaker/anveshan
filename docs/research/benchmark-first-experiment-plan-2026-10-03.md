# Anveshan — Benchmark-First Experiment Plan
## 2026-10-03

## Objective

Before selecting a product, establish whether current Gemini multimodal reasoning can reliably recover **state → action → outcome** structure from procedural video.

The experiment should minimize new data collection and maximize reproducibility.

## 1. Benchmark sources

### Primary: Ego-Exo4D

Ego-Exo4D V2 currently contains 1,286.30 video hours across 5,035 takes, with physical and procedural activities including cooking, bike repair, and health, plus synchronized ego/exo views and extensive annotations. It provides keysteps, atomic action descriptions, expert commentary, and proficiency information. citeturn0search1turn0search10turn0search6turn0search8

For the first experiment, do **not** download the full video corpus.

Use metadata and annotations to select a small set of takes.

Candidate task types:
- bike repair;
- cooking;
- health/procedural tasks;
- other activities with clear ordered keysteps.

Prioritize tasks where:
- actions are visually observable;
- objects are visible;
- success/failure or quality differences are annotated;
- there are multiple takes of the same task.

### Secondary: ProSkill

ProSkill is specifically designed for action-level skill assessment in procedural tasks and includes both absolute and pairwise skill annotations. Its authors report that current state-of-the-art methods achieve suboptimal results, highlighting the difficulty of procedural skill assessment. citeturn0search47turn0search2

Use ProSkill later to test whether a successful state/action representation actually supports skill assessment.

## 2. Dataset selection algorithm

Do not choose examples manually because they "look good."

Select a task family satisfying:

1. >= 5 takes of the same task.
2. >= 3 distinct proficiency levels or clearly differentiated outcomes.
3. >= 4 annotated keysteps.
4. >= 5 atomic action descriptions per take.
5. expert commentary available for at least some takes.
6. video duration <= 10 minutes where possible.
7. no dependency on audio for the ground truth.
8. enough visual observability for an external evaluator.

Then sample:
- 2 high-quality/reference takes;
- 2 intermediate takes;
- 2 lower-quality takes.

## 3. Ground-truth object

For each take create:

```
Take
  task
  participant
  proficiency
  keysteps[]
  atomic_actions[]
  expert_comments[]
  improvement_tips[]
```

For each keystep:

```
Keystep
  start_time
  end_time
  step_name
  step_description
```

For each atomic action:

```
Action
  timestamp
  text
  subject
  best_view
```

For each expert observation:

```
ExpertObservation
  timestamp
  comment
  rating/category
  optional_spatial_grounding
```

This gives us a deterministic reference representation before the model sees the data.

## 4. Experiment A — State/action extraction

Prompt the model to produce structured events:

```json
{
  "events": [
    {
      "timestamp": 0,
      "state_before": "...",
      "action": "...",
      "state_after": "...",
      "evidence": "...",
      "confidence": 0.0
    }
  ]
}
```

Important:
- confidence is not ground truth;
- every claim must carry a timestamp;
- the model must be allowed to return UNKNOWN.

Score:
- timestamp error;
- action overlap;
- state description agreement;
- evidence validity;
- unsupported-claim rate.

## 5. Experiment B — Keystep recovery

Give the model the task goal and video.

Ask:

> Identify each required keystep, its start/end time, the observed action, and whether the step appears successfully completed. Return UNKNOWN when visual evidence is insufficient.

Compare with Ego-Exo4D keystep annotations.

Score:
- keystep detection precision/recall;
- temporal IoU;
- completion classification;
- evidence validity.

This is a strong first test because the benchmark already defines the expected procedural segmentation. citeturn0search10

## 6. Experiment C — Expert-commentary grounding

For each expert commentary timestamp:

Ask the model:

> What event in the video is the expert reacting to at this timestamp? Give the observable evidence only. Separate observation from interpretation.

Compare:
- timestamp;
- action;
- object;
- error/improvement concept.

The expert commentary dataset contains time-indexed retrospective commentary and, in some cases, spatial drawings that ground the expert's observations. citeturn0search8

This experiment tests whether the model can reconstruct the **evidence behind expertise**, rather than merely summarize a video.

## 7. Experiment D — Improvement-tip verification

For an expert improvement tip:

1. identify the relevant moment;
2. state the observable issue;
3. identify the recommended improvement;
4. determine whether the evidence supports the tip.

The model must explicitly distinguish:

- OBSERVED
- INFERRED
- NOT VISIBLE

This prevents the system from turning expert interpretation into fabricated visual facts.

## 8. Experiment E — Reference vs attempt

Choose two takes of the same task.

Provide:
- reference video;
- attempt video;
- task goal.

Ask:

> Identify the first material procedural difference between the two executions. Give timestamps in both videos and explain only what can be directly observed.

Ground truth can be constructed from:
- keystep differences;
- atomic actions;
- expert tips;
- proficiency annotations.

This is the closest existing benchmark approximation to the **First Divergence** hypothesis.

## 9. Experiment F — Recovery

Search the benchmark for examples where:
- a problematic action occurs;
- later actions restore the process.

If explicit recovery labels are unavailable, do not manufacture them.

Instead:
- construct a small human-annotated recovery fixture from a few licensed/public examples;
- keep the fixture tiny;
- record the human ground truth separately.

Question:

> Which action appears associated with the transition from the problematic state to the recovered state?

The model must not claim causality unless the evidence supports it.

## 10. Model ladder

Run experiments in this order.

### M1 — Current free/eligible Flash model

Purpose:
- cheapest broad feasibility check.

### M2 — Stronger current Flash model with agentic video understanding

Gemini's current video documentation says static processing samples at 1 FPS, while supported recent Flash models can dynamically navigate the timeline, selectively inspect transcripts, and adapt frame rates/resolution. Google reports up to 88% token savings and roughly 7% quality improvement on long-form content for agentic processing. citeturn0search13

Purpose:
- determine whether temporal reasoning quality materially changes.

### M3 — Gemini Robotics ER 2 preview

Use only on the smallest subset.

Google describes ER 2 as supporting spatial reasoning, video moment finding, progress classification, success detection, instrument reading, and multi-step tool use. citeturn0search3turn0search4

Purpose:
- determine whether embodied reasoning materially improves the state/action/outcome task.

Do not make this model a product dependency during exploration.

## 11. Evaluation table

For every experiment/model:

| Metric | Definition |
|---|---|
| Temporal MAE | absolute timestamp error |
| Temporal IoU | overlap between predicted and ground-truth interval |
| Action accuracy | normalized action match |
| State accuracy | state category match |
| Evidence validity | percentage of claims supported by cited video moment |
| Unsupported claim rate | claims without adequate evidence |
| UNKNOWN precision | whether uncertainty is correctly used |
| Completion accuracy | correct step completion state |
| Expert agreement | agreement with independent human annotation |
| Cost per case | actual API usage |
| Latency | wall-clock response time |

## 12. Minimum statistical discipline

Do not call a model "good" from 3 examples.

Use:
- pilot: 6 cases;
- promising direction: 20–30 cases;
- serious claim: 50+ cases or a public benchmark metric.

Report:
- n;
- task distribution;
- model/version;
- prompt version;
- evaluation rubric;
- automated vs human evaluation;
- confidence intervals where meaningful.

## 13. What would constitute a breakthrough signal?

A breakthrough signal is **not**:

> "The model gave a convincing explanation."

It is:

> "Across held-out procedural examples, the model reliably localizes and explains the same state/action transitions that independent annotations identify, while exposing uncertainty when the evidence is insufficient."

A particularly strong result would be:

- good temporal localization;
- good evidence grounding;
- good reference-vs-attempt comparison;
- correct use of UNKNOWN;
- low unsupported-claim rate;
- reproducibility across tasks.

## 14. Product consequences

### If A/B/C succeed
The platform can plausibly become a **procedural intelligence engine**.

Potential products:
- First Divergence;
- expert demonstration compiler;
- skill transfer;
- procedural QA.

### If D succeeds but A/B are weak
Focus on expert-grounded coaching/evaluation rather than autonomous state modeling.

### If E succeeds strongly
The strongest product may be comparative process intelligence rather than apprenticeship.

### If F succeeds
Recovery intelligence becomes a distinct product thesis.

### If only M3 succeeds
Keep Robotics ER as an optional research feature and avoid making the entire product preview-dependent.

### If no model succeeds
Kill the state-transition thesis.

## 15. Dataset/licensing discipline

The first prototype should use:
- self-recorded footage for the public demo;
- benchmark datasets for private/research evaluation where their licenses permit;
- no benchmark footage in the final demo unless the license and submission terms clearly permit it.

Ego-Exo4D requires a license agreement for downloads, and its video corpus is extremely large; the project explicitly provides smaller metadata/annotation partitions, so experimenters should not pull the full corpus merely to test the hypothesis. citeturn0search14

## 16. Immediate next implementation

Create a local `research/benchmarks/` harness with:

```
benchmarks/
  egoexo/
    metadata/
    annotations/
    selected_cases.json
  fixtures/
    case_001/
      ground_truth.json
      notes.md
  prompts/
    state_action_v1.txt
    keystep_v1.txt
    divergence_v1.txt
    commentary_v1.txt
  results/
    .gitkeep

scripts/
  select_cases.py
  normalize_annotations.py
  score_temporal.py
  score_events.py
  summarize_runs.py
```

Do not download video automatically.

The harness should accept local media paths or signed/local URLs and keep the evaluation data separate from application code.

## 17. Final decision gate

After the benchmark pilot, create:

`docs/research/validated-theses-2026-10-XX.md`

with only:

- validated technical phenomenon;
- evidence;
- failed hypotheses;
- 3–5 product theses;
- recommended next experiment.

Until that file exists, Anveshan remains in exploration mode.
