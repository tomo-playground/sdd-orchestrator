"""Image validation service using WD14 and Gemini."""

from __future__ import annotations
import csv
import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any
import numpy as np
import onnxruntime as ort
from fastapi import HTTPException
from PIL import Image

from config import CACHE_DIR, CACHE_TTL_SECONDS, WD14_MODEL_DIR, WD14_THRESHOLD, logger
from schemas import SceneValidateRequest
from services.image import load_image_bytes
from services.keywords import normalize_prompt_token

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
        next(reader, None) # headers
        for row in reader:
            if len(row) < 3: continue
            tags.append(row[1].strip())
            categories.append(row[2].strip())

    _WD14_SESSION, _WD14_TAGS, _WD14_TAG_CATEGORIES = session, tags, categories
    return session, tags, categories

def wd14_predict_tags(image: Image.Image, threshold: float | None = None) -> list[dict[str, Any]]:
    if threshold is None: threshold = WD14_THRESHOLD
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
        if category == "9" or score < threshold: continue
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

def compare_prompt_to_tags(prompt: str, tags: list[dict[str, Any]]) -> dict[str, Any]:
    from services.prompt import split_prompt_tokens
    
    # Tokens to skip during comparison (abstract, quality, or lighting tags)
    SKIP_KEYWORDS = {
        "masterpiece", "best_quality", "high_quality", "normal_quality", "worst_quality",
        "absurdres", "incredibly_absurdres", "soft_lighting", "natural_light", "natural_lighting",
        "dramatic_lighting", "volumetric_lighting", "beautiful_lighting", "peaceful", 
        "romantic", "mysterious", "morning", "night", "dawn", "dusk", "evening"
    }

    tokens = [normalize_prompt_token(t) for t in split_prompt_tokens(prompt)]
    # Filter out empty tokens and skip keywords
    tokens = [t for t in tokens if t and t not in SKIP_KEYWORDS]
    
    if not tokens:
        return {"matched": [], "missing": [], "extra": []}

    # Normalize prediction tags for comparison
    tag_set = {normalize_prompt_token(item["tag"]) for item in tags}
    
    matched = []
    missing = []
    
    for t in tokens:
        # Exact match or substring match (e.g. "hair" matches "blue_hair")
        if t in tag_set or any(t in tag for tag in tag_set):
            matched.append(t)
        else:
            missing.append(t)
    
    extra = []
    for item in tags[:20]:
        name = normalize_prompt_token(item["tag"])
        if name and name not in SKIP_KEYWORDS and name not in matched:
            # Check if it was part of a matched token (reverse substring)
            if not any(name in m for m in matched):
                extra.append(item["tag"])

    return {"matched": matched, "missing": missing, "extra": extra}

def validate_scene_image(request: SceneValidateRequest) -> dict:
    try:
        image_bytes = load_image_bytes(request.image_b64)
        image = Image.open(io.BytesIO(image_bytes))
        tags = wd14_predict_tags(image, WD14_THRESHOLD)
        comparison = compare_prompt_to_tags(request.prompt or "", tags)
        total = len(comparison["matched"]) + len(comparison["missing"])
        match_rate = (len(comparison["matched"]) / total) if total else 0.0

        # Create/Update validation score in DB
        _save_scene_quality_score(
            project_name=request.topic or f"session_{request.session_id}" if request.session_id else "unknown",
            scene_id=request.scene_index or 0,
            image_url=f"/outputs/images/scene_{hashlib.sha1(image_bytes).hexdigest()[:16]}.png", # dummy or resolved path
            prompt=request.prompt,
            match_rate=match_rate,
            matched=comparison["matched"],
            missing=comparison["missing"],
            extra=comparison["extra"]
        )

        _update_activity_log_match_rate(
            project_name=f"daily_{request.session_id}" if request.session_id else None,
            scene_id=request.scene_index,
            match_rate=match_rate
        )

        return {
            "mode": "wd14",
            "match_rate": match_rate,
            "matched": comparison["matched"],
            "missing": comparison["missing"],
            "extra": comparison["extra"],
            "tags": tags[:20],
        }
    except Exception as exc:
        logger.exception("Validation failed")
        raise HTTPException(status_code=500, detail="Validation failed") from exc

def _save_scene_quality_score(project_name: str, scene_id: int, image_url: str, prompt: str, match_rate: float, matched: list, missing: list, extra: list):
    from datetime import datetime
    from database import SessionLocal
    from models.scene_quality import SceneQualityScore
    
    db = SessionLocal()
    try:
        score = SceneQualityScore(
            project_name=project_name,
            scene_id=scene_id,
            image_url=image_url,
            prompt=prompt,
            match_rate=match_rate,
            matched_tags=matched,
            missing_tags=missing,
            extra_tags=extra,
            validated_at=datetime.utcnow()
        )
        db.add(score)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save quality score: {e}")
        db.rollback()
    finally:
        db.close()

def _update_activity_log_match_rate(project_name: str | None, scene_id: int | None, match_rate: float):
    if not project_name or scene_id is None: return
    from database import SessionLocal
    from models.activity_log import ActivityLog
    db = SessionLocal()
    try:
        log = db.query(ActivityLog).filter(
            ActivityLog.project_name == project_name,
            ActivityLog.scene_id == scene_id
        ).order_by(ActivityLog.created_at.desc()).first()
        if log:
            log.match_rate = match_rate
            log.status = "success" if match_rate >= 0.7 else "fail"
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()