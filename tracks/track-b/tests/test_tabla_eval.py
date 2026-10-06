"""Track B tabla evaluator on synthetic click/bass tracks (no track_a import; fake model gateway)."""

import json

import numpy as np
import pytest

from tracks.common import locators
from tracks.common import tabla_dsp as dsp
from tracks.common.casedata import GoalModel
from tracks.common.models import AnveshanFailure, FailureCategory, ModelGateway, ModelRegistry, RunStore
from tracks.common.runtime import RunContext
from tracks.common.tests.test_tabla_goal_model import SR, synth_tabla, write_wav

from track_b.evaluators import get_evaluator
from track_b.evaluators.tabla import evaluate
from track_b.trajectory import AttemptMedia


class _FakeModels:
    def __init__(self, text):
        self.text = text

    def generate_content(self, model, contents, config):
        return type("R", (), {"text": self.text})()


def _ctx(tmp_path, audio_model="", reply="{}"):
    gw = ModelGateway("live", RunStore([tmp_path / "runs"]), ModelRegistry({"audio": audio_model}),
                      client=type("C", (), {"models": _FakeModels(reply)})())
    return RunContext(mode="live", gateway=gw, case_dir=tmp_path, data_dir=tmp_path)


def _goal(bols=None):
    x, _, _ = synth_tabla()
    p = dsp.analyze_goal_audio(x, SR)
    p["window_sec"] = [10.0, 10.0 + len(x) / SR]
    if bols:
        p["bols"] = [{"t": o["t"], "bol": b} for o, b in zip(p["onsets"], bols)]
        p["bols_status"] = "inferred"
    return GoalModel(case_id="tabla", version=1, modality="tabla_audio", source_ids=["src.tabla.test.v1"],
                     package_id="kp.tabla.1", payload=p)


def _attempt(tmp_path, x, name="a", kind="audio", extra=None):
    p = write_wav(tmp_path / f"{name}.wav", x)
    return AttemptMedia(kind=kind, path=p, source_id=f"upload.{name}", sha256="0" * 64, mime_type="audio/wav",
                        extra=extra or {})


def _material(res):
    return [e for e in res.events if e.severity == "material"]


@pytest.fixture(scope="module")
def goal():
    return _goal()


def test_registry_points_to_tabla_evaluator():
    assert get_evaluator("tabla_audio") is evaluate


def test_perfect_copy(tmp_path, goal):
    x, _, _ = synth_tabla()
    r = evaluate(goal, _attempt(tmp_path, x), _ctx(tmp_path))
    m = r.metrics
    assert m["tabla.tempo_error_pct"].value < 0.5
    assert m["tabla.timing_median_ms"].value < 5
    assert m["tabla.bass_accuracy"].value == 1.0
    assert m["tabla.missing_extra"].value == 0
    assert m["tabla.ioi_cv"].value < 0.05
    assert m["tabla.bol_accuracy"].value is None and m["tabla.bol_accuracy"].uncertain_reason == "audio_model_disabled"
    assert _material(r) == [] and r.events == []
    assert r.curve_kind == "time" and r.process_observable
    ys = [y for _, y in r.curve]
    assert ys == sorted(ys) and ys[0] == 0.0 and ys[-1] == 1.0
    assert len(r.artifacts["learner_onsets"]) == 28 and len(r.artifacts["alignment"]) == 28


def test_deterministic(tmp_path, goal):
    x, _, _ = synth_tabla(shift={9: 0.07})
    a = evaluate(goal, _attempt(tmp_path, x, "d1"), _ctx(tmp_path))
    b = evaluate(goal, _attempt(tmp_path, x, "d1"), _ctx(tmp_path))
    assert json.dumps(a.artifacts, sort_keys=True) == json.dumps(b.artifacts, sort_keys=True)
    assert [(e.kind, e.position) for e in a.events] == [(e.kind, e.position) for e in b.events]


def test_tempo_change_detected(tmp_path, goal):
    x, _, _ = synth_tabla(tempo=1.08)
    r = evaluate(goal, _attempt(tmp_path, x), _ctx(tmp_path))
    assert abs(r.metrics["tabla.tempo_error_pct"].value - 8.0) < 0.6
    assert r.metrics["tabla.timing_median_ms"].value < 10
    first = _material(r)[0]
    assert first.kind == "tempo_off" and abs(first.position - 0.5) < 0.05


