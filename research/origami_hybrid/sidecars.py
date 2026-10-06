"""
Sidecar writers for the hybrid origami pipeline.

Two JSON sidecar files carry the full FoldingAgent geometry without
touching the frozen Anveshan contract seam:

  fold_state_log.json      — per-checkpoint geometry, timestamps, critic verdicts
  crease_evidence.json     — per-checkpoint crease-pattern summary (M/V/F/B edges)

Both files link back to the EvidenceRef IDs produced by FoldingAgentAdapter,
so downstream tooling can join geometry ↔ contracts without parsing contracts.

Nothing here modifies tracks/common/schemas/ or tracks/track-a/src/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapter import FoldCheckpoint


# ---------------------------------------------------------------------------
# FoldStateLogWriter
# ---------------------------------------------------------------------------

class FoldStateLogWriter:
    """
    Writes fold_state_log.json.

    Schema (fold_state_log_v1)
    --------------------------
    {
      "$schema": "fold_state_log_v1",
      "run_id": str,
      "fps": float | null,
      "states": [
        {
          "frame_index": int,
          "keyframe_global_index": int | null,
          "timestamp_sec": float | null,
          "critic_verdict": str,
          "selected_by_comparator": bool,
          "operations_delta": [{"function": str, "params": dict, "assign_to": str|null}],
          "render_png_path": str | null,
          "critic_analysis": str,
          "raw_representation": {
            "vertices": {...},
            "faces": {...},
            "faces_orientations": {...},
            "edges": [...],
            "layers": [...]
          },
          "image_evidence_id": str,    # links to EvidenceRef in KnowledgePackage
          "video_evidence_id": str | null
        }
      ]
    }
    """

    SCHEMA = "fold_state_log_v1"

    def write(
        self,
        checkpoints: list[FoldCheckpoint],
        output_path: Path,
        run_id: str,
        fps: float | None,
    ) -> dict[str, Any]:
        """
        Serialize all checkpoints to fold_state_log.json.

        Returns the written dict (for testing without touching disk).
        """
        states = []
        for cp in checkpoints:
            states.append({
                "frame_index": cp.frame_index,
                "keyframe_global_index": cp.keyframe_global_index,
                "timestamp_sec": cp.timestamp_sec,
                "critic_verdict": cp.critic_verdict,
                "selected_by_comparator": cp.selected_by_comparator,
                "operations_delta": cp.operations,
                "render_png_path": (
                    str(cp.render_png_path) if cp.render_png_path else None
                ),
                "critic_analysis": cp.critic_analysis,
                "raw_representation": cp.raw_representation,
                # Link back to EvidenceRef IDs from FoldingAgentAdapter
                "image_evidence_id": f"ev.fa.img.{cp.frame_index:02d}",
                "video_evidence_id": (
                    f"ev.fa.vid.{cp.frame_index:02d}"
                    if cp.timestamp_sec is not None
                    else None
                ),
            })

        doc: dict[str, Any] = {
            "$schema": self.SCHEMA,
            "run_id": run_id,
            "fps": fps,
            "states": states,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return doc


# ---------------------------------------------------------------------------
# CreaseEvidenceWriter
# ---------------------------------------------------------------------------

class CreaseEvidenceWriter:
    """
    Writes crease_evidence.json.

    Extracts per-checkpoint crease-pattern summary from the raw geometry:
    mountain (M), valley (V), flat (F), and boundary (B) edge counts and lists.

    Schema (crease_evidence_v1)
    ---------------------------
    {
      "$schema": "crease_evidence_v1",
      "run_id": str,
      "keyframe_crease_maps": [
        {
          "frame_index": int,
          "mountain_edges": [[u, v]],
          "valley_edges": [[u, v]],
          "flat_edges": [[u, v]],
          "boundary_edges": [[u, v]],
          "mountain_count": int,
          "valley_count": int,
          "layer_count": int,       # len(layers)
          "face_count": int,        # len(faces)
          "faces_back_up": [str],   # face IDs with faces_orientations==1
          "image_evidence_id": str  # links to EvidenceRef
        }
      ]
    }
    """

    SCHEMA = "crease_evidence_v1"

    # FoldingAgent edge kind constants
    _MOUNTAIN = "M"
    _VALLEY = "V"
    _FLAT = "F"
    _BOUNDARY = "B"

    def write(
        self,
        checkpoints: list[FoldCheckpoint],
        output_path: Path,
        run_id: str,
    ) -> dict[str, Any]:
        """
        Serialize crease patterns to crease_evidence.json.

        Returns the written dict (for testing without touching disk).
        """
        crease_maps = []
        for cp in checkpoints:
            crease_maps.append(self._extract(cp))

        doc: dict[str, Any] = {
            "$schema": self.SCHEMA,
            "run_id": run_id,
            "keyframe_crease_maps": crease_maps,
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return doc

    # ------------------------------------------------------------------

    def _extract(self, cp: FoldCheckpoint) -> dict[str, Any]:
        raw = cp.raw_representation
        edges: list = raw.get("edges", [])
        faces: dict = raw.get("faces", {})
        layers: list = raw.get("layers", [])
        orientations: dict = raw.get("faces_orientations", {})

        mountain: list[list[int]] = []
        valley: list[list[int]] = []
        flat: list[list[int]] = []
        boundary: list[list[int]] = []

        for edge in edges:
            # edge is [u, v, kind] — kind is a string "M"/"V"/"F"/"B"
            if len(edge) < 3:
                continue
            u, v, kind = edge[0], edge[1], str(edge[2]).upper()
            pair = [int(u), int(v)]
            if kind == self._MOUNTAIN:
                mountain.append(pair)
            elif kind == self._VALLEY:
                valley.append(pair)
            elif kind == self._FLAT:
                flat.append(pair)
            else:  # B or unknown
                boundary.append(pair)

        faces_back_up = [
            fid for fid, orient in orientations.items() if orient == 1
        ]

        return {
            "frame_index": cp.frame_index,
            "mountain_edges": mountain,
            "valley_edges": valley,
            "flat_edges": flat,
            "boundary_edges": boundary,
            "mountain_count": len(mountain),
            "valley_count": len(valley),
            "layer_count": len(layers),
            "face_count": len(faces),
            "faces_back_up": faces_back_up,
            "image_evidence_id": f"ev.fa.img.{cp.frame_index:02d}",
        }
