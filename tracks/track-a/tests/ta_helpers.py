"""Helpers for Track A core tests: temp case packs, fake goal builders, fake model clients.

No network: model calls go through ``ModelGateway`` with a fake google-genai client.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable, List, Optional

import pytest
from PIL import Image

from tracks.common.casedata import Band, ObserverBinding, SourceRecord, SourceRegistry, write_json
from tracks.common.media import sha256_file
from tracks.common.models import ModelRegistry
from tracks.common.runtime import RunContext
from tracks.common.schemas import ClaimType, EvidenceRef, KnowledgeClaim, TaskConstraint

import track_a.goals as goals
from track_a.goals import CriterionTemplate, GoalBuildResult

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_CASES = REPO_ROOT / "tracks" / "cases"
SRC_ID = "src.kolam.target.v1"


# ---------------------------------------------------------------------------
# Case packs
# ---------------------------------------------------------------------------


def write_png(path: Path, size=(64, 48)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", size, (255, 255, 255))
    for x in range(size[0] // 4, size[0] * 3 // 4):
        im.putpixel((x, size[1] // 2), (0, 0, 0))
    im.save(path, format="PNG")





# ---------------------------------------------------------------------------
# Fake goal builder
# ---------------------------------------------------------------------------


def ev(eid: str, source_id: str, *, state="observed", conf=0.8, modality="image", start=None, end=None, cue=None) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=eid,
        source_id=source_id,
        modality=modality,
        start_sec=start,
        end_sec=end,
        cue_excerpt=cue,
        verification_state=state,
        confidence=conf,
    )


def kolam_claims(source_id: str = SRC_ID) -> List[KnowledgeClaim]:
    return [
        KnowledgeClaim(
            claim_id="CLM-01",
            claim_type=ClaimType.CUE,
            statement="The pattern has 13 dots in a 1-3-5-3-1 diamond.",
            is_observed=True,
            evidence_refs=[ev("ev.kolam.target.01", f"{source_id}#xywh=percent:10.00,10.00,80.00,80.00", cue="dot grid")],
        ),
        KnowledgeClaim(
            claim_id="CLM-02",
            claim_type=ClaimType.CUE,
            statement="The line never touches a dot.",
            is_observed=True,
            evidence_refs=[ev("ev.kolam.target.02", f"{source_id}#xywh=percent:30.00,30.00,20.00,20.00", conf=1.0)],
        ),
        KnowledgeClaim(
            claim_id="CLM-03",
            claim_type=ClaimType.STEP,
            statement="One suggested way: draw curve 1 around the centre dot.",
            is_observed=False,
            evidence_refs=[ev("ev.kolam.path.03", f"{source_id}#xywh=percent:40.00,40.00,20.00,20.00", state="inferred", conf=0.4)],
        ),
        KnowledgeClaim(
            claim_id="CLM-04",
            claim_type=ClaimType.STEP,
            statement="Then draw curve 2 around the outer dots.",
            is_observed=False,
            evidence_refs=[ev("ev.kolam.path.04", source_id, state="inferred", conf=0.4)],
        ),
    ]


def binding(metric: str) -> ObserverBinding:
    return ObserverBinding(
        metric=metric,
        direction="higher_is_better",
        bands=[Band(status="satisfied", min=0.9), Band(status="partially_satisfied", min=0.7)],
    )


_KOLAM_PAYLOAD_CACHE: dict = {}


def real_kolam_payload() -> dict:
    """A schema-valid KolamGoal payload computed from the committed public-domain target (cached)."""
    if "p" not in _KOLAM_PAYLOAD_CACHE:
        from tracks.common.goals.kolam import payload_from_image

        root = Path(__file__).resolve().parents[3]
        payload, _ = payload_from_image(root / "tracks" / "cases" / "kolam" / "source" / "ithayakkamalam_target.jpg")
        _KOLAM_PAYLOAD_CACHE["p"] = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
    return dict(_KOLAM_PAYLOAD_CACHE["p"])


def kolam_result(claims: Optional[List[KnowledgeClaim]] = None, **overrides) -> GoalBuildResult:
    r = GoalBuildResult(
        title="Ithayakkamalam kolam",
        summary="A 13-dot sikku kolam made of two continuous curves.",
        goal_payload=real_kolam_payload(),
        claims=claims if claims is not None else kolam_claims(),
        criteria=[
            CriterionTemplate(
                criterion_id="CRIT-KOLAM-COVERAGE",
                name="Every curve drawn",
                description="All curves of the target are drawn.",
                observable_indicator="coverage of goal skeleton samples within tolerance",
                weight=3,
                required=True,
                order_index=0,
                source_claim_ids=["CLM-03", "CLM-04"],
                reference_evidence_ids=["ev.kolam.path.03"],
                why_it_matters="The target is two continuous curves (CLM-03).",
                drill_hint="Trace curve 1 slowly.",
                observer=binding("coverage"),
            ),
            CriterionTemplate(
                criterion_id="CRIT-KOLAM-DOTS",
                name="Dot relations kept",
                description="Each dot keeps its relation to the line.",
                observable_indicator="dot relation agreement",
                weight=2,
                required=True,
                order_index=1,
                source_claim_ids=["CLM-02"],
                reference_evidence_ids=["ev.kolam.target.02"],
                why_it_matters="The line weaves around dots without touching them (CLM-02).",
                drill_hint="Keep a finger-width gap around each dot.",
                observer=binding("dot_relation_accuracy"),
            ),
        ],
        task_title="Draw the Ithayakkamalam kolam",
        task_instructions="1. Draw curve 1 around the centre dot [CLM-03].\n2. Draw curve 2 [CLM-04].",
        task_constraints=[TaskConstraint(constraint_type="grid", description="13 dots rendered by the app", value="1-3-5-3-1")],
        warnings=["test warning"],
        run_keys=["abc123"],
        built_with={"algorithm": "fake-1"},
    )
    for k, v in overrides.items():
        setattr(r, k, v)
    return r





# ---------------------------------------------------------------------------
# Fake model client
# ---------------------------------------------------------------------------


class FakeModels:
    def __init__(self, text: str):
        self.text = text
        self.calls: list = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents})
        return type("R", (), {"text": self.text})()


class FakeClient:
    def __init__(self, models: FakeModels):
        self.models = models
