import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prompt.prompt_composition import get_token_category

from database import SessionLocal
from services.keywords.db_cache import TagCategoryCache, TagRuleCache


def debug_filter():
    db = SessionLocal()
    try:
        TagCategoryCache.initialize(db)
        TagRuleCache.initialize(db)

        test_tags = ["crying", "laughing", "standing", "sitting", "looking_at_viewer", "closed_eyes"]

        print("\n--- Tag Category Debug ---")
        for tag in test_tags:
            category = get_token_category(tag)
            print(f"{tag:20} -> {category}")

        print("\n--- Conflict Rules in Cache ---")
        print(f"Total rules: {len(TagRuleCache._conflicts)}")
        for source, targets in TagRuleCache._conflicts.items():
            print(f"{source} conflicts with: {targets}")

    finally:
        db.close()


if __name__ == "__main__":
    debug_filter()
