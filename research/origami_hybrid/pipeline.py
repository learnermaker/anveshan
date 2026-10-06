"""
Hybrid Origami Pipeline — entry point.

Subcommands
-----------
extract-frames
    Decode a video with PyAV, probe FPS, write frames as NNNNNN.jpg and
    produce keyframes.json + video_meta.json in the output directory.

adapt  (TODO — commit 8)
    Convert a FoldingAgent run directory into Anveshan contracts.

Usage
-----
  python research/origami_hybrid/pipeline.py extract-frames \\
      --video path/to/input.mp4 \\
      --output data/crane/

  python research/origami_hybrid/pipeline.py adapt \\
      --fold-output out/run_<timestamp>_<model>_crane/ \\
      --video-meta data/crane/video_meta.json \\
      --output research/origami_hybrid/output/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Subcommand: extract-frames
# ---------------------------------------------------------------------------

def cmd_extract_frames(args: argparse.Namespace) -> None:
    """Decode video, probe FPS, write frames + video_meta.json + keyframes.json."""
    from extractor import KeyframeExtractor  # local import so PyAV is optional at top-level

    video_path = Path(args.video)
    if not video_path.exists():
        sys.exit(f"[error] Video not found: {video_path}")

    output_dir = Path(args.output)

    extractor = KeyframeExtractor(
        video_path=video_path,
        output_dir=output_dir,
        step=args.step,
        max_frames=args.max_frames,
        front_color=args.front_color,
        back_color=args.back_color,
    )
    result = extractor.run()

    print(f"[ok] frames written : {result['frame_count']} → {output_dir / 'frames'}/")
    print(f"[ok] video_meta.json: fps={result['fps']:.3f}  duration={result['duration_sec']:.1f}s")
    print(f"[ok] keyframes.json : {result['keyframe_count']} keyframes (every {args.step} frames)")
    print()
    print("Next step: review and trim keyframes.json, then run FoldingAgent:")
    print(f"  python -m foldingagent.main {output_dir / 'keyframes.json'}")


# ---------------------------------------------------------------------------
# Subcommand: adapt  (stub — implemented in commit 8)
# ---------------------------------------------------------------------------

def cmd_adapt(args: argparse.Namespace) -> None:
    sys.exit("[error] 'adapt' subcommand not yet implemented (coming in commit 8).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="Hybrid Origami Pipeline — FoldingAgent + Anveshan Track A",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # extract-frames
    ef = sub.add_parser(
        "extract-frames",
        help="Decode video, probe FPS, write frames + keyframes.json + video_meta.json",
    )
    ef.add_argument("--video", required=True, help="Path to input video file")
    ef.add_argument(
        "--output",
        required=True,
        help="Output directory (frames/, keyframes.json, video_meta.json written here)",
    )
    ef.add_argument(
        "--step",
        type=int,
        default=10,
        help="Write every Nth decoded frame (default: 10). Adjust for video length.",
    )
    ef.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Cap total frames written (default: no limit)",
    )
    ef.add_argument("--front-color", default="white", help="Paper front colour for keyframes.json")
    ef.add_argument("--back-color", default="lightblue", help="Paper back colour for keyframes.json")

    # adapt
    ad = sub.add_parser(
        "adapt",
        help="Convert FoldingAgent run output to Anveshan contracts",
    )
    ad.add_argument("--fold-output", required=True, help="FoldingAgent run directory")
    ad.add_argument("--video-meta", required=True, help="Path to video_meta.json (for FPS)")
    ad.add_argument("--output", required=True, help="Directory to write Anveshan contracts")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "extract-frames":
        cmd_extract_frames(args)
    elif args.command == "adapt":
        cmd_adapt(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
