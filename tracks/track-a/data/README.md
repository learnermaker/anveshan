# Track A Case Data

Case data is organized as:

    data/
    └── cases/
        └── <case_id>/
            ├── manifest.yaml
            ├── source/
            ├── expected/
            └── metadata/

Use the shared rules in tracks/common/CASE-DATA-CONVENTIONS.md and tracks/common/MODEL-GATEWAY-CONVENTIONS.md.

No bounded domain is preselected. Do not create a fake real case just to populate this directory. Synthetic fixtures belong in fixtures/ and must be labeled accordingly.

For an implementation-ready case, manifest.yaml is the entry point and must identify source mode, runtime class, version, expected outputs, and replay expectations.