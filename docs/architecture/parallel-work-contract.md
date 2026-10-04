# Parallel Work Contract

**Status:** DECIDED execution boundary  
**Scope:** Current MVP transmission wedge only

This document defines the smallest conceptual handoff between the two parallel development tracks. It does not prescribe a database schema, API protocol, framework, or deployment topology.

## Track A → Track B

Track A is responsible for producing a bounded, source-grounded teaching input:

`KnowledgePackage + EvidenceRef[] + PracticeTask`

Minimum invariants:

- source provenance is preserved;
- observed/source-backed content is distinguishable from inference;
- uncertainty is explicit;
- material claims can be traced to evidence;
- the practice task is bounded and tied to the knowledge package.

## Track B → integration

Track B is responsible for producing learner/transmission evidence:

`LearnerAttempt + Evaluation + Feedback + TransmissionRecord`

Minimum invariants:

- baseline and later attempts are distinguishable;
- evaluation uses explicit observable criteria;
- feedback is traceable to criteria/evidence;
- retry is represented explicitly;
- measured change is reproducible from recorded inputs;
- transmission lineage is preserved.

## Replay rule

Until integration, each track uses frozen fixtures at the boundary.

- Track A tests its outputs without Track B.
- Track B tests against a frozen Track A-compatible input without Track A.
- A fixture is evidence of contract/replay behavior, not evidence that the product hypothesis is validated.

## Integration rule

Integration joins the two tracks by replacing the frozen boundary fixtures with real expert and learner evidence.

Do not widen this seam merely to make integration convenient. A new shared object or cross-track dependency requires an explicit issue and, when architecturally material, a durable decision.

## Ownership

- Track A source code, prompts, tests, and fixtures live under `tracks/track-a/`.
- Track B source code, prompts, tests, and fixtures live under `tracks/track-b/`.
- Shared contracts, integration adapters, and cross-track tests belong outside the two ownership folders and require explicit assignment.

See `docs/status/NOW.md` for current execution gates and this document for the authoritative parallel ownership and handoff boundary.
