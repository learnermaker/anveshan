# Track A — Implementation Readiness Checklist

Use this as the coding-agent gate. It complements SUCCESS-CRITERIA.md.

## Before implementation
- [ ] Read the common seam and validator.
- [ ] Confirm the bounded domain/skill is authorized; otherwise remain domain-agnostic.
- [ ] Identify EvidenceRef, KnowledgePackage, RubricDefinition, and PracticeTask as Track A outputs.
- [ ] Keep learner evaluation, retry orchestration, transmission gain, and UI implementation outside Track A.
- [ ] Define fixtures and expected evidence/uncertainty before live Gemini work.
- [ ] Define whether each fixture is LIVE, REPLAY, SYNTHETIC, or ILLUSTRATIVE.

## Prototype-aware readiness
- [ ] Source mode is explicit: FORWARD, GOAL_CONDITIONED, or CORRECTIVE.
- [ ] Target-first outputs distinguish visible target facts from inferred candidate procedures.
- [ ] OBSERVED / INFERRED / UNVERIFIED semantics are preserved through normalization.
- [ ] Replay/fixture outputs are never represented as live Gemini or real-world validation.
- [ ] Any workspace-composition information is exposed through downstream adapters, not common-contract changes.

## During implementation
- [ ] Keep model/provider DTOs behind a normalization adapter.
- [ ] Preserve source identity, provenance, evidence locators, observation state, uncertainty, and review state.
- [ ] Never fabricate missing evidence to satisfy schema completeness.
- [ ] Keep reusable infrastructure independent of profession, tool, modality, and vocabulary.
- [ ] Keep UI projections downstream and replaceable.
- [ ] Add deterministic negative tests before claiming happy-path completion.

## Integration gate
- [ ] Common contracts validate.
- [ ] Track-local replay passes without live Gemini.
- [ ] Expert review state is explicit for authentic validation.
- [ ] Material claims are evidence-grounded.
- [ ] PracticeTask is bounded and rubric-linked.
- [ ] Track B can consume outputs without importing Track A internals.
- [ ] Handoff packet contains replay instructions and expected results.

## Stop conditions
Stop if success requires changing a frozen contract, inventing source facts, coupling to the UI, selecting a domain without authorization, or adding unrelated platform infrastructure.

## Operational readiness

- [ ] Read `tracks/common/CASE-DATA-CONVENTIONS.md` and `tracks/common/MODEL-GATEWAY-CONVENTIONS.md`.
- [ ] Case has a stable `case_id`, explicit version, source mode, runtime class, and status.
- [ ] Case-local artifacts are under `data/cases/<case_id>/` and are discoverable from `manifest.yaml`.
- [ ] Materially changed source, rubric, prompt/model configuration, or normalized knowledge is versioned rather than silently overwritten.
- [ ] Model-backed runs retain model/configuration, prompt version, input fixture, run ID, and runtime class.
- [ ] Missing/ambiguous/unsupported evidence uses the shared failure taxonomy and escalates to human review where required.
- [ ] Replay command and expected result are documented in the case metadata.
