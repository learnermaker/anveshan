"""Kolam geometry pipeline tests: small synthetic Pillow images, no live APIs.

Tests: dot detection, K (closed-loop count), rotation order, split_stages, and
register_similarity recovering a known rotation and scale.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from tracks.common import kolam_geometry as kg


# ---------------------------------------------------------------------------
# Synthetic image helpers
# ---------------------------------------------------------------------------

def _square_loop_image(size=(300, 300), margin=75, dot_r=7.0, line_w=3):
    """A closed square loop with 4 corner dots (dark ink on white background)."""
    cx, cy = size[0] // 2, size[1] // 2
    corners = np.array([
        [cx - margin, cy - margin],
        [cx + margin, cy - margin],
        [cx + margin, cy + margin],
        [cx - margin, cy + margin],
    ], dtype=np.float64)
    dots = [kg.Dot(float(x), float(y), dot_r) for x, y in corners]
    img = kg.render(size, [corners], width=line_w, dots=dots, closed=[True],
                    ink_value=0, bg_value=255)
    return img, dots, corners


def _two_circles_image(size=(300, 300), r=40.0, line_w=3):
    """Two separate closed circles, no dots (dark ink on white background)."""
    cy = size[1] // 2
    left_cx = size[0] // 4
    right_cx = 3 * size[0] // 4
    n = 48
    angs = np.linspace(0, 2 * math.pi, n, endpoint=False)
    left = np.stack([left_cx + r * np.cos(angs), cy + r * np.sin(angs)], axis=1)
    right = np.stack([right_cx + r * np.cos(angs), cy + r * np.sin(angs)], axis=1)
    img = kg.render(size, [left, right], width=line_w, dots=[], closed=[True, True],
                    ink_value=0, bg_value=255)
    return img


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_dot_detection_and_single_closed_loop():
    """Square loop + 4 corner dots → detect >= 3 dots, K=1 closed curve."""
    img, dots, _ = _square_loop_image()
    an = kg.analyze_image(img)
    dec = kg.decompose_curves(an)

    # At least 3 of the 4 corner dots should be detected (corner placement is
    # unambiguous with dot_r=7 and line_w=3: DOT_BIG_RATIO check passes).
    assert len(an.dots) >= 3, f"expected >= 3 dots, got {len(an.dots)}"

    # One closed loop
    assert len(dec.curves) == 1, f"expected K=1, got {len(dec.curves)}"
    assert dec.closed[0], "expected the single curve to be closed"


def test_two_independent_loops_k_equals_2():
    """Two well-separated circles → K=2 closed curves with no dots."""
    img = _two_circles_image()
    an = kg.analyze_image(img)
    dec = kg.decompose_curves(an)

    # Both circles should decompose as separate closed curves.
    assert len(dec.curves) == 2, f"expected K=2, got {len(dec.curves)}"
    assert all(dec.closed), f"expected both curves closed, got {dec.closed}"

    # Circles have no dots; any 'isolated' dots should be absent.
    assert len(an.dots) == 0, f"expected 0 dots, got {len(an.dots)}"


def test_fourfold_rotation_order():
    """Square loop with 4 corner dots → estimate_symmetry returns rotation_order=4."""
    img, _, _ = _square_loop_image()
    an = kg.analyze_image(img)
    sym = kg.estimate_symmetry(an)

    assert sym["rotation_order"] == 4, (
        f"expected rotation_order=4, got {sym['rotation_order']}; "
        f"scores={sym['scores']['rotation']}"
    )


def test_split_stages_respects_rotation_order():
    """split_stages on a closed circle with rotation_order=4 → exactly 4 equal stages."""
    n_pts = 400
    angs = np.linspace(0, 2 * math.pi, n_pts, endpoint=False)
    r = 100.0
    cx, cy = 150.0, 150.0
    pts = np.stack([cx + r * np.cos(angs), cy + r * np.sin(angs)], axis=1)

    stages = kg.split_stages(pts, closed=True, rotation_order=4, centre=(cx, cy), min_stages=3)

    assert len(stages) == 4, f"expected 4 stages, got {len(stages)}: {stages}"
    # Each stage should cover roughly 1/4 of the curve
    for start, end in stages:
        seg_len = end - start
        assert 0.20 * n_pts <= seg_len <= 0.30 * n_pts, (
            f"stage [{start}:{end}] has {seg_len}/{n_pts} points; expected ~{n_pts//4}"
        )


def test_split_stages_fallback_when_no_rotation():
    """split_stages with rotation_order=1 → falls back to min_stages equal-arc sections."""
    n_pts = 200
    angs = np.linspace(0, 2 * math.pi, n_pts, endpoint=False)
    pts = np.stack([np.cos(angs), np.sin(angs)], axis=1) * 50.0 + 100.0
    min_s = 3

    stages = kg.split_stages(pts, closed=True, rotation_order=1, centre=(100.0, 100.0), min_stages=min_s)

    assert len(stages) == min_s, f"expected {min_s} stages, got {len(stages)}"


def test_register_similarity_recovers_known_rotation_and_scale():
    """register_similarity recovers a synthetic scale and rotation from analytic geometry."""
    # Diamond goal: 4 dots on the compass directions, a closed diamond loop through them.
    # Use r=100 so corners are well within the 300×300 canvas.
    cx, cy = 150.0, 150.0
    r = 100.0
    dot_r = 10.0
    goal_dots_arr = np.array([
        [cx + r, cy],
        [cx, cy + r],
        [cx - r, cy],
        [cx, cy - r],
    ])
    goal_dots = [kg.Dot(float(x), float(y), dot_r) for x, y in goal_dots_arr]
    goal_loop = kg.resample_polyline(goal_dots_arr, 1.0, closed=True)

    # Learner: scale by 0.8, rotate by 20° around the centre.
    known_scale = 0.8
    known_theta_rad = math.radians(20.0)
    M = np.array([
        [math.cos(known_theta_rad) * known_scale, -math.sin(known_theta_rad) * known_scale],
        [math.sin(known_theta_rad) * known_scale,  math.cos(known_theta_rad) * known_scale],
    ])
    c = np.array([cx, cy])
    learner_dots_arr = (goal_dots_arr - c) @ M.T + c
    learner_loop = (goal_loop - c) @ M.T + c
    learner_dots = [kg.Dot(float(x), float(y), dot_r * known_scale) for x, y in learner_dots_arr]

    tau = max(kg.TAU_MIN_PX, kg.TAU_W_FACTOR * 3.0)
    sim = kg.register_similarity(
        src_pts=learner_loop,
        src_dots=learner_dots,
        dst_pts=goal_loop,
        dst_dots=goal_dots,
        dst_shape=(300, 300),
        tol=tau,
    )

    # The similarity maps learner → goal.
    # Expected scale = 1/0.8 = 1.25 (derived from dot RMS ratio; very accurate).
    expected_scale = 1.0 / known_scale
    assert abs(sim.scale - expected_scale) < 0.12, (
        f"scale {sim.scale:.3f} vs expected {expected_scale:.3f}"
    )

    # Expected rotation = -20° ≡ 340°, with 4-fold ambiguity: {340, 70, 160, 250}.
    # Tolerance 12° accounts for flat-top scoring when straight sides are inside the tau band.
    expected_thetas = [(340 + k * 90) % 360 for k in range(4)]
    min_err = min(abs(((sim.theta_deg - et) + 180) % 360 - 180) for et in expected_thetas)
    assert min_err < 12.0, (
        f"theta_deg {sim.theta_deg:.1f}° not near any of {expected_thetas} "
        f"(min error {min_err:.1f}°)"
    )

    assert sim.score > 0.5, f"registration score {sim.score:.3f} too low"
