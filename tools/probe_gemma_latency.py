"""Gemma image-call latency probe for the Origami case.

Measures latency (s) and success/timeout/error for each combination of
n_images × resolution × 2 runs, using frames sampled from the origami expert
video. Each call sends a short JSON task plus the JPEG frames.

Usage (worktree root, with .env present):
    python tools/probe_gemma_latency.py

Set ANVESHAN_MODEL_TIMEOUT_MS=120000 for clean timeout vs success signals.
After running, results are written to:
  var/runs/_probe/<replay_key>/   — individual run records
  docs/kiro/reports/K4-latency.md — summary table
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tracks" / "common"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common.models import (
    FailureCategory,
    ImagePart,
    ModelError,
    ModelGateway,
    ModelRegistry,
    RunStore,
    load_dotenv,
)
from tracks.common.media import sample_frames
from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Schema for the probe task
# ---------------------------------------------------------------------------


class ProbeResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    description: str = ""


PROBE_PROMPT = (
    "Look at the origami fold frames shown. In one sentence describe the visible "
    "paper shape in the last frame. Return JSON only: {\"description\": \"<one sentence>\"}"
)


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------


def _to_jpeg_bytes(img: Image.Image, max_side: int, quality: int = 75) -> bytes:
    w, h = img.size
    scale = max_side / max(w, h)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def _sample_n_frames(video_path: Path, n: int, max_side: int) -> List[ImagePart]:
    """Sample n frames evenly from the origami window [0, 194] s."""
    # Use a fixed set of evenly spaced timestamps covering the window
    import numpy as np

    all_frames = sample_frames(video_path, fps=0.5, start_sec=0.0, end_sec=194.0, max_side=max_side)
    if len(all_frames) <= n:
        chosen = all_frames
    else:
        idx = [int(round(i)) for i in __import__("numpy").linspace(0, len(all_frames) - 1, n)]
        idx = sorted(set(idx))[:n]
        chosen = [all_frames[i] for i in idx]
    parts = []
    for f in chosen:
        data = _to_jpeg_bytes(f.image, max_side=max_side, quality=75)
        parts.append(ImagePart(data=data, mime_type="image/jpeg", label=f"Frame t={f.time_sec:.1f}s"))
    return parts


# ---------------------------------------------------------------------------
# Probe runner
# ---------------------------------------------------------------------------


def run_probe() -> List[Dict[str, Any]]:
    load_dotenv(ROOT / ".env")

    video_path = ROOT / "tracks" / "cases" / "origami" / "media" / "cache" / "src.origami.demo.v1.ogv"
    if not video_path.exists():
        print(f"ERROR: origami media not found at {video_path}")
        print("Run: python tools/fetch_media.py --from-dir <media_dir>")
        sys.exit(1)

    store_root = ROOT / "var" / "runs" / "_probe"
    store_root.mkdir(parents=True, exist_ok=True)
    store = RunStore([store_root])

    registry = ModelRegistry()
    timeout_ms = int(os.environ.get("ANVESHAN_MODEL_TIMEOUT_MS", "120000"))
    print(f"Timeout: {timeout_ms} ms")

    gw = ModelGateway(mode="live", store=store, registry=registry, timeout_ms=timeout_ms)

    configs = [(n, res) for n in [1, 2, 3, 4, 6] for res in [256, 384]]
    results: List[Dict[str, Any]] = []

    total_calls = len(configs) * 2
    call_num = 0
    for n_images, resolution in configs:
        for run_idx in range(1, 3):
            call_num += 1
            print(f"[{call_num}/{total_calls}] n_images={n_images} res={resolution}px run={run_idx} ... ", end="", flush=True)
            row: Dict[str, Any] = {
                "n_images": n_images,
                "resolution": resolution,
                "run": run_idx,
                "status": "unknown",
                "latency_s": None,
                "replay_key": None,
                "error": None,
            }
            try:
                parts = _sample_n_frames(video_path, n_images, resolution)
                t0 = time.perf_counter()
                res = gw.generate_json(
                    model_key="video_frames",
                    prompt_id="probe_latency",
                    prompt_version="v1",
                    prompt_text=PROBE_PROMPT,
                    schema=ProbeResponse,
                    parts=parts,
                    expected_behavior="latency probe — short description of the paper shape",
                )
                elapsed = round(time.perf_counter() - t0, 2)
                row["status"] = "success"
                row["latency_s"] = elapsed
                row["replay_key"] = res.metadata.replay_key
                row["notes"] = res.metadata.notes
                print(f"OK  {elapsed:.1f}s")
            except ModelError as exc:
                elapsed = round(time.perf_counter() - t0, 2) if "t0" in dir() else None  # type: ignore[name-defined]
                if exc.category == FailureCategory.MODEL_TIMEOUT:
                    row["status"] = "timeout"
                else:
                    row["status"] = "error"
                row["error"] = str(exc)[:200]
                status_tag = "TIMEOUT" if row["status"] == "timeout" else "ERROR"
                print(f"{status_tag}  {str(exc)[:80]}")
            except Exception as exc:
                row["status"] = "error"
                row["error"] = str(exc)[:200]
                print(f"ERROR  {exc}")
            results.append(row)

    return results


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _status_icon(status: str) -> str:
    return {"success": "OK", "timeout": "TIMEOUT", "error": "ERROR"}.get(status, status)


def write_report(results: List[Dict[str, Any]], report_path: Path) -> None:
    lines = [
        "# K4 Gemma Latency Probe Results",
        "",
        "Probe ran against `gemma-4-26b-a4b-it` using JPEG frames from `OrigamiCrane.ogv`  ",
        f"Timeout per call: `ANVESHAN_MODEL_TIMEOUT_MS` (set during probe run)  ",
        "",
        "## Results table",
        "",
        "| n_images | resolution (px) | run | status | latency (s) | notes |",
        "|----------|-----------------|-----|--------|-------------|-------|",
    ]
    for r in results:
        latency = f"{r['latency_s']:.1f}" if r["latency_s"] is not None else "—"
        notes = "; ".join(r.get("notes", [])) or ""
        status = _status_icon(r["status"])
        lines.append(
            f"| {r['n_images']} | {r['resolution']} | {r['run']} | {status} | {latency} | {notes} |"
        )

    # Summary
    lines += ["", "## Summary"]
    for n in [1, 2, 3, 4, 6]:
        for res in [256, 384]:
            rows = [r for r in results if r["n_images"] == n and r["resolution"] == res]
            successes = [r["latency_s"] for r in rows if r["status"] == "success" and r["latency_s"] is not None]
            if successes:
                avg = sum(successes) / len(successes)
                lines.append(f"- **{n}img @ {res}px**: mean {avg:.1f}s ({len(successes)}/2 success)")
            else:
                statuses = [r["status"] for r in rows]
                lines.append(f"- **{n}img @ {res}px**: all {'TIMEOUT' if 'timeout' in statuses else 'ERROR'}")

    lines += [
        "",
        "## Batching policy recommendation",
        "",
        "Based on the results above, see Step 3 in K4-REPORT.md for the chosen policy and rationale.",
        "",
    ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport written to {report_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print("=== Gemma Latency Probe ===")
    results = run_probe()

    # Also save raw results JSON for later analysis
    raw_path = ROOT / "var" / "runs" / "_probe" / "probe_results.json"
    raw_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Raw results: {raw_path}")

    report_path = ROOT / "docs" / "kiro" / "reports" / "K4-latency.md"
    write_report(results, report_path)

    success = [r for r in results if r["status"] == "success"]
    timeout_ = [r for r in results if r["status"] == "timeout"]
    error = [r for r in results if r["status"] == "error"]
    print(f"\nDone: {len(success)} success, {len(timeout_)} timeout, {len(error)} error out of {len(results)} calls")


if __name__ == "__main__":
    main()
