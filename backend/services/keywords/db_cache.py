from typing import Any
from functools import lru_cache
from sqlalchemy.orm import Session
from models import Tag, TagAlias, TagRule
from config import logger

# Map DB categories + subcategories to prompt composition categories
SUBCATEGORY_TO_PROMPT = {
    "indoor": "location_indoor",
    "outdoor": "location_outdoor",
    "time": "time_weather",
    "clothing": "clothing",
}

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
                
                # Map DB category to prompt category
                prompt_category = cls._map_db_category(tag.category, tag.subcategory)
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
    def _map_db_category(category: str, subcategory: str | None) -> str | None:
        """Map DB category + subcategory to prompt composition category.
        
        Now uses the subcategory column directly from DB - no more hardcoded heuristics!
        """
        # If subcategory is set, use it directly
        if subcategory:
            prompt_cat = SUBCATEGORY_TO_PROMPT.get(subcategory)
            if prompt_cat:
                return prompt_cat
        
        # Fallback to category mapping
        if category == "scene":
            # Default to indoor if no subcategory specified
            return "location_indoor"
        

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
            aliases = db.query(TagAlias).filter(TagAlias.active == True).all()
            
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
    _initialized = False
    
    @classmethod
    def initialize(cls, db: Session):
        """Load all active tag rules from DB and map to names."""
        if cls._initialized:
            return
            
        try:
            # Join with Tag table to get names
            from sqlalchemy.orm import aliased
            SourceTag = aliased(Tag)
            TargetTag = aliased(Tag)
            
            rules = (
                db.query(
                    SourceTag.name.label("source_name"),
                    TargetTag.name.label("target_name")
                )
                .select_from(TagRule)
                .join(SourceTag, TagRule.source_tag_id == SourceTag.id)
                .join(TargetTag, TagRule.target_tag_id == TargetTag.id)
                .filter(TagRule.rule_type == "conflict", TagRule.active == True)
                .all()
            )
            
            count = 0
            for rule in rules:
                s_name = rule.source_name.lower().strip()
                t_name = rule.target_name.lower().strip()
                
                cls._conflicts.setdefault(s_name, set()).add(t_name)
                cls._conflicts.setdefault(t_name, set()).add(s_name)
                count += 1
                
            cls._initialized = True
            logger.info(f"✅ [TagRuleCache] Loaded {count} conflict rules into cache")
        except Exception as e:
            logger.error(f"❌ [TagRuleCache] Failed to initialize: {e}")

    @classmethod
    def is_conflicting(cls, tag1: str, tag2: str) -> bool:
        """Check if two tags conflict."""
        t1 = tag1.lower().strip()
        t2 = tag2.lower().strip()
        return t2 in cls._conflicts.get(t1, set())

    @classmethod
    def refresh(cls, db: Session):
        cls._initialized = False
        cls._conflicts.clear()
        cls.initialize(db)
