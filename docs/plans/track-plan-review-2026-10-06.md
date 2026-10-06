# Track A / Track B Plan Review and Revised Plan

**Date:** 2026-10-06
**Status:** PROPOSED. Needs human sign-off on the decisions in §8 before anything here becomes NOW scope.
**Submission deadline:** 2026-10-18, 12 calendar days from today.
**Companion specs:** [track-a-spec.md](track-a-spec.md), [track-b-spec.md](track-b-spec.md)

This document does four things:

1. Infers the real requirements for Track A and Track B from the whole repository, not only from the track folders.
2. Reviews the current track plan against those requirements (round 1), proposes a revised plan, then reviews the revised plan again (round 2).
3. Reviews what Amal (`feat/amal-track-a`, PR #40) and Akarsh (`feat/akarsh-track-b`) have built.
4. Points to the two detailed implementation specs.

---

## 0. Verdict in one paragraph

The current track plan is strong on **evidence discipline**: the frozen eight-contract seam, observed vs inferred, deterministic gain, replay vs live, and failure taxonomy are all well specified. It is weak on almost everything needed to **win a demo in 12 days**:

- It never picks which cases are built live.
- It never says how each modality (image, video, audio) is actually observed.
- It has no owner for the backend, deployment, or learner capture in the browser.
- It gives image evidence no way to point at a region.
- It leaves the goal-conditioned "candidate path" without a home.
- It does not connect a rubric criterion back to the expert claim and evidence it verifies.

Both branches inherited these gaps, and the gaps show up as concrete bugs:

- **Track A:** the live Kolam run lost the entire inferred construction path.
- **Track B:** feedback cites unrelated expert evidence chosen round-robin, the model chooses scores, failures fall back silently to Kolam-flavoured mock observations, and its own evaluations fail the shared validator.

The revised plan below keeps the seam frozen. It adds:

- three live **hero cases**, one per modality: Kolam (image), Origami (video) and Tabla (audio);
- modality-specific **hybrid observers**, combining deterministic measurement with Gemini;
- a small set of **case-pack sidecar files** that join Track A to Track B;
- an explicit **Integration owner** for the Cloud Run backend and browser capture.

---

## 1. Inputs considered

| Source | What it contributes to the requirements |
|---|---|
| `AGENTS.md`, `CANONICAL-SOURCES.md`, `NOW.md`, `project.yaml` | Governance, frozen seam, seven-case portfolio, three transmission modes, M1 gate. `project.yaml` still lists domain, skill, expert, learner and rubric as `REFINING`. |
| `product-vision.md`, `product-thesis.md`, `BRD.md` (FR-01…FR-20, NFR-01…09), `user-journeys.md`, `mvp-contract.md` | The 14-point MVP proof, expert review as a mandatory product proof, the evidence query, the teaching step, variants and contradictions, governance. |
| `docs/hackathon/*` | Judging weights: 40% technical / 25% impact / 25% innovation / 10% UX. Cloud Run or Firebase deployment required. 3-minute public video. **Deadline 2026-10-18.** Judge evidence matrix. |
| `docs/governance/*` | Consent scope, access levels, permission checks before model context is built, immutable sources, a provenance hierarchy with 8 evidence states. |
| `docs/validation/*` | Gates 0–7; metrics for fidelity, grounding, timestamp accuracy, evaluation agreement, feedback actionability, uncertainty calibration. **Nothing is validated today** (`findings.md`). |
| `docs/architecture/*` | Three logical responsibilities (Knowledge, Evidence, Transmission); a deterministic list (permissions, scoring, metrics, audit); the case-pack and model-gateway conventions; the Google mapping (Gemini video, Transcribe, Embedding, Cloud Run). |
| `docs/research/source-strategy…`, `multimodal-capability-case-portfolio.md`, `seven-case-data-source-matrix…` | Per-case evidence boundaries (Kolam: image ≠ procedure). The research-source vs shippable-asset distinction. Experiments G1–G4 for goal-conditioned mode. Licensing limits on Ego-Exo4D, EvoStruggle and IIT Bombay Tabla. |
| `tracks/common/*` | The contracts; the cross-contract validator. **Pass semantics: every required criterion must be SATISFIED for `passed = True`.** |
| Track A/B README, CODING-AGENT-GUIDE, SUCCESS-CRITERIA, IMPLEMENTATION-READINESS | The documented plan under review. |
| **The running app** (`app/src`) | What the UI already expects for each case: `FirstDivergenceDetail`, `MicroPracticeChallenge`, `SensoryCueAnnotation`, `uncertainties`, `SourceProvenance`, `WorkspaceSpecification`. **The app has no real learner input at all** (no canvas capture, microphone or upload). Micro-practice is simulated: clicking button 3 passes. `geminiGateway.findFirstDivergence` makes a live call, then returns the fixture labelled `isLive: true`. The browser holds the API key. |
| `feat/amal-track-a`, `feat/akarsh-track-b` | Actual implementation state (§7). |

---

## 2. Inferred requirements

These are what the tracks must deliver for a credible, first-prize-level entry. Each row cites where it comes from. **Bold** rows are missing from, or under-specified in, the current track plan.

| ID | Requirement | Derived from |
|---|---|---|
| R1 | One complete live transmission loop: source → knowledge → evidence → teaching → baseline → evaluation → feedback → retry → gain → record → lineage, running on Cloud Run. | MVP contract §1–14, judging "Does it work?", NFR-09 |
| **R2** | **Live learner capture in the browser for each hero modality: a drawing canvas or photo (image), microphone (audio), recorded video upload (video).** | FR-11, Journey 3; app has no input today |
| **R3** | **A modality-correct evidence locator. Image evidence must point to a region; audio and video to time intervals; derived artifacts such as a stroke trace or onset list must be addressable.** | FR-05, provenance model, CONTRACT-USAGE ("locator semantics may differ") |
| **R4** | **Each rubric criterion is bound to an explicit observation method (deterministic metric, Gemini, or human) and a deterministic status→score policy. The model never authors a score.** | MODEL-GATEWAY ("may not decide … score arithmetic"), system-design §8, Track B guide |
| **R5** | **Criterion ↔ expert claim ↔ expert evidence traceability, so feedback can show the right expert moment or region.** | MVP #10, Track B §7, judge matrix "Where did the knowledge come from?" |
| **R6** | **Goal-conditioned output contains both observed target properties and an explicitly inferred candidate construction path. The path is the teaching content for Kolam.** | Source-strategy §2/§7, G1–G2, Track A guide |
| **R7** | **First divergence is defined for non-temporal evidence (images with no time order) as well as temporal.** | UI `FirstDivergenceDetail`, Track B §20 |
| R8 | Expert review is visible and works: approve, revise or reject claims, stored as a new package version. | UX rule in user-journeys, FR-08, Gate 1 |
| R9 | An evidence query: a hard question returns an answer tied to evidence, or INSUFFICIENT_EVIDENCE. | MVP #5, Gate 2, demo 1:05 |
| **R10** | **A teaching experience between baseline and retry that shows the expert evidence for the failed criterion and a micro-drill. The retry remains the full task so scores stay comparable.** | MVP #6, CONTRACT-USAGE adaptive-retry comparability |
| **R11** | **Honest runtime labels end to end: LIVE, RECORDED-LIVE (replay of a captured live run) and SYNTHETIC replay. No silent fallback from live to mock.** | MODEL-GATEWAY failure behaviour, CONTRACT-USAGE; UI bug above |
| **R12** | **Live runs are recorded (raw model response, prompt hash, model, input sha256) so they can be replayed on stage deterministically.** | Risk register "Demo depends on live model", CASE-DATA §5 |
| **R13** | **Measured AI quality per hero case (small labelled sets) published as validation evidence.** | 40% technical, metrics.md, findings.md (nothing validated) |
| **R14** | **Authentic, owned source media with consent for each hero case. Unattributed or AI-generated assets cannot be the "expert source".** | Gate 0, MVP #1/#3, ethics-and-consent, source strategy |
| R15 | A permission and consent gate: no live processing or public serving of media whose consent or access level does not allow it. | FR-17, access-control "before model context construction" |
| R16 | Variants: when an inferred path and an expert's recorded path both exist, keep both and show the difference. | FR-07, judge "What if experts disagree?" |
| **R17** | **Server-side model access (no key in the browser); one model configuration registry; actual model recorded per run.** | NFR-08, app gateway uses browser key |
| **R18** | **Both tracks importable as Python packages by one backend service. No Windows-only or CLI-only library code.** | Implied by R1 + Cloud Run; branch state |
| R19 | Observability transitions (UNCERTAIN → SATISFIED) are distinguished from skill improvement. | CONTRACT-USAGE, Track B SUCCESS-CRITERIA |
| **R20** | **Latency budget so the live demo stays interactive: image ≤ 10 s, audio ≤ 15 s, video ≤ 60 s with progress shown.** | NFR-07, risk register latency |
| R21 | Canonical case data only in `tracks/cases/`. The UI registry consumes it rather than re-authoring it. No invented people in fixtures. | Case-pack rules, contract single-source rule |

---

## 3. Round 1 — critical review of the current plan

### 3.1 What the plan gets right (keep)

- **Frozen seam plus replay boundary.** Genuine parallelism; both branches built without blocking each other.
- **Evidence discipline:** observed / inferred / unverified, a failure taxonomy, human-review escalation, deterministic gain, and baseline/retry typing.
- **Mode-aware thinking** (forward, goal-conditioned, corrective), including the Kolam image ≠ procedure boundary.
- **Strong anti-hype rules** (replay is not validation; gain is not mastery). Judges reward honesty that survives questioning.

### 3.2 Gaps found

| # | Gap | Evidence | Impact | Fix (in revised plan) |
|---|---|---|---|---|
| G1 | **No case prioritisation or time box.** The plan says "domain not fixed until M0" while NOW says M0 is complete; `project.yaml` still says `REFINING` with 12 days left. | NOW.md vs project.yaml; ai-builder-cup.md timeline | Effort is spread over seven cases; nothing becomes deep enough to win. | Lock three live hero cases by modality, with the four others kept as replay showcase (§4.1). |
| G2 | **Modality-blind observation.** "Gemini may observe" is the only observation strategy. Nothing covers geometry for images, onset timing for audio, or sequence alignment for video. | Track B guide; observer.py sends audio as image/jpeg | Weak technical merit, non-deterministic scores, poor accuracy on fine timing. | Hybrid observers: deterministic metrics where measurable, Gemini for semantics (§4.3). |
| G3 | **No spatial locator** for image evidence. EvidenceRef carries only `start_sec` / `end_sec`. | schemas/evidence.py; Track A writes `0.0–0.0` for images | Kolam claims and divergences cannot point at a region; the UI cannot highlight it. | Locator convention: W3C Media-Fragment suffix on `source_id` (`#xywh=…`), plus `#stroke=` and `#onset=`. No contract change (§4.4). |
| G4 | **Criterion → observation-method binding missing.** | rubric.py has no method field | The model decides the score; Track B cannot know which observer to run. | `practice/observers.vN.json` (case data owned by Track B) (§4.5). |
| G5 | **Criterion → claim → expert-evidence link missing.** | Only a `[source_claim_id: …]` text hack in Track A descriptions | Feedback cannot cite the right expert moment; Track B picks round-robin. | `knowledge/criterion_map.vN.json` (case data owned by Track A) (§4.5). |
| G6 | **Goal-conditioned candidate path has no home.** | DTO and Gemini schema have no field for it | Kolam teaching content is lost (confirmed on the live run). | Inferred `STEP` claims (confidence ≤ 0.5, region evidence), plus `order_index` in the criterion map. |
| G7 | **Corrective mode is owned by both tracks.** Track A's guide says "learner attempt → divergence"; Track B owns evaluation. | Track A guide vs Track B README; Track A puts learner divergences into the KnowledgePackage | Learner errors pollute the expert knowledge; duplicate logic. | Track B owns divergence detection; Track A supplies failure modes, cues and reference evidence. |
| G8 | **First divergence undefined for images.** | UI expects time or step | The Kolam first-divergence UX cannot be driven by data. | Deterministic ordering rule (§4.6). |
| G9 | **Teaching step and evidence query have no owner or output.** | MVP #5/#6; PracticeTask instructions are generic in the branch | Demo 1:05–1:45 cannot be produced live. | Track A owns structured instructions, reference moments and the query API; Integration renders them. |
| G10 | **No backend, deployment or capture owner.** Tracks are Python libraries; the app is browser-only and simulated. | No service directory; app has no inputs | The submission requirement (Cloud Run working prototype) is unmet. | Integration workstream (Jim): FastAPI on Cloud Run, browser capture, app wiring (§4.2, §4.7). |
| G11 | **Packages are not importable together.** Track A uses flat `from case_registry import`; Track B uses `from src.observer`. | Branch code | A single service cannot import both. | Packages `track_a` and `track_b` under each track's `src/`. |
| G12 | **Live runs are not recorded or replayable.** | Track A runs go to a gitignored folder; no raw responses saved anywhere | Stage risk; no evidence trail. | Golden-run recording plus a replay adapter that re-runs the real normaliser. |
| G13 | **No AI accuracy measurement plan tied to the tracks.** | metrics.md exists but is not wired in; findings.md "Validated: None" | Loses the strongest technical-merit argument. | Small labelled eval sets per hero case, with metrics recorded as experiments (§4.8). |
| G14 | **Authentic sources and consent are not scheduled.** Every pack is synthetic, and `kolam.png` has unknown provenance. | Case manifests; Track A branch README | Gate 0 fails; the judge question "where did knowledge come from?" has no answer. | Owned recordings plus a consent record for each hero case (dates in §6). |
| G15 | **Rubric quality is unplanned.** Auto-synthesis gives one criterion per claim. | Track A task_generator.py | Rubrics are not observable or diagnostic, so feedback is weak. | Gemini proposes, a deterministic lint checks, and the expert or lead approves each rubric. |
| G16 | **Determinism of Track B replay.** | uuid and `now()` in IDs and timestamps | Replay output differs between runs. | Inject a clock and ID factory. |
| G17 | **Silent fallbacks** in both the app and Track B. | geminiGateway.ts; observer.py `fallback_mode = True` | Fabricated results labelled live. | Hard rule: failure → explicit `MODEL_FAILURE`. Replay only when requested. |
| G18 | **Media handling.** Audio types, the Files API for video, and browser formats are not specified. | observer.py; app | Tabla and Origami break. | Browser sends PNG + JSON trace, 16-bit PCM WAV, MP4/WebM ≤ 60 s. Video goes through the Files API. |
| G19 | **Model configuration drift:** `gemini-3.8-flash` (A), `gemini-flash-lite-latest` plus a silent fallback list (B), `gemini-2.5-flash` (app). | Code | Results cannot be reproduced or explained. | One `MODEL_REGISTRY`; model recorded per run; any fallback is recorded. |
| G20 | **Case data duplicated:** `registry.ts` inline bundles; Track B's new Kolam fixture with invented people. | Branch and app | Contradictory "truth". | Canonical packs plus a generated UI JSON. Delete the track-local duplicates. |
| G21 | **Permissions and consent are not enforced anywhere.** | No code | FR-17 is unaddressed; reputational risk with cultural material. | Minimal gate on `source.json` access level and consent scope. |
| G22 | **Variants are unaddressed** (FR-07). | — | Misses a judge question with a cheap visible answer. | Kolam: AI-inferred path vs expert-recorded stroke order, shown side by side (stretch). |

### 3.3 Coverage of the three named cases against the current plan

| | Kolam (image only, goal-conditioned) | Origami (video, forward + corrective) | Tabla (audio, forward) |
|---|---|---|---|
| **Track A, current plan** | Mentions the observed vs inferred boundary only. No region locator, no candidate-path field, no reference trace. | Generic "video extraction". No reference step list for alignment. | Not addressed. Extraction is video-centric; no audio source in the manifest; steps forced to `video`. |
| **Track B, current plan** | "Evaluate against target criteria". No capture format, no geometry metrics, no image first divergence. | No video-sequence alignment; no Files API. | Not addressed. No onset or timing measurement; audio is not even a supported MIME type in the branch. |
| **App** | Hard-coded SVG learner path. | Fixture only. | Fixture only. |

Conclusion: the plan does not actually cover image-only or audio cases end to end. Video is covered only by the generic "Gemini watches the video" path.

---

## 4. Revised plan — v1

### 4.1 Hero cases (proposed; needs sign-off)

| Case | Modality / mode | Proposed bounded skill | Expert source (owned) | Learner capture |
|---|---|---|---|---|
| **Kolam** | Image / goal-conditioned (plus forward stretch) | Sikku kolam on a 1-3-5-3-1 dot diamond (13 pulli), a single closed loop | Expert draws it (a) on paper → photo = **target image**; (b) once on the canvas → **reference trace** with stroke order | In-browser canvas over the rendered dot grid (PNG + timed trace). Photo upload as secondary path. |
| **Origami** | Video / forward + corrective | Traditional crane up to the **bird base** (about 8 folds, ≤ 60 s) | Expert phone video (owned) | Recorded phone video upload (≤ 60 s) |
| **Tabla** | Audio / forward | **Teentaal theka padhant**: recite the 16 bols with taali/khaali claps at 60 BPM. Fallback: play "Dha Dhin Dhin Dha" on tabla if the learner has one. | Tabla teacher records padhant (and playing) | Browser microphone → WAV |

Why padhant: a learner without a tabla can still practise. It is authentic (students learn padhant before playing). The audio contains speech syllables (Gemini audio can recognise the bols) and claps (deterministic onset timing). And it keeps the audio modality first-class.

**Not live for the hackathon:** micrometer, bicycle repair, handloom, square knot. They remain replay showcase cases in the app, labelled SYNTHETIC.

### 4.2 Ownership

| Workstream | Owner | Owns |
|---|---|---|
| Track A — Expert Intelligence & Grounding | Amal | `tracks/track-a/`; hero-case `source/source.json`, `knowledge/*`, `practice/rubric*`, `practice/practice_task*` |
| Track B — Practice, Evaluation & Transmission | Akarsh | `tracks/track-b/`; hero-case `practice/observers*`; assembly of the replay bundle |
| Integration — Service, App, Deploy, Demo | Jim | New `service/` (FastAPI), `app/` capture and wiring, Cloud Run, shared helpers `tracks/common/locators.py` (fragment parse/format) and `tracks/common/onsets.py` (one numpy onset detector used by Track A for reference onsets and Track B for learner onsets), sidecar JSON Schemas, CI, case-pack checker updates, consent records, demo video and deck |

### 4.3 Hybrid observation per modality (summary; details in the Track B spec)

- **Kolam:** deterministic geometry on the trace: dot clearance, stroke count and closure, loop–dot enclosure, symmetry Chamfer distance, similarity to the reference trace. Gemini judges the photo path and semantic criteria such as petal-loop shape.
- **Tabla:** deterministic onset detection on the WAV, giving tempo error, inter-onset-interval stability and grid alignment. Gemini audio recognises the bol sequence and clap placement (taali/khaali).
- **Origami:** Gemini video returns step events with timestamps against the reference step list. Deterministic sequence alignment gives order, completeness and first divergence. Gemini checks the final-state frame against the expert's final frame.

### 4.4 Locator convention (no contract change)

`EvidenceRef.source_id = "<stable source id>[#<fragment>]"`

| Fragment | Meaning |
|---|---|
| `#xywh=percent:x,y,w,h` | Image region (W3C Media Fragments) |
| `#stroke=i[-j]` | Stroke indices in a trace artifact |
| `#onset=i[-j]` | Onset indices in an audio-onset artifact |
| `#step=i` | Step index in a reference step list |

Time intervals stay in `start_sec` / `end_sec`. Images use `start_sec = end_sec = None`, never `0.0`. A parser and formatter live in `tracks/common/locators.py`. That file is a helper module, not a contract; Integration owns it and it is tested.

### 4.5 Case-pack sidecar files (case data, not contracts)

```
tracks/cases/<case_id>/
  manifest.json                         (exists; + source_media already proposed in PR #40)
  source/source.json                    Track A — source registry (id, sha256, mime, dims/duration, role, license, consent_ref, access_level)
  source/CONSENT.md                     Integration — consent summary (no sensitive personal data)
  knowledge/knowledge_package.v{N}.json Track A
  knowledge/criterion_map.v{N}.json     Track A — criterion → source_claim_ids, reference_evidence, order_index, why_it_matters
  knowledge/reference/…                 Track A — reference_trace.json (Kolam), reference_onsets.json (Tabla), reference_steps.json (Origami)
  practice/rubric.v{N}.json             Track A (approved)
  practice/practice_task.v{N}.json      Track A
  practice/observers.v{N}.json          Track B — criterion → method, params, thresholds → status
  runs/golden/<run_id>/                 each track — recorded live runs (raw response + normalised output + run_metadata)
  replay/bundle.json                    Track B assembles; must pass the common validator
```

JSON Schemas for the sidecars sit next to `manifest.schema.json` (Integration adds them). `check_case_packs.py` validates whatever files are present.

### 4.6 First-divergence rule (deterministic, Track B)

1. Order criteria by `criterion_map.order_index`, which is the procedure order (Origami steps, the Kolam candidate-path stages, the Tabla bol cycle).
2. Within the evidence, use time (video and audio), stroke index (trace) or onset index (audio) to locate the exact point.
3. The first divergence is the earliest criterion, by that order, whose status is NOT_SATISFIED or PARTIALLY_SATISFIED. Ties are broken by required-before-optional, then by evidence position.
4. UNCERTAIN criteria never become first divergence. They become "needs better evidence" prompts.

### 4.7 Service API (owned by Integration; the tracks provide the functions it calls)

| Endpoint | Calls |
|---|---|
| `GET /api/cases`, `GET /api/cases/{id}` | case-pack loader → handoff view |
| `POST /api/cases/{id}/extract` (live or recorded) | `track_a.run_extraction` |
| `POST /api/cases/{id}/query` | `track_a.answer_query` |
| `POST /api/cases/{id}/review` | `track_a.apply_review` |
| `POST /api/sessions` | `track_b.start_session` |
| `POST /api/sessions/{sid}/attempts` (multipart: media + trace) | `track_b.submit_attempt` → evaluation + first divergence + feedback |
| `GET /api/sessions/{sid}/record` | `track_b.complete_session` → validated bundle |
| `GET /api/media/{source_id}` | access-checked media serving |
| `POST /api/tts` (stretch) | spoken coaching (port of Akarsh's mentor voice) |

### 4.8 Evaluation sets (judge-visible evidence)

| Case | Labelled set | Metrics |
|---|---|---|
| Kolam | 8 learner drawings (traces), each criterion hand-labelled | criterion status agreement %, first-divergence agreement |
| Tabla | 6 learner clips with hand-labelled onsets and bols | onset F1 at ±50 ms, tempo error, bol accuracy |
| Origami | 4 learner videos with hand-labelled step boundaries | step-order agreement, boundary error (s), first-divergence agreement |
| Track A (all three) | Expert ratings of each extracted claim; 10 adversarial questions per case | fidelity (correct / incomplete / incorrect / invented), grounding pass rate, timestamp error |

Results are recorded in `docs/validation/experiments.md` with run IDs.

---

## 5. Round 2 — review of revised plan v1

| # | Challenge | Resolution in v2 |
|---|---|---|
| C1 | **Scope vs 12 days.** Three hero cases × capture × observers × eval sets × backend is a lot. | Priority tiers. **P0:** Kolam end to end live plus deployed. **P1:** Tabla and Origami end to end. **P2:** voice mentor, variants view, photo path. Reduced eval sets (Kolam 8, Tabla 6, Origami 4). Origami learner videos are pre-recorded and analysed live, not captured live on stage. |
| C2 | **Heavy dependencies on Cloud Run** (librosa/numba, OpenCV, ffmpeg). | The browser encodes WAV (Web Audio), so no ffmpeg. Onset detection uses numpy only (spectral flux). Kolam geometry uses numpy only. No OpenCV. |
| C3 | **Is `observers.json` a hidden ninth contract?** | No. It is case data with a JSON Schema in `tracks/cases/`, like `manifest.schema.json`. It never crosses into the eight contracts. The split is two files with two owners: `criterion_map` (A) and `observers` (B). No shared mutable file. |
| C4 | **Tabla needs a tabla player.** | Padhant needs only a voice and claps from the learner. The expert still has to be a real tabla teacher. If no teacher can be reached by Oct 9, **fallback** to konnakol or a vocal rhythm skill with a consenting rhythm practitioner, keeping the same pipeline. Decide on Oct 9. |
| C5 | **Kolam: does goal-conditioned mode hold up with judges?** | Yes, if it is honest. The target photo yields OBSERVED properties; the AI path is INFERRED (≤ 0.5). The expert's own canvas trace is a separate source, which (a) lets the app show the **inferred vs expert path** (variants, FR-07) and (b) validates experiment G2. This turns a weakness into a judge-visible strength. |
| C6 | **Determinism vs live Gemini.** | Scores come only from the deterministic status→score policy and metric thresholds. Gemini produces a status plus a finding. With temperature 0 and recorded raw responses, replays are exact. |
| C7 | **Retry comparability with micro-drills.** | The micro-drill is unscored practice. The retry is always the full PracticeTask under the same rubric. Integration's UI must not award scores in micro-practice (today it does: button 3 = 4.0). |
| C8 | **Expert review could slip.** | Minimal review screen (list claims → approve / revise text / reject). Track A's `apply_review` writes package v{N+1}. The demo shows one revision. One expert session per hero case, Oct 12–13. |
| C9 | **Live-demo fragility.** | Every live call has a recorded golden run. The UI shows a `RECORDED LIVE RUN · model · date` badge when replaying. Backup screen recording. |
| C10 | **Theme choice** affects framing, not the tracks. | Recommend "Future of Work & Enterprise Productivity" (skills transfer) or "Sustainability & Social Impact" (living heritage). Decide on Oct 7 (Jim). |
| C11 | **Ownership collision** on `tracks/cases/<hero>/`. | Disjoint files per owner (§4.5). `manifest.json` edits go through Integration. |
| C12 | **Is the 7-case UI still worth it?** | Yes, as the "same engine, different reasoning shape" breadth argument. But every non-hero case must show a **SYNTHETIC REPLAY** label, and the hero cases must lead the demo. |

## 6. Revised plan — v2 (final proposal)

### 6.1 Priorities

- **P0 (must ship):** Kolam live loop on Cloud Run (canvas → deterministic + Gemini evaluation → grounded feedback with expert reference → retry → record → lineage). Expert review of one claim. Evidence query. Honest labels. Golden runs. Fixes for the P0 branch bugs.
- **P1:** Tabla padhant live loop (mic). Origami loop (uploaded videos). Eval-set metrics for all three. Variants view (Kolam inferred vs expert path).
- **P2:** Kolam photo path, spoken mentor (TTS), multi-retry, embeddings-based search.

### 6.2 Schedule (12 days)

| Date | Track A (Amal) | Track B (Akarsh) | Integration (Jim) |
|---|---|---|---|
| Tue 10-06 | Read the specs | Read the specs | Sign off decisions §8; open issues |
| Wed 10-07 | P0 fixes on PR #40; package rename `track_a`; merge #40 | P0 fixes (pass semantics, no mock fallback, score policy, feedback mapping); package rename `track_b` | `service/` skeleton; `locators.py`; sidecar schemas; consent template; theme |
| Thu 10-08 | Source registry + Kolam v2 extraction (properties + candidate path + regions) | Kolam trace observer + scoring + first divergence | App canvas capture; Cloud Run deploy of the skeleton |
| Fri 10-09 | Kolam criterion map, rubric, task; golden run | Session API; feedback grounding; transitions | Wire Kolam extract → session → feedback UI; **owned media capture day** (all 3 experts + learner eval clips) |
| Sat 10-10 | Origami video extraction + reference steps | Tabla onset observer + Gemini bol observer | **Kolam P0 live on Cloud Run**; mic capture |
| Sun 10-11 | Tabla audio extraction + reference onsets | Origami video observer + sequence alignment | Video upload path; expert review screen |
| Mon 10-12 | Query API hardening; review flow | Golden runs for B; bundle assembly per case | Tabla + Origami wiring; honest badges; UI registry from packs |
| Tue 10-13 | Expert review sessions; fidelity ratings | Eval sets run (agreement metrics) | Grounding eval (10 questions × 3); experiment write-ups |
| Wed 10-14 | Fix-only | Fix-only | Integration freeze; full rehearsal |
| Thu 10-15 | Support | Support | Record demo; backup recording; deck |
| Fri 10-16 | **Code freeze** | **Code freeze** | Video final; README / architecture |
| Sat 10-17 | — | — | Submission dry run; recheck official rules and model availability |
| Sun 10-18 | — | — | **Submit** |

### 6.3 Contract-change stance

**No changes to the eight contracts for the hackathon.** Everything above fits through:

- the locator convention;
- the case-pack sidecar files;
- the derived view models in the app;
- `LineageMetadata.adaptation_notes`, which carries the observability-transition summary.

Two contract gaps are noted for after the hackathon:

- `TransmissionRecord` does not reference feedback or evaluation IDs. Today they live only at bundle level.
- `LearnerAttempt` carries one evidence item. A trace plus a raster image are two artifacts.

---

## 7. Branch review

Severity key:
- **P0:** blocks correctness or honesty; fix before merge or demo.
- **P1:** needed for hero cases.
- **P2:** cleanup.

### 7.1 Track A: `feat/amal-track-a` (PR #40, 14 commits, about 4,200 lines; 54 tests pass, 2 live tests skipped)

**What is OK and should be kept:**

- Provider adapter abstraction (`BaseProviderAdapter` with Replay and Gemini implementations) behind `ModelGateway`. Matches MODEL-GATEWAY-CONVENTIONS.
- `FailureCategory` matches the CASE-DATA taxonomy exactly. `TrackAFailure` carries structured details.
- `RunMetadataDTO` covers all required run-metadata fields.
- Versioned, mode-specific prompt files (`prompts/*_v1.txt`); the adversarial query prompt with INSUFFICIENT_EVIDENCE refusal.
- Gemini Files API upload with cleanup in `finally`; retry wrapper; timeout.
- `ExpertReviewService` (submit / approve / revise / reject, markdown export). `enforce_approved` handoff gate.
- `GroundingService` interval checks and the inferred-claim confidence cap for goal-conditioned mode.
- Replay path validates canonical bundles and runs the common cross-contract validator before handoff.
- Honest placeholder consent (`placeholder_no_real_consent`).
- Origami source media is a properly attributed CC BY 3.0 Wikimedia video.
- A good spread of negative tests.

**What needs updating:**

| Sev | Finding | Where | Required change |
|---|---|---|---|
| P0 | **Goal-conditioned candidate path is never produced.** `GeminiExtractionResponse` and `ExtractionResponseDTO` have no candidate-step field, although the prompt asks for one. The recorded live Kolam run (commit `1a8245c`) has 6 OBSERVED target properties and **zero** inferred construction steps, so there is nothing to teach. | `gemini_schemas.py`, `models.py` | Add `candidate_steps` (and region fields); normalise to INFERRED `STEP` claims with confidence ≤ 0.5. See Track A spec §5. |
| P0 | **Normaliser manufactures observation and locators.** Steps are always `modality=VIDEO`, `OBSERVED`, `confidence=1.0`, whatever the model said or the source modality (Tabla audio would be labelled video). Image target properties get a fake `start_sec=end_sec=0.0`. Conditions are OBSERVED with no locator. | `models.py: normalize_dto_to_knowledge_package` | Apply the confidence policy and locator rules in Track A spec §4. No locator → not observed. Images → `None` times plus an `#xywh` region. Modality comes from source. |
| P1 | **`requirements.txt` is a UTF-16 full `pip freeze` at repo root.** Git shows it as binary, so it cannot be reviewed. | `/requirements.txt` | Replace with UTF-8 per-track requirement files (minimal, pinned) plus a root `service/requirements.txt` that Integration owns. |
| P1 | **Live runs are not recorded or replayable.** Raw model responses are not saved; runs go to a gitignored folder; the recorded Kolam artifacts were later removed from the branch. The replay path loads the canonical bundle and **bypasses the normaliser**, so the normaliser is never tested on real model output. | `providers.py`, `run_pipeline.py`, `.gitignore` | Golden-run recorder plus a `RecordedRunProviderAdapter` that replays raw responses through the same normaliser (spec §8). |
| P1 | **Rubric generation is mechanical.** One criterion per claim, named "Criterion for CLM-0n"; the observable indicator is the claim text; flat weights; arbitrary 70% pass mark. `rubric_synthesis_v1.txt` is unused. The criterion → claim link exists only as text inside `description`. | `task_generator.py` | Gemini-proposed rubric plus a deterministic lint plus human approval; emit `criterion_map` (spec §6). |
| P1 | **PracticeTask is generic** ("Demonstrate mastery of …"; placeholder constraint). | `task_generator.py` | Structured, case-specific instructions that cite claims, with real constraints (spec §7). |
| P1 | **Corrective extraction in Track A overlaps Track B.** Divergences become KnowledgePackage claims (learner errors inside expert knowledge). The corrective prompt needs learner media and a rubric, but extraction uploads only the case source. | `models.py` §7, `prompts/corrective_extraction_v1.txt` | Remove divergence extraction from Track A; keep failure modes and cues (spec §3). |
| P1 | **Query fallback can ground to the wrong claim.** When the model cites no valid claim IDs, keyword overlap picks a claim and returns its evidence as support. | `providers.py: GeminiProviderAdapter.query_evidence` | No fallback: missing or invalid citations → INSUFFICIENT_EVIDENCE. Validate cited IDs. |
| P1 | **Source identity is not stable.** `source_media_id="src-{case}-live"` with no content hash; `skill_id` differs from the replay value; `kp.kolam.1` is reused for different content. | `providers.py`, `models.py` | Source registry with sha256; versioned IDs (spec §4.1, §9). |
| P1 | **Tabla is not runnable live** (no `source_media`; no audio prompt). | `tracks/cases/tabla/manifest.json`, prompts | Audio extraction prompt plus an owned source (spec §5.3). |
| P1 | **`kolam.png` provenance is unknown** ("Traditional … reference", no creator or license). | `tracks/cases/kolam/source/` | Replace with an owned, consented expert photo before public deploy. |
| P2 | Flat imports through `sys.path`; unregistered `@pytest.mark.live`; CLI-only entry point. | `src/*`, `tests/conftest.py` | `track_a` package; register the marker; public API module (spec §2). |
| P2 | Shared-file edits (`manifest.schema.json`, two manifests) bundled into a track PR. | PR #40 | Fine in substance; record in the PR as a cross-track change; Integration updates `check_case_packs.py`. |
| P2 | Default model `gemini-3.8-flash` hard-coded in the adapter. | `providers.py` | Read it from the shared model registry; verify availability on Oct 17. |

**Merge recommendation for PR #40:** fix the two P0 items, re-save `requirements.txt` as UTF-8, and add Track A tests to CI. Then merge (target Oct 7). The P1 items follow as separate issues per the spec.

### 7.2 Track B: `feat/akarsh-track-b` (contains all of PR #40, plus about 3,000 lines of Track B; 14 tests pass; no PR yet)

**What is OK and should be kept:**

- `evaluator.py`: deterministic total, rejects unknown criteria, enforces score bounds and required-criterion presence.
- `transmission.py`: deterministic gain; baseline/retry typing; learner, task and rubric alignment checks; provenance hash.
- `pipeline.run_full_cycle` validates its own output with the common bundle validator, which is the right instinct.
- `observer.py`: a structured-output schema, mapping into common contracts, and the idea of attaching learner evidence timestamps.
- `camera_demo.py`: the **concept** of live capture plus spoken, skill-specific mentoring is a strong UX and innovation idea and worth porting to the web app.

**What needs updating:**

| Sev | Finding | Where | Required change |
|---|---|---|---|
| P0 | **Pass semantics contradict the common validator.** `evaluate_attempt` sets `passed=True` when a required criterion is PARTIALLY_SATISFIED or UNCERTAIN; only NOT_SATISFIED fails. Verified: both cases yield validator errors, so `run_full_cycle` raises on realistic data. | `evaluator.py` | A required criterion must be SATISFIED to pass (spec §6). |
| P0 | **Silent mock fallback.** `GeminiObserver(fallback_mode=True)` by default returns `_mock_observe` on any API error or missing key. The mock emits Kolam-specific findings ("chalk cut through dot center") for any case and assumes criterion IDs C01–C03. The camera demo then issues transmission records from fabricated observations. | `observer.py` | Remove the implicit fallback; failures are explicit `MODEL_FAILURE`. Replay only through recorded runs (spec §9). |
| P0 | **The model authors the score.** The observer takes Gemini's `score` and silently clamps it. | `observer.py` | The model returns status plus finding plus locator; score comes from the deterministic policy and metrics (spec §5). |
| P0 | **Feedback cites unrelated expert evidence.** `expert_evidence_ref = expert_evidence_pool[len(items) % len(pool)]` (round-robin over all claims). | `feedback.py` | Use the criterion map's reference evidence; if none exists, leave it empty (spec §7). |
| P1 | **Audio unsupported, video too large.** MIME is only mp4 or jpeg (audio → "image/jpeg"); inline bytes (≈20 MB limit) instead of the Files API; no expert reference media passed, so "deviation from expert" is ungrounded. | `observer.py` | Per-modality observers (spec §4). |
| P1 | **No run metadata or prompt versioning**; prompt inline; silent fallback across a model-name list whose names are unverified. | `observer.py`, `prompts/` (empty) | Versioned prompts, recorded model, explicit recorded fallback (spec §9). |
| P1 | **Track-local fixture is a new, conflicting Kolam case** with invented people (`expert-meenakshi`, `learner-akash`) and a fake hash (`sha256-kolam-trans-001-replay-verified`). The camera demo labels it "Outside Micrometer Reading". | `fixtures/replay/case-001/`, `camera_demo.py` | Delete; test against `tracks/cases/*/replay/bundle.json` and synthetic-labelled test inputs (spec §11). |
| P1 | **Replay is non-deterministic** (uuid and `now()` in IDs and timestamps). | `evaluator.py`, `feedback.py`, `transmission.py` | Inject clock and ID factory (spec §8). |
| P1 | `criteria_improved` mixes UNCERTAIN→SATISFIED observability changes with skill change; no check that targeted retry-focus criteria appear in the retry. `expert_id` defaults to `"expert-source"`. | `transmission.py` | Transition classes; expert from `package.consent.contributor_name` (spec §8). |
| P1 | `camera_demo.py` is **Windows-only** (`winsound`, `win32com`), needs `cv2`, `sounddevice` and `numpy` which are not in requirements, sits inside the library package, and reads Track A's internal `data/runs` layout. | `src/camera_demo.py` | Move to `tracks/track-b/tools/`; port the mentor concept to `/api/tts` and web capture (spec §10). |
| P2 | Package named `src` (`from src.observer`) collides with Track A; temp images written into `src/`. | `src/` | Rename to `track_b`; temp files go to a temp dir. |
| P2 | Feedback text is template-generic ("Good effort!"); there is no "why it matters". | `feedback.py` | Grounded composition (spec §7). |
| P2 | First divergence, micro-drill and session flow are not implemented. | — | Spec §6, §7, §10. |

**Merge recommendation:** do **not** open a PR from `feat/akarsh-track-b` as it stands. It contains PR #40's commits plus its own. Rebase onto `main` after #40 merges, apply the P0 fixes, delete the conflicting fixture, move `camera_demo.py` to `tools/`, then open a PR. Target Oct 8.

### 7.3 Cross-cutting (Integration)

| Sev | Finding | Change |
|---|---|---|
| P0 | App "LIVE" mode returns the replay first divergence labelled `isLive: true` (`geminiGateway.ts`), and keeps the Gemini key in the browser. | Remove browser model calls; all model work goes through `service/`; labels come from the server. |
| P0 | The app has no learner capture; micro-practice awards scores on button clicks. | Canvas, mic and upload components; micro-drill unscored. |
| P1 | CI runs only `tracks/common/tests`. | Add Track A and B tests (live marker excluded). |
| P1 | `registry.ts` re-authors case content. | Generate UI case JSON from packs at build time; registry keeps UI-only fields. |

---

## 8. Decisions needing human sign-off (by Oct 7)

1. **Hero cases and skills:** Kolam 1-3-5-3-1 Sikku; Origami crane to bird base; Tabla Teentaal padhant at 60 BPM. Fallback decision for Tabla by Oct 9.
2. **People:** the named expert and learner for each hero case, and consent sign-off.
3. **Integration workstream owner:** Jim.
4. **Locator convention and sidecar files** (§4.4, §4.5) as cross-track case-data conventions. No contract change.
5. **Competition theme.**
6. **Merge order:** PR #40 (after P0 fixes) → Track B PR → Integration PRs.

Each accepted item becomes a bounded GitHub issue, per `AGENTS.md`. NOW.md / project.yaml should then record the selected hero cases. That is a scope change: the trade is that four cases become replay-only showcase.

---

## 9. Decisions 2026-10-06 (Jim) — supersede conflicting text above

1. **Hero cases confirmed.** Kolam uses the **final image only**; evaluation interpolates backward from it and checks whether the learner's actions reach the target. Origami uses video (full multimodal). Tabla uses audio; optional video is accepted and displayed but not scored.
2. **No people are required for the hackathon build.** Sources and learner attempts come from **uploads** (Track A source upload and Track B attempt upload) and from licensed internet media. Live capture (mic, camera) is future work. The Kolam canvas stays, because it is an input method rather than capture.
3. **Ownership:** Jim owns integration. Claude is the main developer across Track A, Track B, service and app, and uses parallel sub-agents.
4. **Conventions:** the locator convention and the case-pack sidecars are adopted as proposed. The GoalModel replaces the separate reference files (see `evaluation-core.md`).
5. **Theme:** **Sustainability & Social Impact**, framed as living-heritage and skill transmission (Kolam and Tabla are intangible cultural heritage; Origami is the control case). Recheck the official theme text before submission.
6. **Merge order:** Amal's and Akarsh's branches are merged into `m1/hero-cases` to keep their history. Work continues there in bounded commits, with PRs into `main` once `gh` is available.
7. **Data:** internet sources only, chosen by licence (see `tracks/cases/*/source/source.json`).
8. **Evaluation is the core capability:** designed in `evaluation-core.md` (Goal-Trajectory Verification).
9. **Models:** Gemma 4 26B (`gemma-4-26b-a4b-it`, free on AI Studio) for text, images and video frames. Gemma has no audio, so audio model calls are optional and off by default. Keys go in `.env` (template in `.env.example`).
10. **NOW scope change:** the three hero cases are live; micrometer, bicycle repair, handloom and square knot become SYNTHETIC replay showcase only. NOW.md and project.yaml will be updated to match.
