---
name: anveshan-verify
description: Run Anveshan's full local verification suite (governance, case packs, contract parity, all Python tests, benchmark smoke tests, frontend build, PR-body contract) before committing or opening a PR. Use whenever code, contracts, case packs, or docs governed by CI change.
---

# Anveshan verification (Antigravity entry point)

This skill is shared by every coding agent in this repository. Its single source of truth is
`.claude/skills/anveshan-verify/SKILL.md`: **read that file now and follow it completely.**

This wrapper exists only so Antigravity can discover the skill. Do not copy rules into it; edit the source file instead.

**In Antigravity:** run the commands in a terminal from the repo root with `.venv/Scripts/python`.
