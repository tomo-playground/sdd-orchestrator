"""Image validation service using WD14 and Gemini."""

from __future__ import annotations

import csv
import hashlib
import io
from typing import Any

import numpy as np
import onnxruntime as ort
from fastapi import HTTPException
from PIL import Image
from sqlalchemy.orm import Session

from config import WD14_MODEL_DIR, WD14_THRESHOLD, WD14_UNMATCHABLE_TAGS, logger
from schemas import SceneValidateRequest
from services.image import load_image_bytes
from services.keywords import normalize_prompt_token


def _extract_storage_key(image_url: str | None) -> str | None:
    """Extract storage key from various URL formats.

    Handles:
    - Storage key: projects/.../images/scene_xxx.png → as-is
    - Full URL: http://localhost:9000/shorts-producer/projects/... → extract
    - Absolute path: /outputs/images/... → None (irrecoverable)

    Args:
        image_url: URL or path to extract from

    Returns:
        Storage key (e.g., "projects/1/groups/1/storyboards/1/images/scene_123.png")
        or None if irrecoverable
    """
    if not image_url:
        return None

    # Already a storage key
    if image_url.startswith("projects/") or image_url.startswith("shared/"):
        return image_url

    # Extract from MinIO URL (http://localhost:9000/shorts-producer/projects/...)
    if "shorts-producer/" in image_url:
        parts = image_url.split("shorts-producer/", 1)
        return parts[1] if len(parts) > 1 else None

    # Extract from bucket URL pattern (http://host/bucket/projects/...)
    if "/projects/" in image_url:
        parts = image_url.split("/projects/", 1)
        return f"projects/{parts[1]}" if len(parts) > 1 else None

    # Irrecoverable formats (absolute filesystem paths)
    if image_url.startswith("/outputs/"):
        logger.warning("⚠️ Cannot convert absolute path to storage key: %s", image_url)
        return None

    logger.warning("⚠️ Unknown image_url format: %s", image_url)
    return None


_WD14_SESSION: ort.InferenceSession | None = None
_WD14_TAGS: list[str] | None = None
_WD14_TAG_CATEGORIES: list[str] | None = None


def load_wd14_model() -> tuple[ort.InferenceSession, list[str], list[str]]:
    global _WD14_SESSION, _WD14_TAGS, _WD14_TAG_CATEGORIES
    if _WD14_SESSION and _WD14_TAGS and _WD14_TAG_CATEGORIES:
        return _WD14_SESSION, _WD14_TAGS, _WD14_TAG_CATEGORIES

    model_dir = WD14_MODEL_DIR
    model_path = model_dir / "model.onnx"
    tags_path = model_dir / "selected_tags.csv"
    if not model_path.exists() or not tags_path.exists():
        raise FileNotFoundError("WD14 model files not found.")

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    tags, categories = [], []
    with tags_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # headers
        for row in reader:
            if len(row) < 3:
                continue
            tags.append(row[1].strip())
            categories.append(row[2].strip())

    _WD14_SESSION, _WD14_TAGS, _WD14_TAG_CATEGORIES = session, tags, categories
    return session, tags, categories


def wd14_predict_tags(image: Image.Image, threshold: float | None = None) -> list[dict[str, Any]]:
    if threshold is None:
        threshold = WD14_THRESHOLD
    session, tags, categories = load_wd14_model()
    image = image.convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    image = Image.alpha_composite(background, image).convert("RGB")
    image = image.resize((448, 448), Image.LANCZOS)
    img_array = np.array(image).astype(np.float32)
    img_array = np.expand_dims(img_array, axis=0)
    inputs = {session.get_inputs()[0].name: img_array}
    preds = session.run([session.get_outputs()[0].name], inputs)[0][0]

    results = []
    for score, tag, category in zip(preds, tags, categories, strict=False):
        if category == "9" or score < threshold:
            continue
        results.append({"tag": tag, "score": float(score), "category": category})
    results.sort(key=lambda item: item["score"], reverse=True)
    return results


def resolve_image_mime(image: Image.Image) -> str:
    """Resolve MIME type for an image."""
    fmt = (image.format or "PNG").upper()
    if fmt == "JPEG":
        return "image/jpeg"
    if fmt == "WEBP":
        return "image/webp"
    return "image/png"


