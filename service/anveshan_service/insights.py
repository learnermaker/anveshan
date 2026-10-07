"""Insights: per-skill event log and aggregated analytics.

Never stores names, raw session IDs or media. Uses hashed session IDs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from anveshan_service.settings import Settings

log = logging.getLogger("anveshan_service")

_SUGGESTION_R1 = "About {pct}% of learners miss \"{name}\" on their first try. Consider showing this step more slowly or describing it more clearly."
_SUGGESTION_R2 = "Most learners first go wrong at \"{name}\". Make sure the source shows this moment clearly."
_SUGGESTION_R3 = "Second tries rarely improve the check the feedback focuses on. The advice for it may need clearer wording."
_SUGGESTION_R4 = "Most learners pass on their first try. Consider a harder variation."

_lock = threading.Lock()


def _log_path(settings: Settings, case_id: str) -> Path:
    return settings.data_dir / "insights" / f"{case_id}.jsonl"


def _hash_session(session_id: str) -> str:
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:12]


def record_attempt(
    settings: Settings,
    case_id: str,
    session_id: str,
    result: dict,
    rubric_names: Dict[str, str],
    max_score: Optional[float],
    source: str = "learner",
) -> None:
    """Append an attempt event to the insights log. Never raises into the request."""
    try:
        _do_record_attempt(settings, case_id, session_id, result, rubric_names, max_score, source)
    except Exception:
        log.warning("insights.record_attempt failed (case=%s)", case_id)


def _do_record_attempt(
    settings: Settings,
    case_id: str,
    session_id: str,
    result: dict,
    rubric_names: Dict[str, str],
    max_score: Optional[float],
    source: str,
) -> None:
    attempt = (result.get("attempt") or {})
    evaluation = (result.get("evaluation") or {})
    first_div = result.get("first_divergence")

    attempt_type = attempt.get("attempt_type", "baseline")
    attempt_number = attempt.get("attempt_number", 1)
    score = evaluation.get("total_score")
    passed = evaluation.get("passed", False)
    criterion_results = evaluation.get("criterion_results") or {}

    # Build criteria dict
    criteria: Dict[str, Any] = {}
    for crid, cr in criterion_results.items():
        name = rubric_names.get(crid) or crid
        criteria[crid] = {"name": name, "status": cr.get("status", "unknown")}

    # Build first_wrong
    first_wrong = None
    if first_div:
        first_wrong = {
            "criterion_id": first_div.get("criterion_id"),
            "name": first_div.get("criterion_name") or rubric_names.get(first_div.get("criterion_id", ""), first_div.get("criterion_id", "")),
        }

    event: Dict[str, Any] = {
        "v": 1,
        "at": datetime.now(timezone.utc).isoformat(),
        "kind": "attempt",
        "s": _hash_session(session_id),
        "n": attempt_number,
        "type": attempt_type,
        "passed": bool(passed),
        "criteria": criteria,
        "first": first_wrong,
        "runtime": "RECORDED_LIVE",
        "source": source,
    }
    if score is not None:
        event["score"] = float(score)
    if max_score is not None:
        event["max"] = float(max_score)

    p = _log_path(settings, case_id)
    p.parent.mkdir(parents=True, exist_ok=True)

    with _lock:
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        # Cap the file if it exceeds max_events + 1000 lines
        max_ev = settings.insights_max_events
        _cap_if_needed(p, max_ev)


def record_completion(
    settings: Settings,
    case_id: str,
    session_id: str,
    session_result: dict,
) -> None:
    """Append a completion event. Never raises."""
    try:
        _do_record_completion(settings, case_id, session_id, session_result)
    except Exception:
        log.warning("insights.record_completion failed (case=%s)", case_id)


def _do_record_completion(
    settings: Settings,
    case_id: str,
    session_id: str,
    session_result: dict,
) -> None:
    comparison = (session_result.get("comparison") or {})
    gain = comparison.get("skill_gain_excluding_observability")
    targeted = comparison.get("targeted_change")

    event: Dict[str, Any] = {
        "v": 1,
        "at": datetime.now(timezone.utc).isoformat(),
        "kind": "complete",
        "s": _hash_session(session_id),
    }
    if gain is not None:
        event["gain"] = gain
    if targeted:
        event["targeted"] = {
            "criterion_id": targeted.get("criterion_id"),
            "improved": bool(targeted.get("improved")),
        }
    else:
        event["targeted"] = None

    p = _log_path(settings, case_id)
    p.parent.mkdir(parents=True, exist_ok=True)

    with _lock:
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")


def _cap_if_needed(p: Path, max_ev: int) -> None:
    """Rewrite the log to keep only the last max_ev lines when over max_ev + 1000."""
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
        if len(lines) > max_ev + 1000:
            kept = lines[-max_ev:]
            tmp = p.parent / f".insights_tmp_{os.getpid()}.jsonl"
            tmp.write_text("\n".join(kept) + "\n", encoding="utf-8")
            os.replace(tmp, p)
    except Exception:
        pass


def _read_events(p: Path) -> List[Dict[str, Any]]:
    """Read all events from the log file, skipping bad lines."""
    if not p.is_file():
        return []
    events = []
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    return events


def compute(settings: Settings, case_id: str) -> dict:
    """Compute the InsightsView for a case (deterministic)."""
    p = _log_path(settings, case_id)
    events = _read_events(p)

    attempt_events = [e for e in events if e.get("kind") == "attempt" and e.get("source") != "sample"]
    complete_events = [e for e in events if e.get("kind") == "complete"]

    learners = len({e["s"] for e in attempt_events})
    completed = len({e["s"] for e in complete_events})
    since = min((e["at"] for e in attempt_events), default=None)
    attempts = len(attempt_events)

    def _stats(evs: List[Dict]) -> dict:
        count = len(evs)
        if count == 0:
            return {"count": 0, "pass_rate": None, "avg_pct": None}
        pass_rate = sum(1 for e in evs if e.get("passed")) / count
        with_max = [e for e in evs if e.get("max") and float(e["max"]) > 0]
        avg_pct = sum(float(e.get("score", 0)) / float(e["max"]) for e in with_max) / len(with_max) if with_max else None
        return {"count": count, "pass_rate": pass_rate, "avg_pct": avg_pct}

    baseline_events = [e for e in attempt_events if e.get("type") == "baseline"]
    retry_events = [e for e in attempt_events if e.get("type") == "retry"]
    baseline_stats = _stats(baseline_events)
    retry_stats = _stats(retry_events)

    # first_wrong: baseline events with first != null, count by criterion_id
    first_wrong_counts: Dict[str, Dict] = {}
    for e in baseline_events:
        f = e.get("first")
        if f and f.get("criterion_id"):
            cid = f["criterion_id"]
            if cid not in first_wrong_counts:
                first_wrong_counts[cid] = {"criterion_id": cid, "name": f.get("name", cid), "count": 0}
            first_wrong_counts[cid]["count"] += 1
    total_first = sum(v["count"] for v in first_wrong_counts.values())
    first_wrong_list = []
    for v in first_wrong_counts.values():
        first_wrong_list.append({
            "criterion_id": v["criterion_id"],
            "name": v["name"],
            "count": v["count"],
            "share": v["count"] / total_first if total_first > 0 else 0.0,
        })
    first_wrong_list.sort(key=lambda x: (-x["count"], x["name"]))
    first_wrong_list = first_wrong_list[:5]

    # hardest: per criterion, miss_rate = share with status != "satisfied"
    crit_counts: Dict[str, Dict] = {}
    for e in baseline_events:
        for cid, cr in (e.get("criteria") or {}).items():
            if cid not in crit_counts:
                crit_counts[cid] = {"criterion_id": cid, "name": cr.get("name", cid), "n": 0, "misses": 0}
            crit_counts[cid]["n"] += 1
            if cr.get("status") != "satisfied":
                crit_counts[cid]["misses"] += 1
    hardest_list = []
    for v in crit_counts.values():
        if v["n"] >= 1:
            hardest_list.append({
                "criterion_id": v["criterion_id"],
                "name": v["name"],
                "miss_rate": v["misses"] / v["n"],
                "n": v["n"],
            })
    hardest_list.sort(key=lambda x: (-x["miss_rate"], x["name"]))
    hardest_list = hardest_list[:5]

    # feedback_helped
    targeted_complete = [e for e in complete_events if e.get("targeted")]
    improved = [e for e in targeted_complete if e["targeted"].get("improved")]
    fb_sessions = len(targeted_complete)
    fb_improved = len(improved)
    fb_rate = fb_improved / fb_sessions if fb_sessions > 0 else None

    enough_data = learners >= 3

    # Suggestions
    suggestions = []
    if hardest_list and hardest_list[0]["n"] >= 3 and hardest_list[0]["miss_rate"] >= 0.5:
        h = hardest_list[0]
        pct = int(round(h["miss_rate"] * 100))
        suggestions.append({
            "criterion_id": h["criterion_id"],
            "text": _SUGGESTION_R1.format(pct=pct, name=h["name"]),
            "rule": "R1",
        })
    if first_wrong_list and first_wrong_list[0]["count"] >= 3 and first_wrong_list[0]["share"] >= 0.4:
        fw = first_wrong_list[0]
        suggestions.append({
            "criterion_id": fw["criterion_id"],
            "text": _SUGGESTION_R2.format(name=fw["name"]),
            "rule": "R2",
        })
    if fb_sessions >= 3 and fb_rate is not None and fb_rate < 0.3:
        suggestions.append({
            "criterion_id": None,
            "text": _SUGGESTION_R3,
            "rule": "R3",
        })
    if learners >= 5 and baseline_stats["pass_rate"] is not None and baseline_stats["pass_rate"] >= 0.8:
        suggestions.append({
            "criterion_id": None,
            "text": _SUGGESTION_R4,
            "rule": "R4",
        })

    return {
        "case_id": case_id,
        "since": since,
        "learners": learners,
        "attempts": attempts,
        "completed": completed,
        "baseline": baseline_stats,
        "retry": retry_stats,
        "first_wrong": first_wrong_list,
        "hardest": hardest_list,
        "feedback_helped": {"sessions": fb_sessions, "improved": fb_improved, "rate": fb_rate},
        "suggestions": suggestions,
        "enough_data": enough_data,
    }


def activity(settings: Settings, case_id: str) -> dict:
    """Return high-level activity summary (learners, attempts, last_activity) for library rows."""
    p = _log_path(settings, case_id)
    events = _read_events(p)
    attempt_events = [e for e in events if e.get("kind") == "attempt" and e.get("source") != "sample"]
    sample_attempts = len([e for e in events if e.get("kind") == "attempt" and e.get("source") == "sample"])
    learners = len({e["s"] for e in attempt_events})
    attempts = len(attempt_events)
    last_activity = max((e["at"] for e in attempt_events), default=None)
    return {"learners": learners, "attempts": attempts, "last_activity": last_activity, "sample_attempts": sample_attempts}


def today_totals(settings: Settings) -> dict:
    """Return learners_today and attempts_today across all insight logs."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    insight_dir = settings.data_dir / "insights"
    if not insight_dir.is_dir():
        return {"learners_today": 0, "attempts_today": 0}
    learner_ids: set = set()
    attempt_count = 0
    for p in insight_dir.glob("*.jsonl"):
        events = _read_events(p)
        for e in events:
            if e.get("kind") == "attempt" and e.get("source") != "sample":
                if e.get("at", "").startswith(today):
                    learner_ids.add(e.get("s"))
                    attempt_count += 1
    return {"learners_today": len(learner_ids), "attempts_today": attempt_count}
