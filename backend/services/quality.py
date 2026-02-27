"""Quality measurement service for scenes.

Provides batch validation and quality score tracking using WD14.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image

from config import OUTPUT_DIR, logger
from services.validation import compare_prompt_to_tags, compute_adjusted_match_rate, wd14_predict_tags

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def batch_validate_scenes(
    scenes: list[dict[str, Any]],
    db: Session,
    storyboard_id: int,
) -> dict[str, Any]:
    """Validate all scenes in a project and save quality scores.

    Args:
        scenes: List of scene dictionaries with image_url and prompt
        db: Database session
        storyboard_id: ID of the storyboard

    Returns:
        {
            "total": int,
            "validated": int,
            "average_match_rate": float,
            "scores": [{"scene_id": int, "match_rate": float, ...}, ...]
        }
    """
    from models.scene_quality import SceneQualityScore
    from services.identity_score import compute_identity_score, extract_identity_signature, load_character_identity_tags

    results = []
    validated_count = 0

    for scene in scenes:
        scene_id = scene.get("scene_id")
        image_url = scene.get("image_url")
        prompt = scene.get("prompt", "")
        character_id = scene.get("character_id")

        if not image_url:
            logger.warning(f"Scene {scene_id} has no image_url, skipping")
            continue

        try:
            # Load image from file system
            image_path = _resolve_image_path(image_url)
            if not image_path or not image_path.exists():
                logger.warning(f"Image not found: {image_url}")
                continue

            image = Image.open(image_path)

            # Run WD14 validation
            tags = wd14_predict_tags(image)
            comparison = compare_prompt_to_tags(prompt, tags)

            # Calculate match rate (include partial_matched like validation.py)
            n_matched = len(comparison["matched"]) + len(comparison["partial_matched"])
            total = n_matched + len(comparison["missing"])
            match_rate = (n_matched / total) if total else 0.0

            adjusted = compute_adjusted_match_rate(
                comparison["matched"],
                comparison["partial_matched"],
                comparison["missing"],
            )

            # Identity score + signature (Phase 16-D)
            id_score = None
            id_signature = None
            if character_id:
                identity_tags = load_character_identity_tags(character_id, db)
                if identity_tags:
                    id_score = compute_identity_score(identity_tags, tags)
                id_signature = extract_identity_signature(tags, db)

            # Save to database
            score = SceneQualityScore(
                storyboard_id=storyboard_id,
                scene_id=scene_id,
                prompt=prompt,
                match_rate=match_rate,
                matched_tags=comparison["matched"],
                missing_tags=comparison["missing"],
                extra_tags=comparison["extra"],
                identity_score=id_score,
                identity_tags_detected=id_signature,
                validated_at=datetime.now(UTC),
            )
            db.add(score)
            validated_count += 1

            results.append(
                {
                    "scene_id": scene_id,
                    "match_rate": round(match_rate, 3),
                    "adjusted_match_rate": round(adjusted, 3),
                    "matched_count": len(comparison["matched"]),
                    "missing_count": len(comparison["missing"]),
                    "identity_score": round(id_score, 3) if id_score is not None else None,
                }
            )

        except Exception as exc:
            logger.exception(f"Failed to validate scene {scene_id}: {exc}")
            continue

    try:
        db.commit()
    except Exception as exc:
        logger.error("Failed to commit batch quality scores: %s", exc)
        db.rollback()

    # Calculate average
    avg_match_rate = sum(r["match_rate"] for r in results) / len(results) if results else 0.0

    return {
        "total": len(scenes),
        "validated": validated_count,
        "average_match_rate": round(avg_match_rate, 3),
        "scores": results,
    }


def get_quality_summary(db: Session, storyboard_id: int) -> dict[str, Any]:
    """Get quality summary for a project or storyboard.

    Args:
        db: Database session
        storyboard_id: ID of the storyboard

    Returns:
        {
            "total_scenes": int,
            "average_match_rate": float,
            "excellent_count": int,  # >= 80%
            "good_count": int,       # 70-80%
            "poor_count": int,       # < 70%
            "scores": [...]
        }
    """
    from models.scene_quality import SceneQualityScore

    query = db.query(SceneQualityScore)

    if storyboard_id:
        query = query.filter(SceneQualityScore.storyboard_id == storyboard_id)
    else:
        return {
            "total_scenes": 0,
            "average_match_rate": 0.0,
            "excellent_count": 0,
            "good_count": 0,
            "poor_count": 0,
            "scores": [],
        }

    scores = query.order_by(SceneQualityScore.scene_id).all()

    if not scores:
        return {
            "total_scenes": 0,
            "average_match_rate": 0.0,
            "excellent_count": 0,
            "good_count": 0,
            "poor_count": 0,
            "scores": [],
        }

    match_rates = [s.match_rate for s in scores if s.match_rate is not None]
    avg_match_rate = sum(match_rates) / len(match_rates) if match_rates else 0.0

    # Categorize scores
    excellent = sum(1 for r in match_rates if r >= 0.8)
    good = sum(1 for r in match_rates if 0.7 <= r < 0.8)
    poor = sum(1 for r in match_rates if r < 0.7)

    return {
        "total_scenes": len(scores),
        "average_match_rate": round(avg_match_rate, 3),
        "excellent_count": excellent,
        "good_count": good,
        "poor_count": poor,
        "scores": [
            {
                "scene_id": s.scene_id,
                "match_rate": round(s.match_rate, 3) if s.match_rate else 0.0,
                "matched_tags": s.matched_tags or [],
                "missing_tags": s.missing_tags or [],
                "validated_at": s.validated_at.isoformat() if s.validated_at else None,
            }
            for s in scores
        ],
    }


def get_quality_alerts(threshold: float, db: Session, storyboard_id: int) -> list[dict[str, Any]]:
    """Get scenes with quality below threshold.

    Args:
        threshold: Match rate threshold (default: 0.7)
        db: Database session
        storyboard_id: ID of the storyboard

    Returns:
        [{"scene_id": int, "match_rate": float, "missing_tags": [...], ...}, ...]
    """
    from sqlalchemy.orm import joinedload

    from models.scene_quality import SceneQualityScore

    poor_scores = (
        db.query(SceneQualityScore)
        .options(joinedload(SceneQualityScore.scene))
        .filter(
            SceneQualityScore.storyboard_id == storyboard_id,
            SceneQualityScore.match_rate < threshold,
        )
        .order_by(SceneQualityScore.match_rate)
        .all()
    )

    return [
        {
            "scene_id": s.scene_id,
            "match_rate": round(s.match_rate, 3) if s.match_rate else 0.0,
            "missing_tags": s.missing_tags or [],
            "prompt": s.prompt,
            "image_url": s.image_url,
        }
        for s in poor_scores
    ]


def _resolve_image_path(image_url: str) -> Path | None:
    """Resolve image URL to file system path.

    Args:
        image_url: Image URL (e.g., "/outputs/images/scene_1.png")

    Returns:
        Absolute path to image file, or None if cannot be resolved
    """
    # Remove leading /outputs if present
    if image_url.startswith("/outputs/"):
        relative = image_url[len("/outputs/") :]
    elif image_url.startswith("outputs/"):
        relative = image_url[len("outputs/") :]
    else:
        relative = image_url

    path = OUTPUT_DIR / relative
    return path if path.exists() else None
