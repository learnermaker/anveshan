"""Stress test of the universal pipeline on VIDEO uploads (engineering evidence).

Composes a case from an uploaded video exactly as the UI does (create_draft ->
create_case_from_draft -> build_case), then runs real Track B sessions for several
attempts and reports the deterministic verdict (evaluation.passed + criterion
statuses), not just "no exception".

Scenarios:
  synth  - an entirely new, synthetic procedure video ("draw a house" in 5 steps),
           attempts: perfect re-performance, missing step, swapped order, unrelated video.
  origami - OrigamiCrane.ogv uploaded as a NEW case (no origami specialist code used),
           attempts: Crane.ogv (same performance re-encoded), first 40 % only, unrelated video.

Usage:
  python tools/stress_universal_video.py --scenario synth --mode live
  python tools/stress_universal_video.py --scenario synth --mode recorded   # replays recorded calls
Media for 'origami' is read from --media-dir (default var/scratch/media). Nothing here is committed
except the summary JSON under tracks/track-b/eval/universal_video/ (with --save).
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tracks" / "track-a" / "src", ROOT / "tracks" / "track-b" / "src", ROOT / "service"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common.models import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import av  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

W, H, FPS = 480, 270, 10


# ---------------------------------------------------------------------------
# Synthetic procedure video
# ---------------------------------------------------------------------------

def _house_layers(dx: int = 0, dy: int = 0):
    """Five drawing steps of a simple house; each returns a draw callback."""
    def walls(d):
        d.rectangle([150 + dx, 120 + dy, 330 + dx, 240 + dy], outline=(30, 30, 30), width=5, fill=(235, 210, 160))

    def roof(d):
        d.polygon([(135 + dx, 122 + dy), (240 + dx, 45 + dy), (345 + dx, 122 + dy)], outline=(30, 30, 30), fill=(170, 40, 40))

    def door(d):
        d.rectangle([220 + dx, 170 + dy, 260 + dx, 240 + dy], outline=(30, 30, 30), width=4, fill=(90, 55, 20))

    def window(d):
        d.rectangle([280 + dx, 145 + dy, 315 + dx, 180 + dy], outline=(30, 30, 30), width=4, fill=(120, 190, 240))
        d.line([297 + dx, 145 + dy, 297 + dx, 180 + dy], fill=(30, 30, 30), width=3)

    def sun(d):
        d.ellipse([380 + dx, 25 + dy, 440 + dx, 85 + dy], fill=(250, 200, 30))
        for k in range(8):
            a = k * math.pi / 4
            d.line([410 + dx + 35 * math.cos(a), 55 + dy + 35 * math.sin(a), 410 + dx + 48 * math.cos(a), 55 + dy + 48 * math.sin(a)],
                   fill=(250, 200, 30), width=4)

    return [("walls", walls), ("roof", roof), ("door", door), ("window", window), ("sun", sun)]


def write_procedure_video(path: Path, order: List[int], *, hold_s: float = 5.0, work_s: float = 4.0,
                          dx: int = 0, dy: int = 0, seed: int = 0) -> None:
    """Render: blank paper, then for each step a 'hand' moves while the part appears, then a still hold."""
    rng = np.random.default_rng(seed)
    layers = _house_layers(dx, dy)
    done: List[int] = []

    def canvas(partial: Optional[int] = None, frac: float = 0.0, hand=None) -> Image.Image:
        img = Image.new("RGB", (W, H), (250, 248, 240))
        d = ImageDraw.Draw(img)
        for i in done:
            layers[i][1](d)
        if partial is not None and frac > 0.5:
            layers[partial][1](d)
        if hand is not None:
            hx, hy = hand
            d.ellipse([hx - 22, hy - 22, hx + 22, hy + 22], fill=(205, 160, 130))
            d.rectangle([hx - 10, hy, hx + 10, H], fill=(205, 160, 130))
        arr = np.asarray(img).astype(np.int16) + rng.integers(-3, 4, size=(H, W, 3))
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    out = av.open(str(path), mode="w")
    st = out.add_stream("mpeg4", rate=FPS)
    st.width, st.height, st.pix_fmt = W, H, "yuv420p"

    def emit(img: Image.Image):
        for pkt in st.encode(av.VideoFrame.from_image(img)):
            out.mux(pkt)

    for _ in range(int(hold_s * FPS)):
        emit(canvas())
    for step in order:
        n = int(work_s * FPS)
        for k in range(n):
            frac = k / n
            hand = (160 + 180 * frac + 25 * math.sin(k), 140 + 40 * math.sin(k / 2))
            emit(canvas(step, frac, hand))
        done.append(step)
        for _ in range(int(hold_s * FPS)):
            emit(canvas())
    for pkt in st.encode():
        out.mux(pkt)
    out.close()


def write_clip(src: Path, dst: Path, start: float, end: float, max_side: int = 400) -> None:
    """Re-encode [start, end] of a video (no audio) with PyAV."""
    from tracks.common.media import sample_frames
    frames = sample_frames(src, fps=5.0, start_sec=start, end_sec=end, max_side=max_side)
    w, h = frames[0].image.size
    w, h = w - w % 2, h - h % 2
    out = av.open(str(dst), mode="w")
    st = out.add_stream("mpeg4", rate=5)
    st.width, st.height, st.pix_fmt = w, h, "yuv420p"
    for f in frames:
        for pkt in st.encode(av.VideoFrame.from_image(f.image.convert("RGB").resize((w, h)))):
            out.mux(pkt)
    for pkt in st.encode():
        out.mux(pkt)
    out.close()


# ---------------------------------------------------------------------------
# Compose + sessions
# ---------------------------------------------------------------------------

def compose(src: Path, mime: str, title: str, work: Path, mode: str) -> Dict:
    from tracks.common.runtime import RunContext
    from track_a.composer import create_draft, create_case_from_draft
    from track_a.api import build_case

    data_dir = work / "data"
    ctx = RunContext.create(work / "cases_placeholder", data_dir, mode)
    t0 = time.time()
    draft = create_draft(data_dir, src, mime, ctx, title_hint=title, rights_confirmed=True)
    info: Dict = {"compose_s": round(time.time() - t0, 1)}
    if draft.refused or draft.proposal is None:
        info.update(refused=True, reason=draft.refusal_message or "no proposal")
        return info
    case_dir = create_case_from_draft(work / "cases", data_dir, draft.draft_id, edits={"title": title, "confirmed_by_user": True})
    t1 = time.time()
    handoff = build_case(case_dir, RunContext.create(case_dir, data_dir, mode))
    sk = draft.proposal.skill_model
    info.update(
        refused=False, case_dir=str(case_dir), build_s=round(time.time() - t1, 1),
        structures=list(sk.structures), n_steps=len(sk.steps),
        steps=[f"{s.index}:{s.name}" + (f"@{s.start_sec:.0f}-{s.end_sec:.0f}s" if getattr(s, "start_sec", None) is not None else "") for s in sk.steps],
        checks=[f"{c.check_id}:{c.kind}" for c in sk.checks if c.enabled],
        warnings=list(handoff.warnings)[:6],
    )
    return info


def attempt(case_dir: Path, path: Path, work: Path, mode: str) -> Dict:
    from tracks.common.runtime import RunContext
    from track_b import api as tb
    from tracks.common.models import AnveshanFailure

    data_dir = work / "data"
    sess = tb.start_session(case_dir, "stress", data_dir)
    t0 = time.time()
    try:
        media = tb.intake_attempt(sess, path, "video")
        res = tb.submit_attempt(sess, media, RunContext.create(case_dir, data_dir, mode)).data
    except AnveshanFailure as exc:
        return {"outcome": "REFUSED", "category": exc.category.value, "reason": str(exc)[:160], "s": round(time.time() - t0, 1)}
    ev = res["evaluation"]
    crit = {c["criterion_id"]: c["status"] for c in ev.get("criterion_results", [])}
    fd = res.get("first_divergence") or {}
    return {
        "outcome": "PASS" if ev.get("passed") else "FAIL",
        "score": ev.get("total_score"),
        "criteria": crit,
        "metrics": {k: (v.get("value") if isinstance(v, dict) else v) for k, v in (res.get("metrics") or {}).items()},
        "warnings": [w for w in res.get("warnings", []) if "expert-approved" not in w and "inferred until" not in w][:5],
        "first_divergence": fd.get("summary") or fd.get("criterion_id") if isinstance(fd, dict) else fd,
        "s": round(time.time() - t0, 1),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=["synth", "origami", "origami_window"], default="synth")
    ap.add_argument("--mode", choices=["live", "recorded"], default="recorded")
    ap.add_argument("--media-dir", default=str(ROOT / "var" / "scratch" / "media"))
    ap.add_argument("--work", default=str(ROOT / "var" / "stress"))
    ap.add_argument("--save", action="store_true", help="write the summary to tracks/track-b/eval/universal_video/")
    a = ap.parse_args(argv)

    work = Path(a.work) / a.scenario
    media = work / "media"
    media.mkdir(parents=True, exist_ok=True)
    md = Path(a.media_dir)
    unrelated = md / "src.tabla.demo.v1.webm"

    if a.scenario == "synth":
        src = media / "house_source.mp4"
        variants = {
            "perfect_reperformance": (media / "house_perfect.mp4", dict(order=[0, 1, 2, 3, 4], dx=12, dy=6, seed=7, hold_s=4.0, work_s=5.0)),
            "missing_step_door": (media / "house_missing.mp4", dict(order=[0, 1, 3, 4], seed=8)),
            "swapped_roof_walls": (media / "house_swapped.mp4", dict(order=[1, 0, 2, 3, 4], seed=9)),
            "stopped_after_roof": (media / "house_partial.mp4", dict(order=[0, 1], seed=10)),
        }
        if not src.exists():
            write_procedure_video(src, [0, 1, 2, 3, 4], seed=1)
        for p, kw in variants.values():
            if not p.exists():
                write_procedure_video(p, **kw)
        attempts = {k: v[0] for k, v in variants.items()}
        title, mime = "Drawing a simple house step by step", "video/mp4"
    elif a.scenario == "origami_window":
        # Same setup as the dedicated origami engine eval: expert window 0-194 s (goal = bird base),
        # attempts rendered by tracks/track-b/eval/origami/make_synthetic.py --out-dir var/eval/origami
        src = media / "origami_window_source.mp4"
        if not src.exists():
            write_clip(md / "OrigamiCrane.ogv", src, 0.0, 194.0)
        ev = ROOT / "var" / "eval" / "origami"
        attempts = {n: ev / f"{n}.mp4" for n in ("perfect", "real_learner", "missing_state", "swapped_order", "truncated")}
        title, mime = "Folding an origami bird base", "video/mp4"
    else:
        src = md / "OrigamiCrane.ogv"
        part = media / "origami_first40.mp4"
        if not part.exists():
            write_clip(src, part, 0.0, 130.0)
        attempts = {"crane_reencoded_positive_control": md / "Crane.ogv", "first_40_percent": part}
        title, mime = "Folding an origami crane", "video/ogg"
    if unrelated.exists():
        attempts["unrelated_tabla_video"] = unrelated

    if a.mode == "live" and (work / "cases").exists():
        shutil.rmtree(work / "cases")
    print(f"[{a.scenario}] composing {src.name} ({a.mode}) ...", flush=True)
    comp = compose(src, mime, title, work, a.mode)
    print(json.dumps(comp, indent=1), flush=True)
    results: Dict[str, Dict] = {}
    if not comp.get("refused"):
        for name, p in attempts.items():
            r = attempt(Path(comp["case_dir"]), p, work, a.mode)
            results[name] = r
            print(f"  {name:34s} {r['outcome']:8s} score={r.get('score')} crit={r.get('criteria') or r.get('reason')}", flush=True)
            print(f"      metrics={r.get('metrics')} fd={r.get('first_divergence')}", flush=True)
            print(f"      warnings={r.get('warnings')}", flush=True)
    summary = {"scenario": a.scenario, "mode": a.mode, "compose": comp, "attempts": results}
    (work / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    if a.save:
        out = ROOT / "tracks" / "track-b" / "eval" / "universal_video"
        out.mkdir(parents=True, exist_ok=True)
        comp_slim = {k: v for k, v in comp.items() if k != "case_dir"}
        (out / f"{a.scenario}_summary.json").write_text(json.dumps({**summary, "compose": comp_slim}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
