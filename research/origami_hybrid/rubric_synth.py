"""
RubricSynthesizer v1 — geometry-heuristic synthesized criteria (CRIT-HYB-N).

Derives 5 observable rubric criteria from the fold sequence produced by
FoldingAgent.  Uses mountain/valley edge assignments, layer counts, face
orientation, and geometric state transitions.

Does NOT use the canonical origami criteria (CRIT-CORNER-ALIGN etc.) from
the replay bundle — those are engineering fixture IDs, not geometry-derived.

v2 (commit 11): replaces heuristics with an LLM prompt for richer
observable_indicator text.

No LLM calls in this file.  No imports from tracks/track-a/src/.
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema imports (frozen seam only)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON = _REPO_ROOT / "tracks" / "common"
if str(_COMMON) not in sys.path:
    sys.path.insert(0, str(_COMMON))

from schemas.practice import PracticeTask, TaskConstraint  # noqa: E402
from schemas.rubric import RubricCriterion, RubricDefinition  # noqa: E402

from adapter import FoldCheckpoint  # noqa: E402


# ---------------------------------------------------------------------------
# Criterion builders
# ---------------------------------------------------------------------------

def _build_crit_fold_order(checkpoints: list[FoldCheckpoint]) -> RubricCriterion:
    """
    CRIT-HYB-1: Folds executed in reconstructed sequence order.

    Observable: the learner reaches each state in the correct order as
    determined by the FoldingAgent reconstruction (frame 1 → frame N).
    """
    n = len(checkpoints)
    step_ops = []
    for cp in checkpoints:
        names = [op.get("function", "?") for op in cp.operations if op.get("function")]
        if names:
            step_ops.append(f"frame {cp.frame_index}: {', '.join(names)}")

    if step_ops:
        seq_desc = "; ".join(step_ops[:4])
        if len(step_ops) > 4:
            seq_desc += f" (and {len(step_ops) - 4} more)"
    else:
        seq_desc = f"transitions across {n} keyframes"

    return RubricCriterion(
        criterion_id="CRIT-HYB-1",
        name="Fold sequence order",
        description=(
            "Learner executes the demonstrated fold transitions in the "
            "correct sequential order as reconstructed by FoldingAgent."
        ),
        observable_indicator=(
            f"Learner reaches each paper state in the order: {seq_desc}. "
            "No out-of-order folds observed."
        ),
        weight=2.0,
        required=True,
    )


def _build_crit_crease_polarity(checkpoints: list[FoldCheckpoint]) -> RubricCriterion:
    """
    CRIT-HYB-2: Mountain/valley crease polarity matches reconstruction.

    Observable: each fold edge is assigned the correct M or V kind.
    """
    # Find the first checkpoint with M or V edges
    examples: list[str] = []
    for cp in checkpoints:
        edges = cp.raw_representation.get("edges", [])
        for edge in edges:
            if len(edge) >= 3 and str(edge[2]).upper() in ("M", "V"):
                kind_label = "mountain (M)" if str(edge[2]).upper() == "M" else "valley (V)"
                examples.append(f"edge [{edge[0]},{edge[1]}] → {kind_label}")
            if len(examples) >= 3:
                break
        if examples:
            break

    if examples:
        indicator = (
            "Crease polarity matches reconstruction: "
            + "; ".join(examples)
            + ". Mountain folds form a convex ridge; valley folds form a concave trough."
        )
    else:
        indicator = (
            "Each fold edge has the correct mountain (M) or valley (V) assignment "
            "as shown in the FoldingAgent rendered diagrams. "
            "Mountain = convex ridge; valley = concave trough."
        )

    return RubricCriterion(
        criterion_id="CRIT-HYB-2",
        name="Crease polarity fidelity",
        description=(
            "Learner assigns correct mountain/valley polarity to each crease, "
            "matching the FoldingAgent critic-verified geometric state."
        ),
        observable_indicator=indicator,
        weight=3.0,
        required=True,
    )


def _build_crit_layer_stack(checkpoints: list[FoldCheckpoint]) -> RubricCriterion:
    """
    CRIT-HYB-3: Layer stacking matches expected count at final state.

    Observable: the final checkpoint's layer count.
    """
    if checkpoints:
        final = checkpoints[-1]
        layer_count = len(final.raw_representation.get("layers", []))
        face_count = len(final.raw_representation.get("faces", {}))
        indicator = (
            f"At the final fold state (frame {final.frame_index}), "
            f"paper has {layer_count} layer plane(s) and {face_count} face(s). "
            "Learner's final model shows the same layer structure when held up to light."
        )
    else:
        indicator = (
            "Final fold state layer count matches the FoldingAgent reconstruction. "
            "No unexpected extra layers from mis-folds."
        )

    return RubricCriterion(
        criterion_id="CRIT-HYB-3",
        name="Layer stack count at final state",
        description=(
            "Learner's completed fold has the correct number of layer planes "
            "at the final state, indicating no mis-folds have created extra layers."
        ),
        observable_indicator=indicator,
        weight=2.0,
        required=False,
    )


def _build_crit_face_orientation(checkpoints: list[FoldCheckpoint]) -> RubricCriterion:
    """
    CRIT-HYB-4: Face orientations (front/back) match at key transitions.

    Observable: which faces are front-side up vs back-side up.
    """
    examples: list[str] = []
    for cp in checkpoints:
        orientations = cp.raw_representation.get("faces_orientations", {})
        back_up = [fid for fid, o in orientations.items() if o == 1]
        if back_up:
            examples.append(
                f"frame {cp.frame_index}: face(s) {back_up[:3]} back-side up"
            )
        if len(examples) >= 2:
            break

    if examples:
        indicator = (
            "Face orientation matches reconstruction at key transitions: "
            + "; ".join(examples)
            + ". Front-side colour visible on correct faces."
        )
    else:
        indicator = (
            "All faces maintain correct front/back orientation throughout the fold sequence. "
            "No accidental flips observed."
        )

    return RubricCriterion(
        criterion_id="CRIT-HYB-4",
        name="Face orientation fidelity",
        description=(
            "Learner maintains the correct front/back-side orientation on each face "
            "throughout the fold sequence."
        ),
        observable_indicator=indicator,
        weight=1.0,
        required=False,
    )


def _build_crit_final_state(checkpoints: list[FoldCheckpoint]) -> RubricCriterion:
    """
    CRIT-HYB-5: Final paper state matches the last critic-verified checkpoint.

    Observable: critic-verified final state reached.
    """
    if checkpoints:
        final = checkpoints[-1]
        verdict_tag = (
            "critic-verified (MATCH)"
            if not final.selected_by_comparator
            else "comparator-selected (best available)"
        )
        analysis_snippet = (final.critic_analysis or "")[:150]
        indicator = (
            f"Learner reaches the final reconstructed paper state "
            f"at frame {final.frame_index} ({verdict_tag}). "
            + (f"Expected appearance: {analysis_snippet}" if analysis_snippet else "")
        )
    else:
        indicator = "Learner reaches the final reconstructed paper state."

    return RubricCriterion(
        criterion_id="CRIT-HYB-5",
        name="Final state match",
        description=(
            "Learner's completed model matches the final paper state from "
            "the FoldingAgent reconstruction."
        ),
        observable_indicator=indicator,
        weight=3.0,
        required=True,
    )


# ---------------------------------------------------------------------------
# RubricSynthesizer
# ---------------------------------------------------------------------------

class RubricSynthesizer:
    """
    Synthesizes a RubricDefinition from FoldingAgent checkpoint geometry.

    Produces 5 criteria (CRIT-HYB-1 through CRIT-HYB-5) derived from:
      - Operation sequence (fold order)
      - Edge M/V assignments (crease polarity)
      - Layer count at final state
      - Face orientation transitions
      - Final checkpoint critic verdict

    Does not use canonical origami criteria (CRIT-CORNER-ALIGN etc.).
    Does not make any LLM calls.

    Parameters
    ----------
    passing_score_fraction : float
        Fraction of max_possible_score to use as passing_score (default 0.7).
    """

    def __init__(self, passing_score_fraction: float = 0.7) -> None:
        if not 0.0 < passing_score_fraction <= 1.0:
            raise ValueError(f"passing_score_fraction must be in (0, 1]: {passing_score_fraction}")
        self.passing_score_fraction = passing_score_fraction

    def synthesize(
        self,
        checkpoints: list[FoldCheckpoint],
        rubric_id: str | None = None,
        skill_id: str = "skill-origami-hybrid",
        title: str = "Hybrid Origami Fold Sequence Rubric",
    ) -> RubricDefinition:
        """
        Build a RubricDefinition from the checkpoint sequence.

        Parameters
        ----------
        checkpoints : list[FoldCheckpoint]
            Loaded and sorted checkpoints from FoldingAgentAdapter.
        rubric_id : str | None
            Defaults to "rubric.origami-hybrid.1".
        skill_id : str
            Skill identifier — defaults to "skill-origami-hybrid".
        title : str
            Rubric title.
        """
        rid = rubric_id or "rubric.origami-hybrid.1"

        criteria = [
            _build_crit_fold_order(checkpoints),
            _build_crit_crease_polarity(checkpoints),
            _build_crit_layer_stack(checkpoints),
            _build_crit_face_orientation(checkpoints),
            _build_crit_final_state(checkpoints),
        ]

        max_score = sum(c.weight for c in criteria)
        passing_score = round(max_score * self.passing_score_fraction, 1)

        return RubricDefinition(
            rubric_id=rid,
            skill_id=skill_id,
            title=title,
            description=(
                "Synthesized from FoldingAgent geometric reconstruction. "
                "Criteria are derived from edge M/V assignments, layer counts, "
                "face orientations, and critic-verified states. "
                "Criterion IDs: CRIT-HYB-1 through CRIT-HYB-5."
            ),
            criteria=criteria,
            passing_score=passing_score,
        )

    def generate_practice_task(
        self,
        rubric: RubricDefinition,
        package_id: str,
        task_id: str | None = None,
        title: str = "Fold the Origami Sequence",
    ) -> PracticeTask:
        """
        Generate a PracticeTask from the rubric.

        Parameters
        ----------
        rubric : RubricDefinition
            The synthesized rubric.
        package_id : str
            ID of the KnowledgePackage being practiced.
        task_id : str | None
            Defaults to "task.origami-hybrid.1".
        title : str
            Task title.
        """
        tid = task_id or "task.origami-hybrid.1"

        # Build instructions from required criteria
        required_criteria = [c for c in rubric.criteria if c.required]
        steps = [
            f"- {c.name}: {c.observable_indicator[:120]}"
            for c in required_criteria
        ]
        instructions = (
            "Fold the origami sequence demonstrated in the source video, "
            "achieving the following required criteria:\n"
            + "\n".join(steps)
        )

        return PracticeTask(
            task_id=tid,
            package_id=package_id,
            rubric_id=rubric.rubric_id,
            title=title,
            instructions=instructions,
            constraints=[
                TaskConstraint(
                    constraint_type="material",
                    description="Use square paper of consistent weight (e.g. 15cm kami or copy paper)",
                )
            ],
            target_criteria_ids=[c.criterion_id for c in rubric.criteria],
        )
