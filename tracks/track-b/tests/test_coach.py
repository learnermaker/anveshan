"""AI coaching wording (WI-4.1): rewrites advice only, guarded; failures fall back to the template."""

from __future__ import annotations

import json
from pathlib import Path

from tracks.common.models import ModelGateway, ModelRegistry, RunStore
from tracks.common.runtime import RunContext
from tracks.common.schemas import Feedback, FeedbackItem

from track_b.coach import CoachWording, enabled
from track_b.feedback import guard_wording


def _template() -> Feedback:
    return Feedback(
        feedback_id="fb.1",
        evaluation_id="eval.1",
        attempt_id="att.1",
        summary="1 of 2 criteria met (1 / 3).",
        items=[
            FeedbackItem(
                criterion_id="CRIT-A",
                what_was_observed="42.8% of ink lies within 6.0 px of the line",
                what_differed="Does not meet the target.",
                corrective_advice="Slow down at crossings. Why it matters: no stray marks (CLM-05).",
            )
        ],
        recommended_retry_focus=["CRIT-A"],
    )


class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text


class _Client:
    def __init__(self, text: str) -> None:
        self._text = text
        self.calls = 0
        outer = self

        class Models:
            def generate_content(self, **kw):
                outer.calls += 1
                return _Resp(outer._text)

        self.models = Models()


def _ctx(tmp_path: Path, text: str, monkeypatch) -> RunContext:
    monkeypatch.setenv("ANVESHAN_LIVE_CACHE", "0")
    monkeypatch.delenv("ANVESHAN_DAILY_CALL_BUDGET", raising=False)
    gw = ModelGateway("live", RunStore([tmp_path / "runs"]), registry=ModelRegistry({"vision_fast": "m"}), client=_Client(text))
    return RunContext(mode="live", gateway=gw, case_dir=tmp_path, data_dir=tmp_path)


def _coach(ctx):
    return CoachWording(ctx, "Kolam", {"CRIT-A": "No stray lines"})


def _out(coaching: str) -> str:
    return json.dumps({"items": [{"criterion_id": "CRIT-A", "coaching": coaching}]})


def test_good_rewrite_is_accepted_and_only_advice_changes(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, _out("Go slowly where lines cross so you stay on the faint guide; stray marks cannot be erased (CLM-05)."), monkeypatch)
    t = _template()
    w = _coach(ctx)
    cand = w(t)
    final = guard_wording(t, cand, {"CRIT-A", "CLM-05"})
    assert final.items[0].corrective_advice.startswith("Go slowly")
    assert final.items[0].what_was_observed == t.items[0].what_was_observed
    assert w.view(final != t)["status"] == "ai_worded"


def test_new_number_is_rejected_by_guard(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, _out("Draw 3 times slower at crossings (CLM-05)."), monkeypatch)
    t = _template()
    w = _coach(ctx)
    final = guard_wording(t, w(t), {"CRIT-A", "CLM-05"})
    assert final == t
    assert w.view(False)["status"] == "template"


def test_dropped_claim_id_is_rejected(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, _out("Go slowly where lines cross."), monkeypatch)
    t = _template()
    assert guard_wording(t, _coach(ctx)(t), {"CRIT-A", "CLM-05"}) == t


def test_verdict_language_is_rejected(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, _out("You failed this check; slow down (CLM-05)."), monkeypatch)
    t = _template()
    w = _coach(ctx)
    assert w(t) == t
    assert w.reason == "fixed wording kept for CRIT-A"


def test_model_failure_keeps_template_with_reason(tmp_path, monkeypatch):
    gw = ModelGateway("recorded", RunStore([tmp_path / "none"]), registry=ModelRegistry({"vision_fast": "m"}))
    ctx = RunContext(mode="recorded", gateway=gw, case_dir=tmp_path, data_dir=tmp_path)
    t = _template()
    w = _coach(ctx)
    assert w(t) == t
    assert w.view(False) == {"status": "template", "reason": "coach wording unavailable (REPLAY_MISMATCH)", "model_id": None, "run_key": None}


def test_can_be_disabled(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, _out("x"), monkeypatch)
    monkeypatch.setenv("ANVESHAN_COACH_WORDING", "0")
    assert enabled(ctx) is False


def test_passes_through_is_not_verdict_language(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, _out("Make sure the line passes through each dot at a stopping point (CLM-05)."), monkeypatch)
    t = _template()
    assert _coach(ctx)(t) != t
