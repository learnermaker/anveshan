"""Layer 1 — Perception record (case/runtime data, NOT a contract).

Any media (image / video / audio) is perceived into segments + observations, optionally with
embeddings and specialist payloads. The same perceivers run on the source and on learner attempts.
See docs/plans/universal-pipeline.md §3.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

Modality = Literal["image", "video", "audio"]
Certainty = Literal["observed", "inferred", "unverified"]
ObservationKind = Literal["state", "action", "object", "property", "event", "speech", "measurement", "quality"]


class MediaInfoRecord(BaseModel):
    source_id: str
    modality: Modality
    sha256: str
    mime_type: str
    duration_sec: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    has_audio: Optional[bool] = None


class Segment(BaseModel):
    segment_id: str                      # "seg-000", deterministic order
    kind: Literal["time", "region", "whole"]
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None
    region: Optional[List[float]] = None  # [x, y, w, h] in percent of image
    keyframe_sec: Optional[float] = None
    keyframe_asset: Optional[str] = None  # file name under the artifact's asset dir
    stability: Optional[float] = None     # 0..1 (1 = no change)

    @model_validator(mode="after")
    def _shape(self) -> "Segment":
        if self.kind == "time" and (self.start_sec is None or self.end_sec is None or self.end_sec < self.start_sec):
            raise ValueError(f"{self.segment_id}: time segment needs start_sec <= end_sec")
        if self.kind == "region":
            if self.region is None or len(self.region) != 4 or any(v < 0 or v > 100 for v in self.region):
                raise ValueError(f"{self.segment_id}: region must be [x,y,w,h] percent")
        return self


class Observation(BaseModel):
    obs_id: str                          # "obs-000"
    segment_id: str
    kind: ObservationKind
    label: str                           # short canonical phrase
    detail: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    certainty: Certainty
    producer: str                        # "det:<name>" or "model:<model_key>"

    @model_validator(mode="after")
    def _certainty(self) -> "Observation":
        if self.producer.startswith("model:") and self.certainty == "observed":
            raise ValueError(f"{self.obs_id}: model-produced observations cannot be 'observed' (use 'inferred')")
        if not (self.producer.startswith("det:") or self.producer.startswith("model:")):
            raise ValueError(f"{self.obs_id}: producer must start with 'det:' or 'model:'")
        return self


class PerceptionRecord(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    media: MediaInfoRecord
    segments: List[Segment]
    observations: List[Observation] = Field(default_factory=list)
    embeddings_file: Optional[str] = None            # sidecar .npy (float16, unit rows) next to the record
    embedding_index: Dict[str, int] = Field(default_factory=dict)  # segment_id -> row in embeddings_file
    embedding_model: Optional[str] = None
    specialists: Dict[str, Any] = Field(default_factory=dict)       # name -> specialist payload (dict)
    gates: Dict[str, Any] = Field(default_factory=dict)             # intake/attempt gate results
    runs: List[str] = Field(default_factory=list)                   # replay keys of model calls
    warnings: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _refs(self) -> "PerceptionRecord":
        seg_ids = [s.segment_id for s in self.segments]
        if len(seg_ids) != len(set(seg_ids)):
            raise ValueError("duplicate segment ids")
        known = set(seg_ids)
        for o in self.observations:
            if o.segment_id not in known:
                raise ValueError(f"{o.obs_id} references unknown segment {o.segment_id}")
        for sid in self.embedding_index:
            if sid not in known:
                raise ValueError(f"embedding_index references unknown segment {sid}")
        obs_ids = [o.obs_id for o in self.observations]
        if len(obs_ids) != len(set(obs_ids)):
            raise ValueError("duplicate observation ids")
        return self

    def segment(self, segment_id: str) -> Segment:
        for s in self.segments:
            if s.segment_id == segment_id:
                return s
        raise KeyError(segment_id)

    def observations_for(self, segment_id: str) -> List[Observation]:
        return [o for o in self.observations if o.segment_id == segment_id]
