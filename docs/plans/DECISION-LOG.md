# Decision Log — Anveshan Kiro Orchestration

**Orchestrator:** Kiro session (Sonnet 4.6)  
**Start:** 2026-10-06  
**Branch:** m1/hero-cases  
**Deadline:** 2026-10-18

---

## 2026-10-06 — Session start assessment

### State at handoff

| Item | Status | Notes |
|---|---|---|
| m1/hero-cases base | 7f8fb56, 291 tests green | K2 and K3 merged; foundation + universal pipeline schemas present |
| kiro/k1-kolam | COMPLETE | 7 commits ahead of base; K1-REPORT.md in worktree confirms all 5 steps done, 30 tests passing |
| kiro/k4-origami | PARTIAL | 6 commits ahead of base; steps 1-4 done (latency, batching, goal build, golden runs); steps 5-7 missing (synthetic attempts, RESULTS.md, K4-REPORT.md) |
| kiro/wp1-perception | NOT STARTED | at base commit 3507f44 |
| kiro/wp2-universal | NOT STARTED | at base commit 3507f44 |
| kiro/wp3-composer-ui | NOT STARTED | at base commit 3507f44 |
| kiro/wp4-tabla | NOT STARTED | at base commit 3507f44 |

### Decisions made

1. **K1 Phase 0 task scope:** K1 is complete per K1-REPORT.md. The Phase 0 T-K1 task is a verify-only step (run tests, confirm done, output confirmation). No implementation needed.

2. **K4 Phase 0 task scope:** K4 has latency probe done (max 6.5 s for 4 images, well within budget), batching policy implemented, goal build done with golden runs. Remaining: step 5 (synthetic attempts), step 6 (RESULTS.md), step 7 (band adjustments if needed), K4-REPORT.md.

3. **K4 model decision:** Use `gemini-3.5-flash-lite` (ANVESHAN_VIDEO_FRAMES_MODEL=gemini-3.5-flash-lite). K4 already has batching policy with ≤ 4 images/call implemented. Budget remaining: ~89 calls (used ~31 for probe + goal build).

4. **Phase A starts from updated base:** Each WP task runs `git merge --ff-only m1/hero-cases` as its first step (after K1+K4 are merged). This is per master spec §4.1.

5. **Phase A merge order:** WP4 → WP1 → WP2 → WP3 per master spec §5.1. Conflicts resolved by §3 ownership (track_a/api.py: WP1 owns list_cases/to_view, WP2 owns build_case).

6. **Lazy imports in WP2:** Per master spec §7.9, WP2 imports `tracks.common.perceivers` lazily inside functions (not at module level). Tests inject a fake module. Critical non-negotiable.

7. **Live call budgets:** WP1 ≤ 40 calls, WP2 none in Phase A, WP3 none, WP4 ≤ 5, Phase B WP5 ≤ 150.

8. **8 contracts frozen:** Never modify `tracks/common/schemas/`. This is a hard stop.

9. **Hero cases byte-identical:** The golden run artifacts in tracks/cases/{kolam,origami,tabla} must not change. Tests enforce this.

10. **DECISION-LOG.md created:** This file, at docs/plans/DECISION-LOG.md.

---

## Phase 0 — (in progress)

Launched workflow with Phase 0 parallel (K1 verify + K4 finish), followed by Phase 0 merge, then Phase A parallel (WP1-WP4), Phase A merge, and Phase B integration.

---

## Template for future decisions

```
### [date] [decision title]
**Context:** [why this decision was needed]
**Options considered:** [what was considered]
**Decision:** [what was decided]
**Rationale:** [why, citing defaults if applicable]
**Log entry by:** Kiro orchestrator
```

