"""IP-Adapter enhancement functions (Phase 1~3).

Phase 1-A: Photo upload preprocessing
Phase 1-B: Reference quality validation
Phase 2-A: Multi-angle reference selection
Phase 2-B: Dual IP-Adapter units
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass, field
from typing import Any

from PIL import Image
from sqlalchemy.orm import Session

from config import (
    DEFAULT_CHARACTER_PRESET,
    IP_ADAPTER_DUAL_PRIMARY_RATIO,
    IP_ADAPTER_DUAL_SECONDARY_RATIO,
    REFERENCE_MIN_FACE_RATIO,
    REFERENCE_MIN_RESOLUTION,
    logger,
)
from models import Character
from services.image import load_image_bytes


@dataclass
class ReferenceQualityReport:
    """Quality assessment result for a reference image."""

    valid: bool
    face_detected: bool
    face_count: int = 0
    face_size_ratio: float = 0.0
    resolution_ok: bool = True
    width: int = 0
    height: int = 0
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def validate_reference_quality(image_b64: str) -> ReferenceQualityReport:
    """Validate reference image quality: face detection, resolution, face size ratio.

    Uses a single OpenCV detection pass for both face presence check and multi-face count.

    Args:
        image_b64: Base64 encoded image

    Returns:
        ReferenceQualityReport with detailed validation results
    """
    image_bytes = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = image.size
    warnings: list[str] = []

    # 1. Resolution check
    resolution_ok = width >= REFERENCE_MIN_RESOLUTION and height >= REFERENCE_MIN_RESOLUTION
    if not resolution_ok:
        warnings.append(
            f"해상도가 너무 낮습니다 ({width}x{height}). 최소 {REFERENCE_MIN_RESOLUTION}x{REFERENCE_MIN_RESOLUTION} 필요."
        )

    # 2. Single-pass face detection (returns all faces)
    all_faces = _detect_all_faces(image)
    face_count = len(all_faces)
    face_detected = face_count > 0
    face_size_ratio = 0.0
    face_bbox = None

    if face_detected:
        # Use largest face as primary
        face_bbox = max(all_faces, key=lambda f: f[2] * f[3])
        _, _, fw, fh = face_bbox
        face_area = fw * fh
        image_area = width * height
        face_size_ratio = face_area / image_area if image_area > 0 else 0.0
        if face_size_ratio < REFERENCE_MIN_FACE_RATIO:
            warnings.append(f"얼굴이 너무 작습니다 ({face_size_ratio:.1%}). 최소 {REFERENCE_MIN_FACE_RATIO:.0%} 권장.")
    else:
        warnings.append("얼굴을 탐지하지 못했습니다. 정면 얼굴이 명확한 이미지를 사용하세요.")

    if face_count > 1:
        warnings.append(f"복수 얼굴 감지 ({face_count}명). 단일 인물 이미지를 권장합니다.")

    valid = resolution_ok and face_detected and face_size_ratio >= REFERENCE_MIN_FACE_RATIO

    return ReferenceQualityReport(
        valid=valid,
        face_detected=face_detected,
        face_count=face_count,
        face_size_ratio=face_size_ratio,
        resolution_ok=resolution_ok,
        width=width,
        height=height,
        warnings=warnings,
        details={"face_bbox": list(face_bbox) if face_bbox else None},
    )


def _detect_all_faces(image: Image.Image) -> list[tuple[int, int, int, int]]:
    """Detect all faces in image using OpenCV cascade. Single pass for efficiency."""
    import cv2
    import numpy as np

    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if faces is None or len(faces) == 0:
        return []
    return [(int(x), int(y), int(w), int(h)) for x, y, w, h in faces]


def upload_photo_reference(
    character_key: str,
    image_b64: str,
    db: Session | None = None,
) -> tuple[str, ReferenceQualityReport]:
    """Upload a real photo as IP-Adapter reference with face crop preprocessing.

    Args:
        character_key: Character name
        image_b64: Base64 encoded photo
        db: Optional DB session

    Returns:
        Tuple of (saved filename, quality report)
    """
    from services.controlnet import save_reference_image

    # Remove data URI prefix
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    image_bytes_raw = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_bytes_raw)).convert("RGB")

    # Preprocess: face crop + 512x512 resize
    processed = _preprocess_uploaded_photo(image)

    # Encode back to base64
    buf = io.BytesIO()
    processed.save(buf, format="PNG")
    processed_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    # Quality check
    quality = validate_reference_quality(processed_b64)

    # Save
    filename = save_reference_image(character_key, processed_b64, db=db)

    return filename, quality


def _preprocess_uploaded_photo(image: Image.Image) -> Image.Image:
    """Crop face region and resize to 512x512 for IP-Adapter reference.

    Falls back to center crop if face not detected.
    """
    from services.image import detect_face

    face_bbox = detect_face(image)
    width, height = image.size

    if face_bbox:
        x, y, fw, fh = face_bbox
        # Expand crop to include neck/shoulders (1.8x face area)
        cx, cy = x + fw // 2, y + fh // 2
        crop_size = int(max(fw, fh) * 1.8)
        half = crop_size // 2
        left = max(0, cx - half)
        top = max(0, cy - half)
        right = min(width, cx + half)
        bottom = min(height, cy + half)
        image = image.crop((left, top, right, bottom))
    else:
        # Fallback: center square crop
        side = min(width, height)
        left = (width - side) // 2
        top = (height - side) // 2
        image = image.crop((left, top, left + side, top + side))

    return image.resize((512, 512), Image.LANCZOS)


def load_reference_images(character_key: str, db: Session) -> list[dict[str, Any]]:
    """Load all multi-angle reference images for a character.

    Returns:
        List of dicts: [{"angle": "front", "asset_id": 123, "image_b64": "..."}, ...]
    """
    from models.media_asset import MediaAsset

    char = db.query(Character).filter(Character.name == character_key, Character.deleted_at.is_(None)).first()
    if not char or not char.preview_image_asset_id:
        return []

    asset = db.query(MediaAsset).filter(MediaAsset.id == char.preview_image_asset_id).first()
    if not asset or not asset.url:
        return []

    try:
        img_bytes = load_image_bytes(asset.url)
        image_b64_str = base64.b64encode(img_bytes).decode("utf-8")
        return [{"angle": "front", "asset_id": char.preview_image_asset_id, "image_b64": image_b64_str}]
    except Exception as e:
        logger.warning("[IPAdapter] Failed to load preview image for %s: %s", character_key, e)
        return []


# Angle tag mapping for select_best_reference
_ANGLE_TAG_MAP: dict[str, list[str]] = {
    "side_left": ["from_side", "profile", "side_view", "looking_away"],
    "side_right": ["from_side", "profile", "side_view"],
    "three_quarter": ["three_quarter_view", "looking_to_the_side"],
    "back": ["from_behind", "back", "looking_back"],
}


def select_best_reference(
    prompt_tags: list[str],
    references: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Select the best reference image matching prompt camera angle.

    Args:
        prompt_tags: Tags from the generation prompt
        references: List from load_reference_images()

    Returns:
        Best matching reference dict, or front fallback, or None
    """
    if not references:
        return None

    tag_set = {t.strip().lower().replace(" ", "_") for t in prompt_tags}

    # Try to find matching angle
    for angle, keywords in _ANGLE_TAG_MAP.items():
        if any(kw in tag_set for kw in keywords):
            match = next((r for r in references if r["angle"] == angle), None)
            if match:
                logger.info("📐 [Multi-Ref] Selected '%s' reference for angle tags", angle)
                return match

    # Fallback to front
    front = next((r for r in references if r["angle"] == "front"), None)
    if front:
        return front

    # Fallback to first available
    return references[0]


