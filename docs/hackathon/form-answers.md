# Submission form answers

**Competition:** Google Cloud AI Builder Cup 2026
**Portal:** https://hack2skill.com/event/aibuildercup2026/registration
**Deadline:** 18 Oct 2026 (timezone unconfirmed; assume 23:59 IST) [VERIFY before submission]
**Theme:** Sustainability & Social Impact

---

## Standard submission fields

### Project name
Anveshan

### Tagline (one line)
The skill transfers. The evidence stays.

### Theme / category
Sustainability & Social Impact

### Team name
[VERIFY: add team name]

### Team members
[VERIFY: add names, roles, and confirmation that all are 21+ working professionals in JAPAC]

### GitHub repository
[VERIFY: confirm repository is public before submission; current repo is private]

### Live demo URL (Cloud Run)
[VERIFY: add Cloud Run deployment URL]

### Video URL (public YouTube, Vimeo or Google Drive, ≤ 3 minutes)
[VERIFY: add video URL after recording]

### Deck / presentation (PDF)
[VERIFY: export docs/hackathon/deck.md as PDF before submission]

---

## Problem statement (≤ 150 words)

Skills of the physical world — folding, drawing, drumming, repairing — are passed on through demonstration and correction. When a practitioner is no longer available, the skill degrades with each retelling because no verified transmission record exists.

Text and video courses can show a skill. They cannot see what the learner's hands did. A chat tutor can answer questions. It cannot observe the result of your attempt.

Anveshan addresses the gap between showing and verifying: a creator uploads a real demonstration; the system structures what the expert knows; when a learner submits a photo or video of their own attempt, deterministic checks compare it to the goal model; and a Gemini-worded tip points back to the exact moment in the source that shows what to change. The retry is checked the same way and the change is recorded.

---

## Solution description (≤ 150 words)

Anveshan is a web app that runs a complete skill transmission event: from real source capture through to a measurable learner improvement, with every claim grounded in source evidence.

A creator uploads a real demonstration (photo, video or audio). Gemini structures the skill into steps, checks and a rubric. When a learner submits their attempt, deterministic rules score each check — no model decides pass or fail. The first place the attempt diverged from the model is found; Gemini words a tip citing the source moment. On the retry, the same checks run and the delta is recorded.

The system runs on Cloud Run. Recorded mode replays golden responses deterministically, so the demo needs no live API call. The skill model generalises to any skill with a physical result: Kolam drawing, tabla percussion, paper-folding, and more.

---

## Gen AI use (≤ 150 words)

Gemini 3.5 Flash Lite perceives the creator's demonstration (frames and audio) and proposes the skill model. Gemini Embedding 2 aligns source claims to source moments. When a learner submits an attempt, Gemini 3.5 Flash Lite perceives it. Fixed deterministic rules then score each check against the goal model; Gemini is not asked to pass or fail anything. When a check fails, Gemini 3.5 Flash Lite words the feedback tip, citing the source moment that the fixed rules identified. [VERIFY: confirm production model names match evidence.json and token-economy.md]

This architecture is not a thin wrapper. Each model call has a defined job. The most frequent operation — scoring — costs zero model calls for Kolam and Tabla (deterministic geometry and onset detection). Identical uploads are answered from stored golden runs.

---

## Google Cloud services used (≤ 150 words)

- **Cloud Run:** hosts the FastAPI service (`anveshan_service`). The React frontend is served as static files from the same Cloud Run instance.
- **Gemini 3.5 Flash Lite:** perception of uploaded demonstrations and learner attempts (frames and audio). Wording of coaching tips from fixed-rules feedback. [VERIFY: confirm model name and availability at submission time]
- **Gemini Embedding 2:** source alignment — embedding source claims and learner observations for retrieval.
- **Model Gateway (tracks/common/models.py):** daily call budget, recorded-run replay, media resolution matching, output cap, temperature-0 JSON mode.

No other Google Cloud services are used in the current prototype. The architecture is designed so that each Google capability performs a visible product function rather than being included for stack completeness.

