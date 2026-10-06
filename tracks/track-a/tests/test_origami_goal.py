"""Origami goal builder tests. No live API: a fake gateway "looks" at the JPEG frames (solid
colour per paper state) and returns canned JSON in the prompt's DTO shape."""

from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path

import av
import numpy as np
import pytest
from PIL import Image

from tracks.common.casedata import CriterionMap, CriterionMapEntry, SourceRecord
from tracks.common.goals import origami as goal_schema
from tracks.common.models import (
    FailureCategory,
    GenerationResult,
    ImagePart,
    ModelError,
    ModelGateway,
    ModelRegistry,
    RunMetadata,
    RunStore,
    replay_key,
)
from tracks.common.runtime import RunContext
from track_a.goals import origami as og

PALETTE = [(220, 30, 30), (30, 200, 30), (30, 30, 220), (230, 230, 30), (220, 30, 220), (30, 220, 220)]
NAMES = ["flat square", "folded rectangle", "triangle", "square base", "kite form", "bird base"]


def make_video(path: Path, seq, fps: int = 2, size=(64, 48), audio: bool = False) -> Path:
    """seq: list of (label, seconds); int -> palette colour, 't' -> noise (transition), 'u' -> black."""
    rng = np.random.default_rng(0)
    w, h = size
    with av.open(str(path), "w") as c:
        s = c.add_stream("mpeg4", rate=fps)
        s.width, s.height, s.pix_fmt = w, h, "yuv420p"
        for lab, secs in seq:
            for _ in range(int(round(secs * fps))):
                if lab == "t":
                    img = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
                elif lab == "u":
                    img = np.zeros((h, w, 3), np.uint8)
                elif lab == "x":
                    img = np.full((h, w, 3), (120, 0, 255), np.uint8)
                else:
                    img = np.full((h, w, 3), PALETTE[lab], np.uint8)
                for pk in s.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
                    c.mux(pk)
        for pk in s.encode():
            c.mux(pk)
    return path


def classify(data: bytes):
    img = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.float32)
    mean, std = img.reshape(-1, 3).mean(0), img.reshape(-1, 3).std(0).mean()
    if std > 40:
        return "t"
    if mean.max() < 40:
        return "u"
    if np.linalg.norm(mean - np.array([120, 0, 255])) < 60:
        return "x"
    d = [np.linalg.norm(mean - np.array(p)) for p in PALETTE]
    return int(np.argmin(d)) if min(d) < 70 else "t"


def states_responder(prompt_id, prompt_text, parts):
    assert prompt_id == "origami_states"
    frames, notes = [], []
    for p in parts:
        t = float(re.match(r"Frame t=([\d.]+)s", p.label).group(1))
        c = classify(p.data)
        if isinstance(c, int):
            frames.append({"t": t, "phase": "state", "state_name": NAMES[c].upper() if c == 1 else NAMES[c],
                           "properties": [f"prop {c}a", f"prop {c}b"], "hands_occlude": False})
            if NAMES[c] not in [n["state_name"] for n in notes]:
                notes.append({"state_name": NAMES[c], "how_to": f"fold into {NAMES[c]}"})
        else:
            frames.append({"t": t, "phase": "transition" if c == "t" else "unclear", "state_name": None, "properties": []})
    return json.dumps({"frames": frames, "fold_notes": notes})


class FakeGateway:
    """Duck-typed ModelGateway: records every call, validates through the real DTO path."""

    def __init__(self, responder):
        self.responder = responder
        self.calls = []

    def generate_json(self, *, model_key, prompt_id, prompt_version, prompt_text, schema, parts=(), system="", expected_behavior=""):
        self.calls.append({"model_key": model_key, "prompt_id": prompt_id, "parts": list(parts), "prompt": prompt_text})
        text = self.responder(prompt_id, prompt_text, parts)
        key = replay_key(model_key, prompt_id, prompt_version, system, [*parts, prompt_text])
        meta = RunMetadata(run_id="fake", provider="fake", model_key=model_key, model_id="fake", prompt_id=prompt_id,
                           prompt_version=prompt_version, prompt_sha256="", input_digests=[], runtime_class="RECORDED_LIVE",
                           started_at="", latency_ms=0, replay_key=key)
        return GenerationResult(ModelGateway._validate(text, schema, prompt_id), text, meta)


EXPERT_SEQ = [(0, 3), ("t", 2), (1, 4), ("t", 3), (2, 4), ("t", 2), (3, 3), ("t", 6), (4, 3), ("t", 4), (5, 3)]


@pytest.fixture
def expert(tmp_path):
    video = make_video(tmp_path / "expert.mp4", EXPERT_SEQ)
    src = SourceRecord(source_id="src.origami.test.v1", role="expert_video", mime_type="video/mp4", sha256="0" * 64, bytes=1,
                       path="expert.mp4", window_sec=[0.0, 37.0], creator="test", license="CC0", attribution="test",
                       runtime_label="SYNTHETIC")
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    return video, src, case_dir


