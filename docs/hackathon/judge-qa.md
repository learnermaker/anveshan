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

