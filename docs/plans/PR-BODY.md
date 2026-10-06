## Outcome

Wave 2 integration (WP5): wire universal pipeline to real perceivers, run live checks,
extend e2e smoke suite, calibrate thresholds, update validation docs, README, and deploy
checklist.

Closes #99

<!-- Note: #99 is a placeholder. Jim should create a tracking issue for the Wave 2 integration
     work before opening this PR. If an issue already exists, replace #99 with its number. -->

## Scope

**Included**

- WP5 step 2: add `"universal"` to `ACCEPTED_KINDS` in `track_b/api.py`; real perceivers
  importable (WP1 merged); 34 universal tests pass against real perceiver signatures.
- WP5 step 3: live check golden runs — kolam same/half-erased/refused, rangoli new image
  skill, tabla_chanderi new audio skill. Fix `build_case` to pass `case_dir` to
  `modality_for` (composed cases were being rejected as SYNTHETIC showcase cases). Calibrate
  quality gate thresholds (blur_score 15→0.002, brightness 0.08→0.02; values are in [0,1]).
- WP5 step 4: `tools/e2e_smoke.py` (HTTP smoke), `service/tests/test_e2e_real.py` (10 real-
  tracks tests: health, list cases, get hero cases, query, kolam trace session, composer
  practice attempt, relevance-refused attempt).
- WP5 step 5: `docs/plans/universal-pipeline.md` §11 calibration log with data-backed
  justifications for all threshold changes and min_similarity retention.
- WP5 step 6: `docs/validation/experiments.md` — E1 Kolam, E2 Tabla, E3 Origami, E4
  universal pipeline, E5 latency. `findings.md` updated with honest scope and unvalidated
  items.
- WP5 step 7: `README.md` — hero case descriptions, how-to-run, testing commands, deployed
  URL placeholder, implementation status table.
- WP5 step 8: `docs/deploy/DEPLOY-CHECKLIST.md` — env vars, gemini-api-key secret,
  max-instances 1, 2 GiB memory, 300 s timeout, smoke commands, cost estimate. `.env.example`
  updated with missing `ANVESHAN_STATIC_DIR`.

**Not included**

- No deployment (Jim deploys via GCP console using `docs/deploy/DEPLOY-CHECKLIST.md`).
- No changes to the 8 frozen contracts in `tracks/common/schemas/`.
- No hero case artifact changes (hero tests unchanged and green).
- No KolamCanvas wiring for universal UI (WP3 request #4: deferred — placeholder is
  functional, real geometry wiring requires a separate UI task).
- No `audio/webm` format-gate change for WP1 request (no observed user-impact during
  integration).

## Validation

- Tests: **423 non-live tests pass** (83 common, 110 track-a, 230 track-b + service).
  All governance checks pass (check_governance, check_case_packs, check_contract_parity).
  `npm --prefix app run build` passes.
- Manual / benchmark evidence:
  - WP5 live checks: kolam same-image similarity 1.00, half-erased 0.96, gradient correctly
    refused; rangoli 0.98; tabla_chanderi compose+eval pass. See `var/runs/wp5_live_checks/`
    (gitignored, local run 2026-10-06).
  - All hero case synthetic evals: Kolam 50/50, Tabla 49/49, Origami 5/5 attempts evaluated.
- AI changes: quality gate thresholds recalibrated (blur_score 15→0.002, brightness
  0.08→0.02) based on live measurements. min_similarity=0.72 retained. Documented in
  `docs/plans/universal-pipeline.md` §11.
- No model/prompt/config changes in this PR. No new golden run files committed (live runs
  go to gitignored `var/`).

## Alignment

Canonical source: `docs/plans/wave2-master-spec.md` §5 (WP5 Integration), `docs/kiro/specs/K5-integration-deploy.md` §1–§4, §6.

Architecture/ADR: `docs/plans/universal-pipeline.md` §11 (new calibration log).

## Scope check

- [x] No unrelated work.
- [x] No NOW-scope expansion without a linked Scope Change issue.
