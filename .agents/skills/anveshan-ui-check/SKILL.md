---
name: anveshan-ui-check
description: Visual verification loop for Anveshan UI changes. Start the app, walk the affected role paths, take screenshots at phone and desktop widths, check the console, run the plain-language and role scans, and share before/after proof. Use after any change under app/src that is visible in the browser, and before committing UI work (especially while a Kiro run is merging in parallel).
---

# Anveshan UI check (Antigravity entry point)

This skill is shared by every coding agent in this repository. Its single source of truth is
`.claude/skills/anveshan-ui-check/SKILL.md`: **read that file now and follow it completely.**

This wrapper exists only so Antigravity can discover the skill. Do not copy rules into it; edit the source file instead.

**In Antigravity:** use its browser agent for the preview, screenshot, 375 px and console steps. The Claude-specific tool names (`preview_start`, `resize_window`) map to: start `npm --prefix app run dev:mock` (or the service plus `npm --prefix app run dev`), open the URL, set the viewport and capture. The commands and the pass criteria are identical.
