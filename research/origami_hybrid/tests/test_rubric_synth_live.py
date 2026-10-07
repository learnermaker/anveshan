"""
Live tests for GeminiRubricSynthesizer v2 (commit 11).

Requires GOOGLE_API_KEY in research/origami_hybrid/.env.
Run with:
  cd research/origami_hybrid
  python -m pytest tests/test_rubric_synth_live.py -m live -v

Skipped automatically when GOOGLE_API_KEY is absent or daily quota exhausted.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMON = _REPO_ROOT / "tracks" / "common"
if str(_COMMON) not in sys.path:
    sys.path.insert(0, str(_COMMON))

from schemas.rubric import RubricDefinition


def _load_key() -> str:
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parents[1] / ".env", override=False)
    except ImportError:
        pass
    return os.environ.get("GOOGLE_API_KEY", "")


def _load_checkpoints(tmp_path: Path):
    from adapter import FoldingAgentAdapter
    run_dir = tmp_path / "run_live_rubric"
    logs_dir = run_dir / "logs"
    figs_dir = run_dir / "figs"
    logs_dir.mkdir(parents=True)
    figs_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "sample_checkpoint.json", run_dir / "checkpoints.json")
    shutil.copy(FIXTURES / "sample_attempt_tree.json", logs_dir / "attempt_tree.json")
    shutil.copy(FIXTURES / "sample_frames.json", run_dir / "frames.json")
    (figs_dir / "attempt_n0_render.png").write_bytes(b"PNG")
    (figs_dir / "attempt_n1_render.png").write_bytes(b"PNG")
    vm = tmp_path / "video_meta.json"
    shutil.copy(FIXTURES / "video_meta.json", vm)
    ad = FoldingAgentAdapter(
        fold_output_dir=run_dir, video_meta_path=vm, run_id="run_live_rubric",
    )
    return ad.load_checkpoints()


pytestmark = pytest.mark.live


@pytest.fixture(scope="module", autouse=True)
def require_api_key():
    key = _load_key()
    if not key:
        pytest.skip("GOOGLE_API_KEY not set — skipping live tests")


class TestGeminiRubricSynthesizer:
    def test_synthesize_returns_rubric(self, tmp_path: Path) -> None:
        from rubric_synth import GeminiRubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = GeminiRubricSynthesizer().synthesize(cps)
        assert isinstance(rubric, RubricDefinition)

    def test_rubric_validates_pydantic(self, tmp_path: Path) -> None:
        from rubric_synth import GeminiRubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = GeminiRubricSynthesizer().synthesize(cps)
        RubricDefinition.model_validate(rubric.model_dump())

    def test_exactly_five_criteria(self, tmp_path: Path) -> None:
        from rubric_synth import GeminiRubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = GeminiRubricSynthesizer().synthesize(cps)
        assert len(rubric.criteria) == 5

    def test_criterion_ids_are_crit_hyb_n(self, tmp_path: Path) -> None:
        from rubric_synth import GeminiRubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = GeminiRubricSynthesizer().synthesize(cps)
        ids = [c.criterion_id for c in rubric.criteria]
        assert ids == ["CRIT-HYB-1", "CRIT-HYB-2", "CRIT-HYB-3", "CRIT-HYB-4", "CRIT-HYB-5"]

    def test_no_canonical_criteria_ids(self, tmp_path: Path) -> None:
        from rubric_synth import GeminiRubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = GeminiRubricSynthesizer().synthesize(cps)
        canonical = {"CRIT-CORNER-ALIGN", "CRIT-VALLEY-FOLD", "CRIT-BONE-CREASE"}
        assert {c.criterion_id for c in rubric.criteria}.isdisjoint(canonical)

    def test_observable_indicators_non_empty(self, tmp_path: Path) -> None:
        from rubric_synth import GeminiRubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = GeminiRubricSynthesizer().synthesize(cps)
        for c in rubric.criteria:
            assert c.observable_indicator.strip() != ""

    def test_required_flags_correct(self, tmp_path: Path) -> None:
        from rubric_synth import GeminiRubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = GeminiRubricSynthesizer().synthesize(cps)
        by_id = {c.criterion_id: c for c in rubric.criteria}
        assert by_id["CRIT-HYB-1"].required is True
        assert by_id["CRIT-HYB-2"].required is True
        assert by_id["CRIT-HYB-5"].required is True

    def test_fallback_on_bad_model_response(self, tmp_path: Path) -> None:
        """GeminiRubricSynthesizer must fall back to v1 if LLM returns garbage."""
        from rubric_synth import GeminiRubricSynthesizer, RubricSynthesizer
        from unittest.mock import patch

        cps = _load_checkpoints(tmp_path)
        synth = GeminiRubricSynthesizer()

        with patch.object(synth, "_call_gemini", return_value="not valid json {{{"):
            rubric = synth.synthesize(cps)

        # Should still produce 5 valid CRIT-HYB-N criteria (v1 fallback)
        assert len(rubric.criteria) == 5
        ids = [c.criterion_id for c in rubric.criteria]
        assert ids == ["CRIT-HYB-1", "CRIT-HYB-2", "CRIT-HYB-3", "CRIT-HYB-4", "CRIT-HYB-5"]
