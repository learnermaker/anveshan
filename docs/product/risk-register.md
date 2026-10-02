# Product & Technical Risk Register

**Review date:** 2026-10-03

| Risk | Likelihood | Impact | Mitigation | Release Gate |
|---|---|---|---|---|
| AI misrepresents expert practice | High | Critical | Expert review; source links; direct-source display | Must pass expert fidelity test |
| Video model misses fine-grained action | High | High | Bounded task; explicit rubric; multiple views where possible; uncertainty | Must identify selected observable criteria |
| Feedback is generic | High | Critical | Evidence-linked comparison; rubric-first evaluation | Expert must judge feedback actionable |
| Skill assessment is overconfident | Medium | Critical | Confidence/uncertainty; human review for ambiguous cases | No unsupported competency claims |
| Existing competitor already does MVP | Medium | Critical | Competitive falsification test | Reposition or pivot if reproduced |
| Community knowledge is extracted without authority | Medium | Critical | Consent; permissions; contributor/community review | Governance required before publication |
| Learner improvement is not measurable | Medium | Critical | Select skill with observable rubric before build | Must define baseline and retry |
| Demo depends on live model behavior | High | High | Pre-cached source; deterministic fallback; recorded backup | Full demo rehearsal |
| Latency makes interaction unusable | Medium | High | Precompute ingestion; async processing; cache retrieval | Core demo path must complete predictably |
| Cloud/API availability changes | Medium | High | Verify current APIs; isolate provider adapters | Deployment smoke test |
| Agent complexity obscures system behavior | Medium | Medium | Three logical responsibilities; trace evaluation | Every agent must have a measurable job |
| Privacy/access leak | Low/Medium | Critical | Permission checks before retrieval and generation | Security test before submission |
| Translation changes meaning | Medium | High | Preserve original; show translation as derived | Expert review for important content |
| Cultural variant flattened | Medium | High | Version/variant model; disagreement preservation | No silent merge |
| Product becomes too broad | High | High | MVP contract | Features outside contract are deferred |

## Highest-Risk Unknowns

1. authentic expert/learner access;
2. selected skill;
3. learner evaluation reliability;
4. evidence grounding quality;
5. competitive overlap;
6. community governance requirements.

These must be resolved before feature expansion.