def _ctx(case_dir, gw):
    return RunContext(mode="recorded", gateway=gw, case_dir=case_dir, data_dir=case_dir / "data")


def test_build_states_claims_criteria(expert):
    video, src, case_dir = expert
    gw = FakeGateway(states_responder)
    r = og.build(video, src, _ctx(case_dir, gw), case_id="origami", version=1)
    goal = goal_schema.PAYLOAD_MODEL.model_validate(r.goal_payload)
    assert [s.name for s in goal.states] == NAMES          # names normalised (upper-case variant merged)
    assert goal.final_state_index == 5
    # transitions into states: R1 2s, R2 3s, R3 2s, R4 6s, R5 4s -> key state R4
    assert goal.key_state_index == 4
    for s in goal.states:
        assert (case_dir / "knowledge" / "goal_assets" / s.keyframe_asset).exists()
        assert s.start_sec <= s.keyframe_sec <= s.end_sec
    assert goal.states[0].start_sec == 0.0 and goal.states[5].end_sec >= 34.0
    # claims: 6 observed states, 1 order claim, 5 inferred how-to claims
    assert [c.claim_id for c in r.claims] == [f"CLM-{i:02d}" for i in range(1, 13)]
    assert all(c.is_observed for c in r.claims[:7]) and not any(c.is_observed for c in r.claims[7:])
    assert all(e.verification_state.value == "inferred" for c in r.claims[7:] for e in c.evidence_refs)
    assert r.claims[0].evidence_refs[0].source_id == "src.origami.test.v1"
    assert r.claims[0].evidence_refs[1].source_id.startswith("src.origami.test.v1#frame=")
    assert all(e.modality.value == "video" for c in r.claims for e in c.evidence_refs)
    # criteria per evaluation-core §4.2
    ids = {c.criterion_id: c for c in r.criteria}
    assert set(ids) == {"CRIT-ORI-FINAL", "CRIT-ORI-ORDER", "CRIT-ORI-COMPLETE", "CRIT-ORI-CLEAN", "CRIT-ORI-KEYSTEP"}
    assert ids["CRIT-ORI-FINAL"].required and ids["CRIT-ORI-FINAL"].weight == 3
    assert ids["CRIT-ORI-ORDER"].required and ids["CRIT-ORI-ORDER"].weight == 2
    assert {c.observer.metric for c in r.criteria} == {og.METRIC_FINAL, og.METRIC_ORDER, og.METRIC_MISSING, og.METRIC_OFF_PATH, og.METRIC_KEYSTEP}
    CriterionMap(rubric_id="r", package_id="p", criteria={
        c.criterion_id: CriterionMapEntry(order_index=c.order_index, source_claim_ids=c.source_claim_ids,
                                          reference_evidence_ids=c.reference_evidence_ids, why_it_matters=c.why_it_matters,
                                          drill_hint=c.drill_hint) for c in r.criteria})
    claim_ids = {c.claim_id for c in r.claims}
    ev_ids = {e.evidence_id for c in r.claims for e in c.evidence_refs}
    for c in r.criteria:
        assert set(c.source_claim_ids) <= claim_ids and set(c.reference_evidence_ids) <= ev_ids
    lines = r.task_instructions.splitlines()
    assert lines[0].startswith("1. ") and all(re.search(r"\[CLM-\d\d\]", ln) for ln in lines)
    assert set(re.findall(r"CLM-\d\d", r.task_instructions)) <= claim_ids
    assert len(r.run_keys) == len(gw.calls) == 4           # 37 frames / 12 per batch
    assert r.built_with["placeholder"] is False


def test_frames_not_video_and_batch_limits(expert):
    video, src, case_dir = expert
    gw = FakeGateway(states_responder)
    og.build(video, src, _ctx(case_dir, gw), case_id="origami", version=1)
    raw = video.read_bytes()
    for call in gw.calls:
        assert call["model_key"] == "video_frames"
        assert 1 <= len(call["parts"]) <= 12
        for p in call["parts"]:
            assert isinstance(p, ImagePart) and p.mime_type == "image/jpeg" and p.data[:2] == b"\xff\xd8"
            assert p.data != raw and p.label.startswith("Frame t=")
    # later batches are told the known state names
    assert "(none yet)" in gw.calls[0]["prompt"] and "flat square" in gw.calls[1]["prompt"]


def test_deterministic(expert, tmp_path):
    video, src, case_dir = expert
    r1 = og.build(video, src, _ctx(case_dir, FakeGateway(states_responder)), case_id="origami", version=1)
    a1 = (case_dir / "knowledge" / "goal_assets" / "origami_state_0.jpg").read_bytes()
    r2 = og.build(video, src, _ctx(case_dir, FakeGateway(states_responder)), case_id="origami", version=1)
    assert r1.goal_payload == r2.goal_payload and r1.run_keys == r2.run_keys
    assert [c.model_dump() for c in r1.claims] == [c.model_dump() for c in r2.claims]
    assert r1.task_instructions == r2.task_instructions
    assert a1 == (case_dir / "knowledge" / "goal_assets" / "origami_state_0.jpg").read_bytes()


