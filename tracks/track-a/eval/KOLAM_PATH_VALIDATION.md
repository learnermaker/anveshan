# Kolam inferred path vs the held-out direction diagram

**Status:** experiment record (2026-10-06). Reproduce with
`python tracks/track-a/eval/kolam_path_validation.py`; raw numbers in `kolam_path_validation.json`,
overlay in `kolam_path_overlay.png` (inferred line in orange over the diagram; dots mark arcs whose
arrow direction could be decided: blue = against our traversal, green = with it).

## Setup

- System input: `src.kolam.target.v1` (finished image) only. The goal builder
  (`tracks.common.goals.kolam.payload_from_image`, `kolam_geometry_v1`) inferred **1 closed
  continuous line** through **40 of 41 dots** (the centre dot is enclosed), with **32 crossings**
  resolved by smooth continuation and **8-fold** rotational symmetry, no mirror axes.
- Held out: `src.kolam.direction_diagram.v1` (author's arrow diagram, `used_by_system: false`).
  It is read only by this script.
- The diagram is registered to the goal frame with a similarity transform (ink moments + local
  search): scale 0.992, rotation 269.25 deg (one of the 8 symmetry-equivalent solutions; direction
  results do not depend on which one), score 0.90.

## Results

| Check | Result |
|---|---|
| Diagram line pixels within tau (6 px) of the inferred line | **99.3 %** |
| Inferred line samples within tau of diagram ink | **99.8 %** |
| Dot-to-dot arcs on the inferred line | 40 |
| Arcs whose arrowhead end could be decided | 32 (8 unclear: one arc type per 45 deg sector) |
| Of the decided arcs, arrows pointing the same way along the inferred loop | **32 / 32** (all opposite to our arbitrary clockwise start direction) |

## What this shows (and does not)

- **Route:** the author's arrows lie on the inferred line and the inferred line covers the arrows
  (both > 99 %). The inferred geometry is the drawn geometry.
- **Direction / continuity:** every arrow we could read points the same way when you walk the
  single inferred loop. So the author's arrows define one consistent direction along that loop,
  which is what a single continuous drawing of the inferred loop requires. Our traversal direction
  (clockwise by signed area, starting at the topmost dot) is an arbitrary convention and runs
  against the author's arrows; the builder already labels direction and start as arbitrary.
- **Not shown:** pixel overlap and orientation consistency do not, by themselves, prove the
  straight-through pairing at each crossing (a "turn" pairing would use the same pixels and could
  also be orientation-consistent). The diagram's arrow shafts do visibly pass straight through
  crossings, which supports the smooth-continuation reading, but this script does not measure it.
- The diagram segments the line dot to dot, so it does not state the number of separate lines;
  "one continuous line" remains our inference (claims stay `inferred`, confidence 0.4).
- Arrowhead detection is a heuristic (barb ink 3–10 px off the line near an arc end); 8 arcs were
  undecidable. One image, one author: this is a single data point, not a validated accuracy.
