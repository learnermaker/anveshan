# K9-B2 — Stability numbers and evidence file (technical-panel WI-5.4, part of J-17)

**Wave B task:** it starts only after Wave A is merged. Read `00-COMMON.md`, then this file. Your folder, branch, status file and inbox protocol are in `K9-ORCHESTRATOR.md` §2 and §4.

**Goal.** Measure how repeatable the evaluation is on the committed samples. Write the numbers into:
- `docs/validation/experiments.md`, as entry E10;
- `app/public/evidence.json`, which the "How we check" page renders (schema: `K9-B1-EVIDENCE-A11Y.md` §1.1).

---

## 0. Ground rules and budget

- **Live calls: ≤ 60 in total.** Copy `.env` from the main folder into your folder root (gitignored). Never print it.
- Set `ANVESHAN_LIVE_CACHE=0` for the live runs, so repeated runs really call the model; otherwise the cache would make them trivially identical.
- Kolam (trace) and Tabla are deterministic: run them in recorded mode with **0** live calls (consistency is expected to be 1.0; say "by design").
- **origami-crane** (universal, model-assisted) needs live runs: 3 runs × 3 samples ≈ 9 evaluations. Estimate the calls per evaluation from one run first, and stop before the budget is exceeded.

## 1. Files you own

- `tools/stability_runs.py` (new);
- `app/public/evidence.json` (new);
- `docs/validation/experiments.md` (append E10 only);
- `docs/validation/stability-2026-10.json` (new; the raw results).

## 2. `tools/stability_runs.py`

```text
usage: stability_runs.py [--cases kolam,tabla,origami-crane] [--runs 3] [--live-cases origami-crane] [--max-calls 60]
```

**For each case and each sample** in its `samples/samples.json` (format: K9-P4 §2):
1. Run `--runs` evaluations through the real Track B session API, as in the K9-P4 tests: start a session, submit the sample as the baseline, and read the evaluation. Each run uses a fresh session and a fresh `data_dir` under `var/k9-stability/<case>/<run>/`.
2. **Mode:** recorded for deterministic cases; live with `ANVESHAN_LIVE_CACHE=0` for `--live-cases`.
3. **Record per run:**
   - `passed`, `total_score` and the criterion statuses;
   - the first-divergence criterion;
   - refused or not: an `INVALID_INPUT`/`HUMAN_REVIEW_REQUIRED` failure, or a relevance refusal in the result. Check how the universal evaluator signals "unrelated"; see `track_b/evaluators/universal.py` relevance handling.
   - the number of live calls (count new run dirs).
4. **Consistency per sample** = the share of runs whose (passed, first-divergence criterion, refused) tuple equals the most common tuple. Per case = the mean over its samples.
5. **Sample outcome label:**

| Sample | Condition | Label |
|---|---|---|
| good | passed in the majority of runs | passed |
| good | otherwise | failed |
| flawed | not passed in the majority of runs | caught |
| flawed | otherwise | missed |
| unrelated | refused or not passed in the majority of runs | refused |
| unrelated | otherwise | missed |

6. **Write:**
   - `docs/validation/stability-2026-10.json`: every run, the models (from `tracks/common/models.py` registry ids) and the prompt versions used;
   - `app/public/evidence.json`:
     - `tests.count` from `pytest --collect-only -q … -m "not live"`;
     - one entry per case;
     - `not_yet` = the two default strings plus any limit you observed (e.g. "Swapped-order mistakes are not always caught on video").

## 3. E10 entry (`docs/validation/experiments.md`, same format as the existing entries)

**E10: Repeatability on committed samples (engineering evidence).** Include:
- the date;
- the models and prompts;
- runs per sample;
- the cache disabled for the live runs;
- a table of case × sample → outcome and consistency;
- the live calls used;
- the interpretation;
- the limits: synthetic and internet-derived samples, not real learners, and small n.

**Never call this validation of learning.**

## 4. Acceptance

- The script reruns deterministically for the recorded cases.
- `evidence.json` validates against the B1 schema (write a 10-line check in the script).
- E10 is appended.
- Live calls ≤ 60, reported.
- Report `docs/kiro/reports/K9-B2-REPORT.md`.
