"""Cross-scene character consistency analysis (Phase 16-D).

Computes drift between a character's DB baseline identity tags and
WD14-detected tags across all scenes in a storyboard.
"""

from __future__ import annotations

from typing import Any, TypedDict

from config import IDENTITY_GROUP_WEIGHTS, IDENTITY_SCORE_GROUPS, logger


class GroupDrift(TypedDict):
    group: str
    baseline_tags: list[str]
    detected_tags: list[str]
    status: str  # match | mismatch | missing | extra | no_data
    weight: float


class SceneDrift(TypedDict):
    scene_id: int
    scene_order: int
    character_id: int
    identity_score: float
    drift_score: float
    groups: list[GroupDrift]


class ConsistencyResult(TypedDict):
    storyboard_id: int
    overall_consistency: float
    scenes: list[SceneDrift]


def compute_group_drift(
    group: str,
    baseline_tags: list[str],
    detected_tags: list[str],
) -> GroupDrift:
    """Compare baseline vs detected tags for a single identity group.

    Status rules:
    - no_data: both empty or detected empty with no baseline
    - match: detected tags overlap with baseline (at least one common tag)
    - missing: baseline has tags but none detected
    - extra: no baseline but tags detected
    - mismatch: both have tags but no overlap
    """
    weight = IDENTITY_GROUP_WEIGHTS.get(group, 0.5)
    b_set = set(baseline_tags)
    d_set = set(detected_tags)

    if not b_set and not d_set:
        return GroupDrift(
            group=group, baseline_tags=baseline_tags, detected_tags=detected_tags,
            status="no_data", weight=weight,
        )

    if not d_set:
        return GroupDrift(
            group=group, baseline_tags=baseline_tags, detected_tags=detected_tags,
            status="missing", weight=weight,
        )

    if not b_set:
        return GroupDrift(
            group=group, baseline_tags=baseline_tags, detected_tags=detected_tags,
            status="extra", weight=weight,
        )

    if b_set & d_set:
        return GroupDrift(
            group=group, baseline_tags=baseline_tags, detected_tags=detected_tags,
            status="match", weight=weight,
        )

    return GroupDrift(
        group=group, baseline_tags=baseline_tags, detected_tags=detected_tags,
        status="mismatch", weight=weight,
    )


def compute_scene_drift(
    baseline_by_group: dict[str, list[str]],
    signature: dict[str, list[str]],
) -> tuple[float, list[GroupDrift]]:
    """Compute weighted drift score for a single scene.

    Returns:
        (drift_score, groups) where drift_score is 0.0 (perfect) ~ 1.0 (total drift).
    """
    groups: list[GroupDrift] = []
    weighted_drift = 0.0
    total_weight = 0.0

    for group in IDENTITY_SCORE_GROUPS:
        baseline = baseline_by_group.get(group, [])
        detected = signature.get(group, [])
        drift = compute_group_drift(group, baseline, detected)
        groups.append(drift)

        if drift["status"] == "no_data":
            continue

        total_weight += drift["weight"]
        if drift["status"] in ("mismatch", "missing"):
            weighted_drift += drift["weight"]
        elif drift["status"] == "extra":
            weighted_drift += drift["weight"] * 0.5

    drift_score = (weighted_drift / total_weight) if total_weight > 0 else 0.0
    return drift_score, groups


def _load_baseline_by_group(character_id: int, db: Any) -> dict[str, list[str]]:
    """Load character identity tags grouped by group_name."""
    from models.associations import CharacterTag
    from models.tag import Tag

    rows = (
        db.query(Tag.name, Tag.group_name)
        .join(CharacterTag, CharacterTag.tag_id == Tag.id)
        .filter(
            CharacterTag.character_id == character_id,
            Tag.group_name.in_(IDENTITY_SCORE_GROUPS),
        )
        .all()
    )

    baseline: dict[str, list[str]] = {g: [] for g in IDENTITY_SCORE_GROUPS}
    for row in rows:
        baseline[row.group_name].append(row.name)
    return baseline


def compute_storyboard_consistency(
    storyboard_id: int,
    db: Any,
) -> ConsistencyResult:
    """Compute cross-scene consistency for all characters in a storyboard.

    Uses cached identity_tags_detected from scene_quality_scores when available.
    """
    from models.scene import Scene
    from models.scene_quality import SceneQualityScore
    from models.storyboard import Storyboard
    from models.storyboard_character import StoryboardCharacter

    storyboard = db.query(Storyboard).filter(Storyboard.id == storyboard_id).first()
    if not storyboard:
        return ConsistencyResult(
            storyboard_id=storyboard_id, overall_consistency=1.0, scenes=[],
        )

    # Build speaker → character_id mapping
    sc_rows = (
        db.query(StoryboardCharacter)
        .filter(StoryboardCharacter.storyboard_id == storyboard_id)
        .all()
    )
    speaker_to_char: dict[str, int] = {sc.speaker: sc.character_id for sc in sc_rows}

    if not speaker_to_char:
        return ConsistencyResult(
            storyboard_id=storyboard_id, overall_consistency=1.0, scenes=[],
        )

    # Cache baselines per character
    baselines: dict[int, dict[str, list[str]]] = {}
    for char_id in set(speaker_to_char.values()):
        baselines[char_id] = _load_baseline_by_group(char_id, db)

    # Load scenes with their latest quality scores
    scenes = (
        db.query(Scene)
        .filter(Scene.storyboard_id == storyboard_id, Scene.deleted_at.is_(None))
        .order_by(Scene.order)
        .all()
    )

    scene_drifts: list[SceneDrift] = []
    for scene in scenes:
        character_id = speaker_to_char.get(scene.speaker)
        if not character_id:
            continue

        # Try cached identity_tags_detected
        latest_score = (
            db.query(SceneQualityScore)
            .filter(SceneQualityScore.scene_id == scene.id)
            .order_by(SceneQualityScore.validated_at.desc())
            .first()
        )

        signature = None
        cached_identity_score = None
        if latest_score and latest_score.identity_tags_detected:
            signature = latest_score.identity_tags_detected
            cached_identity_score = latest_score.identity_score

        if not signature:
            logger.debug("Scene %d: no cached identity signature, skipping", scene.id)
            continue

        baseline = baselines[character_id]
        drift_score, groups = compute_scene_drift(baseline, signature)

        identity_score = cached_identity_score if cached_identity_score is not None else (1.0 - drift_score)

        scene_drifts.append(
            SceneDrift(
                scene_id=scene.id,
                scene_order=scene.order,
                character_id=character_id,
                identity_score=round(identity_score, 3),
                drift_score=round(drift_score, 3),
                groups=groups,
            )
        )

    # Overall consistency = 1 - average drift
    if scene_drifts:
        avg_drift = sum(s["drift_score"] for s in scene_drifts) / len(scene_drifts)
        overall = round(1.0 - avg_drift, 3)
    else:
        overall = 1.0

    return ConsistencyResult(
        storyboard_id=storyboard_id,
        overall_consistency=overall,
        scenes=scene_drifts,
    )
