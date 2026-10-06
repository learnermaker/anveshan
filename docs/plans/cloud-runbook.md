# Cloud Session Runbook — finish Anveshan end to end, autonomously

**For:** a Claude Code cloud session on `learnermaker/anveshan`, branch **`m1/hero-cases`**. **Mode:** fully autonomous. Jim will not answer questions. Decide using the defaults here, log each decision in `docs/plans/DECISION-LOG.md`, and keep going. **Deadline:** 2026-10-18.

The work spec is `docs/plans/wave2-master-spec.md` (WP1–WP5). Its K-spec appendices live in `docs/kiro/specs/`. **This runbook overrides both** where they differ (cloud paths, autonomy, budgets, token discipline).

---

## 0. Token and cost discipline (read first; apply throughout)

1. **Keep the cache warm.**
   - Don't edit `CLAUDE.md`, `AGENTS.md` or this runbook during the session, since that invalidates the cached prefix.
   - Work in long, focused turns.
   - Batch independent tool calls in one message.
2. **Read narrowly.**
   - Never read whole large files you don't need. Use `grep -n` / `sed -n 'a,bp'`, and `graphify query|explain` if graphify is installed (`pip install graphifyy` is optional; skip it if that fails).
   - Never `cat` JSON fixtures, golden runs, `.npy`, images, `package-lock.json`, `app/dist`, `screenshots/`, or `tracks/cases/*/runs/`.
   - The K-specs are long: read only the sections the master spec cites for the current WP.
3. **Quiet commands.** Always run `pytest -q … 2>&1 | tail -15`, `npm run build 2>&1 | tail -8`, and `--lf` to rerun failures only. Pipe noisy output through `tail` / `grep`.
4. **Delegate with summaries.**
   - Run the Phase-A WPs as **parallel subagents** (`isolation: "worktree"`).
   - Use `model: "sonnet"` for WP3 (UI) and WP4 (DSP), and Opus (the default) for WP1 and WP2.
   - Subagents must return a report of at most 60 lines (master spec §4.6), never file dumps.
   - Use the `Explore` agent for any broad search instead of reading many files yourself.
5. **Don't redo work.** The gateway records every model call (`tracks/cases/*/runs/golden`, `var/runs`). Use `recorded` mode when re-running evals or tests. Live calls only happen inside the budgets in §4.
6. **Commit after every completed step**, with message trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. If the session is interrupted, resume from `git log` and the DECISION-LOG, not from memory.
7. **Context hygiene:** after finishing each phase, write a 10-line status to `docs/plans/DECISION-LOG.md` (what's done, what's next). If the context gets long, rely on that file instead of re-deriving state.

## 1. Cloud environment setup (first 10 minutes)

```bash
git checkout m1/hero-cases && git pull --ff-only
python3 -m venv .venv && . .venv/bin/activate && pip install -q -r requirements-dev.txt
(cd app && npm ci --no-audit --no-fund)
python tools/fetch_media.py            # downloads licensed media (Wikimedia); retry later on HTTP 429; never commit media
pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live" 2>&1 | tail -5   # expect ~291 passed
```

