"""Layer 1 image perceiver.

Implements K6 §2.1: deterministic measurements, embedding (whole + 2×2 tiles),
and vision_fast perception. All model calls go through ctx.gateway.
"""

from __future__ import annotations

import io
import logging
import warnings as _warnings
from pathlib import Path
from typing import List, Literal, Optional

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

from tracks.common.models import AnveshanFailure, FailureCategory, ImagePart, ModelError, load_prompt
from tracks.common.perception import MediaInfoRecord, Observation, PerceptionRecord, Segment
from tracks.common.runtime import RunContext

log = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_PROMPT_ID = "perceive_image"
_PROMPT_VERSION_FILE = "perceive_image_v1.txt"


# DTO for the vision_fast response
class _ImagePerceptionDTO(BaseModel):
    artefact_kind: str = ""
    objects: List[str] = Field(default_factory=list)
    properties: List[dict] = Field(default_factory=list)
    visible_mistakes_to_avoid: List[str] = Field(default_factory=list)
    plausible_build_order: List[dict] = Field(default_factory=list)
    safety_categories: List[str] = Field(default_factory=lambda: ["none"])
    teachable: str = "unclear"
    teachable_reason: str = ""
    skill_kind: str = ""


def _clamp_region(region) -> Optional[List[float]]:
    """Clamp a [x, y, w, h] region to [0, 100]."""
    if region is None:
        return None
    try:
        r = [float(v) for v in region[:4]]
        return [max(0.0, min(100.0, v)) for v in r]
    except (TypeError, ValueError, IndexError):
        return None


def _resize_jpeg(img: Image.Image, max_side: int) -> bytes:
    img2 = img.copy()
    img2.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img2.convert("RGB").save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _tile_crop(img: Image.Image, x_pct: float, y_pct: float, w_pct: float, h_pct: float, max_side: int) -> bytes:
    """Crop a region (in %) from the image and return JPEG bytes."""
    W, H = img.size
    x1 = int(x_pct / 100 * W)
    y1 = int(y_pct / 100 * H)
    x2 = int((x_pct + w_pct) / 100 * W)
    y2 = int((y_pct + h_pct) / 100 * H)
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(W, x2), min(H, y2)
    crop = img.crop((x1, y1, x2, y2))
    return _resize_jpeg(crop, max_side)


