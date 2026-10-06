from __future__ import annotations

from check_pr_contract import validate_pr_body


VALID_BODY = """
## Outcome
One bounded outcome.

Closes #34

## Scope
**Included**
- The requested change.

**Not included**
- Unrelated cleanup.

## Validation
- Tests: pytest
- Manual / benchmark evidence: none
- AI changes: none
"""


def test_valid_pr_body():
    assert validate_pr_body(VALID_BODY) == []


def test_missing_required_sections():
    violations = validate_pr_body("## Outcome\n\nCloses #34\n")
    assert "scope included section" in violations
    assert "scope excluded section" in violations
    assert "validation section" in violations


def test_issue_linkage_is_required_and_unique():
    assert "issue linkage" in validate_pr_body("## Validation\n")
    assert "exactly one issue linkage" in validate_pr_body(
        "Closes #34\nCloses #35\n## Validation\n**Included**\n**Not included**"
    )


def test_other_headings_do_not_satisfy_scope_contract():
    body = "Closes #34\n## Scope\nIncluded\nNot included\n## Validation\n"
    violations = validate_pr_body(body)
    assert "scope included section" in violations
    assert "scope excluded section" in violations
