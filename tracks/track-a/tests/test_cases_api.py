"""list_cases / load_case / create_upload_case / to_view."""

import json
import wave

import numpy as np
import pytest

from tracks.common.casedata import load_sources
from tracks.common.models import AnveshanFailure, FailureCategory

from track_a import api, config

from ta_helpers import REAL_CASES, write_png

SHOWCASE = ["micrometer", "bicycle-repair", "handloom-weaving", "square-knot"]


def write_wav(path, seconds=1.0, sr=16000):
    x = (np.sin(2 * np.pi * 220 * np.arange(int(seconds * sr)) / sr) * 0.3 * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(x.tobytes())


def test_list_cases_orders_hero_upload_showcase(cases_root, data_dir, tmp_path, fake_builder, make_ctx):
    api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam"))
    img = tmp_path / "mine.png"
    write_png(img)
    up = api.create_upload_case(cases_root, data_dir, "kolam", img, "image/png")
    cases = api.list_cases(cases_root, data_dir)
    ids = [c["case_id"] for c in cases]
    assert ids[:3] == ["kolam", "origami", "tabla"]
    assert ids[3] == up.name
    assert ids[4:] == SHOWCASE
    by = {c["case_id"]: c for c in cases}
    assert by["kolam"] == {
        "case_id": "kolam",
        "title": by["kolam"]["title"],
        "modality": "kolam_image",
        "hero": True,
        "runtime_label": "INTERNET_REFERENCE",
        "review_status": "pending",
        "built": True,
    }
    assert by[up.name]["derived_from"] == "kolam" and by[up.name]["runtime_label"] == "UPLOAD"
    assert by[up.name]["hero"] is False and by[up.name]["modality"] == "kolam_image" and by[up.name]["built"] is False
    for cid in SHOWCASE:
        assert by[cid]["runtime_label"] == "SYNTHETIC" and by[cid]["hero"] is False and by[cid]["modality"] is None
    assert by["tabla"]["built"] is False


def test_list_cases_on_real_case_root(data_dir):
    cases = api.list_cases(REAL_CASES, data_dir)
    assert [c["case_id"] for c in cases] == ["kolam", "origami", "tabla", *SHOWCASE]


@pytest.mark.parametrize("cid", SHOWCASE)
def test_load_showcase_is_synthetic_without_goal(cid):
    h = api.load_case(REAL_CASES / cid)
    assert h.runtime_label == "SYNTHETIC" and h.goal is None and h.criterion_map is None and h.observers is None
    v = h.to_view()
    assert v["goal"] is None and v["runtime_label"] == "SYNTHETIC" and v["hero"] is False
    assert v["task"]["package_id"] == v["package"]["package_id"]
    assert v["lesson"]["criteria"]
    json.dumps(v)


def test_unbuilt_hero_falls_back_to_bundle_with_warning(cases_root):
    h = api.load_case(cases_root / "tabla")
    assert h.goal is None and h.runtime_label == "SYNTHETIC"
    assert any("not built" in w for w in h.warnings)


def test_to_view_never_exposes_held_out(cases_root, fake_builder, make_ctx):
    h = api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam"))
    v = h.to_view()
    blob = json.dumps(v)
    assert "held_out" not in blob and "src.kolam.held_out.v1" not in blob
    assert [s["source_id"] for s in v["sources"]] == ["src.kolam.target.v1"]
    assert v["sources"][0]["media_url"] == "/api/media/kolam/src.kolam.target.v1"
    assert "path" not in v["sources"][0]
    assert v["goal"]["modality"] == "kolam_image" and v["goal"]["version"] == 1
    assert v["criterion_map"]["package_id"] == "kp.kolam.1" and v["observers"]["rubric_id"] == "rubric.kolam.1"
    assert v["review_status"] == "pending" and v["runtime_label"] == "INTERNET_REFERENCE"
    assert [c["criterion_id"] for c in v["lesson"]["criteria"]] == ["CRIT-KOLAM-COVERAGE", "CRIT-KOLAM-DOTS"]
    assert [s["claim_id"] for s in v["lesson"]["steps"]] == ["CLM-03", "CLM-04"]


def test_to_view_real_kolam_registry_hides_held_out():
    reg = load_sources(REAL_CASES / "kolam")
    pub = api.public_sources("kolam", reg)
    assert [s["source_id"] for s in pub] == ["src.kolam.target.v1"]


def test_to_view_goal_ui_view_tolerates_missing_module(cases_root, fake_builder, make_ctx, monkeypatch):
    import importlib

    real = importlib.import_module

    def fake_import(name, *a, **k):
        if name.startswith("tracks.common.goals."):
            raise ImportError(name)
        return real(name, *a, **k)

    monkeypatch.setattr(api.importlib, "import_module", fake_import)
    v = api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam")).to_view()
    assert v["goal"]["ui_view"] is None
    assert any("ui_view unavailable" in w for w in v["warnings"])


def test_to_view_uses_modality_ui_view(cases_root, fake_builder, make_ctx, monkeypatch):
    import types

    mod = types.SimpleNamespace(ui_view=lambda payload: {"n_dots": len(payload["dots"])})
    monkeypatch.setattr(api.importlib, "import_module", lambda name, *a, **k: mod)
    h = api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam"))
    assert h.to_view()["goal"]["ui_view"] == {"n_dots": 1}


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------


def test_create_upload_case_image(cases_root, data_dir, tmp_path, fake_builder, make_ctx):
    img = tmp_path / "photo.PNG"
    write_png(img, size=(40, 30))
    case_dir = api.create_upload_case(cases_root, data_dir, "kolam", img, "image/png")
    assert case_dir.parent == data_dir / "cases"
    base, sha12 = case_dir.name.split("~")
    assert base == "kolam" and len(sha12) == 12
    manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["case_id"] == case_dir.name and manifest["transmission_mode"] == "goal-conditioned"
    assert set(manifest) <= set(json.loads((REAL_CASES / "manifest.schema.json").read_text())["properties"])
    reg = load_sources(case_dir)
    (src,) = reg.sources
    assert src.role == "target_image" and src.runtime_label == "UPLOAD" and src.creator == "uploader"
    assert src.license == config.UPLOAD_LICENSE and src.access_level == "approved_learners"
    assert src.path == f"source/upload.{sha12}.png" and (case_dir / src.path).exists()
    assert src.dimensions == [40, 30]
    # idempotent
    assert api.create_upload_case(cases_root, data_dir, "kolam", img, "image/png") == case_dir

    # derived case builds with the same (inherited) modality and upload consent
    ctx = make_ctx(case_dir)
    h = api.build_case(case_dir, ctx)
    assert h.package.package_id == f"kp.{case_dir.name}.1"
    assert h.package.skill_id == "skill.kolam"
    assert h.package.consent.consent_scope == "user upload" and h.runtime_label == "UPLOAD"
    assert fake_builder["calls"][-1]["source_id"] == src.source_id
    assert h.to_view()["sources"][0]["media_url"] == f"/api/media/{case_dir.name}/{src.source_id}"


def test_create_upload_case_audio(cases_root, data_dir, tmp_path):
    wav = tmp_path / "theka.wav"
    write_wav(wav, seconds=1.5)
    case_dir = api.create_upload_case(cases_root, data_dir, "tabla", wav, "audio/wav")
    (src,) = load_sources(case_dir).sources
    assert src.role == "expert_audio" and src.mime_type == "audio/wav"
    assert src.duration_sec == pytest.approx(1.5, abs=0.05)


@pytest.mark.parametrize(
    "base,mime",
    [("kolam", "video/mp4"), ("tabla", "image/png"), ("origami", "audio/wav"), ("kolam", "")],
)
def test_upload_mime_rejected(cases_root, data_dir, tmp_path, base, mime):
    img = tmp_path / "x.png"
    write_png(img)
    with pytest.raises(AnveshanFailure) as e:
        api.create_upload_case(cases_root, data_dir, base, img, mime)
    assert e.value.category == FailureCategory.INVALID_INPUT
    assert not (data_dir / "cases").exists()


def test_upload_rejects_showcase_size_and_garbage(cases_root, data_dir, tmp_path, monkeypatch):
    img = tmp_path / "x.png"
    write_png(img)
    with pytest.raises(AnveshanFailure) as e:
        api.create_upload_case(cases_root, data_dir, "micrometer", img, "image/png")
    assert e.value.category == FailureCategory.INVALID_INPUT
    monkeypatch.setenv("ANVESHAN_MAX_UPLOAD_MB", "0.00001")
    with pytest.raises(AnveshanFailure) as e:
        api.create_upload_case(cases_root, data_dir, "kolam", img, "image/png")
    assert e.value.category == FailureCategory.INVALID_INPUT and "limit" in e.value.message
    monkeypatch.delenv("ANVESHAN_MAX_UPLOAD_MB")
    junk = tmp_path / "junk.png"
    junk.write_bytes(b"not an image at all")
    with pytest.raises(AnveshanFailure) as e:
        api.create_upload_case(cases_root, data_dir, "kolam", junk, "image/png")
    assert e.value.category == FailureCategory.INVALID_INPUT
    assert not any((data_dir / "cases").iterdir())
