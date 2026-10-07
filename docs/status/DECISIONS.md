# Durable Decisions

This file records decisions that materially affect scope, architecture, validation, or agent behavior.

## Decision format
- Date
- Decision
- Status
- Context
- Evidence
- Alternatives considered
- Consequences
- Revisit trigger

## 2026-10-03 — Multi-agent operating system
**Status:** DECIDED

**Decision:** The repository is the durable coordination system for human and coding-agent work. Implementation is issue-driven; PRs are bounded by issue contracts; current scope is explicitly separated from research; scope expansion requires an explicit trade-off; governance-critical material is code-owned and CI-checked.

**Context:** Multiple people and agents work concurrently, so chat context is not a durable source of truth.

**Consequences:** Agents must stop rather than infer authorization from adjacent code, research, or model capability.

**Revisit trigger:** The repository collaboration model changes materially.

## 2026-10-03 — Current product scope remains validation-first
**Status:** SUPERSEDED by 2026-10-04 active-development decision

**Decision:** The competition effort remains in research/product-definition/validation until the core product hypothesis is supported by recorded evidence.

**Context:** The exact domain, skill, expert, learner, and rubric remain open.

**Evidence:** docs/product/mvp-contract.md, docs/validation/, docs/product/open-questions.md.

**Consequences:** This decision governed the pre-implementation phase. It no longer blocks authorized implementation; its evidence/validation discipline remains applicable.

**Revisit trigger:** Superseded when M0 authorization moved the project into active development.

## 2026-10-04 — Active development with validation in parallel
**Status:** DECIDED

**Decision:** Anveshan is now in active development toward the M1 vertical slice. Implementation is authorized within bounded issues and the established architecture/ownership boundaries. Product validation continues in parallel; engineering implementation, replay fixtures, and prototypes must not be presented as authentic product validation.

**Context:** M0 capability-validation work established sufficient direction to begin implementation. The repository now contains the common contract seam, case-pack layer, frontend prototype, CI, and parallel Track A/Track B workspaces.

**Consequences:** Agents may implement authorized work without waiting for a separate validation gate to re-authorize each engineering task. Scope, evidence, provenance, replay-vs-authentic distinctions, and issue/PR governance remain mandatory.

**Revisit trigger:** Material change to the selected development direction, M1 completion, or a validation finding that changes product scope.

## 2026-10-03 — GitHub/agent operating standard
**Status:** DECIDED

**Decision:** Anveshan uses a low-ceremony, automation-first operating model for three concurrent people/agents. Root `AGENTS.md` is the cross-agent contract; `.github/copilot-instructions.md` supplies GitHub/Copilot-specific context; CI enforces machine-checkable repository and PR invariants; GitHub Free/private limitations are treated as hard constraints; paid-only branch protection, rulesets, required reviews, and native auto-merge are not dependencies.

**Operating path:** Issue → short-lived branch → implementation → PR → CI → merge. Agents make ordinary implementation decisions autonomously. Only product scope, material architecture/security/cost implications, ownership collisions, and unresolved cross-agent conflicts require human intervention.

**Context:** The repository is a hackathon project with three people working concurrently, mostly through coding agents. The objective is maximum parallelism with minimum coordination tax while preserving scope integrity, reproducibility, provenance, and integration safety.

**Revisit trigger:** Team size, GitHub plan, collaboration model, or product-development phase changes materially.

## 2026-10-03 — Parallel development uses a frozen contract seam
**Status:** DECIDED

**Decision:** When two developers work on the transmission MVP in parallel, split work into two independently testable proof surfaces: Track A — Expert Intelligence & Grounding; Track B — Practice, Evaluation & Transmission. The tracks must use a small, explicit contract seam and replay fixtures so either track can build and validate without waiting for the other's implementation. Integration occurs only after each track has independent proof.

**Context:** A product/platform split creates sequential dependencies disguised as parallel work. The team needs genuine parallel execution with minimal synchronization.

**Shared seam:** `KnowledgePackage`, `EvidenceRef`, `RubricDefinition`, `PracticeTask`, `LearnerAttempt`, `Evaluation`, `Feedback`, and `TransmissionRecord`. These names define the handoff concept; they do not authorize implementation of every object.

**Alternatives considered:** A sequential product/evidence track plus platform/engineering track; rejected because most work remained dependency-ordered. A broad shared-service architecture; rejected because it increases synchronization and prematurely commits architecture.

**Consequences:** Work ownership can remain disjoint. Fixture/replay tests become first-class validation seams. Real expert/learner evidence is an explicit integration concern rather than an implicit runtime dependency.

