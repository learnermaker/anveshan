"""Deterministic origami evaluation attempts (SYNTHETIC edits of the expert window + the real learner video).

Usage (repo root):
    python tracks/track-b/eval/origami/make_synthetic.py            # render videos + write ground truth
    python tracks/track-b/eval/origami/make_synthetic.py --labels-only

Videos are re-encoded with PyAV (mpeg4 in .mp4, 10 fps, NO audio track) into the gitignored
``var/eval/origami/``. Ground truth is derived from the AI-assisted expert labels
(labels/expert_window_labels.json) by mapping their intervals through each edit list, and is
written to ``labels/synthetic_ground_truth.json`` (committed). Edits are defined at the midpoint
between labelled states, so cuts fall in transitions:

- perfect        : the expert window unchanged (positive control)
- missing_state  : the segment containing R2 is cut out
- swapped_order  : the segments of R1 and R2 are swapped
- truncated      : stops in the transition after R4 (R5, R6 never reached)
- real_learner   : Crane.ogv window (same performance as the expert in another encode; NOT synthetic)
"""

from __future__ import annotations

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import av

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
LABELS = HERE / "labels"
OUT_DIR = ROOT / "var" / "eval" / "origami"
CASE_DIR = ROOT / "tracks" / "cases" / "origami"
OUT_FPS = 10

Segment = Tuple[float, float]


# ---------------------------------------------------------------------------
# Edit lists from labels
# ---------------------------------------------------------------------------


def state_spans(labels: dict) -> Dict[int, Tuple[float, float]]:
    """index -> (first start, last end)."""
    return {s["index"]: (s["intervals"][0][0], s["intervals"][-1][1]) for s in labels["states"]}


def boundaries(labels: dict) -> Dict[int, float]:
    """b[j] = midpoint between state j-1's end and state j's start (j >= 1)."""
    sp = state_spans(labels)
    return {j: round((sp[j - 1][1] + sp[j][0]) / 2.0, 3) for j in range(1, len(sp))}


def variant_segments(labels: dict) -> Dict[str, List[Segment]]:
    w0, w1 = labels["window_sec"]
    b = boundaries(labels)
    return {
        "perfect": [(w0, w1)],
        "missing_state": [(w0, b[2]), (b[3], w1)],
        "swapped_order": [(w0, b[1]), (b[2], b[3]), (b[1], b[2]), (b[3], w1)],
        "truncated": [(w0, b[5])],
    }


def map_intervals(labels: dict, segments: Sequence[Segment]) -> Dict[int, List[List[float]]]:
    """State intervals on the output timeline of an edit list."""
    out: Dict[int, List[List[float]]] = {}
    offset = 0.0
    for s0, s1 in segments:
        for st in labels["states"]:
            for a, b in st["intervals"]:
                lo, hi = max(a, s0), min(b, s1)
                if lo <= hi:
                    out.setdefault(st["index"], []).append([round(offset + lo - s0, 3), round(offset + hi - s0, 3)])
        offset += s1 - s0
    return {k: sorted(v) for k, v in sorted(out.items())}


def expected_outcome(intervals: Dict[int, List[List[float]]], k: int, duration: float) -> dict:
    first = {s: iv[0][0] for s, iv in intervals.items()}
    order = sorted(first, key=lambda s: first[s])
    events = []
    mx = -1
    for s in order:
        if s < mx:
            jumper = min((x for x in order if x > s and first[x] < first[s]), key=lambda x: first[x])
            events.append({"kind": "out_of_order", "state": s, "position_sec": first[jumper]})
        mx = max(mx, s)
    missing = [s for s in range(1, k + 1) if s not in first]
    for s in missing:
        later = [first[x] for x in first if x > s]
        events.append({"kind": "missing_state", "state": s, "position_sec": min(later) if later else round(duration, 3)})
    events.sort(key=lambda e: (e["position_sec"], e["state"]))
    last = max(first, key=lambda s: intervals[s][-1][1]) if first else None
    return {
        "state_order": order,
        "missing_states": missing,
        "order_violations": sum(e["kind"] == "out_of_order" for e in events),
        "off_path_events": 0,
        "final_reached": last == k,
        "events": events,
        "first_divergence": events[0] if events else None,
    }


