"""Fetch uncommitted case media listed in tracks/cases/<case_id>/source/source.json.

Each source with a ``url`` whose ``path`` is under ``media/cache/`` (or missing) is
downloaded (or copied from --from-dir) into tracks/cases/<case_id>/media/cache/<source_id><ext>
and verified against its sha256. Committed files (path outside media/cache) are verified only.

Usage:
    python tools/fetch_media.py                 # all cases
    python tools/fetch_media.py origami tabla   # selected cases
    python tools/fetch_media.py --from-dir var/scratch/media   # copy local files by sha256 match
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracks.common.casedata import SourceRecord, load_sources  # noqa: E402

UA = "AnveshanHackathon/0.1 (https://github.com/learnermaker/anveshan; research prototype)"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def target_path(case_dir: Path, rec: SourceRecord) -> Path:
    if rec.path:
        return case_dir / rec.path
    ext = Path(rec.url or "").suffix or ".bin"
    return case_dir / "media" / "cache" / f"{rec.source_id}{ext}"


def find_local(from_dir: Path, digest: str) -> Path | None:
    for p in from_dir.rglob("*"):
        if p.is_file() and p.stat().st_size > 0 and sha256(p) == digest:
            return p
    return None


def download(url: str, dest: Path, attempts: int = 6) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for i in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as out:
                shutil.copyfileobj(r, out)
            tmp.replace(dest)
            return
        except Exception as exc:  # rate limits (429) and transient errors: back off
            wait = 15 * i
            print(f"  {url}: {exc}; retry {i}/{attempts} in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"failed to download {url}")


def playable_copy(src: Path) -> Path:
    """Chrome and Safari no longer play Ogg Theora: write an H.264/AAC .mp4 next to an .ogv (the media route serves it)."""
    dst = src.with_suffix(".mp4")
    if dst.exists():
        return dst
    import av

    tmp = dst.with_name(dst.stem + ".part.mp4")
    with av.open(str(src)) as inp, av.open(str(tmp), "w", options={"movflags": "faststart"}) as out:
        vin = inp.streams.video[0]
        vout = out.add_stream("libx264", rate=vin.average_rate)
        vout.width, vout.height = vin.width // 2 * 2, vin.height // 2 * 2
        vout.pix_fmt = "yuv420p"
        vout.options = {"crf": "26", "preset": "fast"}
        ain = inp.streams.audio[0] if inp.streams.audio else None
        aout = out.add_stream("aac", rate=ain.rate) if ain else None
        for packet in inp.demux([s for s in (vin, ain) if s]):
            for frame in packet.decode():
                if packet.stream is vin:
                    frame = frame.reformat(width=vout.width, height=vout.height, format="yuv420p")
                    frame.pts = round(frame.time * vin.average_rate) if frame.time is not None else None
                else:
                    frame.pts = None
                out.mux((vout if packet.stream is vin else aout).encode(frame))
        out.mux(vout.encode(None))
        if aout:
            out.mux(aout.encode(None))
    tmp.replace(dst)
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--from-dir", type=Path, default=None)
    args = ap.parse_args()
    cases_root = ROOT / "tracks" / "cases"
    case_dirs = [cases_root / c for c in args.cases] if args.cases else sorted(p.parent.parent for p in cases_root.glob("*/source/source.json"))
    failures = 0
    for case_dir in case_dirs:
        if not (case_dir / "source" / "source.json").exists():
            print(f"{case_dir.name}: no source.json, skipping")
            continue
        for rec in load_sources(case_dir).sources:
            dest = target_path(case_dir, rec)
            if dest.exists() and sha256(dest) == rec.sha256:
                print(f"{case_dir.name}/{rec.source_id}: ok")
                if dest.suffix == ".ogv":
                    playable_copy(dest)
                continue
            local = find_local(args.from_dir, rec.sha256) if args.from_dir else None
            if local:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(local, dest)
            elif rec.url and "media/cache" in str(dest).replace("\\", "/"):
                print(f"{case_dir.name}/{rec.source_id}: downloading {rec.url}")
                download(rec.url, dest)
            else:
                print(f"{case_dir.name}/{rec.source_id}: MISSING committed file {dest}")
                failures += 1
                continue
            got = sha256(dest)
            if got != rec.sha256:
                print(f"{case_dir.name}/{rec.source_id}: SHA256 MISMATCH {got}")
                failures += 1
            else:
                print(f"{case_dir.name}/{rec.source_id}: fetched")
                if dest.suffix == ".ogv":
                    playable_copy(dest)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
