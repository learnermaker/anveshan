"""
KeyframeExtractor — decode a video with PyAV, probe FPS, and write frames.

Responsibilities
----------------
* Probe video FPS and duration via PyAV (no hard-coding, no CLI parameter).
* Decode frames at a configurable stride and write ``NNNNNN.jpg`` files
  compatible with FoldingAgent's FRAME_NAME_RE (``r'^(?P<index>\\d+)\\.(?:png|jpe?g)$'``).
* Write ``video_meta.json`` recording fps, duration_sec, width, height,
  total_frame_count.
* Write a skeleton ``keyframes.json`` listing every extracted global frame index
  so the user can trim it down to the representative keyframes they want
  FoldingAgent to process.

Output layout
-------------
<output_dir>/
  frames/
    000000.jpg      ← global frame index, zero-padded to 6 digits
    000010.jpg
    ...
  video_meta.json   ← fps, duration_sec, width, height, total_frame_count
  keyframes.json    ← FoldingAgent manifest with every extracted frame listed
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class KeyframeExtractor:
    """
    Parameters
    ----------
    video_path : Path
        Path to the source video (any format PyAV can decode: mp4, webm, ogv, avi…).
    output_dir : Path
        Root output directory.  ``frames/`` subdirectory created automatically.
    step : int
        Write every ``step``-th decoded frame (global index 0, step, 2*step, …).
        Default 10.  For a 24 fps / 335 s video that produces ~800 frames.
    max_frames : int | None
        If set, stop after writing this many frames.
    front_color : str
        FoldingAgent ``front_color`` written into ``keyframes.json``.
    back_color : str
        FoldingAgent ``back_color`` written into ``keyframes.json``.
    """

    def __init__(
        self,
        video_path: Path,
        output_dir: Path,
        step: int = 10,
        max_frames: int | None = None,
        front_color: str = "white",
        back_color: str = "lightblue",
    ) -> None:
        self.video_path = Path(video_path)
        self.output_dir = Path(output_dir)
        self.step = max(1, step)
        self.max_frames = max_frames
        self.front_color = front_color
        self.back_color = back_color

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        """
        Execute extraction.

        Returns
        -------
        dict with keys:
            fps, duration_sec, width, height, total_frame_count,
            frame_count (written), keyframe_count, output_dir
        """
        import av  # type: ignore[import-untyped]

        frames_dir = self.output_dir / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        # --- probe video metadata first ---
        meta = self._probe(av)

        # --- decode and write frames ---
        written_indices: list[int] = []
        global_idx = 0

        with av.open(str(self.video_path)) as container:
            stream = container.streams.video[0]
            # Disable multi-threading for deterministic frame ordering
            stream.thread_type = "NONE"

            for packet in container.demux(stream):
                for frame in packet.decode():
                    if global_idx % self.step == 0:
                        out_path = frames_dir / f"{global_idx:06d}.jpg"
                        frame.to_image().save(str(out_path), quality=95)
                        written_indices.append(global_idx)

                        if self.max_frames is not None and len(written_indices) >= self.max_frames:
                            break
                    global_idx += 1
                else:
                    continue
                break

        meta["total_frame_count"] = global_idx
        meta["frame_count"] = len(written_indices)
        meta["keyframe_count"] = len(written_indices)
        meta["output_dir"] = str(self.output_dir)

        # --- write video_meta.json ---
        self._write_video_meta(meta)

        # --- write keyframes.json (skeleton — user should trim) ---
        self._write_keyframes_json(written_indices, meta["fps"])

        return meta

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _probe(self, av: Any) -> dict[str, Any]:
        """Open the container once just to probe FPS and dimensions."""
        with av.open(str(self.video_path)) as container:
            stream = container.streams.video[0]

            # FPS: prefer average_rate (accounts for VFR), fall back to guessed_rate
            fps_frac = stream.average_rate or stream.guessed_rate
            if fps_frac is None or float(fps_frac) == 0.0:
                raise ValueError(
                    f"Could not determine FPS from {self.video_path}. "
                    "Supply a video with a valid average frame rate."
                )
            fps = float(fps_frac)

            # Duration: prefer stream duration, fall back to container duration
            if stream.duration is not None and stream.time_base is not None:
                duration_sec = float(stream.duration * stream.time_base)
            elif container.duration is not None:
                duration_sec = container.duration / 1_000_000  # microseconds
            else:
                duration_sec = 0.0

            width = stream.width or 0
            height = stream.height or 0

        return {
            "fps": fps,
            "duration_sec": round(duration_sec, 3),
            "width": width,
            "height": height,
        }

    def _write_video_meta(self, meta: dict[str, Any]) -> None:
        """Write video_meta.json with all probed + computed fields."""
        out = {
            "fps": meta["fps"],
            "duration_sec": meta["duration_sec"],
            "width": meta["width"],
            "height": meta["height"],
            "total_frame_count": meta.get("total_frame_count", 0),
            "source_video": str(self.video_path),
            "extraction_step": self.step,
        }
        path = self.output_dir / "video_meta.json"
        path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    def _write_keyframes_json(self, indices: list[int], fps: float) -> None:
        """
        Write a FoldingAgent-compatible keyframes.json.

        The file lists ALL extracted frame indices.  The user is expected to
        trim this to the ~10–20 representative keyframes they want FoldingAgent
        to process.  A comment field notes the timestamp for each index.

        Note: FoldingAgent's ``_load_keyframe_sequence`` uses only ``name``,
        ``frames``, ``front_color``, ``back_color``, and ``keyframes`` — extra
        keys are ignored.
        """
        sequence_name = self.video_path.stem.replace(" ", "_").lower()

        # Build a parallel annotations list for human readability (not used by FA)
        annotations = [
            {"frame_index": idx, "timestamp_sec": round(idx / fps, 3)}
            for idx in indices
        ]

        manifest = {
            "name": sequence_name,
            "frames": "frames",
            "front_color": self.front_color,
            "back_color": self.back_color,
            "keyframes": indices,
            "_annotations": annotations,  # informational only; FA ignores unknown keys
        }
        path = self.output_dir / "keyframes.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
