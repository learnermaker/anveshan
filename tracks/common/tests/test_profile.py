"""Tests for the composed-case profile model."""

import pytest

from tracks.common.profile import CaseProfile, ProbeFacts, composed_case_id, slugify


def _probe(**kw):
    base = dict(modality="image", mime_type="image/png", bytes=10, sha256="ab" * 32, allowed_families=["image_target", "rubric_vlm"])
    base.update(kw)
    return ProbeFacts(**base)


def test_slug_and_case_id():
    assert slugify("Rangoli — Lotus (Simple)!") == "rangoli-lotus-simple"
    assert slugify("தமிழ்") == "skill"
    assert composed_case_id("Paper Cup", "ABCDEF0123456789" + "0" * 48) == "paper-cup~abcdef012345"


def test_profile_validation():
    ok = CaseProfile(case_id="lotus~abcdef012345", title="Lotus", skill_summary="s", domain="d", family="image_target",
                     transmission_mode="goal-conditioned", learner_input_kinds=["trace"], probe=_probe())
    assert ok.modality == "kolam_image"
    with pytest.raises(ValueError):  # family not allowed by probe
        CaseProfile(case_id="lotus~abcdef012345", title="L", skill_summary="s", domain="d", family="video_states",
                    transmission_mode="forward", learner_input_kinds=["video"], probe=_probe())
    with pytest.raises(ValueError):  # kind not accepted by family
        CaseProfile(case_id="lotus~abcdef012345", title="L", skill_summary="s", domain="d", family="image_target",
                    transmission_mode="forward", learner_input_kinds=["audio"], probe=_probe())
    with pytest.raises(ValueError):  # bad id
        CaseProfile(case_id="Lotus", title="L", skill_summary="s", domain="d", family="image_target",
                    transmission_mode="forward", learner_input_kinds=["trace"], probe=_probe())
