# Research Infrastructure

This root-level `research/` directory contains **executable, reproducible research and evaluation infrastructure** used to test Anveshan's technical hypotheses and multimodal capabilities.

It is intentionally separate from `docs/research/`.

## What belongs here

- benchmark harnesses and evaluation scripts;
- deterministic scoring and normalization utilities;
- lightweight benchmark fixtures and annotations;
- versioned evaluation prompts;
- other executable research tooling that is part of the engineering workflow.

The current primary area is:

- `research/benchmarks/` — benchmark metadata, fixtures, prompts, results conventions, and deterministic scoring utilities.

## What does not belong here

Do not use this directory for:

- research notes, literature reviews, strategy, or exploratory prose;
- source/data catalogues that are documentation rather than executable tooling;
- product specifications or architecture decisions;
- production application code;
- large or redistributable media files unless explicitly approved and appropriately licensed.

Those belong in the appropriate `docs/`, application, or case-pack locations.

## Relationship to `docs/research/`

| Location | Purpose |
|---|---|
| `research/` | **Executable research infrastructure** — benchmarks, fixtures, scripts, scoring, and reproducible evaluation tooling |
| `docs/research/` | **Research documentation** — hypotheses, literature/evidence reviews, data-source analysis, experiment plans, and findings |

A benchmark result produced here is **engineering/research evidence**, not automatically a product-validation claim. Product claims require the validation population, rubric, provenance, and evidence standards defined elsewhere in the repository.

## Operating principles

1. Keep evaluation deterministic wherever practical.
2. Separate ground truth from model predictions.
3. Preserve evidence references and timestamps where the task requires them.
4. Treat `UNKNOWN` as a valid prediction when evidence is insufficient.
5. Check dataset/media licensing and redistribution constraints before committing assets.
6. Prefer lightweight metadata and fixtures in Git; keep large media out of the repository unless explicitly approved.
7. Do not promote benchmark results into product claims without the required validation evidence.

See `research/benchmarks/README.md` for the benchmark harness contract and `docs/research/` for the research documentation corpus.
