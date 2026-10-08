# Demo story: 3-minute video script and shot list

**Review checkpoint:** 2026-10-08 (K10 sprint). This file is the authoritative video script.

**Story:** one skill shared from a real video; Gemini turns it into steps; a learner's video attempt is checked against it; the first place it went off track is shown beside the source; the retry is measured.

**Facts it uses:** every number below comes from the committed samples, which replay the same result every time.
- Crane, first try ("stopped after the first folds"): 2.5 of 11.
- Crane, retry ("all the way to the finished crane"): 10 of 11.
- Kolam: 6.5 then 10 of 10.
- Composer, crane video: 9 steps in about 20 s (live Gemini call; record one take).

## Script table

| Time | Screen | On-screen action | Voice-over | Criterion |
|---|---|---|---|---|
| 0:00–0:15 | Home | Headline, then the first-vs-second-try picture | "Folding, drawing, drumming: skills you learn with your hands. A chat tutor can't see your attempt, and a video course never looks back at it." | Problem (25%) |
| 0:15–0:40 | Share a skill → example "Folding a paper crane (video)" | Proposal screen: one frame per step, with its time | "Someone shares a short video. Gemini watches it and proposes the steps, each pinned to a moment in the video. They check it before anyone else sees it." | Gen AI (40%) |
| 0:40–0:55 | Kolam → Learn | "Show me" on stage 6 highlights that region of the source photo | "Every step points back to the source, so a learner can see exactly where it comes from." | Innovation (25%) |
| 0:55–1:25 | Paper crane → Practise → sample "The same video, stopped after the first folds" | Result: where you first went off track; the learner's video cued to 0:15 beside the demonstration | "A learner sends a video of their own hands. Anveshan finds the first moment it went off track: at fifteen seconds the paper is in a state the demonstration never shows." | Innovation (25%) |
| 1:25–1:50 | Same result → "How this result was made" | Hold on the four stages | "Gemini looked at the video and matched each moment to a step. Five checks were scored by fixed rules. Gemini wrote the advice, and a guard rejects any wording that changes a number." | Gen AI (40%) |
| 1:50–2:10 | Retry with "all the way to the finished crane" → Results | The before-and-after comparison | "On the second try, the same checks run again. The change is measured, not declared." | Impact (25%) |
| 2:10–2:35 | Steward console → review queue → publish; My skills | Quick cuts | "A steward reviews a shared skill before it goes public. The creator keeps the credit and sees where learners struggle, without names or recordings." | Impact (25%) |
| 2:35–2:52 | "How we check results" page | Scroll to the stability table | "Every sample gives the same outcome across repeated runs. What a camera can't sense, like pressure, it says it can't." | Technical (40%) |
| 2:52–3:00 | Home | Fade to the one line | "Anveshan. Skills of the physical world, passed on." | Close |

## Recording rules

- Use the deployed Cloud Run URL. Sample attempts replay committed recordings, so they are instant and identical every take. Only the composer step (0:15) calls Gemini live: record it until one take is clean.
- 1080p desktop. Optionally one phone shot (390 px) of the crane result.
- Say only what is on screen. Make no claims about learner studies or expert reviews unless `docs/validation/` records them.
- Avoid dashboards, agent counts, chatbot screens and long architecture narration.

## Judging criterion coverage

| Criterion | Where |
|---|---|
| Technical Merit & Gen AI (40%) | 0:15–0:40 (Gemini turns a video into steps), 1:25–1:50 (what Gemini did vs fixed rules), 2:35–2:52 (repeatability) |
| Problem Alignment & Impact (25%) | 0:00–0:15, 1:50–2:10, 2:10–2:35 |
| Innovation & Creativity (25%) | 0:40–0:55 (source-linked steps), 0:55–1:25 (first divergence beside the source) |
| UX & Solution Design (10%) | the whole learner path, 0:55–2:10 |
