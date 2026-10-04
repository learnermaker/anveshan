#!/usr/bin/env python3
"""CLI runner for Track A pipeline supporting direct execution.

Supports:
    python tracks/track-a/src/run_pipeline.py --case micrometer --mode replay
    python tracks/track-a/src/run_pipeline.py --all --mode replay
    python tracks/track-a/src/run_pipeline.py --case micrometer --mode live
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Resolve import paths
SRC_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Optional dotenv loading for live mode
try:
    from dotenv import load_dotenv  # type: ignore
    env_file = REPO_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

from case_registry import discover_cases, load_manifest
from expert_review import ExpertReviewService
from pipeline import TrackAPipeline


def run_single_case(pipeline: TrackAPipeline, case_id: str, output_dir: Path) -> None:
    print(f"--> Executing Track A pipeline for [{case_id}] (mode: {pipeline.mode})...")
    bundle = pipeline.run(case_id=case_id)

    case_out = output_dir / case_id
    case_out.mkdir(parents=True, exist_ok=True)

    # 1. Save normalized KnowledgePackage
    (case_out / "knowledge_package.json").write_text(
        bundle.package.model_dump_json(indent=2), encoding="utf-8"
    )

    # 2. Save RubricDefinition
    (case_out / "rubric.json").write_text(
        bundle.rubric.model_dump_json(indent=2), encoding="utf-8"
    )

    # 3. Save PracticeTask
    (case_out / "practice_task.json").write_text(
        bundle.practice_task.model_dump_json(indent=2), encoding="utf-8"
    )

    # 4. Save Run Metadata
    (case_out / "run_metadata.json").write_text(
        bundle.run_metadata.model_dump_json(indent=2), encoding="utf-8"
    )

    # 5. Export Expert Review Inspection Sheet
    rev_service = ExpertReviewService()
    sheet_md = rev_service.export_markdown(bundle.package, bundle.manifest)
    (case_out / "expert_review_sheet.md").write_text(sheet_md, encoding="utf-8")

    print(f"    [OK] Emitted KnowledgePackage: {bundle.package.package_id}")
    print(f"    [OK] Emitted RubricDefinition: {bundle.rubric.rubric_id} ({len(bundle.rubric.criteria)} criteria)")
    print(f"    [OK] Emitted PracticeTask:     {bundle.practice_task.task_id}")
    print(f"    [OK] Expert Review Sheet:      {case_out / 'expert_review_sheet.md'}")
    if bundle.uncertainty_summary:
        print(f"    [!] Uncertainty claims ({len(bundle.uncertainty_summary)}): {bundle.uncertainty_summary}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Track A Pipeline CLI Runner.")
    parser.add_argument("--case", type=str, help="Case slug to process (e.g. micrometer, kolam)")
    parser.add_argument("--all", action="store_true", help="Process all registered cases in index.json")
    parser.add_argument(
        "--mode",
        choices=["replay", "live"],
        default="replay",
        help="Pipeline execution mode (default: replay)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "tracks" / "track-a" / "data" / "cases",
        help="Destination directory for emitted Track A artifacts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estimate token cost and inspect media discovery without calling Gemini API",
    )
    args = parser.parse_args()

    cases_root = REPO_ROOT / "tracks" / "cases"
    if not cases_root.exists():
        print(f"Error: cases root not found: {cases_root}", file=sys.stderr)
        return 1

    if args.dry_run:
        from media_service import MediaService

        cases_to_check = discover_cases(cases_root) if args.all else ([args.case] if args.case else [])
        if not cases_to_check:
            print("Error: Specify --case <id> or --all with --dry-run", file=sys.stderr)
            return 1

        print("=== Track A Live Pipeline Dry-Run Audit ===")
        media_svc = MediaService(cases_root)
        for c in cases_to_check:
            try:
                desc = media_svc.discover_media(c)
                print(f"\n[Case: {c}]")
                print(f"  Source Type: {desc.type}")
                if desc.type == "url":
                    print(f"  Source URL:  {desc.url}")
                elif desc.type == "local_file":
                    print(f"  Local Path:  {desc.path}")
                print(f"  MIME Type:   {desc.mime_type}")
                print(f"  Attribution: {desc.attribution}")

                local_p = media_svc.resolve_media_path(c, desc)
                size_mb = local_p.stat().st_size / (1024 * 1024)
                print(f"  Resolved:    {local_p} ({size_mb:.2f} MB)")
                # Token estimation rule of thumb: ~258 tokens/sec video, ~1000 tokens for image/prompt
                if desc.mime_type and "video" in desc.mime_type:
                    print("  Token Est:   ~250 tokens/sec of video + ~1,500 prompt tokens (±20% depending on FPS/resolution)")
                else:
                    print("  Token Est:   ~1,500 - 3,000 multimodal tokens (image/structured prompt)")
            except Exception as e:
                print(f"\n[Case: {c}]")
                print(f"  Media Status: NOT CONFIGURED / FAILED ({e})")
        return 0

    pipeline = TrackAPipeline(cases_root=cases_root, mode=args.mode)

    if args.all:
        cases = discover_cases(cases_root)
        print(f"Processing all {len(cases)} registered cases: {cases}")
        for c in cases:
            run_single_case(pipeline, c, args.output_dir)
        print(f"\nAll {len(cases)} cases successfully processed.")
        return 0
    elif args.case:
        run_single_case(pipeline, args.case, args.output_dir)
        return 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
