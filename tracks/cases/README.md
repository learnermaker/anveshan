# Capability Case Packs

\`tracks/cases/\` is the cross-track data layer for Anveshan capability cases.

A **case pack** is a bounded, versioned source/replay package that can be consumed by Track A and Track B without either track owning the case data. It is not a new contract layer.

## Stable case IDs

- \`micrometer\`
- \`kolam\`
- \`bicycle-repair\`
- \`handloom-weaving\`
- \`tabla\`
- \`origami\`
- \`square-knot\`

New cases should use a stable semantic slug. Do not encode UI labels, workspace names, model names, or ordinal numbers into the directory name.

## Pack structure

Each case follows the same layout:

~~~text
tracks/cases/<case-id>/
├── manifest.json
├── source/
│   └── README.md
├── knowledge/
│   └── knowledge_package.json
├── practice/
│   ├── rubric.json
│   └── practice_task.json
├── replay/
│   ├── baseline_attempt.json
│   ├── baseline_evaluation.json
│   ├── feedback.json
│   ├── retry_attempt.json
│   ├── retry_evaluation.json
│   └── transmission_record.json
└── media/
    └── README.md
~~~

### What belongs where

- **manifest.json** — stable case identity, capability archetype, workspace projection, source posture, and pack status.
- **source/** — source identity, provenance, consent/review/access notes, and source references.
- **knowledge/** — normalized case knowledge entering the common seam.
- **practice/** — case-specific task and deterministic rubric.
- **replay/** — deterministic baseline → evaluation → feedback → retry → evaluation → transmission evidence.
- **media/** — pointers/manifests for media objects. Large binaries do not belong in Git.

## Contract boundary

\`tracks/common/schemas/\` remains the sole authority for the eight shared contracts.

Case-pack JSON is **data**, not a parallel contract definition. Its payloads are expected to conform to the common seam. If a source arrives in another provider or legacy shape, normalization happens at an explicit adapter boundary before common-contract validation.

Do not add a ninth \`Workspace\` common contract.

## Runtime storage posture

For the current prototype, Git is sufficient for small, immutable JSON case/replay data.

For production-scale media:
- **Cloud Storage** should hold recordings, images, audio, derived artifacts, and large files.
- The case pack should retain stable IDs/references and provenance, not the media bytes.
- Object generation/version information should be preserved for evidence lineage.

For mutable runtime state:
- a document database such as **Firestore** is a better fit than putting sessions, learner attempts, lineage indexes, permissions, or live state into the case-pack files.
- case definitions should remain versioned content; runtime state should not mutate the Git case pack.

This deliberately separates **content** from **runtime state**.

## What is not a case pack

Do not put these here:
- React components or workspace layout code;
- Gemini model/provider code;
- common Pydantic schemas;
- global learner/session state;
- credentials or secrets;
- large media binaries;
- generic cross-case business logic.

See \`docs/architecture/case-packs.md\` for the architecture and migration boundary.
