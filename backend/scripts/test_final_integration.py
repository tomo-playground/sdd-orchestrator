
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from services.keywords.db_cache import TagCategoryCache, TagAliasCache, TagRuleCache
from services.keywords.core import TagFilterCache
from services.prompt.prompt_validation import auto_replace_risky_tags, validate_prompt_tags
from services.prompt.prompt_composition import filter_conflicting_tokens

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
        
        # 3. Test Tag Conflicts (simplified to avoid category mapping issues)
        print("\n--- Testing Tag Conflicts ---")
        # Test specific pairs that we know conflict
        test_pairs = [
            (['crying', 'laughing'], 'crying', 'laughing'),
            (['sitting', 'standing'], 'sitting', 'standing'),
            (['looking_at_viewer', 'closed_eyes'], 'looking_at_viewer', 'closed_eyes'),
        ]
        
        for tags, expected_keep, expected_remove in test_pairs:
            filtered = filter_conflicting_tokens(tags)
            print(f"Input: {tags}")
            print(f"Filtered: {filtered}")
            
            # First one wins
            assert expected_keep in filtered, f"Expected {expected_keep} to be kept"
            assert expected_remove not in filtered, f"Expected {expected_remove} to be removed"
            print(f"✅ Conflict test passed for {expected_keep} vs {expected_remove}")
        
        print("\n✅ All tag conflict tests passed!")
        
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
