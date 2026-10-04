# Track B Case Data

Case data is organized as:

    data/
    └── cases/
        └── <case_id>/
            ├── manifest.yaml
            ├── attempts/
            ├── expected/
            └── metadata/

Use the shared rules in tracks/common/CASE-DATA-CONVENTIONS.md and tracks/common/MODEL-GATEWAY-CONVENTIONS.md.

Track B does not wait for Track A implementation. A case may begin with a frozen Track-A-compatible fixture and later replace it with authentic Track A outputs.

Do not create a fake real learner case. Synthetic/replay evidence must be labeled and must never be presented as real-world transmission validation.