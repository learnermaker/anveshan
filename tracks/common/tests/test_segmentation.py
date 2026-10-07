"""Domain-agnostic video segmentation / alignment (tracks/common/segmentation.py)."""
import numpy as np
from PIL import Image

from tracks.common import segmentation as sg
from tracks.common.perception import Segment
from tracks.common.perceivers.video import _monotone_stages


def _states(lengths, dim=32, noise=0.05, seed=0):
    rng = np.random.default_rng(seed)
    protos = rng.normal(size=(len(lengths), dim))
    rows = [protos[k] + noise * rng.normal(size=dim) for k, n in enumerate(lengths) for _ in range(n)]
    return np.array(rows), protos


def test_segment_k_finds_true_boundaries():
    e, _ = _states([5, 7, 4, 6])
    segs = sg.segment_k(e, 4)
    assert [(s.start, s.end) for s in segs] == [(0, 4), (5, 11), (12, 15), (16, 21)]
    assert all(s.start <= s.keyframe <= s.end for s in segs)


def test_segment_k_oversegmentation_keeps_true_boundaries():
    e, _ = _states([6, 6, 6])
    cuts = {s.start for s in sg.segment_k(e, 6)}
    assert {0, 6, 12} <= cuts


def test_motion_frames_do_not_drive_keyframe():
    e, _ = _states([6])
    motion = [0.0, 0.001, 0.5, 0.002, 0.001, 0.0]   # calm is relative to this video's typical motion
    seg = sg.segment_k(e, 1, motion)[0]
    assert seg.keyframe != 2
    assert seg.calm_fraction == round(5 / 6, 4)


def test_layout_features_unit_and_shape():
    imgs = [Image.new("RGB", (64, 36), (i * 20, 0, 0)) for i in range(3)]
    emb = np.random.default_rng(1).normal(size=(3, 8))
    f = sg.layout_features(imgs, emb)
    assert f.shape == (3, 8 + sg.THUMB_SIZE[0] * sg.THUMB_SIZE[1])
    assert np.allclose(np.linalg.norm(f, axis=1), 1.0)


def test_monotone_align_skips_missing_and_never_goes_back():
    # 3 steps; attempt shows step 0, then step 2 (step 1 missing), then a flicker towards 0.
    sim = np.array([[2, -1, -1], [2, -1, -1], [-1, -1, 2], [-1, -1, 2], [1.5, -1, 0.5]], dtype=float)
    path = sg.monotone_align(sim)
    assert path[:4] == [0, 0, 2, 2]
    assert path[4] in (2, None)
    assert 1 not in path


def test_monotone_align_off_frames():
    sim = np.array([[1.0], [-2.0], [1.0]])
    assert sg.monotone_align(sim, off_score=0.0) == [0, None, 0]


def _seg(i):
    return Segment(segment_id=f"seg-{i:03d}", kind="time", start_sec=float(i), end_sec=float(i) + 0.5)


def test_monotone_stages_carries_first_name_and_ignores_backwards():
    segs = [_seg(i) for i in range(1, 5)]
    by_id = {
        "seg-001": {"stage": 0, "stage_name": "blank"},
        "seg-002": {"stage": 1, "stage_name": "walls"},
        "seg-003": {"stage": 0, "stage_name": "blank again"},   # goes backwards -> stays in stage 1
        "seg-004": {"stage": 1, "stage_name": "walls (other words)"},
    }
    out = _monotone_stages(segs, by_id)
    assert out == {"seg-001": "blank", "seg-002": "walls", "seg-003": "walls", "seg-004": "walls"}
