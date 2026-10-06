"""Tests for the universal-pipeline shared schemas: profile v2, perception, skill model, policy, embeddings."""

import numpy as np
import pytest

from tracks.common.models import FailureCategory, ImagePart, ModelError, ModelGateway, ModelRegistry, RunStore
from tracks.common.perception import MediaInfoRecord, Observation, PerceptionRecord, Segment
from tracks.common.policy import safety_decision
from tracks.common.profile import CaseProfile, IntakeResult, ProbeFacts, composed_case_id, slugify
from tracks.common.skill_model import Check, Relevance, SkillModel, Step, TargetProperty


def _skill(**kw):
    base = dict(
        skill_title="Lotus drawing", summary="s", source_modality="image", structures=["final_state"],
        goal_state=[TargetProperty(prop_id="prop-01", statement="eight petals", certainty="inferred")],
        relevance=Relevance(expected_kinds=["image"]),
        checks=[Check(check_id="CHK-01", kind="final_property", name="Eight petals", observable_indicator="eight petals visible",
                      targets=["prop-01"], metric_id="u.final_property.prop-01", method="model_status")],
    )
    base.update(kw)
    return SkillModel(**base)


def _probe(**kw):
    base = dict(modality="image", mime_type="image/png", bytes=10, sha256="ab" * 32, structures_available=["final_state"])
    base.update(kw)
    return ProbeFacts(**base)


def _intake(**kw):
    base = dict(safety=safety_decision(["none"]), teachable="yes")
    base.update(kw)
    return IntakeResult(**base)


def _profile(**kw):
    base = dict(case_id="lotus~abcdef012345", title="Lotus", skill_summary="s", domain="d", transmission_mode="goal-conditioned",
                learner_input_kinds=["image"], probe=_probe(), intake=_intake(), skill_model=_skill())
    base.update(kw)
    return CaseProfile(**base)


def test_slug_and_case_id():
    assert slugify("Rangoli — Lotus (Simple)!") == "rangoli-lotus-simple"
    assert slugify("தமிழ்") == "skill"
    assert composed_case_id("Paper Cup", "ABCDEF0123456789" + "0" * 48) == "paper-cup~abcdef012345"


def test_profile_v2_validation():
    assert _profile().modality == "universal"
    with pytest.raises(ValueError):  # trace needs the line_art specialist
        _profile(learner_input_kinds=["trace"])
    with pytest.raises(ValueError):  # audio not accepted for final_state
        _profile(learner_input_kinds=["audio"])
    with pytest.raises(ValueError):  # structure not available from probe
        _profile(skill_model=_skill(structures=["final_state", "procedure"]))
    with pytest.raises(ValueError):
        _profile(intake=_intake(teachable="no"))
    with pytest.raises(ValueError):
        _profile(intake=_intake(safety=safety_decision(["weapons"])))
    with pytest.raises(ValueError):
        _profile(case_id="Lotus")


def test_skill_model_rules():
    with pytest.raises(ValueError):  # line_art check without specialist payload
        _skill(checks=[Check(check_id="CHK-01", kind="line_art", name="n", observable_indicator="o", metric_id="line_art:kolam.coverage", method="specialist")])
    with pytest.raises(ValueError):  # check kind not valid for structure
        _skill(checks=[Check(check_id="CHK-01", kind="rhythm", name="n", observable_indicator="o", metric_id="m", method="specialist")])
    with pytest.raises(ValueError):  # unknown target
        _skill(checks=[Check(check_id="CHK-01", kind="final_property", name="n", observable_indicator="o", targets=["prop-99"], metric_id="m", method="model_status")])
    with pytest.raises(ValueError):  # strict order needs source-established steps
        _skill(order="strict", steps=[Step(step_id="step-01", index=0, name="a", state_after="b", certainty="inferred", source_established=False)])


def test_perception_record_rules():
    media = MediaInfoRecord(source_id="s", modality="video", sha256="a" * 64, mime_type="video/mp4", duration_sec=10)
    seg = Segment(segment_id="seg-000", kind="time", start_sec=0, end_sec=2)
    ok = PerceptionRecord(media=media, segments=[seg], observations=[
        Observation(obs_id="obs-000", segment_id="seg-000", kind="state", label="flat paper", certainty="inferred", producer="model:vision_fast")])
    assert ok.observations_for("seg-000")[0].label == "flat paper"
    with pytest.raises(ValueError):  # model output cannot be observed
        Observation(obs_id="o", segment_id="seg-000", kind="state", label="x", certainty="observed", producer="model:vision_fast")
    with pytest.raises(ValueError):
        Segment(segment_id="seg-001", kind="time", start_sec=3, end_sec=1)
    with pytest.raises(ValueError):  # unknown segment reference
        PerceptionRecord(media=media, segments=[seg], observations=[
            Observation(obs_id="obs-000", segment_id="seg-404", kind="state", label="x", certainty="inferred", producer="model:vision_fast")])


def test_policy_decisions():
    assert safety_decision(["none"])["decision"] == "ok"
    assert safety_decision(["identifiable_faces"])["decision"] == "flag"
    assert safety_decision(["weapons", "identifiable_faces"])["decision"] == "refuse"


class _FakeEmbedModels:
    def __init__(self):
        self.calls = 0

    def embed_content(self, model, contents, config):
        self.calls += 1
        rows = []
        for i, _ in enumerate(contents):
            v = np.zeros(8)
            v[(self.calls * 3 + i) % 8] = 2.0
            rows.append(type("E", (), {"values": list(v)})())
        return type("R", (), {"embeddings": rows})()


def test_embed_records_and_replays(tmp_path):
    fake = _FakeEmbedModels()
    client = type("C", (), {"models": fake})()
    gw = ModelGateway("live", RunStore([tmp_path]), ModelRegistry({"embedding": "emb-test"}), client=client)
    items = ["a", ImagePart(b"\xff\xd8x"), "c"]
    r = gw.embed(items=items, purpose="t", dims=8, batch_size=2)
    assert r.vectors.shape == (3, 8) and np.allclose(np.linalg.norm(r.vectors, axis=1), 1.0)
    assert fake.calls == 2 and r.metadata.runtime_class == "LIVE"
    rec = ModelGateway("recorded", RunStore([tmp_path]))
    r2 = rec.embed(items=items, purpose="t", dims=8)
    assert np.allclose(r2.vectors, r.vectors, atol=1e-3) and r2.metadata.runtime_class == "RECORDED_LIVE"
    with pytest.raises(ModelError) as e:
        rec.embed(items=["different"], purpose="t", dims=8)
    assert e.value.category == FailureCategory.REPLAY_MISMATCH