---

## Innovation and creativity (≤ 150 words)

The novelty is not a single model capability. It is the integration of source fidelity, observable verification and measurable transfer in one product unit: the transmission event.

Existing tools each do part of this. Expert interview tools capture knowledge. Video courses show skills. AI tutors answer questions. Feedback tools assess attempts. No current product connects expert source → structured knowledge → learner attempt → evidence-grounded feedback → measured retry → lineage in a single auditable record.

Our prototype combines these capabilities around a measurable human-to-human transmission event, and preserves the source and lineage across that event.

What makes it creative in its use of Gen AI: Gemini is used for perception and language, while the trust-sensitive judgment (pass/fail) is deterministic. This is a deliberate design choice, not a gap.

---

## Impact (≤ 150 words)

Heritage craft knowledge, skilled trades and traditional practices live in practitioners' hands, not in any text archive. When a practitioner is gone, so is their capacity to correct the learner.

Anveshan is made for anyone with a phone and a craft. The learner needs no studio, sensor or special equipment. The creator needs no teaching qualification — they upload what they know and confirm what the system proposes.

Three potential impact areas:
1. Heritage: craft knowledge can be structured, taught and verified before practitioners are gone.
2. Livelihoods: creators can publish a verifiable skill model, see learner outcomes and receive recognition.
3. Access: feedback grounded in the source is available to any learner anywhere, in any language the tip can be worded in.

No user study has been run yet. The current evidence is engineering-only. [VERIFY: add pilot results if available before submission]

---

## Technical challenges (≤ 150 words)

The hard problem is grounding every feedback claim in the source. A model that answers from general knowledge cannot satisfy the requirement that each tip points to a specific source moment.

Our approach: build a goal model from the source (steps, checks, rubric, with source-grounded claims). Score learner attempts against the goal model with deterministic rules. Ask Gemini to word the tip only after the fixed rules have decided what failed and where.

Known remaining challenges:
- Step identity varies between live runs for low-resolution hand-held footage (global embeddings separate scenes, not fine-grained object states).
- An attempt visually similar to the source but unrelated can land in the ambiguous relevance band and fail instead of being refused.
- Crop to the work region is not yet implemented for real hand-held footage.

These are documented in `docs/plans/universal-pipeline.md` §12.3.

---

## What is next (≤ 150 words)

Three next steps, in priority order:

1. Real expert and learner study: run a pilot with a Kolam practitioner and 10 learners; measure Transmission Gain (post-transmission learner performance minus baseline performance) as the primary metric.

2. Expert review of the extracted knowledge: have the Kolam practitioner confirm or correct the skill model that Gemini proposed.

3. More skills: the creator flow generalises to any skill with a physical result. Three more cases are ready (origami, origami crane, tabla). Additional cases can be added by anyone with a phone.

Longer term, the transmission architecture could support community knowledge, skilled trades, cultural practices, agriculture, professional expertise and enterprise continuity. That is the product vision; the hackathon prototype proves one complete transmission loop.

---

## Links

- GitHub: [VERIFY: add public repo URL]
- Live demo: [VERIFY: add Cloud Run URL]
- Video: [VERIFY: add video URL]
- Deck (PDF): [VERIFY: attach PDF]

---

## Pre-submission checklist (from submission-checklist.md)

- [ ] Confirm all team members are 21+ working professionals in JAPAC [VERIFY]
- [ ] Confirm project was started on or after 7 Sep 2026 (fresh code requirement) [VERIFY]
- [ ] Repository is public [VERIFY]
- [ ] Cloud Run URL is live and accessible [VERIFY]
- [ ] Video is public, under 3 minutes, on YouTube/Vimeo/Google Drive [VERIFY]
- [ ] Deck is exported as PDF [VERIFY]
- [ ] All `[VERIFY]` markers in this file are resolved [VERIFY]
- [ ] Submission deadline timezone confirmed with Hack2skill [VERIFY]
