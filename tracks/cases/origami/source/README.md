# Origami source

## Canonical external demonstration source

**Role:** `source_evidence`

- **Title:** OrigamiCrane.ogv
- **Creator:** Tavin
- **Description:** Folding of an origami paper crane
- **Original date:** 2010-07-09
- **Source page:** https://commons.wikimedia.org/wiki/File:OrigamiCrane.ogv
- **Original media:** Ogg/Theora/Vorbis video
- **Runtime:** 5 min 35 s
- **Dimensions:** 400 × 226
- **License:** Creative Commons Attribution 3.0 Unported (CC BY 3.0)
- **Attribution:** Credit Tavin, link to the CC BY 3.0 license, and identify changes if the media is adapted.

The source page identifies the work as the uploader's own work and provides the CC BY 3.0 license.

## Anveshan evidence boundary

This external video is a real demonstration source for the Origami capability. It does **not** turn the existing `replay/bundle.json` into authentic expert/learner validation.

Keep these roles distinct:

- external demonstration video = `source_evidence`;
- current replay bundle = deterministic engineering fixture;
- Stitch-generated imagery = `ui_asset` / presentation-only visual.

Do not relabel synthetic replay identities, scores, timestamps, or evaluations as authentic human evidence.

## Stable source IDs

Use stable IDs when wiring the source into adapters or UI:

- `src-origami-tavin-2010` — external demonstration source
- `ev-origami-demo` — whole-video source evidence
- `ev-origami-step-XX` — derived/keyframe evidence, only after actual frame/segment inspection

Do not fabricate source timestamps. Any step-level evidence must come from an actually inspected segment or frame of the external video.

## Research grounding

PurelandFold and FoldingAgent are research references for converting origami demonstrations/keyframes into ordered geometric states. They are research grounding, not substitutes for the concrete demonstration source.

## Media storage

Do not commit the full source video to Git. Retain provenance and stable references in the case pack. Large/production media belongs in object storage.

