# Demo Story — 3-minute video script and shot list

**Review checkpoint:** 2026-10-08 (K10 sprint)

This file is the authoritative video script. When `obs/W8-storyboard.md` is available, align to it.

---

## Script table

| Time | Screen | On-screen action | Voice-over | Judging criterion |
|---|---|---|---|---|
| 0:00–0:08 | Title card: "Anveshan" | Fade in on the one-liner | "Some skills can only be learned by watching real hands and trying with your own." | Problem / Impact |
| 0:08–0:20 | The Kolam source: a traditional floor art photo from Wikimedia | Zoom slowly into the source image; highlight the geometric pattern | "This Kolam was drawn by a practitioner. It lives in a photo — not a tutorial, not a chatbot answer. The source." | Problem / Impact |
| 0:20–0:35 | Anveshan creator flow: skill model screen | The composed steps appear: symmetry, dot alignment, closure | "Gemini reads the source, proposes the key steps and checks. The creator confirms. The rubric is grounded in the actual image — not in generic drawing advice." | Technical Merit / Gen AI |
| 0:35–1:00 | Learner landing page → Start practising → sample attempt submitted | Click 'Start practising', upload the flawed sample attempt | "A learner opens the app on any phone, submits a photo of their own attempt, and waits — no sensors, no special kit." | UX / Problem Alignment |
| 1:00–1:20 | Feedback screen: criterion list, first failure highlighted | Camera holds on the first failed criterion: "Dot alignment — 4 of 8 reference dots matched" | "Four of eight reference dots are off. **The score came from counting pixels against the goal model — not from a model judgment.** Here is the exact source region it compared against." | Technical Merit (scoring is deterministic) |
| 1:20–1:45 | Feedback detail: source moment panel | The source frame or region slides in beside the attempt | "The tip points back to this region in the source. Gemini worded it; the target moment is fixed. [VERIFY: confirm source-frame panel visible in current UI]" | Technical Merit / Innovation |
| 1:45–2:00 | Retry submission | Learner submits a second attempt (sample 'good') | "The learner adjusts. Same checks, same rubric, fresh measurement." | UX / Problem Alignment |
| 2:00–2:20 | Retry result: improvement shown | The criterion bar moves; 'Dot alignment' now passes; delta shown | "Seven of eight dots now aligned. The change is measured, not declared. This is the transmission event." | Innovation / Impact |
| 2:20–2:40 | Creator dashboard / steward review queue | Quick cuts: creator sees attempt count and pass rate; steward sees queue | "The creator sees whether the skill transferred. A steward can approve, withdraw or update the skill model. Every record carries provenance." | Innovation / Impact |
| 2:40–2:55 | Architecture slide or diagram overlay | AR-02 flowchart animates: source → model → learner → fixed-rules score → tip | "Gemini perceives. Fixed rules judge. Gemini explains. The architecture is not a wrapper — each step has a defined job and the evidence stays." | Technical Merit / Gen AI depth |
| 2:55–3:00 | Closing title | Fade to: "Anveshan. The skill transfers. The evidence stays." | "Anveshan. Made for skills of the physical world." | Closing |

---

## Demo rules (from original brief, unchanged)

- one expert source;
- one skill (Kolam);
- one learner path;
- one non-obvious knowledge moment (dot alignment);
- one learner error;
- one meaningful feedback item;
- one visible improvement;
- one lineage record.

Avoid dashboards, agent-count slides, generic chatbot screens, unsupported impact claims and long architecture narration.

---

## Judging criterion coverage

| Criterion | Where it appears |
|---|---|
| Technical Merit & Gen AI (40%) | 0:20–0:35 (skill model), 1:00–1:20 (deterministic scoring), 1:20–1:45 (source-linked tip), 2:40–2:55 (architecture) |
| Problem Alignment & Impact (25%) | 0:00–0:20 (problem), 0:35–1:00 (learner path), 2:00–2:20 (transmission), 2:20–2:40 (creator+steward) |
| Innovation & Creativity (25%) | 2:00–2:20 (measured transmission), 2:20–2:40 (creator loop), 2:40–2:55 (architecture) |
| UX & Solution Design (10%) | 0:35–1:00 (learner flow), 1:45–2:00 (retry) |

---

## Shot requirements

- The source Kolam image: `tracks/cases/kolam/source/` (Wikimedia Commons, CC-licensed).
- The flawed sample attempt: `tracks/cases/kolam/samples/flawed/`.
- The good sample attempt: `tracks/cases/kolam/samples/good/`.
- Sample attempts replay committed recordings (no live call, same result every time). Only the composer step calls Gemini live; record it once and keep the take.
- Screen recording at 1080p minimum; phone view at 390 px width for mobile shots.
- No voiceover improvisation; use the script word for word except where `[VERIFY]` notes require update.
