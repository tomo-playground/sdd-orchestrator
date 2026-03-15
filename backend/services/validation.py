"""Image validation service using WD14 and Gemini."""

from __future__ import annotations

import asyncio
import base64
import csv
import hashlib
import io
from datetime import UTC, datetime
from typing import Any

import numpy as np
import onnxruntime as ort
from fastapi import HTTPException
from PIL import Image
from sqlalchemy.orm import Session

from config import (
    GEMINI_DETECTABLE_GROUPS,
    GEMINI_EVAL_BATCH_CONCURRENCY,
    SKIPPABLE_GROUPS,
    WD14_DETECTABLE_GROUPS,
    WD14_MODEL_DIR,
    WD14_THRESHOLD,
    logger,
)
from schemas import SceneValidateRequest
from services.image import load_image_bytes
from services.keywords import normalize_prompt_token
from services.validation_gemini import evaluate_tags_with_gemini


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
        logger.debug("Cannot convert absolute path to storage key: %s", image_url)
        return None

    logger.debug("Unknown image_url format: %s", image_url)
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


def _get_tag_group(token: str) -> str | None:
    """Return the group_name for a token, stripping weight markers first."""
    from services.keywords.db_cache import TagCategoryCache

    stripped = token.strip()
    if stripped.startswith("(") and ":" in stripped:
        stripped = stripped.lstrip("(").split(":")[0]
    stripped = stripped.strip("()")
    return TagCategoryCache.get_category(stripped)


def _is_skippable_tag(token: str) -> bool:
    """Check if a tag belongs to a skippable group or is DB-unregistered."""
    group = _get_tag_group(token)
    return group in SKIPPABLE_GROUPS or group is None


def classify_prompt_tokens(prompt: str) -> dict[str, list[str]]:
    """Classify prompt tokens into wd14/gemini/skipped by group_name.

    Returns dict with wd14_tokens, gemini_tokens, skipped_tokens lists.
    """
    from services.prompt import split_prompt_tokens

    tokens = [normalize_prompt_token(t) for t in split_prompt_tokens(prompt)]
    tokens = [t for t in tokens if t]

    wd14_tokens: list[str] = []
    gemini_tokens: list[str] = []
    skipped_tokens: list[str] = []

    for t in tokens:
        group = _get_tag_group(t)
        if group in SKIPPABLE_GROUPS or group is None:
            skipped_tokens.append(t)
        elif group in WD14_DETECTABLE_GROUPS:
            wd14_tokens.append(t)
        elif group in GEMINI_DETECTABLE_GROUPS:
            gemini_tokens.append(t)
        else:
            skipped_tokens.append(t)

    return {
        "wd14_tokens": wd14_tokens,
        "gemini_tokens": gemini_tokens,
        "skipped_tokens": skipped_tokens,
    }


def compare_prompt_to_tags(
    prompt: str,
    tags: list[dict[str, Any]],
    *,
    only_tokens: list[str] | None = None,
) -> dict[str, Any]:
    """Compare prompt tokens against WD14-detected tags.

    Args:
        prompt: The prompt string to tokenize (ignored if only_tokens given).
        tags: WD14-detected tags.
        only_tokens: If provided, compare only these tokens instead of
            tokenizing the full prompt. Used by hybrid mode to pass
            pre-classified wd14_tokens.

    Returns dict with matched, partial_matched, missing, extra, skipped lists.
    """
    if only_tokens is not None:
        tokens = only_tokens
    else:
        from services.prompt import split_prompt_tokens  # noqa: PLC0415

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
        # 0) Skippable group or DB-unregistered → skip
        if _is_skippable_tag(t):
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
        if not name or _is_skippable_tag(name) or name in matched_set:
            continue
        extra.append(item["tag"])

    return {
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "skipped": skipped,
        "partial_matched": partial_matched,
    }


def compute_adjusted_match_rate(
    matched: list[str],
    partial_matched: list[str],
    missing: list[str],
) -> float:
    """Compute match rate using only WD14-detectable group tags.

    .. deprecated:: Phase 33
        Replaced by hybrid match rate in ``validate_scene_image()``.
        Kept for backward compatibility with existing callers.

    Returns 0.0 if no detectable tokens exist.
    """
    from services.keywords.db_cache import TagCategoryCache

    detectable_matched = 0
    detectable_total = 0

    for token in matched:
        group = TagCategoryCache.get_category(token)
        if group and group in WD14_DETECTABLE_GROUPS:
            detectable_matched += 1
            detectable_total += 1

    for token in partial_matched:
        group = TagCategoryCache.get_category(token)
        if group and group in WD14_DETECTABLE_GROUPS:
            detectable_matched += 1
            detectable_total += 1

    for token in missing:
        group = TagCategoryCache.get_category(token)
        if group and group in WD14_DETECTABLE_GROUPS:
            detectable_total += 1

    return (detectable_matched / detectable_total) if detectable_total else 0.0


