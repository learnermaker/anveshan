"""AI coaching wording for feedback (technical-panel plan WI-4.1). Never touches scores.

One model call rewrites only each item's ``corrective_advice`` into plain coaching language. The
result passes through ``feedback.guard_wording`` (structure, evidence refs, claim ids and numbers
must survive; no new numbers) plus a local check that each item still says nothing about passing or
scores. On any model failure or rejected rewrite the deterministic template is kept, and the reason
is reported in the attempt result (no silent fallback).
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from tracks.common.models import AnveshanFailure, load_prompt
from tracks.common.runtime import RunContext
from tracks.common.schemas import Feedback

PROMPT = Path(__file__).resolve().parents[3] / "common" / "prompts" / "coach_feedback_v1.txt"
MODEL_KEY = "vision_fast"
_NUM = re.compile(r"\d+(?:\.\d+)?")
# Verdict or scoring language the coach must not use ("passes through a dot" stays allowed).
_VERDICT_WORDS = re.compile(r"\b(passed|failed|fail|fails|failing|scored?|scores|scoring|grade[ds]?|marks out of)\b", re.IGNORECASE)


class _CoachItem(BaseModel):
    criterion_id: str
    coaching: str = Field(max_length=400)


class _CoachOut(BaseModel):
    items: List[_CoachItem]


def enabled(ctx: RunContext) -> bool:
    """On by default; ``ANVESHAN_COACH_WORDING=0`` turns it off (the template is then always used)."""
    if os.environ.get("ANVESHAN_COACH_WORDING", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    return ctx.gateway.registry.enabled(MODEL_KEY)


class CoachWording:
    """A ``WordingPass`` for ``build_feedback`` that remembers what happened for the attempt view."""

    def __init__(self, ctx: RunContext, skill_title: str, criterion_names: Dict[str, str]) -> None:
        self.ctx = ctx
        self.skill_title = skill_title
        self.names = criterion_names
        self.status = "template"
        self.reason: Optional[str] = None
        self.run_key: Optional[str] = None
        self.model_id: Optional[str] = None

    def __call__(self, template: Feedback) -> Feedback:
        items = [
            {
                "criterion_id": it.criterion_id,
                "criterion": self.names.get(it.criterion_id, it.criterion_id),
                "observed": it.what_was_observed,
                "differed": it.what_differed,
                "advice": it.corrective_advice,
            }
            for it in template.items
        ]
        prompt_text, version = load_prompt(PROMPT, skill_title=self.skill_title, items_json=json.dumps(items, ensure_ascii=False, indent=1))
        try:
            res = self.ctx.gateway.generate_json(
                model_key=MODEL_KEY,
                prompt_id="coach_feedback",
                prompt_version=version,
                prompt_text=prompt_text,
                schema=_CoachOut,
                expected_behavior="Rewrite advice only; keep claim ids; no new numbers; no verdicts.",
            )
        except AnveshanFailure as exc:
            self.reason = f"coach wording unavailable ({exc.category.value})"
            return template
        self.run_key = res.metadata.replay_key
        self.model_id = res.metadata.model_id
        by_id = {i.criterion_id: i.coaching.strip() for i in res.data.items}
        new_items, rejected = [], []
        for it in template.items:
            text = by_id.get(it.criterion_id, "")
            source_nums = set(_NUM.findall(" ".join((it.what_was_observed, it.what_differed, it.corrective_advice))))
            if not text or _VERDICT_WORDS.search(text) or not set(_NUM.findall(text)) <= source_nums:
                # verdict language, or a number this item never contained: keep this item's template advice
                rejected.append(it.criterion_id)
                new_items.append(it)
            else:
                new_items.append(it.model_copy(update={"corrective_advice": text}))
        if rejected:
            self.reason = f"fixed wording kept for {', '.join(rejected)}"
        if len(rejected) == len(template.items):
            return template
        self.status = "proposed"
        return template.model_copy(update={"items": new_items})

    def view(self, accepted: bool) -> Dict[str, Optional[str]]:
        if self.status == "proposed" and not accepted:
            self.status, self.reason = "template", "coach wording rejected by the guard (ids or numbers changed)"
        elif self.status == "proposed":
            self.status = "ai_worded"
        return {"status": self.status, "reason": self.reason, "model_id": self.model_id, "run_key": self.run_key}
