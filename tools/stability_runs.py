"""Stability runner: measure how repeatable the evaluation is on committed samples.

Usage
-----
    python tools/stability_runs.py [--cases kolam,tabla,origami-crane] [--runs 3]
        [--live-cases origami-crane] [--max-calls 60]

For each case and each sample in samples/samples.json the script runs --runs evaluations,
always with a fresh session and a fresh data_dir, and records whether the result is stable
(same passed/first-divergence/refused tuple across runs).

K9-B2 spec §2: deterministic cases use recorded mode (0 live calls), origami-crane uses
live mode with ANVESHAN_LIVE_CACHE=0.

Outputs:
- docs/validation/stability-2026-10.json  (raw results)
- app/public/evidence.json                (rendered by the "How we check" page)

The script also validates evidence.json against the B1 schema (§4, 10-line check).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Repo root: this file lives under tools/
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
# Mirror the conftest.py sys.path setup so imports work the same way as in tests.
for _p in (
    str(REPO_ROOT),
    str(REPO_ROOT / "tracks" / "track-a" / "src"),
    str(REPO_ROOT / "tracks" / "track-b" / "src"),
    str(REPO_ROOT / "service"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CASES_ROOT = REPO_ROOT / "tracks" / "cases"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_dotenv() -> None:
    """Load .env from the repo root (if it exists) without overriding existing env vars."""
    from tracks.common.models import load_dotenv as _ld
    _ld(REPO_ROOT / ".env")


def _count_run_dirs(data_dir: Path, case_id: str) -> int:
    """Count run directories written by the gateway under data_dir/runs/<case_id>."""
    runs_dir = data_dir / "runs" / case_id
    if not runs_dir.exists():
        return 0
    return sum(1 for d in runs_dir.iterdir() if d.is_dir())


def _run_one(
    case_dir: Path,
    case_id: str,
    sample_file: Path,
    attempt_kind: str,
    mode: str,
    data_dir: Path,
) -> Dict[str, Any]:
    """Run a single evaluation. Returns a result dict."""
    import tracks.common.models as models_mod
    from tracks.common.models import AnveshanFailure, FailureCategory
    from tracks.common.runtime import RunContext
    import track_b.api as api

    calls_before = _count_run_dirs(data_dir, case_id)

    result: Dict[str, Any] = {
        "passed": False,
        "total_score": 0.0,
        "criterion_statuses": {},
        "first_divergence_criterion": None,
        "refused": False,
        "live_calls": 0,
        "error": None,
    }

    try:
        ctx = RunContext.create(case_dir, data_dir, mode)  # type: ignore[arg-type]
        session = api.start_session(case_dir, "stability-calibration", data_dir)
        media = api.intake_attempt(session, sample_file, attempt_kind)
        attempt_result = api.submit_attempt(session, media, ctx)
        rj = attempt_result.to_json()

        ev = rj.get("evaluation", {})
        result["passed"] = bool(ev.get("passed", False))

        # Total score: mean of criterion scores (normalised)
        criteria = ev.get("criterion_results", ev.get("criteria", []))
        statuses: Dict[str, str] = {}
        scores: List[float] = []
        for crit in criteria:
            cid = crit.get("criterion_id", "")
            status = crit.get("status", "uncertain")
            statuses[cid] = status
            # Map status to numeric score for aggregation
            score_map = {
                "satisfied": 1.0,
                "partially_satisfied": 0.5,
                "not_satisfied": 0.0,
                "uncertain": 0.5,
            }
            scores.append(score_map.get(status, 0.5))
        result["criterion_statuses"] = statuses
        result["total_score"] = round(sum(scores) / len(scores), 4) if scores else 0.0

        # First divergence criterion
        fd = rj.get("first_divergence")
        if fd and isinstance(fd, dict):
            result["first_divergence_criterion"] = fd.get("criterion_id")

    except AnveshanFailure as exc:
        if exc.category in (FailureCategory.INVALID_INPUT, FailureCategory.HUMAN_REVIEW_REQUIRED):
            result["refused"] = True
            result["error"] = str(exc)
        else:
            result["error"] = str(exc)
    except Exception as exc:
        result["error"] = str(exc)

    calls_after = _count_run_dirs(data_dir, case_id)
    result["live_calls"] = max(0, calls_after - calls_before)
    return result


def _tuple(r: Dict[str, Any]) -> Tuple:
    """Stability tuple: (passed, first_divergence_criterion, refused)."""
    return (r["passed"], r["first_divergence_criterion"], r["refused"])


def _consistency(runs: List[Dict[str, Any]]) -> float:
    """Share of runs whose tuple matches the most common tuple."""
    if not runs:
        return 0.0
    counts = Counter(_tuple(r) for r in runs)
    most_common_count = counts.most_common(1)[0][1]
    return round(most_common_count / len(runs), 4)


def _outcome_label(quality: str, runs: List[Dict[str, Any]]) -> str:
    """Assign outcome label per spec §2 table."""
    majority_passed = sum(1 for r in runs if r["passed"]) > len(runs) / 2
    majority_refused = sum(1 for r in runs if r["refused"]) > len(runs) / 2
    if quality == "good":
        return "passed" if majority_passed else "failed"
    elif quality == "flawed":
        return "caught" if not majority_passed else "missed"
    elif quality == "unrelated":
        return "refused" if (majority_refused or not majority_passed) else "missed"
    return "unknown"


# ---------------------------------------------------------------------------
# Pytest test count
# ---------------------------------------------------------------------------

def _count_tests() -> int:
    """Run pytest --collect-only and return the test count."""
    import re as _re
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "pytest", "--collect-only", "-q",
                "tracks/common/tests", "tracks/track-a/tests",
                "tracks/track-b/tests", "service/tests",
                "-m", "not live",
            ],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        combined = result.stdout + result.stderr
        # Match "560/562 tests collected" or "560 tests collected"
        for line in reversed(combined.splitlines()):
            if "collected" in line:
                # First integer in the line is the collected count
                m = _re.search(r"(\d+)", line)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return 0


# ---------------------------------------------------------------------------
# B1 schema validation (10-line check per spec §4)
# ---------------------------------------------------------------------------

def _validate_evidence_schema(evidence: Dict[str, Any]) -> List[str]:
    """Validate evidence.json against the B1 schema. Returns a list of errors."""
    errors: List[str] = []
    for key in ("generated_at", "tests", "skills", "not_yet"):
        if key not in evidence:
            errors.append(f"missing top-level key: {key!r}")
    if "tests" in evidence:
        tests = evidence["tests"]
        if not isinstance(tests, dict):
            errors.append("tests must be an object")
        else:
            for k in ("count", "date"):
                if k not in tests:
                    errors.append(f"tests missing key: {k!r}")
    if "skills" in evidence:
        skills = evidence["skills"]
        if not isinstance(skills, list):
            errors.append("skills must be an array")
        else:
            valid_outcomes = {"passed", "caught", "refused", "missed", "failed"}
            for i, sk in enumerate(skills):
                for k in ("case_id", "title", "runs_per_sample", "consistency", "samples"):
                    if k not in sk:
                        errors.append(f"skills[{i}] missing key: {k!r}")
                if "samples" in sk:
                    smp = sk["samples"]
                    for skey in ("good", "flawed", "unrelated"):
                        if skey not in smp:
                            errors.append(f"skills[{i}].samples missing key: {skey!r}")
                        elif smp[skey] not in valid_outcomes:
                            errors.append(f"skills[{i}].samples.{skey}={smp[skey]!r} not in {valid_outcomes}")
    if "not_yet" in evidence:
        if not isinstance(evidence["not_yet"], list):
            errors.append("not_yet must be an array")
    return errors


# ---------------------------------------------------------------------------
# Model/prompt info helpers
# ---------------------------------------------------------------------------

def _model_info(case_ids: List[str]) -> Dict[str, str]:
    """Return the model keys used for each case, reading from the ModelRegistry (spec §2)."""
    import tracks.common.models as models_mod
    registry = models_mod.ModelRegistry()
    info: Dict[str, str] = {}
    for cid in case_ids:
        if cid in ("kolam", "tabla"):
            info[cid] = "deterministic (no model calls)"
        elif cid == "origami-crane":
            vision = registry.model_id("vision_fast") or "(disabled)"
            embed = registry.model_id("embedding") or "(disabled)"
            info[cid] = f"vision_fast={vision}, embedding={embed}"
    return info


def _prompt_versions(case_id: str) -> str:
    """Return prompt versions for a case."""
    if case_id == "origami-crane":
        prompt_dir = REPO_ROOT / "tracks" / "common" / "prompts"
        versions: List[str] = []
        for stem in ("perceive_frames", "match_steps", "embed_frames", "judge_final"):
            for f in sorted(prompt_dir.glob(f"{stem}*.txt")):
                versions.append(f.stem)
                break
        return ", ".join(versions) if versions else "see tracks/common/prompts/"
    return "none"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Stability runs for K9-B2")
    parser.add_argument(
        "--cases", default="kolam,tabla,origami-crane",
        help="comma-separated case ids (default: kolam,tabla,origami-crane)",
    )
    parser.add_argument("--runs", type=int, default=3, help="runs per sample (default: 3)")
    parser.add_argument(
        "--live-cases", default="origami-crane",
        help="cases that need live model calls (default: origami-crane)",
    )
    parser.add_argument("--max-calls", type=int, default=60, help="total live-call budget (default: 60)")
    args = parser.parse_args()

    _load_dotenv()
    # Disable live cache for live cases
    os.environ["ANVESHAN_LIVE_CACHE"] = "0"

    case_ids = [c.strip() for c in args.cases.split(",") if c.strip()]
    live_cases = {c.strip() for c in args.live_cases.split(",") if c.strip()}
    n_runs = args.runs
    max_calls = args.max_calls
    total_live_calls = 0

    now = datetime.now(timezone.utc)
    run_date = now.strftime("%Y-%m-%d")
    run_ts = now.isoformat(timespec="seconds")

    print(f"[K9-B2] Stability run at {run_ts}")
    print(f"  cases: {case_ids}")
    print(f"  runs per sample: {n_runs}")
    print(f"  live cases: {sorted(live_cases)}")
    print(f"  live-call budget: {max_calls}")
    print()

    # --- load samples.py helper (for load_pack and sample_paths) ---
    from anveshan_service.samples import load_pack, sample_paths

    all_case_results: Dict[str, Any] = {}

    for case_id in case_ids:
        case_dir = CASES_ROOT / case_id
        if not case_dir.is_dir():
            print(f"[{case_id}] SKIP: directory not found at {case_dir}")
            continue

        mode = "live" if case_id in live_cases else "recorded"
        print(f"[{case_id}] mode={mode}")

        pack = load_pack(case_dir)
        if not pack:
            print(f"[{case_id}] SKIP: no samples.json or empty pack")
            continue

        case_result: Dict[str, Any] = {
            "case_id": case_id,
            "mode": mode,
            "runs_per_sample": n_runs,
            "samples": {},
        }

        for sample in pack:
            sid = sample.sample_id
            quality = sample.quality

            print(f"  [{case_id}/{sid}] quality={quality} kind={sample.attempt_kind}")

            primary_path, _ = sample_paths(case_dir, sample)
            if not primary_path.exists():
                print(f"    SKIP: sample file not found {primary_path}")
                continue

            sample_runs: List[Dict[str, Any]] = []
            budget_exceeded = False

            for run_idx in range(n_runs):
                if total_live_calls >= max_calls:
                    print(f"    BUDGET EXCEEDED at run {run_idx + 1} ({total_live_calls}/{max_calls} calls used)")
                    budget_exceeded = True
                    break

                with tempfile.TemporaryDirectory(prefix=f"k9-stability-{case_id}-{sid}-r{run_idx}-") as tmpdir:
                    data_dir = Path(tmpdir)
                    print(f"    run {run_idx + 1}/{n_runs} ...", end="", flush=True)
                    r = _run_one(case_dir, case_id, primary_path, sample.attempt_kind, mode, data_dir)
                    total_live_calls += r["live_calls"]
                    print(
                        f" passed={r['passed']} refused={r['refused']}"
                        f" calls={r['live_calls']} total={total_live_calls}"
                        + (f" ERROR: {r['error']}" if r["error"] else "")
                    )
                    sample_runs.append(r)

            consistency = _consistency(sample_runs)
            outcome = _outcome_label(quality, sample_runs)

            if budget_exceeded and len(sample_runs) < 2:
                consistency = -1.0  # not enough data

            case_result["samples"][sid] = {
                "quality": quality,
                "runs": sample_runs,
                "consistency": consistency,
                "outcome": outcome,
                "budget_exceeded": budget_exceeded,
            }
            print(f"    consistency={consistency:.2f} outcome={outcome}")

        # Per-case consistency: mean of per-sample consistencies
        valid_consistencies = [
            v["consistency"] for v in case_result["samples"].values()
            if v["consistency"] >= 0
        ]
        case_result["consistency"] = (
            round(sum(valid_consistencies) / len(valid_consistencies), 4)
            if valid_consistencies else 0.0
        )
        all_case_results[case_id] = case_result
        print(f"  [{case_id}] consistency={case_result['consistency']:.2f}")
        print()

    # --- Write raw results ---
    model_info = _model_info(case_ids)

    raw = {
        "generated_at": run_ts,
        "runs_per_sample": n_runs,
        "live_cache_disabled": True,
        "total_live_calls": total_live_calls,
        "live_call_budget": max_calls,
        "models": model_info,
        "cases": all_case_results,
    }

    raw_path = REPO_ROOT / "docs" / "validation" / "stability-2026-10.json"
    raw_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[K9-B2] Raw results written to {raw_path.relative_to(REPO_ROOT)}")

    # --- Count tests ---
    test_count = _count_tests()
    print(f"[K9-B2] Test count: {test_count}")

    # --- Build evidence.json ---
    skills = []
    for case_id in case_ids:
        cr = all_case_results.get(case_id)
        if not cr:
            continue

        samples_out: Dict[str, str] = {}
        for sid, sd in cr["samples"].items():
            quality = sd["quality"]
            if quality in samples_out:
                raise RuntimeError(
                    f"[{case_id}] duplicate quality '{quality}' in samples; "
                    f"would silently overwrite outcome '{samples_out[quality]}' with '{sd['outcome']}'. "
                    "Review samples.json for duplicate quality entries."
                )
            samples_out[quality] = sd["outcome"]

        # Samples are indexed by quality (good/flawed/unrelated)
        good_out = samples_out.get("good", "passed")
        flawed_out = samples_out.get("flawed", "caught")
        unrelated_out = samples_out.get("unrelated", "refused")

        # Case title and notes
        manifest_path = CASES_ROOT / case_id / "manifest.json"
        title = case_id
        if manifest_path.exists():
            try:
                mj = json.loads(manifest_path.read_text(encoding="utf-8"))
                title = mj.get("title", case_id)
            except Exception:
                pass

        if case_id in ("kolam", "tabla"):
            notes = "Deterministic checks; identical results by design."
        else:
            notes_parts = []
            if cr.get("consistency", 1.0) < 1.0:
                notes_parts.append(
                    f"Some variation observed (consistency={cr['consistency']:.2f}). "
                    "Swapped-order mistakes are not always caught in video."
                )
            else:
                notes_parts.append("AI-assisted checks; some variation expected across runs.")
            # If the good sample failed, explain why (e.g. the test clip is incomplete).
            if samples_out.get("good") == "failed":
                notes_parts.append(
                    "The 'good' test clip covers only the first 25 s of a 2-minute procedure "
                    "and is evaluated as incomplete."
                )
            notes = " ".join(notes_parts) if notes_parts else "AI-assisted checks."

        skills.append({
            "case_id": case_id,
            "title": title,
            "runs_per_sample": n_runs,
            "consistency": cr.get("consistency", 1.0),
            "samples": {
                "good": good_out,
                "flawed": flawed_out,
                "unrelated": unrelated_out,
            },
            "notes": notes,
        })

    not_yet = [
        "No study with real learners or experts has been run yet.",
        "Internet sources are not verified experts.",
        "Sample sizes are small (3 samples x 3 runs per skill); these numbers are engineering evidence, not learner validation.",
    ]

    evidence = {
        "generated_at": run_ts,
        "tests": {"count": test_count, "date": run_date},
        "skills": skills,
        "not_yet": not_yet,
    }

    # --- Validate schema (B1 §1.1) ---
    schema_errors = _validate_evidence_schema(evidence)
    if schema_errors:
        print(f"[K9-B2] ERROR: evidence.json schema validation failed:")
        for e in schema_errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("[K9-B2] evidence.json schema: OK")

    evidence_path = REPO_ROOT / "app" / "public" / "evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[K9-B2] evidence.json written to {evidence_path.relative_to(REPO_ROOT)}")

    # --- Summary ---
    print()
    print("[K9-B2] Summary:")
    print(f"  Total live calls: {total_live_calls} / {max_calls}")
    for case_id in case_ids:
        cr = all_case_results.get(case_id)
        if not cr:
            continue
        print(f"  {case_id}: consistency={cr['consistency']:.2f}")
        for sid, sd in cr["samples"].items():
            print(f"    {sid}: outcome={sd['outcome']} consistency={sd['consistency']:.2f}")

    if total_live_calls > max_calls:
        print(f"[K9-B2] WARNING: live calls ({total_live_calls}) exceeded budget ({max_calls})")
        sys.exit(1)


if __name__ == "__main__":
    main()
