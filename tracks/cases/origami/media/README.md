# origami media

Large media is intentionally not committed to the case pack.

For the UI prototype, Stitch-generated Origami imagery may be used as **presentation assets** when the generated asset is actually supplied by the design workflow. Do not represent a Stitch-generated image as authentic expert evidence.

Keep asset references stable and distinguish:
- `ui_asset` — generated/presentation-only visual;
- `source_evidence` — evidence that supports a case claim;
- `replay_asset` — deterministic engineering fixture.

When a Stitch asset is checked into the app, reference it from the UI layer and record its origin/role in the case metadata. Prefer local app assets for deterministic rendering rather than remote transient URLs.

For future production media, resolve stable media/evidence IDs to Cloud Storage objects and preserve object generation/version information when media participates in evidence or lineage.
