"""Activity log routes for analytics and pattern learning."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import logger
from database import get_db
from models.activity_log import ActivityLog

router = APIRouter(prefix="/activity-logs", tags=["activity-logs"])


class CreateActivityLogRequest(BaseModel):
    """Request for creating an activity log."""

    storyboard_id: int | None = None
    scene_id: int
    character_id: int | None = None
    prompt: str | None = None
    negative_prompt: str | None = None
    tags: list[str] | None = None
    sd_params: dict | None = None
    match_rate: float | None = None
    seed: int | None = None
    status: str | None = "pending"  # success, fail, pending
    image_url: str | None = None


class UpdateStatusRequest(BaseModel):
    """Request for updating activity log status."""

    status: str  # success, fail, pending


@router.post("")
def create_activity_log(request: CreateActivityLogRequest, db: Session = Depends(get_db)):
    """Create a new activity log entry.

    Example request:
    ```json
    {
        "storyboard_id": 1,
        "scene_id": 0,
        "character_id": 3,
        "prompt": "1girl, smiling, classroom, ...",
        "tags": ["1girl", "smiling", "classroom"],
        "sd_params": {"steps": 20, "cfg_scale": 7, "seed": 12345},
        "match_rate": 0.85,
        "seed": 12345,
        "status": "success",
        "image_url": "/outputs/images/scene_0.png"
    }
    ```

    Returns:
    ```json
    {
        "id": 1,
        "storyboard_id": 1,
        "scene_id": 0,
        "character_id": 3,
        ...
    }
    ```
    """
    try:
        # Lookup media_asset_id from image URL
        media_asset_id = None
        if request.image_url and not request.image_url.startswith("data:"):
            from services.validation import _extract_storage_key
            storage_key = _extract_storage_key(request.image_url)
            if storage_key:
                from models.media_asset import MediaAsset
                asset = db.query(MediaAsset).filter(
                    MediaAsset.storage_key == storage_key
                ).first()
                if asset:
                    media_asset_id = asset.id

        log = ActivityLog(
            storyboard_id=request.storyboard_id,
            scene_id=request.scene_id,
            character_id=request.character_id,
            prompt=request.prompt or "",
            negative_prompt=request.negative_prompt,
            tags_used=request.tags,
            sd_params=request.sd_params,
            match_rate=request.match_rate,
            seed=request.seed,
            status=request.status or "pending",
            media_asset_id=media_asset_id,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        logger.info(
            f"Created activity log: storyboard={request.storyboard_id}, "
            f"scene={request.scene_id}, status={request.status}"
        )

        return {
            "id": log.id,
            "storyboard_id": log.storyboard_id,
            "scene_id": log.scene_id,
            "character_id": log.character_id,
            "status": log.status,
            "match_rate": log.match_rate,
        }
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create activity log")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/storyboard/{storyboard_id}")
def get_storyboard_logs(storyboard_id: int, status: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    """Get activity logs for a storyboard.

    Query parameters:
    - status: Filter by status (success, fail, pending)
    - limit: Max number of results (default: 100)
    """
    try:
        query = db.query(ActivityLog).filter(ActivityLog.storyboard_id == storyboard_id)

        if status:
            query = query.filter(ActivityLog.status == status)

        logs = query.order_by(ActivityLog.created_at.desc()).limit(limit).all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "storyboard_id": log.storyboard_id,
                    "scene_id": log.scene_id,
                    "character_id": log.character_id,
                    "prompt": log.prompt,
                    "tags": log.tags_used,
                    "sd_params": log.sd_params,
                    "match_rate": log.match_rate,
                    "seed": log.seed,
                    "status": log.status,
                    "image_url": log.image_url,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
            "total": len(logs),
        }
    except Exception as exc:
        logger.exception(f"Failed to get logs for storyboard {storyboard_id}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{storyboard_id}/logs")
def get_storyboard_logs_v2(storyboard_id: int, status: str | None = None, limit: int = 100, db: Session = Depends(get_db)):
    """Compatibility alias for get_storyboard_logs."""
    return get_storyboard_logs(storyboard_id, status, limit, db)


@router.patch("/{log_id}/status")
def update_log_status(log_id: int, request: UpdateStatusRequest, db: Session = Depends(get_db)):
    """Update the status of an activity log.

    Example request:
    ```json
    {
        "status": "success"
    }
    ```

    Returns updated log.
    """
    try:
        log = db.query(ActivityLog).filter(ActivityLog.id == log_id).first()

        if not log:
            raise HTTPException(status_code=404, detail=f"Log {log_id} not found")

        log.status = request.status
        db.commit()
        db.refresh(log)

        logger.info(f"Updated activity log {log_id} status to {request.status}")

        return {
            "id": log.id,
            "status": log.status,
            "match_rate": log.match_rate,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(f"Failed to update log {log_id} status")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete("/{log_id}")
def delete_log(log_id: int, db: Session = Depends(get_db)):
    """Delete an activity log."""
    try:
        log = db.query(ActivityLog).filter(ActivityLog.id == log_id).first()

        if not log:
            raise HTTPException(status_code=404, detail=f"Log {log_id} not found")

        db.delete(log)
        db.commit()

        logger.info(f"Deleted activity log {log_id}")

        return {"message": f"Log {log_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(f"Failed to delete log {log_id}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/analyze/patterns")
def analyze_patterns(
    storyboard_id: int,
    min_occurrences: int = 3,
    match_rate_threshold: float = 0.7,
    db: Session = Depends(get_db),
):
    """Analyze activity patterns for a storyboard."""
    try:
        # Base query
        query = db.query(ActivityLog).filter(
            ActivityLog.storyboard_id == storyboard_id,
            ActivityLog.status.in_(["success", "fail"]),
            ActivityLog.tags_used.isnot(None),
        )

        logs = query.all()

        if not logs:
            return {
                "summary": {
                    "total_logs": 0,
                    "success_count": 0,
                    "fail_count": 0,
                    "avg_match_rate": 0,
                },
                "tag_stats": [],
                "conflict_candidates": [],
            }

        # Calculate summary
        success_logs = [log for log in logs if log.status == "success" or (log.match_rate and log.match_rate >= match_rate_threshold)]
        fail_logs = [log for log in logs if log.status == "fail" or (log.match_rate and log.match_rate < match_rate_threshold)]

        total_match_rates = [log.match_rate for log in logs if log.match_rate is not None]
        avg_match_rate = sum(total_match_rates) / len(total_match_rates) if total_match_rates else 0

        # Tag statistics
        tag_counts = {}  # {tag: {"total": int, "success": int, "fail": int, "match_rates": list}}

        for log in logs:
            if not log.tags_used:
                continue

            is_success = log in success_logs

            for tag in log.tags_used:
                if tag not in tag_counts:
                    tag_counts[tag] = {"total": 0, "success": 0, "fail": 0, "match_rates": []}

                tag_counts[tag]["total"] += 1
                if is_success:
                    tag_counts[tag]["success"] += 1
                else:
                    tag_counts[tag]["fail"] += 1

                if log.match_rate is not None:
                    tag_counts[tag]["match_rates"].append(log.match_rate)

        # Build tag stats (filter by min_occurrences)
        tag_stats = []
        for tag, counts in tag_counts.items():
            if counts["total"] < min_occurrences:
                continue

            success_rate = counts["success"] / counts["total"] if counts["total"] > 0 else 0
            avg_tag_match_rate = sum(counts["match_rates"]) / len(counts["match_rates"]) if counts["match_rates"] else 0

            tag_stats.append({
                "tag": tag,
                "total": counts["total"],
                "success": counts["success"],
                "fail": counts["fail"],
                "success_rate": round(success_rate, 2),
                "avg_match_rate": round(avg_tag_match_rate, 2),
            })

        # Sort by success rate (lowest first to find problematic tags)
        tag_stats.sort(key=lambda x: x["success_rate"])

        # Find conflict candidates (tag pairs that often appear together and fail)
        tag_pair_stats = {}  # {(tag1, tag2): {"total": int, "fail": int, "match_rates": list}}

        for log in logs:
            if not log.tags_used or len(log.tags_used) < 2:
                continue

            is_fail = log in fail_logs

            # Check all tag pairs
            for i, tag1 in enumerate(log.tags_used):
                for tag2 in log.tags_used[i+1:]:
                    # Normalize pair (alphabetical order)
                    pair = tuple(sorted([tag1, tag2]))

                    if pair not in tag_pair_stats:
                        tag_pair_stats[pair] = {"total": 0, "fail": 0, "match_rates": []}

                    tag_pair_stats[pair]["total"] += 1
                    if is_fail:
                        tag_pair_stats[pair]["fail"] += 1

                    if log.match_rate is not None:
                        tag_pair_stats[pair]["match_rates"].append(log.match_rate)

        # Build conflict candidates (pairs with high fail rate)
        conflict_candidates = []
        for (tag1, tag2), stats in tag_pair_stats.items():
            if stats["total"] < min_occurrences:
                continue

            fail_rate = stats["fail"] / stats["total"] if stats["total"] > 0 else 0
            avg_pair_match_rate = sum(stats["match_rates"]) / len(stats["match_rates"]) if stats["match_rates"] else 0

            # Only include pairs with high fail rate (>= 50%)
            if fail_rate >= 0.5:
                conflict_candidates.append({
                    "tag1": tag1,
                    "tag2": tag2,
                    "co_occurrence": stats["total"],
                    "fail_count": stats["fail"],
                    "fail_rate": round(fail_rate, 2),
                    "avg_match_rate": round(avg_pair_match_rate, 2),
                })

        # Sort by fail rate (highest first)
        conflict_candidates.sort(key=lambda x: (-x["fail_rate"], -x["co_occurrence"]))

        logger.info(
            f"[Analyze Patterns] storyboard={storyboard_id}, logs={len(logs)}, "
            f"tags={len(tag_stats)}, conflicts={len(conflict_candidates)}"
        )

        return {
            "summary": {
                "total_logs": len(logs),
                "success_count": len(success_logs),
                "fail_count": len(fail_logs),
                "avg_match_rate": round(avg_match_rate, 2),
            },
            "tag_stats": tag_stats,
            "conflict_candidates": conflict_candidates[:20],  # Top 20 conflict candidates
        }

    except Exception as exc:
        logger.exception("Failed to analyze patterns")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/suggest-conflict-rules")
def suggest_conflict_rules(
    storyboard_id: int,
    min_occurrences: int = 5,
    fail_rate_threshold: float = 0.6,
    db: Session = Depends(get_db),
):
    """Suggest new conflict rules based on activity log patterns.

    Analyzes tag pairs with high fail rates and suggests them as conflict rules.
    Only suggests pairs that don't already exist in the tag_rules table.

    Query parameters:
    - min_occurrences: Minimum co-occurrences to consider (default: 5)
    - fail_rate_threshold: Minimum fail rate to suggest (default: 0.6 = 60%)

    Returns:
    ```json
    {
        "suggested_rules": [
            {
                "tag1": "upper body",
                "tag2": "full body",
                "co_occurrence": 10,
                "fail_count": 8,
                "fail_rate": 0.80,
                "avg_match_rate": 0.45,
                "reason": "High fail rate (80%) in 10 generations"
            }
        ],
        "existing_rules_count": 126,
        "new_rules_count": 5
    }
    ```
    """
    try:
        from models.tag import Tag, TagRule

        # Get conflict candidates from pattern analysis
        query = db.query(ActivityLog).filter(
            ActivityLog.storyboard_id == storyboard_id,
            ActivityLog.status.in_(["success", "fail"]),
            ActivityLog.tags_used.isnot(None),
        )

        logs = query.all()

        if not logs:
            return {
                "suggested_rules": [],
                "existing_rules_count": 0,
                "new_rules_count": 0,
            }

        # Calculate fail logs
        [log for log in logs if log.status == "success" or (log.match_rate and log.match_rate >= 0.7)]
        fail_logs = [log for log in logs if log.status == "fail" or (log.match_rate and log.match_rate < 0.7)]

        # Find tag pairs with high fail rate
        tag_pair_stats = {}

        for log in logs:
            if not log.tags_used or len(log.tags_used) < 2:
                continue

            is_fail = log in fail_logs

            for i, tag1 in enumerate(log.tags_used):
                for tag2 in log.tags_used[i+1:]:
                    pair = tuple(sorted([tag1, tag2]))

                    if pair not in tag_pair_stats:
                        tag_pair_stats[pair] = {"total": 0, "fail": 0, "match_rates": []}

                    tag_pair_stats[pair]["total"] += 1
                    if is_fail:
                        tag_pair_stats[pair]["fail"] += 1

                    if log.match_rate is not None:
                        tag_pair_stats[pair]["match_rates"].append(log.match_rate)

        # Build conflict candidates
        candidates = []
        for (tag1, tag2), stats in tag_pair_stats.items():
            if stats["total"] < min_occurrences:
                continue

            fail_rate = stats["fail"] / stats["total"] if stats["total"] > 0 else 0
            avg_match_rate = sum(stats["match_rates"]) / len(stats["match_rates"]) if stats["match_rates"] else 0

            if fail_rate >= fail_rate_threshold:
                candidates.append({
                    "tag1": tag1,
                    "tag2": tag2,
                    "co_occurrence": stats["total"],
                    "fail_count": stats["fail"],
                    "fail_rate": round(fail_rate, 2),
                    "avg_match_rate": round(avg_match_rate, 2),
                })

        # Get existing conflict rules to filter out duplicates
        existing_rules = db.query(TagRule).filter(TagRule.rule_type == "conflict").all()

        # Build set of existing tag name pairs
        existing_pairs = set()
        for rule in existing_rules:
            source_tag = db.query(Tag).filter(Tag.id == rule.source_tag_id).first()
            target_tag = db.query(Tag).filter(Tag.id == rule.target_tag_id).first()
            if source_tag and target_tag:
                pair = tuple(sorted([source_tag.name, target_tag.name]))
                existing_pairs.add(pair)

        # Filter out existing rules
        new_candidates = []
        for candidate in candidates:
            pair = tuple(sorted([candidate["tag1"], candidate["tag2"]]))
            if pair not in existing_pairs:
                candidate["reason"] = (
                    f"High fail rate ({int(candidate['fail_rate']*100)}%) "
                    f"in {candidate['co_occurrence']} generations"
                )
                new_candidates.append(candidate)

        # Sort by fail rate (highest first)
        new_candidates.sort(key=lambda x: (-x["fail_rate"], -x["co_occurrence"]))

        logger.info(
            f"[Suggest Conflict Rules] storyboard={storyboard_id}, "
            f"candidates={len(candidates)}, new={len(new_candidates)}, existing={len(existing_pairs)}"
        )

        return {
            "suggested_rules": new_candidates[:20],  # Top 20 suggestions
            "existing_rules_count": len(existing_pairs),
            "new_rules_count": len(new_candidates),
        }

    except Exception as exc:
        logger.exception("Failed to suggest conflict rules")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/success-combinations")
def get_success_combinations(
    storyboard_id: int,
    match_rate_threshold: float = 0.7,
    min_occurrences: int = 3,
    top_n_per_category: int = 5,
    db: Session = Depends(get_db),
):
    """Generate optimal tag combinations based on successful activities.

    Analyzes successful logs and extracts high-performing tag combinations
    grouped by category (expression, pose, camera, environment, etc.).

    Query parameters:
    - match_rate_threshold: Minimum match rate for "success" (default: 0.7)
    - min_occurrences: Minimum tag occurrences to include (default: 3)
    - top_n_per_category: Number of top tags per category (default: 5)

    Returns:
    ```json
    {
        "summary": {
            "total_success": 75,
            "analyzed_tags": 120,
            "categories_found": 8
        },
        "combinations_by_category": {
            "expression": [
                {
                    "tag": "smile",
                    "success_rate": 0.95,
                    "occurrences": 50,
                    "avg_match_rate": 0.88
                }
            ],
            "pose": [...],
            "camera": [...],
            "environment": [...]
        },
        "suggested_combinations": [
            {
                "tags": ["smile", "standing", "cowboy shot", "classroom"],
                "categories": ["expression", "pose", "camera", "environment"],
                "avg_success_rate": 0.92,
                "conflict_free": true
            }
        ]
    }
    ```
    """
    try:
        from models.tag import Tag, TagRule

        # Get successful logs
        query = db.query(ActivityLog).filter(
            ActivityLog.storyboard_id == storyboard_id,
            ActivityLog.tags_used.isnot(None),
        )

        logs = query.all()

        # Filter success logs
        success_logs = [
            log for log in logs
            if log.status == "success" or (log.match_rate and log.match_rate >= match_rate_threshold)
        ]

        if not success_logs:
            return {
                "summary": {
                    "total_success": 0,
                    "analyzed_tags": 0,
                    "categories_found": 0,
                },
                "combinations_by_category": {},
                "suggested_combinations": [],
            }

        # Get all tags from DB with categories
        all_tags = db.query(Tag).all()
        tag_category_map = {tag.name: tag.category for tag in all_tags}
        tag_group_map = {tag.name: tag.group_name for tag in all_tags}

        # Calculate tag statistics from success logs
        tag_stats = {}  # {tag: {"occurrences": int, "match_rates": [float], "category": str}}

        for log in success_logs:
            if not log.tags_used:
                continue

            for tag in log.tags_used:
                if tag not in tag_stats:
                    tag_stats[tag] = {
                        "occurrences": 0,
                        "match_rates": [],
                        "category": tag_category_map.get(tag, "unknown"),
                        "group": tag_group_map.get(tag),
                    }

                tag_stats[tag]["occurrences"] += 1
                if log.match_rate is not None:
                    tag_stats[tag]["match_rates"].append(log.match_rate)

        # Filter by min_occurrences and group by category
        combinations_by_category = {}

        for tag, stats in tag_stats.items():
            if stats["occurrences"] < min_occurrences:
                continue

            category = stats["category"]
            avg_match_rate = sum(stats["match_rates"]) / len(stats["match_rates"]) if stats["match_rates"] else 0
            success_rate = stats["occurrences"] / len(success_logs)

            tag_data = {
                "tag": tag,
                "success_rate": round(success_rate, 2),
                "occurrences": stats["occurrences"],
                "avg_match_rate": round(avg_match_rate, 2),
                "group": stats["group"],
            }

            if category not in combinations_by_category:
                combinations_by_category[category] = []

            combinations_by_category[category].append(tag_data)

        # Sort each category by success_rate and take top N
        for category in combinations_by_category:
            combinations_by_category[category].sort(
                key=lambda x: (-x["success_rate"], -x["avg_match_rate"])
            )
            combinations_by_category[category] = combinations_by_category[category][:top_n_per_category]

        # Get conflict rules
        conflict_rules = db.query(TagRule).filter(TagRule.rule_type == "conflict").all()
        conflict_pairs = set()

        for rule in conflict_rules:
            source_tag = db.query(Tag).filter(Tag.id == rule.source_tag_id).first()
            target_tag = db.query(Tag).filter(Tag.id == rule.target_tag_id).first()
            if source_tag and target_tag:
                conflict_pairs.add(tuple(sorted([source_tag.name, target_tag.name])))

        # Generate suggested combinations
        # Strategy: Pick top 1 from each key category (expression, pose, camera, environment)
        suggested_combinations = []

        key_categories = ["expression", "pose", "camera", "environment", "lighting", "mood"]
        available_categories = {cat: tags for cat, tags in combinations_by_category.items() if cat in key_categories and tags}

        if available_categories:
            # Generate combination from top tags
            combination_tags = []
            combination_categories = []

            for category in key_categories:
                if category in available_categories and available_categories[category]:
                    top_tag = available_categories[category][0]
                    combination_tags.append(top_tag["tag"])
                    combination_categories.append(category)

            # Check for conflicts
            has_conflict = False
            for i, tag1 in enumerate(combination_tags):
                for tag2 in combination_tags[i+1:]:
                    pair = tuple(sorted([tag1, tag2]))
                    if pair in conflict_pairs:
                        has_conflict = True
                        break
                if has_conflict:
                    break

            # Calculate average success rate
            avg_success_rate = sum(
                next((t["success_rate"] for t in combinations_by_category.get(cat, []) if t["tag"] == tag), 0)
                for cat, tag in zip(combination_categories, combination_tags, strict=False)
            ) / len(combination_tags) if combination_tags else 0

            suggested_combinations.append({
                "tags": combination_tags,
                "categories": combination_categories,
                "avg_success_rate": round(avg_success_rate, 2),
                "conflict_free": not has_conflict,
            })

        logger.info(
            f"[Success Combinations] storyboard={storyboard_id}, success_logs={len(success_logs)}, "
            f"categories={len(combinations_by_category)}, combinations={len(suggested_combinations)}"
        )

        return {
            "summary": {
                "total_success": len(success_logs),
                "analyzed_tags": len(tag_stats),
                "categories_found": len(combinations_by_category),
            },
            "combinations_by_category": combinations_by_category,
            "suggested_combinations": suggested_combinations,
        }

    except Exception as exc:
        logger.exception("Failed to generate success combinations")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class ApplyConflictRulesRequest(BaseModel):
    """Request for applying suggested conflict rules."""

    rules: list[dict]  # [{"tag1": str, "tag2": str}, ...]


@router.post("/apply-conflict-rules")
def apply_conflict_rules(request: ApplyConflictRulesRequest, db: Session = Depends(get_db)):
    """Apply suggested conflict rules to the database.

    Creates bidirectional conflict rules for each tag pair.

    Example request:
    ```json
    {
        "rules": [
            {"tag1": "upper body", "tag2": "full body"},
            {"tag1": "indoors", "tag2": "outdoors"}
        ]
    }
    ```

    Returns:
    ```json
    {
        "applied_count": 4,  # 2 rules × 2 directions = 4 entries
        "skipped_count": 2,
        "details": [
            {"tag1": "upper body", "tag2": "full body", "status": "applied"},
            {"tag1": "indoors", "tag2": "outdoors", "status": "skipped", "reason": "tags not found in DB"}
        ]
    }
    ```
    """
    try:
        from models.tag import Tag, TagRule

        applied = 0
        skipped = 0
        details = []

        for rule in request.rules:
            tag1_name = rule["tag1"]
            tag2_name = rule["tag2"]

            # Get tag IDs
            tag1 = db.query(Tag).filter(Tag.name == tag1_name).first()
            tag2 = db.query(Tag).filter(Tag.name == tag2_name).first()

            if not tag1 or not tag2:
                skipped += 1
                details.append({
                    "tag1": tag1_name,
                    "tag2": tag2_name,
                    "status": "skipped",
                    "reason": "One or both tags not found in DB",
                })
                continue

            # Check if rule already exists (bidirectional)
            existing = db.query(TagRule).filter(
                TagRule.rule_type == "conflict",
                TagRule.source_tag_id == tag1.id,
                TagRule.target_tag_id == tag2.id,
            ).first()

            if existing:
                skipped += 1
                details.append({
                    "tag1": tag1_name,
                    "tag2": tag2_name,
                    "status": "skipped",
                    "reason": "Rule already exists",
                })
                continue

            # Create bidirectional conflict rules
            rule1 = TagRule(
                source_tag_id=tag1.id,
                target_tag_id=tag2.id,
                rule_type="conflict",
            )
            rule2 = TagRule(
                source_tag_id=tag2.id,
                target_tag_id=tag1.id,
                rule_type="conflict",
            )

            db.add(rule1)
            db.add(rule2)
            applied += 2  # Bidirectional = 2 entries

            details.append({
                "tag1": tag1_name,
                "tag2": tag2_name,
                "status": "applied",
            })

        db.commit()

        logger.info(
            f"[Apply Conflict Rules] applied={applied}, skipped={skipped}"
        )

        return {
            "applied_count": applied,
            "skipped_count": skipped,
            "details": details,
        }

    except Exception as exc:
        db.rollback()
        logger.exception("Failed to apply conflict rules")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