def build_dual_ip_adapter_args(
    primary_image: str,
    secondary_image: str,
    weight: float | None = None,
    model: str | None = None,
    guidance_start: float | None = None,
    guidance_end: float | None = None,
) -> list[dict[str, Any]]:
    """Build dual IP-Adapter units (primary 70% + secondary 30%).

    Args:
        primary_image: Base64 primary reference
        secondary_image: Base64 secondary reference
        weight: Base weight (split by ratios)
        model: IP-Adapter model type
        guidance_start: Override guidance start
        guidance_end: Override guidance end

    Returns:
        List of 2 ControlNet args dicts
    """
    from services.controlnet import build_ip_adapter_args

    base_weight = weight or DEFAULT_CHARACTER_PRESET.get("weight", 0.35)

    primary_args = build_ip_adapter_args(
        reference_image=primary_image,
        weight=base_weight * IP_ADAPTER_DUAL_PRIMARY_RATIO,
        model=model,
        guidance_start=guidance_start,
        guidance_end=guidance_end,
    )
    secondary_args = build_ip_adapter_args(
        reference_image=secondary_image,
        weight=base_weight * IP_ADAPTER_DUAL_SECONDARY_RATIO,
        model=model,
        guidance_start=guidance_start,
        guidance_end=guidance_end,
    )
    return [primary_args, secondary_args]
