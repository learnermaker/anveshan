# Track A Replay Case 001

Placeholder case for contract development.

## Required inputs

- source artifact ID;
- source modality;
- source metadata;
- bounded skill identifier;
- optional timestamped segments.

## Expected outputs

- `KnowledgePackage`;
- `EvidenceRef[]`;
- `PracticeTask`.

## Assertions

At minimum:

- every material claim has a provenance reference;
- observed and inferred content remain distinguishable;
- uncertainty is preserved;
- output matches the agreed contract names;
- no invented domain-specific facts are encoded in the fixture.

This case is intentionally domain-agnostic until M0 selects the bounded use case.
