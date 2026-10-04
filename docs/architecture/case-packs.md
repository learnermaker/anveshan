# Capability Case-Pack Architecture

**Status:** CURRENT / bounded prototype architecture

## Decision

Anveshan uses \`tracks/cases/\` as the versioned, cross-track source-data boundary for bounded capability cases.

The case pack is intentionally different from the shared contract seam:

~~~text
Case pack
  source + knowledge + practice + replay + provenance
                  |
                  v
        normalization / validation
                  |
                  v
tracks/common/schemas/   <-- eight frozen contracts
                  |
          Track A / Track B
                  |
                  v
          app / runtime UI
~~~

The case pack describes **what this case contains**. The common seam describes **what must cross the Track A → Track B boundary**.

## Why a case-pack layer

The seven current cases are capability archetypes, not seven independent architectures. A shared directory gives every future case the same predictable structure while allowing domain-specific source material and criteria.

The alternative—keeping all case data inside \`app/src/data/cases/registry.ts\`—couples source data to presentation code and makes it difficult to reuse the same case from Track A, Track B, experiments, validators, or future backend services.

## Stable identity

Use stable semantic case IDs:

- \`micrometer\`
- \`kolam\`
- \`bicycle-repair\`
- \`handloom-weaving\`
- \`tabla\`
- \`origami\`
- \`square-knot\`

The ID should survive changes to display title, workspace composition, model provider, and UI language.

## Data lifecycle

1. **Source** — original/owned/research/reference material and provenance posture.
2. **Understand** — extracted claims, observations, cues, and uncertainty.
3. **Ground** — evidence references and review state.
4. **Transmit** — task/rubric/replay material.
5. **Practice** — learner attempt and evaluation.
6. **Verify** — deterministic/common-contract validation.
7. **Evolve** — transmission record and lineage.

The pack may contain replay/synthetic data, but every pack must state its epistemic posture. Replay is not authentic expert validation.

## Git vs database

### Use Git case packs for

- versioned case definitions;
- small structured knowledge objects;
- rubrics and practice tasks;
- deterministic replay fixtures;
- provenance/access documentation;
- benchmark fixtures.

### Use Cloud Storage for

- source video/audio/images;
- learner-uploaded media;
- large derived artifacts;
- immutable evidence objects.

Cloud Storage objects are immutable for their storage lifetime and have generation identifiers, which is useful for evidence/provenance references.

### Use Firestore later for

- learner/session state;
- attempts created at runtime;
- evaluations and feedback generated at runtime;
- transmission records when they become live application state;
- lineage indexes and retrieval metadata;
- permissions/access state;
- mutable case publication/version pointers.

Firestore is a document database suited to collections of small documents, hierarchical subcollections, and transactional updates. It fits runtime state better than treating the Git case pack as a mutable database.

### Do not add a database yet

For the current seven-case prototype, a database would add infrastructure without solving the primary problem. The immediate problem is **organization and ownership of case data**, not high-volume mutable state.

## Future production shape

~~~text
Git / case authoring
  |
  +--> case manifest + structured definitions
  |
  +--> Cloud Storage
  |      source media / artifacts / immutable evidence
  |
  +--> publication pipeline
           |
           v
       Firestore
         runtime state
         learner attempts
         lineage indexes
         access/publication metadata
           |
           v
        application
~~~

The exact database choice remains an implementation decision until runtime persistence requirements are validated.

## Migration rule

The UI registry is a downstream projection during this bounded migration. Do not introduce a second contract vocabulary to make the migration easier.

When the case-pack loader is introduced, the registry should consume pack data rather than re-author it. Until then, any UI-only fields may remain in the registry, but case payloads must not silently diverge from the pack.
