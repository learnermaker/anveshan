"""The audio model's audio_kind resolves speech vs rhythm when both look available."""
from tracks.common.perception import MediaInfoRecord, Observation, PerceptionRecord, Segment
from tracks.common.perceivers.specialist_probe import available_structures

RHYTHM_OK = {"rhythm": (True, "regular onsets")}


def _record(kind: str, transcript: bool = True) -> PerceptionRecord:
    obs = [Observation(obs_id="obs-000", segment_id="seg-000", kind="state", label=f"audio_kind: {kind}",
                       certainty="inferred", producer="model:audio")]
    if transcript:
        obs.append(Observation(obs_id="obs-001", segment_id="seg-000", kind="speech", label="dha dhin dhin dha",
                               certainty="inferred", producer="model:audio"))
    return PerceptionRecord(
        media=MediaInfoRecord(source_id="s", modality="audio", sha256="c" * 64, mime_type="audio/wav", duration_sec=8.0),
        segments=[Segment(segment_id="seg-000", kind="whole")], observations=obs)


def test_speech_disables_rhythm():
    s = available_structures(_record("speech"), RHYTHM_OK)
    assert s["utterance"][0] and not s["temporal_pattern"][0]


def test_percussion_disables_utterance_even_with_transcript():
    s = available_structures(_record("percussion"), RHYTHM_OK)
    assert s["temporal_pattern"][0] and not s["utterance"][0]


def test_mixed_keeps_both():
    s = available_structures(_record("mixed"), RHYTHM_OK)
    assert s["temporal_pattern"][0] and s["utterance"][0]
