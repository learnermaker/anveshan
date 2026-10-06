"""Dev CLI over track_a.api (thin wrapper; no logic of its own).

    python tracks/track-a/tools/run_pipeline.py build  <case_dir> [--mode live|recorded] [--source-id ID]
    python tracks/track-a/tools/run_pipeline.py show   <case_dir>
    python tracks/track-a/tools/run_pipeline.py query  <case_dir> "<question>" [--mode live|recorded]
    python tracks/track-a/tools/run_pipeline.py review <case_dir> approve|revise_claim|reject_claim|reject_package
                                                     --reviewer NAME [--note T] [--claim-id CLM-01] [--new-statement T]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in (ROOT, ROOT / "tracks" / "track-a" / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common.models import AnveshanFailure, load_dotenv  # noqa: E402
from tracks.common.runtime import RunContext  # noqa: E402

from track_a import api  # noqa: E402


def _ctx(case_dir: Path, mode: str) -> RunContext:
    data_dir = Path(os.environ.get("ANVESHAN_DATA_DIR", str(ROOT / "var")))
    return RunContext.create(case_dir, data_dir, mode)  # type: ignore[arg-type]


def main(argv: list[str] | None = None) -> int:
    load_dotenv(ROOT / ".env")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    default_mode = os.environ.get("ANVESHAN_MODE", "recorded")

    b = sub.add_parser("build")
    b.add_argument("case_dir", type=Path)
    b.add_argument("--mode", choices=["live", "recorded"], default=default_mode)
    b.add_argument("--source-id")

    s = sub.add_parser("show")
    s.add_argument("case_dir", type=Path)

    q = sub.add_parser("query")
    q.add_argument("case_dir", type=Path)
    q.add_argument("question")
    q.add_argument("--mode", choices=["live", "recorded"], default=default_mode)

    r = sub.add_parser("review")
    r.add_argument("case_dir", type=Path)
    r.add_argument("action", choices=["approve", "revise_claim", "reject_claim", "reject_package"])
    r.add_argument("--reviewer", required=True)
    r.add_argument("--note", default="")
    r.add_argument("--claim-id")
    r.add_argument("--new-statement")

    a = ap.parse_args(argv)
    try:
        if a.cmd == "build":
            out = api.build_case(a.case_dir, _ctx(a.case_dir, a.mode), source_id=a.source_id).to_view()
        elif a.cmd == "show":
            out = api.load_case(a.case_dir).to_view()
        elif a.cmd == "query":
            out = api.answer_query(a.case_dir, a.question, _ctx(a.case_dir, a.mode))
        else:
            action = {"action": a.action, "reviewer": a.reviewer, "note": a.note}
            if a.claim_id:
                action["claim_id"] = a.claim_id
            if a.new_statement:
                action["new_statement"] = a.new_statement
            out = api.apply_review(a.case_dir, action).to_view()
    except AnveshanFailure as exc:
        print(json.dumps({"error": {"category": exc.category.value, "message": exc.message, "details": exc.details}}, indent=2, default=str), file=sys.stderr)
        return 1
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
