# origami media

Large media is intentionally not committed to the case pack.

For the UI prototype, Stitch-generated Origami imagery may be used as **presentation assets** when the generated asset is actually supplied by the design workflow. Do not represent a Stitch-generated image as authentic expert evidence.

Keep asset references stable and distinguish:
- `ui_asset` — generated/presentation-only visual;
- `source_evidence` — evidence that supports a case claim;
- `replay_asset` — deterministic engineering fixture.

When a Stitch asset is checked into the app, reference it from the UI layer and record its origin/role in the case metadata. Prefer local app assets for deterministic rendering rather than remote transient URLs.

For future production media, resolve stable media/evidence IDs to Cloud Storage objects and preserve object generation/version information when media participates in evidence or lineage.
## Current external source

The case currently catalogs the Wikimedia Commons demonstration `File:OrigamiCrane.ogv` as `source_evidence` under `src-origami-tavin-2010`.

- Source page: https://commons.wikimedia.org/wiki/File:OrigamiCrane.ogv
- License: CC BY 3.0
- Runtime: 5 min 35 s
- Original dimensions: 400 × 226

Do not commit the full source video to Git. The app may use an external source reference or a compliant lightweight local derivative/poster, but CI and screenshot audits must not depend on network media.