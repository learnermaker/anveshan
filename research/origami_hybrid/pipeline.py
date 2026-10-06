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
# Subcommand: adapt
# ---------------------------------------------------------------------------

def cmd_adapt(args: argparse.Namespace) -> None:
    """
    Convert a FoldingAgent run directory into Anveshan contracts.

    Steps
    -----
    1. Load FoldingAgent checkpoints via FoldingAgentAdapter.
    2. Build KnowledgePackage (claims + evidence refs).
    3. Synthesize RubricDefinition (5 CRIT-HYB-N criteria).
    4. Generate PracticeTask.
    5. Validate grounding (EvidenceGrounder).
    6. Write sidecars (fold_state_log.json, crease_evidence.json).
    7. Emit run_metadata.json and expert_review_sheet.md.
    8. Write contracts (knowledge_package.json, rubric.json, practice_task.json).
    """
    from adapter import FoldingAgentAdapter
    from grounding import EvidenceGrounder
    from rubric_synth import RubricSynthesizer
    from sidecars import FoldStateLogWriter, CreaseEvidenceWriter
    from expert_review import (
        HybridRunMetadata,
        HybridRunMetadataWriter,
        HybridExpertReviewExporter,
    )

    fold_output_dir = Path(args.fold_output)
    video_meta_path = Path(args.video_meta)
    output_dir = Path(args.output)

    if not fold_output_dir.exists():
        sys.exit(f"[error] FoldingAgent run directory not found: {fold_output_dir}")
    if not video_meta_path.exists():
        sys.exit(f"[error] video_meta.json not found: {video_meta_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    attribution = args.attribution or ""
    run_id = fold_output_dir.name

    print(f"[1/8] Loading FoldingAgent checkpoints from {fold_output_dir} …")
    adapter = FoldingAgentAdapter(
        fold_output_dir=fold_output_dir,
        video_meta_path=video_meta_path,
        source_attribution=attribution,
        run_id=run_id,
    )
    checkpoints = adapter.load_checkpoints()
    print(f"      {len(checkpoints)} checkpoint(s) loaded")

    print("[2/8] Building KnowledgePackage …")
    package = adapter.build_knowledge_package()
    print(f"      package_id={package.package_id}, claims={len(package.claims)}")

    print("[3/8] Synthesizing RubricDefinition …")
    synth = RubricSynthesizer()
    rubric = synth.synthesize(checkpoints)
    print(f"      rubric_id={rubric.rubric_id}, criteria={len(rubric.criteria)}, passing_score={rubric.passing_score}")

    print("[4/8] Generating PracticeTask …")
    task = synth.generate_practice_task(rubric, package_id=package.package_id)
    print(f"      task_id={task.task_id}")

    print("[5/8] Validating grounding …")
    grounder = EvidenceGrounder()
    result = grounder.validate(package)
    if not result.is_valid:
        print(f"[!]   Grounding violations ({len(result.violations)}):")
        for v in result.violations:
            print(f"        {v}")
    else:
        print("      Grounding: OK")
    if result.uncertainty_flags:
        print(f"      Uncertainty flags ({len(result.uncertainty_flags)} INFERRED claims)")

    print("[6/8] Writing sidecars …")
    import json as _json
    meta_raw = _json.loads(video_meta_path.read_text())
    fps = float(meta_raw.get("fps", 0.0))

    FoldStateLogWriter().write(
        checkpoints, output_dir / "fold_state_log.json", run_id=run_id, fps=fps
    )
    CreaseEvidenceWriter().write(
        checkpoints, output_dir / "crease_evidence.json", run_id=run_id
    )
    print(f"      fold_state_log.json + crease_evidence.json → {output_dir}/")

    print("[7/8] Writing run_metadata.json and expert_review_sheet.md …")
    run_meta = HybridRunMetadata(
        provider=args.provider,
        model_id=args.model_id,
        prompt_id="hybrid_pipeline_v1",
        prompt_version="v1",
        input_artifact_id=attribution or "src-hybrid-video",
        runtime_class="LIVE",
        run_id=run_id,
        fold_output_dir=str(fold_output_dir.resolve()),
        package_id=package.package_id,
        claim_count=len(package.claims),
        grounding_violations=len(result.violations),
        uncertainty_flag_count=len(result.uncertainty_flags),
        source_attribution=attribution,
    )
    HybridRunMetadataWriter().write(run_meta, output_dir)
    HybridExpertReviewExporter().write(package, output_dir, run_meta)
    print(f"      run_metadata.json + expert_review_sheet.md → {output_dir}/")

    print("[8/8] Writing Anveshan contracts …")
    (output_dir / "knowledge_package.json").write_text(
        package.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "rubric.json").write_text(
        rubric.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "practice_task.json").write_text(
        task.model_dump_json(indent=2), encoding="utf-8"
    )
    print(f"      knowledge_package.json + rubric.json + practice_task.json → {output_dir}/")

    print()
    print("[ok] Hybrid pipeline complete.")
    print(f"     Output directory: {output_dir.resolve()}")


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
    ad.add_argument(
        "--attribution",
        default="",
        help="Source video attribution (e.g. 'Creator, CC BY 3.0, URL')",
    )
    ad.add_argument(
        "--provider",
        default="google",
        help="LLM provider used by FoldingAgent (default: google)",
    )
    ad.add_argument(
        "--model-id",
        default="gemini-3.1-pro-preview",
        dest="model_id",
        help="Model ID used by FoldingAgent (default: gemini-3.1-pro-preview)",
    )

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
