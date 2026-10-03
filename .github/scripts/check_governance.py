from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

required = [
    "AGENTS.md",
    "docs/status/NOW.md",
    "docs/status/DECISIONS.md",
    "docs/status/project.yaml",
    ".github/pull_request_template.md",
    ".github/CODEOWNERS",
]

missing = [p for p in required if not (ROOT / p).exists()]
if missing:
    print("Missing governance files:")
    print("\n".join(missing))
    sys.exit(1)

agents = (ROOT / "AGENTS.md").read_text()
required_rules = [
    "Issue before implementation.",
    "One issue, one outcome.",
    "No free scope.",
    "Research is not authorization.",
    "Capability is not scope.",
    "No speculative architecture.",
    "No unrelated edits.",
    "Do not bypass governance.",
]
missing_rules = [r for r in required_rules if r not in agents]
if missing_rules:
    print("AGENTS.md is missing mandatory rules:")
    print("\n".join(missing_rules))
    sys.exit(1)

project = (ROOT / "docs/status/project.yaml").read_text()
for token in ("implementation_requires_issue", "pull_request_requires_issue", "scope_change_requires_trade"):
    if token not in project:
        print(f"project.yaml missing governance rule: {token}")
        sys.exit(1)

print("Governance invariants: PASS")
