from __future__ import annotations

from typing import Any

from database import SessionLocal
from models.lora import LoRA
from models.tag import Tag

from .core import logger
from .patterns import CATEGORY_PATTERNS


def sync_lora_triggers_to_tags() -> dict[str, Any]:
    """Sync LoRA trigger words to tags table."""
    from .patterns import GROUP_NAME_TO_LAYER

    def classify_trigger(trigger: str, lora_type: str | None) -> tuple[str, str, int]:
        trigger_lower = trigger.lower()
        if "eyes" in trigger_lower:
            return ("eye_color", "character", 4)
        if "hair" in trigger_lower:
            if any(
                c in trigger_lower
                for c in [
                    "black",
                    "blonde",
                    "brown",
                    "red",
                    "blue",
                    "green",
                    "pink",
                    "purple",
                    "white",
                    "silver",
                    "grey",
                    "gray",
                    "orange",
                    "aqua",
                ]
            ):
                return ("hair_color", "character", 4)
            return (
                ("hair_length", "character", 4)
                if any(x in trigger_lower for x in ["short", "long", "medium"])
                else ("hair_style", "character", 4)
            )
        if lora_type == "style":
            return ("style", "scene", 16)
        if trigger_lower in ["laughing", "crying", "smiling", "eyebrow", "eyebrow_down", "eyebrow_up"]:
            return ("expression", "scene", 6)
        return ("identity", "character", 3)

    db = SessionLocal()
    try:
        added, updated, skipped = [], [], []
        loras = db.query(LoRA).all()
        for lora in loras:
            if not lora.trigger_words:
                continue
            for trigger in lora.trigger_words:
                if not trigger or not trigger.strip():
                    continue
                trigger_clean = trigger.strip().lower()

                # Ensure trigger exists as a Tag
                existing_tag = db.query(Tag).filter(Tag.name == trigger_clean).first()
                if not existing_tag:
                    # Classify and add tag
                    cat, category, priority = classify_trigger(trigger_clean, lora.lora_type)
                    db.add(
                        Tag(
                            name=trigger_clean,
                            category=category,
                            group_name=cat,
                            priority=priority,
                            default_layer=GROUP_NAME_TO_LAYER.get(cat, 0),
                            classification_source="lora_sync",
                        )
                    )
                    added.append(trigger_clean)

        db.commit()
        return {
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "summary": {"added_count": len(added), "updated_count": len(updated), "skipped_count": len(skipped)},
        }
    finally:
        db.close()


def sync_category_patterns_to_tags(update_existing: bool = False) -> dict[str, Any]:
    """Sync CATEGORY_PATTERNS to tags table."""
    from .patterns import GROUP_NAME_TO_LAYER

    GROUP_TO_DB_CATEGORY: dict[str, tuple[str, int]] = {
        "identity": ("character", 3),
        "hair_color": ("character", 4),
        "hair_length": ("character", 4),
        "hair_style": ("character", 4),
        "hair_accessory": ("character", 4),
        "eye_color": ("character", 4),
        "skin_color": ("character", 4),
        "body_feature": ("character", 4),
        "appearance": ("character", 4),
        "body_type": ("character", 4),
        "clothing_top": ("character", 5),
        "clothing_bottom": ("character", 5),
        "clothing_outfit": ("character", 5),
        "clothing_detail": ("character", 5),
        "legwear": ("character", 5),
        "footwear": ("character", 5),
        "accessory": ("character", 5),
        "quality": ("quality", 1),
        "subject": ("scene", 2),
        "expression": ("scene", 6),
        "gaze": ("scene", 7),
        "pose": ("scene", 8),
        "action_body": ("scene", 9),
        "action_hand": ("scene", 9),
        "action_daily": ("scene", 9),
        "camera": ("scene", 10),
        "location_indoor": ("scene", 11),
        "location_outdoor": ("scene", 11),
        "location_indoor_general": ("scene", 12),
        "location_indoor_specific": ("scene", 11),
        "environment": ("scene", 11),
        "background_type": ("scene", 12),
        "time_of_day": ("scene", 13),
        "weather": ("scene", 13),
        "particle": ("scene", 13),
        "lighting": ("scene", 14),
        "mood": ("scene", 15),
        "style": ("scene", 16),
    }

    db = SessionLocal()
    try:
        added, updated, skipped = [], [], []
        existing_tags = {t.name: t for t in db.query(Tag).all()}
        batch_names: set[str] = set()

        for group_name, patterns in CATEGORY_PATTERNS.items():
            db_info = GROUP_TO_DB_CATEGORY.get(group_name)
            if not db_info:
                logger.warning("[Sync Patterns] Unknown group: %s", group_name)
                continue
            db_category, priority = db_info

            for pattern in patterns:
                tag_name = pattern.strip().lower()
                if not tag_name:
                    continue
                existing = existing_tags.get(tag_name)
                if existing:
                    if update_existing:
                        expected_layer = GROUP_NAME_TO_LAYER.get(group_name, 0)
                        changes = []
                        if existing.category != db_category:
                            changes.append(f"category: {existing.category}→{db_category}")
                            existing.category = db_category
                        if existing.group_name != group_name:
                            changes.append(f"group: {existing.group_name}→{group_name}")
                            existing.group_name = group_name
                        if existing.priority != priority:
                            changes.append(f"priority: {existing.priority}→{priority}")
                            existing.priority = priority
                        if existing.default_layer != expected_layer:
                            changes.append(f"default_layer: {existing.default_layer}→{expected_layer}")
                            existing.default_layer = expected_layer

                        if changes:
                            updated.append({"tag": tag_name, "changes": changes})
                        else:
                            skipped.append({"tag": tag_name, "group": group_name, "reason": "no changes needed"})
                    else:
                        skipped.append({"tag": tag_name, "group": group_name, "reason": "already in DB"})
                elif tag_name in batch_names:
                    skipped.append({"tag": tag_name, "group": group_name, "reason": "duplicate in patterns"})
                else:
                    db.add(
                        Tag(
                            name=tag_name,
                            category=db_category,
                            group_name=group_name,
                            priority=priority,
                            default_layer=GROUP_NAME_TO_LAYER.get(group_name, 0),
                        )
                    )
                    batch_names.add(tag_name)
                    added.append({"tag": tag_name, "group": group_name, "category": db_category, "priority": priority})

        db.commit()
        logger.info("[Sync Patterns Complete] added=%d updated=%d skipped=%d", len(added), len(updated), len(skipped))
        return {
            "added": added,
            "updated": updated,
            "skipped": skipped,
            "summary": {
                "added_count": len(added),
                "updated_count": len(updated),
                "skipped_count": len(skipped),
                "by_group": _count_by_group(added),
            },
        }
    finally:
        db.close()


def _count_by_group(items: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        group = item.get("group", "unknown")
        counts[group] = counts.get(group, 0) + 1
    return counts
