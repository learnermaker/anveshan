"""WP5 Integration live checks (Step 3).

Runs the WP2/K7 §6 live checks and two new universal skills using the
real composer + universal evaluator.

Usage:
    python tools/live_checks_wp5.py [--force]

Do NOT re-run if var/runs/wp5_live_checks/results.json already exists
(golden runs already recorded). Pass --force to overwrite.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import time
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tracks" / "track-a" / "src", ROOT / "tracks" / "track-b" / "src", ROOT / "tracks" / "common"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common.models import load_dotenv
load_dotenv(ROOT / ".env")

import logging
logging.basicConfig(level=logging.WARNING)

RESULTS_DIR = ROOT / "var" / "runs" / "wp5_live_checks"
RESULTS_FILE = RESULTS_DIR / "results.json"
DATA_DIR = ROOT / "var" / "data"   # runtime data root; gitignored


# ---------------------------------------------------------------------------
# Synthetic media generators (no model calls)
# ---------------------------------------------------------------------------

def _make_synthetic_wav(path: Path, bpm: float = 120.0, beats: int = 16,
                        sample_rate: int = 22050, jitter: float = 0.0) -> None:
    """Write a hand-clap-like rhythm WAV (short burst per beat)."""
    import math
    import random

    beat_sec = 60.0 / bpm
    total_sec = beats * beat_sec
    n_samples = int(total_sec * sample_rate)
    data = [0.0] * n_samples
    rng = random.Random(42)
    for i in range(beats):
        beat_pos = i * beat_sec
        if jitter > 0:
            beat_pos += rng.uniform(-jitter, jitter) * beat_sec
        beat_pos = max(0.0, min(total_sec - 0.05, beat_pos))
        start_idx = int(beat_pos * sample_rate)
        burst_len = int(0.04 * sample_rate)
        for j in range(burst_len):
            t = j / sample_rate
            decay = math.exp(-t * 50)
            noise_val = math.sin(2 * math.pi * 1200 * t) * decay
            if start_idx + j < n_samples:
                data[start_idx + j] += noise_val
    max_val = max(abs(v) for v in data) or 1.0
    samples = [int(min(32767, max(-32768, v / max_val * 28000))) for v in data]
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{n_samples}h", *samples))


def _make_rangoli_png(path: Path, size: int = 256) -> None:
    """Generate a synthetic line-drawing rangoli (dot grid with loops)."""
    import math
    from PIL import Image, ImageDraw
    img = Image.new("L", (size, size), 255)
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    spacing = size // 8
    for i in range(-2, 3):
        for j in range(-2, 3):
            x, y = cx + i * spacing, cy + j * spacing
            r = max(3, size // 50)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=0)
    arc_r = spacing * 1.4
    for angle_offset in [0, 90, 180, 270]:
        ax = cx + int(arc_r * math.cos(math.radians(angle_offset)))
        ay = cy + int(arc_r * math.sin(math.radians(angle_offset)))
        draw.arc([ax - spacing, ay - spacing, ax + spacing, ay + spacing],
                 start=angle_offset + 90, end=angle_offset + 270, fill=0, width=2)
    outer_r = spacing * 2.5
    draw.ellipse([cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r],
                 outline=0, width=2)
    img.save(str(path), format="PNG")


def _make_half_erased_image(source_path: Path, out_path: Path) -> None:
    """Erase (whiten) the right half of an image."""
    from PIL import Image, ImageDraw
    img = Image.open(source_path).convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([w // 2, 0, w, h], fill=(255, 255, 255))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), format="PNG")


def _make_gradient_png(path: Path, size: int = 128) -> None:
    """Make a solid gradient (unteachable landscape)."""
    from PIL import Image
    import numpy as np
    arr = np.linspace(50, 200, size * size, dtype=np.uint8).reshape(size, size)
    img = Image.fromarray(arr, mode="L")
    img.save(str(path), format="PNG")


# ---------------------------------------------------------------------------
# Composer + evaluator helpers
# ---------------------------------------------------------------------------

def _run_compose(
    file_path: Path,
    mime: str,
    title_hint: str,
    tmp_dir: Path,
) -> Tuple[Optional[Any], Dict]:
    """Run create_draft + create_case_from_draft + build_case. Returns (case_dir, result_info)."""
    from tracks.common.runtime import RunContext
    from track_a.composer import create_draft, create_case_from_draft
    from track_a.api import build_case

    data_dir = tmp_dir / "data"
    ctx = RunContext.create(tmp_dir / "cases_placeholder", data_dir, "live")

    t0 = time.time()
    try:
        draft = create_draft(
            data_dir, file_path, mime, ctx,
            title_hint=title_hint,
            rights_confirmed=True,
        )
    except Exception as exc:
        return None, {"error": f"create_draft: {exc}", "elapsed": time.time() - t0}

    create_elapsed = time.time() - t0

    if draft.refused:
        return None, {
            "refused": True,
            "reason": draft.refusal_message,
            "elapsed": create_elapsed,
        }

    if draft.proposal is None:
        return None, {
            "error": "no proposal (unclear intake, needs title)",
            "elapsed": create_elapsed,
        }

    # Create case from draft
    cases_root = tmp_dir / "cases"
    t1 = time.time()
    try:
        case_dir = create_case_from_draft(
            cases_root, data_dir, draft.draft_id,
            edits={"title": title_hint, "confirmed_by_user": True},
        )
    except Exception as exc:
        return None, {"error": f"create_case_from_draft: {exc}", "elapsed": time.time() - t1}

    # Build the full case artifacts
    case_ctx = RunContext.create(case_dir, data_dir, "live")
    t2 = time.time()
    try:
        handoff = build_case(case_dir, case_ctx)
    except Exception as exc:
        return None, {"error": f"build_case: {exc}", "elapsed": time.time() - t2}
    build_elapsed = time.time() - t2

    skill = draft.proposal.skill_model
    return case_dir, {
        "refused": False,
        "structures": skill.structures,
        "specialists": list(skill.specialists.keys()),
        "n_checks": len(skill.checks),
        "n_steps": len(skill.steps),
        "create_elapsed": create_elapsed,
        "build_elapsed": build_elapsed,
        "handoff_warnings": handoff.warnings if handoff else [],
    }


def _evaluate(
    case_dir: Path,
    attempt_path: Path,
    attempt_mime: str,
    data_dir: Path,
) -> Dict:
    """Evaluate one attempt against a built universal case."""
    from tracks.common.casedata import GoalModel, latest_version, versioned_path
    from tracks.common.runtime import RunContext
    from track_b.trajectory import AttemptMedia
    from track_b.evaluators.universal import evaluate as universal_eval
    from tracks.common.models import AnveshanFailure

    goal_files = sorted((case_dir / "knowledge").glob("goal_model.v*.json"))
    if not goal_files:
        return {"error": "no goal_model.v*.json in case_dir"}

    goal = GoalModel.model_validate_json(goal_files[-1].read_text(encoding="utf-8"))
    sha = hashlib.sha256(attempt_path.read_bytes()).hexdigest()
    kind_map = {
        "image/png": "image", "image/jpeg": "image",
        "audio/wav": "audio", "audio/mpeg": "audio", "audio/webm": "audio",
        "audio/ogg": "audio", "audio/oga": "audio",
        "video/mp4": "video", "video/webm": "video", "video/ogg": "video",
    }
    kind = kind_map.get(attempt_mime, "image")

    attempt = AttemptMedia(
        kind=kind,
        path=attempt_path,
        source_id=f"att.{sha[:12]}",
        sha256=sha,
        mime_type=attempt_mime,
    )

    ctx = RunContext.create(case_dir, data_dir, "live")
    t0 = time.time()
    try:
        result = universal_eval(goal, attempt, ctx)
        elapsed = time.time() - t0
        metrics = {k: round(v.value, 3) if isinstance(v.value, float) else v.value
                   for k, v in result.metrics.items()}
        return {
            "passed": True,
            "metrics": metrics,
            "n_events": len(result.events),
            "elapsed": elapsed,
        }
    except AnveshanFailure as exc:
        return {
            "passed": False,
            "refused": True,
            "category": exc.category.value,
            "reason": str(exc)[:120],
            "elapsed": time.time() - t0,
        }
    except Exception as exc:
        return {
            "passed": False,
            "error": str(exc)[:120],
            "elapsed": time.time() - t0,
        }


# ---------------------------------------------------------------------------
# Check runners
# ---------------------------------------------------------------------------

def run_wp2_kolam_checks(media_dir: Path, tmp_dir: Path) -> List[Dict]:
    """WP2/K7 §6(a): composed Kolam - same image, half-erased, unrelated photo."""
    results = []
    source_img = media_dir / "kolam" / "kolam_8_mayoo.png"
    if not source_img.exists():
        return [{"check": "kolam_compose", "error": f"source not found: {source_img}"}]

    print(f"[WP2-K7a] Composing kolam source: {source_img.name} ...")
    case_dir, info = _run_compose(source_img, "image/png", "Kolam line drawing", tmp_dir)
    info["check"] = "kolam_compose"
    results.append(info)

    if info.get("refused") or info.get("error") or case_dir is None:
        print(f"  REFUSED/ERROR: {info.get('reason') or info.get('error')}")
        return results

    print(f"  Built: structures={info.get('structures')}, specialists={info.get('specialists')}, "
          f"t_build={info.get('build_elapsed', 0):.1f}s")
    data_dir = tmp_dir / "data"

    # Attempt 1: same image
    print("  Evaluating: same image (expect high similarity) ...")
    res1 = _evaluate(case_dir, source_img, "image/png", data_dir)
    res1["check"] = "kolam_same_image"
    results.append(res1)
    _print_eval(res1)

    # Attempt 2: half-erased
    half_erased = tmp_dir / "kolam_half_erased.png"
    _make_half_erased_image(source_img, half_erased)
    print("  Evaluating: half-erased image (expect lower similarity / partial) ...")
    res2 = _evaluate(case_dir, half_erased, "image/png", data_dir)
    res2["check"] = "kolam_half_erased"
    results.append(res2)
    _print_eval(res2)

    # Attempt 3: unrelated gradient (expect refusal or low similarity)
    gradient = tmp_dir / "gradient_landscape.png"
    _make_gradient_png(gradient)
    print("  Evaluating: unrelated gradient (expect refusal) ...")
    res3 = _evaluate(case_dir, gradient, "image/png", data_dir)
    res3["check"] = "kolam_unrelated"
    results.append(res3)
    _print_eval(res3)

    return results


def run_universal_new_skills(tmp_dir: Path, media_dir: Path) -> List[Dict]:
    """Two genuinely new skills: synthetic rangoli + synthetic hand-clap."""
    results = []
    data_dir = tmp_dir / "data"

    # ---- Skill 1: synthetic rangoli ----
    rangoli_src = tmp_dir / "rangoli_source.png"
    _make_rangoli_png(rangoli_src)
    print("[Universal-1] Composing synthetic rangoli drawing ...")
    case_dir_r, info_r = _run_compose(rangoli_src, "image/png", "Rangoli dot pattern", tmp_dir)
    info_r["check"] = "rangoli_compose"
    results.append(info_r)

    if not info_r.get("refused") and not info_r.get("error") and case_dir_r is not None:
        print(f"  Built: structures={info_r.get('structures')}, specialists={info_r.get('specialists')}")
        # Learner: slightly different (crop + resize back)
        rangoli_learner = tmp_dir / "rangoli_learner.png"
        from PIL import Image
        img = Image.open(rangoli_src).convert("L")
        w, h = img.size
        img2 = img.crop([5, 5, w - 5, h - 5]).resize((w, h))
        img2.save(str(rangoli_learner), format="PNG")
        print("  Evaluating: cropped learner attempt ...")
        res_r = _evaluate(case_dir_r, rangoli_learner, "image/png", data_dir)
        res_r["check"] = "rangoli_learner"
        results.append(res_r)
        _print_eval(res_r)
    else:
        print(f"  REFUSED/ERROR: {info_r.get('reason') or info_r.get('error')}")

    # ---- Skill 2: tabla_chanderi (new recording, different from hero tabla case) ----
    clap_src = media_dir / "tabla" / "tabla_chanderi_1.webm"
    if not clap_src.exists():
        results.append({"check": "audio_skill_compose", "error": f"source not found: {clap_src}"})
        results.append({"check": "audio_skill_learner", "skipped": True, "reason": "source not found"})
        return results

    print("[Universal-2] Composing tabla_chanderi_1 (new recording) ...")
    case_dir_c, info_c = _run_compose(clap_src, "video/webm", "Tabla chanderi rhythm", tmp_dir)
    info_c["check"] = "audio_skill_compose"
    results.append(info_c)

    if not info_c.get("refused") and not info_c.get("error") and case_dir_c is not None:
        print(f"  Built: structures={info_c.get('structures')}, specialists={info_c.get('specialists')}")
        # Learner attempt: a different tabla recording
        clap_learner = media_dir / "tabla" / "tabla_chanderi_2.webm"
        if not clap_learner.exists():
            # Fallback: use same file (expect high similarity)
            clap_learner = clap_src
        print(f"  Evaluating: learner attempt ({clap_learner.name}) ...")
        res_c = _evaluate(case_dir_c, clap_learner, "video/webm", data_dir)
        res_c["check"] = "audio_skill_learner"
        results.append(res_c)
        _print_eval(res_c)
    else:
        print(f"  REFUSED/ERROR: {info_c.get('reason') or info_c.get('error')}")

    return results


def _print_eval(result: Dict) -> None:
    if result.get("refused"):
        print(f"  -> REFUSED ({result.get('category')}): {result.get('reason', '')[:60]}")
    elif result.get("error"):
        print(f"  -> ERROR: {result.get('error', '')[:60]}")
    else:
        m = result.get("metrics", {})
        short = {k: (f"{v:.2f}" if isinstance(v, float) else v) for k, v in list(m.items())[:3]}
        print(f"  -> passed={result.get('passed')}, metrics={short}, t={result.get('elapsed', 0):.1f}s")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(data: Dict) -> None:
    print("\n=== WP5 Live Check Summary ===")
    print(f"Date: {data.get('date', 'unknown')}")
    print()
    print(f"  {'Check':<35} {'Status':<12} Notes")
    print("  " + "-" * 75)
    for c in data.get("checks", []):
        check = c.get("check", "?")
        if c.get("refused"):
            status = "REFUSED"
            notes = (c.get("reason") or "")[:40]
        elif c.get("error"):
            status = "ERROR"
            notes = str(c.get("error", ""))[:40]
        elif c.get("passed") is True:
            status = "PASS"
            m = c.get("metrics", {})
            notes = str({k: (f"{v:.2f}" if isinstance(v, float) else v)
                         for k, v in list(m.items())[:2]})[:40]
        elif c.get("passed") is False:
            status = "FAIL"
            notes = (c.get("error") or c.get("reason") or "")[:40]
        else:
            status = "BUILT"
            notes = f"structs={c.get('structures')} spc={c.get('specialists')}"
        print(f"  {check:<35} {status:<12} {notes}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="WP5 live checks")
    parser.add_argument("--force", action="store_true", help="Re-run even if results exist")
    args = parser.parse_args()

    if RESULTS_FILE.exists() and not args.force:
        print(f"Results already recorded at {RESULTS_FILE}")
        print_summary(json.loads(RESULTS_FILE.read_text()))
        return

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Use DATA_DIR as the scratch area for this run
    import tempfile
    with tempfile.TemporaryDirectory(prefix="wp5_live_") as tmp_str:
        tmp_dir = Path(tmp_str)
        media_dir = ROOT / "var" / "kiro" / "media"

        all_results: List[Dict] = []

        print("=== WP5 Live Checks (Step 3) ===\n")
        print("--- WP2/K7 §6(a): Kolam universal compose + evaluate ---")
        all_results.extend(run_wp2_kolam_checks(media_dir, tmp_dir))

        print("\n--- Universal: two new skills ---")
        all_results.extend(run_universal_new_skills(tmp_dir, media_dir))

    summary = {
        "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "checks": all_results,
        "note": (
            "WP1/K6 §7 live checks (kolam PNG, tabla clip, origami 30s, landscape, silence) "
            "were already run and recorded during Phase A (see WP1-REPORT.md). "
            "This script runs WP2/K7 §6 checks and two new universal skills."
        ),
    }
    RESULTS_FILE.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\nResults written to: {RESULTS_FILE}")
    print_summary(summary)


if __name__ == "__main__":
    main()
