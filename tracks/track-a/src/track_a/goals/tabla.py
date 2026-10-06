"""Tabla goal builder (``tabla_audio``): expert audio -> TablaGoal + grounded claims + criteria.

Deterministic core (evaluation-core §5.1): PyAV decode of the skill window to mono 16 kHz,
spectral-flux onsets, bass (bayan) flag by 2-means on the expert's low-band ratios, stroke
pulse from the IOI histogram, cycle from the autocorrelation of the bass pattern. All of
these claims are OBSERVED (computed, audio modality, interval locators, confidence 1.0).

Bol names are never asserted from the deterministic analysis. Only if the optional paid
audio model is enabled (``ANVESHAN_AUDIO_MODEL``) does the builder ask it to name bols; those
labels are INFERRED (confidence 0.5) and a CRIT-TABLA-BOLS criterion is added. The taal is
never named.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from tracks.common import tabla_dsp as dsp
from tracks.common.casedata import Band, ObserverBinding, SourceRecord
from tracks.common.goals.tabla import PAYLOAD_MODEL
from tracks.common.media import decode_audio
from tracks.common.models import AnveshanFailure, AudioPart, FailureCategory, ModelError, load_prompt
from tracks.common.onsets import OnsetParams
from tracks.common.runtime import RunContext
from tracks.common.schemas import ClaimType, EvidenceRef, KnowledgeClaim, Modality, TaskConstraint, VerificationState

from track_a.goals import CriterionTemplate, GoalBuildResult

SR = 16000
BUILDER_VERSION = "tabla_goal_v1"
PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "tabla_bols_v1.txt"
MIN_ONSETS = 8

# evaluation-core §5.2 default bands
TEMPO_BANDS = (5.0, 10.0)
TIMING_BANDS = (50.0, 100.0)
BASS_BANDS = (0.9, 0.7)
COMPLETE_BANDS = (1.0, 3.0)
STEADY_BANDS = (0.08, 0.15)
BOL_BANDS = (0.85, 0.6)


def _lower(sat: float, partial: float) -> List[Band]:
    return [Band(status="satisfied", max=sat), Band(status="partially_satisfied", max=partial)]


def _higher(sat: float, partial: float) -> List[Band]:
    return [Band(status="satisfied", min=sat), Band(status="partially_satisfied", min=partial)]


def analyze_window(x: np.ndarray, sample_rate: int = SR) -> Dict[str, Any]:
    """Deterministic analysis of the expert window (tracks.common.tabla_dsp.analyze_goal_audio)."""
    try:
        return dsp.analyze_goal_audio(x, sample_rate, timing_ms=TIMING_BANDS[0], tempo_pct=TEMPO_BANDS[0],
                                      min_onsets=MIN_ONSETS)
    except dsp.GoalAnalysisError as exc:
        cat = FailureCategory.INVALID_INPUT if exc.kind == "too_few_strokes" else FailureCategory.AMBIGUOUS_EVIDENCE
        raise AnveshanFailure(cat, f"expert window: {exc}") from exc


def _bass_pattern(payload: Dict[str, Any]) -> str:
    """One cycle of the bass pattern as text: B = bass stroke, - = stroke without bass, . = empty pulse."""
    L = payload["cycle_length_pulses"] or len(payload["grid"])
    out = []
    for slot in payload["grid"][:L]:
        out.append("." if slot["stroke"] is None else ("B" if slot["bass"] else "-"))
    return "".join(out)


def _request_bols(x: np.ndarray, payload: Dict[str, Any], ctx: RunContext, warnings: List[str], run_keys: List[str]) -> None:
    times = [o["t"] for o in payload["onsets"]]
    prompt, version = load_prompt(
        PROMPT_PATH,
        duration_sec=f"{payload['duration_sec']:.2f}",
        onset_times=", ".join(f"{v:.3f}" for v in times),
    )
    try:
        res = ctx.gateway.generate_json(
            model_key="audio",
            prompt_id="tabla_bols",
            prompt_version=version,
            prompt_text=prompt,
            schema=dsp.BolsDTO,
            parts=[AudioPart(dsp.wav_bytes(x, payload["sample_rate"]))],
            expected_behavior="one bol label per listed onset; '?' when unclear; no taal named",
        )
    except ModelError as exc:
        payload["bols_status"] = "model_failed"
        warnings.append(f"audio model bol naming failed ({exc.category.value}): {exc.message}; bols stay UNVERIFIED")
        return
    run_keys.append(res.metadata.replay_key)
    labels, unmatched = dsp.match_bols(times, [(b.t, b.bol) for b in res.data.bols])
    if unmatched:
        warnings.append(f"{unmatched} audio-model bol labels matched no detected onset (dropped)")
    payload["bols"] = [{"t": t, "bol": b} for t, b in zip(times, labels) if b]
    payload["bols_status"] = "inferred" if payload["bols"] else "model_failed"


def build(source_path: Path, source: SourceRecord, ctx: RunContext, *, case_id: str, version: int) -> GoalBuildResult:
    w0, w1 = (source.window_sec or [0.0, None])[0], (source.window_sec or [0.0, None])[1]
    try:
        x = decode_audio(source_path, SR, start_sec=w0, end_sec=w1)
    except ValueError as exc:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"cannot decode audio from {source.source_id}: {exc}") from exc
    if w1 is None:
        w1 = w0 + len(x) / SR
    warnings: List[str] = []
    run_keys: List[str] = []
    payload = analyze_window(x, SR)
    payload["window_sec"] = [float(w0), float(w1)]
    payload["bols"] = None
    payload["bols_status"] = "audio_model_disabled"
    audio_enabled = ctx.gateway.registry.enabled("audio")
    if audio_enabled:
        _request_bols(x, payload, ctx, warnings, run_keys)

    # Steadiness bands are calibrated so that the source itself is "satisfied" (a perfect copy
    # must not be penalised for the expert's own micro-timing).
    steady_sat = STEADY_BANDS[0]
    steady_partial = STEADY_BANDS[1]
    if payload["ioi_cv"] is not None and payload["ioi_cv"] * 1.25 > steady_sat:
        steady_sat = round(payload["ioi_cv"] * 1.25, 3)
        steady_partial = round(max(steady_partial, payload["ioi_cv"] * 2.0), 3)
        warnings.append(
            f"source pulse-normalised IOI CV is {payload['ioi_cv']:.3f}; CRIT-TABLA-STEADY bands widened to "
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

    def ev(kind: str, idx: int, start: float, end: float, excerpt: str, state=VerificationState.OBSERVED, conf=1.0) -> EvidenceRef:
        return EvidenceRef(
            evidence_id=f"ev.{case_id}.{kind}.{idx:02d}", source_id=sid, modality=Modality.AUDIO,
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
                      "steady": [steady_sat, steady_partial], "bols": BOL_BANDS},
        },
    )
