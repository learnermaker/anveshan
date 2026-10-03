# Anveshan Diagrams

Two canonical diagrams are maintained as Mermaid source so humans can read them and agents can parse them.

## Files

- `TX-01-transmission-evidence-loop.mmd` — bounded MVP proof: expert evidence → grounded teaching → learner practice → rubric-based verification → measured improvement → transmission lineage.
- `AR-01-system-knowledge-architecture.mmd` — indicative system context, logical AI responsibilities, data/provenance boundaries, knowledge-object shape, Google Cloud mapping, roadmap, and long-term vision.

## Source of truth

These diagrams summarize canonical product and architecture documents. They do not define new scope.

- Product: `docs/product/mvp-contract.md`, `docs/product/product-vision.md`
- Architecture: `docs/architecture/system-design.md`, `docs/architecture/knowledge-model.md`, `docs/architecture/ai-agent-architecture.md`, `docs/architecture/data-flow.md`
- Validation: `docs/validation/metrics.md`

## Maintenance

Update the relevant `.mmd` in the same issue/PR when the canonical documents materially change.

GitHub renders Mermaid files directly, making the source useful without a separate renderer. Presentation HTML is a view over these sources; Mermaid source remains authoritative.
