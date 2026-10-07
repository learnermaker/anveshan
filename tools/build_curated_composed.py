"""Build the origami-crane featured skill via the universal pipeline.

Mirrors the compose route exactly but runs in-process so the packed case can be
committed at tracks/cases/origami-crane/.

Usage (from worktree root):
    python tools/build_curated_composed.py \\
        --source tracks/cases/origami/media/cache/src.origami.demo.v1.ogv \\
        --case-id origami-crane \\
        --title "Fold a paper crane: the first folds" \\
        --description "Fold a square of paper into a crane, following the demonstration step by step." \\
        [--data-dir var/k9-compose] [--live]

Steps (mirroring service/anveshan_service/routes/compose.py):
  1. RunContext in live mode.
  2. composer.create_draft(data_dir, source, mime, ctx, ...).
  3. Print proposal summary; stop if refused or None.
  4. composer.create_case_from_draft(cases_root_tmp, data_dir, draft_id, edits).
  5. track_a.api.build_case(case_dir_in_data_dir, ctx).
  6. Copy case_dir to tracks/cases/origami-crane/:
     - rewrite case_id references from composed slug~hash to origami-crane;
     - delete .owners.json and .library.json;
     - replace source media > 2 MB with a source-registry entry pointing to the URL;
  7. Rebuild in place (run keys computed against final path; live cache avoids new calls).
  8. Promote golden runs to tracks/cases/origami-crane/runs/golden/.

Live-call budget: <= 40. Each run directory created counts as one call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
for p in [
    str(ROOT),
    str(ROOT / "tracks" / "track-a" / "src"),
    str(ROOT / "tracks" / "track-b" / "src"),
    str(ROOT / "service"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

from tracks.common.models import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

CASES_ROOT = ROOT / "tracks" / "cases"
FINAL_CASE_ID = "origami-crane"
FINAL_CASE_DIR = CASES_ROOT / FINAL_CASE_ID

MAX_COMMITTED_BYTES = 2 * 1024 * 1024  # 2 MB

# Attribution for this case — same Wikimedia source as origami
ATTRIBUTION = "OrigamiCrane.ogv by Tavin, CC BY 3.0, via Wikimedia Commons"
SOURCE_URL = "https://upload.wikimedia.org/wikipedia/commons/b/bb/OrigamiCrane.ogv"
SOURCE_SHA256 = "4489d37966da1be348742b9cb8f0e99abda7553078bfce2e7abe94062f32b485"
# Cache path within the case pack
CACHE_PATH = "media/cache/src.origami.crane.demo.v1.ogv"
# Path in origami case (same sha256)
ORIGAMI_CACHE = CASES_ROOT / "origami" / "media" / "cache" / "src.origami.demo.v1.ogv"


def sha256_bytes(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_run_dirs(path: Path) -> int:
    """Count immediate subdirectories (each = one model run record)."""
    if not path.exists():
        return 0
    return sum(1 for p in path.iterdir() if p.is_dir())


def count_all_runs(data_dir: Path) -> int:
    """Sum all run dirs across all case subdirs in data_dir/runs."""
    runs_root = data_dir / "runs"
    if not runs_root.exists():
        return 0
    return sum(
        count_run_dirs(case_runs)
        for case_runs in runs_root.iterdir()
        if case_runs.is_dir()
    )


def print_proposal_summary(draft: Any) -> None:
    if draft.refused:
        print(f"\n[REFUSED] {draft.refusal_message}")
        return
    if draft.proposal is None:
        print("\n[NO PROPOSAL] Draft has no proposal — needs title/description hint")
        return
    p = draft.proposal
    sm = p.skill_model
    print("\n=== PROPOSAL SUMMARY ===")
    print(f"Title: {p.title}")
    print(f"Case ID (composed): {p.case_id}")
    print(f"Structures: {sm.structures}")
    print(f"Steps ({len(sm.steps)}):")
    for s in sm.steps:
        ts = f"t={s.start_sec:.1f}-{s.end_sec:.1f}s" if s.start_sec is not None else ""
        print(f"  [{s.step_id}] {s.name} {ts} (critical={s.critical})")
    print(f"Goal properties ({len(sm.goal_state)}):")
    for g in sm.goal_state:
        print(f"  [{g.prop_id}] {g.statement}")
    print(f"Checks ({len(sm.checks)}):")
    for c in sm.checks:
        print(f"  [{c.check_id}] {c.kind}: {c.name}")
    if sm.warnings:
        print(f"Warnings: {sm.warnings[:3]}")
    print("========================\n")


def rewrite_case_id_in_jsons(old_id: str, new_id: str, case_dir: Path) -> None:
    """Replace all occurrences of old_id with new_id in JSON files in case_dir."""
    for json_file in case_dir.rglob("*.json"):
        try:
            text = json_file.read_text(encoding="utf-8")
            if old_id in text:
                new_text = text.replace(old_id, new_id)
                json_file.write_text(new_text, encoding="utf-8")
                print(f"  Rewrote case_id in: {json_file.relative_to(case_dir)}")
        except Exception as e:
            print(f"  WARNING: could not rewrite {json_file}: {e}")


def create_canonical_source_json(case_dir: Path, original_video: Path) -> None:
    """Replace the upload-style source.json with a canonical source-registry entry.

    The actual video (>2MB) is not committed; fetch_media.py downloads it via sha256/URL.
    """
    from tracks.common.casedata import SourceRecord, SourceRegistry, write_json

    dimensions = None
    duration_sec = None
    actual_bytes = 25026185  # known from origami/source/source.json
    if original_video and original_video.exists():
        try:
            from tracks.common.media import probe
            info = probe(original_video)
            duration_sec = info.duration_sec
            if info.width and info.height:
                dimensions = [int(info.width), int(info.height)]
            actual_bytes = original_video.stat().st_size
        except Exception as exc:
            print(f"  WARNING: could not probe source media: {exc}")

    src = SourceRecord(
        source_id="src.origami-crane.demo.v1",
        role="expert_video",
        mime_type="video/ogg",
        sha256=SOURCE_SHA256,
        bytes=actual_bytes,
        path=CACHE_PATH,
        url=SOURCE_URL,
        duration_sec=duration_sec or 335.0,
        dimensions=dimensions or [400, 226],
        creator="Tavin",
        license="CC BY 3.0",
        attribution=ATTRIBUTION,
        access_level="public",
        runtime_label="INTERNET_REFERENCE",
        used_by_system=True,
        notes=(
            "Universal pipeline case built from the origami demo video. "
            "Same source as tracks/cases/origami/source/source.json (sha256 matches). "
            "Full 335 s video; universal pipeline segments it automatically."
        ),
    )
    registry = SourceRegistry(case_id=FINAL_CASE_ID, sources=[src])
    write_json(case_dir / "source" / "source.json", registry)
    print(f"  Written canonical source.json: {src.source_id}")


def copy_media_cache(case_dir: Path) -> None:
    """Copy the demo video into the case's media/cache directory (not committed)."""
    cache_dir = case_dir / "media" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    target = cache_dir / Path(CACHE_PATH).name
    if not target.exists():
        if ORIGAMI_CACHE.exists():
            shutil.copyfile(ORIGAMI_CACHE, target)
            print(f"  Copied demo video to cache: {target.name}")
        else:
            print(f"  WARNING: origami cache not found at {ORIGAMI_CACHE}")
            print("  Run: python tools/fetch_media.py origami")


