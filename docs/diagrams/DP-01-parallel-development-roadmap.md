# DP-01 — Parallel Development Roadmap

## Objective

Two developers/agents can build and validate independently, with explicit contracts and only a small number of integration gates.

## Work split

### Part A — Product / Evidence Vertical

Own the user-visible knowledge transmission proof:

A1 source capture → A2 knowledge extraction → A3 evidence grounding → A4 teaching → A5 learner observation → A6 criterion-level evaluation/feedback → A7 transmission proof.

Primary evidence outputs:
- authentic source fixture;
- structured knowledge;
- source-linked claims;
- learner baseline/attempt artifacts;
- rubric observations;
- feedback;
- retry and measured change;
- transmission record + lineage.

### Part B — Platform / Engineering Vertical

Own the reusable execution substrate:

B1 app shell/UX contracts → B2 model gateway + replay → B3 data contracts → B4 deterministic permissions/state/audit → B5 evaluation harness → B6 Cloud Run/storage/observability → B7 reliability/reproducibility hardening.

Primary engineering outputs:
- stable interfaces between UI, agents, and data;
- replayable model boundary;
- deterministic state/permission/evaluation behavior;
- test fixtures and scorers;
- deployable prototype;
- failure-path handling.

## Shared contracts

Part A and Part B may proceed in parallel, but they must agree on:
- source/evidence identifiers;
- knowledge-object schema;
- learner-attempt schema;
- rubric/evaluation schema;
- transmission record schema;
- model gateway interface;
- provenance/uncertainty semantics.

Do not solve the same contract in both branches.

## Integration gates

**G1 — End-to-end:** one authentic transmission works.

**G2 — Independent validation:** expert review, baseline/retry comparison, adversarial evidence-grounding checks.

**G3 — Demo readiness:** replayable path, visible evidence, understandable AI contribution.

**G4 — Submission:** working prototype plus required documentation/media/deck.

Failure should send work back only to the branch responsible for the failing contract or evidence. Avoid broad rewrites.

## GitHub execution

Recommended issues:
- one parent issue for DP-01 if needed;
- one issue per bounded A/B work item;
- each agent owns disjoint files/modules;
- each issue produces one PR;
- PRs merge independently when their contract/evidence is satisfied;
- integration PRs should touch shared contracts only when required.

This is intentionally a development map, not a new product scope decision.
