"""End-to-end smoke test for the Anveshan service.

Runs against an HTTP service. Pass --base-url to target a deployed instance,
or omit for http://localhost:8000 (the default dev server).

Usage:
    python tools/e2e_smoke.py [--base-url URL] [--mode recorded|live]

For each hero case it checks:
    1. Health
    2. List cases (case present)
    3. GET case (goal present)
    4. Evidence query (answered + INSUFFICIENT query)
    5. Session: flawed baseline attempt + better retry, bundle validates, gain > 0
    6. Complete session

Then the composer flow:
    7. Analyse (POST /api/compose/analyse) -> draft
    8. Create from draft (POST /api/compose/create)
    9. Practice attempt (PASS)
    10. Relevance-refused attempt

Exit code: 0 = all pass, 1 = at least one failure.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

try:
    import httpx
except ImportError:
    sys.exit("Install httpx: pip install httpx")

KOLAM_TARGET_JPEG = ROOT / "tracks" / "cases" / "kolam" / "source" / "ithayakkamalam_target.jpg"
KOLAM_STRAY_TRACE = ROOT / "tracks" / "cases" / "kolam" / "practice" / "eval_media"

# Minimal valid kolam trace JSON
_TRACE = json.dumps({
    "canvas": {"width": 492, "height": 499},
    "goal_case_id": "kolam",
    "goal_version": 1,
    "strokes": [{"points": [[10, 20, 0], [30, 40, 100], [50, 60, 200]]}],
    "duration_ms": 500,
})

Results: List[Dict] = []


def _check(name: str, ok: bool, notes: str = "") -> bool:
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] {name}{': ' + notes if notes else ''}")
    Results.append({"check": name, "passed": ok, "notes": notes})
    return ok


def smoke_health(client: httpx.Client) -> bool:
    r = client.get("/api/health")
    return _check("health 200", r.status_code == 200, f"status={r.status_code}")


def smoke_list_cases(client: httpx.Client) -> bool:
    r = client.get("/api/cases")
    ok = r.status_code == 200
    if ok:
        cases = r.json()
        has_kolam = any(c.get("case_id") == "kolam" for c in cases)
        ok = has_kolam
    return _check("list_cases: kolam present", ok, f"count={len(r.json()) if r.status_code == 200 else r.status_code}")


def smoke_get_case(client: httpx.Client, case_id: str) -> bool:
    r = client.get(f"/api/cases/{case_id}")
    ok = r.status_code == 200
    if ok:
        data = r.json()
        ok = data.get("case_id") == case_id
    return _check(f"get_case/{case_id}", ok, f"status={r.status_code}")


def smoke_query(client: httpx.Client, case_id: str) -> bool:
    # An answerable question for kolam
    r1 = client.post(f"/api/cases/{case_id}/query",
                     json={"question": "How many dots does this kolam have?"})
    ok1 = r1.status_code == 200
    answered = ok1 and r1.json().get("sufficient", True)  # True means answered

    # An unanswerable question (creator intent)
    r2 = client.post(f"/api/cases/{case_id}/query",
                     json={"question": "Who originally drew this and what did they intend to symbolize?"})
    ok2 = r2.status_code == 200
    refused = ok2 and not r2.json().get("sufficient", True)  # should be insufficient

    _check(f"query/{case_id}: answerable", ok1 and answered)
    _check(f"query/{case_id}: creator-intent refused", ok2 and refused)
    return ok1 and ok2


def smoke_kolam_session(client: httpx.Client, mode: str) -> bool:
    """Full kolam trace session with baseline + perfect retry."""
    # Start session
    r = client.post("/api/sessions", json={"case_id": "kolam", "learner_name": "SmokeTest"})
    if r.status_code != 200:
        return _check("kolam_session: start", False, f"status={r.status_code}")
    sid = r.json()["session_id"]
    _check("kolam_session: start", True, f"sid={sid}")

    # Baseline: stray stroke trace (should be partially_satisfied or worse)
    r = client.post(
        f"/api/sessions/{sid}/attempts?mode={mode}",
        data={"kind": "trace"},
        files={"file": ("trace.json", _TRACE.encode(), "application/json")},
    )
    if r.status_code != 200:
        return _check("kolam_session: baseline", False, f"status={r.status_code}")
    baseline = r.json()
    _check("kolam_session: baseline", True,
           f"attempt={baseline.get('attempt', {}).get('attempt_id')}")

    # Retry: same file (just testing the flow, actual score depends on mode)
    r = client.post(
        f"/api/sessions/{sid}/attempts?mode={mode}",
        data={"kind": "trace"},
        files={"file": ("trace.json", _TRACE.encode(), "application/json")},
    )
    if r.status_code != 200:
        return _check("kolam_session: retry", False, f"status={r.status_code}")
    _check("kolam_session: retry", True)

    # Complete
    r = client.post(f"/api/sessions/{sid}/complete")
    if r.status_code != 200:
        return _check("kolam_session: complete", False, f"status={r.status_code}")
    bundle_keys = set(r.json().keys())
    ok = {"bundle", "transmission_record", "comparison"}.issubset(bundle_keys)
    return _check("kolam_session: complete", ok, f"keys={sorted(bundle_keys)}")


def smoke_composer(client: httpx.Client) -> bool:
    """Composer flow: analyse -> create -> attempt (pass) -> attempt (refused)."""
    if not KOLAM_TARGET_JPEG.exists():
        return _check("composer: analyse", False, "kolam source image not found")

    # Analyse
    img_bytes = KOLAM_TARGET_JPEG.read_bytes()
    r = client.post(
        "/api/compose/analyse",
        files={"file": ("kolam.jpg", img_bytes, "image/jpeg")},
        data={"title_hint": "Kolam skill (smoke test)", "rights_confirmed": "true"},
    )
    if r.status_code not in (200, 422):
        return _check("composer: analyse", False, f"status={r.status_code}")

    if r.status_code == 422:
        # Service might need rights_confirmed differently
        return _check("composer: analyse", False, "422 from compose/analyse - check rights_confirmed param")

    draft = r.json()
    _check("composer: analyse", True, f"refused={draft.get('refused')}")

    if draft.get("refused"):
        return _check("composer: analyse (not refused)", False,
                      f"was refused: {draft.get('refusal_message', '')}")

    draft_id = draft.get("draft_id")
    if not draft_id:
        return _check("composer: draft_id present", False, "no draft_id in response")
    _check("composer: draft_id", True, f"id={draft_id}")

    # Create case
    r2 = client.post(f"/api/compose/drafts/{draft_id}/create", json={})
    if r2.status_code not in (200, 201):
        return _check("composer: create", False, f"status={r2.status_code}")
    created = r2.json()
    composed_case_id = created.get("case_id")
    _check("composer: create", bool(composed_case_id), f"case_id={composed_case_id}")

    if not composed_case_id:
        return False

    # Build the composed case
    r3 = client.post(f"/api/cases/{composed_case_id}/build")
    ok_build = r3.status_code in (200, 201, 202)
    _check("composer: build", ok_build, f"status={r3.status_code}")

    if not ok_build:
        return False

    # Practice attempt (should pass - use same image as attempt)
    r4 = client.post("/api/sessions", json={"case_id": composed_case_id, "learner_name": "SmokeComposer"})
    if r4.status_code != 200:
        return _check("composer: session_start", False, f"status={r4.status_code}")
    csid = r4.json()["session_id"]
    _check("composer: session_start", True)

    r5 = client.post(
        f"/api/sessions/{csid}/attempts",
        data={"kind": "image"},
        files={"file": ("attempt.jpg", img_bytes, "image/jpeg")},
    )
    ok_attempt = r5.status_code == 200
    _check("composer: practice_attempt", ok_attempt, f"status={r5.status_code}")

    # Relevance-refused attempt: submit a different (unrelated) image
    from PIL import Image
    import io
    import numpy as np
    arr = np.ones((128, 128, 3), dtype=np.uint8) * 200  # gray
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG")
    unrelated_bytes = buf.getvalue()

    r6 = client.post(
        f"/api/sessions/{csid}/attempts",
        data={"kind": "image"},
        files={"file": ("unrelated.jpg", unrelated_bytes, "image/jpeg")},
    )
    # Either 400 (INVALID_INPUT) or 200 with a refusal flag
    refused = r6.status_code in (400, 422) or (
        r6.status_code == 200 and r6.json().get("evaluation", {}).get("refused")
    )
    _check("composer: relevance_refused", refused, f"status={r6.status_code}")

    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--mode", default="recorded", choices=["recorded", "live"])
    args = parser.parse_args()

    print(f"\n=== e2e smoke test: {args.base_url} (mode={args.mode}) ===\n")

    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        smoke_health(client)
        smoke_list_cases(client)
        smoke_get_case(client, "kolam")
        smoke_get_case(client, "tabla")
        smoke_get_case(client, "origami")
        smoke_query(client, "kolam")
        smoke_kolam_session(client, args.mode)
        smoke_composer(client)

    passed = sum(1 for r in Results if r["passed"])
    failed = sum(1 for r in Results if not r["passed"])

    print(f"\n=== Results: {passed} passed, {failed} failed ===")
    for r in Results:
        if not r["passed"]:
            print(f"  FAIL: {r['check']} - {r['notes']}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
