"""
smoke_deployed.py — WS1 deployment gate (technical-panel plan §4).

Usage:
  python tools/smoke_deployed.py <base_url> [options]

Options:
  --steward-code-env ENV  Name of the env var holding the steward code (never the code itself).
  --skip-live             Skip the isolation live-mode check.
  --check-429             Enable rate-limit hammer test.
  --insecure              Disable TLS verification (for local testing on this network).

Exits 1 if any check fails (FAIL); exits 0 when all are PASS or WARN.
Never prints secrets.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional
import httpx

TIMEOUT = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class Result:
    def __init__(self, name: str, status: str, detail: str = "") -> None:
        self.name = name
        self.status = status  # PASS | FAIL | WARN | SKIP
        self.detail = detail

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.status:6s}  {self.name}  {self.detail}"


results: list[Result] = []


def add(name: str, status: str, detail: str = "") -> None:
    results.append(Result(name, status, detail))
    icon = {"PASS": "[+]", "FAIL": "[!]", "WARN": "[W]", "SKIP": "[ ]"}.get(status, "[?]")
    line = f"  {icon} [{status}] {name}{': ' + detail if detail else ''}"
    print(line)


def check(name: str, condition: bool, detail: str = "", warn_only: bool = False) -> bool:
    if condition:
        add(name, "PASS", detail)
        return True
    add(name, "WARN" if warn_only else "FAIL", detail)
    return condition


def is_localhost(url: str) -> bool:
    return "localhost" in url or "127.0.0.1" in url


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_health(client: httpx.Client, base: str, deployed: bool) -> None:
    """Check 1: GET /api/health"""
    print("\n[1] Health")
    try:
        r = client.get(f"{base}/api/health", timeout=TIMEOUT)
        check("health 200", r.status_code == 200, f"HTTP {r.status_code}")
        if r.status_code != 200:
            return
        j = r.json()
        check("health.ok", j.get("ok") is True)
        # steward_enabled and data_ttl_hours are added by K9-P1; tolerate absence
        has_steward = "steward_enabled" in j
        has_ttl = "data_ttl_hours" in j
        if has_steward and has_ttl:
            add("health has steward_enabled+data_ttl_hours", "PASS")
        else:
            missing = [k for k in ("steward_enabled", "data_ttl_hours") if k not in j]
            add("health has steward_enabled+data_ttl_hours", "WARN",
                f"needs P1: missing keys: {missing}")
        if deployed:
            check("mode_override false on deployed", j.get("mode_override") is False,
                  f"got {j.get('mode_override')!r}")
            check("curated_review_open false on deployed", j.get("curated_review_open") is False,
                  f"got {j.get('curated_review_open')!r}")
    except httpx.RequestError as exc:
        add("health reachable", "FAIL", str(exc))


def check_cases(client: httpx.Client, base: str) -> list[str]:
    """Check 2: GET /api/cases. Returns list of case_ids with samples to probe."""
    print("\n[2] Cases")
    cases_with_samples: list[str] = []
    try:
        r = client.get(f"{base}/api/cases", timeout=TIMEOUT)
        check("cases 200", r.status_code == 200, f"HTTP {r.status_code}")
        if r.status_code != 200:
            return cases_with_samples
        items = r.json()
        ids = [x.get("case_id", "") for x in items]
        check("cases includes kolam", "kolam" in ids)
        check("cases includes tabla", "tabla" in ids)
        if "origami-crane" in ids:
            add("cases includes origami-crane", "PASS")
        else:
            add("cases includes origami-crane", "WARN", "needs K9-P5 to merge first")
        for item in items:
            cid = item.get("case_id", "")
            if not item.get("access"):
                # access field is added by K9-P1; tolerate absence before merge
                add(f"case {cid} has access", "WARN", "needs P1: access field not in case list yet")
            else:
                add(f"case {cid} has access", "PASS")
            cases_with_samples.append(cid)
    except httpx.RequestError as exc:
        add("cases reachable", "FAIL", str(exc))
    return cases_with_samples


def check_session_flow(client_a: httpx.Client, base: str, case_ids: list[str]) -> None:
    """Check 3: For each featured case with samples, run a session flow."""
    print("\n[3] Session flow (cases with samples)")
    featured = [c for c in case_ids if c in ("kolam", "tabla", "origami-crane")]
    for cid in featured:
        _probe_case_samples(client_a, base, cid)


def _probe_case_samples(client: httpx.Client, base: str, case_id: str) -> None:
    # needs P4 for /api/cases/{id}/samples
    prefix = f"session/{case_id}"
    try:
        r = client.get(f"{base}/api/cases/{case_id}/samples", timeout=TIMEOUT)
        if r.status_code == 404:
            add(f"{prefix} samples endpoint", "WARN", "needs P4: /api/cases/{id}/samples not found")
            return
        if r.status_code != 200:
            add(f"{prefix} samples 200", "FAIL", f"HTTP {r.status_code}")
            return
        samples = r.json()
        if not samples:
            add(f"{prefix} has samples", "WARN", "no samples — skipping session flow")
            return
        add(f"{prefix} has samples", "PASS", f"{len(samples)} samples")
        # start session as A
        sr = client.post(f"{base}/api/sessions",
                         json={"case_id": case_id, "learner_name": "smoke"},
                         timeout=TIMEOUT)
        check(f"{prefix} start session", sr.status_code == 200, f"HTTP {sr.status_code}")
        if sr.status_code != 200:
            return
        sid = sr.json().get("session_id")
        # submit good sample attempt
        ar = client.post(f"{base}/api/sessions/{sid}/attempts/sample/good", timeout=TIMEOUT)
        check(f"{prefix} good sample attempt", ar.status_code == 200,
              f"HTTP {ar.status_code}")
        if ar.status_code == 200:
            j = ar.json()
            check(f"{prefix} attempt has evaluation", "evaluation" in j or "result" in j,
                  f"keys: {list(j.keys())}")
        # submit flawed sample as retry
        fr = client.post(f"{base}/api/sessions/{sid}/attempts/sample/flawed", timeout=TIMEOUT)
        check(f"{prefix} flawed sample retry", fr.status_code == 200, f"HTTP {fr.status_code}")
        # complete
        cr = client.post(f"{base}/api/sessions/{sid}/complete", timeout=TIMEOUT)
        check(f"{prefix} complete", cr.status_code == 200, f"HTTP {cr.status_code}")
    except httpx.RequestError as exc:
        add(f"{prefix} reachable", "FAIL", str(exc))


def check_isolation(client_a: httpx.Client, client_b: httpx.Client,
                    base: str, skip_live: bool) -> None:
    """Check 4: Isolation."""
    print("\n[4] Isolation")
    try:
        r404 = client_b.get(f"{base}/api/cases/fake-case~aaaaaaaaaaaa", timeout=TIMEOUT)
        check("unknown case_id returns 404 for visitor B",
              r404.status_code == 404, f"HTTP {r404.status_code}")
        if not skip_live:
            # In live mode: POST /api/compose/sample/kolam-photo as A, then GET as B → 404.
            # We only do this when in live mode; skip if server is in recorded mode.
            health_r = client_a.get(f"{base}/api/health", timeout=TIMEOUT)
            mode = health_r.json().get("mode", "") if health_r.status_code == 200 else ""
            if mode != "live":
                add("draft isolation (live-mode only)", "SKIP",
                    f"server mode is {mode!r}; pass --skip-live to suppress")
            else:
                dr = client_a.post(f"{base}/api/compose/sample/kolam-photo", timeout=TIMEOUT)
                if dr.status_code == 200:
                    draft_id = dr.json().get("draft_id")
                    if draft_id:
                        gr = client_b.get(f"{base}/api/compose/{draft_id}", timeout=TIMEOUT)
                        check("B cannot read A's draft", gr.status_code == 404,
                              f"HTTP {gr.status_code}")
                    else:
                        add("draft isolation", "WARN", "no draft_id in response")
                else:
                    add("compose/sample endpoint", "WARN",
                        f"HTTP {dr.status_code} — needs P4/P5")
        else:
            add("draft isolation (--skip-live set)", "SKIP")
    except httpx.RequestError as exc:
        add("isolation reachable", "FAIL", str(exc))


def check_key(client: httpx.Client, base: str) -> None:
    """Check 5: POST /api/key/check with an invalid key → 400, body must not echo the key."""
    print("\n[5] Key check")
    fake_key = "AIzaInvalidInvalidInvalidInvalid123"
    try:
        r = client.post(
            f"{base}/api/key/check",
            headers={"X-Gemini-Api-Key": fake_key},
            timeout=TIMEOUT,
        )
        check("key/check returns 400", r.status_code == 400, f"HTTP {r.status_code}")
        body_text = r.text
        check("key not echoed in response", fake_key not in body_text,
              "(key found in body)" if fake_key in body_text else "")
    except httpx.RequestError as exc:
        add("key/check reachable", "FAIL", str(exc))


def check_steward(client_a: httpx.Client, base: str,
                  steward_code: Optional[str]) -> None:
    """Check 6: Steward endpoints (needs P1)."""
    print("\n[6] Steward (needs P1)")
    try:
        # Without code → 401 or 403 when not enabled
        r_no_code = client_a.post(f"{base}/api/steward/check", timeout=TIMEOUT)
        if r_no_code.status_code in (404, 405):
            add("steward/check without code", "WARN",
                "needs P1: /api/steward/check not found yet")
            return
        check("steward/check without code is 401 or 403",
              r_no_code.status_code in (401, 403),
              f"HTTP {r_no_code.status_code}")
        # With correct code (if available)
        if steward_code:
            r_with_code = client_a.post(
                f"{base}/api/steward/check",
                headers={"X-Steward-Token": steward_code},
                timeout=TIMEOUT,
            )
            check("steward/check with code is 200",
                  r_with_code.status_code == 200,
                  f"HTTP {r_with_code.status_code}")
        else:
            add("steward/check with code", "SKIP", "no steward code env var set")
        # GET /api/steward/usage
        r_usage = client_a.get(f"{base}/api/steward/usage", timeout=TIMEOUT)
        if r_usage.status_code in (401, 403):
            add("steward/usage accessible", "WARN",
                "needs auth — check steward code; needs P1")
        elif r_usage.status_code == 404:
            add("steward/usage", "WARN", "needs P1: not found yet")
        else:
            check("steward/usage 200", r_usage.status_code == 200,
                  f"HTTP {r_usage.status_code}")
            if r_usage.status_code == 200:
                j = r_usage.json()
                check("steward/usage has requests_by_class",
                      "requests_by_class" in j,
                      f"keys: {list(j.keys())}")
    except httpx.RequestError as exc:
        add("steward reachable", "FAIL", str(exc))


def check_rate_limit(client: httpx.Client, base: str) -> None:
    """Check 7 (opt-in): hammer steward/check with wrong code until 429."""
    print("\n[7] Rate limit hammer")
    MAX_TRIES = 15
    try:
        for i in range(1, MAX_TRIES + 1):
            r = client.post(
                f"{base}/api/steward/check",
                headers={"X-Steward-Token": "wrong-code"},
                timeout=TIMEOUT,
            )
            if r.status_code == 429:
                has_retry_after = "retry-after" in {k.lower() for k in r.headers}
                check("rate limit 429 reached", True, f"after {i} tries")
                check("Retry-After header present", has_retry_after)
                return
        add("rate limit 429 reached", "FAIL",
            f"did not get 429 in {MAX_TRIES} tries")
    except httpx.RequestError as exc:
        add("rate limit test reachable", "FAIL", str(exc))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("base_url", help="Base URL, e.g. http://localhost:8080")
    parser.add_argument("--steward-code-env", default="ANVESHAN_SMOKE_STEWARD_CODE",
                        help="Name of the env var that holds the steward code")
    parser.add_argument("--skip-live", action="store_true",
                        help="Skip the live-mode isolation check")
    parser.add_argument("--check-429", action="store_true",
                        help="Enable rate-limit hammer (check 7)")
    parser.add_argument("--insecure", action="store_true",
                        help="Disable TLS certificate verification (local testing only)")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    deployed = not is_localhost(base)
    steward_code: Optional[str] = os.environ.get(args.steward_code_env)
    verify_tls = not args.insecure

    print(f"Anveshan smoke test -> {base}")
    print(f"  deployed={deployed}  skip_live={args.skip_live}  insecure={args.insecure}")

    # Two separate cookie jars (visitor A and visitor B)
    cookies_a: dict = {}
    cookies_b: dict = {}
    client_a = httpx.Client(cookies=cookies_a, verify=verify_tls, follow_redirects=True)
    client_b = httpx.Client(cookies=cookies_b, verify=verify_tls, follow_redirects=True)

    try:
        check_health(client_a, base, deployed)
        case_ids = check_cases(client_a, base)
        check_session_flow(client_a, base, case_ids)
        check_isolation(client_a, client_b, base, args.skip_live)
        check_key(client_a, base)
        check_steward(client_a, base, steward_code)
        if args.check_429:
            check_rate_limit(client_a, base)
    finally:
        client_a.close()
        client_b.close()

    # Summary table
    print("\n" + "=" * 60)
    print(f"{'Check':<45} {'Status':<6}")
    print("-" * 60)
    for r in results:
        mark = {"PASS": "[+]", "FAIL": "[!]", "WARN": "[W]", "SKIP": "[ ]"}.get(r.status, "[?]")
        suffix = f" -- {r.detail}" if r.detail else ""
        print(f"  {mark} {r.name:<43}{suffix}")
    print("=" * 60)

    fails = [r for r in results if r.status == "FAIL"]
    warns = [r for r in results if r.status == "WARN"]
    print(f"\nResult: {len([r for r in results if r.status == 'PASS'])} PASS, "
          f"{len(warns)} WARN, {len(fails)} FAIL, "
          f"{len([r for r in results if r.status == 'SKIP'])} SKIP")

    if fails:
        print("\nFailed checks:")
        for r in fails:
            print(f"  [!] {r.name}: {r.detail}")
        sys.exit(1)
    print("\nAll checks passed or warned.")


if __name__ == "__main__":
    main()
