---
name: anveshan-verify
description: Run Anveshan's full local verification suite (governance, case packs, contract parity, all Python tests, benchmark smoke tests, frontend build, PR-body contract) before committing or opening a PR. Use whenever code, contracts, case packs, or docs governed by CI change.
---

# Anveshan verification

Run from the repository root. Use the project venv (`.venv/Scripts/python` on Windows, `.venv/bin/python` elsewhere). Stop at the first failure, fix it, and re-run.

```bash
PY=.venv/Scripts/python
$PY .github/scripts/check_governance.py
$PY .github/scripts/check_case_packs.py
$PY -m pytest -q .github/scripts/test_check_case_packs.py .github/scripts/test_check_pr_contract.py
$PY .github/scripts/check_contract_parity.py
$PY -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"
$PY -m compileall -q research/benchmarks/scripts
(cd app && npm run build)
```

Skip a test directory only if it does not exist yet. Never skip a failing check or weaken a test to pass.

## PR body
Before opening a PR, write the body to a temp file and validate it:

```bash
PR_BODY="$(cat /path/to/body.md)" $PY .github/scripts/check_pr_contract.py
```

The body must link exactly one issue (`Closes #N`), state included/excluded scope, validation evidence, AI/model/prompt changes, and whether NOW scope changed.

## Report
Report each step as pass/fail with the failing output. Do not claim "all green" unless every step ran.
