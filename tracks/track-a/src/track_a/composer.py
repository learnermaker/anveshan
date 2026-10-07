"""Composer: create draft cases from uploaded media (Layer 1 -> proposal).

See docs/kiro/specs/K6-composer-backend.md §3 and docs/plans/universal-pipeline.md §5.

Flow:
  create_draft  -> perceive -> intake -> (propose_skill_model or _fallback_skill_model) -> Draft
  refine_draft  -> re-run proposal with new hints (no new perception)
  create_case_from_draft -> write case directory structure
"""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.perception import PerceptionRecord
from tracks.common.perceivers import load_record, perceive, save_record
from tracks.common.perceivers.screen import intake_from_perception
from tracks.common.perceivers.specialist_probe import available_specialists, available_structures
from tracks.common.policy import REFUSE_TEACHABILITY_MESSAGE
from tracks.common.profile import (
    COMPOSED_MODALITY,
    SPECIALIST_LABEL,
    STRUCTURE_LABEL,
    CaseProfile,
    IntakeResult,
    ProbeFacts,
    composed_case_id,
)
from tracks.common.runtime import RunContext
from tracks.common.skill_model import STRUCTURE_ATTEMPT_KINDS, SkillModel

log = logging.getLogger(__name__)

# ---- lazy import of K7's propose_skill_model --------------------------------
try:
    from track_a.universal import propose_skill_model  # type: ignore[import]
except ImportError:
    propose_skill_model = None  # use _fallback_skill_model

# Upload limits (matching K6 §3.2 step 1)
_MAX_BYTES = 30 * 1024 * 1024       # 30 MB
_VIDEO_MIN_SEC = 8.0
_VIDEO_MAX_SEC = 600.0   # perceiver samples <= 120 frames adaptively, so cost does not grow with length
_AUDIO_MIN_SEC = 3.0
_AUDIO_MAX_SEC = 60.0
_IMAGE_MIN_PX = 64


def _ext_for(file_path: Path, mime: str) -> str:
    ext = file_path.suffix.lower()
    if ext and len(ext) <= 6 and ext[1:].isalnum():
        return ext
    return mimetypes.guess_extension(mime) or ".bin"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---- Fallback skill model (deterministic; no model calls) -------------------------


