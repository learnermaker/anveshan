"""Tabla learner evaluator (``tabla_audio``): learner audio -> stroke trajectory vs the goal.

evaluation-core §5.2, all deterministic:

1. Decode any container (PyAV) to mono 16 kHz; reject unusable input explicitly
   (shorter than 3 s, silence / no strokes, more than 1 % clipped samples).
2. Onsets + bass flags. The goal's bass threshold is used unless the learner recording is
   clearly at another low-band level (rule in ``tabla_dsp.learner_bass_threshold``).
3. Tempo normalisation: learner pulse estimated near the goal pulse, initial offset by onset
   coincidence, then DTW-with-skips alignment of learner strokes to goal strokes, refined by a
   robust linear fit ``learner_t = a + b * goal_t`` (two passes).
4. Metrics (ids match practice/observers): tabla.tempo_error_pct, tabla.timing_median_ms
   (also worst), tabla.ioi_cv, tabla.bass_accuracy (balanced accuracy on aligned strokes),
   tabla.missing_extra, tabla.bol_accuracy (None unless the optional audio model is enabled),
   tabla.stroke_class_accuracy (None unless goal has timbre, v2 goals only).
5. Divergence events: early/late stroke beyond the goal timing tolerance, bass mismatch,
   missing stroke, extra stroke, tempo beyond tolerance, stroke class mismatch (v2 only).
   Progress curve = cumulative fraction of goal strokes matched correctly (on time and with
   the right bass) vs learner time.

An optional ``attempt.extra["video"]`` is accepted but never scored.
Neutral wording used for stroke class findings; "bayan" and "bol" only in goal-specific text.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from tracks.common import locators
from tracks.common import tabla_dsp as dsp
from tracks.common.casedata import GoalModel
from tracks.common.goals.tabla import TablaGoal
from tracks.common.media import decode_audio
from tracks.common.models import AnveshanFailure, AudioPart, FailureCategory, ModelError, load_prompt
from tracks.common.onsets import OnsetParams, detect_onsets
from tracks.common.runtime import RunContext
from tracks.common.schemas import EvidenceRef, Modality

from track_b.trajectory import AttemptMedia, DivergenceEvent, MetricValue, TrajectoryResult

SR = 16000
EVALUATOR_VERSION = "tabla_eval_v2"
MIN_DURATION_SEC = 3.0
MAX_CLIP_FRACTION = 0.01
MIN_STROKES = 4
SILENCE_PEAK = 1e-3
MIN_PERCUSSIVE_CONTRAST = 1.5   # p95/p50 short-time RMS; real tabla recordings measured 2.9-5.6
# Strokes with normalised onset strength below this are "soft" (ghost strokes near the detector
# threshold): missing/extra soft strokes are still counted in tabla.missing_extra but are
# "minor" events, so they never become the first (material) divergence.
SOFT_STROKE = 0.25
BOL_PROMPT = Path(__file__).resolve().parents[4] / "common" / "prompts" / "tabla_bols_v1.txt"

M_TEMPO = "tabla.tempo_error_pct"
M_TIMING = "tabla.timing_median_ms"
# Median is the scored criterion: robust to sparse large outliers that are already captured
# by individual divergence events and by CRIT-TABLA-STEADY for sustained jitter.
# M_TIMING_P90 is reported for visibility without changing the pass/fail outcome.
M_TIMING_P90 = "tabla.timing_p90_ms"   # reported only; no observer band
M_BASS = "tabla.bass_accuracy"
M_COMPLETE = "tabla.missing_extra"
M_STEADY = "tabla.ioi_cv"
M_BOLS = "tabla.bol_accuracy"
M_STROKES = "tabla.stroke_class_accuracy"


def _invalid(msg: str, **details: Any) -> AnveshanFailure:
    return AnveshanFailure(FailureCategory.INVALID_INPUT, msg, details)


def _load_learner(attempt: AttemptMedia) -> np.ndarray:
    if attempt.kind != "audio":
        raise _invalid(f"The tabla case expects an audio recording, got a {attempt.kind!r} attempt.")
    try:
        x = decode_audio(attempt.path, SR)
    except Exception as exc:  # no audio stream, unreadable container
        raise _invalid("We could not read any audio from this file. Please upload an audio recording (for example .wav, .m4a, .mp3, .ogg).",
                       error=str(exc)) from exc
    dur = len(x) / SR
    if dur < MIN_DURATION_SEC:
        raise _invalid(f"The recording is only {dur:.1f} s long. Please record at least {MIN_DURATION_SEC:.0f} s "
                       "(ideally the same length as the source segment).", duration_sec=round(dur, 3))
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    if peak < SILENCE_PEAK:
        raise _invalid("The recording is silent. Check that the microphone is working and close enough to the drums.",
                       peak=peak)
    clip = dsp.clipping_fraction(x)
    if clip > MAX_CLIP_FRACTION:
        raise _invalid(f"The recording is distorted ({clip * 100:.1f}% of samples are clipped). Move the phone further "
                       "from the drums or lower the input level and record again.", clipping_fraction=round(clip, 4))
    contrast = dsp.percussive_contrast(x, SR)
    if contrast < MIN_PERCUSSIVE_CONTRAST:
        raise _invalid("No distinct drum strokes can be heard in this recording (it sounds like a steady tone or "
                       "background noise). Record the tabla closer to the microphone in a quiet room.",
                       percussive_contrast=round(contrast, 3))
    return x


def _ev(attempt: AttemptMedia, idx: str, start: float, end: float, excerpt: str, onset: Optional[int] = None) -> EvidenceRef:
    sid = locators.with_index(attempt.source_id + ".onsets", "onset", onset) if onset is not None else attempt.source_id
    return EvidenceRef(
        evidence_id=f"ev.{attempt.source_id}.{idx}", source_id=sid, modality=Modality.AUDIO,
        start_sec=round(max(0.0, start), 3), end_sec=round(max(0.0, end, start), 3), cue_excerpt=excerpt,
    )


def _align(goal: TablaGoal, lt: np.ndarray, strokes_l: List[dsp.Stroke]) -> Tuple[dsp.Alignment, float, float, float]:
    """Returns (alignment, a, b, learner_pulse) with learner_t ~= a + b * goal_t."""
    gt = np.array([o.t for o in goal.onsets])
    strokes_g = [dsp.Stroke(o.t, o.strength, o.bass) for o in goal.onsets]
    pg = goal.stroke_pulse_sec
    try:
        pl, _ = dsp.estimate_pulse(lt, lo=0.6 * pg, hi=1.6 * pg, prefer=pg)
    except ValueError:
        pl = pg
    # coarse scale/offset search: +-25 % tempo in 1 % steps plus the learner's own pulse estimate
    scales = sorted({round(float(s), 3) for s in np.arange(0.80, 1.2501, 0.01)} | {round(pl / pg, 4)})
    a, b = dsp.initial_fit(gt, lt, pg, scales, max_shift=min(2.0, 0.5 * goal.duration_sec),
                           goal_bass=[o.bass for o in goal.onsets], learner_bass=[s.bass for s in strokes_l])
    aln = None
    for _ in range(3):
        mapped = [dsp.Stroke((s.t - a) / b, s.strength, s.bass) for s in strokes_l]
        aln = dsp.align_strokes(strokes_g, mapped, pg)
        if len(aln.pairs) < 3:
            break
        gx = np.array([gt[j] for j, _ in aln.pairs])
        ly = np.array([lt[i] for _, i in aln.pairs])
        nb, na = dsp.robust_fit_line(gx, ly)
        if nb <= 0:
            break
        if abs(nb - b) < 1e-5 and abs(na - a) < 1e-4:
            a, b = na, nb
            break
        a, b = na, nb
    mapped = [dsp.Stroke((s.t - a) / b, s.strength, s.bass) for s in strokes_l]
    aln = dsp.align_strokes(strokes_g, mapped, pg)
    return aln, a, b, b * pg


def _bol_accuracy(goal: TablaGoal, x: np.ndarray, lt: np.ndarray, ctx: RunContext, run_keys: List[str]) -> MetricValue:
    if not ctx.gateway.registry.enabled("audio"):
        return MetricValue(None, "Bol identity not evaluated: the optional audio model is disabled.",
                           uncertain_reason="audio_model_disabled")
    if not goal.bols:
        return MetricValue(None, "Bol identity not evaluated: the goal has no bol labels.",
                           uncertain_reason="goal_has_no_bols")
    prompt, version = load_prompt(BOL_PROMPT, duration_sec=f"{len(x) / SR:.2f}",
                                  onset_times=", ".join(f"{v:.3f}" for v in lt))
    try:
        res = ctx.gateway.generate_json(
            model_key="audio", prompt_id="tabla_bols", prompt_version=version, prompt_text=prompt,
            schema=dsp.BolsDTO, parts=[AudioPart(dsp.wav_bytes(x, SR))],
            expected_behavior="one bol label per listed onset; '?' when unclear; no taal named",
        )
    except ModelError as exc:
        return MetricValue(None, f"Bol identity not evaluated: audio model failed ({exc.category.value}).",
                           uncertain_reason="audio_model_failed")
    run_keys.append(res.metadata.replay_key)
    labels, _ = dsp.match_bols(list(lt), [(b.t, b.bol) for b in res.data.bols])
    learner_seq = [b for b in labels if b]
    goal_seq = [b.bol for b in goal.bols]
    dist = dsp.levenshtein(goal_seq, learner_seq)
    acc = max(0.0, 1.0 - dist / max(1, len(goal_seq)))
    return MetricValue(round(acc, 4), f"Bol sequence accuracy {acc:.2f} (edit distance {dist} over {len(goal_seq)} source bols; audio-model labels).")


def _stroke_class_accuracy(
    goal: TablaGoal,
    l_class_map: Dict[int, int],
    pairs: List[dict],
    attempt: AttemptMedia,
    events: List[DivergenceEvent],
) -> MetricValue:
    """Compute stroke_class_accuracy; adds first-mismatch DivergenceEvent.

    Neutral wording: "bass (low-frequency) strokes" and "stroke class" (never bayan/bol).
    Returns MetricValue(None) if goal has no timbre (v1 goal) or fewer than 8 aligned pairs.
    ``l_class_map`` maps learner onset index -> assigned timbre class (-1 = outlier).
    """
    if goal.timbre is None:
        return MetricValue(None, "Stroke class accuracy not evaluated: goal has no timbre model (v1 goal).",
                           uncertain_reason="no_timbre_model")
    if len(pairs) < 8:
        return MetricValue(None, "Too few aligned strokes to measure stroke class accuracy (need >= 8).",
                           uncertain_reason="too_few_aligned_strokes")

    goal_classes = [o.timbre_class for o in goal.onsets]
    class_display = goal.class_display or []
    display_map = {int(e["class"]): e["label"] for e in class_display} if class_display else {}
    timbre_k = goal.timbre.get("k", 1) if goal.timbre else 1

    correct = 0
    first_mismatch_added = False
    for pair in pairs:
        gi = pair["goal"]
        li = pair["learner"]
        g_class = goal_classes[gi] if gi < len(goal_classes) else None
        l_class = l_class_map.get(li)
        if g_class is None or l_class is None:
            continue
        if g_class == l_class:
            correct += 1
        elif not first_mismatch_added:
            first_mismatch_added = True
            g_label = display_map.get(g_class, f"Class {g_class}")
            l_label = display_map.get(l_class, f"Class {l_class}") if l_class >= 0 else "outlier"
            t_ev = pair["learner_t"]
            events.append(DivergenceEvent(
                M_STROKES, "stroke_mismatch", t_ev, "time",
                _ev(attempt, f"onset.{li}", t_ev - 0.05, t_ev + 0.15,
                    "stroke class mismatch", onset=li),
                f"Expected {g_label}, but learner stroke sounds like {l_label}.",
                severity="minor",
            ))

    acc = correct / len(pairs)
    return MetricValue(
        round(acc, 4),
        f"Stroke class accuracy {acc:.2f}: {correct}/{len(pairs)} aligned strokes match the source timbre class "
        f"({timbre_k} classes; -1 = unlike any source stroke).",
    )


def evaluate(goal: GoalModel, attempt: AttemptMedia, ctx: RunContext) -> TrajectoryResult:
    if goal.modality != "tabla_audio":
        raise AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, f"tabla evaluator got a {goal.modality} goal")
    g = TablaGoal.model_validate(goal.payload)
    warnings: List[str] = []
    run_keys: List[str] = []
    if "video" in attempt.extra:
        warnings.append("A video was attached; it is shown next to the audio timeline but not scored (audio only in this build).")

    x = _load_learner(attempt)
    duration = len(x) / SR
    on = detect_onsets(x, SR, OnsetParams(**g.onset_params) if g.onset_params else OnsetParams())
    if len(on) < MIN_STROKES:
        raise _invalid(f"Only {len(on)} drum strokes were detected. Please record the tabla segment closer to the microphone.",
                       strokes=len(on))
    lt = np.asarray(on.times_sec, dtype=float)
    thr = dsp.learner_bass_threshold(on.low_ratio, g.bass_threshold, (g.bass_centres[0], g.bass_centres[1]))
    if thr.adapted:
        warnings.append(f"Bass threshold adapted to this recording: {thr.rule}.")
    lbass = [bool(r > thr.value) for r in on.low_ratio]
    strokes_l = [dsp.Stroke(float(lt[i]), float(min(1.0, on.strength[i])), lbass[i]) for i in range(len(lt))]

    aln, a, b, pl = _align(g, lt, strokes_l)
    tol_ms = g.tolerances.timing_ms
    tol_tempo = g.tolerances.tempo_pct
    gt = np.array([o.t for o in g.onsets])
    G = len(gt)

    def expected(j: int) -> float:
        return a + b * gt[j]

    pairs = []
    for j, i in aln.pairs:
        dev_ms = (lt[i] - expected(j)) * 1000.0
        bass_ok = bool(g.onsets[j].bass == lbass[i])
        pairs.append({"goal": j, "learner": i, "goal_t": float(gt[j]), "learner_t": float(lt[i]),
                      "dev_ms": round(float(dev_ms), 1), "bass_goal": g.onsets[j].bass, "bass_learner": lbass[i],
                      "bass_ok": bass_ok, "on_time": bool(abs(dev_ms) <= tol_ms)})

    metrics: Dict[str, MetricValue] = {}
    events: List[DivergenceEvent] = []
    enough = len(pairs) >= 3
    first_t, last_t = float(lt[0]), float(lt[-1])

    # --- tempo
    if enough:
        tempo_change = (1.0 / b - 1.0) * 100.0   # + = learner faster
        tempo_err = abs(tempo_change)
        ev = _ev(attempt, "tempo", first_t, last_t, f"learner pulse {pl:.3f} s vs source {g.stroke_pulse_sec:.3f} s")
        metrics[M_TEMPO] = MetricValue(
            round(tempo_err, 2),
            f"Tempo {'faster' if tempo_change > 0 else 'slower'} than the source by {tempo_err:.1f}% "
            f"(learner pulse {pl:.3f} s vs {g.stroke_pulse_sec:.3f} s).",
            evidence=ev, position=first_t,
        )
        if tempo_err > tol_tempo:
            events.append(DivergenceEvent(M_TEMPO, "tempo_off", first_t, "time", ev,
                                          f"Tempo {tempo_change:+.1f}% vs the source (tolerance {tol_tempo:.0f}%)."))
    else:
        metrics[M_TEMPO] = MetricValue(None, "Too few strokes could be aligned to the source to measure tempo.",
                                       uncertain_reason="alignment_failed")

    # --- timing
    if enough:
        devs = np.array([abs(p["dev_ms"]) for p in pairs])
        worst = pairs[int(np.argmax(devs))]
        metrics[M_TIMING] = MetricValue(
            round(float(np.median(devs)), 1),
            f"Median stroke deviation {np.median(devs):.0f} ms, worst {devs.max():.0f} ms "
            f"(stroke at {worst['learner_t']:.2f} s), after fitting offset and tempo.",
            evidence=_ev(attempt, f"onset.{worst['learner']}", worst["learner_t"] - 0.05, worst["learner_t"] + 0.15,
                         f"deviation {worst['dev_ms']:+.0f} ms", onset=worst["learner"]),
            position=worst["learner_t"],
        )
        p90_val = round(float(np.percentile(devs, 90)), 1)
        metrics[M_TIMING_P90] = MetricValue(
            p90_val,
            f"P90 stroke deviation {p90_val:.0f} ms after offset/tempo fit "
            f"(reported only; criterion uses the median).",
            evidence=None,
            position=None,
        )
        for p in pairs:
            if not p["on_time"]:
                kind = "late_stroke" if p["dev_ms"] > 0 else "early_stroke"
                events.append(DivergenceEvent(
                    M_TIMING, kind, p["learner_t"], "time",
                    _ev(attempt, f"onset.{p['learner']}", p["learner_t"] - 0.05, p["learner_t"] + 0.15,
                        f"{p['dev_ms']:+.0f} ms vs source stroke {p['goal']}", onset=p["learner"]),
                    f"Stroke {abs(p['dev_ms']):.0f} ms {'late' if p['dev_ms'] > 0 else 'early'} vs source stroke {p['goal']} "
                    f"(source {g.window_sec[0] + p['goal_t']:.2f} s; tolerance {tol_ms:.0f} ms).",
                ))
    else:
        metrics[M_TIMING] = MetricValue(None, "Too few strokes could be aligned to measure timing.",
                                        uncertain_reason="alignment_failed")
        metrics[M_TIMING_P90] = MetricValue(None, "Too few strokes could be aligned to measure timing.",
                                            uncertain_reason="alignment_failed")

    # --- steadiness
    cv = dsp.pulse_cv(lt, pl)
    metrics[M_STEADY] = MetricValue(
        None if cv is None else round(cv, 4),
        "Not enough strokes to measure steadiness." if cv is None else
        f"Pulse-normalised interval variation {cv * 100:.1f}% (source {((g.ioi_cv or 0) * 100):.1f}%).",
        uncertain_reason=None if cv is not None else "too_few_strokes", position=first_t,
    )

    # --- bass
    if enough:
        gb = [p for p in pairs if p["bass_goal"]]
        gn = [p for p in pairs if not p["bass_goal"]]
        rec_b = sum(p["bass_learner"] for p in gb) / len(gb) if gb else None
        rec_n = sum(not p["bass_learner"] for p in gn) / len(gn) if gn else None
        parts = [r for r in (rec_b, rec_n) if r is not None]
        acc = float(np.mean(parts))
        bad = [p for p in pairs if not p["bass_ok"]]
        first_bad = bad[0] if bad else None
        metrics[M_BASS] = MetricValue(
            round(acc, 4),
            f"Bass on {sum(p['bass_learner'] for p in gb)}/{len(gb)} source bass strokes and withheld on "
            f"{sum(not p['bass_learner'] for p in gn)}/{len(gn)} source non-bass strokes (balanced accuracy {acc:.2f}).",
            evidence=None if first_bad is None else _ev(
                attempt, f"onset.{first_bad['learner']}", first_bad["learner_t"] - 0.05, first_bad["learner_t"] + 0.15,
                "bass mismatch", onset=first_bad["learner"]),
            position=None if first_bad is None else first_bad["learner_t"],
        )
        for p in bad:
            kind = "bass_missing" if p["bass_goal"] else "bass_extra"
            events.append(DivergenceEvent(
                M_BASS, kind, p["learner_t"], "time",
                _ev(attempt, f"onset.{p['learner']}", p["learner_t"] - 0.05, p["learner_t"] + 0.15,
                    kind.replace("_", " "), onset=p["learner"]),
                ("Bass expected here but not heard" if p["bass_goal"] else "Bass heard where the source withholds it")
                + f" (source stroke {p['goal']} at {g.window_sec[0] + p['goal_t']:.2f} s).",
            ))
    else:
        metrics[M_BASS] = MetricValue(None, "Too few strokes could be aligned to compare bass.",
                                      uncertain_reason="alignment_failed")

    # --- completeness
    for j in aln.missing:
        t_exp = max(0.0, float(expected(j)))
        soft = g.onsets[j].strength < SOFT_STROKE
        events.append(DivergenceEvent(
            M_COMPLETE, "missing_stroke", t_exp, "time",
            _ev(attempt, f"missing.{j}", t_exp - 0.05, t_exp + 0.15, f"no stroke for source stroke {j}"),
            f"Source stroke {j} (source {g.window_sec[0] + gt[j]:.2f} s{', bass' if g.onsets[j].bass else ''}"
            f"{', soft' if soft else ''}) was not heard; expected near {t_exp:.2f} s.",
            severity="minor" if soft else "material",
        ))
    for i in aln.extra:
        soft = on.strength[i] < SOFT_STROKE
        events.append(DivergenceEvent(
            M_COMPLETE, "extra_stroke", float(lt[i]), "time",
            _ev(attempt, f"onset.{i}", lt[i] - 0.05, lt[i] + 0.15, "extra stroke", onset=i),
            f"Extra {'soft ' if soft else ''}stroke at {lt[i]:.2f} s that the source does not have.",
            severity="minor" if soft else "material",
        ))
    n_me = len(aln.missing) + len(aln.extra)
    comp_events = sorted((e for e in events if e.metric == M_COMPLETE), key=lambda e: e.position)
    metrics[M_COMPLETE] = MetricValue(
        float(n_me),
        f"{len(aln.missing)} missing and {len(aln.extra)} extra strokes out of {G} source strokes"
        + (f" ({len(aln.outside)} strokes outside the segment ignored)." if aln.outside else "."),
        evidence=comp_events[0].evidence if comp_events else None,
        position=comp_events[0].position if comp_events else None,
    )
    if aln.outside:
        warnings.append(f"{len(aln.outside)} strokes before/after the source segment were ignored.")

    metrics[M_BOLS] = _bol_accuracy(g, x, lt, ctx, run_keys)

    # --- stroke class accuracy (v2 goals only) ---
    learner_feats = dsp.stroke_features(x, SR, list(lt))
    # Compute learner class labels once (used for metric and artifacts)
    l_class_map: Dict[int, int] = {}
    if g.timbre is not None and learner_feats.shape[0] > 0:
        tm = dsp.TimbreModel.from_dict(g.timbre)
        l_labels_arr, _ = dsp.assign(tm, learner_feats)
        for i, lbl in enumerate(l_labels_arr):
            l_class_map[i] = int(lbl)
    metrics[M_STROKES] = _stroke_class_accuracy(g, l_class_map, pairs, attempt, events)

    events.sort(key=lambda e: (e.position, e.metric, e.kind))

    # --- progress curve: cumulative fraction of goal strokes matched correctly
    correct_times = sorted(p["learner_t"] for p in pairs if p["on_time"] and p["bass_ok"])
    curve: List[Tuple[float, float]] = [(0.0, 0.0)]
    c = 0
    for t in lt:
        while c < len(correct_times) and correct_times[c] <= t + 1e-9:
            c += 1
        curve.append((round(float(t), 3), round(c / G, 4)))
    curve.append((round(duration, 3), round(len(correct_times) / G, 4)))

    # --- build pairs with class info for artifacts ---
    goal_classes = [o.timbre_class for o in g.onsets]
    pairs_with_classes = []
    for p in pairs:
        li = p["learner"]
        gi = p["goal"]
        entry = dict(p)
        entry["expert_class"] = goal_classes[gi] if gi < len(goal_classes) else None
        entry["learner_class"] = l_class_map.get(li)
        pairs_with_classes.append(entry)

    return TrajectoryResult(
        metrics=metrics,
        events=events,
        curve=curve,
        curve_kind="time",
        process_observable=True,
        final_state={
            "coverage": round(len(correct_times) / G, 4),
            "matched": len(pairs), "correct": len(correct_times),
            "missing": len(aln.missing), "extra": len(aln.extra), "outside": len(aln.outside),
            "goal_strokes": G, "learner_strokes": int(len(lt)),
        },
        artifacts={
            "evaluator": EVALUATOR_VERSION,
            "dsp": dsp.ALGO_VERSION,
            "duration_sec": round(duration, 3),
            "learner_onsets": [
                {"i": i, "t": float(lt[i]), "strength": float(on.strength[i]), "low_ratio": float(on.low_ratio[i]), "bass": lbass[i]}
                for i in range(len(lt))
            ],
            "alignment": pairs_with_classes,
            "missing": [{"goal": j, "goal_t": float(gt[j]), "expected_t": round(float(expected(j)), 3)} for j in aln.missing],
            "extra": [{"learner": i, "t": float(lt[i])} for i in aln.extra],
            "outside": [{"learner": i, "t": float(lt[i])} for i in aln.outside],
            "fit": {"offset_sec": round(a, 4), "time_scale": round(b, 5), "learner_pulse_sec": round(pl, 4)},
            "bass_threshold": {"value": round(thr.value, 4), "adapted": thr.adapted, "rule": thr.rule},
            "class_display": g.class_display,
            "video_ignored": "video" in attempt.extra,
        },
        run_keys=run_keys,
        warnings=warnings,
    )
