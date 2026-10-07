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
│   └── README.md
├── practice/
│   └── README.md
├── replay/
│   └── bundle.json
└── media/
    └── README.md
~~~

### What belongs where

- **manifest.json** — stable case identity, capability archetype, workspace projection, source posture, and pack status.
- **source/** — source identity, provenance, consent/review/access notes, and source references.
- **knowledge/** — case knowledge authoring boundary. The current prototype keeps it co-located in the replay bundle; it can be promoted to its own JSON artifact when independently authored.
- **practice/** — case-specific task and deterministic rubric authoring boundary. The current prototype keeps them co-located in the replay bundle.
- **replay/** — the current atomic deterministic bundle containing knowledge, practice, baseline/retry attempts, evaluations, feedback, and transmission record.
- **media/** — pointers/manifests for media objects. Large binaries do not belong in Git. Use stable media/evidence IDs and resolve them to local replay assets during prototype execution or to Cloud Storage objects in a deployed runtime; preserve object generation/version information when media participates in evidence or lineage.

Each folder's `README.md` states only what is specific to that case (for `source/`, its source posture) and links back here. Do not infer authenticity from the existence of a pack: replay data is engineering scaffolding and must remain visibly distinguished from live or authentic expert evidence. Knowledge, practice tasks and rubrics are case-specific data that must stay compatible with the frozen common contracts; they are not new shared contracts.

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


## Scaling rule

Do not create `case-008`, `case-009`, or other ordinal directory names. Add a stable semantic slug under `tracks/cases/` and register it in `index.json`.

Do not duplicate the same canonical case content under `tracks/track-a/` and `tracks/track-b/`. Track-local `data/` is reserved for implementation-specific artifacts.

For production, keep this ownership model even when storage changes: versioned case content, large media, and mutable runtime state are separate concerns.


## Manifest authority

Each `tracks/cases/<case-id>/manifest.json` must conform to `tracks/cases/manifest.schema.json`. The schema is the authoritative vocabulary for case-pack metadata; prose documentation must not introduce new enum values.

The manifest schema is intentionally separate from the eight shared contracts under `tracks/common/schemas/`. It governs case-pack metadata only.

### Local validation

Run:

```bash
python .github/scripts/check_case_packs.py
python -m pytest .github/scripts/test_check_case_packs.py
```

A replay bundle is deterministic engineering evidence. It must not be labeled as authentic expert validation merely because an external reference or source is catalogued alongside it.