def _fallback_skill_model(
    record: PerceptionRecord,
    probe: ProbeFacts,
    intake: IntakeResult,
    title_hint: Optional[str],
) -> tuple:
    """Build a minimal deterministic SkillModel when K7's propose_skill_model is unavailable."""
    from tracks.common.skill_model import (
        Check, Relevance, SkillModel, TargetProperty,
        STRUCTURE_ATTEMPT_KINDS,
    )

    # Pick first available structure in preferred order
    # Skip temporal_pattern: it requires rhythm specialist payload in SkillModel.specialists (K7's job)
    structure_order = ["final_state", "procedure", "utterance", "temporal_pattern"]
    structures = [s for s in structure_order if s in probe.structures_available]
    structures = [s for s in structures if s != "temporal_pattern"]
    if not structures:
        # Only temporal_pattern was available (e.g. rhythm-only audio), use final_state as fallback
        structures = ["final_state"]
        model_warnings = ["temporal_pattern dropped in fallback — needs K7 rhythm specialist; defaulting to final_state"]
    else:
        model_warnings = []

    # Collect inferred property observations for goal_state
    prop_obs = [
        o for o in record.observations
        if o.kind == "property" and o.certainty == "inferred"
    ][:4]

    goal_state = []
    for i, obs in enumerate(prop_obs):
        goal_state.append(TargetProperty(
            prop_id=f"prop-{i + 1:02d}",
            statement=obs.detail or obs.label,
            region=None,
            evidence=[obs.obs_id],
            certainty="inferred",
            keep=True,
        ))

    # Build checks
    checks = []
    chk_idx = 1

    if "final_state" in structures:
        checks.append(Check(
            check_id=f"CHK-{chk_idx:02d}",
            kind="final_similarity",
            name="Visual similarity",
            observable_indicator="attempt resembles the goal image",
            metric_id="u.final_similarity",
            method="deterministic",
            weight=2.0,
        ))
        chk_idx += 1
        for prop in goal_state:
            checks.append(Check(
                check_id=f"CHK-{chk_idx:02d}",
                kind="final_property",
                name=f"Property: {prop.statement[:50]}",
                observable_indicator=prop.statement,
                targets=[prop.prop_id],
                metric_id=f"u.final_property.{prop.prop_id}",
                method="model_status",
                weight=2.0,
            ))
            chk_idx += 1

    if "procedure" in structures and "final_state" not in structures:
        checks.append(Check(
            check_id=f"CHK-{chk_idx:02d}",
            kind="step_coverage",
            name="Step coverage",
            observable_indicator="steps are covered in the attempt",
            metric_id="u.step_coverage",
            method="deterministic",
            weight=3.0,
        ))
        chk_idx += 1

    if "temporal_pattern" in structures:
        # Only add rhythm check if the rhythm specialist data is available
        # Note: fallback drops temporal_pattern above, so this should never run
        # Left for clarity
        pass

    if "utterance" in structures:
        checks.append(Check(
            check_id=f"CHK-{chk_idx:02d}",
            kind="utterance_match",
            name="Utterance match",
            observable_indicator="spoken phrase matches",
            metric_id="u.utterance_match",
            method="deterministic",
            weight=3.0,
        ))
        chk_idx += 1

    if not checks:
        checks.append(Check(
            check_id="CHK-01",
            kind="final_similarity",
            name="Visual similarity",
            observable_indicator="attempt resembles the goal",
            metric_id="u.final_similarity",
            method="deterministic",
            weight=2.0,
        ))

    # Expected kinds = intersection over structures
    expected_kinds: List[str] = []
    for s in structures:
        kinds = STRUCTURE_ATTEMPT_KINDS.get(s, [])
        if not expected_kinds:
            expected_kinds = list(kinds)
        else:
            expected_kinds = [k for k in expected_kinds if k in kinds]
    if not expected_kinds:
        expected_kinds = ["image"]

    # Remove trace if no line_art
    if "line_art" not in probe.specialists_available:
        expected_kinds = [k for k in expected_kinds if k != "trace"]
    if not expected_kinds:
        expected_kinds = ["image"]

    title = title_hint or intake.skill_kind or "Untitled skill"
    modality = record.media.modality

    model = SkillModel(
        skill_title=title,
        summary=f"Learn to reproduce {title.lower()}",
        source_modality=modality,
        structures=structures,
        goal_state=goal_state,
        relevance=Relevance(expected_kinds=expected_kinds),
        checks=checks,
        warnings=["fallback_skill_model: K7 propose_skill_model not available"] + model_warnings,
    )
    return model, {"fallback": True}, ["fallback skill model used (K7 not merged)"] + model_warnings


# ---- Draft -----------------------------------------------------------------------


@dataclass
class Draft:
    draft_id: str
    dir: Path
    source_path: Path
    perception: PerceptionRecord
    probe: Optional[ProbeFacts]
    intake: IntakeResult
    proposal: Optional[CaseProfile]
    refused: bool
    refusal_message: Optional[str]
    warnings: List[str]

    def to_view(self) -> dict:
        """JSON-serialisable view for the API (no embeddings)."""
        perc_view = {
            "segments": [s.model_dump(mode="json") for s in self.perception.segments],
            "observations": [o.model_dump(mode="json") for o in self.perception.observations],
        }
        return {
            "draft_id": self.draft_id,
            "probe": self.probe.model_dump(mode="json") if self.probe else None,
            "intake": self.intake.model_dump(mode="json"),
            "proposal": self.proposal.model_dump(mode="json") if self.proposal else None,
            "refused": self.refused,
            "refusal_message": self.refusal_message,
            "warnings": list(self.warnings),
            "structure_labels": STRUCTURE_LABEL,
            "specialist_labels": SPECIALIST_LABEL,
            "perception": perc_view,
        }


def _load_draft(draft_dir: Path) -> Optional[Draft]:
    """Load a Draft from its saved draft.json. Returns None if not found."""
    draft_json = draft_dir / "draft.json"
    if not draft_json.exists():
        return None
    try:
        data = json.loads(draft_json.read_text(encoding="utf-8"))
        record = load_record(draft_dir / "perception_source.json")

        intake = IntakeResult.model_validate(data["intake"])
        probe = ProbeFacts.model_validate(data["probe"]) if data.get("probe") else None
        proposal = CaseProfile.model_validate(data["proposal"]) if data.get("proposal") else None

        return Draft(
            draft_id=data["draft_id"],
            dir=draft_dir,
            source_path=Path(data["source_path"]),
            perception=record,
            probe=probe,
            intake=intake,
            proposal=proposal,
            refused=data.get("refused", False),
            refusal_message=data.get("refusal_message"),
            warnings=data.get("warnings", []),
        )
    except Exception as e:
        log.warning("could not reload draft from %s: %s", draft_dir, e)
        return None


