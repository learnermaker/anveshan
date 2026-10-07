"""Stress test of the universal pipeline on entirely new IMAGE and AUDIO skills.

image: a synthetic block-arrangement ("tangram-like" final state, nothing like kolam);
       attempts: same arrangement re-drawn with a small shift, one block missing,
       blocks in wrong colours/positions, unrelated image.
audio: a whistled melody-like tone sequence (temporal pattern, not tabla);
       attempts: same melody re-synthesised, rushed tempo, irregular rhythm, white noise.
speech: a spoken phrase (utterance structure) made with the local Windows speech synthesizer;
       attempts: same phrase in another voice, a different phrase, half the phrase, white noise.

Usage: python tools/stress_universal_other.py --scenario image|audio|speech --mode live|recorded [--save]
Verdicts come from real Track B sessions (evaluation.passed + criterion statuses).
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from stress_universal_video import attempt, compose  # noqa: E402  (also sets up sys.path and .env)

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

BLOCKS = [((60, 160, 140, 240), (220, 60, 50)), ((140, 160, 220, 240), (50, 120, 220)),
          ((100, 80, 180, 160), (240, 190, 40)), ((220, 160, 300, 240), (60, 170, 90)),
          ((180, 80, 260, 160), (150, 70, 180))]


def blocks_image(path: Path, keep=range(5), dx=0, dy=0, recolour=False, swap=False) -> None:
    img = Image.new("RGB", (360, 300), (245, 242, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([30, 240, 330, 250], fill=(120, 100, 80))       # table edge
    blocks = list(BLOCKS)
    if swap:
        blocks[2], blocks[4] = (blocks[4][0], blocks[2][1]), (blocks[2][0], blocks[4][1])
    for i in keep:
        (x0, y0, x1, y1), col = blocks[i]
        if recolour:
            col = (col[2], col[0], col[1])
        d.rectangle([x0 + dx, y0 + dy, x1 + dx, y1 + dy], fill=col, outline=(30, 30, 30), width=3)
    img.save(path)


def tone_melody(path: Path, notes, beat=0.35, sr=22050, jitter=0.0, seed=0) -> None:
    rng = np.random.default_rng(seed)
    out = []
    for f in notes:
        dur = beat * (1 + (rng.uniform(-jitter, jitter) if jitter else 0))
        t = np.arange(int(dur * sr)) / sr
        env = np.minimum(1, t / 0.01) * np.exp(-t * 4)
        out.append(0.6 * env * np.sin(2 * math.pi * f * t) + 0.3 * env * np.sin(4 * math.pi * f * t))
        out.append(np.zeros(int(0.05 * sr)))
    x = np.concatenate(out)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 30000).astype("<i2").tobytes())


def tts(path: Path, text: str, voice: str = "Microsoft David Desktop", rate: int = 0) -> None:
    """Windows-only: synthesise speech to a WAV with System.Speech (local, no network)."""
    def q(v: str) -> str:
        return "'" + v.replace("'", "''") + "'"
    script = (
        "Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SelectVoice({q(voice)}); $s.Rate = {int(rate)}; $s.SetOutputToWaveFile({q(str(path))}); "
        f"$s.Speak({q(text)}); $s.Dispose()"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)


def write_noise(path: Path, sec: float = 6.0, sr: int = 22050) -> None:
    noise = np.random.default_rng(1).normal(0, 0.3, int(sec * sr))
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(noise, -1, 1) * 30000).astype("<i2").tobytes())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", choices=["image", "audio", "speech"], default="image")
    ap.add_argument("--mode", choices=["live", "recorded"], default="recorded")
    ap.add_argument("--save", action="store_true")
    a = ap.parse_args(argv)
    work = ROOT / "var" / "stress" / a.scenario
    media = work / "media"
    media.mkdir(parents=True, exist_ok=True)
    if a.scenario == "image":
        src = media / "blocks_source.png"
        blocks_image(src)
        att = {"redrawn_shifted": media / "b_shift.png", "one_block_missing": media / "b_missing.png",
               "wrong_colours": media / "b_colours.png", "unrelated_house_frame": media / "b_unrel.png"}
        blocks_image(att["redrawn_shifted"], dx=8, dy=5)
        blocks_image(att["one_block_missing"], keep=[0, 1, 2, 3])
        blocks_image(att["wrong_colours"], recolour=True)
        Image.new("RGB", (360, 300), (40, 90, 160)).save(att["unrelated_house_frame"])
        title, mime, kind = "Stacking coloured blocks into a pattern", "image/png", "image"
    elif a.scenario == "speech":
        phrase = ("Please keep the left lane clear for emergency vehicles at all times, "
                  "and slow down when you pass the school gate in the morning.")
        src = media / "speech_source.wav"
        att = {"same_phrase_other_voice": media / "s_same.wav", "different_phrase": media / "s_diff.wav",
               "half_phrase": media / "s_half.wav", "white_noise": media / "s_noise.wav"}
        if a.mode == "live" or not src.exists():
            tts(src, phrase)
            tts(att["same_phrase_other_voice"], phrase, voice="Microsoft Zira Desktop", rate=1)
            tts(att["different_phrase"], "The museum opens at nine in the morning and closes early on "
                "public holidays, so please plan your visit ahead.",
                voice="Microsoft Zira Desktop")
            tts(att["half_phrase"], "Please keep the left lane clear for emergency vehicles at all times.",
                voice="Microsoft Zira Desktop")
            write_noise(att["white_noise"])
        title, mime, kind = "Saying a road-safety announcement clearly", "audio/wav", "audio"
    else:
        mel = [523, 587, 659, 523, 659, 784, 659, 587, 523, 440, 523, 587, 659, 523, 523, 659]
        src = media / "melody_source.wav"
        tone_melody(src, mel)
        att = {"same_melody": media / "m_same.wav", "rushed": media / "m_rushed.wav",
               "irregular": media / "m_irregular.wav", "white_noise": media / "m_noise.wav"}
        tone_melody(att["same_melody"], mel, seed=3)
        tone_melody(att["rushed"], mel, beat=0.22)
        tone_melody(att["irregular"], mel, jitter=0.45, seed=5)
        sr = 22050
        write_noise(att["white_noise"], sr=sr)
        title, mime, kind = "Whistling a short melody in steady time", "audio/wav", "audio"
    if a.mode == "live" and (work / "data").exists():
        shutil.rmtree(work / "data")
    comp = compose(src, mime, title, work, a.mode)
    print(json.dumps({k: v for k, v in comp.items() if k != "case_dir"}, indent=1)[:1500])
    res = {}
    if not comp.get("refused"):
        for n, p in att.items():
            r = attempt(Path(comp["case_dir"]), p, work, a.mode, kind)
            res[n] = r
            print(f"  {n:24s} {r['outcome']:8s} score={r.get('score')} crit={r.get('criteria') or r.get('reason')}")
            print(f"      metrics={r.get('metrics')}")
    summary = {"scenario": a.scenario, "mode": a.mode, "compose": {k: v for k, v in comp.items() if k != "case_dir"}, "attempts": res}
    (work / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    if a.save:
        out = ROOT / "tracks" / "track-b" / "eval" / "universal_video"
        (out / f"{a.scenario}_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
