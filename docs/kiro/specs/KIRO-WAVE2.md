# Kiro Wave 2 — how to run the master spec in Kiro (Windows, Sonnet 4.6)

This replaces `docs/plans/cloud-runbook.md` for Kiro. The work definition is still `docs/plans/wave2-master-spec.md` (WP1–WP5) and its K-spec appendices. Read `docs/kiro/specs/00-COMMON.md` (environment, rules) first.

## Session layout (one Kiro session per folder; never share a folder)

| Session | Folder (already created) | Branch | Work | Start |
|---|---|---|---|---|
| K1 (existing) | `anveshan-wt\k1-kolam` | `kiro/k1-kolam` | finish `K1-kolam-finish.md` | now (continue) |
| K4 (existing) | `anveshan-wt\k4-origami` | `kiro/k4-origami` | finish `K4-origami-live.md` | now (continue) |
| WP1 | `anveshan-wt\wp1-perception` | `kiro/wp1-perception` | master spec WP1 = `K6-composer-backend.md` | now |
| WP2 | `anveshan-wt\wp2-universal` | `kiro/wp2-universal` | master spec WP2 = `K7-engines-generalise.md` §0–§5 | now |
| WP3 | `anveshan-wt\wp3-composer-ui` | `kiro/wp3-composer-ui` | master spec WP3 = `K8-composer-ui.md` | now |
| WP4 | `anveshan-wt\wp4-tabla` | `kiro/wp4-tabla` | master spec WP4 = `K2b-tabla-timbre.md` | now |
| WP5 | done by Claude Code (or a later Kiro session) | — | master spec §5 integration | after all of the above are merged |

All folders are under `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\`.

## Rules for every Wave-2 Kiro session (in addition to 00-COMMON)
1. **Work only in your folder and branch. Commit after every numbered step.** Never merge, rebase, push or switch branches.
2. **Apply master spec §7 overrides 2–10** (ignore override 1 about folders, because this table defines the folders). Especially:
   - **WP2: import `tracks.common.perceivers` lazily inside functions, and inject a fake module in tests (§7.9).** It does not exist in your branch.
   - WP1: import `track_a.universal` lazily, with the fallback.
3. **Do not use parallel sub-tasks that edit files at the same time in one folder.** Sub-tasks are fine for reading and research. Make code edits sequentially.
4. **API key:** copy `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.env` into your folder root (WP1, WP2 and WP4 only). Never print it.
5. **Live-call budgets:** WP1 ≤ 40 calls; WP2 none (its live check happens in WP5); WP3 none; WP4 ≤ 5 calls.
6. **Fast models:** `vision_fast` / `audio` = gemini-3.5-flash-lite and `embedding` = gemini-embedding-2. Never use Gemma for interactive paths (43 s per image).
7. **Save tokens:**
   - read only the K-spec sections cited for your WP;
   - use `grep -n` / partial reads instead of opening big files;
   - never open JSON fixtures, golden runs, `.npy`, images, `package-lock.json` or `app/dist`;
   - pipe test output through `| Select-Object -Last 15` (PowerShell) or `| tail -15` (bash).
8. **Done** = the master spec §4.6 definition of done. Then write `docs/kiro/reports/<WP>-REPORT.md` (≤ 60 lines: Done, Tests, Live results, Deviations, Requests for WP5, Open issues), commit it, and tell Jim "<WP> complete — branch kiro/<…> ready to merge".
