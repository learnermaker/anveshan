# Knowledge Model — Anveshan

## 1. Purpose

Define the conceptual data model behind the Multimodal Knowledge Transmission Graph.

The model is intentionally domain-agnostic but must support the first bounded MVP skill.

## 2. Core Entity Types

### Person

Represents an expert, learner, contributor, teacher, student, curator, or other participant.

Potential attributes:

- identity
- display name
- role
- language
- location
- community
- consent
- access policy.

### Community

Represents a family, cultural group, professional group, village, organization, or other knowledge-owning context.

### Skill

A capability that can be learned or demonstrated.

### Practice

A way of performing a skill in a specific context.

### Technique

A specific method or action within a practice.

### Knowledge Claim

A proposition extracted from source material.

### Evidence

Material supporting or contradicting a claim.

### Recording

Original audio/video source.

### Artifact

Physical or digital object relevant to the knowledge.

### Document

Original textual or scanned source.

### Place

Geographic or contextual location.

### Event

An occurrence associated with knowledge, transmission, or history.

### Lesson

A derived teaching representation.

### Practice Task

A concrete activity assigned to a learner.

### Attempt

A learner's performance evidence.

### Feedback

Evaluation produced by an expert, community, deterministic rubric, or AI-assisted process.

### Transmission

A knowledge transfer event from source person/practice to learner.

### Variant

A contextually different form of a practice or technique.

### Version

A temporal state of a knowledge representation.

### Permission

Rules controlling access and use.

### Consent Record

Record of contributor agreement and scope.

### Review

Human/community validation of a derived representation.

## 3. Core Relationships

- Person **knows** Skill.
- Person **demonstrates** Technique.
- Person **practices** Practice.
- Practice **contains** Technique.
- Practice **has variant** Variant.
- Variant **is version of** Practice.
- Recording **contains** Claim.
- Recording **demonstrates** Technique.
- Claim **supported by** Evidence.
- Claim **contradicted by** Evidence.
- Claim **interpreted as** Structured Knowledge.
- Person **contributed** Recording.
- Community **governs** Knowledge.
- Learner **learns from** Expert.
- Learner **attempts** Skill.
- Attempt **evaluated against** Demonstration or Rubric.
- Feedback **references** Evidence.
- Attempt **improves after** Feedback.
- Transmission **connects** Expert and Learner.
- Transmission **transmits** Knowledge.
- Transmission **produces** Adaptation.
- Adaptation **becomes variant of** Practice.
- Learner **becomes transmitter to** another Learner.

## 4. Evidence Model

Every important claim should be able to point to:

- source ID
- source type
- timestamp
- speaker
- language
- location
- date
- context
- evidence excerpt
- modality
- verification state.

## 5. Knowledge State

A knowledge claim can have:

- direct-source state
- demonstrated state
- observed state
- AI-inferred state
- corroborated state
- disputed state
- unverified state
- unknown state.

## 6. Lineage

A lineage edge should ideally answer:

- who originated it?
- who learned it?
- who taught it?
- what evidence supports it?
- what changed?
- who changed it?
- why?
- when?
- under what conditions?
- who learned the new version?

## 7. Transmission Record

Minimum fields:

- transmission ID
- expert
- learner
- knowledge/practice
- source evidence
- lesson
- practice task
- baseline
- attempt
- feedback
- retry
- outcome
- expert review
- learner improvement
- adaptation
- timestamp.

## 8. Knowledge Graph Examples

Example:

**Person A → demonstrates → Technique X**

**Recording R → contains → Claim C**

**Claim C → supported by → Timestamp T in Recording R**

**Learner B → learns from → Person A**

**Learner B → attempts → Skill S**

**Attempt A → evaluated against → Technique X**

**Feedback F → references → Evidence E**

**Learner B → adapts → Practice P**

**Adaptation P2 → variant of → Practice P**

**Learner C → learns from → Learner B**

This creates an actual transmission lineage rather than a static archive.

## 9. Permissions

Permissions may attach to:

- person
- community
- recording
- claim
- practice
- evidence
- lesson
- learner access
- generated representation.

Permissions should be inherited carefully and evaluated before retrieval.

## 10. Data Modeling Principle

Do not collapse source and derived data into one mutable record.

Prefer:

**immutable/source evidence + derived knowledge + review state + lineage**

This allows correction without rewriting history.