def make_ctx_with_cache(
    final_case_dir: Path,
    data_dir: Path,
    orig_case_id: str,
) -> Any:
    """Build a live RunContext for the rebuild that also searches the step-5 run cache.

    This allows the gateway to replay identical calls without making new API requests.
    """
    from tracks.common.models import ModelGateway, RunStore
    from tracks.common.runtime import RunContext

    store = RunStore([
        data_dir / "runs" / final_case_dir.name,   # write new runs here
        data_dir / "runs" / orig_case_id,            # search step-5 runs (live cache)
        final_case_dir / "runs" / "golden",           # search committed golden runs
    ])
    gw = ModelGateway(mode="live", store=store)
    return RunContext(mode="live", gateway=gw, case_dir=final_case_dir, data_dir=data_dir)


def promote_golden_runs(case_dir: Path, data_dir: Path) -> int:
    """Copy run dirs from data_dir/runs/<case_id> to case_dir/runs/golden.

    Returns the number of runs promoted.
    """
    runs_src = data_dir / "runs" / case_dir.name
    golden_dir = case_dir / "runs" / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)

    if not runs_src.exists():
        print(f"  No runs to promote from {runs_src}")
        return 0

    promoted = 0
    skipped = 0
    for run_dir in sorted(runs_src.iterdir()):
        if not run_dir.is_dir():
            continue
        dst = golden_dir / run_dir.name
        if dst.exists():
            skipped += 1
            continue
        shutil.copytree(run_dir, dst)
        promoted += 1

    print(f"  Promoted {promoted} new runs, skipped {skipped} already present")
    return promoted


