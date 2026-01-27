"""Image validation service using WD14 and Gemini.

Provides tag prediction and prompt-to-image comparison.
"""

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

from config import CACHE_DIR, CACHE_TTL_SECONDS, WD14_MODEL_DIR, WD14_THRESHOLD, gemini_client, logger
from schemas import SceneValidateRequest
from services.image import load_image_bytes

from .keywords import (
    IGNORE_TOKENS,
    expand_synonyms,
    normalize_prompt_token,
    update_keyword_suggestions,
    update_tag_effectiveness,
)

# --- Lazy imports for circular dependency avoidance ---
_parse_json_payload = None
_split_prompt_tokens = None

# --- WD14 model cache ---
_WD14_SESSION: ort.InferenceSession | None = None
_WD14_TAGS: list[str] | None = None
_WD14_TAG_CATEGORIES: list[str] | None = None


def _get_wd14_model_dir() -> Path:
    return WD14_MODEL_DIR


def _get_wd14_threshold() -> float:
    return WD14_THRESHOLD


def _get_gemini_client():
    return gemini_client


def _get_parse_json_payload():
    global _parse_json_payload
    if _parse_json_payload is None:
        from services.utils import parse_json_payload
        _parse_json_payload = parse_json_payload
    return _parse_json_payload


def _get_split_prompt_tokens():
    global _split_prompt_tokens
    if _split_prompt_tokens is None:
        from services.prompt import split_prompt_tokens
        _split_prompt_tokens = split_prompt_tokens
    return _split_prompt_tokens


def resolve_image_mime(image: Image.Image) -> str:
    """Resolve MIME type for an image."""
    fmt = (image.format or "PNG").upper()
    if fmt == "JPEG":
        return "image/jpeg"
    if fmt == "WEBP":
        return "image/webp"
    return "image/png"


def load_wd14_model() -> tuple[ort.InferenceSession, list[str], list[str]]:
    """Load WD14 ONNX model and tags."""
    global _WD14_SESSION, _WD14_TAGS, _WD14_TAG_CATEGORIES
    if _WD14_SESSION and _WD14_TAGS and _WD14_TAG_CATEGORIES:
        return _WD14_SESSION, _WD14_TAGS, _WD14_TAG_CATEGORIES

    model_dir = _get_wd14_model_dir()
    model_path = model_dir / "model.onnx"
    tags_path = model_dir / "selected_tags.csv"
    if not model_path.exists() or not tags_path.exists():
        raise FileNotFoundError("WD14 model files not found.")

    session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    tags: list[str] = []
    categories: list[str] = []
    with tags_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        name_idx = 1
        category_idx = 2
        if headers:
            lowered = [h.strip().lower() for h in headers]
            if "name" in lowered:
                name_idx = lowered.index("name")
            if "category" in lowered:
                category_idx = lowered.index("category")
        for row in reader:
            if len(row) <= max(name_idx, category_idx):
                continue
            tag = row[name_idx].replace("_", " ").strip()
            category = row[category_idx].strip()
            tags.append(tag)
            categories.append(category)

    _WD14_SESSION = session
    _WD14_TAGS = tags
    _WD14_TAG_CATEGORIES = categories
    return session, tags, categories


def wd14_predict_tags(image: Image.Image, threshold: float | None = None) -> list[dict[str, Any]]:
    """Predict tags for an image using WD14 model."""
    if threshold is None:
        threshold = _get_wd14_threshold()

    session, tags, categories = load_wd14_model()
    image = image.convert("RGBA")
    background = Image.new("RGBA", image.size, (255, 255, 255, 255))
    image = Image.alpha_composite(background, image).convert("RGB")
    image = image.resize((448, 448), Image.LANCZOS)
    img_array = np.array(image).astype(np.float32)
    # Note: This WD14 model expects RGB values in 0-255 range (no normalization)
    img_array = np.expand_dims(img_array, axis=0)
    inputs = {session.get_inputs()[0].name: img_array}
    preds = session.run([session.get_outputs()[0].name], inputs)[0][0]

    results: list[dict[str, Any]] = []
    for score, tag, category in zip(preds, tags, categories, strict=False):
        if category == "9":
            continue
        if score < threshold:
            continue
        results.append({"tag": tag, "score": float(score), "category": category})

    results.sort(key=lambda item: item["score"], reverse=True)
    return results


def gemini_predict_tags(image: Image.Image) -> list[dict[str, Any]]:
    """Predict tags for an image using Gemini vision."""
    from google.genai import types

    client = _get_gemini_client()
    if not client:
        raise RuntimeError("Gemini key missing")

    mime_type = resolve_image_mime(image)
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    image_bytes = buf.getvalue()
    instruction = (
        "Analyze the image and return JSON only: "
        "{\"tags\": [\"short tag\", ...]}. "
        "Use Stable Diffusion tag-style nouns/adjectives, no sentences."
    )
    res = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            instruction,
        ],
    )
    parse_json = _get_parse_json_payload()
    data = parse_json(res.text)
    tags = data.get("tags", [])
    results: list[dict[str, Any]] = []
    for tag in tags:
        if not isinstance(tag, str):
            continue
        cleaned = tag.strip()
        if not cleaned:
            continue
        results.append({"tag": cleaned, "score": 1.0, "category": "gemini"})
    return results


