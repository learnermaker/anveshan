# K10 sprint: 6 hours to the development freeze, aiming for first prize

**Read this first.** It overrides `K10-REVIEW.md` wherever they differ. `K10-REVIEW.md` stays the reference for *how* to observe:
- §2 rules;
- §3 setup;
- §4 observation format, viewports, screenshots, key ideas K1–K9;
- §6 walk details;
- §7 static checks.

**Situation.** Development freezes 6 hours after launch (T+6:00). After the freeze, only the deploy, the video and the deck. The goal is first prize. Kiro is a trusted team member running three tracks in parallel. Claude Code works on `main` at the same time and is the integrator and decision-maker.

```
T+0:00 setup ─┬─ A review (browser):   W8 → W1 → W2 → W4+W5 → W7-lite → compile         (ends ≈ T+3:30)
              ├─ B submission (docs):  pitch → README top → diagram → video script → deck → form answers → Q&A (ends ≈ T+4:30)
              └─ C fixes (code):       S3 + S1-lite → then the fix loop on INBOX instructions until FREEZE
T+5:30 freeze (Claude writes freeze.json) → final gate: rebuild main, restart, smoke, W8 re-run (ends ≈ T+6:00)
```

## 0. For Jim: how to start

1. Pull `main` and open the repo folder in Kiro. You need Workflows on, Claude Sonnet 4.6, and the playwright MCP enabled.
2. Paste this into a new chat:

> Run the K10 sprint. Read `docs/kiro/specs/K10-SPRINT.md` fully, then `docs/kiro/specs/K10-REVIEW.md` §2–§4, and `.kiro/steering/k9-run-rules.md`. The sprint overrides K10-REVIEW. Validate `.kiro/workflows/k10-sprint.workflow.yaml` with validate_workflow. If an agent name is unknown, swap it as in `K9-ORCHESTRATOR.md` §5.6. Launch `k10-sprint` with no inputs. Stay in this chat as the orchestrator. Every 15 minutes, read `.kiro/k10-run/STATUS.md`, `HOT.md` and `INBOX.md`, and pass new inbox entries to the affected track. Answer questions with `K10-REVIEW.md` §9. Never wait on me unless a human is truly needed. Track C must keep looping until `.kiro/k10-run/freeze.json` says FREEZE.

## 1. Shared rules for the sprint

1. **Time boxes are hard.** When a box ends, write what you have, mark the item `DONE (partial)`, and move on. Never let one item eat the next one's time.
2. **Stream the important findings.** The moment you see an S0 or S1, append it to `.kiro/k10-run/HOT.md` in the `K10-REVIEW.md` §4.1 block format. Write it to your `obs` file as well. Claude Code watches `HOT.md` and starts fixing immediately; nothing waits for the final report.
3. **Ownership.** Each track writes only its own files. Nobody edits `main`'s working tree except Claude Code.

   | Track | Files it may write |
   |---|---|
   | A | `.kiro/k10-run/` only, observe only |
   | B | branch `kiro/k10-submission`, worktree `.worktrees/k10-submission`. Only: `README.md`, `docs/hackathon/*.md`, `docs/diagrams/AR-02-*.mmd` |
   | C | branch `kiro/k10-fixes`, worktree `.worktrees/k10-fixes`. Only the files named in each instruction |

4. **Push after every item** (B and C): `git push -u origin <branch>`. Claude Code merges the branches into `main` about once an hour. Before each item, run `git fetch origin` and `git merge origin/main --no-edit`. If the merge conflicts, run `git merge --abort` and write the conflict to `HOT.md`. Don't resolve it yourself.
5. **Live AI budget:** 40 calls in total, all tracks together, logged in `live-calls.md`.
6. Everything else in `K10-REVIEW.md` §2 still applies. That includes: never type a key, never read `.env`, the steward code is `local-test-code`, and uploads come only from the §6.6 files.

## 2. Setup (step `setup`, ≤ 20 min)

Do `K10-REVIEW.md` §3, then:
1. Create `HOT.md` with the header `# K10 hot findings (S0/S1, newest last)`.
2. Create the two worktrees from `origin/main`:
   ```powershell
   git fetch origin
   git worktree add .worktrees/k10-submission -b kiro/k10-submission origin/main
   git worktree add .worktrees/k10-fixes -b kiro/k10-fixes origin/main
   cmd /c mklink /J .worktrees\k10-fixes\app\node_modules C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\app\node_modules
   ```
   If a branch already exists, use `git worktree add <dir> <branch>` and then `git merge origin/main`.
