# Track A Case Data

Case data is organized as:

    data/
    └── cases/
        └── <case_id>/
            ├── manifest.json
            ├── source/
            ├── expected/
            └── metadata/

Use the shared rules in tracks/common/CASE-DATA-CONVENTIONS.md and tracks/common/MODEL-GATEWAY-CONVENTIONS.md.

No bounded domain is preselected. Do not create a fake real case just to populate this directory. Synthetic fixtures belong in fixtures/ and must be labeled accordingly.

For a shared implementation-ready case, `tracks/cases/<case_id>/manifest.json` is the entry point. Track-local `data/` is reserved for implementation-specific fixtures and metadata.