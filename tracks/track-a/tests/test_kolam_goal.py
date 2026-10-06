"""Track A kolam goal builder: real-target facts, claim structure, fake gateway."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tracks.common.casedata import CriterionMap, CriterionMapEntry, SourceRecord
from tracks.common.media import sha256_file
from tracks.common.models import (
    ModelGateway,
    ModelRegistry,
    RunStore,
)
from tracks.common.runtime import RunContext
from tracks.common.schemas.evidence import VerificationState

from track_a.goals import get_builder
from track_a.goals.kolam import build

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = REPO_ROOT / "tracks" / "cases" / "kolam" / "source" / "ithayakkamalam_target.jpg"
SRC_ID = "src.kolam.target.v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _source() -> SourceRecord:
    return SourceRecord(
        source_id=SRC_ID,
        role="target_image",
        mime_type="image/jpeg",
        sha256=sha256_file(TARGET),
        bytes=TARGET.stat().st_size,
        path=str(TARGET.relative_to(REPO_ROOT)),
        creator="Traditional artist",
        license="Public domain",
        attribution="Ithayakkamalam kolam, public domain",
        runtime_label="INTERNET_REFERENCE",
    )


class _FakeModels:
    def __init__(self, text: str):
        self.text = text
        self.calls: int = 0

    def generate_content(self, model, contents, config):
        self.calls += 1
        return type("R", (), {"text": self.text})()


class _FakeClient:
    def __init__(self, models: _FakeModels):
        self.models = models


def _ctx(tmp_path: Path, reply: str) -> RunContext:
    """RunContext backed by a fake model client that returns ``reply``."""
    gw = ModelGateway(
        "live",
        RunStore([tmp_path / "runs"]),
        ModelRegistry({"text_image": "gemma-test"}),
        client=_FakeClient(_FakeModels(reply)),
    )
    return RunContext(mode="live", gateway=gw, case_dir=tmp_path, data_dir=tmp_path)


# ---------------------------------------------------------------------------
# Module-scoped fixture: one real build (deterministic, ~1.4 s, reused)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_build():
    """Build from the real JPEG target without a model context."""
    return build(TARGET, _source(), None, case_id="kolam", version=1)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_registry_points_to_kolam_builder():
    assert get_builder("kolam_image") is build


def test_goal_geometry_from_real_target(real_build):
    """41 dots, K=1 closed line, 8-fold rotational symmetry."""
    r = real_build
    from tracks.common.goals.kolam import KolamGoal
    g = KolamGoal.model_validate(r.goal_payload)
    assert g.features.n_dots == 41, f"expected 41 dots, got {g.features.n_dots}"
    assert g.features.n_curves == 1, f"expected K=1, got {g.features.n_curves}"
    assert g.features.n_closed == 1, "expected the single curve to be closed"
    assert g.symmetry.rotation_order == 8, (
        f"expected rotation_order=8, got {g.symmetry.rotation_order}"
    )


def test_claim_ids_start_with_clm01(real_build):
    """First 5 claims are CLM-01..CLM-05 and all are OBSERVED."""
    r = real_build
    ids = [c.claim_id for c in r.claims]
    # At least 5 claims (5 observed facts + stage step claims)
    assert len(ids) >= 5, f"expected >= 5 claims, got {len(ids)}"
    # First 5 are CLM-01 through CLM-05
    for i, clm_id in enumerate(ids[:5], start=1):
        assert clm_id == f"CLM-{i:02d}", f"claim {i} id is {clm_id!r}, expected CLM-{i:02d}"
    # First 5 are all observed
    for c in r.claims[:5]:
        assert c.is_observed, f"{c.claim_id} should be observed"


def test_observed_claims_have_xywh_locators_no_times(real_build):
    """Every OBSERVED claim's evidence has an #xywh=percent: locator and no timestamps."""
    for c in real_build.claims:
        for ev in c.evidence_refs:
            if ev.verification_state == VerificationState.OBSERVED:
                assert "#xywh=percent:" in ev.source_id, (
                    f"{c.claim_id} observed ev has locator {ev.source_id!r}; "
                    "expected #xywh=percent:"
                )
                assert ev.start_sec is None, (
                    f"{c.claim_id} observed ev should have no start_sec; got {ev.start_sec}"
                )
                assert ev.end_sec is None, (
                    f"{c.claim_id} observed ev should have no end_sec; got {ev.end_sec}"
                )


