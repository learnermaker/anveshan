---
inclusion: always
---

Token tools for coding agents: [docs/architecture/agent-tools.md](../../docs/architecture/agent-tools.md).

- Kiro has no RTK hook. If `rtk` is on PATH, prefix commands with long output with it: `rtk git status`, `rtk git diff`, `rtk pytest …`, `rtk npm run build`. Run without `rtk` when you need the full output of a failure.
- After editing code, run `graphify update .` (AST only, no API cost) so the graph in `graphify-out/` stays current.