def clean_duplicate_claims(case_dir: Path) -> int:
    """Find and reject duplicate/normalised-identical claims via apply_review.

    'taller than wide' and 'taller-than-wide' are the known duplicate (WI-2.1).
    Returns number of claims rejected.
    """
    from track_a import api as track_a_api

    handoff = track_a_api.load_case(case_dir)
    claims = handoff.package.claims

    def normalize(s: str) -> str:
        return re.sub(r"[-_]+", " ", s.lower().strip())

    seen: dict[str, str] = {}   # normalized_statement -> first_claim_id
    to_reject: list[str] = []

    for claim in claims:
        norm = normalize(claim.statement)
        if norm in seen:
            print(f"  Duplicate found: '{claim.statement}' = '{seen[norm]}'")
            to_reject.append(claim.claim_id)
        else:
            seen[norm] = claim.claim_id

    rejected = 0
    for claim_id in to_reject:
        try:
            track_a_api.apply_review(case_dir, {
                "action": "reject_claim",
                "claim_id": claim_id,
                "reviewer": "anveshan-team",
                "note": "Duplicate property statement removed (WI-2.1 deduplication pass)",
            })
            print(f"  Rejected duplicate claim: {claim_id}")
            rejected += 1
        except Exception as exc:
            print(f"  WARNING: could not reject {claim_id}: {exc}")

    if rejected == 0:
        print("  No duplicate claims found")
    return rejected


def _ensure_source_for_build(case_dir: Path, source_path: Path) -> None:
    """Ensure the source video is at the path specified in source.json (for the build)."""
    from tracks.common.casedata import load_sources

    try:
        reg = load_sources(case_dir)
        for src in reg.sources:
            if src.path and src.used_by_system:
                media_path = case_dir / src.path
                if not media_path.exists() and source_path.exists():
                    media_path.parent.mkdir(parents=True, exist_ok=True)
                    # Don't copy the 25 MB file - symlink via cache dir
                    cache_name = Path(CACHE_PATH).name
                    cache_path = case_dir / "media" / "cache" / cache_name
                    if cache_path.exists() and str(src.path).startswith("media/cache"):
                        pass  # already accessible via cache
                    elif source_path.exists():
                        shutil.copyfile(source_path, media_path)
                        print(f"  Staged source at {src.path}")
    except Exception as exc:
        print(f"  WARNING: _ensure_source_for_build: {exc}")


