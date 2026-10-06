"""
Tests for FoldStateLogWriter and CreaseEvidenceWriter (commit 4).

All offline — no LLM, no network.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_adapter(tmp_path: Path):
    from adapter import FoldingAgentAdapter
    import shutil as _shutil

    run_dir = tmp_path / "run_test"
    logs_dir = run_dir / "logs"
    figs_dir = run_dir / "figs"
    logs_dir.mkdir(parents=True)
    figs_dir.mkdir(parents=True)

    _shutil.copy(FIXTURES / "sample_checkpoint.json", run_dir / "checkpoints.json")
    _shutil.copy(FIXTURES / "sample_attempt_tree.json", logs_dir / "attempt_tree.json")
    _shutil.copy(FIXTURES / "sample_frames.json", run_dir / "frames.json")
    (figs_dir / "attempt_n0_render.png").write_bytes(b"PNG")
    (figs_dir / "attempt_n1_render.png").write_bytes(b"PNG")

    video_meta = tmp_path / "video_meta.json"
    _shutil.copy(FIXTURES / "video_meta.json", video_meta)

    ad = FoldingAgentAdapter(
        fold_output_dir=run_dir,
        video_meta_path=video_meta,
        source_attribution="Test, CC BY 3.0",
        run_id="run_test",
    )
    ad.load_checkpoints()
    return ad


# ---------------------------------------------------------------------------
# TestFoldStateLogWriter
# ---------------------------------------------------------------------------

class TestFoldStateLogWriter:
    def test_file_written(self, tmp_path: Path) -> None:
        from sidecars import FoldStateLogWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "output" / "fold_state_log.json"
        w = FoldStateLogWriter()
        w.write(ad._checkpoints, out, run_id="run_test", fps=24.0)
        assert out.exists()

    def test_schema_field(self, tmp_path: Path) -> None:
        from sidecars import FoldStateLogWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "fold_state_log.json"
        w = FoldStateLogWriter()
        doc = w.write(ad._checkpoints, out, run_id="run_test", fps=24.0)
        assert doc["$schema"] == "fold_state_log_v1"

    def test_run_id_and_fps(self, tmp_path: Path) -> None:
        from sidecars import FoldStateLogWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "fold_state_log.json"
        doc = FoldStateLogWriter().write(ad._checkpoints, out, run_id="run_test", fps=24.0)
        assert doc["run_id"] == "run_test"
        assert doc["fps"] == pytest.approx(24.0)

    def test_two_states(self, tmp_path: Path) -> None:
        from sidecars import FoldStateLogWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "fold_state_log.json"
        doc = FoldStateLogWriter().write(ad._checkpoints, out, run_id="run_test", fps=24.0)
        assert len(doc["states"]) == 2

    def test_state_fields_present(self, tmp_path: Path) -> None:
        from sidecars import FoldStateLogWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "fold_state_log.json"
        doc = FoldStateLogWriter().write(ad._checkpoints, out, run_id="run_test", fps=24.0)
        required = {
            "frame_index", "keyframe_global_index", "timestamp_sec",
            "critic_verdict", "selected_by_comparator", "operations_delta",
            "render_png_path", "critic_analysis", "raw_representation",
            "image_evidence_id", "video_evidence_id",
        }
        for state in doc["states"]:
            assert required.issubset(state.keys())

    def test_image_evidence_id_format(self, tmp_path: Path) -> None:
        from sidecars import FoldStateLogWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "fold_state_log.json"
        doc = FoldStateLogWriter().write(ad._checkpoints, out, run_id="run_test", fps=24.0)
        assert doc["states"][0]["image_evidence_id"] == "ev.fa.img.01"
        assert doc["states"][1]["image_evidence_id"] == "ev.fa.img.02"

    def test_video_evidence_id_present_when_timestamp(self, tmp_path: Path) -> None:
        from sidecars import FoldStateLogWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "fold_state_log.json"
        doc = FoldStateLogWriter().write(ad._checkpoints, out, run_id="run_test", fps=24.0)
        # Both checkpoints have timestamps in the fixture
        for state in doc["states"]:
            assert state["video_evidence_id"] is not None

    def test_raw_representation_preserved(self, tmp_path: Path) -> None:
        from sidecars import FoldStateLogWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "fold_state_log.json"
        doc = FoldStateLogWriter().write(ad._checkpoints, out, run_id="run_test", fps=24.0)
        for state in doc["states"]:
            rr = state["raw_representation"]
            assert "vertices" in rr
            assert "edges" in rr

    def test_json_round_trip(self, tmp_path: Path) -> None:
        from sidecars import FoldStateLogWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "fold_state_log.json"
        FoldStateLogWriter().write(ad._checkpoints, out, run_id="run_test", fps=24.0)
        reloaded = json.loads(out.read_text())
        assert reloaded["$schema"] == "fold_state_log_v1"
        assert len(reloaded["states"]) == 2


# ---------------------------------------------------------------------------
# TestCreaseEvidenceWriter
# ---------------------------------------------------------------------------

class TestCreaseEvidenceWriter:
    def test_file_written(self, tmp_path: Path) -> None:
        from sidecars import CreaseEvidenceWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")
        assert out.exists()

    def test_schema_field(self, tmp_path: Path) -> None:
        from sidecars import CreaseEvidenceWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        doc = CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")
        assert doc["$schema"] == "crease_evidence_v1"

    def test_two_keyframe_crease_maps(self, tmp_path: Path) -> None:
        from sidecars import CreaseEvidenceWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        doc = CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")
        assert len(doc["keyframe_crease_maps"]) == 2

    def test_crease_map_fields_present(self, tmp_path: Path) -> None:
        from sidecars import CreaseEvidenceWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        doc = CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")
        required = {
            "frame_index", "mountain_edges", "valley_edges", "flat_edges",
            "boundary_edges", "mountain_count", "valley_count",
            "layer_count", "face_count", "faces_back_up", "image_evidence_id",
        }
        for cm in doc["keyframe_crease_maps"]:
            assert required.issubset(cm.keys())

    def test_frame1_boundary_edges_only(self, tmp_path: Path) -> None:
        """Frame 1 is a flat square — all edges are boundary (B), no M/V."""
        from sidecars import CreaseEvidenceWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        doc = CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")
        f1 = doc["keyframe_crease_maps"][0]
        assert f1["frame_index"] == 1
        assert f1["mountain_count"] == 0
        assert f1["valley_count"] == 0
        assert len(f1["boundary_edges"]) == 4

    def test_frame2_has_mountain_and_valley(self, tmp_path: Path) -> None:
        """Frame 2 has a fold: edges [1,5]=M and [2,5]=V."""
        from sidecars import CreaseEvidenceWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        doc = CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")
        f2 = doc["keyframe_crease_maps"][1]
        assert f2["frame_index"] == 2
        assert f2["mountain_count"] == 1
        assert f2["valley_count"] == 1

    def test_frame2_back_face_detected(self, tmp_path: Path) -> None:
        """Frame 2 has faces_orientations: face '3' = 1 (back side up)."""
        from sidecars import CreaseEvidenceWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        doc = CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")
        f2 = doc["keyframe_crease_maps"][1]
        assert "3" in f2["faces_back_up"]

    def test_layer_count(self, tmp_path: Path) -> None:
        """Frame 1 has 1 layer plane; frame 2 has 2."""
        from sidecars import CreaseEvidenceWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        doc = CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")
        assert doc["keyframe_crease_maps"][0]["layer_count"] == 1
        assert doc["keyframe_crease_maps"][1]["layer_count"] == 2

    def test_image_evidence_id_links_match_adapter(self, tmp_path: Path) -> None:
        """image_evidence_id must match the IDs produced by FoldingAgentAdapter."""
        from sidecars import CreaseEvidenceWriter
        from schemas.evidence import Modality
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        doc = CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")

        adapter_image_ids = {
            r.evidence_id
            for r in ad.to_evidence_refs()
            if r.modality == Modality.IMAGE
        }
        sidecar_ids = {
            cm["image_evidence_id"]
            for cm in doc["keyframe_crease_maps"]
        }
        assert sidecar_ids == adapter_image_ids

    def test_json_round_trip(self, tmp_path: Path) -> None:
        from sidecars import CreaseEvidenceWriter
        ad = _load_adapter(tmp_path)
        out = tmp_path / "crease_evidence.json"
        CreaseEvidenceWriter().write(ad._checkpoints, out, run_id="run_test")
        reloaded = json.loads(out.read_text())
        assert reloaded["$schema"] == "crease_evidence_v1"
        assert len(reloaded["keyframe_crease_maps"]) == 2