def cache_key_for_validation(image_bytes: bytes, prompt: str) -> str:
    """Generate a cache key for validation results."""
    digest = hashlib.sha256()
    digest.update(image_bytes)
    digest.update(prompt.encode("utf-8"))
    return digest.hexdigest()


def _is_composite_match(prompt_token: str, tag_set: set[str]) -> bool:
    """Check if a compound prompt token partially matches any detected tag.

    Example: prompt has ``blue_shirt`` but WD14 only detected ``shirt``
    → suffix ``shirt`` is in tag_set → partial match.
    """
    parts = prompt_token.split("_")
    if len(parts) < 2:
        return False
    for i in range(1, len(parts)):
        suffix = "_".join(parts[i:])
        if suffix in tag_set:
            return True
    return False


def _build_synonym_set(token: str) -> set[str]:
    """Return the set of synonyms for *token* using TagAliasCache."""
    from services.keywords.db_cache import TagAliasCache

    synonyms = {token}
    replacement = TagAliasCache.get_replacement(token)
    if replacement is not ... and replacement is not None:
        synonyms.add(replacement)
    # Reverse lookup: find source tags that map to this token
    for source, target in TagAliasCache._cache.items():
        if target == token:
            synonyms.add(source)
    return synonyms


def compare_prompt_to_tags(prompt: str, tags: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare prompt tokens against WD14-detected tags.

    Returns dict with matched, partial_matched, missing, extra, skipped lists.
    """
    from services.prompt import split_prompt_tokens

    tokens = [normalize_prompt_token(t) for t in split_prompt_tokens(prompt)]
    tokens = [t for t in tokens if t]

    if not tokens:
        return {
            "matched": [],
            "missing": [],
            "extra": [],
            "skipped": [],
            "partial_matched": [],
        }

    tag_set = {normalize_prompt_token(item["tag"]) for item in tags}

    matched: list[str] = []
    partial_matched: list[str] = []
    missing: list[str] = []
    skipped: list[str] = []

    for t in tokens:
        # 0) WD14 unmatchable → skip (not counted in match_rate)
        if t in WD14_UNMATCHABLE_TAGS:
            skipped.append(t)
            continue

        # 1) Exact match
        if t in tag_set:
            matched.append(t)
            continue

        # 2) Synonym match (via TagAliasCache)
        synonyms = _build_synonym_set(t)
        if synonyms & tag_set:
            matched.append(t)
            continue

        # 3) Composite / suffix match
        if _is_composite_match(t, tag_set):
            partial_matched.append(t)
            continue

        # 4) Not found
        missing.append(t)

    # EXTRA: high-confidence WD14 tags not accounted for by prompt
    matched_set = set(matched) | set(partial_matched)
    extra: list[str] = []
    for item in tags:
        if item["score"] < 0.5:
            continue
        name = normalize_prompt_token(item["tag"])
        if not name or name in WD14_UNMATCHABLE_TAGS or name in matched_set:
            continue
        extra.append(item["tag"])

    return {
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "skipped": skipped,
        "partial_matched": partial_matched,
    }


def validate_scene_image(request: SceneValidateRequest, db: Session | None = None) -> dict:
    """Validate scene image using WD14 tagger.

    Args:
        request: SceneValidateRequest with image (image_b64 or image_url) and prompt
        db: Database session (optional, for saving validation results)

    Returns:
        Validation result dict with match_rate, matched/missing/extra tags
    """
    try:
        source = request.image_b64 or request.image_url
        if not source:
            raise ValueError("Either image_b64 or image_url must be provided")
        image_bytes = load_image_bytes(source)
        image = Image.open(io.BytesIO(image_bytes))
        tags = wd14_predict_tags(image, WD14_THRESHOLD)
        comparison = compare_prompt_to_tags(request.prompt or "", tags)
        n_matched = len(comparison["matched"]) + len(comparison["partial_matched"])
        total = n_matched + len(comparison["missing"])
        match_rate = (n_matched / total) if total else 0.0

        # Create/Update validation score in DB (if db session provided)
        if db is not None:
            # Use scene_id (DB PK) if provided, fallback to scene_index
            actual_scene_id = request.scene_id or request.scene_index or 0

            _save_scene_quality_score(
                db=db,
                storyboard_id=request.storyboard_id,
                scene_id=actual_scene_id,
                prompt=request.prompt,
                match_rate=match_rate,
                matched=comparison["matched"],
                missing=comparison["missing"],
                extra=comparison["extra"],
            )

            _update_activity_log_match_rate(
                db=db,
                storyboard_id=request.storyboard_id,
                scene_id=actual_scene_id,
                match_rate=match_rate,
            )

            _increment_tag_effectiveness(
                db=db,
                matched_tags=comparison["matched"],
                missing_tags=comparison["missing"],
            )

        return {
            "mode": "wd14",
            "match_rate": match_rate,
            "matched": comparison["matched"],
            "missing": comparison["missing"],
            "extra": comparison["extra"],
            "skipped": comparison["skipped"],
            "partial_matched": comparison["partial_matched"],
            "tags": tags[:20],
        }
    except Exception as exc:
        logger.exception("Validation failed")
        raise HTTPException(status_code=500, detail="Validation failed") from exc


def _save_scene_quality_score(
    db: Session,
    storyboard_id: int | None,
    scene_id: int,
    prompt: str,
    match_rate: float,
    matched: list,
    missing: list,
    extra: list,
):
    """Save scene quality score to database."""
    from datetime import datetime

    from models.scene_quality import SceneQualityScore

    try:
        # Verify scene_id exists (scenes may be recreated during PUT with new IDs)
        if scene_id is not None:
            from models.scene import Scene

            exists = db.query(Scene.id).filter(Scene.id == scene_id).first()
            if not exists:
                logger.warning(
                    "[QualityScore] scene_id %d not found (likely recreated), skipping save",
                    scene_id,
                )
                return

        score = SceneQualityScore(
            storyboard_id=storyboard_id,
            scene_id=scene_id,
            prompt=prompt,
            match_rate=match_rate,
            matched_tags=matched,
            missing_tags=missing,
            extra_tags=extra,
            validated_at=datetime.utcnow(),
        )
        db.add(score)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save quality score: {e}")
        db.rollback()


def _update_activity_log_match_rate(
    db: Session,
    storyboard_id: int | None,
    scene_id: int | None,
    match_rate: float,
):
    """Update activity log with match rate."""
    if not storyboard_id or scene_id is None:
        return

    from models.activity_log import ActivityLog

    try:
        log = (
            db.query(ActivityLog)
            .filter(ActivityLog.storyboard_id == storyboard_id, ActivityLog.scene_id == scene_id)
            .order_by(ActivityLog.created_at.desc())
            .first()
        )
        if log:
            log.match_rate = match_rate
            log.status = "success" if match_rate >= 0.7 else "fail"
            db.commit()
    except Exception:
        db.rollback()


def _increment_tag_effectiveness(
    db: Session,
    matched_tags: list[str],
    missing_tags: list[str],
) -> None:
    """Increment tag_effectiveness counters from WD14 validation results.

    - matched_tags: use_count++ AND match_count++
    - missing_tags: use_count++ only
    - Tags in WD14_UNMATCHABLE_TAGS or not in DB are skipped.
    """
    from models.tag import Tag, TagEffectiveness

    all_tags = set(matched_tags) | set(missing_tags)
    if not all_tags:
        return

    try:
        for tag_name in all_tags:
            if tag_name in WD14_UNMATCHABLE_TAGS:
                continue

            tag = db.query(Tag).filter(Tag.name == tag_name).first()
            if not tag:
                continue

            eff = db.query(TagEffectiveness).filter(TagEffectiveness.tag_id == tag.id).first()
            if not eff:
                eff = TagEffectiveness(tag_id=tag.id, use_count=0, match_count=0, effectiveness=0.0)
                db.add(eff)

            eff.use_count += 1
            if tag_name in matched_tags:
                eff.match_count += 1
            eff.effectiveness = eff.match_count / eff.use_count

        db.commit()
    except Exception as e:
        logger.error("Failed to update tag effectiveness: %s", e)
        db.rollback()
