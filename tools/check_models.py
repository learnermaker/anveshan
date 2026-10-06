"""Smoke-test the configured Gemini API key and models (run after filling .env).

Probes exactly what the Anveshan build relies on and writes a JSON report:
  1. key works; which gemma / flash-lite model ids are visible
  2. Gemma text call: system instruction + JSON mode (response_mime_type) support
  3. Gemma without JSON mode: JSON extractable from text
  4. Gemma single-image input (kolam target)
  5. Gemma multi-image input (several labelled images in one call, as origami frames)
  6. the full ModelGateway path (records a run under var/runs/_smoke)
  7. optional audio model (only if ANVESHAN_AUDIO_MODEL is set)

Never prints the API key. Usage:
    .venv/Scripts/python tools/check_models.py            # writes var/model_check.json
"""

from __future__ import annotations

import io
import json
import math
import os
import struct
import sys
import time
import traceback
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel  # noqa: E402

from tracks.common.models import (  # noqa: E402
    ImagePart,
    ModelGateway,
    ModelRegistry,
    RunStore,
    extract_json,
    load_dotenv,
)

REPORT = ROOT / "var" / "model_check.json"
KOLAM = ROOT / "tracks" / "cases" / "kolam" / "source" / "ithayakkamalam_target.jpg"


class _Echo(BaseModel):
    ok: bool
    note: str


def _run(name: str, fn, results: dict) -> None:
    t0 = time.perf_counter()
    try:
        out = fn()
        results[name] = {"status": "PASS", "latency_ms": int((time.perf_counter() - t0) * 1000), "output": out}
    except Exception as exc:  # report, never hide
        results[name] = {
            "status": "FAIL",
            "latency_ms": int((time.perf_counter() - t0) * 1000),
            "error": f"{type(exc).__name__}: {str(exc)[:500]}",
            "trace_tail": traceback.format_exc().splitlines()[-3:],
        }
    print(f"[{results[name]['status']}] {name} ({results[name]['latency_ms']} ms)")


def _tone_wav(seconds: float = 1.0, sr: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / sr))) for i in range(int(seconds * sr))))
    return buf.getvalue()


def main() -> int:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        print("GEMINI_API_KEY is empty. Copy .env.example to .env and fill it in.")
        return 2
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=120_000))
    reg = ModelRegistry()
    gemma = reg.model_id("text_image") or "gemma-4-26b-a4b-it"
    results: dict = {"text_image_model": gemma, "video_frames_model": reg.model_id("video_frames"), "audio_model": reg.model_id("audio")}

    def list_models():
        names = []
        for m in client.models.list():
            n = getattr(m, "name", "")
            if "gemma" in n or "flash-lite" in n or "flash" in n:
                names.append(n)
        return sorted(names)

    def text_json_mode():
        r = client.models.generate_content(
            model=gemma,
            contents='Return JSON {"ok": true, "note": "<one short sentence>"} confirming you can read this.',
            config=types.GenerateContentConfig(temperature=0, system_instruction="You reply only with JSON.", response_mime_type="application/json"),
        )
        return {"text": (r.text or "")[:300], "parsed": extract_json(r.text or "")}

    def text_plain():
        r = client.models.generate_content(
            model=gemma,
            contents='Reply with only this JSON object and nothing else: {"ok": true, "note": "plain mode"}',
            config=types.GenerateContentConfig(temperature=0),
        )
        return {"text": (r.text or "")[:300], "parsed": extract_json(r.text or "")}

    img = KOLAM.read_bytes()

    def single_image():
        r = client.models.generate_content(
            model=gemma,
            contents=[types.Part.from_bytes(data=img, mime_type="image/jpeg"),
                      'Describe this drawing as JSON: {"line_color": str, "background_color": str, "approx_dot_count": int, "rotational_symmetry_order": int}'],
            config=types.GenerateContentConfig(temperature=0),
        )
        return {"text": (r.text or "")[:500], "parsed": extract_json(r.text or "")}

    def multi_image():
        from PIL import Image

        parts = []
        base = Image.open(KOLAM).convert("RGB")
        for i, angle in enumerate((0, 90, 180, 270)):
            b = io.BytesIO()
            base.rotate(angle).save(b, format="JPEG", quality=80)
            parts += [f"Frame t={i * 2}.0s", types.Part.from_bytes(data=b.getvalue(), mime_type="image/jpeg")]
        parts.append('For each frame above return JSON {"frames": [{"t": float, "rotation_guess_deg": int}]}')
        r = client.models.generate_content(model=gemma, contents=parts, config=types.GenerateContentConfig(temperature=0))
        return {"text": (r.text or "")[:500], "parsed": extract_json(r.text or "")}

    def gateway_path():
        gw = ModelGateway("live", RunStore([ROOT / "var" / "runs" / "_smoke"]), reg)
        res = gw.generate_json(
            model_key="text_image", prompt_id="smoke_check", prompt_version="v1",
            prompt_text='Return JSON {"ok": true, "note": "gateway works"}', schema=_Echo,
            parts=[ImagePart(img, label="Reference image:")], system="Reply only with JSON.",
        )
        return {"data": res.data.model_dump(), "model_id": res.metadata.model_id, "notes": res.metadata.notes, "latency_ms": res.metadata.latency_ms}

    def audio_model():
        audio = reg.model_id("audio")
        if not audio:
            return {"skipped": "ANVESHAN_AUDIO_MODEL not set (expected; optional)"}
        r = client.models.generate_content(
            model=audio,
            contents=[types.Part.from_bytes(data=_tone_wav(), mime_type="audio/wav"), 'Return JSON {"heard": str}'],
            config=types.GenerateContentConfig(temperature=0),
        )
        return {"text": (r.text or "")[:300]}

    _run("1_list_models", list_models, results)
    _run("2_gemma_text_json_mode_and_system_instruction", text_json_mode, results)
    _run("3_gemma_text_plain_json_extractable", text_plain, results)
    _run("4_gemma_single_image", single_image, results)
    _run("5_gemma_multi_image_labelled_frames", multi_image, results)
    _run("6_model_gateway_full_path", gateway_path, results)
    _run("7_optional_audio_model", audio_model, results)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport written to {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
