---
inclusion: fileMatch
fileMatchPattern: "app/**"
---

# Anveshan UI work: read the UI skills

When you change anything under `app/`, follow these three files. They live in the main folder (`C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\`). Worktrees created before 2026-10-07 may not contain them, so read them from the main folder by absolute path:

- `.claude/skills/anveshan-ux/SKILL.md`: who the screen is for, what each role may see, the plain-language copy table, honesty labels and the visual language. It is a summary of `docs/kiro/specs/K9-00-PRODUCT-UX.md`, which wins on conflict.
- `.claude/skills/anveshan-a11y/SKILL.md`: the accessibility checklist, with grep commands.
- `.claude/skills/anveshan-ui-check/SKILL.md`: how to verify a UI change. Use the scripted parts: builds, `check:plain`, the 375 px check.

These do not change your task's file ownership, scope or acceptance criteria (see `k9-run-rules.md`). Apply them inside the files you own.