- **Paths:** replace every `C:/Users/JIMSEELAN/.../.venv/Scripts/python` in the specs with `.venv/bin/python` (or `python` inside the venv). Drop every `--from-dir …var/scratch/media` (that folder only exists on Jim's PC; download instead).
- **API key:** `GEMINI_API_KEY` comes from the cloud environment's variables. Check with `python -c "import os;print(bool(os.environ.get('GEMINI_API_KEY')))"`.
  - **If False:** do all work with tests and recorded/fake gateways, skip the live checks, mark them `PENDING-KEY` in the DECISION-LOG and the final report, and continue. **Never** write a key to any file.
- **Model env defaults** (export if not set):
  ```bash
  export ANVESHAN_AUDIO_MODEL=gemini-3.5-flash-lite ANVESHAN_VISION_FAST_MODEL=gemini-3.5-flash-lite ANVESHAN_EMBEDDING_MODEL=gemini-embedding-2 ANVESHAN_TEXT_IMAGE_MODEL=gemini-3.5-flash-lite ANVESHAN_VIDEO_FRAMES_MODEL=gemini-3.5-flash-lite ANVESHAN_MODEL_TIMEOUT_MS=300000
  ```
- **Origami media** (`OrigamiCrane.ogv` / `Crane.ogv`, about 25 MB each) is needed only for the origami steps; download it once.

## 2. Phase 0 — finish the Kiro leftovers (K1, K4): WP0

K1 (Kolam finish) and K4 (Origami live) were running in Kiro on Jim's PC and may or may not have been pushed.

```bash
git fetch origin
git branch -r | grep -E "kiro/k1-kolam|kiro/k4-origami"
```

- **If `origin/kiro/k1-kolam` exists:** merge it (`git merge --no-ff origin/kiro/k1-kolam`), run the tests, and then complete any acceptance item of `docs/kiro/specs/K1-kolam-finish.md` that its report (`docs/kiro/reports/K1-REPORT.md`) doesn't mark done.
- **If it doesn't exist:** do K1 yourself, inline or as one Sonnet subagent:
  - the three Kolam test files;
  - faster photo path;
  - evaluation-core §3.2 note;
  - real build + golden run;
  - Kolam e2e session test.

  The Kolam build makes one optional vision call. Use `vision_fast` instead of Gemma, since the builder's call uses `text_image`. If the key is missing, accept the warning path; the deterministic build is complete without it.
- **Same rule for K4** (`docs/kiro/specs/K4-origami-live.md`), with these adjustments:
  - Use **`vision_fast` (flash-lite)** for Origami state recognition instead of Gemma. Set `ANVESHAN_VIDEO_FRAMES_MODEL=gemini-3.5-flash-lite`, or change the origami code to use model key `vision_fast`. Keep ≤ 4 images per call. This makes the latency probe a quick confirmation, not a research task.
  - Then do the real goal build, golden runs, the 5 synthetic/control attempt evals and `RESULTS.md`.
  - **Budget:** ≤ 120 calls.
- **Also clean up:** the files `docs/kiro/reports/K1-tests-review.{md,json}` were written into the main tree by mistake. Keep them (they're harmless notes); don't duplicate them.

## 3. Phase A — WP1–WP4 in parallel (master spec §2–§4)

Launch **4 subagents in one message**, each with `isolation: "worktree"`, running WP1, WP2, WP3 and WP4 from `docs/plans/wave2-master-spec.md`. Give each:
- the WP row, its K-spec path and the ownership table (§3);
- the §7 overrides (especially **§7.9: lazy imports in WP2**);
- the §0/§1 rules of this runbook (cloud paths, quiet commands, per-step commits, the ≤ 60-line report).

Start Phase A **after Phase 0 is merged** so all worktrees start from the same base.

When the subagents finish, merge in the order WP4 → WP1 → WP2 → WP3. After each merge, run the full tests, the 3 checks and the app build. Resolve conflicts using master spec §3 ownership.

If a subagent stops early (rate limit), resume it via its worktree's `git log`, or finish its remaining steps yourself.

## 4. Phase B — WP5 integration (master spec §5), plus pending items

Do master spec §5 steps 1–9, with these additions and clarifications.

**Live budgets** (if the key is present): Phase 0 ≤ 150 calls; Phase A ≤ 50; Phase B ≤ 150. That is about $1 in total, given flash-lite and embeddings at ≈ $0.0003 per call. Record every live run; promote useful ones to `runs/golden`.

**Pending items to include:**
1. **Relevance-gate calibration:** measure the embedding cosine for (same, edited, unrelated) attempts in the live checks and set `min_similarity` with the data. Log it in the `universal-pipeline.md` §11 calibration log.
2. **Origami independent learner:** no licence-clean independent crane video exists. Use the synthetic variants plus `Crane.ogv` (a positive control: same performance, re-encoded) and say so honestly in the validation docs.
3. **Live-service UI audit** (from K3): run the service plus the built app (`uvicorn` serving `app/dist`) and exercise the hero flows and one composer flow with Python `httpx` against the HTTP API (the e2e smoke suite). If a headless browser exists in the cloud, take screenshots; otherwise skip them and note it.
4. **Tabla bol path:** with the audio model enabled, confirm the bol labels appear only as INFERRED class labels (WP4) and never affect scores.
5. **Kolam extra images** (Wikimedia was rate-limited from Jim's IP): try once with a 60 s gap between downloads, for upload testing only; never commit them. Skip if it fails.
6. **Docs:**
   - `docs/validation/experiments.md` and `findings.md`, honest about scope (engineering/capability evidence on internet and synthetic data, not human-learner validation);
   - `README.md` status;
   - `docs/deploy/DEPLOY-CHECKLIST.md`, covering console deployment by Jim (see `docs/kiro/cloud-run-console-guide.md`): env vars, the `gemini-api-key` secret, `max-instances 1`, 2 GiB memory, 300 s timeout, smoke commands;
   - make sure `.env.example` documents every key;
   - update `docs/status/NOW.md` and `project.yaml` with the implemented state.
7. **Competition facts to surface in the final report** (no action needed in code):
   - teams must have 2–4 members, registered by 2026-10-11;
   - the deadline time zone isn't published; check with Hack2skill;
   - fresh-code rule: the first commit is 2026-10-02, which complies;
   - portal: https://hack2skill.com/event/aibuildercup2026/registration.

## 5. Autonomy rules and defaults
- **Never ask Jim.** If something is ambiguous, pick the option that (a) keeps the 8 contracts frozen, (b) keeps hero cases byte-identical, (c) is deterministic, and (d) is cheapest. Log it in the DECISION-LOG with one line of reasoning.
- **Never:**
  - push to or merge into `main`;
  - force-push;
  - delete branches other than your own temporary ones;
  - commit secrets or media over 2 MB;
  - weaken tests or governance checks to make them pass;
  - mark anything "validated" without evidence.
- **Push** `m1/hero-cases` to origin at the end of each phase (`git push origin m1/hero-cases`).
- **If a WP can't be completed** (e.g. a missing key blocks it), finish everything else, leave clean TODOs in the DECISION-LOG, and continue.
- **Finish by opening a PR `m1/hero-cases → main`.** Use the repo's PR template, link an issue (create one with `gh issue create` if `gh` is available and authenticated; otherwise write the issue text in the PR body and note it), and validate the body with `python .github/scripts/check_pr_contract.py`. If `gh` is unavailable, push the branch and put the ready-to-paste PR body in `docs/plans/PR-BODY.md`.

## 6. Final report (last message of the session, ≤ 80 lines)
- Phases done / partial, with commit ranges.
- Tests, checks and build status, with counts.
- Live-check table: case, attempt, statuses, latency, cost.
- Calibration decisions.
- Deviations from the specs.
- Items marked `PENDING-KEY` or blocked.
- PR link or `PR-BODY.md` path.
- The competition facts in §4.7.