def _save_draft(draft: Draft) -> None:
    data = {
        "draft_id": draft.draft_id,
        "source_path": str(draft.source_path),
        "intake": draft.intake.model_dump(mode="json"),
        "probe": draft.probe.model_dump(mode="json") if draft.probe else None,
        "proposal": draft.proposal.model_dump(mode="json") if draft.proposal else None,
        "refused": draft.refused,
        "refusal_message": draft.refusal_message,
        "warnings": draft.warnings,
    }
    (draft.dir / "draft.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _build_probe_and_proposal(
    record: PerceptionRecord,
    intake: IntakeResult,
    ctx: RunContext,
    title_hint: Optional[str],
    description: Optional[str],
    sha: str,
    asset_dir: Path,
) -> tuple:
    """Run specialist/structure probes and call the skill model proposer."""
    spec_results = available_specialists(record, asset_dir)
    struct_results = available_structures(record, spec_results)

    structures_available = [s for s, (ok, _) in struct_results.items() if ok]
    specialists_available = [s for s, (ok, _) in spec_results.items() if ok]
    reasons = {k: r for k, (_, r) in {**spec_results, **struct_results}.items()}

    m = record.media
    probe = ProbeFacts(
        modality=m.modality,
        mime_type=m.mime_type,
        bytes=0,  # filled by caller
        sha256=m.sha256,
        width=m.width,
        height=m.height,
        duration_sec=m.duration_sec,
        has_audio=m.has_audio,
        structures_available=structures_available,
        specialists_available=specialists_available,
        reasons=reasons,
    )

    if not structures_available:
        return probe, None, None, ["no structures available for this source"]

    skill_model = None
    proposal_meta = {}
    model_warnings: List[str] = []

    if propose_skill_model is not None:
        try:
            skill_model, proposal_meta, model_warnings = propose_skill_model(
                record, probe, intake, ctx, title_hint, description
            )
        except Exception as e:
            log.warning("propose_skill_model failed: %s; using fallback", e)
            model_warnings.append(f"propose_skill_model failed: {e}")
            skill_model = None

    if skill_model is None:
        skill_model, proposal_meta, model_warnings = _fallback_skill_model(record, probe, intake, title_hint)

    return probe, skill_model, proposal_meta, model_warnings


