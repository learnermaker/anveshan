---
trigger: glob
globs: "app/**"
description: "Anveshan UI rules: three roles, plain language, honesty labels, accessibility, visual verification"
---

# Anveshan UI work

You are changing the Anveshan app UI. Before designing or editing, read and follow these three files:

1. `.claude/skills/anveshan-ux/SKILL.md`: who each screen is for; what learners and creators must never see (claim IDs, confidence, run classes, provenance, approve/reject); the plain-language copy table; honesty labels via `trustLine()`; one primary action per screen; the visual tokens.
2. `.claude/skills/anveshan-a11y/SKILL.md`: the accessibility checklist (text size, contrast, aria, dialogs, focus, 375 px).
3. `.claude/skills/anveshan-ui-check/SKILL.md`: how to prove a change works. Use the browser at phone and desktop widths, a clean console, `check:plain`, and both builds.

**Product source of truth:** `docs/kiro/specs/K9-00-PRODUCT-UX.md` (it wins over the skills and over `DESIGN.md` §4 on any conflict).

**Parallel work:** a Kiro build may be running on `kiro/k9-*` branches. Before editing a file, check `.kiro/k9-run/STATUS.md` and the ownership table in `docs/kiro/specs/K9-ORCHESTRATOR.md` §5. If a running task owns the file, add an `INSTRUCTION` to `.kiro/k9-run/INBOX.md` instead of editing it, or commit on `main` and add a `CHANGED-ON-MAIN` entry.