3. In `STATUS.md`, list every item of tracks A, B and C as `TODO`, with its time box.

## 3. Track A: review (browser, sequential; total ≈ 3 h)

| Order | Item | Box | Spec |
|---|---|---|---|
| 1 | **W8** the judge's path: first 60 s, the wow moment, Gen AI visibility, storyboard, reliability | 50 min | K10-REVIEW §6.9 |
| 2 | **W1** learner, desktop, Kolam | 30 min | §6.1 (skip step 7) |
| 3 | **W2** learner, phone, paper crane video | 35 min | §6.2 |
| 4 | **W4 + W5** creator shares a skill, then the steward reviews and publishes it | 50 min | §6.4 steps 1–3 and 6; §6.5 steps 1–3 and 5 |
| 5 | **W7-lite** keyboard walk through the Kolam path; 375 px sweep of every view; deep links `?view=source&case=nope` and `?view=steward` signed out | 25 min | §6.8 steps 1–2; §6.7 step 5 |
| 6 | **compile**: `REPORT.md` per K10-REVIEW §8.2. The four judges and the weighted score (§8.1) go in §6–§7 of the report; there is no separate jury step | 20 min | §8 |

Skip W3 (tabla) and W6, apart from the deep links in W7-lite. Write `obs\W3-skipped.md` with one line saying so.

## 4. Track B: submission materials (docs only, `kiro/k10-submission`; total ≈ 4 h)

**Read first:**
- `docs/product/novelty-boundary.md` (the positioning; use its one line as written);
- `README.md`;
- `docs/hackathon/*.md`, which already contains demo-story, judge-qa, judging-strategy, submission-checklist and ai-builder-cup;
- `docs/kiro/official-rules-2026-10-06.md` (deliverables and judging criteria);
- `app/public/evidence.json` and `docs/validation/` (the only numbers you may quote);
- `docs/architecture/token-economy.md` (models and cost).

**Rules for every file:**
- Claims must be ones the app really does. Mark anything unverified `[VERIFY]`, and Claude Code resolves it.
- Never write "nobody does this", "revolutionary" or any other superlative.
- Never call internet sources experts. Synthetic is labelled synthetic.
- Use plain words, short sentences and no filler.
- Extend existing files in `docs/hackathon/` rather than creating parallel copies (the single-copy rule in `AGENTS.md`).

| Order | Item | Box | Output |
|---|---|---|---|
| B1 | **Pitch texts** | 25 min | `docs/hackathon/pitch.md` |
| B2 | **README top** | 40 min | `README.md` |
| B3 | **Judge architecture diagram** | 30 min | `docs/diagrams/AR-02-judge-architecture.mmd` |
| B4 | **3-minute video script and shot list** | 45 min | `docs/hackathon/demo-story.md` |
| B5 | **Deck content**, 11 slides | 50 min | `docs/hackathon/deck.md` |
| B6 | **Submission form answers** | 25 min | `docs/hackathon/form-answers.md` |
| B7 | **Judge Q&A** | 25 min | `docs/hackathon/judge-qa.md` |

**B1, pitch texts.** Write these in `pitch.md`:
- the one line (as written in the positioning);
- a 25-word, a 50-word and a 150-word description;
- a 10-word tagline;
- three "why it matters" bullets, one each for heritage, livelihoods and access.

**B2, README top.** Rewrite only the part above the first `##` heading, plus one new section "How it works", at most 15 lines. It must contain:
- the one line;
- a `[Live demo](…)` placeholder `[VERIFY: Cloud Run URL]`;
- a screenshot placeholder pointing at `docs/hackathon/img/hero.png` `[VERIFY]`;
- a 3-step "how it works";
- "Built with Gemini on Google Cloud": which models do which jobs (from token-economy.md), and that Cloud Run hosts it;
- the honesty line that scores come from fixed rules;
- a 3-command quick start.

Keep the rest of the README unchanged.

**B3, judge architecture diagram.** A Mermaid flowchart that a judge can read in 20 seconds, with at most 12 nodes:

```
upload (photo / video / audio) → Gemini perceives (frames, audio) → skill model (steps, checks; observed vs AI's reading)
  → creator reviews → learner attempt → Gemini perceives the attempt → fixed rules score the checks
  → first point off track → Gemini words the tip, citing the source moment → retry → measured change + record
```