def create_draft(
    data_dir: Path,
    file_path: Path,
    mime: str,
    ctx: RunContext,
    *,
    title_hint: Optional[str] = None,
    description: Optional[str] = None,
    rights_confirmed: bool = False,
) -> Draft:
    """Create (or reload) a draft from an uploaded file.

    Steps (K6 §3.2):
    1. Validate rights, limits.
    2. Compute draft_id from sha256; idempotent if draft.json exists.
    3. Perceive the source.
    4. Intake screen.
    5. Propose SkillModel (or fallback).
    6. Build CaseProfile.
    7. Write draft.json.
    """
    from tracks.common.media import probe as media_probe, sha256_file

    data_dir = Path(data_dir)
    file_path = Path(file_path)
    mime = (mime or "").split(";", 1)[0].strip().lower()

    # Step 1: rights check and format/limits
    if not rights_confirmed:
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            "You must confirm that you have the rights to use this file.",
        )

    if not file_path.is_file():
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"file not found: {file_path}")

    size = file_path.stat().st_size
    if size == 0:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, "upload is empty")
    if size > _MAX_BYTES:
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            f"file is {size / (1024 * 1024):.1f} MB; maximum is 30 MB",
            {"bytes": size},
        )

    # Duration checks for audio/video
    if mime.startswith("video/") or mime.startswith("audio/"):
        try:
            info = media_probe(file_path)
            dur = info.duration_sec or 0.0
        except Exception as e:
            raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"cannot probe media: {e}")

        if mime.startswith("video/"):
            if dur < _VIDEO_MIN_SEC:
                raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"video is {dur:.1f}s; minimum is {_VIDEO_MIN_SEC}s")
            if dur > _VIDEO_MAX_SEC:
                raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"video is {dur:.1f}s; maximum is {_VIDEO_MAX_SEC}s")
        else:
            if dur < _AUDIO_MIN_SEC:
                raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"audio is {dur:.1f}s; minimum is {_AUDIO_MIN_SEC}s")
            if dur > _AUDIO_MAX_SEC:
                raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"audio is {dur:.1f}s; maximum is {_AUDIO_MAX_SEC}s")

    if mime.startswith("image/"):
        try:
            from PIL import Image
            with Image.open(file_path) as im:
                w, h = im.size
                if min(w, h) < _IMAGE_MIN_PX:
                    raise AnveshanFailure(
                        FailureCategory.INVALID_INPUT,
                        f"image is {w}×{h}px; minimum short side is {_IMAGE_MIN_PX}px",
                    )
        except AnveshanFailure:
            raise
        except Exception as e:
            raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"cannot open image: {e}")

    # Step 2: draft_id from sha256
    sha = sha256_file(file_path)
    draft_id = sha[:16]
    draft_dir = data_dir / "drafts" / draft_id
    draft_dir.mkdir(parents=True, exist_ok=True)

    # Idempotent: reload if already done
    existing = _load_draft(draft_dir)
    if existing is not None:
        return existing

    # Copy source file
    ext = _ext_for(file_path, mime)
    source_dest = draft_dir / f"source{ext}"
    shutil.copyfile(file_path, source_dest)

    # Step 3: Perceive
    asset_dir = draft_dir / "assets"
    record = perceive(
        source_dest, mime, ctx,
        source_id=f"upload.{sha[:12]}",
        asset_dir=asset_dir,
        purpose="source",
        skill_hint=title_hint or description,
    )
    save_record(record, draft_dir / "perception_source.json")

    # Step 4: Intake screen
    intake = intake_from_perception(record)

    warnings_list: List[str] = list(record.warnings)
    refused = False
    refusal_message = None
    probe = None
    proposal = None

    # Safety refuse
    if intake.safety.get("decision") == "refuse":
        refused = True
        reasons = intake.safety.get("reasons", [])
        refusal_message = "We can't use this file: " + "; ".join(reasons)

    # Teachability refuse
    elif intake.teachable == "no":
        refused = True
        refusal_message = REFUSE_TEACHABILITY_MESSAGE.format(reason=intake.teachable_reason)

    else:
        # Step 5+6: Build probe and proposal
        if intake.teachable == "unclear" and not title_hint and not description:
            # Need more info from user
            warnings_list.append(
                "Tell us what skill this is (title and what a learner should achieve) to continue"
            )
        else:
            try:
                probe, skill_model, proposal_meta, model_warnings = _build_probe_and_proposal(
                    record, intake, ctx, title_hint, description, sha, asset_dir
                )
                warnings_list.extend(model_warnings)

                # Update probe bytes
                probe = ProbeFacts(
                    **{**probe.model_dump(), "bytes": size}
                )

                if skill_model is not None:
                    title = title_hint or getattr(skill_model, "skill_title", None) or intake.skill_kind or "Untitled skill"
                    learner_kinds = list(dict.fromkeys(
                        k for s in skill_model.structures
                        for k in STRUCTURE_ATTEMPT_KINDS.get(s, [])
                    ))
                    if "line_art" not in probe.specialists_available:
                        learner_kinds = [k for k in learner_kinds if k != "trace"]
                    if not learner_kinds:
                        learner_kinds = ["image"]

                    t_mode = "goal-conditioned" if skill_model.structures == ["final_state"] else "forward"

                    proposal = CaseProfile(
                        case_id=composed_case_id(title, sha),
                        title=title,
                        skill_summary=skill_model.summary,
                        domain=intake.skill_kind or "general",
                        transmission_mode=t_mode,
                        learner_input_kinds=learner_kinds,
                        probe=probe,
                        intake=intake,
                        skill_model=skill_model,
                        perception_file="perception_source.json",
                        model_proposal=proposal_meta or {},
                        confirmed_by_user=False,
                        warnings=model_warnings,
                    )
            except AnveshanFailure:
                raise
            except Exception as e:
                log.warning("draft proposal failed: %s", e)
                warnings_list.append(f"proposal failed: {e}")

    draft = Draft(
        draft_id=draft_id,
        dir=draft_dir,
        source_path=source_dest,
        perception=record,
        probe=probe,
        intake=intake,
        proposal=proposal,
        refused=refused,
        refusal_message=refusal_message,
        warnings=warnings_list,
    )
    _save_draft(draft)
    return draft


