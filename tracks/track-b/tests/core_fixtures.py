"""Helpers for the Track B core tests: a small fake case pack and a fake modality evaluator.

The fake evaluator reads the metric values it should report from a ``"fake"`` block inside
the (otherwise valid) canvas-trace JSON, so the whole pipeline - intake included - runs
end-to-end without any real modality evaluator or model call.
All data here is SYNTHETIC test data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tracks.common.casedata import (
    CriterionMap,
    CriterionMapEntry,
    GoalModel,
    Observers,
    ObserverBinding,
    Band,
    versioned_path,
    write_json,
)
from tracks.common.runtime import RunContext
from tracks.common.schemas import (
    ConsentMetadata,
    EvidenceRef,
    ExpertReview,
    KnowledgeClaim,
    KnowledgePackage,
    PracticeTask,
    ReviewStatus,
    RubricCriterion,
    RubricDefinition,
)

from track_b import evaluators
from track_b.trajectory import AttemptMedia, DivergenceEvent, MetricValue, TrajectoryResult

CASE = "fakecase"
METRICS = {"CRIT-A": "fake.coverage", "CRIT-B": "fake.precision", "CRIT-C": "fake.continuity"}


def make_case(
    root: Path,
    *,
    case_id: str = CASE,
    version: int = 1,
    review: ReviewStatus = ReviewStatus.APPROVED,
    passing_score: Optional[float] = None,
    contributor: str = "Test Source (SYNTHETIC)",
    mutate: Optional[Dict[str, Any]] = None,
) -> Path:
    """Write a consistent 3-criterion case pack (vN of all six artifacts) under ``root/case_id``."""
    case_dir = root / case_id
    pkg_id, rubric_id = f"kp.{case_id}.{version}", f"rubric.{case_id}.{version}"
    claims = [
        KnowledgeClaim(
            claim_id=f"CLM-0{i}",
            claim_type="step",
            statement=f"Synthetic claim {i}",
            evidence_refs=[
                EvidenceRef(
                    evidence_id=f"ev.ref.{i}",
                    source_id=f"src.{case_id}.goal#step={i}",
                    modality="image",
                    cue_excerpt=f"reference region {i}",
                )
            ],
        )
        for i in (1, 2, 3)
    ]
    package = KnowledgePackage(
        package_id=pkg_id,
        skill_id=f"skill.{case_id}",
        title="Synthetic skill",
        summary="Synthetic package for Track B core tests.",
        claims=claims,
        consent=ConsentMetadata(contributor_name=contributor, consent_scope="test"),
        expert_review=ExpertReview(reviewer_name="tester", status=review),
    )
    rubric = RubricDefinition(
        rubric_id=rubric_id,
        skill_id=f"skill.{case_id}",
        title="Synthetic rubric",
        passing_score=passing_score,
        criteria=[
            RubricCriterion(criterion_id="CRIT-A", name="Coverage", description="d", observable_indicator="Every curve drawn", weight=3, required=True),
            RubricCriterion(criterion_id="CRIT-B", name="Precision", description="d", observable_indicator="No stray lines", weight=2, required=True),
            RubricCriterion(criterion_id="CRIT-C", name="Continuity", description="d", observable_indicator="Few pen lifts", weight=1, required=False),
        ],
    )
    task = PracticeTask(
        task_id=f"task.{case_id}.{version}", package_id=pkg_id, rubric_id=rubric_id,
        title="Draw it", instructions="Draw the pattern.",
    )
    cmap = CriterionMap(
        rubric_id=rubric_id,
        package_id=pkg_id,
        criteria={
            "CRIT-A": CriterionMapEntry(order_index=1, source_claim_ids=["CLM-01"], reference_evidence_ids=["ev.ref.1"],
                                        why_it_matters="The goal needs every curve [CLM-01].", drill_hint="Trace each curve fully"),
            "CRIT-B": CriterionMapEntry(order_index=2, source_claim_ids=["CLM-02"], reference_evidence_ids=["ev.ref.2"],
                                        why_it_matters="Stray powder stays [CLM-02].", drill_hint="Stay on the line"),
            "CRIT-C": CriterionMapEntry(order_index=3, source_claim_ids=["CLM-03"], reference_evidence_ids=[],
                                        why_it_matters="Continuous lines [CLM-03].", drill_hint="Lift the hand less"),
        },
    )
    observers = Observers(
        rubric_id=rubric_id,
        modality="kolam_image",
        version=version,
        criteria={
            "CRIT-A": ObserverBinding(metric="fake.coverage", direction="higher_is_better",
                                      bands=[Band(status="satisfied", min=0.9), Band(status="partially_satisfied", min=0.7)]),
            "CRIT-B": ObserverBinding(metric="fake.precision", direction="higher_is_better",
                                      bands=[Band(status="satisfied", min=0.92), Band(status="partially_satisfied", min=0.8)]),
            "CRIT-C": ObserverBinding(metric="fake.continuity", direction="lower_is_better", process=True,
                                      bands=[Band(status="satisfied", max=2), Band(status="partially_satisfied", max=4)]),
        },
    )
    goal = GoalModel(case_id=case_id, version=version, modality="kolam_image", source_ids=[f"src.{case_id}.goal"],
                     package_id=pkg_id, payload={"synthetic": True})
    docs = {
        ("knowledge", "knowledge_package"): package.model_dump(mode="json"),
        ("knowledge", "goal_model"): goal.model_dump(mode="json"),
        ("knowledge", "criterion_map"): cmap.model_dump(mode="json"),
        ("practice", "rubric"): rubric.model_dump(mode="json"),
        ("practice", "practice_task"): task.model_dump(mode="json"),
        ("practice", "observers"): observers.model_dump(mode="json"),
    }
    for (sub, stem), data in docs.items():
        if mutate and stem in mutate:
            mutate[stem](data)
        write_json(versioned_path(case_dir / sub, stem, version), data)
    return case_dir


# ---------------------------------------------------------------------------
# Fake evaluator
# ---------------------------------------------------------------------------


def write_trace(path: Path, metrics: Dict[str, Optional[float]], *, events: Optional[List[Dict[str, Any]]] = None,
                process_observable: bool = True, run_keys: Optional[List[str]] = None) -> Path:
    """A valid canvas trace that also carries the fake evaluator's answer."""
    doc = {
        "canvas": {"width": 100, "height": 100},
        "strokes": [{"points": [[i * 10, i * 10, i * 100] for i in range(6)]}],
        "duration_ms": 500,
        "fake": {"metrics": metrics, "events": events or [], "process_observable": process_observable,
                 "run_keys": run_keys or []},
    }
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def fake_evaluate(goal: GoalModel, attempt: AttemptMedia, ctx: RunContext) -> TrajectoryResult:
    spec = json.loads(Path(attempt.path).read_text(encoding="utf-8"))["fake"]
    metrics: Dict[str, MetricValue] = {}
    for i, (mid, value) in enumerate(spec["metrics"].items()):
        metrics[mid] = MetricValue(
            value=value,
            finding=f"{mid} = {value}" if value is not None else f"{mid} not computable",
            evidence=EvidenceRef(evidence_id=f"ev.{attempt.source_id}.{mid}", source_id=f"{attempt.source_id}#stroke={i}",
                                 modality="sensor"),
            uncertain_reason=None if value is not None else "too little ink",
            position=float(i),
        )
    events = [
        DivergenceEvent(metric=e["metric"], kind="off_path", position=e["position"], position_kind="stroke",
                        evidence=EvidenceRef(evidence_id=f"ev.{attempt.source_id}.event{j}",
                                             source_id=f"{attempt.source_id}#stroke={int(e['position'])}", modality="sensor"),
                        detail="synthetic event", severity=e.get("severity", "material"))
        for j, e in enumerate(spec["events"])
    ]
    n = len(metrics) or 1
    return TrajectoryResult(
        metrics=metrics,
        events=sorted(events, key=lambda e: e.position),
        curve=[(float(i), (i + 1) / n) for i in range(n)],
        curve_kind="stroke",
        process_observable=spec["process_observable"],
        artifacts={"n_metrics": n},
        run_keys=spec["run_keys"],
    )


def install_fake_evaluator(monkeypatch) -> None:
    monkeypatch.setattr(evaluators, "get_evaluator", lambda modality: fake_evaluate)


def make_ctx(case_dir: Path, data_dir: Path, mode: str = "recorded") -> RunContext:
    return RunContext.create(case_dir, data_dir, mode)
