"""Universal GoalModel payload (case data, not a contract) + UI view.

The payload IS a SkillModel (docs/plans/universal-pipeline.md §5.1).
Built by ``track_a.goals.universal.build``; read by
``track_b.evaluators.universal.evaluate``.
"""

from __future__ import annotations

from typing import Any, Dict

from tracks.common.skill_model import SkillModel

PAYLOAD_MODEL = SkillModel


def ui_view(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Compact view for the app UI."""
    skill = SkillModel.model_validate(payload)
    steps_view = [
        {
            "step_id": s.step_id,
            "index": s.index,
            "name": s.name,
            "state_after": s.state_after,
            "critical": s.critical,
            "source_established": s.source_established,
            "keyframe_asset": s.keyframe_asset,
            "start_sec": s.start_sec,
            "end_sec": s.end_sec,
        }
        for s in skill.steps
    ]
    properties_view = [
        {
            "prop_id": p.prop_id,
            "statement": p.statement,
            "region": p.region,
            "certainty": p.certainty,
            "keep": p.keep,
        }
        for p in skill.goal_state
    ]
    checks_view = [
        {
            "check_id": c.check_id,
            "kind": c.kind,
            "name": c.name,
            "metric_id": c.metric_id,
            "method": c.method,
            "weight": c.weight,
            "required": c.required,
            "process": c.process,
            "enabled": c.enabled,
        }
        for c in skill.checks
    ]
    return {
        "kind": "universal",
        "skill_title": skill.skill_title,
        "summary": skill.summary,
        "source_modality": skill.source_modality,
        "structures": list(skill.structures),
        "steps": steps_view,
        "goal_state": properties_view,
        "order": skill.order,
        "specialists": list(skill.specialists.keys()),
        "relevance": skill.relevance.model_dump(mode="json"),
        "checks": checks_view,
        "vocabulary": dict(skill.vocabulary),
        "warnings": list(skill.warnings),
    }
