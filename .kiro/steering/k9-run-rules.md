---
inclusion: always
---

# Anveshan K9 run rules (every Kiro session, step and task)

These rules apply to the K9 build (`docs/kiro/specs/K9-ORCHESTRATOR.md`) and to any Kiro work in this repository.

1. **Execute; don't redesign.** Claude Code has done the product and technical planning. The specs are exhaustive on purpose: follow them literally. When reality differs from a spec (a file moved, an anchor changed), follow the spec's intent and log the deviation in `docs/kiro/reports/K9-DECISIONS.md`.
2. **Stay in your folder.**
   - Each task works only in its own worktree under `.worktrees/` and commits only on its own branch.
   - Never edit the main folder's tracked files.
   - The only main-folder writes allowed are under `.kiro/k9-run/`.
   - Never merge, rebase, switch branches or push `main`.
3. **Stay in your files.** Edit only files listed in your spec's ownership section. If you need another file changed, write it under "Requests for PC" in your status file and work around it.
4. **Report status continuously** to `.kiro/k9-run/status/<TASK-ID>.md` (template in `K9-ORCHESTRATOR.md` §4): at the start, after every numbered spec section, when blocked, and at the end. Claude Code and Jim read these files to follow progress.
5. **Read the inbox.** Read `.kiro/k9-run/INBOX.md` at the start and after every numbered section. Follow entries addressed to your task ID or to `ALL`, unless they conflict with rules 1–3 or 7. Acknowledge each one in your status file ("Inbox: handled <entry id>").
6. **Push regularly.** After each numbered section, commit, then `git push -u origin <your branch>`. If a push fails, note it in your status file and continue.
7. **Non-negotiables:**
   - The 8 contracts in `tracks/common/schemas/` and `app/src/types/contracts.ts` are frozen.
   - No model call decides scores, permissions, status or insights.
   - No new dependencies.
   - No live model calls unless your spec gives a budget.
   - Never print, log or commit `.env` or any key or access code.
   - Committed files are ≤ 2 MB.
   - Synthetic content is labelled; internet sources are never called experts.
8. **Windows:**
   - Python is `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.venv\Scripts\python.exe`;
   - use `curl.exe --ssl-no-revoke`;
   - `app/node_modules` in worktrees is a junction: never run `npm install`.
9. **Save tokens:**
   - use `grep -n` and partial reads;
   - never open `package-lock.json`, `app/dist`, golden runs, `.npy`, media, large JSON fixtures or `app/src/data/cases/registry.ts`;
   - pipe test output through `| Select-Object -Last 15`.
