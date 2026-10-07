"""
Live tests for GeminiEvidenceEnricher (commit 10).

Requires GOOGLE_API_KEY in research/origami_hybrid/.env.
Run with:
  cd research/origami_hybrid
  python -m pytest tests/test_grounding_live.py -m live -v

Skipped automatically in CI (no API key).
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

from schemas.knowledge import KnowledgePackage


def _load_key() -> str:
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parents[1] / ".env", override=False)
    except ImportError:
        pass
    return os.environ.get("GOOGLE_API_KEY", "")


def _adapter_package(tmp_path: Path):
    from adapter import FoldingAgentAdapter

    run_dir = tmp_path / "run_live_test"
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
        fold_output_dir=run_dir, video_meta_path=vm,
        source_attribution="Test CC BY 3.0", run_id="run_live_test",
    )
    checkpoints = ad.load_checkpoints()
    package = ad.build_knowledge_package()
    return package, checkpoints


pytestmark = pytest.mark.live


@pytest.fixture(scope="module", autouse=True)
def require_api_key():
    key = _load_key()
    if not key:
        pytest.skip("GOOGLE_API_KEY not set — skipping live tests")


class TestGeminiEvidenceEnricher:
    def test_enrich_returns_package(self, tmp_path: Path) -> None:
        from grounding import GeminiEvidenceEnricher
        pkg, cps = _adapter_package(tmp_path)
        enricher = GeminiEvidenceEnricher()
        result = enricher.enrich(pkg, cps)
        assert isinstance(result, KnowledgePackage)

    def test_cue_excerpts_non_empty_after_enrichment(self, tmp_path: Path) -> None:
        from grounding import GeminiEvidenceEnricher
        pkg, cps = _adapter_package(tmp_path)
        enricher = GeminiEvidenceEnricher()
        enricher.enrich(pkg, cps)
        for claim in pkg.claims:
            for ev in claim.evidence_refs:
                assert ev.cue_excerpt is not None
                assert len(ev.cue_excerpt.strip()) > 0, (
                    f"Empty cue_excerpt for {ev.evidence_id}"
                )

    def test_enrichment_does_not_change_verification_state(self, tmp_path: Path) -> None:
        from grounding import GeminiEvidenceEnricher
        from schemas.evidence import VerificationState
        pkg, cps = _adapter_package(tmp_path)
        # Record original verification states
        original_states = {
            ev.evidence_id: ev.verification_state
            for claim in pkg.claims
            for ev in claim.evidence_refs
        }
        GeminiEvidenceEnricher().enrich(pkg, cps)
        for claim in pkg.claims:
            for ev in claim.evidence_refs:
                assert ev.verification_state == original_states[ev.evidence_id], (
                    f"verification_state changed for {ev.evidence_id}"
                )

    def test_enrichment_does_not_change_confidence(self, tmp_path: Path) -> None:
        from grounding import GeminiEvidenceEnricher
        pkg, cps = _adapter_package(tmp_path)
        original_conf = {
            ev.evidence_id: ev.confidence
            for claim in pkg.claims
            for ev in claim.evidence_refs
        }
        GeminiEvidenceEnricher().enrich(pkg, cps)
        for claim in pkg.claims:
            for ev in claim.evidence_refs:
                assert ev.confidence == original_conf[ev.evidence_id]

    def test_enriched_package_still_passes_grounding(self, tmp_path: Path) -> None:
        from grounding import GeminiEvidenceEnricher, EvidenceGrounder
        pkg, cps = _adapter_package(tmp_path)
        GeminiEvidenceEnricher().enrich(pkg, cps)
        result = EvidenceGrounder().validate(pkg)
        assert result.is_valid, f"Violations after enrichment: {result.violations}"

    def test_cue_excerpt_references_geometry(self, tmp_path: Path) -> None:
        """Enriched excerpts should reference geometric terms, not generic filler."""
        from grounding import GeminiEvidenceEnricher
        pkg, cps = _adapter_package(tmp_path)
        GeminiEvidenceEnricher().enrich(pkg, cps)
        # At least one claim should mention a geometric term
        geometric_terms = {"fold", "edge", "vertex", "face", "layer", "mountain",
                           "valley", "crease", "paper", "square"}
        found_geometric = False
        for claim in pkg.claims:
            for ev in claim.evidence_refs:
                if ev.cue_excerpt:
                    words = set(ev.cue_excerpt.lower().split())
                    if words & geometric_terms:
                        found_geometric = True
                        break
        assert found_geometric, "No enriched excerpt references geometric terms"

    def test_cue_excerpt_max_length(self, tmp_path: Path) -> None:
        """cue_excerpt must not exceed 500 chars (adapter truncates)."""
        from grounding import GeminiEvidenceEnricher
        pkg, cps = _adapter_package(tmp_path)
        GeminiEvidenceEnricher().enrich(pkg, cps)
        for claim in pkg.claims:
            for ev in claim.evidence_refs:
                if ev.cue_excerpt:
                    assert len(ev.cue_excerpt) <= 500

    def test_missing_api_key_raises(self, tmp_path: Path) -> None:
        from grounding import GeminiEvidenceEnricher
        pkg, cps = _adapter_package(tmp_path)
        enricher = GeminiEvidenceEnricher(api_key="INVALID_KEY_FOR_TEST")
        with pytest.raises(Exception):
            enricher.enrich(pkg, cps)
