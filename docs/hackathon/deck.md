# Deck content — Google Cloud AI Builder Cup 2026

**11 slides. Convert to PDF before submission.**

---

## Slide 1 — Title

**Title:** Anveshan

**Tagline:** The skill transfers. The evidence stays.

**Speaker note:** Open with the one-liner. Don't explain the name. The first slide earns 10 seconds of attention; use them.

---

## Slide 2 — The problem

**Title:** Skills of the physical world are being lost

**Bullets:**
- Folding, drawing, drumming, repairing: skills done with hands, body and sound
- Text and video courses can show the skill — they cannot see what your hands did
- When a practitioner is gone, so is the knowledge of how they corrected the learner

**Speaker note:** Ground this in a real example immediately: a Kolam artist who learned from her grandmother. Resist population statistics — one real example is more credible than a market-size claim.

---

## Slide 3 — The insight

**Title:** A skill only moves when it can be verified

**Bullets:**
- Showing is not teaching; teaching is not confirmed until the learner's attempt is observed
- Feedback is only honest if it points back to the source, not to a model's general knowledge
- Transfer is only real if the change is measured on the retry

**Speaker note:** This is the product insight that justifies everything else. The insight is not "AI can perceive video" — that's the tool. The insight is that grounding feedback in the actual source moment is what makes it trustworthy.

---

## Slide 4 — The demo in 3 images

**Title:** One transmission event

**Bullets:**
- Source: a paper-crane video from Wikimedia Commons (CC BY 3.0); Gemini proposes 9 folding steps, each pinned to a moment
- Attempt: a video that stops after the first folds scores 2.5 of 11; the result shows where it first went off track, beside the matching moment in the source
- Retry: the full fold, checked by the same rules, scores 10 of 11 (Kolam: 6.5 then 10 of 10)

**Speaker note:** Show the three screenshots side by side. Let the images do the work. Don't narrate what is already visible.

---

## Slide 5 — How it works

**Title:** The architecture in one diagram

**[Embed the AR-02-judge-architecture.mmd diagram here as an image or paste the Mermaid block]**

**Bullets:**
- Creator uploads a real demonstration; Gemini structures the skill model
- Learner submits an attempt; fixed rules score each check — no model judges
- Gemini words the feedback tip, citing the exact source moment

**Speaker note:** Walk the diagram left to right. Pause on "fixed rules score" — that is the trust anchor. The judge will want to know this.

---

## Slide 6 — How Gemini is used

**Title:** Gemini does specific jobs; it does not judge

| Job | Model |
|---|---|
| Perceiving the source (frames, audio) | Gemini 3.5 Flash Lite [VERIFY] |
| Structuring steps and rubric | Gemini 3.5 Flash Lite [VERIFY] |
| Perceiving the learner's attempt | Gemini 3.5 Flash Lite [VERIFY] |
| Wording the coaching tip | Gemini 3.5 Flash Lite [VERIFY] |
| Source alignment embeddings | Gemini Embedding 2 |
| Scoring pass/fail | **No model — fixed deterministic rules** |

**Speaker note:** The judge will ask "how do you know the feedback is correct?" The answer is: scoring is deterministic. Gemini only words what the fixed rules already decided. This slide earns the Technical Merit score.

---

## Slide 7 — What is new

**Title:** The transmission event as a product unit

**Bullets:**
- Source fidelity: every teaching claim links to a specific source moment (timestamp or region)
- Observable verification: the learner's attempt is assessed against the goal model, not generic AI knowledge
- Measured transfer: the retry runs the same checks; the delta is the evidence that knowledge moved

**Speaker note:** Frame this against the competitors named in the positioning: "Chat tutors explain a skill but cannot see your hands. Video courses show the skill but never look back at your attempt." Say it once, move on. No superlatives.

---

## Slide 8 — Evidence

**Title:** Engineering evidence (no user study yet)

**Bullets:**
- 566 non-live tests as of 2026-10-07 (`pytest -m "not live"`)
- Kolam and Tabla: 100% consistency across 3 runs per sample (good/flawed/unrelated)
- Origami crane (video, Gemini perception): 100% consistency across 3 live runs per sample (good passed, flawed caught, unrelated refused); source: `app/public/evidence.json`
- Expert and learner study: not yet run [VERIFY: add pilot results if available before submission]

**Speaker note:** Be honest. "No user study yet" is a strength if said plainly — judges can tell when evidence is fabricated. Label what is synthetic, label what is engineering-only. The rubric works. The study is next.

---

## Slide 9 — Impact and sustainability

**Title:** Made for anyone with a phone and a craft

**Bullets:**
- Heritage: craft knowledge that lives in practitioners' hands can be structured, taught and verified
- Livelihoods: creators can publish a verifiable skill model and see learner outcomes
- Access: any phone camera; no sensors, no studio, no special equipment

**Speaker note:** Connect to the "Sustainability & Social Impact" theme. Don't quantify impact you haven't measured. "Could reach" is not evidence; "this is who it is made for" is.

---

## Slide 10 — Scale and cost

**Title:** Designed to be cheap to run

**Bullets:**
- Recorded runs: identical uploads are answered from stored golden runs at zero model cost
- Media resolution matching: video frames sent at the right resolution level (70 tokens/frame at low)
- No server key: samples and examples replay committed results; a visitor's own uploads run on their own Gemini key
- Kolam and Tabla scoring: zero model calls (deterministic geometry and onset detection)

**Speaker note:** Cite `docs/architecture/token-economy.md` for detail. The key point for judges: the architecture limits cost by design, not by accident. Scoring is the most frequent operation and it costs nothing.

---

## Slide 11 — What is next and the team

**Title:** Next and team

**Bullets:**
- Real expert and learner study: run a pilot with a Kolam practitioner and 10 learners; measure Transmission Gain
- More skills: the creator flow generalises to any skill with a physical result; three more cases are ready
- Deployment: Cloud Run, public repo, three-minute video — all ready for the Oct 18 submission

**Team:** [VERIFY: add team names and roles]

**Speaker note:** End on the one-liner: "Anveshan passes on skills of the physical world from one person to another: learned from a real demonstration, practised with real hands, and checked against a recording of the learner's real attempt."
