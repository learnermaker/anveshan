"""Attempt images in any PIL mode reach the judges; an unreadable attempt is never judged blind."""
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from tracks.common.media import to_rgb
from track_b.evaluators import universal as U
from track_b.trajectory import AttemptMedia


def test_to_rgb_composites_transparency_on_white():
    im = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    assert to_rgb(im).getpixel((0, 0)) == (255, 255, 255)
    assert to_rgb(Image.new("L", (2, 2), 7)).mode == "RGB"


class _Gateway:
    def __init__(self):
        self.parts = None

    def generate_json(self, *, parts=(), schema=None, **kw):
        self.parts = list(parts)
        data = schema.model_validate({"results": [{"check_id": "CHK-1", "status": "met", "finding": "ok"}]})
        return SimpleNamespace(data=data)


def _check():
    return SimpleNamespace(check_id="CHK-1", observable_indicator="red block bottom left",
                           metric_id="u.final_property.prop-01")


def _skill():
    return SimpleNamespace(steps=[], skill_title="Blocks")


def test_rgba_attempt_image_is_sent_to_judge(tmp_path):
    p = tmp_path / "a.png"
    Image.new("RGBA", (64, 64), (200, 30, 30, 255)).save(p)
    gw = _Gateway()
    att = AttemptMedia(kind="image", path=p, source_id="upload.x", sha256="0" * 64, mime_type="image/png")
    warnings = []
    out = U._call_judge_final(_skill(), att, None, [_check()], SimpleNamespace(gateway=gw, case_dir=None), warnings)
    assert out["CHK-1"]["status"] == "met"
    assert any(getattr(x, "label", "") == "Attempt image" for x in gw.parts)
    assert not any("Could not load" in w for w in warnings)


def test_unreadable_attempt_is_not_judged(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(b"not an image")
    gw = _Gateway()
    att = AttemptMedia(kind="image", path=p, source_id="upload.x", sha256="0" * 64, mime_type="image/png")
    out = U._call_judge_final(_skill(), att, None, [_check()], SimpleNamespace(gateway=gw, case_dir=None), [])
    assert out["CHK-1"]["status"] == "cannot_tell"
    assert gw.parts is None, "the judge must not be called without the attempt's image"