def test_inferred_claims_confidence_at_most_0_5(real_build):
    """Every INFERRED claim's evidence has confidence <= 0.5."""
    for c in real_build.claims:
        for ev in c.evidence_refs:
            if ev.verification_state == VerificationState.INFERRED:
                assert ev.confidence <= 0.5, (
                    f"{c.claim_id} inferred ev has confidence {ev.confidence}; must be <= 0.5"
                )


def test_criterion_map_cites_claims(real_build):
    """why_it_matters on every criterion cites at least one of its source claims (validator rule)."""
    r = real_build
    claim_ids = {c.claim_id for c in r.claims}
    ev_ids = {ev.evidence_id for c in r.claims for ev in c.evidence_refs}

    # Building a CriterionMap exercises the citation validator: each why_it_matters must
    # contain a reference to one of its source_claim_ids.
    cmap = CriterionMap(
        rubric_id="rubric.kolam.1",
        package_id="kp.kolam.1",
        criteria={
            c.criterion_id: CriterionMapEntry(
                order_index=c.order_index,
                source_claim_ids=c.source_claim_ids,
                reference_evidence_ids=c.reference_evidence_ids,
                why_it_matters=c.why_it_matters,
                drill_hint=c.drill_hint,
            )
            for c in r.criteria
        },
    )
    assert len(cmap.criteria) == len(r.criteria)
    # All source_claim_ids must exist in the claims we built
    for c in r.criteria:
        for cid in c.source_claim_ids:
            assert cid in claim_ids, f"criterion {c.criterion_id} cites unknown claim {cid}"
        for eid in c.reference_evidence_ids:
            assert eid in ev_ids, f"criterion {c.criterion_id} cites unknown evidence {eid}"


def test_build_with_fake_gateway_success(tmp_path):
    """Fake model returns a valid KolamDescribeDTO; run_keys is populated."""
    valid_dto = json.dumps({
        "description": "A symmetric kolam with a single continuous line.",
        "rotation_order_estimate": 8,
        "curve_count_estimate": 1,
        "stage_instructions": [],
        "caveats": [],
    })
    ctx = _ctx(tmp_path, valid_dto)
    r = build(TARGET, _source(), ctx, case_id="kolam", version=1)

    assert len(r.run_keys) == 1, f"expected 1 run_key, got {r.run_keys}"
    # Model disagreements trigger extra warnings; with matching estimates there should be none.
    model_warnings = [w for w in r.warnings if "model rotation" in w or "model curve" in w]
    assert model_warnings == [], f"unexpected model-disagreement warnings: {model_warnings}"


def test_build_model_error_becomes_warning(tmp_path):
    """Model returns invalid JSON (schema validation fails) → warning, build still succeeds."""
    ctx = _ctx(tmp_path, "{}")  # empty dict fails KolamDescribeDTO validation (description required)
    r = build(TARGET, _source(), ctx, case_id="kolam", version=1)

    assert r.run_keys == [], f"model failure should produce no run_keys, got {r.run_keys}"
    assert any("model call unavailable" in w for w in r.warnings), (
        f"expected a 'model call unavailable' warning, got: {r.warnings}"
    )
    # Build still produced valid claims and criteria despite model failure.
    assert len(r.claims) >= 5
    assert len(r.criteria) == 5


def test_build_is_deterministic():
    """Two builds from the same file (no model) produce identical JSON."""
    src = _source()
    a = build(TARGET, src, None, case_id="kolam", version=1)
    b = build(TARGET, src, None, case_id="kolam", version=1)

    assert json.dumps(a.goal_payload, sort_keys=True) == json.dumps(b.goal_payload, sort_keys=True), \
        "goal_payload is not deterministic"
    assert [c.model_dump() for c in a.claims] == [c.model_dump() for c in b.claims], \
        "claims are not deterministic"
    assert a.task_instructions == b.task_instructions, \
        "task_instructions are not deterministic"
