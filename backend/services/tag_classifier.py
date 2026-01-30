"""Dynamic Tag Classification Service (15.7).

Hybrid classification: DB Cache → Rules → Danbooru API → LLM Fallback
Replaces hardcoded CATEGORY_PATTERNS with dynamic, learnable system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import logger
from models.tag import ClassificationRule, Tag

if TYPE_CHECKING:
    pass


class ClassificationResult(TypedDict):
    """Result of tag classification."""

    group: str | None
    confidence: float
    source: str  # 'db', 'rule', 'danbooru', 'llm'


# Danbooru category mapping (ID → SD group hint)
DANBOORU_CATEGORY_MAP = {
    0: None,  # General - needs further classification
    1: "style",  # Artist
    3: None,  # Copyright - usually not useful for SD
    4: "identity",  # Character
    5: "quality",  # Meta
}


class TagClassifier:
    """Hybrid tag classification service."""

    def __init__(self, db: Session):
        self.db = db
        self._rules_cache: list[ClassificationRule] | None = None

    def classify(self, tag: str) -> ClassificationResult:
        """Classify a single tag.

        Priority:
        1. Pattern rules (classification_rules table) - always check first
        2. DB cache (existing tag with group_name)
        3. Danbooru API (if available)
        4. LLM fallback (Gemini)
        """
        from services.keywords.core import normalize_prompt_token

        # Disable lower() in normalize_prompt_token if we want case-sensitive (but tokens are usually lower)
        # normalize_prompt_token returns lowercased, stripped, weight-removed string
        normalized = normalize_prompt_token(tag)
        # DB uses underscores, normalize_prompt_token uses underscores. Perfect.

        # Step 1: Rule-based classification (highest priority)
        rule_result = self._apply_rules(normalized)
        if rule_result and rule_result["confidence"] >= 0.9:
            # Save to DB (will override any existing Danbooru classification)
            self._save_classification(normalized, rule_result)
            return rule_result

        # Step 2: DB lookup (only if no rule matched)
        db_result = self._lookup_db(normalized)
        if db_result and db_result["confidence"] >= 0.8:
            return db_result

        # Step 3: Danbooru API
        danbooru_result = self._classify_via_danbooru(normalized)
        if danbooru_result and danbooru_result["group"]:
            self._save_classification(normalized, danbooru_result)
            return danbooru_result

        # Step 4: LLM fallback (placeholder - implement with Gemini)
        # For now, return unknown
        return {
            "group": None,
            "confidence": 0.0,
            "source": "unknown",
        }

    def _classify_via_danbooru(self, tag: str) -> ClassificationResult | None:
        """Classify tag using Danbooru API."""
        from services.danbooru import classify_from_danbooru, get_tag_info_sync
        from services.keywords.core import normalize_prompt_token

        try:
            # Danbooru uses underscores, weight removal handled by normalize_prompt_token
            # limit: normalize_prompt_token handles space->underscore
            normalized = normalize_prompt_token(tag)
            tag_info = get_tag_info_sync(normalized)
            if tag_info:
                group = classify_from_danbooru(tag_info)
                if group:
                    logger.info(
                        "🏷️ [Danbooru] Classified '%s' → %s (category=%s, posts=%d)",
                        tag,
                        group,
                        tag_info.get("category_name"),
                        tag_info.get("post_count", 0),
                    )
                    return {
                        "group": group,
                        "confidence": 0.85,
                        "source": "danbooru",
                    }
        except Exception as e:
            logger.warning("⚠️ [Danbooru] Classification failed for '%s': %s", tag, e)

        return None

    def classify_batch(self, tags: list[str]) -> dict[str, ClassificationResult]:
        """Classify multiple tags at once."""
        from services.keywords.core import normalize_prompt_token

        results = {}
        no_rule_match = []

        # First pass: check pattern rules (highest priority)
        for tag in tags:
            normalized = normalize_prompt_token(tag)
            rule_result = self._apply_rules(normalized)
            if rule_result and rule_result["confidence"] >= 0.9:
                self._save_classification(normalized, rule_result)
                results[tag] = rule_result
            else:
                no_rule_match.append(tag)

        # Second pass: check DB cache for tags without rule match
        still_unknown = []
        for tag in no_rule_match:
            normalized = normalize_prompt_token(tag)
            db_result = self._lookup_db(normalized)
            if db_result and db_result["confidence"] >= 0.8:
                results[tag] = db_result
            else:
                still_unknown.append(tag)

        # Third pass: try Danbooru for still unknown tags (limit to avoid rate limiting)
        for tag in still_unknown[:10]:  # Limit to 10 Danbooru calls per batch
            normalized = normalize_prompt_token(tag)
            danbooru_result = self._classify_via_danbooru(normalized)
            if danbooru_result and danbooru_result["group"]:
                self._save_classification(normalized, danbooru_result)
                results[tag] = danbooru_result
            else:
                results[tag] = {
                    "group": None,
                    "confidence": 0.0,
                    "source": "unknown",
                }

        # Mark remaining as unknown (beyond Danbooru limit)
        for tag in still_unknown[10:]:
            results[tag] = {
                "group": None,
                "confidence": 0.0,
                "source": "unknown",
            }

        return results

    def _lookup_db(self, tag: str) -> ClassificationResult | None:
        """Look up tag in database."""
        stmt = select(Tag).where(Tag.name == tag)
        result = self.db.execute(stmt).scalar_one_or_none()

        if result and result.group_name:
            return {
                "group": result.group_name,
                "confidence": result.classification_confidence or 1.0,
                "source": "db",
            }
        return None

    def _get_rules(self) -> list[ClassificationRule]:
        """Get classification rules (cached)."""
        if self._rules_cache is None:
            stmt = (
                select(ClassificationRule)
                .where(ClassificationRule.active == True)  # noqa: E712
                .order_by(ClassificationRule.priority.desc())
            )
            self._rules_cache = list(self.db.execute(stmt).scalars().all())
        return self._rules_cache

    def _apply_rules(self, tag: str) -> ClassificationResult | None:
        """Apply pattern rules to classify tag."""
        rules = self._get_rules()

        for rule in rules:
            matched = False
            pattern = rule.pattern.lower()

            if rule.rule_type == "exact":
                matched = tag == pattern
            elif rule.rule_type == "suffix":
                matched = tag.endswith(pattern)
            elif rule.rule_type == "prefix":
                matched = tag.startswith(pattern)
            elif rule.rule_type == "contains":
                matched = pattern in tag

            if matched:
                return {
                    "group": rule.target_group,
                    "confidence": 0.95,
                    "source": "rule",
                }

        return None

    def _save_classification(self, tag: str, result: ClassificationResult) -> None:
        """Save classification result to DB."""
        try:
            stmt = select(Tag).where(Tag.name == tag)
            existing = self.db.execute(stmt).scalar_one_or_none()

            if existing:
                existing.group_name = result["group"]
                existing.classification_source = result["source"]
                existing.classification_confidence = result["confidence"]
            else:
                # Determine category based on group
                category = self._group_to_category(result["group"])
                new_tag = Tag(
                    name=tag,
                    category=category,
                    group_name=result["group"],
                    classification_source=result["source"],
                    classification_confidence=result["confidence"],
                )
                self.db.add(new_tag)

            self.db.commit()
            logger.info("✅ [TagClassifier] Saved: %s → %s", tag, result["group"])
        except Exception as e:
            logger.error("❌ [TagClassifier] Failed to save %s: %s", tag, e)
            self.db.rollback()

    @staticmethod
    def _group_to_category(group: str | None) -> str:
        """Map group_name to category."""
        if not group:
            return "scene"

        character_groups = {
            "identity",
            "hair_color",
            "hair_length",
            "hair_style",
            "hair_accessory",
            "eye_color",
            "skin_color",
            "body_feature",
            "appearance",
            "clothing",
        }
        meta_groups = {"quality", "style"}

        if group in character_groups:
            return "character"
        if group in meta_groups:
            return "meta"

        # For granular groups (action, pose, expression, camera, etc.),
        # return the group itself as the category so it matches composition priorities.
        granular_groups = {
            "expression", "gaze", "pose", "action", "camera",
            "time_weather", "lighting", "mood", "location_indoor", "location_outdoor"
        }
        if group in granular_groups:
            return group

        return "scene"


# Utility function to migrate CATEGORY_PATTERNS to classification_rules
def migrate_patterns_to_rules(db: Session, patterns: dict[str, list[str]]) -> int:
    """Migrate hardcoded CATEGORY_PATTERNS to classification_rules table.

    Args:
        db: Database session
        patterns: Dictionary of group_name → list of patterns

    Returns:
        Number of rules created
    """
    from sqlalchemy.dialects.postgresql import insert

    count = 0
    rules_to_insert = []

    for group_name, pattern_list in patterns.items():
        for pattern in pattern_list:
            rules_to_insert.append({
                "rule_type": "exact",
                "pattern": pattern.lower(),
                "target_group": group_name,
                "priority": 0,
                "active": True,
            })

    if rules_to_insert:
        # Use ON CONFLICT DO NOTHING to skip duplicates
        stmt = insert(ClassificationRule).values(rules_to_insert)
        stmt = stmt.on_conflict_do_nothing(index_elements=["rule_type", "pattern"])
        result = db.execute(stmt)
        count = result.rowcount
        db.commit()

    logger.info("✅ [Migration] Created %d classification rules", count)
    return count