def test_late_stroke_is_first_divergence_with_onset_locator(tmp_path, goal):
    x, times, _ = synth_tabla(shift={12: 0.09})
    r = evaluate(goal, _attempt(tmp_path, x, "late"), _ctx(tmp_path))
    first = _material(r)[0]
    assert first.kind == "late_stroke" and abs(first.position - times[12]) < 0.03
    loc = locators.parse(first.evidence.source_id)
    assert loc.source == "upload.late.onsets" and loc.key == "onset" and loc.value == "12"
    assert first.evidence.modality.value == "audio" and first.evidence.start_sec < first.position
    assert r.metrics["tabla.timing_median_ms"].value < 10  # one late stroke does not move the median


def test_dropped_stroke_is_missing(tmp_path, goal):
    full, times, _ = synth_tabla()
    x, _, _ = synth_tabla(drop={10})
    r = evaluate(goal, _attempt(tmp_path, x, "drop"), _ctx(tmp_path))
    assert r.metrics["tabla.missing_extra"].value == 1
    first = _material(r)[0]
    assert first.kind == "missing_stroke" and abs(first.position - times[10]) < 0.03
    assert r.final_state["missing"] == 1 and r.curve[-1][1] == pytest.approx(27 / 28, abs=1e-3)


def test_bass_withheld_where_source_has_it(tmp_path, goal):
    _, times, bass = synth_tabla()
    j = [i for i, b in enumerate(bass) if b][4]
    x, _, _ = synth_tabla(nobass={j})
    r = evaluate(goal, _attempt(tmp_path, x, "nob"), _ctx(tmp_path))
    first = _material(r)[0]
    assert first.kind == "bass_missing" and abs(first.position - times[j]) < 0.03
    n_b = sum(bass)
    assert r.metrics["tabla.bass_accuracy"].value == pytest.approx((1 - 1 / n_b + 1) / 2, abs=1e-3)
    assert not r.artifacts["bass_threshold"]["adapted"]


def test_extra_stroke_in_empty_pulse(tmp_path, goal):
    t_extra = 0.5 + 3 * 0.25 + 8 * 0.25   # the empty pulse of the second cycle
    x, _, _ = synth_tabla(extra_at=[t_extra])
    r = evaluate(goal, _attempt(tmp_path, x, "extra"), _ctx(tmp_path))
    assert r.metrics["tabla.missing_extra"].value == 1
    first = _material(r)[0]
    assert first.kind == "extra_stroke" and abs(first.position - t_extra) < 0.03


def test_video_is_ignored_with_note(tmp_path, goal):
    x, _, _ = synth_tabla()
    r = evaluate(goal, _attempt(tmp_path, x, "v", extra={"video": tmp_path / "v.mp4"}), _ctx(tmp_path))
    assert any("not scored" in w for w in r.warnings) and r.artifacts["video_ignored"] is True
    assert r.metrics["tabla.missing_extra"].value == 0


@pytest.mark.parametrize("case", ["short", "silence", "clipped", "no_strokes", "wrong_kind"])
def test_invalid_input(tmp_path, goal, case):
    x, _, _ = synth_tabla()
    kind = "audio"
    if case == "short":
        x = x[: int(2.0 * SR)]
    elif case == "silence":
        x = np.zeros(5 * SR, dtype=np.float32)
    elif case == "clipped":
        x = np.clip(x * 40, -1, 1)
    elif case == "no_strokes":
        x = (0.1 * np.sin(2 * np.pi * 220 * np.arange(5 * SR) / SR)).astype(np.float32)
    else:
        kind = "video"
    with pytest.raises(AnveshanFailure) as e:
        evaluate(goal, _attempt(tmp_path, x, case, kind=kind), _ctx(tmp_path))
    assert e.value.category == FailureCategory.INVALID_INPUT
    assert len(e.value.message) > 20  # learner-readable message


def test_bols_scored_only_when_audio_model_enabled(tmp_path):
    bols = ["Dha", "Dhin", "Na", "Dha", "Na", "Tin", "Na"] * 4
    goal = _goal(bols)
    x, times, _ = synth_tabla()
    reply = json.dumps({"bols": [{"t": round(t, 3), "bol": b} for t, b in zip(times, bols[:-1] + ["Ta"])]})
    r = evaluate(goal, _attempt(tmp_path, x, "b"), _ctx(tmp_path, "audio-test-model", reply))
    assert r.metrics["tabla.bol_accuracy"].value == pytest.approx(1 - 1 / 28, abs=1e-3) and len(r.run_keys) == 1
    r2 = evaluate(goal, _attempt(tmp_path, x, "b2"), _ctx(tmp_path))
    assert r2.metrics["tabla.bol_accuracy"].value is None
    assert r2.metrics["tabla.bol_accuracy"].uncertain_reason == "audio_model_disabled"
