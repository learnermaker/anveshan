#!/usr/bin/env python3
"""Apply an expert review to a curated case knowledge package.

Usage:
    apply_expert_review.py <case_id> <review.json> [--cases-root tracks/cases] [--dry-run]

The review.json may be:
  1. A steward review-export from GET /api/steward/review-export/{case_id}:
     {"knowledge_package": {...}, "review_status": "...", ...}
  2. A hand-written action list:
     {"reviewer": "Name", "actions": [{"action": "revise_claim", ...}, ...]}

For the export form:
  - diff the exported claims against the current package and emit revise_claim for each changed
    statement and reject_claim for each claim missing from the export;
  - emit "approve" when the export's review_status is "approved" (or "revised" with no remaining changes).

Run .github/scripts/check_case_packs.py and commit after applying.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Put the repo root and track-a/src on sys.path
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_TRACK_A_SRC = _REPO_ROOT / "tracks" / "track-a" / "src"
if str(_TRACK_A_SRC) not in sys.path:
    sys.path.insert(0, str(_TRACK_A_SRC))


def _build_actions_from_export(export: dict, current_view: dict) -> list:
    """Diff an export payload against the current package and return a list of actions."""
    actions = []
    export_pkg = export.get("knowledge_package") or {}
    export_claims = {c["claim_id"]: c for c in (export_pkg.get("claims") or [])}
    current_pkg = current_view.get("package") or {}
    current_claims = {c["claim_id"]: c for c in (current_pkg.get("claims") or [])}

    reviewer = (export_pkg.get("expert_review") or {}).get("reviewer_name", "Expert")

    # Revise claims whose statement changed
    for cid, exp_claim in export_claims.items():
        cur_claim = current_claims.get(cid)
        if cur_claim and exp_claim.get("statement") != cur_claim.get("statement"):
            actions.append({
                "action": "revise_claim",
                "claim_id": cid,
                "new_statement": exp_claim["statement"],
            })

    # Reject claims missing from the export
    for cid in current_claims:
        if cid not in export_claims:
            actions.append({"action": "reject_claim", "claim_id": cid})

    # Approve when the exported review_status is approved/revised with no remaining changes
    review_status = export.get("review_status") or (export_pkg.get("expert_review") or {}).get("status", "pending")
    if review_status in ("approved", "revised") and not any(
        a["action"] in ("revise_claim", "reject_claim") for a in actions
    ):
        actions.append({"action": "approve", "reviewer": reviewer})
    elif review_status == "approved":
        actions.append({"action": "approve", "reviewer": reviewer})

    return actions


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("case_id", help="case id (e.g. 'kolam')")
    parser.add_argument("review_json", help="path to the review JSON file")
    parser.add_argument("--cases-root", default="tracks/cases", help="path to the cases root")
    parser.add_argument("--dry-run", action="store_true", help="print actions only, do not apply")
    args = parser.parse_args()

    cases_root = (_REPO_ROOT / args.cases_root).resolve()
    case_dir = cases_root / args.case_id
    if not case_dir.is_dir():
        print(f"ERROR: case directory not found: {case_dir}", file=sys.stderr)
        sys.exit(1)

    review_data = json.loads(Path(args.review_json).read_text(encoding="utf-8"))

    # Determine if this is an export form or hand-written form
    if "knowledge_package" in review_data:
        # Export form: diff against current package
        try:
            import track_a.api as api
            current_view = api.load_case(case_dir).to_view()
        except Exception as exc:
            print(f"ERROR: cannot load current case view: {exc}", file=sys.stderr)
            sys.exit(1)
        if not isinstance(current_view, dict):
            print("ERROR: load_case did not return a dict view", file=sys.stderr)
            sys.exit(1)
        actions = _build_actions_from_export(review_data, current_view)
    else:
        # Hand-written form
        actions = review_data.get("actions", [])

    if not actions:
        print("No actions to apply.")
        return

    print(f"Actions for {args.case_id}:")
    for action in actions:
        print(f"  {action}")

    if args.dry_run:
        print("\n[dry-run] No changes applied.")
        return

    try:
        import track_a.api as api
    except ImportError as exc:
        print(f"ERROR: cannot import track_a.api: {exc}", file=sys.stderr)
        sys.exit(1)

    for action in actions:
        try:
            result = api.apply_review(case_dir, action)
            if hasattr(result, "to_view"):
                view = result.to_view()
                pkg = (view or {}).get("package") or {}
                version = pkg.get("version")
                if version:
                    print(f"  Applied {action.get('action')} -> package version {version}")
                else:
                    print(f"  Applied {action.get('action')}")
            else:
                print(f"  Applied {action.get('action')}")
        except Exception as exc:
            print(f"ERROR applying {action.get('action')}: {exc}", file=sys.stderr)

    print("\nDone. Run .github/scripts/check_case_packs.py and commit the changes.")


if __name__ == "__main__":
    main()