def load_draft(data_dir: Path, draft_id: str) -> Draft:
    """Load an existing draft. Raises MISSING_EVIDENCE if not found."""
    draft_dir = Path(data_dir) / "drafts" / draft_id
    draft = _load_draft(draft_dir)
    if draft is None:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"draft {draft_id} not found")
    return draft


def refine_draft(
    data_dir: Path,
    draft_id: str,
    ctx: RunContext,
    *,
    title: str,
    description: str,
) -> Draft:
    """Re-run step 5 (proposal) with new title/description. No new perception calls."""
    from tracks.common.media import sha256_file

    draft = load_draft(data_dir, draft_id)

    if draft.refused:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, "cannot refine a refused draft")

    sha = draft.perception.media.sha256
    size = draft.source_path.stat().st_size if draft.source_path.exists() else 0

    probe, skill_model, proposal_meta, model_warnings = _build_probe_and_proposal(
        draft.perception, draft.intake, ctx,
        title, description, sha, draft.dir / "assets",
    )
    probe = ProbeFacts(**{**probe.model_dump(), "bytes": size})

    warnings_list = list(model_warnings)
    proposal = None

    if skill_model is not None:
        title_val = title or getattr(skill_model, "skill_title", None) or "Untitled skill"
        learner_kinds = list(dict.fromkeys(
            k for s in skill_model.structures
            for k in STRUCTURE_ATTEMPT_KINDS.get(s, [])
        ))
        if "line_art" not in probe.specialists_available:
            learner_kinds = [k for k in learner_kinds if k != "trace"]
        if not learner_kinds:
            learner_kinds = ["image"]

        t_mode = "goal-conditioned" if skill_model.structures == ["final_state"] else "forward"

        proposal = CaseProfile(
            case_id=composed_case_id(title_val, sha),
            title=title_val,
            skill_summary=skill_model.summary,
            domain=draft.intake.skill_kind or "general",
            transmission_mode=t_mode,
            learner_input_kinds=learner_kinds,
            probe=probe,
            intake=draft.intake,
            skill_model=skill_model,
            perception_file="perception_source.json",
            model_proposal=proposal_meta or {},
            confirmed_by_user=False,
            warnings=model_warnings,
        )

    refined = Draft(
        draft_id=draft.draft_id,
        dir=draft.dir,
        source_path=draft.source_path,
        perception=draft.perception,
        probe=probe,
        intake=draft.intake,
        proposal=proposal,
        refused=False,
        refusal_message=None,
        warnings=warnings_list,
    )
    _save_draft(refined)
    return refined


