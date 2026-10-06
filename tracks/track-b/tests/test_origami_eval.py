"""Origami evaluator tests: deterministic trajectory rules, DTO validation, frames-not-video,
determinism, and the synthetic generator. No live API (fake gateway reads the JPEG colours)."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import re
from pathlib import Path

import av
import numpy as np
import pytest
from PIL import Image

from tracks.common.casedata import GoalModel
from tracks.common.media import probe, sample_frames, sha256_file
from tracks.common.models import (
    AnveshanFailure,
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
from track_b.evaluators import get_evaluator
from track_b.evaluators import origami as ev
from track_b.evaluators.origami_trajectory import analyze, mode_filter
from track_b.trajectory import AttemptMedia

ROOT = Path(__file__).resolve().parents[3]
PALETTE = [(220, 30, 30), (30, 200, 30), (30, 30, 220), (230, 230, 30), (220, 30, 220)]
OFF = (120, 0, 255)


# ---------------------------------------------------------------------------
# Pure trajectory rules
# ---------------------------------------------------------------------------

T = "transition"
U = "unclear"
X = "off_path"


def run(labels, k=4, key=None, times=None):
    return analyze(times or [float(i) for i in range(len(labels))], labels, k, key)


def test_mode_filter_window3():
    assert mode_filter([0, 1, 0, 0]) == [0, 0, 0, 0]
    assert mode_filter([0, 1, 2]) == [0, 1, 2]
    assert mode_filter([1, 1, T, 1]) == [1, 1, 1, 1]
    assert mode_filter([X, 0]) == [X, 0]                 # edge window of 2 needs agreement


def test_perfect_path():
    tr = run([0, 0, T, 1, 1, T, 2, 2, T, 3, 3, T, 4, 4], key=3)
    assert tr.missing == [] and tr.order_violations == 0 and tr.off_path_events == 0
    assert tr.final_reached and tr.progress == 1.0 and tr.events == []
    assert tr.keystep == 1.0
    assert [p for _, p in tr.curve][:4] == [0.0, 0.0, 0.0, 0.25]
    assert all(b >= a for (_, a), (_, b) in zip(tr.curve, tr.curve[1:]))   # progress is monotone


def test_single_frame_blip_is_filtered():
    tr = run([0, 0, 3, 0, 1, 1, 2, 2, 3, 3, 4, 4])
    assert tr.events == [] and tr.first_reached[3] == 8.0


def test_skipped_state_missing_with_position():
    tr = run([0, 0, T, 1, 1, T, T, 3, 3, T, 4, 4], key=3)
    assert tr.missing == [2]
    e = tr.events[0]
    assert (e.kind, e.expected_state, e.position) == ("missing_state", 2, 7.0)
    assert tr.keystep == 0.0                                # R3 not reached from R2


def test_skip_uncertain_when_unclear_or_brief_or_sparse():
    assert run([0, 0, 1, 1, U, U, 3, 3, 4, 4]).uncertain_missing == [(2, "not visible: frames around the jump are unclear")]
    tr = run([0, 0, 1, 1, T, 2, T, 3, 3, 4, 4])
    assert tr.missing == [] and tr.uncertain_missing[0][0] == 2 and "briefly" in tr.uncertain_missing[0][1]
    times = [0, 1, 2, 3, 10, 11, 12, 13]
    tr = run([0, 0, 1, 1, 3, 3, 4, 4], times=times)
    assert tr.missing == [] and "sparse" in tr.uncertain_missing[0][1]


def test_out_of_order_backfill():
    tr = run([0, 0, T, 2, 2, T, 1, 1, T, 3, 3, 4, 4], key=2)
    assert tr.missing == [] and tr.order_violations == 1
    e = tr.events[0]
    assert (e.kind, e.expected_state, e.position) == ("out_of_order", 1, 3.0)   # placed at the jump
    assert tr.keystep == 0.0


def test_regression_and_off_path():
    tr = run([0, 0, 1, 1, 2, 2, 3, 3, 1, 1, T, 3, 4, 4])   # back two states for 2 frames
    assert tr.off_path_events == 1 and tr.events[0].kind == "regression" and tr.events[0].position == 8.0
    tr = run([0, 0, 1, 1, 2, 2, 3, 3, 2, 2, 3, 3, 4, 4])   # back one state is allowed (e.g. unfolding)
    assert tr.off_path_events == 0
    tr = run([0, 0, 1, 1, X, X, X, 2, 2, 3, 3, 4, 4], key=2)
    assert tr.off_path_events == 1 and tr.events[0].kind == "off_path" and tr.events[0].position == 4.0
    assert tr.keystep == 0.0                                # off-path on the way to the key state
    assert run([0, 0, 1, 1, X, 2, 2, 3, 3, 4, 4]).off_path_events == 0   # single frame is filtered


def test_truncated_and_final():
    tr = run([0, 0, T, 1, 1, T, 2, 2, T])
    assert tr.missing == [3, 4] and not tr.final_reached and tr.last_stable_state == 2
    assert tr.events[0].kind == "missing_state" and tr.events[0].position == 8.0
    tr = run([0, 0, 1, 1, 2, 2, U, U])
    assert tr.missing == [] and [s for s, _ in tr.uncertain_missing] == [3, 4]
    tr = run([0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 2, 2])       # reached k, then fell back
    assert not tr.final_reached and tr.off_path_events == 1


def test_first_divergence_is_earliest_event():
    tr = run([0, 0, 2, 2, X, X, 1, 1, 4, 4])
    kinds = [(e.kind, e.position) for e in tr.events]
    assert kinds[0] == ("out_of_order", 2.0) and kinds == sorted(kinds, key=lambda x: x[1])
    assert ("missing_state", 8.0) in kinds                   # R3 skipped


def test_invalid_labels_rejected():
    with pytest.raises(ValueError):
        run([0, 5])
    with pytest.raises(ValueError):
        run([0, "maybe"])
    with pytest.raises(ValueError):
        run([0, True])


# ---------------------------------------------------------------------------
# Evaluator with a fake gateway over a generated video
# ---------------------------------------------------------------------------


def make_video(path: Path, seq, fps: int = 2, size=(64, 48), audio: bool = False) -> Path:
    rng = np.random.default_rng(0)
    w, h = size
    with av.open(str(path), "w") as c:
        s = c.add_stream("mpeg4", rate=fps)
        s.width, s.height, s.pix_fmt = w, h, "yuv420p"
        a = None
        if audio:
            a = c.add_stream("aac", rate=16000)
        for lab, secs in seq:
            for _ in range(int(round(secs * fps))):
                if lab == "t":
                    img = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
                elif lab == "u":
                    img = np.zeros((h, w, 3), np.uint8)
                elif lab == "x":
                    img = np.full((h, w, 3), OFF, np.uint8)
                else:
                    img = np.full((h, w, 3), PALETTE[lab], np.uint8)
                for pk in s.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
                    c.mux(pk)
        for pk in s.encode():
            c.mux(pk)
        if a is not None:   # a real audio track, like phone videos (Gemma rejects these as video files)
            total = sum(secs for _, secs in seq)
            n = a.codec_context.frame_size or 1024
            tone = (0.1 * np.sin(2 * np.pi * 440 * np.arange(int(total * 16000)) / 16000)).astype(np.float32)
            for i in range(0, len(tone) - n + 1, n):
                af = av.AudioFrame.from_ndarray(tone[i:i + n].reshape(1, -1), format="fltp", layout="mono")
                af.sample_rate, af.pts = 16000, i
                for pk in a.encode(af):
                    c.mux(pk)
            for pk in a.encode():
                c.mux(pk)
    return path


def classify(data: bytes):
    img = np.asarray(Image.open(io.BytesIO(data)).convert("RGB"), dtype=np.float32)
    mean, std = img.reshape(-1, 3).mean(0), img.reshape(-1, 3).std(0).mean()
    if std > 40:
        return T
    if mean.max() < 40:
        return U
    if np.linalg.norm(mean - np.array(OFF)) < 60:
        return X
    d = [np.linalg.norm(mean - np.array(p)) for p in PALETTE]
    return int(np.argmin(d)) if min(d) < 70 else T


def responder(prompt_id, prompt_text, parts):
    refs = [p for p in parts if p.label.startswith("Reference")]
    if prompt_id == "origami_match":
        frames = []
        # v2: no reference image parts; all parts are learner frames
        for p in parts:
            m = re.match(r"Learner frame t=([\d.]+)s", p.label)
            if m:
                frames.append({"t": float(m.group(1)), "state": classify(p.data), "note": "fake"})
        return json.dumps({"frames": frames})
    assert prompt_id == "origami_final"
    # final check still has reference image as first part
    ref_img = classify(refs[0].data) if refs else None
    last = classify(parts[-1].data)
    match = last == ref_img if last != U and ref_img is not None else None
    return json.dumps({"matches": match, "properties": [{"property": "p", "present": match}], "note": "fake"})


class FakeGateway:
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


@pytest.fixture
def goal_case(tmp_path):
    case = tmp_path / "origami"
    assets = case / "knowledge" / "goal_assets"
    assets.mkdir(parents=True)
    states = []
    for i, col in enumerate(PALETTE):
        Image.new("RGB", (64, 48), col).save(assets / f"origami_state_{i}.jpg", quality=90)
        states.append({"index": i, "name": f"state {i}", "properties": [f"prop {i}"], "start_sec": i * 10.0,
                       "end_sec": i * 10.0 + 3, "keyframe_sec": i * 10.0 + 1, "keyframe_asset": f"origami_state_{i}.jpg"})
    goal = GoalModel(case_id="origami", version=1, modality="origami_video", source_ids=["src.origami.test.v1"],
                     package_id="kp.origami.1", payload={"window": [0, 50], "fps": 1.0, "states": states,
                                                         "final_state_index": 4, "key_state_index": 2})
    return goal, case


def attempt_for(path: Path) -> AttemptMedia:
    return AttemptMedia(kind="video", path=path, source_id="upload.test", sha256=sha256_file(path), mime_type="video/mp4")


def ctx_for(case, gw):
    return RunContext(mode="recorded", gateway=gw, case_dir=case, data_dir=case / "data")


def test_registry_points_here():
    assert get_evaluator("origami_video") is ev.evaluate


def test_evaluate_perfect_attempt(goal_case, tmp_path):
    goal, case = goal_case
    video = make_video(tmp_path / "a.mp4", [(0, 3), ("t", 2), (1, 3), ("t", 2), (2, 3), ("t", 2), (3, 3), ("t", 2), (4, 4)])
    gw = FakeGateway(responder)
    r = ev.evaluate(goal, attempt_for(video), ctx_for(case, gw))
    m = r.metrics
    assert m[ev.M_FINAL].value == 1.0 and m[ev.M_ORDER].value == 0 and m[ev.M_MISSING].value == 0
    assert m[ev.M_OFF].value == 0 and m[ev.M_KEY].value == 1.0 and m[ev.M_PROGRESS].value == 1.0
    assert r.events == [] and r.curve_kind == "time" and r.process_observable
    assert r.final_state["reached_by_trajectory"] and r.final_state["pairwise"]["matches"] is True
    assert len(r.run_keys) == len(gw.calls) and gw.calls[-1]["prompt_id"] == "origami_final"
    assert len(r.artifacts["frame_labels"]) == len(r.curve)


def test_evaluate_divergences_with_evidence(goal_case, tmp_path):
    goal, case = goal_case
    # R0, R2 (skips R1, back-filled later -> out of order), off-path, R1, R3, stops (R4 missing)
    seq = [(0, 3), ("t", 1), (2, 3), ("x", 3), (1, 3), ("t", 1), (3, 4)]
    video = make_video(tmp_path / "b.mp4", seq)
    r = ev.evaluate(goal, attempt_for(video), ctx_for(case, FakeGateway(responder)))
    m = r.metrics
    assert m[ev.M_ORDER].value == 1 and m[ev.M_MISSING].value == 1 and m[ev.M_OFF].value >= 1
    assert m[ev.M_FINAL].value == 0.0 and m[ev.M_KEY].value == 0.0
    first = r.events[0]
    assert first.kind == "out_of_order" and first.position_kind == "time" and first.position == pytest.approx(4.0)
    assert first.evidence.source_id == "upload.test#frame=4.000" and first.evidence.modality.value == "video"
    assert "expected R1" in first.detail
    assert [e.position for e in r.events] == sorted(e.position for e in r.events)
    assert m[ev.M_MISSING].evidence is not None and "R4" in m[ev.M_MISSING].finding


def test_frames_not_video_and_image_budget(goal_case, tmp_path):
    goal, case = goal_case
    video = make_video(tmp_path / "c.mp4", [(0, 4), (1, 4), (2, 4), (3, 4), (4, 4)], audio=True)
    assert probe(video).has_audio
    gw = FakeGateway(responder)
    ev.evaluate(goal, attempt_for(video), ctx_for(case, gw))
    raw = video.read_bytes()
    for call in gw.calls:
        assert call["model_key"] == "video_frames"
        assert len(call["parts"]) <= ev.MAX_IMAGES_PER_CALL
        for p in call["parts"]:
            assert isinstance(p, ImagePart) and p.mime_type == "image/jpeg" and p.data[:2] == b"\xff\xd8"
            assert p.data != raw and raw.find(p.data) == -1
    match_calls = [c for c in gw.calls if c["prompt_id"] == "origami_match"]
    # v2 policy: no reference images in match calls; all parts are learner frames
    for mc in match_calls:
        assert all(p.label.startswith("Learner frame") for p in mc["parts"])
    # reference state text must still appear in the prompt
    assert all("R0" in mc["prompt"] for mc in match_calls)


def test_long_video_subsampled_with_warning(goal_case, tmp_path):
    goal, case = goal_case
    video = make_video(tmp_path / "d.mp4", [(0, 20), (1, 20), (2, 20), (3, 20), (4, 20)], fps=1)
    r = ev.evaluate(goal, attempt_for(video), ctx_for(case, FakeGateway(responder)))
    assert r.artifacts["sampled_frames"] == ev.MAX_FRAMES
    assert any("subsampled" in w for w in r.warnings)
    assert r.metrics[ev.M_FINAL].value == 1.0


def test_deterministic(goal_case, tmp_path):
    goal, case = goal_case
    video = make_video(tmp_path / "e.mp4", [(0, 3), ("t", 2), (1, 3), (3, 3), (4, 3)])
    a = ev.evaluate(goal, attempt_for(video), ctx_for(case, FakeGateway(responder)))
    b = ev.evaluate(goal, attempt_for(video), ctx_for(case, FakeGateway(responder)))
    assert a.curve == b.curve and a.run_keys == b.run_keys and a.artifacts == b.artifacts
    assert {k: (v.value, v.finding) for k, v in a.metrics.items()} == {k: (v.value, v.finding) for k, v in b.metrics.items()}
    assert [(e.kind, e.position, e.detail) for e in a.events] == [(e.kind, e.position, e.detail) for e in b.events]


def test_recorded_replay_through_real_gateway(goal_case, tmp_path):
    """Live run with a fake google-genai client is recorded, then replays identically in recorded mode."""
    goal, case = goal_case
    video = make_video(tmp_path / "f.mp4", [(0, 3), (1, 3), (2, 3), (3, 3), (4, 3)])

    class Models:
        def generate_content(self, model, contents, config):
            parts = []
            label = None
            for c in contents[:-1]:
                if isinstance(c, str):
                    label = c
                else:
                    parts.append(ImagePart(data=c.inline_data.data, label=label))
            pid = "origami_final" if "final frame" in contents[-1] else "origami_match"
            return type("R", (), {"text": responder(pid, contents[-1], parts)})()

    store = tmp_path / "runs"
    live = RunContext(mode="live", gateway=ModelGateway("live", RunStore([store]), ModelRegistry({"video_frames": "gemma-test"}),
                                                        client=type("C", (), {"models": Models()})()),
                      case_dir=case, data_dir=tmp_path)
    a = ev.evaluate(goal, attempt_for(video), live)
    rec = RunContext(mode="recorded", gateway=ModelGateway("recorded", RunStore([store])), case_dir=case, data_dir=tmp_path)
    b = ev.evaluate(goal, attempt_for(video), rec)
    assert a.run_keys == b.run_keys and a.curve == b.curve and a.metrics[ev.M_FINAL].value == 1.0


def test_invalid_model_output_and_inputs(goal_case, tmp_path):
    goal, case = goal_case
    video = make_video(tmp_path / "g.mp4", [(0, 3), (1, 3)])

    def out_of_range(pid, text, parts):
        if pid == "origami_match":
            return json.dumps({"frames": [{"t": float(re.match(r"Learner frame t=([\d.]+)s", p.label).group(1)), "state": 9}
                                          for p in parts if p.label.startswith("Learner")]})
        return responder(pid, text, parts)

    for bad in (out_of_range, lambda *a: '{"frames": [{"t": 0.0, "state": "maybe"}]}', lambda *a: '{"frames": []}', lambda *a: "nope"):
        with pytest.raises(ModelError):
            ev.evaluate(goal, attempt_for(video), ctx_for(case, FakeGateway(bad)))
    assert ev.FrameMatchDTO.model_validate({"t": 1, "state": "R2"}).state == 2
    assert ev.FrameMatchDTO.model_validate({"t": 1, "state": 3.0}).state == 3
    with pytest.raises(ValueError):
        ev.FrameMatchDTO.model_validate({"t": 1, "state": True})
    with pytest.raises(AnveshanFailure) as e:
        ev.evaluate(goal, AttemptMedia(kind="image", path=video, source_id="u", sha256="", mime_type="image/png"),
                    ctx_for(case, FakeGateway(responder)))
    assert e.value.category == FailureCategory.INVALID_INPUT
    (case / "knowledge" / "goal_assets" / "origami_state_3.jpg").unlink()
    with pytest.raises(AnveshanFailure) as e:
        ev.evaluate(goal, attempt_for(video), ctx_for(case, FakeGateway(responder)))
    assert e.value.category == FailureCategory.MISSING_EVIDENCE


def test_missing_model_is_honest_failure(goal_case, tmp_path, monkeypatch):
    goal, case = goal_case
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    video = make_video(tmp_path / "h.mp4", [(0, 3), (1, 3)])
    ctx = RunContext.create(case, tmp_path / "data", "live")
    with pytest.raises(ModelError):
        ev.evaluate(goal, attempt_for(video), ctx)


# ---------------------------------------------------------------------------
# Synthetic generator
# ---------------------------------------------------------------------------


def _gen():
    p = ROOT / "tracks" / "track-b" / "eval" / "origami" / "make_synthetic.py"
    spec = importlib.util.spec_from_file_location("origami_make_synthetic", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ground_truth_committed_matches_generator():
    g = _gen()
    labels = json.loads((g.LABELS / "expert_window_labels.json").read_text(encoding="utf-8"))
    learner = json.loads((g.LABELS / "learner_crane_window_labels.json").read_text(encoding="utf-8"))
    gt = g.ground_truth(labels, learner)
    committed = json.loads((g.LABELS / "synthetic_ground_truth.json").read_text(encoding="utf-8"))
    assert gt == committed
    v = gt["variants"]
    assert v["missing_state"]["expected"]["missing_states"] == [2]
    assert v["swapped_order"]["expected"]["order_violations"] == 1
    assert v["swapped_order"]["expected"]["state_order"] == [0, 2, 1, 3, 4, 5, 6]
    assert v["truncated"]["expected"]["missing_states"] == [5, 6] and not v["truncated"]["expected"]["final_reached"]
    assert v["perfect"]["expected"]["first_divergence"] is None
    for name, var in v.items():
        assert var["duration_sec"] == pytest.approx(sum(b - a for a, b in var["segments"]))
        assert var["runtime_label"] == ("INTERNET_REFERENCE" if name == "real_learner" else "SYNTHETIC")
    assert labels["annotator"].startswith("claude (AI-assisted)")


def test_render_segments_no_audio(tmp_path):
    g = _gen()
    src = make_video(tmp_path / "src.mp4", [(0, 2), (1, 2), (2, 2), (3, 2)], fps=10, audio=True)
    out = tmp_path / "out.mp4"
    n = g.render(src, [(0.0, 2.0), (4.0, 6.0), (2.0, 4.0)], out, fps=10)
    assert n == 60
    info = probe(out)
    assert not info.has_audio and info.duration_sec == pytest.approx(6.0, abs=0.2)
    fr = sample_frames(out, fps=1.0, max_side=64)
    from track_b.evaluators.origami import image_to_jpeg_bytes

    labels = [classify(image_to_jpeg_bytes(f.image)) for f in fr]
    assert labels[0] == 0 and labels[2] == 2 and labels[4] == 1     # swapped segment order is rendered


def test_agreement_scoring():
    p = ROOT / "tracks" / "track-b" / "eval" / "origami" / "run_eval.py"
    spec = importlib.util.spec_from_file_location("origami_run_eval", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    gt = {"state_intervals": {"0": [[0, 2]], "1": [[5, 6]]},
          "expected": {"missing_states": [2], "order_violations": 0, "final_reached": False,
                       "first_divergence": {"kind": "missing_state", "state": 2, "position_sec": 9.0}}}
    result = {"metrics": {"origami.order_violations": {"value": 0.0}},
              "trajectory": {"events": [{"kind": "missing_state", "position": 10.0}],
                             "final_state": {"reached_by_trajectory": False},
                             "artifacts": {"missing_states": [2], "uncertain_states": [],
                                           "frame_labels": [{"t": 0, "filtered": 0}, {"t": 1, "filtered": 0},
                                                            {"t": 5, "filtered": "transition"}, {"t": 6, "filtered": 1}]}}}
    s = mod.score(result, gt)
    assert s["frame_state_accuracy"] == 0.75 and s["missing_exact"] and s["order_violations_exact"]
    assert s["first_divergence_kind_agrees"] and s["first_divergence_abs_error_sec"] == 1.0
    ga = mod.goal_agreement([{"start_sec": 0, "end_sec": 3}, {"start_sec": 9, "end_sec": 15}],
                            [{"index": 0, "intervals": [[0, 3]]}, {"index": 1, "intervals": [[8, 16]]}])
    assert ga["order_preserved"] and ga["median_boundary_error_sec"] == 0.5


@pytest.mark.live
def test_live_evaluate_real_learner():
    """Real Gemma run on the real learner window against the built goal (needs key, built goal, generated videos)."""
    from tracks.common.casedata import latest_version, load_versioned
    from tracks.common.models import load_dotenv

    load_dotenv(ROOT / ".env")
    if not os.environ.get("GEMINI_API_KEY"):
        pytest.skip("GEMINI_API_KEY not set")
    case = ROOT / "tracks" / "cases" / "origami"
    if latest_version(case / "knowledge", "goal_model") is None:
        pytest.skip("origami goal not built yet")
    video = ROOT / "var" / "eval" / "origami" / "real_learner.mp4"
    if not video.exists():
        pytest.skip("run make_synthetic.py first")
    goal = load_versioned(case / "knowledge", "goal_model", GoalModel)
    ctx = RunContext.create(case, ROOT / "var" / "data", "live")
    r = ev.evaluate(goal, attempt_for(video), ctx)
    assert r.metrics[ev.M_FINAL].value is not None
