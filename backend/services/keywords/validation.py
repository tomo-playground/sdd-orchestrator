from __future__ import annotations

from typing import Any

from database import SessionLocal
from models.tag import Tag

from .core import normalize_prompt_token


def validate_prompt_tags(prompt_tags: list[str]) -> dict[str, Any]:
    """Validate prompt tags against conflict and requires rules."""
    if not prompt_tags:
        return {"valid": True, "conflicts": [], "missing_dependencies": [], "warnings": []}

    db = SessionLocal()
    try:
        normalized_tags = {normalize_prompt_token(t) for t in prompt_tags if t}
        normalized_tags.discard("")

        tag_lookup: dict[str, int] = {}
        tag_id_lookup: dict[int, str] = {}
        for name in normalized_tags:
            tag = db.query(Tag).filter(Tag.name == name).first()
            if not tag:
                tag = db.query(Tag).filter(Tag.name == name.replace(" ", "_")).first()
            if tag:
                tag_lookup[name] = tag.id
                tag_id_lookup[tag.id] = name

        tag_ids = set(tag_lookup.values())
        conflicts, missing_deps, warnings = [], [], []

        if tag_ids:
            from models.tag import TagRule

            conflict_rules = (
                db.query(TagRule)
                .filter(
                    TagRule.rule_type == "conflict",
                    TagRule.source_tag_id.in_(tag_ids),
                    TagRule.target_tag_id.in_(tag_ids),
                )
                .all()
            )

            seen_conflicts = set()
            for rule in conflict_rules:
                pair = tuple(sorted([rule.source_tag_id, rule.target_tag_id]))
                if pair not in seen_conflicts:
                    seen_conflicts.add(pair)
                    tag1 = tag_id_lookup.get(rule.source_tag_id, "?")
                    tag2 = tag_id_lookup.get(rule.target_tag_id, "?")
                    conflicts.append({"tag1": tag1, "tag2": tag2, "message": f"'{tag1}' conflicts with '{tag2}'"})

            requires_rules = (
                db.query(TagRule).filter(TagRule.rule_type == "requires", TagRule.source_tag_id.in_(tag_ids)).all()
            )

            for rule in requires_rules:
                if rule.target_tag_id not in tag_ids:
                    source_name = tag_id_lookup.get(rule.source_tag_id, "?")
                    target_tag = db.query(Tag).filter(Tag.id == rule.target_tag_id).first()
                    target_name = target_tag.name if target_tag else "?"
                    missing_deps.append(
                        {
                            "tag": source_name,
                            "requires": target_name,
                            "message": f"'{source_name}' requires '{target_name}'",
                        }
                    )

        is_valid = len(conflicts) == 0 and len(missing_deps) == 0
        return {"valid": is_valid, "conflicts": conflicts, "missing_dependencies": missing_deps, "warnings": warnings}
    finally:
        db.close()


def get_tag_rules_summary() -> dict[str, Any]:
    """Get summary of all tag rules in the database."""
    db = SessionLocal()
    try:
        from models.tag import TagRule

        conflict_count = db.query(TagRule).filter(TagRule.rule_type == "conflict").count()
        requires_count = db.query(TagRule).filter(TagRule.rule_type == "requires").count()

        conflict_examples, requires_examples = [], []
        conflict_rules = db.query(TagRule).filter(TagRule.rule_type == "conflict").limit(10).all()
        for rule in conflict_rules:
            source = db.query(Tag).filter(Tag.id == rule.source_tag_id).first()
            target = db.query(Tag).filter(Tag.id == rule.target_tag_id).first()
            if source and target:
                conflict_examples.append(f"{source.name} ↔ {target.name}")

        requires_rules = db.query(TagRule).filter(TagRule.rule_type == "requires").limit(10).all()
        for rule in requires_rules:
            source = db.query(Tag).filter(Tag.id == rule.source_tag_id).first()
            target = db.query(Tag).filter(Tag.id == rule.target_tag_id).first()
            if source and target:
                requires_examples.append(f"{source.name} → {target.name}")

        return {
            "conflict_count": conflict_count // 2,
            "requires_count": requires_count,
            "conflict_examples": conflict_examples[:5],
            "requires_examples": requires_examples[:5],
        }
    finally:
        db.close()


def get_effective_tags() -> dict[str, list[str]]:
    """Get tags grouped by effectiveness level (Stub)."""
    return {"high": [], "medium": [], "low": [], "unknown": []}


def get_tag_effectiveness_report() -> list[dict[str, Any]]:
    """Get full effectiveness report for all tags (Stub)."""
    return []