def create_case_from_draft(
    cases_root: Path,
    data_dir: Path,
    draft_id: str,
    edits: dict,
) -> Path:
    """Create a confirmed case directory from a draft with user edits.

    edits: {title, skill_summary, domain, transmission_mode, learner_input_kinds,
             goal_hint, skill_model}

    The caller (service) then calls track_a.api.build_case(case_dir, ctx).
    """
    from tracks.common.casedata import SourceRecord, SourceRegistry, write_json

    draft = load_draft(data_dir, draft_id)
    if draft.refused:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, "cannot create a case from a refused draft")
    if draft.proposal is None:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, "draft has no proposal; use refine_draft first")

    # Apply edits
    proposal_dict = draft.proposal.model_dump()

    if edits.get("title"):
        proposal_dict["title"] = edits["title"]
    if edits.get("skill_summary"):
        proposal_dict["skill_summary"] = edits["skill_summary"]
    if edits.get("domain"):
        proposal_dict["domain"] = edits["domain"]
    if edits.get("transmission_mode"):
        proposal_dict["transmission_mode"] = edits["transmission_mode"]
    if edits.get("learner_input_kinds"):
        proposal_dict["learner_input_kinds"] = edits["learner_input_kinds"]
    if edits.get("goal_hint"):
        proposal_dict["goal_hint"] = edits["goal_hint"]
    if edits.get("skill_model"):
        proposal_dict["skill_model"] = edits["skill_model"]

    proposal_dict["confirmed_by_user"] = True
    proposal_dict["confirmed_at"] = datetime.now(timezone.utc).isoformat()

    # Validate
    try:
        confirmed_profile = CaseProfile.model_validate(proposal_dict)
    except (ValidationError, ValueError) as e:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"invalid edits: {e}") from e

    title = confirmed_profile.title
    sha = draft.perception.media.sha256
    case_id = composed_case_id(title, sha)

    cases_root = Path(cases_root)
    data_dir = Path(data_dir)
    case_dir = data_dir / "cases" / case_id

    # Idempotent: if already confirmed, return
    profile_path = next(case_dir.glob("knowledge/case_profile.v*.json"), None) if case_dir.exists() else None
    if profile_path is not None:
        try:
            existing = CaseProfile.model_validate(json.loads(profile_path.read_text(encoding="utf-8")))
            if existing.confirmed_by_user:
                return case_dir
        except Exception:
            pass

    (case_dir / "source").mkdir(parents=True, exist_ok=True)
    (case_dir / "knowledge" / "goal_assets").mkdir(parents=True, exist_ok=True)

    # Copy source file
    source_ext = draft.source_path.suffix
    rel_source = f"source/upload.{sha[:12]}{source_ext}"
    shutil.copyfile(draft.source_path, case_dir / rel_source)

    # Write source/source.json
    modality = draft.perception.media.modality
    role = {
        "image": "target_image",
        "video": "expert_video",
        "audio": "expert_audio",
    }.get(modality, "target_image")

    source_record = SourceRecord(
        source_id=f"src.upload.{sha[:12]}",
        role=role,
        mime_type=draft.perception.media.mime_type,
        sha256=sha,
        bytes=draft.source_path.stat().st_size if draft.source_path.exists() else 0,
        path=rel_source,
        duration_sec=draft.perception.media.duration_sec,
        dimensions=(
            [draft.perception.media.width, draft.perception.media.height]
            if draft.perception.media.width and draft.perception.media.height
            else None
        ),
        creator="uploader",
        license="user upload — rights asserted by uploader",
        attribution="Uploaded by the user; rights asserted by the uploader.",
        access_level="approved_learners",
        runtime_label="UPLOAD",
        used_by_system=True,
        notes=f"Composed upload case.",
    )
    write_json(case_dir / "source" / "source.json", SourceRegistry(case_id=case_id, sources=[source_record]))

    # Copy perception record and assets to knowledge/
    perc_src = draft.dir / "perception_source.json"
    perc_dest = case_dir / "knowledge" / "perception_source.v1.json"

    # Copy .npy if present
    perc_record = draft.perception
    if perc_record.embeddings_file:
        npy_src = draft.dir / "assets" / perc_record.embeddings_file
        if not npy_src.exists():
            npy_src = draft.dir / perc_record.embeddings_file
        if npy_src.exists():
            shutil.copyfile(npy_src, case_dir / "knowledge" / perc_record.embeddings_file)

    # Copy keyframe assets
    asset_src = draft.dir / "assets"
    if asset_src.exists():
        for kf_file in asset_src.glob("kf_*.jpg"):
            shutil.copyfile(kf_file, case_dir / "knowledge" / "goal_assets" / kf_file.name)

    shutil.copyfile(perc_src, perc_dest)

    # Write knowledge/case_profile.v1.json
    write_json(case_dir / "knowledge" / "case_profile.v1.json", confirmed_profile)

    # Write manifest.json
    structures = confirmed_profile.skill_model.structures
    archetype = "universal:" + "+".join(structures)
    if structures == ["final_state"]:
        workspace_type = "spatial_canvas"
    elif "temporal_pattern" in structures:
        workspace_type = "rhythm_envelope"
    else:
        workspace_type = "spatial_sequence"

    manifest = {
        "case_id": case_id,
        "title": confirmed_profile.title,
        "archetype": archetype,
        "workspace_type": workspace_type,
        "transmission_mode": confirmed_profile.transmission_mode,
        "source_mode": "composed",
        "source_media": {"type": "local_file", "path": rel_source, "mime_type": draft.perception.media.mime_type, "attribution": "user upload"},
        "learner_input_kinds": confirmed_profile.learner_input_kinds,
    }
    (case_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return case_dir