def perceive_image(
    path: Path,
    mime: str,
    ctx: RunContext,
    *,
    source_id: str,
    asset_dir: Path,
    purpose: Literal["source", "attempt"],
    skill_hint: Optional[str] = None,
    want_specialists: bool = True,
) -> PerceptionRecord:
    """Perceive a single image: measurements, embeddings (whole + 2×2 tiles), vision_fast."""
    from tracks.common.media import sha256_file

    path = Path(path)
    sha = sha256_file(path)
    asset_dir = Path(asset_dir)
    asset_dir.mkdir(parents=True, exist_ok=True)

    img = Image.open(path).convert("RGB")
    W, H = img.size

    segments: List[Segment] = []
    observations: List[Observation] = []
    runs: List[str] = []
    warnings_list: List[str] = []

    # seg-000: whole image
    segments.append(Segment(segment_id="seg-000", kind="whole"))

    obs_idx = 0

    def next_obs() -> str:
        nonlocal obs_idx
        oid = f"obs-{obs_idx:03d}"
        obs_idx += 1
        return oid

    # ---- Step 1: Deterministic measurements ----
    gray = np.asarray(img.convert("L"), dtype=np.float32) / 255.0

    brightness = float(gray.mean())
    rms_contrast = float(gray.std())

    # Blur: variance of Laplacian (3x3 kernel via numpy convolution)
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float32)
    # Manual convolution for Laplacian
    padded = np.pad(gray, 1, mode="reflect")
    lap = (
        padded[:-2, 1:-1] + padded[2:, 1:-1] + padded[1:-1, :-2] + padded[1:-1, 2:]
        - 4 * padded[1:-1, 1:-1]
    )
    blur_score = float(lap.var())

    # Ink fraction and Otsu separation
    from tracks.common.kolam_geometry import binarize, otsu_threshold

    otsu_val = otsu_threshold(gray)
    # Ink = dark pixels (minority class for line art)
    dark_fraction = float((gray < otsu_val).mean())
    light_fraction = 1.0 - dark_fraction
    ink_fraction = min(dark_fraction, light_fraction)  # smaller is likely ink

    # Otsu separation: difference between means of the two classes
    dark_pixels = gray[gray < otsu_val]
    light_pixels = gray[gray >= otsu_val]
    dark_mean = float(dark_pixels.mean()) if dark_pixels.size > 0 else 0.0
    light_mean = float(light_pixels.mean()) if light_pixels.size > 0 else 1.0
    otsu_separation = light_mean - dark_mean

    # Skeleton length ratio (simple heuristic: perimeter / area of binary image)
    binary = (gray < otsu_val).astype(np.uint8)
    ink_pixels = binary.sum()
    # Count boundary pixels (pixels adjacent to opposite-class pixels)
    from tracks.common.kolam_geometry import label_components, thin

    try:
        skeleton = thin(binary)
        skeleton_px = int(skeleton.sum())
        skeleton_length_ratio = float(skeleton_px) / max(ink_pixels, 1) if ink_pixels > 0 else 0.0
    except Exception:
        skeleton_length_ratio = 0.0
        skeleton_px = 0

    # Component count
    try:
        components = label_components(binary > 0)
        n_components = int(components.max())
    except Exception:
        n_components = 0

    meas_defs = [
        ("width", float(W), "px"),
        ("height", float(H), "px"),
        ("brightness", round(brightness, 4), None),
        ("rms_contrast", round(rms_contrast, 4), None),
        ("blur_score", round(blur_score, 4), None),
        ("ink_fraction", round(ink_fraction, 4), None),
        ("otsu_separation", round(otsu_separation, 4), None),
        ("skeleton_length_ratio", round(skeleton_length_ratio, 4), None),
        ("component_count", float(n_components), None),
    ]
    for label, value, unit in meas_defs:
        obs = Observation(
            obs_id=next_obs(),
            segment_id="seg-000",
            kind="measurement",
            label=label,
            value=value,
            unit=unit,
            certainty="observed",
            producer="det:image_basic",
        )
        observations.append(obs)

    # ---- Step 2: Embedding (whole + 2×2 tiles) ----
    # Segments: seg-000 whole, seg-001..seg-004 four 2x2 grid regions
    tile_regions = [
        (0.0, 0.0, 50.0, 50.0),   # top-left
        (50.0, 0.0, 50.0, 50.0),  # top-right
        (0.0, 50.0, 50.0, 50.0),  # bottom-left
        (50.0, 50.0, 50.0, 50.0), # bottom-right
    ]
    for i, (x, y, w, h) in enumerate(tile_regions, start=1):
        segments.append(Segment(
            segment_id=f"seg-{i:03d}",
            kind="region",
            region=[x, y, w, h],
        ))

    whole_jpeg = _resize_jpeg(img, 768)
    tile_jpegs = [_tile_crop(img, x, y, w, h, 384) for (x, y, w, h) in tile_regions]

    embed_items = [ImagePart(whole_jpeg)] + [ImagePart(j) for j in tile_jpegs]  # 5 items total

    embedding_index = {}
    embeddings_file = None

    try:
        embed_result = ctx.gateway.embed(
            items=embed_items,
            purpose=f"{purpose}_image",
        )
        runs.append(embed_result.metadata.replay_key)
        vecs = embed_result.vectors  # shape (5, 768), float32
        # Save as float16
        npy_name = f"emb_{sha[:12]}.npy"
        npy_path = asset_dir / npy_name
        np.save(str(npy_path), vecs.astype(np.float16))
        embeddings_file = npy_name
        embedding_index = {
            "seg-000": 0,
            "seg-001": 1,
            "seg-002": 2,
            "seg-003": 3,
            "seg-004": 4,
        }
    except ModelError as e:
        warnings_list.append(f"embedding failed: {e.message}")

    # ---- Step 3: Perception call (vision_fast) ----
    seg_offset = 5  # next region segment index

    try:
        prompt_text, prompt_ver = load_prompt(_PROMPTS_DIR / _PROMPT_VERSION_FILE)
        result = ctx.gateway.generate_json(
            model_key="vision_fast",
            prompt_id=_PROMPT_ID,
            prompt_version=prompt_ver,
            prompt_text=prompt_text,
            schema=_ImagePerceptionDTO,
            parts=[ImagePart(_resize_jpeg(img, 768))],
        )
        runs.append(result.metadata.replay_key)
        dto = result.data

        # Map objects
        for obj_label in dto.objects[:10]:
            observations.append(Observation(
                obs_id=next_obs(),
                segment_id="seg-000",
                kind="object",
                label=obj_label,
                certainty="inferred",
                producer="model:vision_fast",
            ))

        # Map properties (with optional region segments)
        for prop in dto.properties[:12]:
            raw_region = _clamp_region(prop.get("region"))
            seg_id = "seg-000"
            if raw_region is not None:
                seg_id = f"seg-{seg_offset:03d}"
                seg_offset += 1
                segments.append(Segment(
                    segment_id=seg_id,
                    kind="region",
                    region=raw_region,
                ))
            observations.append(Observation(
                obs_id=next_obs(),
                segment_id=seg_id,
                kind="property",
                label=prop.get("label", "property"),
                detail=prop.get("detail"),
                certainty="inferred",
                producer="model:vision_fast",
            ))

        # Map visible_mistakes_to_avoid
        for mistake in dto.visible_mistakes_to_avoid[:5]:
            observations.append(Observation(
                obs_id=next_obs(),
                segment_id="seg-000",
                kind="quality",
                label=f"avoid: {mistake}",
                certainty="inferred",
                producer="model:vision_fast",
            ))

        # Map plausible_build_order
        for i, step in enumerate(dto.plausible_build_order[:8]):
            raw_region = _clamp_region(step.get("region"))
            seg_id = "seg-000"
            if raw_region is not None:
                seg_id = f"seg-{seg_offset:03d}"
                seg_offset += 1
                segments.append(Segment(
                    segment_id=seg_id,
                    kind="region",
                    region=raw_region,
                ))
            observations.append(Observation(
                obs_id=next_obs(),
                segment_id=seg_id,
                kind="action",
                label=f"build step {i + 1}: {step.get('step', '')}",
                certainty="inferred",
                producer="model:vision_fast",
            ))

        # Store gate info for intake screen (source only)
        if purpose == "source":
            gate = {
                "artefact_kind": dto.artefact_kind,
                "skill_kind": dto.skill_kind,
                "teachable": dto.teachable,
                "teachable_reason": dto.teachable_reason,
                "safety_categories": dto.safety_categories,
            }
        else:
            gate = {}

    except ModelError as e:
        warnings_list.append(f"vision_fast perception failed: {e.message}")
        gate = {}

    from tracks.common.media import sha256_file as _sha_fn

    record = PerceptionRecord(
        media=MediaInfoRecord(
            source_id=source_id,
            modality="image",
            sha256=sha,
            mime_type=mime,
            width=W,
            height=H,
        ),
        segments=segments,
        observations=observations,
        embeddings_file=embeddings_file,
        embedding_index=embedding_index,
        gates={"intake": gate} if purpose == "source" else {},
        runs=runs,
        warnings=warnings_list,
    )
    return record
