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


# ---------------------------------------------------------------------------
# GeminiRubricSynthesizer  (v2 — requires GOOGLE_API_KEY)
# ---------------------------------------------------------------------------

class GeminiRubricSynthesizer:
    """
    LLM-driven rubric synthesizer.  v2 of RubricSynthesizer.

    Uses Gemini to produce richer, more context-specific observable_indicator
    text for each of the 5 CRIT-HYB-N criteria, informed by the full fold
    sequence geometry.

    Falls back to v1 heuristic criteria if the LLM response is malformed.

    Parameters
    ----------
    model_id : str
        Gemini model (default: gemini-3.8-flash).
    api_key : str | None
        GOOGLE_API_KEY — falls back to environment / .env.
    prompt_path : Path | None
        Override the default prompt file.
    passing_score_fraction : float
        Passed through to RubricDefinition (default 0.7).
    """

    DEFAULT_MODEL = "gemini-3.8-flash"
    PROMPT_FILE = Path(__file__).parent / "prompts" / "rubric_synth_v1.txt"

    def __init__(
        self,
        model_id: str | None = None,
        api_key: str | None = None,
        prompt_path: Path | None = None,
        passing_score_fraction: float = 0.7,
    ) -> None:
        self.model_id = model_id or self.DEFAULT_MODEL
        self._api_key = api_key
        self._prompt_path = prompt_path or self.PROMPT_FILE
        self.passing_score_fraction = passing_score_fraction
        self._client: Any = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(
        self,
        checkpoints: list[FoldCheckpoint],
        rubric_id: str | None = None,
        skill_id: str = "skill-origami-hybrid",
        title: str = "Hybrid Origami Fold Sequence Rubric (LLM-enriched)",
    ) -> RubricDefinition:
        """
        Synthesize a RubricDefinition using Gemini for richer criteria text.

        Falls back to v1 heuristic synthesizer if LLM output is invalid.
        """
        import json as _json

        rid = rubric_id or "rubric.origami-hybrid.llm.1"

        # Build summary inputs for the prompt
        fold_summary = self._fold_summary(checkpoints)
        mv_summary = self._mv_summary(checkpoints)
        final_desc = self._final_desc(checkpoints)
        total_ops = sum(len(cp.operations) for cp in checkpoints)
        final_layers = len(checkpoints[-1].raw_representation.get("layers", [])) if checkpoints else 0

        prompt_template = self._prompt_path.read_text(encoding="utf-8")
        prompt = prompt_template.format(
            skill_id=skill_id,
            fold_sequence_summary=fold_summary,
            mountain_valley_summary=mv_summary,
            final_state_description=final_desc,
            total_operations=total_ops,
            layer_count_at_final=final_layers,
        )

        client = self._ensure_client()
        raw_response = self._call_gemini(client, prompt)

        # Parse JSON response; fall back to v1 on any parse/validation error
        try:
            criteria_dicts = _json.loads(raw_response)
            criteria = [
                RubricCriterion(
                    criterion_id=c["criterion_id"],
                    name=c["name"],
                    description=c["description"],
                    observable_indicator=c["observable_indicator"],
                    weight=float(c["weight"]),
                    required=bool(c["required"]),
                )
                for c in criteria_dicts
            ]
            if len(criteria) != 5:
                raise ValueError(f"Expected 5 criteria, got {len(criteria)}")
        except Exception:
            # Fall back to v1 heuristic
            fallback = RubricSynthesizer(self.passing_score_fraction)
            return fallback.synthesize(checkpoints, rubric_id=rid, skill_id=skill_id, title=title)

        max_score = sum(c.weight for c in criteria)
        passing_score = round(max_score * self.passing_score_fraction, 1)

        return RubricDefinition(
            rubric_id=rid,
            skill_id=skill_id,
            title=title,
            description=(
                "LLM-enriched rubric synthesized by GeminiRubricSynthesizer v2 "
                "from FoldingAgent geometric reconstruction. "
                "Criterion IDs: CRIT-HYB-1 through CRIT-HYB-5."
            ),
            criteria=criteria,
            passing_score=passing_score,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fold_summary(self, checkpoints: list[FoldCheckpoint]) -> str:
        parts = []
        for cp in checkpoints:
            ops = [op.get("function", "?") for op in cp.operations if op.get("function")]
            if ops:
                parts.append(f"frame {cp.frame_index}: {', '.join(ops)}")
        return "; ".join(parts) if parts else "no operations recorded"

    def _mv_summary(self, checkpoints: list[FoldCheckpoint]) -> str:
        lines = []
        for cp in checkpoints:
            edges = cp.raw_representation.get("edges", [])
            m = [[e[0], e[1]] for e in edges if len(e) >= 3 and str(e[2]).upper() == "M"]
            v = [[e[0], e[1]] for e in edges if len(e) >= 3 and str(e[2]).upper() == "V"]
            if m or v:
                lines.append(f"frame {cp.frame_index}: M={m}, V={v}")
        return "; ".join(lines) if lines else "no mountain/valley edges detected"

    def _final_desc(self, checkpoints: list[FoldCheckpoint]) -> str:
        if not checkpoints:
            return "no final state"
        cp = checkpoints[-1]
        raw = cp.raw_representation
        return (
            f"frame {cp.frame_index}, verdict={cp.critic_verdict}, "
            f"faces={len(raw.get('faces', {}))}, "
            f"layers={len(raw.get('layers', []))}, "
            f"analysis: {(cp.critic_analysis or '')[:150]}"
        )

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        key = self._api_key or self._load_env_key()
        if not key:
            raise RuntimeError(
                "GOOGLE_API_KEY not set. Add it to research/origami_hybrid/.env."
            )
        from google import genai
        from google.genai import types
        self._client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(timeout=60_000),
        )
        return self._client

    @staticmethod
    def _load_env_key() -> str:
        import os
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent / ".env", override=False)
        except ImportError:
            pass
        return os.environ.get("GOOGLE_API_KEY", "")

    def _call_gemini(self, client: Any, prompt: str) -> str:
        """Call Gemini with fixed-interval retry on 429 and 5xx."""
        import time
        from google.genai import types
        from google.genai.errors import ClientError, ServerError

        max_retries = 3
        retry_wait = 60.0

        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=1024,
                        response_mime_type="application/json",
                    ),
                )
                return (response.text or "").strip()
            except (ClientError, ServerError) as exc:
                retryable = (
                    (isinstance(exc, ClientError) and exc.code == 429) or
                    isinstance(exc, ServerError)
                )
                if retryable and attempt < max_retries:
                    time.sleep(retry_wait)
                    continue
                raise