def validate_scene_image(request: SceneValidateRequest, db: Session | None = None) -> dict:
    """Validate scene image using WD14 + Gemini hybrid (Phase 33).

    Phase 1 (synchronous): WD14 evaluates visual tags → immediate match_rate.
    Phase 2 (deferred):    Gemini evaluates non-visual tags → updated later.

    Returns:
        Validation result dict with match_rate, matched/missing/extra tags,
        plus gemini_tokens list for deferred evaluation.
    """
    try:
        source = request.image_b64 or request.image_url
        if not source:
            raise ValueError("Either image_b64 or image_url must be provided")
        image_bytes = load_image_bytes(source)
        image = Image.open(io.BytesIO(image_bytes))
        tags = wd14_predict_tags(image, WD14_THRESHOLD)

        # Phase 33: Classify tokens by evaluation method
        classification = classify_prompt_tokens(request.prompt or "")
        wd14_tokens = classification["wd14_tokens"]
        gemini_tokens = classification["gemini_tokens"]
        skipped_tokens = classification["skipped_tokens"]

        # WD14 comparison: only wd14_tokens (pre-classified)
        comparison = compare_prompt_to_tags(
            request.prompt or "",
            tags,
            only_tokens=wd14_tokens,
        )

        # WD14-only match rate (immediate)
        n_wd14_matched = len(comparison["matched"]) + len(comparison["partial_matched"])
        wd14_total = n_wd14_matched + len(comparison["missing"])
        wd14_rate = (n_wd14_matched / wd14_total) if wd14_total else 0.0

        # Combined match rate: WD14 now + Gemini pending (updated later via C-4)
        # Gemini tokens count as "pending" — not yet matched or missing
        n_gemini = len(gemini_tokens)
        combined_total = wd14_total + n_gemini
        match_rate = (n_wd14_matched / combined_total) if combined_total else 0.0

        # Identity score
        identity_score = None
        identity_signature = None
        if request.character_id and db is not None:
            from services.identity_score import (
                compute_identity_score,
                extract_identity_signature,
                load_character_identity_tags,
            )

            identity_tags = load_character_identity_tags(request.character_id, db)
            if identity_tags:
                identity_score = compute_identity_score(identity_tags, tags)
            identity_signature = extract_identity_signature(tags, db)

        if db is not None:
            actual_scene_id = request.scene_id or request.scene_index or None

            if actual_scene_id:
                _save_scene_quality_score(
                    db=db,
                    storyboard_id=request.storyboard_id,
                    scene_id=actual_scene_id,
                    prompt=request.prompt,
                    match_rate=match_rate,
                    matched=comparison["matched"],
                    missing=comparison["missing"],
                    extra=comparison["extra"],
                    identity_score=identity_score,
                    identity_tags_detected=identity_signature,
                )

                _update_activity_log_match_rate(
                    db=db,
                    storyboard_id=request.storyboard_id,
                    scene_id=actual_scene_id,
                    match_rate=match_rate,
                )
            else:
                logger.debug("[QualityScore] No scene_id provided, skipping save")

            _increment_tag_effectiveness(
                db=db,
                matched_tags=comparison["matched"],
                missing_tags=comparison["missing"],
            )

        from services.critical_failure import detect_critical_failure

        critical = detect_critical_failure(request.prompt or "", tags)

        # Store image_b64 for deferred Gemini evaluation
        image_b64_clean = base64.b64encode(image_bytes).decode("ascii")

        return {
            "mode": "hybrid",
            "match_rate": match_rate,
            "adjusted_match_rate": wd14_rate,  # backward compat (deprecated)
            "wd14_match_rate": wd14_rate,
            "matched": comparison["matched"],
            "missing": comparison["missing"],
            "extra": comparison["extra"],
            "skipped": skipped_tokens,
            "partial_matched": comparison["partial_matched"],
            "tags": [t["tag"] for t in tags[:20]],
            "critical_failure": critical.to_dict() if critical.has_failure else None,
            "identity_score": identity_score,
            # Phase 33: Gemini deferred evaluation data
            "gemini_tokens": gemini_tokens,
            "image_b64": image_b64_clean,
            # Internal: for background Gemini task
            "wd14_matched": n_wd14_matched,
            "wd14_total": wd14_total,
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
    identity_score: float | None = None,
    identity_tags_detected: dict | None = None,
):
    """Save scene quality score to database."""

    from models.scene_quality import SceneQualityScore

    try:
        # Verify scene_id FK target exists (allow soft-deleted scenes for FK validity)
        if scene_id is not None:
            from models.scene import Scene

            exists = db.query(Scene.id).filter(Scene.id == scene_id).first()
            if not exists:
                logger.warning("[QualityScore] scene_id %d not found, skipping save", scene_id)
                return

        score = SceneQualityScore(
            storyboard_id=storyboard_id,
            scene_id=scene_id,
            prompt=prompt,
            match_rate=match_rate,
            matched_tags=matched,
            missing_tags=missing,
            extra_tags=extra,
            identity_score=identity_score,
            identity_tags_detected=identity_tags_detected,
            validated_at=datetime.now(UTC),
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
    - Tags in skippable groups or not in WD14_DETECTABLE_GROUPS are skipped.
    """
    from models.tag import Tag, TagEffectiveness
    from services.keywords.db_cache import TagCategoryCache

    all_tags = set(matched_tags) | set(missing_tags)
    if not all_tags:
        return

    try:
        for tag_name in all_tags:
            # Skip tags not in WD14-detectable groups
            group = TagCategoryCache.get_category(tag_name)
            if not group or group not in WD14_DETECTABLE_GROUPS:
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


async def apply_gemini_evaluation(
    *,
    storyboard_id: int | None,
    scene_id: int | None,
    image_b64: str,
    gemini_tokens: list[str],
    wd14_matched: int,
    wd14_total: int,
    db_factory: Any = None,
) -> dict[str, Any] | None:
    """Run deferred Gemini evaluation and update DB match_rate.

    Called as a background task after the WD14 synchronous response.

    Args:
        storyboard_id: Storyboard ID for DB lookup.
        scene_id: Scene ID for DB lookup.
        image_b64: Base64-encoded image.
        gemini_tokens: Tags to evaluate with Gemini.
        wd14_matched: Number of WD14-matched tokens (for combined rate).
        wd14_total: Total WD14-evaluated tokens.
        db_factory: Callable returning a DB session (for background use).

    Returns:
        Gemini evaluation summary dict, or None on failure.
    """
    if not gemini_tokens:
        return None

    results = await evaluate_tags_with_gemini(image_b64, gemini_tokens)
    if not results:
        logger.info("[MatchRate] Gemini returned no results for scene %s", scene_id)
        return None

    # Count Gemini matches (confidence >= 0.5 and present=True)
    gemini_matched = sum(1 for r in results if r.get("present") and r.get("confidence", 0) >= 0.5)
    gemini_total = len(results)

    # Combined match rate
    combined_matched = wd14_matched + gemini_matched
    combined_total = wd14_total + gemini_total
    combined_rate = (combined_matched / combined_total) if combined_total else 0.0

    summary = {
        "gemini_matched": gemini_matched,
        "gemini_total": gemini_total,
        "combined_match_rate": combined_rate,
        "details": results,
    }

    if scene_id and db_factory:
        _update_db_match_rate(
            scene_id=scene_id,
            storyboard_id=storyboard_id,
            combined_rate=combined_rate,
            wd14_matched=wd14_matched,
            wd14_total=wd14_total,
            gemini_matched=gemini_matched,
            gemini_total=gemini_total,
            gemini_details=results,
            db_factory=db_factory,
        )

    return summary


async def batch_apply_gemini_evaluation(
    *,
    items: list[dict[str, Any]],
    db_factory: Any = None,
    concurrency: int = GEMINI_EVAL_BATCH_CONCURRENCY,
) -> list[dict[str, Any] | None]:
    """Batch Gemini evaluation with image-based deduplication (Phase 33 E-2).

    Merges Gemini tags for scenes sharing the same image → single API call.
    Different images are evaluated in parallel with semaphore control.

    Args:
        items: List of dicts with keys:
            storyboard_id, scene_id, image_b64, gemini_tokens,
            wd14_matched, wd14_total.
        db_factory: Callable returning a DB session context manager.
        concurrency: Max concurrent Gemini API calls.

    Returns:
        List of Gemini evaluation summaries (same order as items).
    """
    import hashlib
    from collections import defaultdict

    if not items:
        return []

    # Group by image hash → deduplicate Gemini calls
    image_groups: dict[str, list[int]] = defaultdict(list)  # hash → item indices
    image_b64_map: dict[str, str] = {}  # hash → image_b64

    for idx, item in enumerate(items):
        if not item.get("gemini_tokens"):
            continue
        img_hash = hashlib.sha256(item["image_b64"].encode("ascii")).hexdigest()[:16]
        image_groups[img_hash].append(idx)
        image_b64_map[img_hash] = item["image_b64"]

    if not image_groups:
        return [None] * len(items)

    # Merge tags per image → single Gemini call
    sem = asyncio.Semaphore(concurrency)
    results_map: dict[str, list[dict]] = {}  # hash → gemini results

    async def _eval_group(img_hash: str) -> None:
        indices = image_groups[img_hash]
        # Union of all gemini_tokens for this image
        all_tags: list[str] = []
        seen: set[str] = set()
        for idx in indices:
            for tag in items[idx]["gemini_tokens"]:
                if tag not in seen:
                    all_tags.append(tag)
                    seen.add(tag)

        async with sem:
            try:
                results_map[img_hash] = await evaluate_tags_with_gemini(image_b64_map[img_hash], all_tags)
            except Exception as exc:
                logger.error("[MatchRate] Gemini eval failed for group %s: %s", img_hash, exc)
                results_map[img_hash] = []

    await asyncio.gather(*[_eval_group(h) for h in image_groups])

    # Map results back to individual scenes
    output: list[dict[str, Any] | None] = [None] * len(items)
    for img_hash, indices in image_groups.items():
        all_results = results_map.get(img_hash, [])

        for idx in indices:
            item = items[idx]
            scene_tokens = set(item["gemini_tokens"])
            scene_results = [r for r in all_results if r["tag"] in scene_tokens]

            gemini_matched = sum(1 for r in scene_results if r.get("present") and r.get("confidence", 0) >= 0.5)
            gemini_total = len(scene_results)

            wd14_m = item["wd14_matched"]
            wd14_t = item["wd14_total"]
            combined_matched = wd14_m + gemini_matched
            combined_total = wd14_t + gemini_total
            combined_rate = (combined_matched / combined_total) if combined_total else 0.0

            summary = {
                "gemini_matched": gemini_matched,
                "gemini_total": gemini_total,
                "combined_match_rate": combined_rate,
                "details": scene_results,
            }
            output[idx] = summary

            if item.get("scene_id") and db_factory:
                _update_db_match_rate(
                    scene_id=item["scene_id"],
                    storyboard_id=item.get("storyboard_id"),
                    combined_rate=combined_rate,
                    wd14_matched=wd14_m,
                    wd14_total=wd14_t,
                    gemini_matched=gemini_matched,
                    gemini_total=gemini_total,
                    gemini_details=scene_results,
                    db_factory=db_factory,
                )

    n_calls = len(image_groups)
    n_scenes = sum(len(idxs) for idxs in image_groups.values())
    logger.info(
        "[MatchRate] Batch Gemini: %d scenes → %d API calls (saved %d)",
        n_scenes,
        n_calls,
        n_scenes - n_calls,
    )
    return output


def _update_db_match_rate(
    *,
    scene_id: int,
    storyboard_id: int | None,
    combined_rate: float,
    wd14_matched: int,
    wd14_total: int,
    gemini_matched: int,
    gemini_total: int,
    gemini_details: list[dict] | None = None,
    db_factory: Any,
) -> None:
    """Persist combined match_rate + evaluation_details to SceneQualityScore."""
    from models.scene_quality import SceneQualityScore

    try:
        with db_factory() as db:
            score = (
                db.query(SceneQualityScore)
                .filter(
                    SceneQualityScore.scene_id == scene_id,
                    SceneQualityScore.storyboard_id == storyboard_id,
                )
                .order_by(SceneQualityScore.validated_at.desc())
                .first()
            )
            if score:
                score.match_rate = combined_rate
                score.evaluation_details = {
                    "mode": "hybrid",
                    "wd14": {"matched": wd14_matched, "total": wd14_total},
                    "gemini": {
                        "matched": gemini_matched,
                        "total": gemini_total,
                        "tags": gemini_details or [],
                    },
                }
                db.commit()
                logger.info(
                    "[MatchRate] Updated scene %d: %.1f%% → %.1f%% (Gemini +%d/%d)",
                    scene_id,
                    (wd14_matched / wd14_total * 100) if wd14_total else 0,
                    combined_rate * 100,
                    gemini_matched,
                    gemini_total,
                )
    except Exception as exc:
        logger.error("[MatchRate] DB update failed: %s", exc)
