"""Admin endpoints for database management."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Tag, TagRule

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/migrate-tag-rules")
async def migrate_tag_conflict_rules(db: Session = Depends(get_db)):
    """Migrate hardcoded tag conflict rules to database.

    This is a one-time migration endpoint to populate tag_rules table
    with conflict pairs that were previously hardcoded in prompt_composition.py.
    """

    # List of conflicting pairs to migrate
    conflicts = [
        # Expression conflicts
        ('crying', 'laughing'), ('crying', 'happy'), ('crying', 'smile'),
        ('sad', 'happy'), ('sad', 'smile'), ('sad', 'laughing'),
        ('angry', 'happy'), ('angry', 'smile'),
        # Gaze conflicts
        ('looking_down', 'looking_up'), ('looking_away', 'looking_at_viewer'),
        ('closed_eyes', 'looking_at_viewer'),
        # Pose conflicts
        ('sitting', 'standing'), ('lying', 'standing'), ('lying', 'sitting'),
    ]

    added = []
    skipped = []
    errors = []

    for s_name, t_name in conflicts:
        try:
            # Find tags
            s_tag = db.query(Tag).filter(Tag.name == s_name).first()
            t_tag = db.query(Tag).filter(Tag.name == t_name).first()

            if not s_tag or not t_tag:
                errors.append(f"Tag not found: {s_name} or {t_name}")
                continue

            # Check if rule already exists
            exists = db.query(TagRule).filter(
                TagRule.source_tag_id == s_tag.id,
                TagRule.target_tag_id == t_tag.id,
                TagRule.rule_type == 'conflict'
            ).first()

            if not exists:
                # Also check reverse direction
                reverse_exists = db.query(TagRule).filter(
                    TagRule.source_tag_id == t_tag.id,
                    TagRule.target_tag_id == s_tag.id,
                    TagRule.rule_type == 'conflict'
                ).first()

                if not reverse_exists:
                    rule = TagRule(
                        source_tag_id=s_tag.id,
                        target_tag_id=t_tag.id,
                        rule_type='conflict',
                        message='Conflicting tags',
                        active=True
                    )
                    db.add(rule)
                    added.append(f"{s_name} <-> {t_name}")
                else:
                    skipped.append(f"{s_name} <-> {t_name} (reverse exists)")
            else:
                skipped.append(f"{s_name} <-> {t_name} (already exists)")

        except Exception as e:
            errors.append(f"Error processing {s_name} <-> {t_name}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "added": added,
            "skipped": skipped,
            "errors": errors
        }

    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "total_added": len(added),
        "total_skipped": len(skipped),
        "total_errors": len(errors)
    }


@router.post("/migrate-category-rules")
async def migrate_category_conflict_rules(db: Session = Depends(get_db)):
    """Migrate hardcoded category conflict rules to database.

    This migrates CONFLICTING_CATEGORY_PAIRS that were previously hardcoded.
    """

    # Category conflict pairs (source, target, message)
    category_conflicts = [
        ("hair_length", "hair_length", "Only one hair length allowed"),
        ("skin_color", "skin_color", "Only one skin color allowed"),
        ("location_indoor", "location_indoor", "Only one indoor location allowed"),
        ("location_outdoor", "location_outdoor", "Only one outdoor location allowed"),
        ("location_indoor", "location_outdoor", "Cannot be both indoor and outdoor"),
        ("location_outdoor", "location_indoor", "Cannot be both outdoor and indoor"),
        ("background_type", "background_type", "Only one background type allowed"),
        ("camera", "camera", "Only one camera angle allowed"),
    ]

    added = []
    skipped = []
    errors = []

    for s_cat, t_cat, message in category_conflicts:
        try:
            # Check if rule already exists
            exists = db.query(TagRule).filter(
                TagRule.source_category == s_cat,
                TagRule.target_category == t_cat,
                TagRule.rule_type == 'conflict'
            ).first()

            if not exists:
                rule = TagRule(
                    rule_type='conflict',
                    source_category=s_cat,
                    target_category=t_cat,
                    message=message,
                    active=True
                )
                db.add(rule)
                added.append(f"{s_cat} <-> {t_cat}")
            else:
                skipped.append(f"{s_cat} <-> {t_cat} (already exists)")

        except Exception as e:
            errors.append(f"Error processing {s_cat} <-> {t_cat}: {str(e)}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "error": str(e),
            "added": added,
            "skipped": skipped,
            "errors": errors
        }

    return {
        "success": True,
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "total_added": len(added),
        "total_skipped": len(skipped),
        "total_errors": len(errors)
    }


@router.post("/refresh-caches")
async def refresh_all_caches(db: Session = Depends(get_db)):
    """Refresh all in-memory caches from database.

    Call this after migrating data to ensure caches are up-to-date.
    """
    from services.keywords.core import TagFilterCache
    from services.keywords.db_cache import TagAliasCache, TagCategoryCache, TagRuleCache

    try:
        TagCategoryCache.refresh(db)
        TagFilterCache.refresh(db)
        TagAliasCache.refresh(db)
        TagRuleCache.refresh(db)

        return {
            "success": True,
            "message": "All caches refreshed successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
