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


## Architectural assessment

This is the preferred architecture for the current prototype and is intentionally **not** described as a universal final infrastructure design.

### Why this boundary is the right one now

The central problem at the seven-case stage is separation of **case content** from **track implementation**. A database does not solve that problem; a canonical case-pack does.

The design optimizes for four properties:

1. **Single ownership** — one canonical case definition is shared by Track A and Track B.
2. **Stable identity** — semantic `case_id` values survive UI, provider, and workspace changes.
3. **Deterministic replay** — small structured fixtures can be versioned and validated in Git.
4. **Clean production migration** — large media and mutable runtime state can move to dedicated systems later without changing the common contract seam.

### When a database becomes justified

Introduce a runtime database only when one or more of these requirements becomes real:

- concurrent learner/session writes;
- persistent attempts and evaluations across devices/sessions;
- authenticated per-user authorization;
- queries across many cases/learners/attempts;
- mutable publication/version pointers;
- operational lineage indexes that cannot be rebuilt efficiently from content artifacts;
- transactional runtime updates.

At that point, **do not migrate the case-pack itself into the database wholesale**. Keep versioned case content in an authoring/content layer, store media in object storage, and persist mutable runtime state separately.

### Future split

The intended evolution is:

```text
                 VERSIONED CONTENT
Git case packs ──────────────────────────┐
  manifest / knowledge / rubric / task   │
                                          │
                 LARGE MEDIA              │
Cloud Storage ────────────────────────────┤
  video / audio / images / artifacts      │
                                          v
                                  application adapters
                                          │
                 RUNTIME STATE             │
Firestore or equivalent ──────────────────┘
  sessions / attempts / evaluations /
  feedback / transmission / lineage
```

The three layers may be introduced independently. This avoids both premature infrastructure and an expensive data-model rewrite later.

### Non-goals

The case-pack layer is not:

- a database;
- an event store;
- a general CMS;
- a replacement for the eight common contracts;
- a place for React/UI configuration that is merely presentation-specific;
- a place for live learner state.

### Case-count scaling

Seven, seventy, or several hundred cases should still use the same semantic directory/index pattern. At higher scale, the likely change is **storage/serving strategy**, not the conceptual ownership model: case packs can be published from Git/object storage and indexed for retrieval without redefining the case semantics.
