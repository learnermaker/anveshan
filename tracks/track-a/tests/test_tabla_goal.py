"""Track A tabla goal builder: deterministic claims/criteria from synthetic audio; fake model gateway."""

import json
import re

import pytest

from tracks.common.casedata import CriterionMap, CriterionMapEntry, SourceRecord
from tracks.common.goals.tabla import PAYLOAD_MODEL
from tracks.common.models import AnveshanFailure, FailureCategory, ModelGateway, ModelRegistry, RunStore
from tracks.common.runtime import RunContext
from tracks.common.schemas import VerificationState
from tracks.common.tests.test_tabla_goal_model import SR, synth_tabla, write_wav

from track_a.goals import get_builder
from track_a.goals.tabla import build


class _FakeModels:
    def __init__(self, text=None, fail=False):
        self.text, self.fail, self.calls = text, fail, 0

    def generate_content(self, model, contents, config):
        self.calls += 1
        if self.fail:
            raise RuntimeError("503 UNAVAILABLE")
        return type("R", (), {"text": self.text})()


class _FakeClient:
    def __init__(self, models):
        self.models = models


def _ctx(tmp_path, audio_model="", models=None):
    gw = ModelGateway("live", RunStore([tmp_path / "runs"]), ModelRegistry({"audio": audio_model}),
                      client=_FakeClient(models or _FakeModels("{}")))
    return RunContext(mode="live", gateway=gw, case_dir=tmp_path, data_dir=tmp_path)


def _source(path, dur):
    return SourceRecord(source_id="src.tabla.test.v1", role="expert_audio", mime_type="audio/wav", sha256="0" * 64,
                        bytes=path.stat().st_size, path=str(path), duration_sec=dur, window_sec=[0.0, dur],
                        creator="synthetic", license="CC0", attribution="synthetic test audio", runtime_label="SYNTHETIC")


@pytest.fixture
def expert(tmp_path):
    x, times, bass = synth_tabla()
    p = write_wav(tmp_path / "expert.wav", x)
    return p, _source(p, len(x) / SR), times, bass


def test_registry_points_to_tabla_builder():
    assert get_builder("tabla_audio") is build


def test_build_observed_claims_and_criteria(tmp_path, expert):
    path, src, times, bass = expert
    r = build(path, src, _ctx(tmp_path), case_id="tabla", version=1)
    g = PAYLOAD_MODEL.model_validate(r.goal_payload)
    assert abs(g.stroke_pulse_sec - 0.25) < 0.003 and g.cycle_length_pulses == 8
    assert [o.bass for o in g.onsets] == bass
    # v2 builder: CLM-01..CLM-06 unchanged, CLM-07 always present (timbre classes)
    claim_ids = [c.claim_id for c in r.claims]
    assert claim_ids[:6] == [f"CLM-0{i}" for i in range(1, 7)]
    assert "CLM-07" in claim_ids
    for c in r.claims[:5]:
        assert c.is_observed
        ev = c.evidence_refs[0]
        assert ev.modality.value == "audio" and ev.verification_state == VerificationState.OBSERVED
        assert ev.confidence == 1.0 and ev.start_sec is not None and ev.end_sec > ev.start_sec
    bol = r.claims[5]
    assert not bol.is_observed and bol.evidence_refs[0].verification_state == VerificationState.UNVERIFIED
    timbre_clm = next(c for c in r.claims if c.claim_id == "CLM-07")
    assert timbre_clm.is_observed and timbre_clm.evidence_refs[0].verification_state == VerificationState.OBSERVED
    assert "distinct stroke timbres" in timbre_clm.statement
    assert "8 pulses" in r.claims[2].statement and "BB-.B---" in r.claims[3].statement
    # never assert taal/bol names as observed
    for c in r.claims:
        assert not re.search(r"\b(teentaal|keherwa|dadra|tintal)\b", c.statement, re.I)
    ids = [c.criterion_id for c in r.criteria]
    assert "CRIT-TABLA-TEMPO" in ids and "CRIT-TABLA-TIMING" in ids
    assert "CRIT-TABLA-BAYAN" in ids and "CRIT-TABLA-COMPLETE" in ids
    assert "CRIT-TABLA-STEADY" in ids
    # CRIT-TABLA-STROKES always present in v2 (timbre always computed)
    assert "CRIT-TABLA-STROKES" in ids
    assert [c.required for c in r.criteria if c.criterion_id in {
        "CRIT-TABLA-TEMPO", "CRIT-TABLA-TIMING", "CRIT-TABLA-BAYAN"}] == [True, True, True]
    metric_set = {c.observer.metric for c in r.criteria}
    assert metric_set >= {"tabla.tempo_error_pct", "tabla.timing_median_ms", "tabla.bass_accuracy",
                          "tabla.missing_extra", "tabla.ioi_cv", "tabla.stroke_class_accuracy"}
    claim_ids_set = {c.claim_id for c in r.claims}
    ev_ids = {e.evidence_id for c in r.claims for e in c.evidence_refs}
    cmap = CriterionMap(rubric_id="rubric.tabla.1", package_id="kp.tabla.1", criteria={
        c.criterion_id: CriterionMapEntry(order_index=c.order_index, source_claim_ids=c.source_claim_ids,
                                          reference_evidence_ids=c.reference_evidence_ids,
                                          why_it_matters=c.why_it_matters, drill_hint=c.drill_hint)
        for c in r.criteria})
    for c in r.criteria:
        assert set(c.source_claim_ids) <= claim_ids_set and set(c.reference_evidence_ids) <= ev_ids
    lines = r.task_instructions.splitlines()
    assert all(re.search(r"\[CLM-0\d\]", ln) for ln in lines)
    assert "same length" in r.task_instructions and "tempo" in r.task_instructions
    assert r.run_keys == [] and r.goal_payload["bols_status"] == "audio_model_disabled"
    # v2: timbre payload present
    assert r.goal_payload["timbre"] is not None
    assert r.goal_payload["class_display"] is not None
    assert all(o.get("timbre_class") is not None for o in r.goal_payload["onsets"])