def run_build(args: argparse.Namespace, data_dir: Path) -> str:
    """Run the full compose pipeline. Returns the original (slug~hash) case_id."""
    from tracks.common.runtime import RunContext
    from track_a import api as track_a_api
    from track_a import composer

    source_path = Path(args.source)
    if not source_path.is_absolute():
        source_path = ROOT / source_path

    if not source_path.exists():
        print(f"ERROR: source not found: {source_path}")
        print("Run: python tools/fetch_media.py origami")
        sys.exit(1)

    mime = "video/ogg"

    print(f"Source: {source_path}")
    print(f"Title:  {args.title}")
    print(f"Data dir: {data_dir}")
    print(f"Live calls budget: 40")

    calls_start = count_all_runs(data_dir)

    # -------------------------------------------------------------------------
    # Step 1: RunContext for draft creation
    # -------------------------------------------------------------------------
    print("\n[Step 1] Creating RunContext (live mode)...")
    ctx = RunContext.create(data_dir, data_dir, "live")

    # -------------------------------------------------------------------------
    # Step 2: Create draft (analyze the source video)
    # -------------------------------------------------------------------------
    print("[Step 2] Creating draft (analyze source video — this makes live calls)...")
    draft = composer.create_draft(
        data_dir, source_path, mime, ctx,
        title_hint="Paper crane",
        description=args.description,
        rights_confirmed=True,
    )
    calls_after_2 = count_all_runs(data_dir)
    print(f"  Draft ID: {draft.draft_id}")
    print(f"  Calls used so far: {calls_after_2 - calls_start}")

    # -------------------------------------------------------------------------
    # Step 3: Print summary and check
    # -------------------------------------------------------------------------
    print_proposal_summary(draft)
    if draft.refused:
        print("ERROR: Pipeline refused the source. Stopping.")
        sys.exit(1)
    if draft.proposal is None:
        print("ERROR: No proposal generated. Stopping.")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Step 4: Create case from draft with edits
    # -------------------------------------------------------------------------
    print("[Step 4] Creating case from draft...")
    edits = {
        "title": args.title,
        "skill_summary": "Learn to fold a paper crane by following the step-by-step video demonstration.",
    }
    tmp_cases_root = data_dir / "_cases_tmp"
    tmp_cases_root.mkdir(parents=True, exist_ok=True)

    case_dir = composer.create_case_from_draft(
        tmp_cases_root, data_dir, draft.draft_id, edits
    )
    original_case_id = case_dir.name
    print(f"  Case ID (composed): {original_case_id}")
    print(f"  Case dir: {case_dir}")

    # -------------------------------------------------------------------------
    # Step 5: Build case (first pass; runs stored under data_dir/runs/<orig_id>)
    # -------------------------------------------------------------------------
    print("[Step 5] Building case (first pass)...")
    ctx5 = RunContext.create(case_dir, data_dir, "live")
    handoff5 = track_a_api.build_case(case_dir, ctx5)
    calls_after_5 = count_all_runs(data_dir)
    print(f"  Built: {handoff5.case_id}, versions={handoff5.versions}")
    print(f"  Calls used so far: {calls_after_5 - calls_start}")

    # -------------------------------------------------------------------------
    # Step 6: Copy to final location, rewrite case_id references
    # -------------------------------------------------------------------------
    print(f"\n[Step 6] Copying to {FINAL_CASE_DIR}...")
    if FINAL_CASE_DIR.exists():
        print(f"  Removing existing {FINAL_CASE_DIR.name}")
        shutil.rmtree(FINAL_CASE_DIR)

    # Copy (excluding the .npy embedding files if any are large — they'll be rebuilt)
    shutil.copytree(case_dir, FINAL_CASE_DIR)

    # 6a: Rewrite case_id in JSON files
    print("  Rewriting case_id references in JSON files...")
    rewrite_case_id_in_jsons(original_case_id, FINAL_CASE_ID, FINAL_CASE_DIR)

    # 6b: Delete service metadata files that don't belong in a committed pack
    for extra in [".owners.json", ".library.json"]:
        p = FINAL_CASE_DIR / extra
        if p.exists():
            p.unlink()
            print(f"  Deleted {extra}")

    # 6c: Replace the upload source.json with a canonical one (URL + sha256)
    create_canonical_source_json(FINAL_CASE_DIR, source_path)

    # 6d: Remove the large upload copy of the video
    source_subdir = FINAL_CASE_DIR / "source"
    for f in list(source_subdir.iterdir()):
        if f.is_file() and f.suffix != ".json" and f.stat().st_size > MAX_COMMITTED_BYTES:
            print(f"  Removing large upload copy: {f.name} ({f.stat().st_size // 1024} KB)")
            f.unlink()

    # 6e: Put the video in the cache dir (not committed; for local test/rebuild)
    copy_media_cache(FINAL_CASE_DIR)

    # -------------------------------------------------------------------------
    # Step 7: Rebuild in place (run keys are now against the final path)
    # -------------------------------------------------------------------------
    print(f"\n[Step 7] Rebuilding in place at {FINAL_CASE_DIR.name}...")
    _ensure_source_for_build(FINAL_CASE_DIR, source_path)
    ctx7 = make_ctx_with_cache(FINAL_CASE_DIR, data_dir, original_case_id)
    handoff7 = track_a_api.build_case(FINAL_CASE_DIR, ctx7)
    calls_after_7 = count_all_runs(data_dir)
    new_calls_7 = calls_after_7 - calls_after_5
    print(f"  Rebuilt: {handoff7.case_id}, versions={handoff7.versions}")
    print(f"  New calls in step 7 (should be ~0 from live cache): {new_calls_7}")
    print(f"  Total calls so far: {calls_after_7 - calls_start}")

    # -------------------------------------------------------------------------
    # Step 8: Promote golden runs
    # -------------------------------------------------------------------------
    print("\n[Step 8] Promoting golden runs...")
    promoted = promote_golden_runs(FINAL_CASE_DIR, data_dir)

    total_calls = count_all_runs(data_dir) - calls_start
    print(f"\n=== BUILD COMPLETE ===")
    print(f"Case: {FINAL_CASE_ID}")
    print(f"Review status: {handoff7.review_status}")
    print(f"Warnings: {handoff7.warnings[:3]}")
    print(f"Total live calls: {total_calls}")

    return original_case_id