def ground_truth(labels: dict, learner_labels: Optional[dict] = None) -> dict:
    k = max(s["index"] for s in labels["states"])
    variants = {}
    for name, segs in variant_segments(labels).items():
        dur = round(sum(b - a for a, b in segs), 3)
        iv = map_intervals(labels, segs)
        variants[name] = {
            "runtime_label": "SYNTHETIC",
            "source_id": labels["source_id"],
            "file": f"var/eval/origami/{name}.mp4",
            "segments": [[a, b] for a, b in segs],
            "duration_sec": dur,
            "state_intervals": {str(s): v for s, v in iv.items()},
            "expected": expected_outcome(iv, k, dur),
        }
    if learner_labels is not None:
        w0, w1 = learner_labels["window_sec"]
        iv = map_intervals(learner_labels, [(w0, w1)])
        variants["real_learner"] = {
            "runtime_label": "INTERNET_REFERENCE",
            "source_id": learner_labels["source_id"],
            "file": "var/eval/origami/real_learner.mp4",
            "segments": [[w0, w1]],
            "duration_sec": round(w1 - w0, 3),
            "state_intervals": {str(s): v for s, v in iv.items()},
            "expected": expected_outcome(iv, k, w1 - w0),
            "note": learner_labels.get("observation", ""),
        }
    return {
        "label_kind": "EVALUATION_GROUND_TRUTH",
        "never_system_input": True,
        "derived_from": ["expert_window_labels.json", "learner_crane_window_labels.json"],
        "annotator": labels["annotator"],
        "edit_rule": "cuts at the midpoint between the labelled end of state j-1 and start of state j",
        "boundaries_sec": {str(j): v for j, v in boundaries(labels).items()},
        "out_fps": OUT_FPS,
        "variants": variants,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _frames_between(path: Path, s0: float, s1: float):
    """Yield (t, VideoFrame) for frames with s0 <= t < s1, seeking near s0 when possible."""
    with av.open(str(path)) as c:
        st = c.streams.video[0]
        if s0 > 1.0:
            try:
                c.seek(int(max(s0 - 1.0, 0) / st.time_base), stream=st, backward=True, any_frame=False)
            except av.error.FFmpegError:
                c.seek(0, stream=st)
        for packet in c.demux(st):
            try:
                decoded = packet.decode()
            except av.error.FFmpegError:
                continue
            for fr in decoded:
                if fr.pts is None:
                    continue
                t = float(fr.pts * st.time_base)
                if t >= s1:
                    return
                if t >= s0 - 1e-6:
                    yield t, fr


def render(src: Path, segments: Sequence[Segment], out: Path, fps: int = OUT_FPS) -> int:
    """Concatenate segments of ``src`` into ``out`` (mpeg4, ``fps``, video only). Returns frame count."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(src)) as c:
        w, h = c.streams.video[0].width, c.streams.video[0].height
    w, h = w - w % 2, h - h % 2
    n_out = 0
    with av.open(str(out), "w") as oc:
        os_ = oc.add_stream("mpeg4", rate=fps)
        os_.width, os_.height, os_.pix_fmt = w, h, "yuv420p"
        os_.bit_rate = 1_500_000
        os_.time_base = Fraction(1, fps)
        for s0, s1 in segments:
            n_seg = int(round((s1 - s0) * fps))
            i = 0
            last = None
            for t, fr in _frames_between(src, s0, s1):
                while i < n_seg and t + 1e-6 >= s0 + i / fps:
                    img = fr.to_ndarray(format="rgb24")[:h, :w]
                    vf = av.VideoFrame.from_ndarray(img, format="rgb24")
                    vf.pts = n_out
                    for pk in os_.encode(vf):
                        oc.mux(pk)
                    n_out += 1
                    i += 1
                    last = img
            while last is not None and i < n_seg:   # pad with the last frame if the source ended early
                vf = av.VideoFrame.from_ndarray(last, format="rgb24")
                vf.pts = n_out
                for pk in os_.encode(vf):
                    oc.mux(pk)
                n_out += 1
                i += 1
        for pk in os_.encode():
            oc.mux(pk)
    return n_out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels-only", action="store_true", help="only (re)write synthetic_ground_truth.json")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)
    labels = json.loads((LABELS / "expert_window_labels.json").read_text(encoding="utf-8"))
    learner = json.loads((LABELS / "learner_crane_window_labels.json").read_text(encoding="utf-8"))
    gt = ground_truth(labels, learner)
    (LABELS / "synthetic_ground_truth.json").write_text(json.dumps(gt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {LABELS / 'synthetic_ground_truth.json'}")
    if args.labels_only:
        return 0
    from tracks.common.casedata import load_sources, resolve_media

    reg = load_sources(CASE_DIR)
    for name, v in gt["variants"].items():
        src = resolve_media(CASE_DIR, reg.get(v["source_id"]))
        out = args.out_dir / f"{name}.mp4"
        n = render(src, [tuple(s) for s in v["segments"]], out)
        print(f"{name}: {n} frames ({n / OUT_FPS:.1f} s, expected {v['duration_sec']:.1f} s) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
