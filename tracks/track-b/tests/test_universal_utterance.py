"""Utterance skills: an attempt with no audible speech is refused, not scored."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from tracks.common.models import AnveshanFailure
from track_b.evaluators.universal import _utterance_checks
from track_b.trajectory import AttemptMedia


def _skill():
    check = SimpleNamespace(kind="utterance_match", enabled=True, metric_id="u.utterance_match")
    return SimpleNamespace(utterance={"transcript": "keep the lane clear", "duration_sec": 3.0}, checks=[check])


def _ctx(audio_model):
    return SimpleNamespace(gateway=SimpleNamespace(registry=SimpleNamespace(model_id=lambda k: audio_model)))


ATTEMPT = AttemptMedia(kind="audio", path=Path("a.wav"), source_id="upload.abc", sha256="0" * 64, mime_type="audio/wav")
NO_SPEECH = SimpleNamespace(observations=[])


def test_no_speech_with_audio_model_is_refused():
    with pytest.raises(AnveshanFailure) as exc:
        _utterance_checks(_skill(), ATTEMPT, NO_SPEECH, _ctx("gemini-3.5-flash-lite"))
    assert "No speech" in str(exc.value)


def test_no_speech_without_audio_model_is_uncertain():
    m = _utterance_checks(_skill(), ATTEMPT, NO_SPEECH, _ctx(""))
    assert m["u.utterance_match"].value is None
    assert "audio model disabled" in m["u.utterance_match"].uncertain_reason
