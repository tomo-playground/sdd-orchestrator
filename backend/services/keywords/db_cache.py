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
        """Map DB category + group_name to prompt composition category.

        group_name이 있으면 그대로 prompt layer key로 사용한다.
        없으면 DB category → prompt category 매핑으로 fallback.

        Gemini Template Context Tags → 12-Layer Mapping:
        - expression, gaze → LAYER_EXPRESSION (7)
        - pose, action → LAYER_ACTION (8)
        - camera → LAYER_CAMERA (9)
        - environment, location_*, time_weather, lighting → LAYER_ENVIRONMENT (10)
        - mood → LAYER_ATMOSPHERE (11)
        """
        if group_name:
            # location sub-groups → parent group 정규화
            if group_name in ("location_indoor_general", "location_indoor_specific"):
                return "location_indoor"
            return group_name

        # group_name 없으면 category 기반 fallback
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
            aliases = db.query(TagAlias).filter(TagAlias.is_active).all()

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
                db.query(SourceTag.name.label("source_name"), TargetTag.name.label("target_name"))
                .select_from(TagRule)
                .join(SourceTag, TagRule.source_tag_id == SourceTag.id)
                .join(TargetTag, TagRule.target_tag_id == TargetTag.id)
                .filter(TagRule.rule_type == "conflict", TagRule.is_active, TagRule.source_tag_id.isnot(None))
                .all()
            )

            tag_count = 0
            for rule in tag_rules:
                s_name = rule.source_name.lower().strip()
                t_name = rule.target_name.lower().strip()

                cls._conflicts.setdefault(s_name, set()).add(t_name)
                cls._conflicts.setdefault(t_name, set()).add(s_name)
                tag_count += 1

            # Category-level conflicts removed (Phase 6-4.26)
            # Reason: Never used (0/16 rules), logically unnecessary

            cls._initialized = True
            logger.info(f"✅ [TagRuleCache] Loaded {tag_count} tag conflicts into cache")
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
    """In-memory cache for mapping trigger words to LoRA names and types."""

    _cache: dict[str, str] = {}
    _name_to_type: dict[str, str] = {}
    _initialized = False

    @classmethod
    def initialize(cls, db: Session):
        """Load all LoRA trigger words from DB."""
        if cls._initialized:
            return

        try:
            from models.lora import LoRA

            loras = db.query(LoRA).filter(LoRA.is_active.is_(True)).all()

            count = 0
            for lora in loras:
                # Build name -> lora_type mapping
                if lora.lora_type:
                    cls._name_to_type[lora.name] = lora.lora_type
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
    def get_lora_type(cls, lora_name: str) -> str | None:
        """Get LoRA type (character, style, pose, etc.) by LoRA name."""
        return cls._name_to_type.get(lora_name)

    @classmethod
    def refresh(cls, db: Session):
        cls._initialized = False
        cls._cache.clear()
        cls._name_to_type.clear()
        cls.initialize(db)


class TagValenceCache:
    """In-memory cache for tag valence (emotion polarity) from DB.

    Used for cross-group conflict detection (expression ↔ mood).
    """

    _cache: dict[str, str] = {}  # tag_name → valence
    _initialized = False

    @classmethod
    def initialize(cls, db: Session):
        """Load all tags with valence from DB."""
        if cls._initialized:
            return

        try:
            tags = db.query(Tag.name, Tag.valence).filter(Tag.valence.isnot(None)).all()

            count = 0
            for name, valence in tags:
                normalized = name.lower().replace(" ", "_").strip()
                cls._cache[normalized] = valence
                count += 1

            cls._initialized = True
            logger.info(f"✅ [TagValenceCache] Loaded {count} tag valences into cache")
        except Exception as e:
            logger.error(f"❌ [TagValenceCache] Failed to initialize: {e}")

    @classmethod
    def get_valence(cls, tag: str) -> str | None:
        """Get valence for a tag. Returns None if not classified."""
        normalized = tag.lower().replace(" ", "_").strip()
        return cls._cache.get(normalized)

    @classmethod
    def is_valence_conflicting(cls, tag1: str, tag2: str) -> bool:
        """Check if two tags have opposing valence (positive ↔ negative).

        Returns False if either tag has no valence or is neutral.
        """
        v1 = cls.get_valence(tag1)
        v2 = cls.get_valence(tag2)
        if not v1 or not v2 or v1 == "neutral" or v2 == "neutral":
            return False
        return v1 != v2

    @classmethod
    def refresh(cls, db: Session):
        cls._initialized = False
        cls._cache.clear()
        cls.initialize(db)


class TagFilterCache:
    """Unified in-memory cache for tag filters from DB.

    Handles three filter_type values:
    - "restricted": tags excluded from Identity DNA
    - "ignore": tokens ignored during prompt processing
    - "skip": tags skipped during category suggestion
    """

    _restricted: set[str] = set()
    _ignored: set[str] = set()
    _ignore_tokens: frozenset[str] = frozenset()
    _skip_tags: frozenset[str] = frozenset()
    _initialized = False

    @classmethod
    def initialize(cls, db: Session):
        """Load all active tag filters from DB."""
        if cls._initialized:
            return

        try:
            from models.tag_filter import TagFilter

            filters = db.query(TagFilter).filter(TagFilter.is_active).all()

            restricted_count = 0
            ignored_count = 0
            skip_count = 0
            ignore_tokens: set[str] = set()
            skip_tags: set[str] = set()

            for filter_rule in filters:
                normalized = filter_rule.tag_name.lower().strip()
                if filter_rule.filter_type == "restricted":
                    cls._restricted.add(normalized)
                    restricted_count += 1
                elif filter_rule.filter_type == "ignore":
                    cls._ignored.add(normalized)
                    ignore_tokens.add(normalized)
                    ignored_count += 1
                elif filter_rule.filter_type == "skip":
                    skip_tags.add(normalized)
                    skip_count += 1

            cls._ignore_tokens = frozenset(ignore_tokens)
            cls._skip_tags = frozenset(skip_tags)
            cls._initialized = True
            logger.info(
                f"✅ [TagFilterCache] Loaded {restricted_count} restricted, "
                f"{ignored_count} ignored, {skip_count} skip tags"
            )
        except Exception as e:
            logger.error(f"❌ [TagFilterCache] Failed to initialize: {e}")
            cls._ignore_tokens = frozenset()
            cls._skip_tags = frozenset()

    @classmethod
    def is_restricted(cls, tag: str) -> bool:
        """Check if a tag is restricted (should not be in Identity DNA)."""
        normalized = tag.lower().strip()
        return normalized in cls._restricted

    @classmethod
    def is_ignored(cls, tag: str) -> bool:
        """Check if a tag should be ignored completely."""
        normalized = tag.lower().strip()
        return normalized in cls._ignored

    @classmethod
    def get_ignore_tokens(cls) -> frozenset[str]:
        """Get the set of tokens to ignore during prompt processing."""
        return cls._ignore_tokens

    @classmethod
    def get_skip_tags(cls) -> frozenset[str]:
        """Get the set of tags to skip during category suggestion."""
        return cls._skip_tags

    @classmethod
    def refresh(cls, db: Session):
        cls._initialized = False
        cls._restricted.clear()
        cls._ignored.clear()
        cls._ignore_tokens = frozenset()
        cls._skip_tags = frozenset()
        cls.initialize(db)
