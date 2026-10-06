import json
from gemini_schemas import (
    GeminiStepSchema,
    GeminiCueSchema,
    GeminiConditionSchema,
    GeminiExceptionSchema,
    GeminiFailureModeSchema,
    GeminiTargetPropertySchema,
    GeminiDivergenceSchema,
    GeminiExtractionResponse,
    GeminiQueryResponse,
)


def test_gemini_extraction_response_schema_serialization():
    resp = GeminiExtractionResponse(
        title="Micrometer Calibration",
        summary="Zeroing and calibration of external micrometer",
        steps=[
            GeminiStepSchema(
                index=0,
                title="Wipe anvil",
                description="Clean anvil surfaces with clean paper",
                start_sec=1.5,
                end_sec=3.0,
            )
        ],
        cues=[
            GeminiCueSchema(
                modality="video",
                statement="Clean contact surface",
                observable_indicator="Absence of dust particles",
                start_sec=1.5,
                end_sec=2.0,
                evidence_sufficiency="OBSERVED",
            )
        ],
        conditions=[
            GeminiConditionSchema(
                statement="Room temperature 20C",
                tools_or_materials=["Lint-free paper", "Micrometer standard"],
            )
        ],
        exceptions=[
            GeminiExceptionSchema(
                condition_trigger="Zero line misaligned > 0.01mm",
                alternative_action="Use adjusting spanner to rotate sleeve",
            )
        ],
        failure_modes=[
            GeminiFailureModeSchema(
                symptom="Ratchet slips prematurely",
                mistake_description="Dirt in ratchet mechanism",
                severity="moderate",
            )
        ],
        target_properties=[
            GeminiTargetPropertySchema(
                property_id="zero_mark_alignment",
                description="Thimble zero coincides with sleeve datum line",
                evidence_sufficiency="OBSERVED",
                measurement="0.000 mm",
            )
        ],
        divergences=[
            GeminiDivergenceSchema(
                criterion_id="CRIT-01",
                observed_behavior="Rotated thimble directly without cleaning",
                expected_behavior="Clean anvils before closing",
                timestamp_sec=2.1,
                evidence_sufficiency="OBSERVED",
            )
        ],
    )

    data = resp.model_dump()
    assert data["title"] == "Micrometer Calibration"
    assert len(data["steps"]) == 1
    assert data["steps"][0]["title"] == "Wipe anvil"
    assert len(data["cues"]) == 1
    assert len(data["target_properties"]) == 1
    assert len(data["divergences"]) == 1

    # Verify JSON roundtrip
    json_str = resp.model_dump_json()
    reconstructed = GeminiExtractionResponse.model_validate_json(json_str)
    assert reconstructed.title == resp.title
    assert reconstructed.steps[0].end_sec == 3.0


def test_gemini_query_response_serialization():
    q_resp = GeminiQueryResponse(
        answer="Anvil was wiped with lint-free paper at 01.5s.",
        cited_claim_ids=["CLM-01"],
        cited_timestamps=["00:01.5 - 00:03.0"],
        has_sufficient_evidence=True,
    )
    data = q_resp.model_dump()
    assert data["has_sufficient_evidence"] is True
    assert "CLM-01" in data["cited_claim_ids"]