Show Cloud Run and the model names. Embed the same Mermaid block in the README "How it works" section. That embed is the one allowed copy, because GitHub renders it in place; add a comment at the top of the `.mmd` file naming the README as its mirror.

**B4, video script and shot list.** Rewrite `demo-story.md` as a timed 3-minute script with a table: time, screen, on-screen action, voice-over (one line each), and which judging criterion it serves.
- The beats: the problem by 0:20, the wow by 1:00, Gen AI depth by 2:00, the creator/steward loop and impact by 2:40, the close by 3:00.
- When `obs\W8-storyboard.md` exists (around T+1:00), align to it. Until then, use the app as documented.

**B5, deck content.** Write `deck.md` with 11 slides; each has a title, at most 3 bullets, and a speaker note:
1. title;
2. the problem (skills of the physical world are being lost; text and video can't see your hands);
3. the insight;
4. the demo in 3 images;
5. how it works (B3);
6. how Gemini is used: perception, structuring, wording, and **never** scoring;
7. what's new (K1–K9 from K10-REVIEW §4.5, phrased for judges);
8. evidence (only numbers from `evidence.json` or `docs/validation`, plus `[VERIFY]` for the pilot and the expert review);
9. impact and sustainability;
10. scale and cost (from token-economy.md);
11. what's next and the team `[VERIFY names]`.

**B6, submission form answers.** In `form-answers.md`, answer every field listed in `submission-checklist.md` and the official rules. Answer the typical fields too: problem, solution, Gen AI use, Google Cloud services, impact, innovation, challenges, what's next, links. Keep each answer within any length limit; where none is known, use at most 150 words.

**B7, judge Q&A.** Extend `judge-qa.md` to the 12 hardest questions a sceptical judge would ask, each with an answer of at most 3 sentences. Examples:
- "Isn't this a Gemini wrapper?"
- "How do you know feedback is correct?"
- "Why not just YouTube?"
- "What about pressure and touch?"
- "Who are the experts?"
- "Does it scale beyond 3 skills?"
- "What does it cost per learner?"
- "Is it synthetic data?"

Push after each item. Mark each one `DONE` in `STATUS.md`.

## 5. Track C: fixes (code, `kiro/k10-fixes`; runs until FREEZE)

**C0, fast checks (≤ 45 min).** Run `K10-REVIEW.md` §7 S3, steps 1–4 only, and S1, steps 2–3 only. Run them against the `main` folder's server on 8080; the worktree has no server. Stream S0 and S1 findings to `HOT.md`.

**C-loop (repeat until FREEZE).** Claude Code writes exact fix instructions to `INBOX.md`, addressed `to: FIX`. Each names the files, the change and the acceptance check. In each iteration:
1. Read `INBOX.md`. Take every `to: FIX` entry that you have not yet acknowledged in `obs\FIX.md`, oldest first.
2. Update the worktree: `git fetch origin` then `git merge origin/main --no-edit`.
3. Apply the change, touching **only** the files the instruction names. If an instruction is unclear, apply nothing for it, ask in `HOT.md` under `QUESTION`, and go to the next one.
4. Verify:
   - always: `npm --prefix app run build` (tsc must pass);
   - if the change touches the UI: `npm --prefix app run check:plain`, against the 8080 server; its findings for screens you didn't touch can be ignored;
   - if it touches Python: the pytest command from `K10-REVIEW.md` §7 S3.1.
5. Commit with the message `fix(k10): <IN-id> <summary>` and push. Acknowledge it in `obs\FIX.md` with `IN-n: DONE <sha>` or `IN-n: FAILED <reason>`.
6. If there were no new instructions, wait (`Start-Sleep -Seconds 240`) and end the iteration.

The loop stops when `.kiro/k10-run/freeze.json` contains `{"state": "FREEZE"}`.

## 6. Final gate (step `final-gate`, after the freeze, ≤ 30 min)

1. In the main folder, run `git pull`. Claude Code has merged everything by then. Then rebuild `app/dist`: `npm --prefix app run build`.
2. Restart the service (K10-REVIEW §3.2).
3. Run `tools/smoke_deployed.py` against `http://localhost:8080`.
4. Re-run W8 steps 1, 2 and 5 (the first 60 s, the wow moment, and reliability, twice).
5. Write `obs\GATE.md`, and append a "Freeze gate" section to `REPORT.md`: pass or fail per check, and every regression since the first W8.
6. Call `send_message`: "K10 sprint done: gate PASS/FAIL, N open S0/S1."
