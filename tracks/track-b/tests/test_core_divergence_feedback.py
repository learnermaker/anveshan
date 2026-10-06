"""First divergence ordering, feedback expert-evidence mapping, drill, wording guard."""

from tracks.common.schemas import CriterionStatus as S, EvidenceRef
from tracks.common.validator import validate_feedback_against_evaluation

from track_b.divergence import find_first_divergence
from track_b.drill import build_drill
from track_b.evaluate import build_evaluation
from track_b.feedback import build_feedback, guard_wording
from track_b.handoff import load_handoff
from track_b.scoring import score_trajectory
from track_b.trajectory import DivergenceEvent, MetricValue, TrajectoryResult

from core_fixtures import make_case


def _traj(values, events=(), process=True, positions=None):
    metrics = {}
    for mid, v in values.items():
        metrics[mid] = MetricValue(
            value=v, finding=f"{mid}={v}", uncertain_reason=None if v is not None else "not visible",
            evidence=EvidenceRef(evidence_id=f"ev.l.{mid}", source_id=f"src.attempt.x#{mid}", modality="sensor"),
            position=(positions or {}).get(mid),
        )
    evs = [
        DivergenceEvent(metric=m, kind="off_path", position=p, position_kind="time",
                        evidence=EvidenceRef(evidence_id=f"ev.e.{m}.{p}", source_id="src.attempt.x", modality="sensor",
                                             start_sec=p, end_sec=p),
                        detail="d", severity=sev)
        for m, p, sev in events
    ]
    return TrajectoryResult(metrics=metrics, events=evs, curve=[(0.0, 0.5)], curve_kind="stroke",
                            process_observable=process)


def _run(h, traj):
    scored = score_trajectory(h.rubric, h.observers, traj)
    ev, _ = build_evaluation(evaluation_id="e1", attempt_id="a1", rubric=h.rubric, scored=scored,
                             model_assisted=False, evaluated_at="t")
    return scored, ev, find_first_divergence(h, ev, scored, traj)


GOOD = {"fake.coverage": 0.95, "fake.precision": 0.95, "fake.continuity": 1}


def test_no_events_uses_goal_order(tmp_path):
    h = load_handoff(make_case(tmp_path))
    _, ev, first = _run(h, _traj({**GOOD, "fake.precision": 0.5, "fake.continuity": 9}))
    assert first["criterion_id"] == "CRIT-B"  # order_index 2 before 3
    assert first["status"] == "not_satisfied"
    assert first["expert_evidence"]["evidence_id"] == "ev.ref.2"
    assert first["source_claim_ids"] == ["CLM-02"] and "CLM-02" in first["why_it_matters"]
    assert first["drill_hint"] == "Stay on the line"
    assert first["learner_evidence"]["evidence_id"] == "ev.l.fake.precision"
    assert set(first) == {"criterion_id", "criterion_name", "status", "position", "position_kind", "learner_evidence",
                          "expert_evidence", "observed_finding", "why_it_matters", "source_claim_ids", "drill_hint"}


def test_earliest_material_event_wins_over_order(tmp_path):
    h = load_handoff(make_case(tmp_path))
    traj = _traj({**GOOD, "fake.coverage": 0.8, "fake.continuity": 9},
                 events=[("fake.coverage", 7.0, "material"), ("fake.continuity", 2.0, "material"),
                         ("fake.precision", 0.5, "material")])  # precision is satisfied -> ignored
    _, _, first = _run(h, traj)
    assert first["criterion_id"] == "CRIT-C"
    assert first["position"] == 2.0 and first["position_kind"] == "time"
    assert first["learner_evidence"]["evidence_id"] == "ev.e.fake.continuity.2.0"
    assert first["expert_evidence"] is None  # CRIT-C has no reference evidence


def test_minor_events_ignored(tmp_path):
    h = load_handoff(make_case(tmp_path))
    traj = _traj({**GOOD, "fake.coverage": 0.8, "fake.continuity": 9}, events=[("fake.continuity", 1.0, "minor")])
    _, _, first = _run(h, traj)
    assert first["criterion_id"] == "CRIT-A"


