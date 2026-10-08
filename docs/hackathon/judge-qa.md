# Judge Q&A

## What is Anveshan?

Anveshan helps one person pass a real piece of expertise to another.

It turns an authentic expert demonstration into source-grounded teaching, observes the learner's attempt, provides evidence-linked feedback, and records whether transmission occurred.

## Isn't this just an AI tutor?

No. The starting point is not generic model knowledge.

The teaching experience is grounded in an authentic expert's demonstration, the learner performs a related task, and the system evaluates the transmission against source evidence or an explicit rubric.

## Isn't this just RAG?

No.

RAG can ground answers. Anveshan adds the human transmission loop:

**source → teaching → attempt → verification → improvement → lineage**

## Isn't tacit-knowledge extraction already solved?

No single technology solves it generally, and existing products already capture substantial expert knowledge.

We therefore do not claim that extraction itself is novel. Our hypothesis is that source-grounded extraction becomes more valuable when connected to learner practice and measurable transmission.

## What prevents hallucination?

The system distinguishes:

- source statement;
- observed evidence;
- AI interpretation;
- community interpretation;
- unknown.

Important claims retain source evidence and timestamps. When evidence is insufficient, the system should say so rather than invent.

## What happens when experts disagree?

We preserve variants and contradictions rather than silently selecting one as universal truth.

## Why video?

Some expertise is embodied. Video can preserve action, sequence, timing, tool interaction, and visible cues that a transcript cannot.

Gemini's current video capabilities support timestamp-grounded questions and multimodal video analysis.

## Why Google Cloud?

The current prototype can use Gemini multimodal capabilities, Gemini 3.5 Transcribe, Gemini Embedding 2, ADK, and Cloud Run.

The architecture is designed so each Google capability performs a visible product function rather than being included for branding.

## What is the hard technical problem?

Connecting:

multimodal source understanding → structured knowledge → evidence retrieval → adaptive teaching → learner-attempt analysis → evidence-grounded feedback → measurable transmission → lineage.

## What is the metric?

The candidate flagship metric is Transmission Gain:

**post-transmission learner performance − baseline performance**

The score must use a skill-specific rubric and be validated against expert assessment.

## What if the AI cannot judge the learner reliably?

It should not pretend to.

The system marks uncertain observations and can request another observation or route the case to human review.

## What is the long-term opportunity?

The same transmission architecture could support community knowledge, skilled trades, cultural practices, agriculture, professional expertise, and enterprise continuity.

The hackathon prototype only needs to prove one complete transmission loop.

---

## Hard questions from a sceptical judge

### 1. "Isn't this a Gemini wrapper?"

No. Gemini perceives the source and the learner's attempt; it also words the coaching tip. But the pass/fail decision on each check is made by deterministic rules, not by a model. The skill model — steps, checks, rubric — is structured by Gemini once and then evaluated by code on every subsequent attempt. The architecture is designed so the most trust-sensitive step (scoring) is the one that needs no model call at all.

### 2. "How do you know the feedback is correct?"

Each feedback item comes from a check that failed. The check compares a specific measurable property of the learner's attempt to a threshold from the goal model. The goal model is grounded in the source evidence. Gemini words the tip, but the tip cites the source moment that the fixed rules identified. If the rubric is wrong, the feedback will be wrong — and we say that plainly. What we do not do is ask a model to invent a verdict.

### 3. "Why not just YouTube?"

YouTube shows the skill. It cannot see what your hands did. A YouTube video never looks back at the learner's attempt, finds the first place they went off track, and points to the source moment that shows what to change. Anveshan closes that loop. The key step is not the demonstration — it is the observation of the attempt and the evidence-grounded response to it.

### 4. "What about pressure and touch?"

A phone camera or microphone cannot sense force, pressure, torque or texture. The app says this plainly rather than guessing. Criteria that require sensing pressure are marked as not assessable in the current version. This is a known limit, documented in the app and in the codebase. It is not a gap we claim to fill.

### 5. "Who are the experts?"

For the current prototype, the hero skill (Kolam) uses source media from Wikimedia Commons under open licences. The photographer or uploader is not a verified Anveshan expert — the app labels this as "INTERNET REFERENCE". The skill model was proposed by Gemini and confirmed by the development team; it has not been reviewed by a Kolam practitioner. [VERIFY: update this answer if an expert review is completed before submission]

### 6. "Does it scale beyond 3 skills?"

The creator flow generalises to any skill with a physical result that a camera or microphone can observe. The goal model, checks and rubric are generated from the uploaded source; the creator confirms them. Adding a new skill requires no code change. Three more cases are included in the prototype (origami, origami crane, tabla). The limit is the quality of the uploaded source, not the architecture.

### 7. "What does it cost per learner?"

For Kolam and Tabla, scoring uses zero model calls (deterministic geometry and onset detection). For skills that use the universal pipeline, each attempt evaluation uses one Gemini call for perception. Identical uploads replay from golden runs at zero cost. Details are in `docs/architecture/token-economy.md`. A rough order of magnitude: at gemini-3.5-flash-lite pricing, a perception call with a few frames costs fractions of a US cent. [VERIFY: add a specific cost figure from token_report.py before submission]

### 8. "Is it synthetic data?"

The hero case (Kolam) uses real source media from Wikimedia Commons, not synthetic data. Three of the seven case packs include synthetic showcase cases labelled "synthetic" in the UI. The test suite uses sample attempts that are either recorded real attempts or labelled synthetic. No synthetic content is passed off as real. The `not_yet` field in `evidence.json` states this explicitly.

### 9. "What is your evidence that it works?"

The current evidence is engineering evidence only: 566 non-live tests; 100% consistency on Kolam and Tabla across 3 runs per sample type (good/flawed/unrelated); 89% consistency on origami crane. No study with real learners or experts has been run yet. The test suite shows the system behaves as designed; it does not show that learners improve or that experts endorse the skill models. We say this plainly. [VERIFY: update with pilot results if available before submission]

### 10. "Why not an existing enterprise tool like DeepHow?"

Industrial physical-AI tools target enterprise procedures, require specialist hardware or setup, and are not designed for individual practitioners or learners with ordinary phones. Anveshan is for anyone with a craft and a phone, keeps the creator's credit and consent, and measures whether the skill transferred. The positioning is different, not just the price point.

### 11. "How is this different from Khan Academy or Duolingo?"

Khan Academy and Duolingo teach through structured content and repetition. Neither observes what the learner physically did. They cannot look at a photo of your Kolam and tell you which dot is misaligned relative to the source. The gap Anveshan fills is not explanation or practice — it is the observation and measurement of a physical attempt against a specific, grounded rubric.

### 12. "What if the source media is wrong or the creator is not actually an expert?"

The system does not verify the creator's credentials. It grades attempts against the skill model, not against an absolute standard of truth. If the source is wrong, the feedback will be wrong — and the creator takes responsibility for what they publish. The steward role exists precisely to review the skill model and its source before it is made available to learners. This is a governance design, not a technical safeguard.
