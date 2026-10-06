"""
FoldingAgentAdapter — converts FoldingAgent run output to Anveshan contracts.

This module is a pure data-transformation layer.  It makes NO LLM calls.
Epistemic assignment is deterministic:
  - critic_verdict == "MATCH"  →  is_observed=True,  verification_state=OBSERVED, confidence=1.0
  - comparator-selected         →  is_observed=False, verification_state=INFERRED, confidence=0.5

The adapter imports contract classes ONLY from tracks/common/schemas/ (the frozen
seam).  It does NOT import from tracks/track-a/src/.

Usage
-----
    from adapter import FoldingAgentAdapter

    adapter = FoldingAgentAdapter(
        fold_output_dir=Path("out/run_20260101_120000_gemini_crane/"),
        video_meta_path=Path("data/crane/video_meta.json"),
        source_attribution="User-supplied video — add attribution here",
    )
    checkpoints = adapter.load_checkpoints()
    knowledge_package = adapter.build_knowledge_package()
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve common schemas (read-only — do NOT import from tracks/track-a/src/)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]  # …/anveshan/
_COMMON_SCHEMAS = _REPO_ROOT / "tracks" / "common" / "schemas"

if str(_COMMON_SCHEMAS.parent) not in sys.path:
    sys.path.insert(0, str(_COMMON_SCHEMAS.parent))

from schemas.evidence import EvidenceRef, Modality, VerificationState  # noqa: E402
from schemas.knowledge import (  # noqa: E402
    ClaimType,
    ConsentMetadata,
    ExpertReview,
    KnowledgeClaim,
    KnowledgePackage,
    ReviewStatus,
)


# ---------------------------------------------------------------------------
# Internal data class
# ---------------------------------------------------------------------------

@dataclass
class FoldCheckpoint:
    """Parsed representation of one FoldingAgent checkpoint entry."""

    frame_index: int
    """1-based position within the agent's keyframe sequence."""

    raw_representation: dict[str, Any]
    """GeometryState.raw_representation — vertices, faces, edges, layers."""

    operations: list[dict[str, Any]]
    """GeometryFunctionCall list: [{"function": str, "params": dict, "assign_to": str|None}]"""

    paper_colors: dict[str, str]
    """{"front_color": str, "back_color": str}"""

    critic_verdict: str
    """'MATCH', 'MISMATCH', 'EXTREME DIVERGANCE', or 'COMPARATOR' (our label)."""

    critic_analysis: str
    """Prose analysis from the critic or comparator selection note."""

    selected_by_comparator: bool
    """True when no MATCH verdict was reached and the comparator chose the best attempt."""

    render_png_path: Path | None
    """Absolute path to the rendered PNG diagram for this checkpoint (may be None)."""

    timestamp_sec: float | None
    """keyframe_global_index / fps — set by adapter using video_meta.json."""

    keyframe_global_index: int | None = field(default=None)
    """Global frame index as listed in keyframes.json (used for timestamp calc)."""


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class FoldingAgentAdapter:
    """
    Converts a FoldingAgent run directory into Anveshan contract objects.

    Parameters
    ----------
    fold_output_dir : Path
        FoldingAgent run directory containing:
          checkpoints.json, logs/attempt_tree.json, frames.json
    video_meta_path : Path
        Path to video_meta.json produced by KeyframeExtractor.
        Must contain {"fps": float, ...}.
    source_attribution : str
        Human-readable attribution for the source video
        (e.g. "Tavin, CC BY 3.0, …").  Written into ConsentMetadata.notes.
    run_id : str | None
        Explicit run identifier.  Defaults to the run directory name.
    """

    MATCH_VERDICT = "MATCH"
    COMPARATOR_VERDICT = "COMPARATOR"  # our internal label for comparator-selected states

    def __init__(
        self,
        fold_output_dir: Path,
        video_meta_path: Path,
        source_attribution: str = "",
        run_id: str | None = None,
    ) -> None:
        self.fold_output_dir = Path(fold_output_dir)
        self.video_meta_path = Path(video_meta_path)
        self.source_attribution = source_attribution
        self.run_id = run_id or self.fold_output_dir.name

        self._fps: float | None = None
        self._checkpoints: list[FoldCheckpoint] | None = None
        self._frames_data: list[str] | None = None

    # ------------------------------------------------------------------
    # Step 1 — load raw FoldingAgent output files
    # ------------------------------------------------------------------

    def load_checkpoints(self) -> list[FoldCheckpoint]:
        """
        Parse checkpoints.json and attempt_tree.json into FoldCheckpoint list.

        File locations (relative to fold_output_dir):
          checkpoints.json
          logs/attempt_tree.json
          frames.json

        Field mappings
        ~~~~~~~~~~~~~~
        checkpoints.json key (str)          → FoldCheckpoint.frame_index (int)
        checkpoints[n]["raw_representation"] → FoldCheckpoint.raw_representation
        checkpoints[n]["operations"]         → FoldCheckpoint.operations
          each {"function": str, "params": dict, "assign_to": str|None}
        checkpoints[n]["paper_colors"]       → FoldCheckpoint.paper_colors

        attempt_tree["_checkpoint_node"][str(n)] → node_id (str)
        attempt_tree["nodes"][node_id]["critic_verdict"]   → critic_verdict
        attempt_tree["nodes"][node_id]["critic_analysis"]  → critic_analysis
        attempt_tree["nodes"][node_id]["render_path"]      → render_png_path

        Comparator detection: selected_by_comparator = (critic_verdict != "MATCH")

        Timestamps: keyframe_global_index extracted from frame filename in frames.json;
          timestamp_sec = global_index / fps  (fps from video_meta.json)
        """
        self._fps = self._load_fps()

        checkpoints_path = self.fold_output_dir / "checkpoints.json"
        attempt_tree_path = self.fold_output_dir / "logs" / "attempt_tree.json"
        frames_path = self.fold_output_dir / "frames.json"

        with open(checkpoints_path, encoding="utf-8") as f:
            raw_checkpoints: dict[str, dict[str, Any]] = json.load(f)

        attempt_tree: dict[str, Any] = {}
        if attempt_tree_path.exists():
            with open(attempt_tree_path, encoding="utf-8") as f:
                attempt_tree = json.load(f)

        # frames.json is a list of resolved frame file paths
        frames_list: list[str] = []
        if frames_path.exists():
            with open(frames_path, encoding="utf-8") as f:
                frames_list = json.load(f)
        self._frames_data = frames_list

        # Build global-index lookup from frames list
        # Each entry is an absolute (or relative) path; filename is NNNNNN.jpg
        global_index_by_position: dict[int, int] = {}  # frame_sequence_pos → global_idx
        for pos, fpath in enumerate(frames_list):
            name = Path(fpath).stem
            try:
                global_index_by_position[pos] = int(name)
            except ValueError:
                pass

        checkpoint_node_map: dict[str, str] = attempt_tree.get("_checkpoint_node", {})
        nodes: dict[str, dict[str, Any]] = attempt_tree.get("nodes", {})

        result: list[FoldCheckpoint] = []
        for frame_str, ckpt in raw_checkpoints.items():
            frame_n = int(frame_str)

            # Attempt tree lookup (frame_n is 1-based keyframe sequence position)
            node_id = checkpoint_node_map.get(str(frame_n))
            node = nodes.get(node_id, {}) if node_id else {}

            critic_verdict: str = node.get("critic_verdict") or "UNKNOWN"
            critic_analysis: str = node.get("critic_analysis") or ""
            render_path_str: str | None = node.get("render_path")
            render_png = Path(render_path_str) if render_path_str else None
            selected_by_comparator = critic_verdict != self.MATCH_VERDICT

            # Timestamp: frame_n is 1-based position in the keyframes list
            # Position 0 in frames_list corresponds to keyframe sequence index 1
            keyframe_pos = frame_n - 1
            global_idx = global_index_by_position.get(keyframe_pos)
            timestamp_sec: float | None = None
            if global_idx is not None and self._fps and self._fps > 0:
                timestamp_sec = round(global_idx / self._fps, 3)

            result.append(FoldCheckpoint(
                frame_index=frame_n,
                raw_representation=ckpt.get("raw_representation") or {},
                operations=ckpt.get("operations") or [],
                paper_colors=ckpt.get("paper_colors") or {
                    "front_color": "white",
                    "back_color": "lightblue",
                },
                critic_verdict=critic_verdict,
                critic_analysis=critic_analysis,
                selected_by_comparator=selected_by_comparator,
                render_png_path=render_png,
                timestamp_sec=timestamp_sec,
                keyframe_global_index=global_idx,
            ))

        self._checkpoints = sorted(result, key=lambda c: c.frame_index)
        return self._checkpoints

    # ------------------------------------------------------------------
    # Step 2 — produce EvidenceRef objects
    # ------------------------------------------------------------------

    def to_evidence_refs(self) -> list[EvidenceRef]:
        """
        Produce EvidenceRef objects for each checkpoint.

        Two refs per checkpoint:
          - IMAGE ref pointing to rendered PNG (source: FoldingAgent run)
          - VIDEO ref pointing to source video segment (if timestamp available)

        Epistemic mapping:
          critic_verdict == "MATCH"  → OBSERVED, confidence=1.0
          comparator-selected        → INFERRED,  confidence=0.5

        Field mappings:
          IMAGE ref:
            evidence_id  = "ev.fa.img.{frame_n:02d}"
            source_id    = "src-fa-{run_id}"
            modality     = IMAGE
            cue_excerpt  = critic_analysis (up to 500 chars)
            verification_state / confidence  → from critic_verdict

          VIDEO ref (only when timestamp_sec is available):
            evidence_id  = "ev.fa.vid.{frame_n:02d}"
            source_id    = "src-hybrid-video"
            modality     = VIDEO
            start_sec    = checkpoint.timestamp_sec
            end_sec      = next checkpoint timestamp_sec (or start + 5.0)
            verification_state / confidence  → same as IMAGE ref
        """
        if self._checkpoints is None:
            self.load_checkpoints()

        checkpoints = self._checkpoints  # type: ignore[union-attr]
        refs: list[EvidenceRef] = []
        src_fa = f"src-fa-{self.run_id}"

        for i, cp in enumerate(checkpoints):
            vs, conf = self._epistemic(cp)
            excerpt = (cp.critic_analysis or "")[:500]

            # IMAGE evidence ref
            refs.append(EvidenceRef(
                evidence_id=f"ev.fa.img.{cp.frame_index:02d}",
                source_id=src_fa,
                modality=Modality.IMAGE,
                start_sec=None,
                end_sec=None,
                cue_excerpt=excerpt or None,
                verification_state=vs,
                confidence=conf,
            ))

            # VIDEO evidence ref (only if we have a timestamp)
            if cp.timestamp_sec is not None:
                next_ts = (
                    checkpoints[i + 1].timestamp_sec
                    if i + 1 < len(checkpoints) and checkpoints[i + 1].timestamp_sec is not None
                    else cp.timestamp_sec + 5.0
                )
                refs.append(EvidenceRef(
                    evidence_id=f"ev.fa.vid.{cp.frame_index:02d}",
                    source_id="src-hybrid-video",
                    modality=Modality.VIDEO,
                    start_sec=cp.timestamp_sec,
                    end_sec=max(next_ts, cp.timestamp_sec),
                    cue_excerpt=excerpt or None,
                    verification_state=vs,
                    confidence=conf,
                ))

        return refs

    # ------------------------------------------------------------------
    # Step 3 — produce KnowledgeClaim objects
    # ------------------------------------------------------------------

    def to_knowledge_claims(self) -> list[KnowledgeClaim]:
        """
        Produce one KnowledgeClaim per checkpoint (skips the initial flat-square
        checkpoint if it has no operations and is not critic-verified).

        Field mappings:
          claim_id    = "CLM-{frame_n:02d}"
          claim_type  = STEP  (all transitions are steps)
          statement   = critic_analysis, enriched with operation names
          is_observed = not selected_by_comparator
          evidence_refs = [IMAGE_ref, VIDEO_ref?]  (same as to_evidence_refs per frame)

        The initial flat-square frame (frame_index==1, no operations) is included
        as claim CLM-01 with statement "Initial flat square starting state."
        """
        if self._checkpoints is None:
            self.load_checkpoints()

        checkpoints = self._checkpoints  # type: ignore[union-attr]
        claims: list[KnowledgeClaim] = []
        src_fa = f"src-fa-{self.run_id}"

        for i, cp in enumerate(checkpoints):
            vs, conf = self._epistemic(cp)
            excerpt = (cp.critic_analysis or "")[:500]

            # Enrich statement with operation names
            op_names = [op.get("function", "?") for op in cp.operations if op.get("function")]
            if op_names:
                ops_str = ", ".join(op_names)
                statement = f"{excerpt} [operations: {ops_str}]" if excerpt else f"Operations: {ops_str}"
            elif excerpt:
                statement = excerpt
            else:
                statement = (
                    "Initial flat square starting state."
                    if cp.frame_index == 1
                    else f"Fold state at keyframe {cp.frame_index}."
                )

            # Build evidence refs for this claim
            ev_refs: list[EvidenceRef] = [
                EvidenceRef(
                    evidence_id=f"ev.fa.img.{cp.frame_index:02d}",
                    source_id=src_fa,
                    modality=Modality.IMAGE,
                    start_sec=None,
                    end_sec=None,
                    cue_excerpt=excerpt or None,
                    verification_state=vs,
                    confidence=conf,
                )
            ]

            if cp.timestamp_sec is not None:
                next_ts = (
                    checkpoints[i + 1].timestamp_sec
                    if i + 1 < len(checkpoints) and checkpoints[i + 1].timestamp_sec is not None
                    else cp.timestamp_sec + 5.0
                )
                ev_refs.append(EvidenceRef(
                    evidence_id=f"ev.fa.vid.{cp.frame_index:02d}",
                    source_id="src-hybrid-video",
                    modality=Modality.VIDEO,
                    start_sec=cp.timestamp_sec,
                    end_sec=max(next_ts, cp.timestamp_sec),
                    cue_excerpt=excerpt or None,
                    verification_state=vs,
                    confidence=conf,
                ))

            claims.append(KnowledgeClaim(
                claim_id=f"CLM-{cp.frame_index:02d}",
                claim_type=ClaimType.STEP,
                statement=statement,
                is_observed=not cp.selected_by_comparator,
                evidence_refs=ev_refs,
            ))

        return claims

    # ------------------------------------------------------------------
    # Step 4 — build KnowledgePackage
    # ------------------------------------------------------------------

    def build_knowledge_package(
        self,
        package_id: str | None = None,
        skill_id: str = "skill-origami-hybrid",
        title: str = "Origami Fold Sequence (Hybrid Reconstruction)",
        summary: str | None = None,
    ) -> KnowledgePackage:
        """
        Assemble a KnowledgePackage from all checkpoints.

        Parameters
        ----------
        package_id : str | None
            Defaults to "kp.origami-hybrid.<run_id>".
        skill_id : str
            Skill identifier — defaults to "skill-origami-hybrid".
        title : str
            Package title.
        summary : str | None
            Defaults to a generated summary.
        """
        claims = self.to_knowledge_claims()
        n = len(claims)
        pkg_id = package_id or f"kp.origami-hybrid.{self.run_id}"
        pkg_summary = summary or (
            f"Hybrid reconstruction of {n} origami fold states "
            f"via FoldingAgent geometric simulation + Anveshan knowledge grounding. "
            f"Run: {self.run_id}. "
            f"Source attribution: {self.source_attribution or 'not set — please supply attribution.'}"
        )

        consent = ConsentMetadata(
            contributor_name="FoldingAgent Hybrid Pipeline",
            consent_scope="research_prototype",
            revocable=True,
            notes=(
                f"User-supplied origami video. {self.source_attribution or 'Attribution not set — add before use beyond research folder.'}"
            ),
        )

        expert_review = ExpertReview(
            reviewer_name="Pending — human review required",
            status=ReviewStatus.PENDING,
            reviewed_at=None,
            notes=(
                "This knowledge package was produced by the hybrid FoldingAgent + Anveshan pipeline. "
                "An expert must review and approve before the package is used for teaching."
            ),
        )

        return KnowledgePackage(
            package_id=pkg_id,
            skill_id=skill_id,
            title=title,
            summary=pkg_summary,
            claims=claims,
            consent=consent,
            expert_review=expert_review,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_fps(self) -> float:
        """Read fps from video_meta.json."""
        with open(self.video_meta_path, encoding="utf-8") as f:
            meta = json.load(f)
        fps = float(meta["fps"])
        if fps <= 0:
            raise ValueError(f"Invalid fps={fps} in {self.video_meta_path}")
        return fps

    @staticmethod
    def _epistemic(cp: FoldCheckpoint) -> tuple[VerificationState, float]:
        """Return (verification_state, confidence) from the checkpoint's critic result."""
        if cp.selected_by_comparator:
            return VerificationState.INFERRED, 0.5
        return VerificationState.OBSERVED, 1.0