def test_event_ties_break_by_order_index(tmp_path):
    h = load_handoff(make_case(tmp_path))
    traj = _traj({**GOOD, "fake.coverage": 0.8, "fake.precision": 0.5},
                 events=[("fake.precision", 3.0, "material"), ("fake.coverage", 3.0, "material")])
    assert _run(h, traj)[2]["criterion_id"] == "CRIT-A"


def test_uncertain_never_qualifies(tmp_path):
    h = load_handoff(make_case(tmp_path))
    traj = _traj({**GOOD, "fake.coverage": None}, events=[("fake.coverage", 0.1, "material")])
    _, ev, first = _run(h, traj)
    assert first is None
    drill = build_drill(h, ev, first, "trace")
    assert drill["kind"] == "re_record" and drill["criterion_id"] == "CRIT-A" and drill["scored"] is False


def test_feedback_items_order_and_expert_evidence_mapping(tmp_path):
    h = load_handoff(make_case(tmp_path))
    traj = _traj({"fake.coverage": None, "fake.precision": 0.85, "fake.continuity": 9},
                 events=[("fake.continuity", 1.0, "material")])
    _, ev, first = _run(h, traj)
    assert first["criterion_id"] == "CRIT-C"
    fb = build_feedback(feedback_id="f1", handoff=h, evaluation=ev, first_divergence=first, attempt_kind="trace")
    assert [i.criterion_id for i in fb.items] == ["CRIT-C", "CRIT-A", "CRIT-B"]
    assert fb.recommended_retry_focus == ["CRIT-C", "CRIT-A", "CRIT-B"]
    by = {i.criterion_id: i for i in fb.items}
    assert by["CRIT-C"].expert_evidence_ref is None                       # unmapped -> None, never borrowed
    assert by["CRIT-A"].expert_evidence_ref.evidence_id == "ev.ref.1"
    assert by["CRIT-B"].expert_evidence_ref.evidence_id == "ev.ref.2"
    assert by["CRIT-B"].learner_evidence_ref.evidence_id == "ev.l.fake.precision"
    assert "not visible" in by["CRIT-A"].what_was_observed               # uncertain -> evidence-quality item
    assert "canvas" in by["CRIT-A"].corrective_advice
    assert "CLM-02" in by["CRIT-B"].corrective_advice
    assert fb.summary.startswith("0 of 3 criteria met (1 / 6).")
    assert "First divergence: Continuity at time 1 [CLM-03]." in fb.summary
    assert validate_feedback_against_evaluation(fb, ev) == []

    drill = build_drill(h, ev, first, "trace")
    assert drill["kind"] == "practice" and drill["instruction"] == "Lift the hand less" and drill["expert_evidence"] is None


def test_all_satisfied_feedback_has_one_factual_item(tmp_path):
    h = load_handoff(make_case(tmp_path))
    _, ev, first = _run(h, _traj(GOOD))
    assert ev.passed and first is None
    fb = build_feedback(feedback_id="f1", handoff=h, evaluation=ev, first_divergence=None, attempt_kind="trace")
    assert len(fb.items) == 1 and fb.recommended_retry_focus == []
    assert build_drill(h, ev, None, "trace") is None


def test_wording_guard(tmp_path):
    h = load_handoff(make_case(tmp_path))
    _, ev, first = _run(h, _traj({**GOOD, "fake.precision": 0.5}))
    tpl = build_feedback(feedback_id="f1", handoff=h, evaluation=ev, first_divergence=first, attempt_kind="trace")

    def reword(fb, summary):
        return fb.model_copy(update={"summary": summary})

    warm = reword(tpl, "Nice work so far! " + tpl.summary)
    assert guard_wording(tpl, warm, {"CRIT-B", "CLM-02"}) is warm
    assert "(4 / 6)" in tpl.summary
    altered = reword(tpl, tpl.summary.replace("(4 / 6)", "(5 / 6)"))
    assert guard_wording(tpl, altered, {"CRIT-B"}) is tpl
    dropped_claim = reword(tpl, tpl.summary.replace("CLM-02", "the source"))
    assert guard_wording(tpl, dropped_claim, {"CLM-02"}) is tpl

    out = build_feedback(feedback_id="f1", handoff=h, evaluation=ev, first_divergence=first, attempt_kind="trace",
                         wording=lambda fb: reword(fb, fb.summary + " Keep going, you scored 99!"))
    assert out == tpl  # new number -> template kept