def main() -> int:
    ap = argparse.ArgumentParser(description="Build origami-crane featured skill via universal pipeline")
    ap.add_argument("--source", default="tracks/cases/origami/media/cache/src.origami.demo.v1.ogv")
    ap.add_argument("--case-id", default="origami-crane")
    ap.add_argument(
        "--title", default="Fold a paper crane: the first folds",
        help="Title for the case (keep honest: name only the folds actually covered)",
    )
    ap.add_argument(
        "--description",
        default="Fold a square of paper into a crane, following the demonstration step by step.",
    )
    ap.add_argument("--data-dir", default="var/k9-compose")
    ap.add_argument("--live", action="store_true",
                    help="Actually make live model calls (required to build)")
    ap.add_argument("--clean-only", action="store_true",
                    help="Run only the duplicate-claim cleanup on an already-built case")
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    if not args.live and not args.clean_only:
        print("DRY RUN — pass --live to make model calls and build the case.")
        print(f"Source: {ROOT / args.source}")
        print(f"Target: {FINAL_CASE_DIR}")
        return 0

    calls_before = count_all_runs(data_dir)

    if args.clean_only:
        if not FINAL_CASE_DIR.exists():
            print(f"ERROR: {FINAL_CASE_DIR} does not exist; run without --clean-only first")
            return 1
        print("\n=== CLEANING DUPLICATE CLAIMS ===")
        n = clean_duplicate_claims(FINAL_CASE_DIR)
        print(f"Rejected {n} duplicate claims")
    else:
        original_id = run_build(args, data_dir)
        print(f"\n=== CLEANING DUPLICATE CLAIMS ===")
        n = clean_duplicate_claims(FINAL_CASE_DIR)
        print(f"Rejected {n} duplicate claims")

    total_calls = count_all_runs(data_dir) - calls_before
    print(f"\nTotal new live calls: {total_calls} / 40 budget")
    if total_calls > 40:
        print("WARNING: Exceeded budget of 40 calls!")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