def test_build_is_deterministic(tmp_path, expert):
    path, src, _, _ = expert
    a = build(path, src, _ctx(tmp_path), case_id="tabla", version=1)
    b = build(path, src, _ctx(tmp_path), case_id="tabla", version=1)
    assert json.dumps(a.goal_payload, sort_keys=True) == json.dumps(b.goal_payload, sort_keys=True)
    assert [c.model_dump() for c in a.claims] == [c.model_dump() for c in b.claims]
    assert a.task_instructions == b.task_instructions


def test_audio_model_enabled_infers_bols_and_adds_criterion(tmp_path, expert):
    path, src, times, _ = expert
    # v2 prompt returns ordered bol sequence (not timestamps)
    reply = json.dumps({"bols": ["Dha" if i % 2 == 0 else "Na" for i in range(len(times))],
                        "confidence": "high"})
    models = _FakeModels(reply)
    r = build(path, src, _ctx(tmp_path, "audio-test-model", models), case_id="tabla", version=1)
    assert models.calls == 1 and len(r.run_keys) == 1
    assert r.goal_payload["bols_status"] == "inferred" and len(r.goal_payload["bols"]) == len(times)
    bol = r.claims[5]
    assert bol.evidence_refs[0].verification_state == VerificationState.INFERRED and bol.evidence_refs[0].confidence == 0.5
    assert "CRIT-TABLA-BOLS" in [c.criterion_id for c in r.criteria]
    assert r.criteria[-1].criterion_id == "CRIT-TABLA-STROKES"  # STROKES is last
    # class_display labels should have 'inferred' entries when bols succeeded
    assert any(e["source"] == "inferred" for e in r.goal_payload["class_display"])


def test_audio_model_failure_is_a_warning(tmp_path, expert):
    path, src, _, _ = expert
    r = build(path, src, _ctx(tmp_path, "audio-test-model", _FakeModels(fail=True)), case_id="tabla", version=1)
    assert r.goal_payload["bols_status"] == "model_failed"
    assert any("bol naming failed" in w for w in r.warnings)
    assert "CRIT-TABLA-BOLS" not in [c.criterion_id for c in r.criteria]
    assert r.claims[5].evidence_refs[0].verification_state == VerificationState.UNVERIFIED
    # CRIT-TABLA-STROKES still present even when bols fail (timbre is deterministic)
    assert "CRIT-TABLA-STROKES" in [c.criterion_id for c in r.criteria]


def test_too_few_strokes_is_invalid_input(tmp_path):
    x, _, _ = synth_tabla(cycles=1, pattern="B-..")
    p = write_wav(tmp_path / "short.wav", x)
    with pytest.raises(AnveshanFailure) as e:
        build(p, _source(p, len(x) / SR), _ctx(tmp_path), case_id="tabla", version=1)
    assert e.value.category == FailureCategory.INVALID_INPUT
