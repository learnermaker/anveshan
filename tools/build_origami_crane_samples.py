"""Build and evaluate origami-crane sample attempts.

Creates three video samples in tracks/cases/origami-crane/samples/ and runs Track B
evaluation in live mode to calibrate the expected outcomes.

Usage (from worktree root):
    python tools/build_origami_crane_samples.py [--live] [--data-dir var/k9-compose]

Live-call budget: about 3-9 calls per sample = ~9-27 calls total.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
for p in [
    str(ROOT),
    str(ROOT / "tracks" / "track-a" / "src"),
    str(ROOT / "tracks" / "track-b" / "src"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from tracks.common.models import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

CASE_DIR = ROOT / "tracks" / "cases" / "origami-crane"
ORIGAMI_CACHE = ROOT / "tracks" / "cases" / "origami" / "media" / "cache"
DEMO_VIDEO = ORIGAMI_CACHE / "src.origami.demo.v1.ogv"
LEARNER_VIDEO = ORIGAMI_CACHE / "src.origami.learner_crane.v1.ogv"
SWAPPED_ORDER_MP4 = ROOT / "var" / "eval" / "origami" / "swapped_order.mp4"

MAX_COMMITTED_BYTES = 2 * 1024 * 1024  # 2 MB
TARGET_WIDTH = 320
TARGET_FPS = 10
MAX_DURATION_S = 25.0

SAMPLES = [
    {
        "sample_id": "good",
        "label": "A careful attempt",
        "quality": "good",
        "attempt_kind": "video",
        "file": "good.mp4",
        "description": (
            "A re-encoding of Crane.ogv (CC BY 3.0, Tavin, via Wikimedia Commons). "
            "Nearly the same folding as the demo. Expect most checks to be met."
        ),
        "synthetic": False,
        "credit": "Crane.ogv by Tavin, CC BY 3.0, via Wikimedia Commons",
        "licence": "CC BY 3.0",
    },
    {
        "sample_id": "flawed",
        "label": "An attempt with steps out of order",
        "quality": "flawed",
        "attempt_kind": "video",
        "file": "flawed.mp4",
        "description": (
            "Derived from OrigamiCrane.ogv (CC BY 3.0, Tavin) by reordering segments (1, 3, 2, 4). "
            "See where the feedback says it first went off track."
        ),
        "synthetic": False,
        "credit": "Derived from OrigamiCrane.ogv by Tavin, CC BY 3.0, via Wikimedia Commons",
        "licence": "CC BY 3.0",
    },
    {
        "sample_id": "unrelated",
        "label": "Something unrelated",
        "quality": "unrelated",
        "attempt_kind": "video",
        "file": "unrelated.mp4",
        "description": (
            "Synthetic video: slowly moving coloured rectangles (CC0). "
            "Anveshan should say it does not match instead of scoring it."
        ),
        "synthetic": True,
        "credit": "Synthetic. Generated for the demo.",
        "licence": "CC0-1.0",
    },
]


# ---------------------------------------------------------------------------
# Video encoding helpers
# ---------------------------------------------------------------------------


def _resize_width(orig_w: int, orig_h: int, target_w: int) -> tuple[int, int]:
    """Compute target dimensions maintaining aspect ratio, ensuring even pixels."""
    scale = target_w / orig_w
    new_h = int(orig_h * scale)
    # Ensure both dimensions are even (required by x264)
    new_h = new_h if new_h % 2 == 0 else new_h + 1
    new_w = target_w if target_w % 2 == 0 else target_w + 1
    return new_w, new_h


def encode_video_segment(
    src: Path,
    dst: Path,
    start_sec: float = 0.0,
    duration_sec: Optional[float] = None,
    target_w: int = TARGET_WIDTH,
    fps: int = TARGET_FPS,
    codec: str = "libx264",
) -> None:
    """Re-encode a segment of src to dst at target_w wide and fps."""
    import av
    from fractions import Fraction

    dst.parent.mkdir(parents=True, exist_ok=True)

    with av.open(str(src)) as in_container:
        in_stream = in_container.streams.video[0]
        orig_w = in_stream.width
        orig_h = in_stream.height
        new_w, new_h = _resize_width(orig_w, orig_h, target_w)

        with av.open(str(dst), "w", format="mp4") as out_container:
            out_stream = out_container.add_stream(codec, rate=fps)
            out_stream.width = new_w
            out_stream.height = new_h
            out_stream.pix_fmt = "yuv420p"
            out_stream.options = {
                "preset": "fast",
                "crf": "28",
                "profile": "baseline",
                "level": "3.0",
            }

            end_sec = (start_sec + duration_sec) if duration_sec else None
            current_pts = 0

            for packet in in_container.demux(in_stream):
                if packet.dts is None:
                    continue
                done = False
                for frame in packet.decode():
                    t = float(frame.pts * in_stream.time_base) if frame.pts is not None else 0.0
                    if t < start_sec:
                        continue
                    if end_sec is not None and t >= end_sec:
                        done = True
                        break

                    # Resize using PIL
                    img = frame.to_image().resize((new_w, new_h))
                    new_frame = av.VideoFrame.from_image(img)
                    new_frame.pts = current_pts
                    current_pts += 1
                    for out_packet in out_stream.encode(new_frame):
                        out_container.mux(out_packet)

                if done:
                    break

            # Flush encoder
            for out_packet in out_stream.encode(None):
                out_container.mux(out_packet)

    if dst.exists() and dst.stat().st_size > MAX_COMMITTED_BYTES:
        print(f"  WARNING: {dst.name} is {dst.stat().st_size // 1024} KB (>2 MB limit)")


def get_video_duration(path: Path) -> float:
    """Get video duration in seconds."""
    import av
    with av.open(str(path)) as c:
        return float(c.duration / av.time_base) if c.duration else 0.0


def build_swapped_order_sample(src: Path, dst: Path, clip_sec: float = 5.0) -> None:
    """Build the flawed sample: short clips from quarters 1,3,2,4 of the source.

    Each clip is clip_sec seconds from the start of its quarter, concatenated
    in the order 1, 3, 2, 4 to show obvious order violations.
    Decodes in one pass (no seeking) for OGV compatibility.
    """
    import av
    from PIL import Image

    dur = get_video_duration(src)
    q = dur / 4  # quarter duration

    # Take clip_sec seconds from the start of each quarter
    quarter_starts = [0.0, q, 2 * q, 3 * q]
    # Reorder: 1, 3, 2, 4 -> indices 0, 2, 1, 3
    reordered_starts = [quarter_starts[0], quarter_starts[2], quarter_starts[1], quarter_starts[3]]

    clip_ranges = [(start, start + clip_sec) for start in reordered_starts]
    print(f"  Swapped order clip ranges: {[(round(s,1), round(e,1)) for s, e in clip_ranges]}")
    print(f"  Total duration: {len(clip_ranges) * clip_sec:.1f}s")

    # Collect all needed time ranges, sorted by start time for single-pass decode
    needed_times = set()
    for start, end in clip_ranges:
        needed_times.add((start, end))

    # Decode in a single pass, collecting frames for each needed time range
    # {(start, end): [(t, PIL.Image), ...]}
    collected: dict[tuple, list] = {r: [] for r in clip_ranges}

    with av.open(str(src)) as in_container:
        in_stream = in_container.streams.video[0]
        in_stream.thread_type = "AUTO"

        # Determine first needed timestamp
        all_starts = sorted(s for s, _ in needed_times)
        all_ends = sorted(e for _, e in needed_times)

        for packet in in_container.demux(in_stream):
            if packet.dts is None:
                continue
            for frame in packet.decode():
                t = float(frame.pts * in_stream.time_base) if frame.pts is not None else 0.0

                # Check if this frame belongs to any needed range
                for clip_start, clip_end in clip_ranges:
                    if clip_start <= t < clip_end:
                        img = frame.to_image()
                        collected[(clip_start, clip_end)].append((t, img))

                # Stop once we've passed all needed ranges
                if t > max(all_ends):
                    break

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Now encode in the reordered order
    orig_w = orig_h = None
    for frames_list in collected.values():
        if frames_list:
            _, img = frames_list[0]
            orig_w, orig_h = img.size
            break

    if not orig_w:
        raise RuntimeError("No frames collected for swapped order sample")

    new_w, new_h = _resize_width(orig_w, orig_h, TARGET_WIDTH)

    with av.open(str(dst), "w", format="mp4") as out_container:
        out_stream = out_container.add_stream("libx264", rate=TARGET_FPS)
        out_stream.width = new_w
        out_stream.height = new_h
        out_stream.pix_fmt = "yuv420p"
        out_stream.options = {
            "preset": "fast",
            "crf": "28",
            "profile": "baseline",
            "level": "3.0",
        }

        current_pts = 0
        # Sub-sample to TARGET_FPS
        for clip_start, clip_end in clip_ranges:
            frames = collected[(clip_start, clip_end)]
            # Uniformly sample TARGET_FPS frames per second
            n_output = max(1, int(clip_sec * TARGET_FPS))
            if len(frames) > n_output:
                step = len(frames) / n_output
                frames = [frames[int(i * step)] for i in range(n_output)]

            for _, img in frames:
                img_resized = img.resize((new_w, new_h))
                new_frame = av.VideoFrame.from_image(img_resized)
                new_frame.pts = current_pts
                current_pts += 1
                for out_packet in out_stream.encode(new_frame):
                    out_container.mux(out_packet)

        for out_packet in out_stream.encode(None):
            out_container.mux(out_packet)


def build_unrelated_sample(dst: Path) -> None:
    """Build synthetic 8s 320×240 video of slowly moving colored rectangles."""
    import av
    import numpy as np
    from PIL import Image

    dst.parent.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    width, height = 320, 240
    fps = TARGET_FPS
    duration_frames = fps * 8  # 8 seconds

    # Generate 3-5 rectangles with slow random motion
    n_rects = 4
    colors = [(255, 100, 50), (50, 200, 100), (100, 80, 255), (220, 200, 50)]
    rect_w, rect_h = 80, 60
    positions = [(rng.integers(0, width - rect_w), rng.integers(0, height - rect_h)) for _ in range(n_rects)]
    velocities = [
        (rng.integers(-1, 2, dtype=int) * 1, rng.integers(-1, 2, dtype=int) * 1)
        for _ in range(n_rects)
    ]
    # Ensure some velocity
    velocities = [(vx if vx != 0 else 1, vy if vy != 0 else 1) for vx, vy in velocities]

    with av.open(str(dst), "w", format="mp4") as out_container:
        out_stream = out_container.add_stream("libx264", rate=fps)
        out_stream.width = width
        out_stream.height = height
        out_stream.pix_fmt = "yuv420p"
        out_stream.options = {
            "preset": "fast",
            "crf": "28",
            "profile": "baseline",
            "level": "3.0",
        }

        for frame_idx in range(duration_frames):
            # Light grey background
            img = Image.new("RGB", (width, height), color=(200, 200, 200))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)

            # Draw rectangles, updating positions
            for i in range(n_rects):
                x, y = positions[i]
                vx, vy = velocities[i]
                draw.rectangle([x, y, x + rect_w, y + rect_h], fill=colors[i])

                # Bounce off walls
                nx, ny = x + vx, y + vy
                if nx < 0 or nx + rect_w > width:
                    vx = -vx
                    nx = max(0, min(nx, width - rect_w))
                if ny < 0 or ny + rect_h > height:
                    vy = -vy
                    ny = max(0, min(ny, height - rect_h))
                positions[i] = (nx, ny)
                velocities[i] = (vx, vy)

            # Convert to PyAV frame
            frame_arr = np.array(img)
            av_frame = av.VideoFrame.from_ndarray(frame_arr, format="rgb24")
            av_frame.pts = frame_idx

            for packet in out_stream.encode(av_frame):
                out_container.mux(packet)

        for packet in out_stream.encode(None):
            out_container.mux(packet)


# ---------------------------------------------------------------------------
# Track B evaluation
# ---------------------------------------------------------------------------


def run_track_b_eval(sample_file: Path, sample_id: str, data_dir: Path) -> dict:
    """Evaluate a sample against the origami-crane case in live mode.

    Returns a result dict with passed, run_keys, and evaluation details.
    """
    from tracks.common.models import ModelGateway, RunStore
    from tracks.common.runtime import RunContext
    from track_b import api as tb_api
    from track_b.trajectory import AttemptMedia

    runs_dir = data_dir / "runs" / "origami-crane"
    store = RunStore([
        runs_dir,
        CASE_DIR / "runs" / "golden",
    ])
    gw = ModelGateway(mode="live", store=store)
    ctx = RunContext(mode="live", gateway=gw, case_dir=CASE_DIR, data_dir=data_dir)

    session = tb_api.start_session(CASE_DIR, f"K9-P5 sample {sample_id}", data_dir)

    # Build media (kind=video for all origami-crane samples)
    import hashlib

    with open(sample_file, "rb") as f:
        sha = hashlib.sha256(f.read()).hexdigest()

    media = AttemptMedia(
        kind="video",
        path=sample_file,
        source_id=f"sample.{sample_id}.{sha[:12]}",
        sha256=sha,
        mime_type="video/mp4",
    )

    runs_before = _count_runs(runs_dir)
    try:
        result = tb_api.submit_attempt(session, media, ctx)
    except Exception as exc:
        cat = getattr(getattr(exc, "category", None), "value", None)
        if cat == "INVALID_INPUT":
            # Unrelated video correctly refused
            return {
                "refused": True,
                "passed": False,
                "error": str(exc),
                "run_keys": [],
            }
        raise

    runs_after = _count_runs(runs_dir)
    new_runs = runs_after - runs_before

    passed = getattr(result, "passed", None)
    if passed is None:
        # Check via evaluation
        try:
            ev = result.evaluation
            passed = getattr(ev, "passed", False)
        except Exception:
            passed = False

    # Collect run_keys used
    run_keys = []
    for run_dir in sorted(runs_dir.iterdir()) if runs_dir.exists() else []:
        if run_dir.is_dir():
            run_keys.append(run_dir.name)

    print(f"  Sample {sample_id}: passed={passed}, new_runs={new_runs}")

    return {
        "refused": False,
        "passed": bool(passed),
        "run_keys": run_keys,
        "new_runs": new_runs,
    }


def _count_runs(runs_dir: Path) -> int:
    if not runs_dir.exists():
        return 0
    return sum(1 for p in runs_dir.iterdir() if p.is_dir())


def promote_sample_runs(data_dir: Path) -> int:
    """Promote all runs from data_dir/runs/origami-crane to CASE_DIR/runs/golden."""
    runs_src = data_dir / "runs" / "origami-crane"
    golden_dir = CASE_DIR / "runs" / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)

    if not runs_src.exists():
        return 0

    promoted = 0
    skipped = 0
    for run_dir in sorted(runs_src.iterdir()):
        if not run_dir.is_dir():
            continue
        dst = golden_dir / run_dir.name
        if dst.exists():
            skipped += 1
            continue
        shutil.copytree(run_dir, dst)
        promoted += 1

    print(f"  Promoted {promoted} runs, skipped {skipped} already present")
    return promoted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_samples(samples_dir: Path) -> None:
    """Generate all sample video files."""
    samples_dir.mkdir(parents=True, exist_ok=True)

    # 1. Good sample: first 25s of the learner video (Crane.ogv)
    good_path = samples_dir / "good.mp4"
    if good_path.exists():
        print(f"  good.mp4: already exists ({good_path.stat().st_size // 1024} KB)")
    else:
        print("  Building good.mp4 (learner video, first 25s)...")
        if not LEARNER_VIDEO.exists():
            print("  ERROR: Learner video not found. Run: python tools/fetch_media.py origami")
            return
        encode_video_segment(LEARNER_VIDEO, good_path, start_sec=0.0, duration_sec=MAX_DURATION_S)
        print(f"  good.mp4: {good_path.stat().st_size // 1024} KB")

    # 2. Flawed sample: use pre-existing swapped_order.mp4, or build from demo
    flawed_path = samples_dir / "flawed.mp4"
    if flawed_path.exists():
        print(f"  flawed.mp4: already exists ({flawed_path.stat().st_size // 1024} KB)")
    else:
        print("  Building flawed.mp4 (swapped order)...")
        if SWAPPED_ORDER_MP4.exists():
            # Use the existing eval swapped-order video (re-encode to 320px, 10fps, ≤25s)
            print(f"  Source: {SWAPPED_ORDER_MP4.name} ({SWAPPED_ORDER_MP4.stat().st_size // 1024} KB)")
            encode_video_segment(SWAPPED_ORDER_MP4, flawed_path, start_sec=0.0, duration_sec=MAX_DURATION_S)
        elif DEMO_VIDEO.exists():
            print("  swapped_order.mp4 not found; building from demo (single pass)...")
            build_swapped_order_sample(DEMO_VIDEO, flawed_path)
        else:
            print("  ERROR: Neither swapped_order.mp4 nor demo video found.")
            return
        if flawed_path.exists():
            print(f"  flawed.mp4: {flawed_path.stat().st_size // 1024} KB")

    # 3. Unrelated sample: synthetic colored rectangles
    unrelated_path = samples_dir / "unrelated.mp4"
    if unrelated_path.exists():
        print(f"  unrelated.mp4: already exists ({unrelated_path.stat().st_size // 1024} KB)")
    else:
        print("  Building unrelated.mp4 (synthetic colored rectangles)...")
        build_unrelated_sample(unrelated_path)
        print(f"  unrelated.mp4: {unrelated_path.stat().st_size // 1024} KB")

    # Check sizes
    for name in ["good.mp4", "flawed.mp4", "unrelated.mp4"]:
        p = samples_dir / name
        if p.exists() and p.stat().st_size > MAX_COMMITTED_BYTES:
            print(f"  WARNING: {name} is {p.stat().st_size // 1024} KB (>2 MB)")


def evaluate_samples(samples_dir: Path, data_dir: Path) -> dict:
    """Run Track B evaluation for each sample. Returns {sample_id: result}."""
    results = {}
    for s in SAMPLES:
        sample_path = samples_dir / s["file"]
        if not sample_path.exists():
            print(f"  SKIP {s['sample_id']}: file not found ({sample_path})")
            continue
        print(f"\n  Evaluating sample '{s['sample_id']}'...")
        result = run_track_b_eval(sample_path, s["sample_id"], data_dir)
        results[s["sample_id"]] = result
    return results


def write_samples_json(samples_dir: Path, results: Optional[dict] = None) -> None:
    """Write samples.json with expected outcomes calibrated from evaluation results."""
    samples_data = []
    for s in SAMPLES:
        sample = dict(s)
        sample["preview"] = None
        sample["raster"] = None

        if results and s["sample_id"] in results:
            r = results[s["sample_id"]]
            if r.get("refused"):
                sample["expected"] = {"refused": True}
            else:
                passed = r.get("passed", False)
                # Honesty rule: if good doesn't pass, change label
                if s["quality"] == "good" and not passed:
                    sample["label"] = "A real learner's attempt"
                    print(f"  NOTE: good sample did not pass; label updated to 'A real learner's attempt'")
                sample["expected"] = {"passed": passed}
        else:
            # Default expected before calibration
            sample["expected"] = {"passed": s["quality"] == "good"}

        samples_data.append(sample)

    data = {
        "schema_version": 1,
        "samples": samples_data,
    }
    out_path = samples_dir / "samples.json"
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Written {out_path}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build and evaluate origami-crane samples")
    ap.add_argument("--data-dir", default="var/k9-compose")
    ap.add_argument("--live", action="store_true", help="Run live Track B evaluations")
    ap.add_argument("--build-only", action="store_true", help="Only build video files, skip evaluation")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    samples_dir = CASE_DIR / "samples"
    print(f"=== BUILDING ORIGAMI-CRANE SAMPLES ===")
    print(f"Samples dir: {samples_dir}")

    # Check case exists
    if not CASE_DIR.exists():
        print(f"ERROR: Case not found at {CASE_DIR}")
        print("Run: python tools/build_curated_composed.py --live")
        return 1

    # Build video files
    build_samples(samples_dir)

    if args.build_only:
        write_samples_json(samples_dir)
        print("Build-only mode: samples.json written with default expected values")
        return 0

    if not args.live:
        write_samples_json(samples_dir)
        print("\nDRY RUN (no evaluation): samples.json written with default expected values")
        print("Pass --live to run Track B evaluations and calibrate expected values")
        return 0

    # Run Track B evaluations
    print("\n=== EVALUATING SAMPLES (live mode) ===")
    results = evaluate_samples(samples_dir, data_dir)

    # Write samples.json with calibrated expected
    write_samples_json(samples_dir, results)

    # Promote evaluation runs to golden
    print("\n=== PROMOTING RUNS ===")
    promoted = promote_sample_runs(data_dir)
    print(f"Promoted {promoted} runs to golden")

    total_calls = sum(r.get("new_runs", 0) for r in results.values())
    print(f"\nSample evaluation calls: {total_calls}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
