
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from services.keywords.core import TagFilterCache
from services.keywords.db_cache import TagAliasCache, TagCategoryCache, TagRuleCache
from services.prompt.prompt_validation import auto_replace_risky_tags


def test_final_integration():
    db = SessionLocal()
    try:
        # 1. Initialize Caches
        print("Initializing caches...")
        TagCategoryCache.initialize(db)
        TagFilterCache.initialize(db)
        TagAliasCache.initialize(db)
        TagRuleCache.initialize(db)

        # 2. Test Tag Aliases (Replacements)
        print("\n--- Testing Tag Aliases ---")
        test_tags = ["medium shot", "unreal engine", "short_green_hair", "smiling"]
        result = auto_replace_risky_tags(test_tags)

        print(f"Original: {test_tags}")
        print(f"Replaced: {result['replaced']}")
        print(f"Removed: {result['removed']}")

        # Verify specific expectations (from DB population)
        assert "cowboy_shot" in result['replaced']  # medium shot replacement
        # Handle composite replacement "short_hair, green_hair"
        assert any("short_hair" in r for r in result['replaced'])
        assert any("green_hair" in r for r in result['replaced'])
        assert "unreal engine" not in result['replaced'] # removed
        print("✅ Tag Alias test passed!")

        # 3. Test Tag-Pair Conflicts (Cache Verification)
        print("\n--- Testing Tag-Pair Conflicts ---")
        # Verify tag conflicts are loaded in cache
        tag_conflicts = TagRuleCache._conflicts
        print(f"Loaded {len(tag_conflicts)} tag conflict mappings")

        # Verify specific tag conflicts exist in cache
        assert TagRuleCache.is_conflicting("crying", "laughing")
        assert TagRuleCache.is_conflicting("sitting", "standing")
        assert TagRuleCache.is_conflicting("1girl", "1boy")
        assert TagRuleCache.is_conflicting("masterpiece", "lowres")
        print("✅ Tag-pair conflict rules verified in cache!")

        # 4. Test Category-Level Conflicts (Cache Verification)
        print("\n--- Testing Category-Level Conflicts ---")
        # Verify category conflicts are loaded
        cat_conflicts = TagRuleCache._category_conflicts
        print(f"Loaded {len(cat_conflicts)} category conflict mappings")

        # Verify specific category conflicts exist
        assert TagRuleCache.is_category_conflicting("hair_length", "hair_length")
        assert TagRuleCache.is_category_conflicting("location_indoor", "location_outdoor")
        assert TagRuleCache.is_category_conflicting("camera", "camera")
        print("✅ Category conflict rules verified in cache!")

        print("\n🎉 All final integration tests passed successfully!")

    except Exception as e:
        print(f"\n❌ Integration tests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    test_final_integration()