def test_invalid_model_output_raises(expert):
    video, src, case_dir = expert

    def drops_a_frame(pid, text, parts):
        d = json.loads(states_responder(pid, text, parts))
        d["frames"] = d["frames"][1:]
        return json.dumps(d)

    with pytest.raises(ModelError) as e:
        og.build(video, src, _ctx(case_dir, FakeGateway(drops_a_frame)), case_id="origami", version=1)
    assert e.value.category == FailureCategory.MODEL_FAILURE
    with pytest.raises(ModelError):
        og.build(video, src, _ctx(case_dir, FakeGateway(lambda *a: '{"frames": [{"t": 0, "phase": "state"}]}')),
                 case_id="origami", version=1)
    with pytest.raises(ModelError):
        og.build(video, src, _ctx(case_dir, FakeGateway(lambda *a: "not json")), case_id="origami", version=1)


def test_missing_model_is_honest_failure(expert, monkeypatch):
    video, src, case_dir = expert
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    live = RunContext(mode="live", gateway=ModelGateway("live", RunStore([case_dir / "runs"]), ModelRegistry({"video_frames": "gemma-x"})),
                      case_dir=case_dir, data_dir=case_dir)
    with pytest.raises(ModelError):
        og.build(video, src, live, case_id="origami", version=1)
    rec = RunContext.create(case_dir, case_dir / "data", "recorded")
    with pytest.raises(ModelError) as e:
        og.build(video, src, rec, case_id="origami", version=1)
    assert e.value.category == FailureCategory.REPLAY_MISMATCH


def test_too_few_states_is_ambiguous(tmp_path):
    video = make_video(tmp_path / "v.mp4", [(0, 6), ("t", 6)])
    src = SourceRecord(source_id="s", role="expert_video", mime_type="video/mp4", sha256="0" * 64, bytes=1, path="v.mp4",
                       creator="c", license="CC0", attribution="a", runtime_label="SYNTHETIC")
    from tracks.common.models import AnveshanFailure

    with pytest.raises(AnveshanFailure) as e:
        og.build(video, src, _ctx(tmp_path, FakeGateway(states_responder)), case_id="o", version=1)
    assert e.value.category == FailureCategory.AMBIGUOUS_EVIDENCE


def test_merge_states_rules():
    t = [float(i) for i in range(14)]
    raw = ["a", "a", None, "b", "x", "b", None, "b", "b", "a", "a", None, "c", "c"]
    states, warn = og.merge_states(t, raw)
    # single-frame blip "x" is filtered; b's second run extends b; a revisit after b is ignored
    assert [(s.name, s.start_sec, s.end_sec) for s in states] == [("a", 0.0, 1.0), ("b", 3.0, 8.0), ("c", 12.0, 13.0)]
    assert warn and "revisit" in warn[0]
    assert og.mode_filter(["a", "b", "a"]) == ["a", "a", "a"]
    assert og.mode_filter(["a", "b", "c"]) == ["a", "b", "c"]
    assert og.top_properties([["Open End", "x"], ["open end"], ["y"]]) == ["open end", "x", "y"]


def test_payload_schema_and_ui_view():
    st = [{"index": i, "name": n, "properties": ["p"], "start_sec": i * 10.0, "end_sec": i * 10.0 + 2,
           "keyframe_sec": i * 10.0 + 1, "keyframe_asset": f"origami_state_{i}.jpg"} for i, n in enumerate(["a", "b", "c"])]
    p = {"window": [0, 30], "fps": 1.0, "states": st, "final_state_index": 2, "key_state_index": 1}
    v = goal_schema.ui_view(p)
    assert v["kind"] == "origami_video" and [s["label"] for s in v["states"]] == ["R0", "R1", "R2"]
    with pytest.raises(ValueError):
        goal_schema.PAYLOAD_MODEL.model_validate({**p, "final_state_index": 1})
    with pytest.raises(ValueError):
        goal_schema.PAYLOAD_MODEL.model_validate({**p, "states": [st[1], st[0], st[2]]})


@pytest.mark.live
def test_live_build_expert_video(tmp_path):
    """Real Gemma run over the expert window (needs GEMINI_API_KEY and fetched media)."""
    from tracks.common.casedata import load_sources, resolve_media
    from tracks.common.models import load_dotenv

    root = Path(__file__).resolve().parents[3]
    load_dotenv(root / ".env")
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    case = root / "tracks" / "cases" / "origami"
    reg = load_sources(case)
    src = reg.get("src.origami.demo.v1")
    try:
        path = resolve_media(case, src)
    except FileNotFoundError:
        pytest.skip("origami media not fetched")
    work = tmp_path / "origami"
    work.mkdir()
    ctx = RunContext.create(work, tmp_path / "data", "live")
    r = og.build(path, src, ctx, case_id="origami", version=1)
    goal = goal_schema.PAYLOAD_MODEL.model_validate(r.goal_payload)
    assert goal.final_state_index >= 3
