"""Grounding audit: locator / observation / confidence / creator-intent rules."""

import pytest

from tracks.common.casedata import SourceRecord, SourceRegistry
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import ClaimType, ConsentMetadata, KnowledgeClaim, KnowledgePackage

from track_a import api, grounding

from ta_helpers import SRC_ID, ev, kolam_claims, kolam_result

AUDIO_ID = "src.tabla.theka.v1"


def registry() -> SourceRegistry:
    common = dict(sha256="0" * 64, bytes=1, creator="c", license="CC BY 4.0", attribution="a", runtime_label="INTERNET_REFERENCE")
    return SourceRegistry(
        case_id="x",
        sources=[
            SourceRecord(source_id=SRC_ID, role="target_image", mime_type="image/jpeg", path="s.jpg", **common),
            SourceRecord(source_id=AUDIO_ID, role="expert_audio", mime_type="audio/ogg", path="t.ogg", duration_sec=20.0, **common),
            SourceRecord(
                source_id="src.held", role="held_out_reference", mime_type="image/jpeg", path="h.jpg", used_by_system=False, **common
            ),
        ],
    )


def pkg(claims) -> KnowledgePackage:
    return KnowledgePackage(
        package_id="kp.x.1",
        skill_id="s",
        title="t",
        summary="s",
        claims=claims,
        consent=ConsentMetadata(contributor_name="c", consent_scope="public licence: CC BY 4.0"),
    )


def claim(cid, refs, *, observed=True, ctype=ClaimType.CUE, statement="A visible property."):
    return KnowledgeClaim(claim_id=cid, claim_type=ctype, statement=statement, is_observed=observed, evidence_refs=refs)


def _fails(package, category, modality="tabla_audio"):
    with pytest.raises(AnveshanFailure) as e:
        grounding.audit_package(package, registry(), modality)
    assert e.value.category == category, e.value
    return e.value


def test_valid_kolam_package_passes_and_reports_uncertainty():
    notes = grounding.audit_package(pkg(kolam_claims()), registry(), "kolam_image")
    assert notes == ["CLM-03: not directly observed", "CLM-04: not directly observed"]


def test_observed_image_needs_region_and_no_times():
    _fails(pkg([claim("CLM-01", [ev("e1", SRC_ID)])]), FailureCategory.CONTRACT_VIOLATION)
    _fails(
        pkg([claim("CLM-01", [ev("e1", f"{SRC_ID}#xywh=percent:1,1,5,5", start=1.0, end=2.0)])]),
        FailureCategory.CONTRACT_VIOLATION,
    )


def test_fake_zero_locator_rejected():
    _fails(
        pkg([claim("CLM-01", [ev("e1", AUDIO_ID, modality="audio", start=0.0, end=0.0)])]),
        FailureCategory.CONTRACT_VIOLATION,
    )


def test_audio_interval_required_and_within_duration():
    ok = pkg([claim("CLM-01", [ev("e1", AUDIO_ID, modality="audio", start=1.0, end=2.5)])])
    assert grounding.audit_package(ok, registry(), "tabla_audio") == []
    _fails(pkg([claim("CLM-01", [ev("e1", AUDIO_ID, modality="audio")])]), FailureCategory.CONTRACT_VIOLATION)
    _fails(
        pkg([claim("CLM-01", [ev("e1", AUDIO_ID, modality="audio", start=19.0, end=25.0)])]),
        FailureCategory.CONTRACT_VIOLATION,
    )


def test_modality_must_match_source_mime():
    _fails(
        pkg([claim("CLM-01", [ev("e1", AUDIO_ID, modality="video", start=1.0, end=2.0)])]),
        FailureCategory.CONTRACT_VIOLATION,
    )


def test_observation_flag_must_match_evidence():
    _fails(pkg([claim("CLM-01", [ev("e1", SRC_ID, state="inferred", conf=0.4)], observed=True)]), FailureCategory.CONTRACT_VIOLATION)
    _fails(
        pkg([claim("CLM-01", [ev("e1", f"{SRC_ID}#xywh=percent:1,1,5,5")], observed=False)]),
        FailureCategory.CONTRACT_VIOLATION,
    )


def test_inferred_step_confidence_capped():
    _fails(
        pkg([claim("CLM-01", [ev("e1", SRC_ID, state="inferred", conf=0.7)], observed=False, ctype=ClaimType.STEP)]),
        FailureCategory.CONTRACT_VIOLATION,
    )


def test_held_out_source_never_cited():
    _fails(pkg([claim("CLM-01", [ev("e1", "src.held", state="inferred", conf=0.3)], observed=False)]), FailureCategory.CONTRACT_VIOLATION)


def test_goal_conditioned_needs_inferred_step():
    observed_only = [c for c in kolam_claims() if c.is_observed]
    _fails(pkg(observed_only), FailureCategory.UNSUPPORTED_CLAIM, modality="kolam_image")


@pytest.mark.parametrize(
    "text",
    [
        "The artist intended this as a lotus.",
        "This kolam was originally drawn clockwise from the top.",
        "The pattern symbolizes prosperity.",
    ],
)
def test_creator_intent_phrases_rejected(text):
    claims = kolam_claims()
    claims[0].statement = text
    _fails(pkg(claims), FailureCategory.UNSUPPORTED_CLAIM, modality="kolam_image")


def test_statement_of_unknown_is_allowed():
    claims = kolam_claims()
    claims[3].statement = "One suggested order; the original stroke order is not established by the image."
    grounding.audit_package(pkg(claims), registry(), "kolam_image")


def test_build_surfaces_grounding_failure_and_writes_nothing(cases_root, fake_builder, make_ctx):
    claims = kolam_claims()
    claims[1].evidence_refs[0].source_id = SRC_ID  # observed image claim without region
    fake_builder["result"] = kolam_result(claims)
    with pytest.raises(AnveshanFailure) as e:
        api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam"))
    assert e.value.category == FailureCategory.CONTRACT_VIOLATION
    assert not list((cases_root / "kolam" / "knowledge").glob("*.v1.json"))


def test_intent_in_task_instructions_rejected(cases_root, fake_builder, make_ctx):
    fake_builder["result"] = kolam_result(task_instructions="1. Draw it as the artist intended [CLM-03].")
    with pytest.raises(AnveshanFailure) as e:
        api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam"))
    assert e.value.category == FailureCategory.UNSUPPORTED_CLAIM
