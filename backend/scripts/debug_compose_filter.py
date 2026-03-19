import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prompt.prompt_composition import filter_conflicting_tokens, get_token_category

from database import SessionLocal
from services.keywords.db_cache import TagCategoryCache, TagRuleCache


def test_filter_debug():
    db = SessionLocal()
    try:
        # Initialize caches
        TagCategoryCache.initialize(db)
        TagRuleCache.initialize(db)

        # Test tokens from the screenshot
        test_tokens = [
            "surprised",
            "looking_at_viewer",
            "standing",
            "stretching",
            "upper_body",
            "bedroom",
            "day",
            "bright",
            "anime_style",
            "best_quality",
            "masterpiece",
            "1girl",
            "short_hair",
            "pink_hair",
            "school_uniform",
        ]

        print(f"\n=== Testing {len(test_tokens)} tokens ===\n")

        # Show category for each token
        print("Token Categories:")
        for token in test_tokens:
            category = get_token_category(token)
            print(f"  {token:20} -> {category}")

        print("\n=== Before Filtering ===")
        print(f"Tokens: {test_tokens}")
        print(f"Count: {len(test_tokens)}")

        # Apply filter
        filtered = filter_conflicting_tokens(test_tokens)

        print("\n=== After Filtering ===")
        print(f"Tokens: {filtered}")
        print(f"Count: {len(filtered)}")

        # Show what was removed
        removed = set(test_tokens) - set(filtered)
        print(f"\n=== Removed ({len(removed)}) ===")
        for token in removed:
            category = get_token_category(token)
            print(f"  {token:20} (category: {category})")

    finally:
        db.close()


if __name__ == "__main__":
    test_filter_debug()
