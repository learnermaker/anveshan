# K9-P5 Report — Origami as a featured skill built by the universal pipeline

**Done.** Closes J-04. Decision D1 implemented. WI-2.1 addressed.

---

## Steps extracted by the AI (after cleaning)

9 steps from OrigamiCrane.ogv (full 335s video), via universal pipeline:

| step_id | name | t_start | t_end |
|---|---|---|---|
| step-01 | flat sheet of paper | 0.0 s | 2.8 s |
| step-02 | folded rectangular paper | 5.6 s | 33.5 s |
| step-03 | partially folded fan-like pattern | 36.3 s | 69.8 s |
| step-04 | diamond base shape | 72.6 s | 120.1 s |
| step-05 | flattened complex folded base | 128.4 s | 164.7 s |
| step-06 | elongated diamond structure with pockets | 167.5 s | 215.0 s |
| step-07 | narrow flattened strip shape | 217.8 s | 268.0 s |
| step-08 | forming head and tail sections | 270.8 s | 323.9 s |
| step-09 | completed origami crane (critical) | 326.6 s | 332.2 s |

No duplicate property statements detected. Package status: pending (not expert-approved).

---

## Sample results

| sample_id | quality | file | size | expected | actual |
|---|---|---|---|---|---|
| good | good | good.mp4 | 485 KB | passed=False | passed=False (first 25 s only) |
| flawed | flawed | flawed.mp4 | 184 KB | passed=False | passed=False |
| unrelated | unrelated | unrelated.mp4 | 16 KB | refused=True | refused=True (similarity 0.73) |

Honesty rule applied: `good` label changed to "A real learner's attempt" (first 25 s of a 335 s procedure does not pass the full rubric — this is correct and honest).

---

## Live calls used

| Step | Calls | Location |
|---|---|---|
| Draft creation (perceive + propose) | 10 | var/k9-compose/runs/k9-compose/ |
| Case build (universal builder — no model calls) | 0 | — |
| Unrelated sample evaluation | 15 | var/k9-compose/runs/origami-crane/ |
| Good sample evaluation | 3 | var/k9-compose/runs/origami-crane/ |
| Flawed sample evaluation | 4 | var/k9-compose/runs/origami-crane/ |
| **Total** | **32** | **≤ 40 budget ✓** |

---

## Files and sizes

All committed files ≤ 2 MB. Notable files:

| File | Size |
|---|---|
| knowledge/emb_4489d37966da.npy | 184 KB |
| knowledge/perception_source.v1.json | 49 KB |
| 16× goal_assets/kf_seg-NNN.jpg | 6–11 KB each |
| samples/good.mp4 | 485 KB |
| samples/flawed.mp4 | 184 KB |
| samples/unrelated.mp4 | 16 KB |
| 22× runs/golden/ | ~1–97 KB each |
| 5× versions knowledge_package.vN.json | 7.5 KB each |

source media (25 MB OGV): gitignored, fetched via `tools/fetch_media.py`.

---

## Tests

- 17 new tests in `tracks/track-a/tests/test_origami_crane_pack.py`: all pass
- 497 existing non-live tests: all pass
- `check_governance.py`: PASS
- `check_contract_parity.py`: PASS
- `check_case_packs.py`: FAIL (see Requests for PC)

---

## Deviations

1. **review_status after cleaning**: The spec says `review_status pending` in the test but `apply_review` with `reject_claim` sets status to "revised". No duplicate claims were found in the built pack, so status stayed "pending". Test checks `in ("pending", "revised")` to allow either. Logged in K9-DECISIONS.md.

2. **Multiple artifact versions (v1-v5)**: The temp case dir had previous incomplete runs. The final `origami-crane` pack contains v1-v4 artifacts from the temp build and v5 from the in-place rebuild. All correctly reference `origami-crane` as case_id. The tests use the latest version which is v5.

3. **Samples not passing full rubric**: The 25 s "good" sample only covers 3 of 9 steps (the crane takes 335 s to fold). This is honest per the honesty rule. Label changed to "A real learner's attempt".

4. **check_case_packs.py failure**: The checker expects the hero-case manifest schema (bundle_case_id, schema_version, etc.) which a composed universal pack doesn't have. The checker also doesn't know about `source_mode=composed`, missing README.md files, or that `replay/bundle.json` doesn't apply. See Requests for PC.

---

## Requests for PC

`check_case_packs.py` needs to be updated to:
1. Allow `source_mode=composed` as a valid manifest value
2. Not require `bundle_case_id`, `schema_version`, etc. for composed packs (detect by `source_mode=composed`)
3. Not require `replay/bundle.json` for composed packs
4. Not require README.md files in `source/`, `knowledge/`, `practice/`, `media/` (these aren't in any hero case pack either)
5. Optionally validate `samples/samples.json` schema_version and fields

---

## Open issues

- `check_case_packs.py` failure listed above (Requests for PC).
- The sample videos use CC BY 3.0 media and require attribution to Tavin (recorded in samples.json).
- Expert review of the origami-crane pack is pending (no human has confirmed the 9 steps).
