---
name: anveshan-ui-check
description: Visual verification loop for Anveshan UI changes. Start the app, walk the affected role paths, take screenshots at phone and desktop widths, check the console, run the plain-language and role scans, and share before/after proof. Use after any change under app/src that is visible in the browser, and before committing UI work (especially while a Kiro run is merging in parallel).
---

# Anveshan UI check

A UI change is not done until you have seen it render, at both sizes, for the role it affects. Compiling is not enough. Follow `anveshan-ux` for what "right" means; this skill is how you prove it.

## 1. Start the app

**Claude Code (desktop app):** use the preview tools with the names in `.claude/launch.json`. Never start servers with Bash.

| Need | Start |
|---|---|
| UI only, no backend (fastest; mock data incl. steward code `steward`) | `preview_start {name: "app-mock"}` → http://localhost:5174 |
| Real backend (recorded mode, no live calls) | `preview_start {name: "service"}` then `preview_start {name: "app"}` → http://localhost:5173 |

**Kiro or a terminal:**
1. Run `npm --prefix app run dev:mock` in the background.
2. Use the puppeteer scripts in §4. Never run `npm install` in a worktree, because `node_modules` there is a junction.

## 2. Walk the paths your change touches

| Role | Path (query string) | What to look at |
|---|---|---|
| Learner | `?view=discovery` → open Kolam → `?view=source` → Start practising → "Try a sample attempt" → first try → feedback → second try → `?view=transmission` | one primary button per screen; plain words; trust line visible; "Why this feedback?" opens and reads in the fixed order |
| Creator | `?view=composer` (or a sample source) → `?view=mine` → the skill's Learn page → "Your skill" panel → Check steps → Publish | status chip and help line; Publish disabled until steps are checked; confirmations |
| Steward | `?view=steward` → sign in (`steward` in mock) → Overview, Review queue → detail, Library, Consent & licences, Usage | plain labels first, IDs only inside Details; the temporary-data banner |
| Team | add `&debug=1` | technical panels appear only here |

Also open the **empty**, **loading** and **error** states for the screen you changed. With mock data, an unknown case id or a stopped service usually triggers the error state.

## 3. Look at it

For each changed screen:
1. **Desktop:** `resize_window {preset: "desktop"}` → `computer {action: "screenshot"}`.
2. **Phone:** `resize_window {preset: "mobile"}` (375×812) → reload → screenshot. Then check there is no sideways scroll: `javascript_tool`: `document.documentElement.scrollWidth <= window.innerWidth`.
3. **Console:** `read_console_messages {onlyErrors: true}` must be empty of new errors. With the real backend, also check `read_network_requests` for 4xx/5xx.
4. **Text:** `get_page_text` and skim it for banned words (the `anveshan-ux` §3 table). This is faster than squinting at screenshots.
5. **Finish:** `resize_window {preset: "desktop"}` when done.

The app is dark-only; there is no light mode to check.

## 4. Automated scans

These exist once K9-P7 is merged (check `app/package.json` scripts):

```bash
npm --prefix app run check:plain
```

- **check:plain** scans every main view for banned learner terms. It needs the app running (default URL is mock :5174, override with `ANVESHAN_URL`).
- **check:roles** walks creator → steward → learner with two visitors. It needs the service with `ANVESHAN_STEWARD_TOKEN=local-test-code`.
- **Self-test:** `node app/scripts/check_plain_language.mjs --self-test`.

Always also run:

```bash
npm --prefix app run build
```

```bash
npm --prefix app run build:mock
```

## 5. Share proof

- Give the user one screenshot per changed screen (desktop, plus phone when layout changed), labelled with role and view.
- State the check results: build ok, console clean, check:plain pass or the findings, 375 px pass.
- For a visible change, show before and after: take the "before" screenshot first.

## 6. Coordination while Kiro is running

- **Status:** the K9 build runs in `.worktrees/` on `kiro/k9-*` branches. Before touching a file, check `.kiro/k9-run/STATUS.md` and the ownership table in `docs/kiro/specs/K9-ORCHESTRATOR.md` §5.
- **If the file is owned by a running task:** prefer an `INSTRUCTION` entry in `.kiro/k9-run/INBOX.md` addressed to that task.
- **If you change it on `main` anyway:** commit, push, and add a `CHANGED-ON-MAIN` inbox entry with the commit, files and intent, so the integrator merges it rather than overwriting it.
