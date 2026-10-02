# AI / Agent Architecture — Anveshan

## 1. Principle

Agent count is not a product feature.

Anveshan should use agentic reasoning where multi-step judgment is useful and deterministic workflows where determinism is preferable.

## 2. Knowledge Agent

### Inputs

- audio
- video
- images
- documents
- transcripts
- metadata
- prior approved knowledge.

### Responsibilities

- understand source
- identify speakers
- identify objects
- identify actions
- extract claims
- extract steps
- identify conditions
- identify exceptions
- identify cues
- build candidate knowledge objects
- retrieve related knowledge
- update graph candidates.

### Outputs

- structured knowledge
- candidate graph nodes/edges
- source references
- confidence
- unresolved questions.

## 3. Evidence Agent

### Inputs

- question
- claim
- knowledge object
- source collection
- permissions.

### Responsibilities

- retrieve evidence
- locate timestamps
- rank evidence
- detect contradictions
- assess sufficiency
- distinguish direct evidence from inference
- generate grounded answers
- expose uncertainty.

### Outputs

- answer
- evidence references
- confidence
- uncertainty
- conflicts
- missing evidence.

## 4. Transmission Agent

### Inputs

- validated knowledge
- expert demonstrations
- learner profile
- learner history
- available tools/materials
- practice rubric.

### Responsibilities

- select teaching sequence
- explain
- demonstrate via source media
- generate practice task
- inspect learner attempt
- compare to reference
- identify deviations
- generate evidence-based feedback
- recommend retry
- evaluate improvement
- create transmission event.

### Outputs

- lesson
- practice task
- evaluation
- feedback
- improvement measure
- transmission record.

## 5. Conceptual Agent Universe

Future responsibilities may be separated into:

- Discovery Agent
- Interviewer Agent
- Knowledge Curator
- Evidence Agent
- Knowledge Scout
- Transmission Designer
- Learning Coach
- Verification Agent
- Lineage Agent
- Community Governance Agent
- Research Agent
- Matching Agent.

This is a conceptual decomposition, not an implementation requirement.

## 6. Agent Memory

Memory should be separated into:

- session state
- learner state
- knowledge state
- source evidence
- transmission history
- permissions.

A model should not be allowed to treat conversational memory as authoritative source truth.

## 7. Tool Boundaries

Agents may need tools for:

- source retrieval
- graph queries
- semantic search
- timestamp retrieval
- media inspection
- knowledge creation
- review creation
- lesson generation
- practice evaluation
- lineage update.

Tools must enforce permissions.

## 8. Agent Guardrails

Agents should:

- cite evidence
- preserve source/interpretation distinction
- expose uncertainty
- avoid unsupported claims
- avoid revealing restricted information
- avoid inventing people or statements
- request clarification when evidence is insufficient.

## 9. Evaluation

Evaluate agents on:

- extraction fidelity
- evidence grounding
- citation correctness
- contradiction handling
- feedback correctness
- learner improvement
- expert agreement.

## 10. Failure Modes

### Hallucinated claim

Response:
Reject or mark unsupported.

### Incorrect extraction

Response:
Route to expert review.

### Conflicting sources

Response:
Preserve both and explain uncertainty.

### Ambiguous learner video

Response:
Request another observation or mark uncertain.

### Permission failure

Response:
Do not retrieve or reveal restricted source.

## 11. MVP Agent Count

Prefer three logical components:

**Knowledge + Evidence + Transmission**

Only split further if testing demonstrates a concrete benefit.
