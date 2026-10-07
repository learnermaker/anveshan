"""Tests for the origami-crane universal pipeline case pack (K9-P5).

All tests run in recorded mode (no live model calls).
Tests spec §4.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_DIR = REPO_ROOT / "tracks" / "cases" / "origami-crane"
REAL_CASES = REPO_ROOT / "tracks" / "cases"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _recorded_ctx(data_dir: Path) -> Any:
    """Recorded-mode RunContext for origami-crane."""
    from tracks.common.models import ModelGateway, RunStore
    from tracks.common.runtime import RunContext

    store = RunStore([
        CASE_DIR / "runs" / "golden",
        data_dir / "runs" / "origami-crane",
    ])
    gw = ModelGateway(mode="recorded", store=store)
    return RunContext(mode="recorded", gateway=gw, case_dir=CASE_DIR, data_dir=data_dir)


def _normalize_statement(s: str) -> str:
    """Normalize for duplicate detection: lowercase, hyphens → spaces."""
    return re.sub(r"[-_]+", " ", s.lower().strip())


# ---------------------------------------------------------------------------
# §4.1 — load_case
# ---------------------------------------------------------------------------


class TestLoadOrigamiCranePack:
    def test_modality_is_universal(self):
        from track_a import api
        h = api.load_case(CASE_DIR)
        assert h.modality == "universal", f"Expected universal, got {h.modality}"

    def test_review_status_not_approved(self):
        """Package is pending or revised (not approved) — not yet expert-reviewed."""
        from track_a import api
        h = api.load_case(CASE_DIR)
        # After reject_claim actions, status may be "revised" or "pending"
        assert h.review_status in ("pending", "revised"), (
            f"Expected pending or revised, got {h.review_status}"
        )

    def test_claims_non_empty(self):
        from track_a import api
        h = api.load_case(CASE_DIR)
        assert len(h.package.claims) > 0, "Package should have claims"

    def test_no_duplicate_statements(self):
        """Case-insensitive, hyphens normalized to spaces."""
        from track_a import api
        h = api.load_case(CASE_DIR)
        seen: dict[str, str] = {}
        for claim in h.package.claims:
            norm = _normalize_statement(claim.statement)
            assert norm not in seen, (
                f"Duplicate claim: '{claim.statement}' duplicates '{seen[norm]}'"
            )
            seen[norm] = claim.statement

    def test_to_view_hero_is_true(self):
        from track_a import api
        h = api.load_case(CASE_DIR)
        v = h.to_view()
        assert v["hero"] is True, f"Expected hero=True, got {v['hero']}"

    def test_to_view_composed_profile(self):
        """Universal case has a profile in the view."""
        from track_a import api
        h = api.load_case(CASE_DIR)
        v = h.to_view()
        assert v.get("profile") is not None, "Universal case should have profile in to_view"


# ---------------------------------------------------------------------------
# §4.2 — list_cases
# ---------------------------------------------------------------------------


class TestListCasesWithOrigamiCrane:
    def test_contains_origami_crane_with_hero_and_composed(self, tmp_path: Path):
        from track_a import api
        cases = api.list_cases(REAL_CASES, tmp_path)
        by_id = {c["case_id"]: c for c in cases}
        assert "origami-crane" in by_id, "origami-crane should be in list"
        oc = by_id["origami-crane"]
        assert oc["hero"] is True, "origami-crane should have hero=True"
        assert oc.get("composed") is True, "origami-crane should have composed=True"

    def test_origami_not_in_list(self, tmp_path: Path):
        """origami (dedicated engine) is hidden from the list."""
        from track_a import api
        cases = api.list_cases(REAL_CASES, tmp_path)
        ids = [c["case_id"] for c in cases]
        assert "origami" not in ids, "origami (experimental) should not be in list"

    def test_kolam_and_tabla_present(self, tmp_path: Path):
        from track_a import api
        cases = api.list_cases(REAL_CASES, tmp_path)
        ids = [c["case_id"] for c in cases]
        assert "kolam" in ids, "kolam should be in list"
        assert "tabla" in ids, "tabla should be in list"

    def test_order_kolam_origami_crane_tabla(self, tmp_path: Path):
        """Featured cards: kolam, origami-crane, tabla (spec §3.5)."""
        from track_a import api
        cases = api.list_cases(REAL_CASES, tmp_path)
        ids = [c["case_id"] for c in cases]
        featured = [i for i in ids if i in ("kolam", "origami-crane", "tabla")]
        assert featured == ["kolam", "origami-crane", "tabla"], (
            f"Featured order should be kolam, origami-crane, tabla. Got: {featured}"
        )

    def test_runtime_label_internet_reference(self, tmp_path: Path):
        """origami-crane is built from a Wikimedia source, not a user upload."""
        from track_a import api
        cases = api.list_cases(REAL_CASES, tmp_path)
        by_id = {c["case_id"]: c for c in cases}
        oc = by_id["origami-crane"]
        assert oc["runtime_label"] == "INTERNET_REFERENCE", (
            f"Expected INTERNET_REFERENCE, got {oc['runtime_label']}"
        )


# ---------------------------------------------------------------------------
# §4.3 — samples (recorded mode, real Track B)
# ---------------------------------------------------------------------------


class TestOrigamiCraneSamplesRecorded:
    """Each sample runs through real Track B in recorded mode.

    The golden runs in runs/golden/ must contain all needed model responses.
    """

    def _load_expected(self) -> Dict[str, Any]:
        """Load expected outcomes from samples.json."""
        samples_json = CASE_DIR / "samples" / "samples.json"
        if not samples_json.exists():
            pytest.skip(f"samples.json not found at {samples_json}")
        data = json.loads(samples_json.read_text(encoding="utf-8"))
        return {s["sample_id"]: s for s in data["samples"]}

    def _run_sample(
        self, sample_id: str, data_dir: Path
    ) -> Dict[str, Any]:
        """Evaluate a sample in recorded mode. Returns result dict."""
        import hashlib
        from tracks.common.models import AnveshanFailure
        from track_b import api as tb_api
        from track_b.trajectory import AttemptMedia

        ctx = _recorded_ctx(data_dir)
        sample_file = CASE_DIR / "samples" / f"{sample_id}.mp4"

        if not sample_file.exists():
            pytest.skip(f"Sample file not found: {sample_file}")

        with open(sample_file, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()

        session = tb_api.start_session(CASE_DIR, f"K9-P5 test {sample_id}", data_dir)
        media = AttemptMedia(
            kind="video",
            path=sample_file,
            source_id=f"sample.{sample_id}.{sha[:12]}",
            sha256=sha,
            mime_type="video/mp4",
        )

        try:
            result = tb_api.submit_attempt(session, media, ctx)
            return {"refused": False, "passed": result.evaluation.get("passed", False)}
        except AnveshanFailure as exc:
            cat = getattr(exc.category, "value", str(exc.category))
            if cat == "INVALID_INPUT":
                return {"refused": True, "passed": False}
            raise
        except Exception as exc:
            # Check for REPLAY_MISMATCH
            if "REPLAY_MISMATCH" in str(exc):
                pytest.fail(
                    f"REPLAY_MISMATCH for sample {sample_id}: "
                    "golden runs may be incomplete. Re-run with --live to regenerate."
                )
            raise

    def test_good_sample_recorded(self, tmp_path: Path):
        expected = self._load_expected()
        result = self._run_sample("good", tmp_path)
        exp = expected.get("good", {})
        assert "REPLAY_MISMATCH" not in str(result), "Should not have replay mismatch"
        assert result["passed"] == exp.get("expected", {}).get("passed", False), (
            f"good sample expected passed={exp.get('expected',{}).get('passed')}, "
            f"got passed={result['passed']}"
        )

    def test_flawed_sample_recorded(self, tmp_path: Path):
        expected = self._load_expected()
        result = self._run_sample("flawed", tmp_path)
        exp = expected.get("flawed", {})
        assert "REPLAY_MISMATCH" not in str(result), "Should not have replay mismatch"
        assert result["passed"] == exp.get("expected", {}).get("passed", False), (
            f"flawed sample expected passed={exp.get('expected',{}).get('passed')}, "
            f"got passed={result['passed']}"
        )

    def test_unrelated_sample_refused(self, tmp_path: Path):
        """Unrelated sample should be refused (not scored)."""
        result = self._run_sample("unrelated", tmp_path)
        assert result["refused"] is True, (
            f"unrelated sample should be refused, got: {result}"
        )


# ---------------------------------------------------------------------------
# §4.4 — learner session end-to-end (recorded mode)
# ---------------------------------------------------------------------------


class TestOrigamiCraneSessionE2E:
    """Full Track B session in recorded mode with the good sample."""

    def test_session_completes_end_to_end(self, tmp_path: Path):
        """Start session, submit baseline (good sample), submit retry (same), complete."""
        import hashlib
        from track_b import api as tb_api
        from track_b.trajectory import AttemptMedia
        from tracks.common.models import AnveshanFailure

        ctx = _recorded_ctx(tmp_path)
        sample_file = CASE_DIR / "samples" / "good.mp4"
        if not sample_file.exists():
            pytest.skip(f"good.mp4 not found")

        with open(sample_file, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()

        session = tb_api.start_session(CASE_DIR, "K9-P5 e2e test", tmp_path)
        assert session is not None

        # Baseline
        media = AttemptMedia(
            kind="video",
            path=sample_file,
            source_id=f"sample.good.{sha[:12]}",
            sha256=sha,
            mime_type="video/mp4",
        )
        try:
            result1 = tb_api.submit_attempt(session, media, ctx)
            assert result1 is not None
        except AnveshanFailure as exc:
            if "REPLAY_MISMATCH" in str(exc):
                pytest.fail(f"REPLAY_MISMATCH on baseline: {exc}")
            raise

        # Retry with same file
        media2 = AttemptMedia(
            kind="video",
            path=sample_file,
            source_id=f"sample.good.retry.{sha[:12]}",
            sha256=sha,
            mime_type="video/mp4",
        )
        try:
            result2 = tb_api.submit_attempt(session, media2, ctx)
            assert result2 is not None
        except AnveshanFailure as exc:
            if "REPLAY_MISMATCH" in str(exc):
                pytest.fail(f"REPLAY_MISMATCH on retry: {exc}")
            raise

        # Complete session
        session_result = tb_api.complete_session(session)
        assert session_result is not None


# ---------------------------------------------------------------------------
# §4.5 — existing listing tests don't assert origami in list
# ---------------------------------------------------------------------------


def test_list_cases_on_real_case_root_no_origami(tmp_path: Path):
    """The real case root listing should NOT include bare 'origami' (experimental)."""
    from track_a import api

    cases = api.list_cases(REAL_CASES, tmp_path)
    ids = [c["case_id"] for c in cases]
    assert "origami" not in ids, "origami (dedicated engine) should not be in the public library"
    assert "origami-crane" in ids, "origami-crane (universal pipeline) should be in the library"


def test_origami_direct_access_still_works():
    """GET /api/cases/origami still works via load_case (direct URL access)."""
    from track_a import api

    # load_case should still work for origami (even though it's not in list)
    origami_dir = REAL_CASES / "origami"
    h = api.load_case(origami_dir)
    assert h.case_id == "origami"
    # Should have the experimental title
    assert h.manifest.get("title") == "Origami crane (dedicated engine, experimental)", (
        f"Expected experimental title, got: {h.manifest.get('title')}"
    )
