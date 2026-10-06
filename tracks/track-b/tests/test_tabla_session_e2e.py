"""End-to-end session test for the tabla evaluator.

Flow: build a synthetic goal in tmp_path → start_session → submit baseline → submit retry →
complete_session → assert bundle validates, gain > 0, targeted_change improved.

All WAVs are generated in tmp_path; no media is committed.
Track B never imports track_a; synth_tabla is from tracks.common.tests.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from tracks.common import tabla_dsp as dsp
from tracks.common.casedata import (
    Band,
    CriterionMap,
    CriterionMapEntry,
    GoalModel,
    Observers,
    ObserverBinding,
    versioned_path,
    write_json,
)
from tracks.common.models import ModelGateway, ModelRegistry, RunStore
from tracks.common.runtime import RunContext
from tracks.common.schemas import (
    ClaimType,
    ConsentMetadata,
    EvidenceRef,
    KnowledgeClaim,
    KnowledgePackage,
    Modality,
    PracticeTask,
    RubricCriterion,
    RubricDefinition,
    TaskConstraint,
    VerificationState,
)
from tracks.common.tests.test_tabla_goal_model import SR, synth_tabla, write_wav
from tracks.common.validator import validate_transmission_bundle

from track_b import api

# ---------------------------------------------------------------------------
# Rubric bands (match evaluation-core §5.2 and committed observers)
# ---------------------------------------------------------------------------
_TEMPO_BANDS  = (5.0, 10.0)
_TIMING_BANDS = (50.0, 100.0)
_BASS_BANDS   = (0.9, 0.7)
_COMP_BANDS   = (1.0, 3.0)
_STEADY_BANDS = (0.08, 0.15)

PKG_ID    = "kp.tabla.e2e.1"
RUBRIC_ID = "rubric.tabla.e2e.1"
CASE_NAME = "tabla_e2e"


def _lo(sat: float, partial: float):
    return [Band(status="satisfied", max=sat), Band(status="partially_satisfied", max=partial)]


def _hi(sat: float, partial: float):
    return [Band(status="satisfied", min=sat), Band(status="partially_satisfied", min=partial)]


def _make_case(tmp_path: Path) -> Path:
    """Build all 6 case-pack artifacts for a synthetic tabla case in ``tmp_path``."""
    x, _, _ = synth_tabla()
    p = dsp.analyze_goal_audio(x, SR)
    p["window_sec"] = [0.0, len(x) / SR]
    p["bols"] = None
    p["bols_status"] = "audio_model_disabled"

    case_dir = tmp_path / "cases" / CASE_NAME
    kdir = case_dir / "knowledge"
    pdir = case_dir / "practice"
    kdir.mkdir(parents=True)
    pdir.mkdir(parents=True)

    # ── claim (inferred; no grounding audit in track_b) ──────────────────────
    ev = EvidenceRef(
        evidence_id="ev.e2e.tempo.01",
        source_id="src.e2e.test.v1",
        modality=Modality.AUDIO,
        start_sec=0.0,
        end_sec=float(len(x) / SR),
        cue_excerpt="synthetic tempo",
        verification_state=VerificationState.INFERRED,
        confidence=0.5,
    )
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.CONDITION,
        is_observed=False,
        statement="Synthetic test claim.",
        evidence_refs=[ev],
    )

    # ── 1. goal_model ─────────────────────────────────────────────────────────
    goal = GoalModel(
        case_id=CASE_NAME,
        version=1,
        modality="tabla_audio",
        source_ids=["src.e2e.test.v1"],
        package_id=PKG_ID,
        built_with={"bands": {"steady": list(_STEADY_BANDS)}},
        payload=p,
    )
    write_json(versioned_path(kdir, "goal_model", 1), goal)

    # ── 2. knowledge_package ──────────────────────────────────────────────────
    pkg = KnowledgePackage(
        package_id=PKG_ID,
        skill_id="skill.tabla",
        title="Synthetic tabla e2e",
        summary="Test package; all content is SYNTHETIC.",
        claims=[claim],
        consent=ConsentMetadata(contributor_name="SYNTHETIC", consent_scope="test", revocable=False,
                                granted_at="2026-01-01T00:00:00Z"),
        expert_review=None,
    )
    write_json(versioned_path(kdir, "knowledge_package", 1), pkg)

    # ── 3. criterion_map ──────────────────────────────────────────────────────
    _cmap_entry: Dict[str, Any] = {}
    for i, cid in enumerate(("CRIT-TABLA-TEMPO", "CRIT-TABLA-TIMING",
                              "CRIT-TABLA-BAYAN", "CRIT-TABLA-COMPLETE", "CRIT-TABLA-STEADY")):
        _cmap_entry[cid] = CriterionMapEntry(
            order_index=i,
            source_claim_ids=["CLM-01"],
            reference_evidence_ids=[],
            why_it_matters=f"See CLM-01 for context [CLM-01].",
            drill_hint="Practice slowly then speed up.",
        )
    cmap = CriterionMap(rubric_id=RUBRIC_ID, package_id=PKG_ID, criteria=_cmap_entry)
    write_json(versioned_path(kdir, "criterion_map", 1), cmap)

    # ── 4. rubric ─────────────────────────────────────────────────────────────
    rubric = RubricDefinition(
        rubric_id=RUBRIC_ID,
        skill_id="skill.tabla",
        title="Synthetic tabla rubric",
        description="E2E test rubric.",
        criteria=[
            RubricCriterion(criterion_id="CRIT-TABLA-TEMPO",   name="Tempo",       required=True,  weight=2.0,
                            description="Tempo matches.", observable_indicator="tempo error %"),
            RubricCriterion(criterion_id="CRIT-TABLA-TIMING",  name="Timing",      required=True,  weight=3.0,
                            description="On the grid.",   observable_indicator="median timing ms"),
            RubricCriterion(criterion_id="CRIT-TABLA-BAYAN",   name="Bass",        required=True,  weight=3.0,
                            description="Bass pattern.",  observable_indicator="bass accuracy"),
            RubricCriterion(criterion_id="CRIT-TABLA-COMPLETE",name="Complete",    required=False, weight=1.0,
                            description="No missing/extra.", observable_indicator="missing+extra count"),
            RubricCriterion(criterion_id="CRIT-TABLA-STEADY",  name="Steady",      required=False, weight=1.0,
                            description="Steady pulse.",  observable_indicator="IOI CV"),
        ],
    )
    write_json(versioned_path(pdir, "rubric", 1), rubric)

    # ── 5. observers ──────────────────────────────────────────────────────────
    observers = Observers(
        rubric_id=RUBRIC_ID,
        modality="tabla_audio",
        version=1,
        criteria={
            "CRIT-TABLA-TEMPO":    ObserverBinding(metric="tabla.tempo_error_pct",  direction="lower_is_better",
                                                   bands=_lo(*_TEMPO_BANDS),  process=True),
            "CRIT-TABLA-TIMING":   ObserverBinding(metric="tabla.timing_median_ms", direction="lower_is_better",
                                                   bands=_lo(*_TIMING_BANDS), process=True),
            "CRIT-TABLA-BAYAN":    ObserverBinding(metric="tabla.bass_accuracy",    direction="higher_is_better",
                                                   bands=_hi(*_BASS_BANDS),   process=True),
            "CRIT-TABLA-COMPLETE": ObserverBinding(metric="tabla.missing_extra",    direction="lower_is_better",
                                                   bands=_lo(*_COMP_BANDS),   process=True),
            "CRIT-TABLA-STEADY":   ObserverBinding(metric="tabla.ioi_cv",           direction="lower_is_better",
                                                   bands=_lo(*_STEADY_BANDS), process=True),
        },
    )
    write_json(versioned_path(pdir, "observers", 1), observers)

    # ── 6. practice_task ──────────────────────────────────────────────────────
    task = PracticeTask(
        task_id=f"task.{CASE_NAME}.1",
        package_id=PKG_ID,
        rubric_id=RUBRIC_ID,
        title="Play the tabla segment",
        instructions="1. Listen to the source. 2. Record yourself [CLM-01].",
        constraints=[TaskConstraint(constraint_type="media", description="Audio upload", value="audio")],
        target_criteria_ids=["CRIT-TABLA-TEMPO", "CRIT-TABLA-TIMING",
                              "CRIT-TABLA-BAYAN", "CRIT-TABLA-COMPLETE", "CRIT-TABLA-STEADY"],
    )
    write_json(versioned_path(pdir, "practice_task", 1), task)

    return case_dir


def _ctx(case_dir: Path, data_dir: Path) -> RunContext:
    gw = ModelGateway(
        "recorded",
        RunStore([data_dir / "runs"]),
        ModelRegistry({"audio": ""}),
    )
    return RunContext(mode="recorded", gateway=gw, case_dir=case_dir, data_dir=data_dir)


def _intake_and_submit(session, wav: Path, ctx: RunContext):
    media = api.intake_attempt(session, wav, "audio")
    return api.submit_attempt(session, media, ctx)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_session_tempo_drift_then_perfect(tmp_path):
    """Baseline: 8% tempo drift (CRIT-TABLA-TEMPO = partial → passed=False).
    Retry: perfect copy (all required satisfied → passed=True).
    Assert: bundle validates, transmission_gain > 0, targeted_change on CRIT-TABLA-TEMPO improved.
    """
    case_dir = _make_case(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ctx = _ctx(case_dir, data_dir)

    # generate WAVs in tmp_path
    x_base, _, _ = synth_tabla(tempo=1.08)
    x_retry, _, _ = synth_tabla()
    wav_base  = write_wav(tmp_path / "base.wav",  x_base)
    wav_retry = write_wav(tmp_path / "retry.wav", x_retry)

    session = api.start_session(case_dir, "TestLearner", data_dir)
    b_res = _intake_and_submit(session, wav_base,  ctx)
    r_res = _intake_and_submit(session, wav_retry, ctx)
    result = api.complete_session(session)
    out = result.to_json()

    # bundle validates against the contract schema
    ok, errors = validate_transmission_bundle(out["bundle"])
    assert ok, f"Bundle invalid: {errors}"

    # transmission gain > 0 (retry scored higher than baseline)
    rec = out["transmission_record"]
    assert rec["transmission_gain"] > 0, f"Expected gain > 0, got {rec['transmission_gain']}"

    # targeted_change: CRIT-TABLA-TEMPO improved from partial → satisfied
    cmp = out["comparison"]
    tc = cmp["targeted_change"]
    assert tc is not None, "targeted_change is None"
    assert tc["criterion_id"] == "CRIT-TABLA-TEMPO"
    assert tc["after"] == "satisfied", f"Expected TEMPO satisfied on retry, got {tc['after']}"

    # basic evaluation sanity checks
    b_eval = b_res.to_json()["evaluation"]
    r_eval = r_res.to_json()["evaluation"]
    assert b_eval["passed"] is False, "Baseline with 8% tempo drift should fail"
    assert r_eval["passed"] is True,  "Perfect retry should pass"


def test_session_dropped_strokes_then_perfect(tmp_path):
    """Baseline: 3 dropped strokes (CRIT-TABLA-COMPLETE = partial; all required criteria
    still satisfied so passed=True but score is lower than perfect).
    Retry: perfect copy.
    Assert: bundle validates, gain > 0.
    """
    case_dir = _make_case(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ctx = _ctx(case_dir, data_dir)

    # Drop strokes 8, 9, 10 (interior, non-adjacent) — COMPLETE metric = 3
    x_base, _, _ = synth_tabla(drop={8, 9, 10})
    x_retry, _, _ = synth_tabla()
    wav_base  = write_wav(tmp_path / "base_drop.wav",  x_base)
    wav_retry = write_wav(tmp_path / "retry_drop.wav", x_retry)

    session = api.start_session(case_dir, "TestLearner2", data_dir)
    _intake_and_submit(session, wav_base,  ctx)
    _intake_and_submit(session, wav_retry, ctx)
    result = api.complete_session(session)
    out = result.to_json()

    ok, errors = validate_transmission_bundle(out["bundle"])
    assert ok, f"Bundle invalid: {errors}"

    rec = out["transmission_record"]
    assert rec["transmission_gain"] > 0, f"Expected gain > 0, got {rec['transmission_gain']}"