**Revisit trigger:** The bounded domain and actual implementation interfaces are selected, or the team size/work allocation changes materially.
## 2026-10-03 — Parallel track workspace ownership
**Status:** DECIDED

**Decision:** Implementation work for the current transmission wedge is organized into two disjoint workspaces: `tracks/track-a/` for Expert Intelligence & Grounding and `tracks/track-b/` for Practice, Evaluation & Transmission. Shared contracts, integration adapters, and cross-track tests stay outside both ownership folders and require explicit assignment.

**Context:** The team needs parallel execution without shared-file collisions or hidden runtime dependencies.

**Consequences:** An agent can start from either track using its local README, replay fixtures, and the shared contract document. Cross-track work is introduced only through explicit issues.

**Revisit trigger:** The bounded domain is selected and the implementation topology requires a material change in ownership boundaries.


## 2026-10-06 — Hero cases, evaluation core, and model choice
**Status:** DECIDED

**Decision:** Build three live hero cases: Kolam (final image only, goal-conditioned), Origami (demonstration video) and Tabla (audio; optional video not scored). Evaluation is Goal-Trajectory Verification (`docs/plans/evaluation-core.md`): a goal model derived from the source; learner trajectories checked for progress, constraint violations, first divergence and targeted change; scores come from deterministic bands only. Models: Gemma 4 26B (free) for text, images and video frames. Audio model calls are optional and off by default. Sources are licensed internet media and uploads.

**Context:** 12 days to submission. The team chose breadth across modalities with one deep evaluation core. No human recordings are required for the build.

**Alternatives considered:** human expert recordings (deferred: time and consent); a single deep case (rejected: weaker modality story); browser-side model calls (rejected: key exposure and dishonest labels).

**Consequences:** The other four cases become SYNTHETIC replay showcase only. The eight contracts are unchanged; new case-data sidecars (goal model, criterion map, observers) and the locator convention are added. Validation evidence is produced from held-out references and labelled synthetic perturbations; it is not claimed as human-learner validation.

**Revisit trigger:** real expert/learner recordings become available, or Gemma capabilities change.


## 2026-10-07 — Three product roles; end-user-centric surfaces
**Status:** DECIDED (Jim)

**Decision:** Anveshan serves three roles:
- **learner:** Library → Learn → Practise → Results in plain language, with no audit tooling;
- **creator:** create, check what the AI understood, publish with credit, licence and consent, see aggregate learner insights;
- **steward:** review queue, library curation and moderation, consent and licence ledger, insights, usage and cost.

Audit detail (claim ids, confidence, run class, lineage, approve/reject controls) appears only in the steward console and in `?debug=1`. Honesty labels stay visible to learners in plain words. The demo runs without accounts:
- creators are identified by the visitor cookie;
- stewards by a server-configured access code (`ANVESHAN_STEWARD_TOKEN`).

Runtime state is temporary on the demo server. Durable decisions are exported and committed.

**Context:** The learner path showed evaluation tooling ("Expert review · Approve, revise or reject claims"), which made the product read as an evaluation harness. The BRD already named knowledge owners and curators (§4.3–4.4) without a surface for them.

**Alternatives considered:**
- Hide the tooling behind a judge-only "inspect" mode: rejected, because judges are not users.
- Learner and creator only: rejected, because collective consent, quality and continuity need an accountable role.
- A full admin console with accounts and persistent storage: deferred to NEXT, because of the time and security cost and an ephemeral demo disk.

**Consequences:**
- Steward endpoints exist behind an access code.
- Learner outcomes are logged anonymously (no names, no media) for insights.
- Universal-path robustness (technical-panel plan WS6) moves to NEXT as the scope trade.

Spec: `docs/kiro/specs/K9-ORCHESTRATOR.md`.

**Revisit trigger:** accounts and persistent storage are introduced, or real communities or organisations pilot the steward role.


## 2026-10-07 — Positioning: skills of the physical world

**Decision:** Anveshan is described, in the app and in the key documents, as made for skills of the physical world (hands, tools, materials, sound), learned from a real demonstration and checked against a photo, video or recording of the learner's real attempt. Decided by Jim.

**Single statement:** [`docs/product/novelty-boundary.md`, "Skills of the physical world"](../product/novelty-boundary.md#skills-of-the-physical-world-positioning-decided-2026-10-07). The app adapts it in `PITCH` (`app/src/copy/plain.ts`).

**Consequences:** no "nobody does this" claims (industrial "Physical AI" tools exist); the app asks for attempts in real-world terms and says what a camera or microphone cannot sense.

**Revisit trigger:** a learner or expert study shows the physical-world framing does not match how people use the product.
