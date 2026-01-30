from typing import Any

from sqlalchemy.orm import Session

from config import logger
from models import Tag, TagAlias, TagRule

# Map DB categories to prompt composition categories
DB_TO_PROMPT_CATEGORY = {
    "character": "identity",
    "style": "style",
    "quality": "quality",
    "meta": "meta",
}

class TagCategoryCache:
    """In-memory cache for tag -> category mapping from DB."""

    _cache: dict[str, str] = {}
    _initialized = False

    @classmethod
    def initialize(cls, db: Session):
        """Load all tags from DB into memory cache."""
        if cls._initialized:
            return

        try:
            # Load all tags that have a category
            tags = db.query(Tag).filter(Tag.category.isnot(None)).all()

            count = 0
            for tag in tags:
                normalized = tag.name.lower().replace(" ", "_").strip()

                # Map DB entry to prompt category (group_name priority)
                prompt_category = cls._map_db_category(tag.category, tag.group_name)
                if prompt_category:
                    cls._cache[normalized] = prompt_category
                    count += 1

            cls._initialized = True
            logger.info(f"✅ [TagCache] Loaded {count} tags into cache")
        except Exception as e:
            logger.error(f"❌ [TagCache] Failed to initialize: {e}")

    @classmethod
    def get_category(cls, token: str) -> str | None:
        """Get category for a token from cache."""
        normalized = token.lower().replace(" ", "_").strip()
        return cls._cache.get(normalized)

    @classmethod
    def refresh(cls, db: Session):
        """Refresh cache from DB."""
        cls._initialized = False
        cls._cache.clear()
        cls.initialize(db)

    @staticmethod
    def _map_db_category(category: str, group_name: str | None = None) -> str | None:
        """Map DB category + group_name to prompt composition category."""
        # 1. Use group_name for granular categories (expression, pose, action, etc.)
        granular_groups = {
            "expression", "gaze", "pose", "action", "camera",
            "time_weather", "lighting", "mood", "location_indoor", "location_outdoor"
        }
        if group_name in granular_groups:
            return group_name

        # 2. Fallback to category mapping
        if category == "scene":
            return "scene"

        return DB_TO_PROMPT_CATEGORY.get(category, category)

class TagAliasCache:
    """In-memory cache for tag aliases (replacements) from DB."""

    _cache: dict[str, str | None] = {}
    _initialized = False

    @classmethod
    def initialize(cls, db: Session):
        """Load all active tag aliases from DB."""
        if cls._initialized:
            return

        try:
            aliases = db.query(TagAlias).filter(TagAlias.active).all()

            count = 0
            for alias in aliases:
                source = alias.source_tag.lower().strip()
                target = alias.target_tag.lower().strip() if alias.target_tag else None
                cls._cache[source] = target
                count += 1

            cls._initialized = True
            logger.info(f"✅ [TagAliasCache] Loaded {count} aliases into cache")
        except Exception as e:
            logger.error(f"❌ [TagAliasCache] Failed to initialize: {e}")

    @classmethod
    def get_replacement(cls, tag: str) -> str | None | Any:
        """Get replacement for a tag. Returns Ellipsis if no replacement found."""
        normalized = tag.lower().strip()
        if normalized in cls._cache:
            return cls._cache[normalized]
        return ...

    @classmethod
    def refresh(cls, db: Session):
        cls._initialized = False
        cls._cache.clear()
        cls.initialize(db)


class TagRuleCache:
    """In-memory cache for tag interaction rules (conflicts) from DB."""

    # Map tag1_name -> set(conflicting_tag2_names)
    _conflicts: dict[str, set[str]] = {}
    # Map category1 -> set(conflicting_category2)
    _category_conflicts: dict[str, set[str]] = {}
    _initialized = False

    @classmethod
    def initialize(cls, db: Session):
        """Load all active tag rules from DB and map to names."""
        if cls._initialized:
            return

        try:
            from sqlalchemy.orm import aliased
            SourceTag = aliased(Tag)
            TargetTag = aliased(Tag)

            # Load tag-level conflicts
            tag_rules = (
                db.query(
                    SourceTag.name.label("source_name"),
                    TargetTag.name.label("target_name")
                )
                .select_from(TagRule)
                .join(SourceTag, TagRule.source_tag_id == SourceTag.id)
                .join(TargetTag, TagRule.target_tag_id == TargetTag.id)
                .filter(
                    TagRule.rule_type == "conflict",
                    TagRule.active,
                    TagRule.source_tag_id.isnot(None)
                )
                .all()
            )

            tag_count = 0
            for rule in tag_rules:
                s_name = rule.source_name.lower().strip()
                t_name = rule.target_name.lower().strip()

                cls._conflicts.setdefault(s_name, set()).add(t_name)
                cls._conflicts.setdefault(t_name, set()).add(s_name)
                tag_count += 1

            # Load category-level conflicts
            category_rules = (
                db.query(TagRule)
                .filter(
                    TagRule.rule_type == "conflict",
                    TagRule.active,
                    TagRule.source_category.isnot(None)
                )
                .all()
            )

            cat_count = 0
            for rule in category_rules:
                s_cat = rule.source_category.lower().strip()
                t_cat = rule.target_category.lower().strip()

                cls._category_conflicts.setdefault(s_cat, set()).add(t_cat)
                # Bidirectional for symmetric conflicts
                cls._category_conflicts.setdefault(t_cat, set()).add(s_cat)
                cat_count += 1

            cls._initialized = True
            logger.info(
                f"✅ [TagRuleCache] Loaded {tag_count} tag conflicts "
                f"and {cat_count} category conflicts into cache"
            )
        except Exception as e:
            logger.error(f"❌ [TagRuleCache] Failed to initialize: {e}")

    @classmethod
    def is_conflicting(cls, tag1: str, tag2: str) -> bool:
        """Check if two tags conflict."""
        t1 = tag1.lower().strip()
        t2 = tag2.lower().strip()
        return t2 in cls._conflicts.get(t1, set())

    @classmethod
    def is_category_conflicting(cls, cat1: str, cat2: str) -> bool:
        """Check if two categories conflict."""
        c1 = cat1.lower().strip()
        c2 = cat2.lower().strip()
        return c2 in cls._category_conflicts.get(c1, set())

    @classmethod
    def refresh(cls, db: Session):
        cls._initialized = False
        cls._conflicts.clear()
        cls._category_conflicts.clear()
        cls.initialize(db)

class LoRATriggerCache:
    """In-memory cache for mapping trigger words to LoRA names."""

    _cache: dict[str, str] = {}
    _initialized = False

    @classmethod
    def initialize(cls, db: Session):
        """Load all LoRA trigger words from DB."""
        if cls._initialized:
            return

        try:
            from models.lora import LoRA
            loras = db.query(LoRA).all()

            count = 0
            for lora in loras:
                if not lora.trigger_words:
                    continue
                for trigger in lora.trigger_words:
                    normalized = trigger.lower().strip()
                    # If multiple LoRAs share a trigger, the last one wins (could be refined)
                    cls._cache[normalized] = lora.name
                    count += 1

            cls._initialized = True
            logger.info(f"✅ [LoRATriggerCache] Loaded {count} trigger-to-LoRA mappings")
        except Exception as e:
            logger.error(f"❌ [LoRATriggerCache] Failed to initialize: {e}")

    @classmethod
    def get_lora_name(cls, trigger: str) -> str | None:
        """Get LoRA name for a trigger word."""
        normalized = trigger.lower().strip()
        return cls._cache.get(normalized)

    @classmethod
    def refresh(cls, db: Session):
        cls._initialized = False
        cls._cache.clear()
        cls.initialize(db)
