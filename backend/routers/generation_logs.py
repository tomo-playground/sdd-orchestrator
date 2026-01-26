"""Generation log routes for analytics and pattern learning."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from config import logger
from database import SessionLocal
from models.generation_log import GenerationLog

router = APIRouter(prefix="/generation-logs", tags=["generation-logs"])


class CreateGenerationLogRequest(BaseModel):
    """Request for creating a generation log."""

    project_name: str
    scene_index: int
    prompt: str | None = None
    tags: list[str] | None = None
    sd_params: dict | None = None
    match_rate: float | None = None
    seed: int | None = None
    status: str | None = "pending"  # success, fail, pending
    image_url: str | None = None


class UpdateStatusRequest(BaseModel):
    """Request for updating generation log status."""

    status: str  # success, fail, pending


@router.post("")
def create_generation_log(request: CreateGenerationLogRequest):
    """Create a new generation log entry.

    Example request:
    ```json
    {
        "project_name": "my_project",
        "scene_index": 0,
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
        "project_name": "my_project",
        "scene_index": 0,
        ...
    }
    ```
    """
    db = SessionLocal()
    try:
        log = GenerationLog(
            project_name=request.project_name,
            scene_index=request.scene_index,
            prompt=request.prompt,
            tags=request.tags,
            sd_params=request.sd_params,
            match_rate=request.match_rate,
            seed=request.seed,
            status=request.status,
            image_url=request.image_url,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        logger.info(
            f"Created generation log: project={request.project_name}, "
            f"scene={request.scene_index}, status={request.status}"
        )

        return {
            "id": log.id,
            "project_name": log.project_name,
            "scene_index": log.scene_index,
            "status": log.status,
            "match_rate": log.match_rate,
        }
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create generation log")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/project/{project_name}")
def get_project_logs(project_name: str, status: str | None = None, limit: int = 100):
    """Get generation logs for a project.

    Query parameters:
    - status: Filter by status (success, fail, pending)
    - limit: Max number of results (default: 100)

    Returns:
    ```json
    {
        "logs": [
            {
                "id": 1,
                "scene_index": 0,
                "match_rate": 0.85,
                "status": "success",
                ...
            }
        ],
        "total": 10
    }
    ```
    """
    db = SessionLocal()
    try:
        query = db.query(GenerationLog).filter(GenerationLog.project_name == project_name)

        if status:
            query = query.filter(GenerationLog.status == status)

        logs = query.order_by(GenerationLog.created_at.desc()).limit(limit).all()

        return {
            "logs": [
                {
                    "id": log.id,
                    "project_name": log.project_name,
                    "scene_index": log.scene_index,
                    "prompt": log.prompt,
                    "tags": log.tags,
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
        logger.exception(f"Failed to get logs for project {project_name}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.patch("/{log_id}/status")
def update_log_status(log_id: int, request: UpdateStatusRequest):
    """Update the status of a generation log.

    Example request:
    ```json
    {
        "status": "success"
    }
    ```

    Returns updated log.
    """
    db = SessionLocal()
    try:
        log = db.query(GenerationLog).filter(GenerationLog.id == log_id).first()

        if not log:
            raise HTTPException(status_code=404, detail=f"Log {log_id} not found")

        log.status = request.status
        db.commit()
        db.refresh(log)

        logger.info(f"Updated generation log {log_id} status to {request.status}")

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
    finally:
        db.close()


@router.delete("/{log_id}")
def delete_log(log_id: int):
    """Delete a generation log."""
    db = SessionLocal()
    try:
        log = db.query(GenerationLog).filter(GenerationLog.id == log_id).first()

        if not log:
            raise HTTPException(status_code=404, detail=f"Log {log_id} not found")

        db.delete(log)
        db.commit()

        logger.info(f"Deleted generation log {log_id}")

        return {"message": f"Log {log_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception(f"Failed to delete log {log_id}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.close()


@router.get("/analyze/patterns")
def analyze_patterns(
    project_name: str | None = None,
    min_occurrences: int = 3,
    match_rate_threshold: float = 0.7,
):
    """Analyze generation patterns to find successful tags and conflicts.

    Query parameters:
    - project_name: Filter by project (optional)
    - min_occurrences: Minimum tag occurrences to include (default: 3)
    - match_rate_threshold: Match rate threshold for "success" (default: 0.7)

    Returns:
    ```json
    {
        "summary": {
            "total_logs": 100,
            "success_count": 75,
            "fail_count": 25,
            "avg_match_rate": 0.82
        },
        "tag_stats": [
            {
                "tag": "smile",
                "total": 50,
                "success": 45,
                "fail": 5,
                "success_rate": 0.90,
                "avg_match_rate": 0.85
            }
        ],
        "conflict_candidates": [
            {
                "tag1": "upper body",
                "tag2": "full body",
                "co_occurrence": 10,
                "fail_rate": 0.80,
                "avg_match_rate": 0.45
            }
        ]
    }
    ```
    """
    db = SessionLocal()
    try:
        # Base query
        query = db.query(GenerationLog).filter(
            GenerationLog.status.in_(["success", "fail"]),
            GenerationLog.tags.isnot(None),
        )
        if project_name:
            query = query.filter(GenerationLog.project_name == project_name)

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
            if not log.tags:
                continue

            is_success = log in success_logs

            for tag in log.tags:
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
            if not log.tags or len(log.tags) < 2:
                continue

            is_fail = log in fail_logs

            # Check all tag pairs
            for i, tag1 in enumerate(log.tags):
                for tag2 in log.tags[i+1:]:
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
            f"[Analyze Patterns] project={project_name}, logs={len(logs)}, "
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
    finally:
        db.close()


@router.get("/suggest-conflict-rules")
def suggest_conflict_rules(
    project_name: str | None = None,
    min_occurrences: int = 5,
    fail_rate_threshold: float = 0.6,
):
    """Suggest new conflict rules based on generation log patterns.

    Analyzes tag pairs with high fail rates and suggests them as conflict rules.
    Only suggests pairs that don't already exist in the tag_rules table.

    Query parameters:
    - project_name: Filter by project (optional)
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
    db = SessionLocal()
    try:
        from models.tag import Tag, TagRule

        # Get conflict candidates from pattern analysis
        query = db.query(GenerationLog).filter(
            GenerationLog.status.in_(["success", "fail"]),
            GenerationLog.tags.isnot(None),
        )
        if project_name:
            query = query.filter(GenerationLog.project_name == project_name)

        logs = query.all()

        if not logs:
            return {
                "suggested_rules": [],
                "existing_rules_count": 0,
                "new_rules_count": 0,
            }

        # Calculate fail logs
        success_logs = [log for log in logs if log.status == "success" or (log.match_rate and log.match_rate >= 0.7)]
        fail_logs = [log for log in logs if log.status == "fail" or (log.match_rate and log.match_rate < 0.7)]

        # Find tag pairs with high fail rate
        tag_pair_stats = {}

        for log in logs:
            if not log.tags or len(log.tags) < 2:
                continue

            is_fail = log in fail_logs

            for i, tag1 in enumerate(log.tags):
                for tag2 in log.tags[i+1:]:
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
            f"[Suggest Conflict Rules] project={project_name}, "
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
    finally:
        db.close()


class ApplyConflictRulesRequest(BaseModel):
    """Request for applying suggested conflict rules."""

    rules: list[dict]  # [{"tag1": str, "tag2": str}, ...]


@router.post("/apply-conflict-rules")
def apply_conflict_rules(request: ApplyConflictRulesRequest):
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
    db = SessionLocal()
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
    finally:
        db.close()
