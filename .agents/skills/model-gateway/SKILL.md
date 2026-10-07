---
name: model-gateway
description: Rules and code patterns for any Gemma/Gemini model call in Anveshan (Track A extraction/query, Track B observation, service). Use before writing or changing code that calls google-genai, chooses a model, builds a prompt, parses model JSON, or records/replays model runs.
---

# Model gateway rules (Antigravity entry point)

This skill is shared by every coding agent in this repository. Its single source of truth is
`.claude/skills/model-gateway/SKILL.md`: **read that file now and follow it completely.**

This wrapper exists only so Antigravity can discover the skill. Do not copy rules into it; edit the source file instead.
