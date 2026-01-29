from functools import lru_cache
from sqlalchemy.orm import Session
from models import Tag
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
        
        return DB_TO_PROMPT_CATEGORY.get(category, category)
