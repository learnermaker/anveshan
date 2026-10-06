# Kiro Orchestrator — ONE Kiro session finishes everything (workflows with parallel tasks)

You are the single orchestrating Kiro session (Sonnet 4.6) for the Anveshan hackathon. Jim will not answer questions: decide using the defaults below and log each decision in `docs/plans/DECISION-LOG.md`. Deadline: 2026-10-18.

**Read, in order:**
1. this file;
2. `docs/kiro/specs/00-COMMON.md` (environment and rules);
3. `docs/kiro/specs/KIRO-WAVE2.md` (folder table and rules, which apply to your parallel tasks);
4. `docs/plans/wave2-master-spec.md` (WP1–WP5);
5. `docs/plans/cloud-runbook.md` §0 (token discipline), §4 (pending items) and §5 (autonomy rules). Use its content, but **Windows paths, not Linux**: Python is `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe`, media comes from `--from-dir C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\var\scratch\media`, and `.env` exists in the main folder.

## Golden rule: one folder per parallel task
**Parallel tasks must never edit the same folder.** Every task works only inside its own git worktree folder (already created under `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan-wt\`) and commits only there. **You (the orchestrator) are the only one who merges, in the main folder** `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan` on branch `m1/hero-cases`.

## Phase 0 — finish K1 and K4 (2 parallel tasks)
The earlier K1 and K4 sessions must be stopped. If they are still running, Jim stops them before starting you.

| Task | Folder | Spec | Notes |
|---|---|---|---|
| T-K1 | `anveshan-wt\k1-kolam` (branch `kiro/k1-kolam`) | `docs/kiro/specs/K1-kolam-finish.md` | Read `docs/kiro/reports/K1-*` in the main folder for progress so far. Finish every acceptance item not yet done. Commit any uncommitted work first. |
| T-K4 | `anveshan-wt\k4-origami` (branch `kiro/k4-origami`) | `docs/kiro/specs/K4-origami-live.md` | **Use `gemini-3.5-flash-lite` for origami vision** (set model key `video_frames` via env `ANVESHAN_VIDEO_FRAMES_MODEL=gemini-3.5-flash-lite` in that folder's `.env`), ≤ 4 images per call. Budget ≤ 120 calls. |

When both are done, merge them into `m1/hero-cases` in the main folder (K1, then K4), then run the full verification (§Verify).

## Phase A — WP1–WP4 (4 parallel tasks)
First update each WP folder to the merged base. In each WP folder run:
```bash
git merge --ff-only m1/hero-cases
```
It works because WP branches have no commits yet; if it fails, run `git reset --hard m1/hero-cases` on a clean tree.

| Task | Folder | Work |
|---|---|---|
| T-WP1 | `anveshan-wt\wp1-perception` | master spec WP1 (`K6-composer-backend.md`) |
| T-WP2 | `anveshan-wt\wp2-universal` | master spec WP2 (`K7-engines-generalise.md` §0–§5) — **lazy imports of `tracks.common.perceivers` (master §7.9)** |
| T-WP3 | `anveshan-wt\wp3-composer-ui` | master spec WP3 (`K8-composer-ui.md`) |
| T-WP4 | `anveshan-wt\wp4-tabla` | master spec WP4 (`K2b-tabla-timbre.md`) |

Give each task: its row, the master spec §3 ownership table, the §7 overrides, and the KIRO-WAVE2 rules. Each task ends with a ≤ 60-line report file `docs/kiro/reports/<WP>-REPORT.md`, committed in its own folder.

Then merge into `m1/hero-cases` in the order **WP4 → WP1 → WP2 → WP3**, running §Verify after each merge. Resolve conflicts by master spec §3 ownership; `track_a/api.py` is split by function (WP1: `list_cases`/`to_view`; WP2: `build_case`).

## Phase B — WP5 integration (you, sequentially, in the main folder)
Do master spec §5 steps 2–9, plus cloud-runbook §4 pending items 1–7 (Windows paths). Live budget ≤ 150 calls. You may use parallel tasks only for **read-only** work (e.g. reviewing reports, drafting docs in a scratch folder under `var/kiro/`).

## Verify (after every merge)
```powershell
.\.venv\Scripts\python.exe -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live" | Select-Object -Last 5
.\.venv\Scripts\python.exe .github/scripts/check_governance.py
.\.venv\Scripts\python.exe .github/scripts/check_case_packs.py
.\.venv\Scripts\python.exe .github/scripts/check_contract_parity.py
npm --prefix app run build | Select-Object -Last 5
```
- All must pass. On a failure, fix it in the main folder (small, owned-by-integration fixes) and commit.
- Never weaken tests or checks.

## Commits and pushes
- Commit after every step: `type(scope): summary`.
- After each phase, push: `git push origin m1/hero-cases`. Pushes work through the Git Credential Manager that GitHub Desktop set up. If a push fails, continue and note it.
- **Never touch `main`.**
- At the end, write the PR body to `docs/plans/PR-BODY.md`; validate it with `.\.venv\Scripts\python.exe .github/scripts/check_pr_contract.py` (set env `PR_BODY` to the file contents first). Jim opens the PR in GitHub Desktop.

## Defaults when unsure
In priority order:
1. keep the 8 contracts frozen;
2. keep hero cases byte-identical;
3. prefer deterministic over model-based;
4. prefer the cheapest option.

Log the decision. If something is blocked (e.g. the key fails), finish everything else and log TODOs.

## Final message to Jim (≤ 60 lines)
- Phases done, with commit ranges.
- Test, check and build counts.
- The live-check table.
- Calibration decisions.
- Deviations.
- Blocked items.
- The `PR-BODY.md` path.
- Competition reminders: team of 2–4 by 2026-10-11; deadline time zone unknown (ask Hack2skill); portal https://hack2skill.com/event/aibuildercup2026/registration.
