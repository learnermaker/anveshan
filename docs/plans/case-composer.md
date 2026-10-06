# Case Composer: onboarding an entirely new skill from an upload

**Date:** 2026-10-06 · **Status:** DECIDED for the hackathon build (Jim asked for "intelligence in processing new things": a user uploads an entirely new case interactively in the UI).

## 1. Problem

Today a user can upload a *new source for an existing hero case* (another kolam image, another origami video, another tabla clip) through `track_a.api.create_upload_case`. What they cannot do is bring a **new skill**: say a rangoli, a knot, a calligraphy stroke, a cup-folding video, a hand-clap rhythm, or a fortune-teller fold. The platform should:

1. understand what kind of capability the upload represents;
2. choose the right evaluation engine, or honestly fall back;
3. propose a teaching and evaluation plan;
4. let the user confirm or edit it;
5. build a working case (goal model, claims, rubric, task) that a learner can practise immediately.

## 2. Principle: model proposes, deterministic code disposes, human confirms

```
upload ─► deterministic probe (facts) ─► allowed engines (deterministic suitability checks)
       ─► model analysis (Gemma image/frames, Flash-Lite audio): proposal constrained to allowed engines
       ─► user confirms/edits in UI (title, mode, engine, criteria)
       ─► compose case dir + build with the chosen engine ─► review ─► practise
```

- Facts from the probe (duration, resolution, has-audio, ink fraction, percussive contrast) are **OBSERVED**.
- Everything the model suggests (skill name, domain, criteria wording, vocabulary) is **INFERRED** until the user confirms it.
- User confirmation is recorded (`confirmed_by_user`, `confirmed_at`). It does not turn an inference into a source fact.
- The model may only pick from the engines that the deterministic checks allowed.
- Cost cap per analysis: at most 2 Gemma calls and at most 1 Flash-Lite call.

## 3. Engine families

Each family is a goal builder (Track A) plus a trajectory evaluator (Track B). The family is stored in the case profile; hero cases keep their fixed mapping.

| Family id | Engine (existing code, generalised) | Goal-model modality key | Use for | Learner input kinds |
|---|---|---|---|---|
| `image_target` | Kolam engine: line-art goal model; coverage / precision / off-path / continuity. Dots are optional. | `kolam_image` | Any **final-image line drawing** to reproduce: kolam, rangoli outline, simple mandala, a letter or calligraphy shape, a maze path, a simple sketch | `trace`, `image` |
| `video_states` | Origami engine: Gemma state recognition from frames plus a deterministic trajectory | `origami_video` | Any **procedure with visually distinct sequential states**: folding, knots, simple assembly, plating | `video` |
| `audio_rhythm` | Tabla engine: onsets, pulse, bass/timbre classes, DTW | `tabla_audio` | Any **percussive rhythm**: tabla, other drums, hand claps, tapping patterns | `audio` |
| `rubric_vlm` | **New:** general rubric review. Gemma (images/frames) or Flash-Lite (audio) judges the learner's evidence against user-confirmed observable criteria. Status only; scores come from the deterministic policy. | `rubric_vlm` | Anything that fits none of the above (e.g. a posture, an arrangement, a spoken phrase) | `image`, `video`, `audio` (matching the source modality) |

`rubric_vlm` is honest but weaker. Every result is `MODEL_ASSISTED`, process criteria are UNCERTAIN, and the UI labels it "General rubric review (lower confidence)". Its claims are INFERRED, apart from probe facts.

## 4. Deterministic suitability checks (`allowed_families`)

| Source | Check | Allows |
|---|---|---|
| image | Binarises cleanly (Otsu separation ≥ 0.25), ink fraction 1–40%, skeleton length ≥ 0.5 × max(width, height), ≤ 6 connected ink components larger than 0.5% of ink | `image_target` |
| image | always | `rubric_vlm` |
| video | ≥ 8 s; mean frame-to-frame change > 1% of pixels over ≥ 30% of 1-fps samples (something visibly changes) | `video_states` |
| video with audio track, or audio | onsets ≥ 1.5/s over ≥ 6 s with percussive contrast ≥ 1.5 | `audio_rhythm` (video: uses the audio track) |
| any | audio model enabled (for audio) / always (for image, video) | `rubric_vlm` |

## 5. Case profile (case data, not a contract)

Stored at `<case_dir>/knowledge/case_profile.v{N}.json`. Pydantic model `CaseProfile` in `tracks/common/profile.py`:

```python
class CriterionSuggestion(BaseModel):
    criterion_id: str            # CRIT-<SLUG>-<NN>, deterministic
    name: str
    observable_indicator: str    # must name something visible/audible
    weight: float = 2.0          # 1..5
    required: bool = False
    method: Literal["engine_default", "vlm_status"] = "engine_default"

class ProbeFacts(BaseModel):
    modality: Literal["image", "video", "audio"]
    mime_type: str; bytes: int; sha256: str
    width: int | None = None; height: int | None = None
    duration_sec: float | None = None; has_audio: bool | None = None
    metrics: dict[str, float] = {}   # e.g. ink_fraction, otsu_separation, change_ratio, onset_rate, percussive_contrast
    allowed_families: list[str]
    family_reasons: dict[str, str]   # human-readable reason per allowed/denied family

class CaseProfile(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    case_id: str                     # "<slug>~<sha12>"
    title: str                       # learner-facing skill name (user-confirmed)
    skill_summary: str
    domain: str
    family: Literal["image_target", "video_states", "audio_rhythm", "rubric_vlm"]
    transmission_mode: Literal["forward", "goal-conditioned", "corrective"]
    learner_input_kinds: list[Literal["trace", "image", "audio", "video"]]
    vocabulary: dict[str, str] = {}  # prompt/UI wording, e.g. {"state_noun": "fold state", "object": "paper", "unit": "stroke"}
    goal_hint: str | None = None     # the user's own description of the target
    criteria: list[CriterionSuggestion] = []
    probe: ProbeFacts
    model_proposal: dict = {}        # raw validated model suggestion (INFERRED), kept for audit
    model_run_keys: list[str] = []
    confirmed_by_user: bool = False
    confirmed_at: str | None = None
    warnings: list[str] = []
```

`case_id` slug: lowercase ASCII from the title (`[a-z0-9-]`, ≤ 32 characters, else `skill`), then `~`, then the first 12 hex digits of the source sha256. It matches the service id regex `^[a-z0-9-]+(~[0-9a-f]{12})?$`.

## 6. Modality resolution (replaces the hard-coded map for new cases)

`track_a.config.modality_for(case_id)` returns, in order:
1. `HERO_CASES` (kolam / origami / tabla);
2. for derived `<base>~<sha12>` cases whose base is a hero case, the base's modality;
3. otherwise the latest `knowledge/case_profile.v*.json` family mapped to its modality key (§3);
4. otherwise `None`.

Track B does the same with its own reader (it must not import track_a): `track_b.handoff` reads `goal_model.modality`, which is already in the GoalModel file.

## 7. Builder and evaluator generalisation

- Builder signature gains an optional keyword: `build(source_path, source, ctx, *, case_id, version, profile: CaseProfile | None = None)`. Hero builds pass `None` and are unchanged, byte for byte.
- When `profile` is given:
  - claim, task and criterion wording uses `profile.title`, `profile.vocabulary` and neutral nouns ("dots", "line", "state", "stroke") instead of kolam/origami/tabla terms;
  - prompts use v2 files with placeholders `{skill_title}`, `{state_noun}`, `{object_noun}`, `{goal_hint}`;
  - user-confirmed `criteria` with `method="engine_default"` are matched to the engine's metric catalogue by the engine's default templates (the user can toggle `required` and change `weight`). Criteria with `method="vlm_status"` are added as `rubric_vlm`-style criteria evaluated by a status call.
- `image_target` without dots: dot claims and dot criteria are omitted when no dots are detected (`dot_relation_match` becomes not applicable and is left out of the rubric).

## 8. Service API (new; added to service-api.md)

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/compose/analyze` | multipart `file`, optional `title`, `description`, required `rights_confirmed=true` | `{draft_id, probe: ProbeFacts, proposal: CaseProfile (unconfirmed), warnings}` |
| GET | `/api/compose/{draft_id}` | — | same as above |
| POST | `/api/compose/{draft_id}/create` | JSON `{title, skill_summary, domain, family, transmission_mode, learner_input_kinds, vocabulary, goal_hint, criteria}` | `CaseHandoff.to_view()` of the built case (`case_id` = `<slug>~<sha12>`) |

- Drafts live in `<data_dir>/drafts/<draft_id>/` (`source.<ext>`, `draft.json`), with `draft_id = sha256[:16]`.
- Limits: ≤ 30 MB; video ≤ 120 s; audio ≤ 60 s.
- `create` validates that the chosen `family` is in `probe.allowed_families` (else 400), writes the case dir, `source/source.json` (runtime_label UPLOAD, licence "user upload — rights asserted by uploader") and `knowledge/case_profile.v1.json` (confirmed), then calls `build_case`.

## 9. UI (summary; detail in K8)

The wizard runs Upload → Analyzing → Proposal (facts vs suggestions, engine with reasons and alternatives, editable fields, criteria editor) → Create & build (progress) → Review claims → Practise. Composed cases appear in Discovery under "Your skills", labelled UPLOAD (plus "General rubric review" for `rubric_vlm`).

## 10. Honesty rules specific to the composer

- Never present the model's guess about what the skill *is* as a fact. The proposal screen separates "What we measured" (probe) from "What the AI suggests".
- `rubric_vlm` results carry the label `MODEL_ASSISTED · lower confidence` and list every UNCERTAIN reason.
- Composed cases cannot claim expert provenance. Consent comes from the user's rights assertion only.

## 11. Work split (Kiro wave 2; starts after K1–K4 merge)

| Spec | Scope |
|---|---|
| K6 | Composer backend: profile, probe, allowed families, analysis, drafts, compose, modality resolution, service routes |
| K7 | Engine generalisation (profile-aware builders and evaluators, v2 prompts) and the new `rubric_vlm` family |
| K8 | Composer UI wizard + "Your skills" (after K3) |
| K2b | Tabla timbre classes + Flash-Lite bol labels (after K2) |