def compare_prompt_to_tags(prompt: str, tags: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare prompt tokens to detected image tags."""
    split_tokens = _get_split_prompt_tokens()
    raw_tokens = split_tokens(prompt)
    skip_tokens = {
        # Quality tags (not visually detectable)
        "best quality",
        "masterpiece",
        "high quality",
        "ultra detailed",
        "ultra detail",
        "highres",
        "8k",
        "4k",
        "photorealistic",
        "realistic",
        "stylized",
        "anime",
        "illustration",
        "digital painting",
        "artstation",
        "sharp focus",
        "cinematic",
        # Lighting tags (hard to detect by WD14)
        "natural light",
        "soft lighting",
        "soft light",  # Space format variant
        "hard lighting",
        "dramatic lighting",
        "studio lighting",
        "backlighting",
        "rim lighting",
        "daylight",  # Time of day (WD14 can't detect)
        "sunlight",
        # Mood tags (abstract, not visually detectable)
        "energetic",
        "peaceful",
        "romantic",
        "tense",
        "melancholic",
        "comedic",
        "warm",
        "mysterious",
        "serene",
        "dramatic",
        "content",
        "emotional",
        "nostalgic",
        "hopeful",
        "cheerful",
        "cozy",
        "lively",
        "contemplative",
        "joyful",
        "bittersweet",
        "thinking",
        "excited",
        "anxious",
        "surprised",
        "determined",
        "curious",
        "focused",
        # Time tags (hard to detect visually)
        "morning",
        "afternoon",
        "evening",
        "night",
        "dawn",
        "dusk",
        # Character-specific tags (LoRA-generated, not in WD14 training)
        "eureka",  # Character name from LoRA
        "chibi",  # Style tag from LoRA
        "eyebrow",  # Fine-grained facial feature
        "eyebrow down",
        # Abstract mood
        "flustered",
    }
    tokens = [normalize_prompt_token(token) for token in raw_tokens]
    tokens = [token for token in tokens if token and token not in skip_tokens and token not in IGNORE_TOKENS]
    if not tokens:
        return {"matched": [], "missing": [], "extra": []}

    tag_names = [item["tag"].lower() for item in tags]
    tag_set = set(tag_names)
    expanded_tags = expand_synonyms(list(tag_set))

    matched: list[str] = []
    missing: list[str] = []
    for token in tokens:
        if token in expanded_tags or any(token in tag for tag in tag_set):
            matched.append(token)
        else:
            missing.append(token)

    extra = []
    for item in tags[:20]:
        name = normalize_prompt_token(item["tag"])
        if not name or name in IGNORE_TOKENS:
            continue
        if name not in expand_synonyms(tokens):
            extra.append(item["tag"])

    return {"matched": matched, "missing": missing, "extra": extra}


def cache_key_for_validation(image_bytes: bytes, prompt: str, mode: str) -> str:
    """Generate a cache key for validation results."""
    digest = hashlib.sha256()
    digest.update(image_bytes)
    digest.update(prompt.encode("utf-8"))
    digest.update(mode.encode("utf-8"))
    return digest.hexdigest()
def validate_scene_image(request: SceneValidateRequest) -> dict:
    try:
        image_bytes = load_image_bytes(request.image_b64)
        mode = request.mode.lower().strip() if request.mode else "wd14"
        cache_key = cache_key_for_validation(image_bytes, request.prompt or "", mode)
        cache_file = CACHE_DIR / f"image_validate_{cache_key}.json"
        if cache_file.exists():
            age = time.time() - cache_file.stat().st_mtime
            if age < CACHE_TTL_SECONDS:
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                cached["cached"] = True
                return cached
        image = Image.open(io.BytesIO(image_bytes))
        if mode == "gemini":
            tags = gemini_predict_tags(image)
        else:
            tags = wd14_predict_tags(image, WD14_THRESHOLD)
        comparison = compare_prompt_to_tags(request.prompt or "", tags)
        total = len(comparison["matched"]) + len(comparison["missing"])
        match_rate = (len(comparison["matched"]) / total) if total else 0.0
        from services.keywords import load_known_keywords
        known_keywords = load_known_keywords()
        unknown_tags = []
        for item in tags[:50]:
            name = normalize_prompt_token(item["tag"])
            if not name:
                continue
            if name not in known_keywords:
                unknown_tags.append(name)
        update_keyword_suggestions(unknown_tags)

        # Update tag effectiveness feedback loop
        if request.prompt:
            split_tokens = _get_split_prompt_tokens()
            prompt_tags = split_tokens(request.prompt)
            update_tag_effectiveness(prompt_tags, tags)

        result = {
            "mode": mode,
            "match_rate": match_rate,
            "matched": comparison["matched"],
            "missing": comparison["missing"],
            "extra": comparison["extra"],
            "tags": tags[:20],
            "unknown_tags": unknown_tags[:20],
        }
        cache_file.write_text(json.dumps(result, ensure_ascii=False))
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Scene image validation failed")
        raise HTTPException(status_code=500, detail="Image validation failed") from exc
