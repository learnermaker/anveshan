"""
Task 1 helper: extract the tabla source window (20.0–32.0 s) and write two WAV files.
- var/kiro/tabla_window_20-32s.wav        — 12 s at 16 kHz mono
- var/kiro/tabla_window_20-32s_3x_slow.wav — 36 s (3× duration, nearest-neighbour, no scipy)

Uses PyAV only (bundled ffmpeg). No librosa, no scipy, no soundfile.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

import av
import numpy as np

# ── paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tracks/cases/tabla/media/cache/src.tabla.demo.v1.webm"
OUT_DIR = ROOT / "var/kiro"
NORMAL = OUT_DIR / "tabla_window_20-32s.wav"
SLOW   = OUT_DIR / "tabla_window_20-32s_3x_slow.wav"

START_SEC = 20.0
END_SEC   = 32.0
TARGET_SR = 16_000


def decode_mono_float(path: Path, sr: int) -> np.ndarray:
    """Decode audio file to mono float32 at the requested sample rate using PyAV."""
    frames: list[np.ndarray] = []
    with av.open(str(path)) as container:
        stream = container.streams.audio[0]
        resampler = av.AudioResampler(
            format="fltp",
            layout="mono",
            rate=sr,
        )
        for packet in container.demux(stream):
            for frame in packet.decode():
                for out in resampler.resample(frame):
                    frames.append(out.to_ndarray()[0].copy())
        # flush resampler
        for out in resampler.resample(None):
            frames.append(out.to_ndarray()[0].copy())
    if not frames:
        raise RuntimeError("No audio decoded from %s" % path)
    return np.concatenate(frames, dtype=np.float32)


def write_wav_pcm16(path: Path, data: np.ndarray, sr: int) -> None:
    """Write mono float32 array as 16-bit PCM WAV without any external lib."""
    # clamp and convert to int16
    samples = np.clip(data, -1.0, 1.0)
    pcm = (samples * 32767).astype(np.int16)
    n_samples = len(pcm)
    data_chunk = pcm.tobytes()
    data_size = len(data_chunk)
    riff_size = 36 + data_size

    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", riff_size))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))        # chunk size
        f.write(struct.pack("<H", 1))         # PCM
        f.write(struct.pack("<H", 1))         # mono
        f.write(struct.pack("<I", sr))        # sample rate
        f.write(struct.pack("<I", sr * 2))    # byte rate (16-bit mono)
        f.write(struct.pack("<H", 2))         # block align
        f.write(struct.pack("<H", 16))        # bits per sample
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(data_chunk)


def nearest_stretch(x: np.ndarray, factor: int) -> np.ndarray:
    """Nearest-neighbour time stretch: each sample repeated `factor` times."""
    return np.repeat(x, factor)


def main() -> None:
    print(f"Source: {SRC}")
    if not SRC.exists():
        print("ERROR: source file not found. Run fetch_media.py first.", file=sys.stderr)
        sys.exit(1)

    print("Decoding audio …")
    audio = decode_mono_float(SRC, TARGET_SR)
    total_sec = len(audio) / TARGET_SR
    print(f"  Total duration: {total_sec:.2f} s  |  samples: {len(audio)}")

    start_samp = int(START_SEC * TARGET_SR)
    end_samp   = int(END_SEC   * TARGET_SR)
    window = audio[start_samp:end_samp]
    print(f"  Window [{START_SEC}–{END_SEC} s]: {len(window)} samples ({len(window)/TARGET_SR:.2f} s)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Writing normal speed → {NORMAL.name}")
    write_wav_pcm16(NORMAL, window, TARGET_SR)
    print(f"  {NORMAL.stat().st_size:,} bytes")

    print(f"Writing 3× slow → {SLOW.name}")
    slow_audio = nearest_stretch(window, 3)
    write_wav_pcm16(SLOW, slow_audio, TARGET_SR)
    print(f"  {SLOW.stat().st_size:,} bytes")

    print("\nDone.")
    print(f"  Normal: {NORMAL}")
    print(f"  Slow:   {SLOW}")


if __name__ == "__main__":
    main()
