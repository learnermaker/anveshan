"""Tabla goal builder (``tabla_audio``): expert audio -> TablaGoal + grounded claims + criteria.

Deterministic core (evaluation-core §5.1): PyAV decode of the skill window to mono 16 kHz,
spectral-flux onsets, bass (bayan) flag by 2-means on the expert's low-band ratios, stroke
pulse from the IOI histogram, cycle from the autocorrelation of the bass pattern. All of
these claims are OBSERVED (computed, audio modality, interval locators, confidence 1.0).

Bol names are never asserted from the deterministic analysis. Only if the optional paid
audio model is enabled (``ANVESHAN_AUDIO_MODEL``) does the builder ask it to name bols; those
labels are INFERRED (confidence 0.5) and a CRIT-TABLA-BOLS criterion is added. The taal is
never named.

v2 adds: stroke timbre classes (MFCC-based k-means on expert strokes, CLM-07, OBSERVED),
CRIT-TABLA-STROKES (stroke class accuracy, not required, weight 2), and bol class labels
(INFERRED when the audio model is enabled). Calls payload_from_audio from the common layer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from tracks.common import tabla_dsp as dsp
from tracks.common.casedata import Band, ObserverBinding, SourceRecord
from tracks.common.goals.tabla import PAYLOAD_MODEL, payload_from_audio
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.onsets import OnsetParams
from tracks.common.runtime import RunContext
from tracks.common.schemas import ClaimType, EvidenceRef, KnowledgeClaim, Modality, TaskConstraint, VerificationState

from track_a.goals import CriterionTemplate, GoalBuildResult

SR = 16000
BUILDER_VERSION = "tabla_goal_v2"

# evaluation-core §5.2 default bands
TEMPO_BANDS = (5.0, 10.0)
TIMING_BANDS = (50.0, 100.0)
BASS_BANDS = (0.9, 0.7)
COMPLETE_BANDS = (1.0, 3.0)
STEADY_BANDS = (0.08, 0.15)
BOL_BANDS = (0.85, 0.6)
STROKES_BANDS = (0.80, 0.60)


def _lower(sat: float, partial: float) -> List[Band]:
    return [Band(status="satisfied", max=sat), Band(status="partially_satisfied", max=partial)]


def _higher(sat: float, partial: float) -> List[Band]:
    return [Band(status="satisfied", min=sat), Band(status="partially_satisfied", min=partial)]


def _bass_pattern(payload: Dict[str, Any]) -> str:
    """One cycle of the bass pattern as text: B = bass stroke, - = stroke without bass, . = empty pulse."""
    L = payload["cycle_length_pulses"] or len(payload["grid"])
    out = []
    for slot in payload["grid"][:L]:
        out.append("." if slot["stroke"] is None else ("B" if slot["bass"] else "-"))
    return "".join(out)


def build(source_path: Path, source: SourceRecord, ctx: RunContext, *, case_id: str, version: int) -> GoalBuildResult:
    w0, w1_raw = (source.window_sec or [0.0, None])[0], (source.window_sec or [0.0, None])[1]
    window: Any = (w0, w1_raw)

    payload, _built_with, warnings, run_keys = payload_from_audio(source_path, window, ctx)
    w1 = payload["window_sec"][1]

    if w1_raw is None:
        w1_raw = w1

    # Steadiness bands calibrated so the source is "satisfied"
    steady_sat = STEADY_BANDS[0]
    steady_partial = STEADY_BANDS[1]
    ioi_cv = payload.get("ioi_cv")
    if ioi_cv is not None and ioi_cv * 1.25 > steady_sat:
        steady_sat = round(ioi_cv * 1.25, 3)
        steady_partial = round(max(steady_partial, ioi_cv * 2.0), 3)
        warnings.append(
            f"source pulse-normalised IOI CV is {ioi_cv:.3f}; CRIT-TABLA-STEADY bands widened to "
            f"<= {steady_sat} sat / <= {steady_partial} partial (default 0.08 / 0.15)"
        )
    if payload["cycle_length_pulses"] is None:
        warnings.append(f"no repeating bass cycle established ({payload['cycle_note']})")

    PAYLOAD_MODEL.model_validate(payload)  # fail loudly on schema drift

    sid = source.source_id
    a0, a1 = float(w0), float(w1)
    on = payload["onsets"]
    n = len(on)
    n_bass = sum(1 for o in on if o["bass"])
    pulse = payload["stroke_pulse_sec"]
    audio_enabled = payload.get("bols_status") != "audio_model_disabled" or \
        (ctx.gateway.registry.enabled("audio") if ctx else False)
    # Re-read from ctx since payload_from_audio may not have called the model
    try:
        audio_enabled = ctx.gateway.registry.enabled("audio")
    except Exception:
        audio_enabled = False

    def ev(kind: str, idx: int, start: float, end: float, excerpt: str,
           state: VerificationState = VerificationState.OBSERVED, conf: float = 1.0) -> EvidenceRef:
        mime_major = source.mime_type.split("/", 1)[0].lower()
        ev_modality = Modality.VIDEO if mime_major == "video" else Modality.AUDIO
        return EvidenceRef(
            evidence_id=f"ev.{case_id}.{kind}.{idx:02d}", source_id=sid, modality=ev_modality,
            start_sec=round(start, 3), end_sec=round(end, 3), cue_excerpt=excerpt,
            verification_state=state, confidence=conf,
        )

    claims: List[KnowledgeClaim] = []
    claims.append(KnowledgeClaim(
        claim_id="CLM-01", claim_type=ClaimType.CONDITION, is_observed=True,
        statement=(
            f"The source keeps a stroke pulse of {pulse:.3f} s ({payload['strokes_per_min']:.0f} strokes per minute); "
            f"counted in groups of {payload['beat_pulses']} pulses this is {payload['tempo_bpm']:.0f} beats per minute "
            f"(a counting convention; the matra is not established from audio)."
        ),
        evidence_refs=[ev("tempo", 1, a0, a1, f"pulse {pulse:.3f} s over {n} strokes")],
    ))
    claims.append(KnowledgeClaim(
        claim_id="CLM-02", claim_type=ClaimType.STEP, is_observed=True,
        statement=(
            f"The {n} strokes of the segment occupy {n} of {len(payload['grid'])} slots of that pulse grid; the median "
            f"distance of a stroke from the fitted grid is {payload['grid_residual_median_ms']:.0f} ms."
        ),
        evidence_refs=[ev("grid", 2, a0 + on[0]["t"], a0 + on[-1]["t"], f"{n} strokes on {len(payload['grid'])} slots")],
    ))
    L = payload["cycle_length_pulses"]
    if L is not None:
        cyc_end = min(a1, a0 + payload["grid"][0]["t"] + L * pulse)
        cyc_stmt = (
            f"The bass pattern repeats every {L} pulses (about {L * pulse:.2f} s; autocorrelation "
            f"{payload['cycle_confidence']:.2f}). The taal is not identified by the system."
        )
        cyc_ev = ev("cycle", 3, a0 + max(0.0, payload["grid"][0]["t"]), cyc_end, f"cycle {L} pulses")
    else:
        cyc_stmt = f"No repeating bass cycle could be established in this segment ({payload['cycle_note']})."
        cyc_ev = ev("cycle", 3, a0, a1, "no cycle established")
    claims.append(KnowledgeClaim(claim_id="CLM-03", claim_type=ClaimType.CONDITION, is_observed=True,
                                 statement=cyc_stmt, evidence_refs=[cyc_ev]))
    pattern = _bass_pattern(payload)
    bass_refs = [ev("bass", 4, a0, a1, f"bass on {n_bass}/{n} strokes; pattern {pattern}")]
    claims.append(KnowledgeClaim(
        claim_id="CLM-04", claim_type=ClaimType.CUE, is_observed=True,
        statement=(
            f"The bass drum (bayan) is sounded on {n_bass} of {n} strokes and withheld on the rest; one "
            f"{'cycle' if L else 'segment'} reads {pattern} (B = bass stroke, - = stroke without bass, . = empty pulse)."
        ),
        evidence_refs=bass_refs,
    ))
    cv = payload["ioi_cv"]
    claims.append(KnowledgeClaim(
        claim_id="CLM-05", claim_type=ClaimType.CONDITION, is_observed=True,
        statement=(
            f"The pulse is steady: intervals between strokes, divided by their pulse count, vary by "
            f"{(cv or 0) * 100:.1f}% (coefficient of variation)."
        ),
        evidence_refs=[ev("steady", 5, a0, a1, f"pulse-normalised IOI CV {cv}")],
    ))
    if payload["bols_status"] == "inferred":
        seq = " ".join(b["bol"] for b in payload["bols"][:24])
        claims.append(KnowledgeClaim(
            claim_id="CLM-06", claim_type=ClaimType.CUE, is_observed=False,
            statement=f"An audio model labelled the strokes as: {seq}{' ...' if len(payload['bols']) > 24 else ''} (model inference, not confirmed by an expert).",
            evidence_refs=[ev("bols", 6, a0, a1, "audio-model bol labels", VerificationState.INFERRED, 0.5)],
        ))
    else:
        claims.append(KnowledgeClaim(
            claim_id="CLM-06", claim_type=ClaimType.CUE, is_observed=False,
            statement="The bol names of these strokes are not identified by the system (no audio model was used); they are unverified.",
            evidence_refs=[ev("bols", 6, a0, a1, "bol identity not analysed", VerificationState.UNVERIFIED, 0.3)],
        ))

    # CLM-07: stroke timbre classes (OBSERVED, always present in v2)
    timbre = payload.get("timbre")
    if timbre is not None:
        k = timbre["k"]
        sil = timbre["silhouette"]
        class_display = payload.get("class_display") or []
        # Build bol class statement if any class labels are inferred
        inferred_classes = [e for e in class_display if e.get("source") == "inferred"]
        if inferred_classes:
            bol_mapping = "; ".join(f"{e['label']}" for e in class_display)
            bol_stmt = f" ({bol_mapping})"
        else:
            label_list = ", ".join(e["label"] for e in class_display)
            bol_stmt = f" ({label_list})" if class_display else ""
        claims.append(KnowledgeClaim(
            claim_id="CLM-07", claim_type=ClaimType.CONDITION, is_observed=True,
            statement=(
                f"The source uses {k} distinct stroke timbres (silhouette {sil:.2f}); "
                f"each stroke is assigned to a timbre class by k-means on its MFCC and spectral features{bol_stmt}."
            ),
            evidence_refs=[ev("timbre", 7, a0, a1, f"k={k} timbre classes, silhouette {sil:.2f}")],
        ))
        # Add INFERRED claim about bol-class correspondence when audio model ran
        if payload["bols_status"] == "inferred" and inferred_classes:
            bol_seq_labels = "; ".join(e["label"] for e in inferred_classes)
            claims.append(KnowledgeClaim(
                claim_id="CLM-08", claim_type=ClaimType.CUE, is_observed=False,
                statement=(
                    f"Stroke classes correspond mostly to bols: {bol_seq_labels} "
                    f"(inferred by audio model; not confirmed by an expert)."
                ),
                evidence_refs=[ev("bol_class", 8, a0, a1, "audio model bol-class labels",
                                   VerificationState.INFERRED, 0.5)],
            ))

    criteria: List[CriterionTemplate] = [
        CriterionTemplate(
            criterion_id="CRIT-TABLA-TEMPO", name="Holds the source tempo",
            description="The learner's stroke pulse matches the source pulse.",
            observable_indicator="tempo error % of the learner's fitted stroke pulse vs the source pulse",
            weight=2, required=True, order_index=0, source_claim_ids=["CLM-01"], reference_evidence_ids=["ev.%s.tempo.01" % case_id],
            why_it_matters=f"The source holds a {pulse:.3f} s stroke pulse throughout the segment (CLM-01); rushing or dragging changes the rhythm itself.",
            drill_hint=f"Play along with the source segment, counting {payload['beat_pulses']} strokes per beat, then record without it.",
            observer=ObserverBinding(metric="tabla.tempo_error_pct", direction="lower_is_better", bands=_lower(*TEMPO_BANDS), process=True),
        ),
        CriterionTemplate(
            criterion_id="CRIT-TABLA-TIMING", name="Strokes land on the pulse grid",
            description="Each stroke lands where the source stroke lands, after allowing for overall offset and tempo.",
            observable_indicator="median absolute stroke timing deviation (ms) after offset/tempo fit",
            weight=3, required=True, order_index=1, source_claim_ids=["CLM-02"], reference_evidence_ids=["ev.%s.grid.02" % case_id],
            why_it_matters=f"Every stroke of the source sits on the pulse grid, with a median of {payload['grid_residual_median_ms']:.0f} ms off it (CLM-02).",
            drill_hint="Loop one cycle slowly with a metronome on the pulse; speed up only when every stroke coincides with the click.",
            observer=ObserverBinding(metric="tabla.timing_median_ms", direction="lower_is_better", bands=_lower(*TIMING_BANDS), process=True),
        ),
        CriterionTemplate(
            criterion_id="CRIT-TABLA-BAYAN", name="Bass used and withheld where the source does",
            description="Bass (bayan) strokes occur on the same strokes as in the source.",
            observable_indicator="balanced accuracy of the per-stroke bass flag on aligned strokes",
            weight=3, required=True, order_index=2, source_claim_ids=["CLM-04", "CLM-03"],
            reference_evidence_ids=["ev.%s.bass.04" % case_id, "ev.%s.cycle.03" % case_id],
            why_it_matters=f"The source sounds the bayan on {n_bass} of {n} strokes in a fixed pattern ({pattern}) (CLM-04); where the bass is withheld is part of the cycle's shape.",
            drill_hint="Speak the pattern aloud (B for bass, dash for no bass) while playing only the bayan strokes, then add the right hand.",
            observer=ObserverBinding(metric="tabla.bass_accuracy", direction="higher_is_better", bands=_higher(*BASS_BANDS), process=True),
        ),
        CriterionTemplate(
            criterion_id="CRIT-TABLA-COMPLETE", name="No missing or extra strokes",
            description="Every source stroke is played once and nothing is added.",
            observable_indicator="count of missing + extra strokes after alignment",
            weight=1, required=False, order_index=3, source_claim_ids=["CLM-02"], reference_evidence_ids=["ev.%s.grid.02" % case_id],
            why_it_matters=f"The source segment contains {n} strokes on a fixed grid (CLM-02); a dropped or added stroke breaks the phrase.",
            drill_hint="Play one cycle at half speed and count the strokes out loud against the reference count.",
            observer=ObserverBinding(metric="tabla.missing_extra", direction="lower_is_better", bands=_lower(*COMPLETE_BANDS), process=True),
        ),
        CriterionTemplate(
            criterion_id="CRIT-TABLA-STEADY", name="Steady pulse",
            description="The pulse does not waver from stroke to stroke.",
            observable_indicator="coefficient of variation of pulse-normalised inter-onset intervals",
            weight=1, required=False, order_index=4, source_claim_ids=["CLM-05"], reference_evidence_ids=["ev.%s.steady.05" % case_id],
            why_it_matters=f"The source's pulse varies by only {(cv or 0) * 100:.1f}% between strokes (CLM-05).",
            drill_hint="Play only the pulse on one drum for a minute against a metronome, then add the pattern.",
            observer=ObserverBinding(metric="tabla.ioi_cv", direction="lower_is_better", bands=_lower(steady_sat, steady_partial), process=True),
        ),
    ]
    if audio_enabled and payload["bols_status"] == "inferred":
        criteria.append(CriterionTemplate(
            criterion_id="CRIT-TABLA-BOLS", name="Bol identity",
            description="The learner's bols match the bols the audio model heard in the source.",
            observable_indicator="1 - edit distance / length between learner and source bol sequences (audio model)",
            weight=2, required=False, order_index=5, source_claim_ids=["CLM-06"], reference_evidence_ids=["ev.%s.bols.06" % case_id],
            why_it_matters="An audio model labelled the source strokes with specific bols (CLM-06); this is a model inference, not expert-confirmed.",
            drill_hint="Recite the bols aloud with the source, then play them one cycle at a time.",
            observer=ObserverBinding(metric="tabla.bol_accuracy", direction="higher_is_better", bands=_higher(*BOL_BANDS), process=True),
        ))
    # CRIT-TABLA-STROKES: stroke class accuracy (v2, not required)
    if timbre is not None:
        clm_ref = "CLM-07"
        ev_ref = "ev.%s.timbre.07" % case_id
        criteria.append(CriterionTemplate(
            criterion_id="CRIT-TABLA-STROKES", name="Stroke timbre matches the source",
            description="Each learner stroke belongs to the same timbre class as the aligned source stroke.",
            observable_indicator="fraction of aligned stroke pairs where learner and source timbre classes match",
            weight=2, required=False, order_index=6 if audio_enabled and payload["bols_status"] == "inferred" else 5,
            source_claim_ids=[clm_ref], reference_evidence_ids=[ev_ref],
            why_it_matters=(
                f"The source has {timbre['k']} distinct stroke timbres (silhouette {timbre['silhouette']:.2f}, CLM-07); "
                "matching them requires the same articulation and ring/mute technique."
            ),
            drill_hint="For each class, isolate just those strokes and practise until the sound matches the source.",
            observer=ObserverBinding(metric="tabla.stroke_class_accuracy", direction="higher_is_better",
                                     bands=_higher(*STROKES_BANDS), process=True),
        ))

    dur = a1 - a0
    instructions = "\n".join([
        f"1. Listen to the source segment ({a0:.1f}-{a1:.1f} s of the recording, {dur:.0f} s) several times. "
        f"Its stroke pulse is {pulse:.3f} s, about {payload['tempo_bpm']:.0f} beats per minute counting {payload['beat_pulses']} strokes per beat [CLM-01].",
        f"2. Record yourself playing about the same length ({dur:.0f} s) at the source tempo, placing every stroke on the pulse as the source does [CLM-02].",
        f"3. Sound the bass (bayan) on the same strokes as the source and withhold it elsewhere: {pattern} "
        + (f"repeating every {L} pulses [CLM-04] [CLM-03]." if L else "[CLM-04]."),
        "4. Keep the pulse steady from the first stroke to the last; do not speed up or slow down [CLM-05].",
        "5. Record in a quiet room with the phone about 1 m from the drums and check the recording is not distorted. "
        "Upload audio (any common format); a video may be attached but is not scored [CLM-06].",
    ])
    constraints = [
        TaskConstraint(constraint_type="duration", description="Record about the same length as the source segment", value=f"{dur:.0f}s"),
        TaskConstraint(constraint_type="tempo", description="Play at the source tempo (counted beats per minute)", value=f"{payload['tempo_bpm']:.0f} BPM"),
        TaskConstraint(constraint_type="media", description="Audio upload, at least 3 s, no clipping; video optional and not scored", value="audio"),
    ]
    return GoalBuildResult(
        title="Tabla stroke pattern: tempo, grid and bayan",
        summary=(
            f"A {dur:.0f} s tabla segment ({n} strokes, pulse {pulse:.3f} s, bass on {n_bass} strokes"
            + (f", bass pattern repeating every {L} pulses" if L else "")
            + (f", {timbre['k']} timbre classes" if timbre else "")
            + "). Timing and bass are measured deterministically from the audio; bols and taal are not asserted."
        ),
        goal_payload=payload,
        claims=claims,
        criteria=criteria,
        task_title="Play the source tabla segment at its tempo with the same bass pattern",
        task_instructions=instructions,
        task_constraints=constraints,
        warnings=warnings,
        run_keys=run_keys,
        built_with={
            "builder": BUILDER_VERSION,
            "dsp": dsp.ALGO_VERSION,
            "sample_rate": SR,
            "onset_params": OnsetParams().__dict__.copy(),
            "audio_model_enabled": audio_enabled,
            "bands": {"tempo": TEMPO_BANDS, "timing": TIMING_BANDS, "bass": BASS_BANDS, "complete": COMPLETE_BANDS,
                      "steady": [steady_sat, steady_partial], "bols": BOL_BANDS, "strokes": list(STROKES_BANDS)},
        },
    )
