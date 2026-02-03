"""
Comprehensive Test Suite for Prompt Composition

Tests the complete prompt composition pipeline including:
- Tag category mapping
- Conflict filtering
- Alias replacement
- Compose modes (standard vs lora)
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prompt.prompt_composition import (
    compose_prompt_tokens,
    filter_conflicting_tokens,
    get_token_category,
)

from database import SessionLocal
from services.keywords.db_cache import TagAliasCache, TagCategoryCache, TagRuleCache


def test_category_mapping():
    """Test that tags are mapped to correct categories."""
    print("\n" + "="*80)
    print("TEST 1: Category Mapping")
    print("="*80)

    test_cases = [
        # (tag, expected_category)
        ("surprised", "expression"),
        ("looking_at_viewer", "gaze"),
        ("standing", "pose"),
        ("stretching", "action"),
        ("upper_body", "camera"),
        ("1girl", "subject"),
        ("bedroom", "location_indoor"),
        ("day", "time_weather"),
        ("bright", "lighting"),
        ("anime_style", "style"),
        ("masterpiece", "meta"),
        ("short_hair", "identity"),  # character -> identity mapping
        ("pink_hair", "identity"),
    ]

    passed = 0
    failed = 0

    for tag, expected in test_cases:
        actual = get_token_category(tag)
        status = "✅" if actual == expected else "❌"
        print(f"  {status} {tag:25} -> {actual:20} (expected: {expected})")

        if actual == expected:
            passed += 1
        else:
            failed += 1

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return failed == 0


def test_conflict_filtering():
    """Test that conflicting tags are properly filtered."""
    print("\n" + "="*80)
    print("TEST 2: Conflict Filtering")
    print("="*80)

    test_cases = [
        # (input_tags, expected_kept, expected_removed)
        (
            ["crying", "laughing"],
            ["crying"],
            ["laughing"]
        ),
        (
            ["sitting", "standing"],
            ["sitting"],
            ["standing"]
        ),
        (
            ["1girl", "1boy"],
            ["1girl"],
            ["1boy"]
        ),
        (
            ["masterpiece", "lowres"],
            ["masterpiece"],
            ["lowres"]
        ),
        (
            ["bedroom", "classroom"],  # Both location_indoor
            ["bedroom"],
            ["classroom"]
        ),
    ]

    passed = 0
    failed = 0

    for input_tags, expected_kept, expected_removed in test_cases:
        filtered = filter_conflicting_tokens(input_tags)

        all_kept = all(tag in filtered for tag in expected_kept)
        none_removed = all(tag not in filtered for tag in expected_removed)

        if all_kept and none_removed:
            print(f"  ✅ {input_tags} -> {filtered}")
            passed += 1
        else:
            print(f"  ❌ {input_tags} -> {filtered}")
            print(f"     Expected to keep: {expected_kept}")
            print(f"     Expected to remove: {expected_removed}")
            failed += 1

    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return failed == 0


def test_no_false_positives():
    """Test that non-conflicting tags are NOT filtered."""
    print("\n" + "="*80)
    print("TEST 3: No False Positives")
    print("="*80)

    # These tags should all pass through without being filtered
    test_tags = [
        "surprised", "looking_at_viewer", "standing", "stretching",
        "upper_body", "day", "bright", "anime_style",
        "best_quality", "masterpiece", "1girl",
        "short_hair", "pink_hair", "school_uniform"
    ]

    filtered = filter_conflicting_tokens(test_tags)

    # We expect most tags to pass, except for potential quality tag conflicts
    expected_min = len(test_tags) - 2  # Allow for some quality tag filtering

    if len(filtered) >= expected_min:
        print(f"  ✅ {len(filtered)}/{len(test_tags)} tags kept (expected >= {expected_min})")
        print(f"     Input:  {test_tags}")
        print(f"     Output: {filtered}")
        return True
    else:
        print(f"  ❌ Only {len(filtered)}/{len(test_tags)} tags kept (expected >= {expected_min})")
        print(f"     Input:  {test_tags}")
        print(f"     Output: {filtered}")
        removed = set(test_tags) - set(filtered)
        print(f"     Removed: {removed}")
        return False


def test_compose_standard_mode():
    """Test standard mode composition."""
    print("\n" + "="*80)
    print("TEST 4: Standard Mode Composition")
    print("="*80)

    test_tokens = [
        "1girl", "short_hair", "pink_hair", "school_uniform",
        "surprised", "looking_at_viewer", "standing",
        "bedroom", "day", "bright",
        "anime_style", "masterpiece", "best_quality"
    ]

    composed = compose_prompt_tokens(
        tokens=test_tokens,
        mode="standard",
        lora_strings=None,
        trigger_words=None,
        use_break=False
    )

    # Check that we got a reasonable number of tokens
    if len(composed) >= 10:
        print(f"  ✅ Composed {len(composed)} tokens from {len(test_tokens)} input")
        print(f"     Result: {', '.join(composed[:10])}...")
        return True
    else:
        print(f"  ❌ Only composed {len(composed)} tokens from {len(test_tokens)} input")
        print(f"     Result: {composed}")
        return False


def test_compose_lora_mode():
    """Test LoRA mode composition."""
    print("\n" + "="*80)
    print("TEST 5: LoRA Mode Composition")
    print("="*80)

    test_tokens = [
        "1girl", "short_hair", "pink_hair", "school_uniform",
        "surprised", "looking_at_viewer", "standing",
        "bedroom", "day", "bright",
        "anime_style", "masterpiece", "best_quality"
    ]

    lora_strings = ["<lora:test_character:0.8>"]
    trigger_words = ["test_character"]

    composed = compose_prompt_tokens(
        tokens=test_tokens,
        mode="lora",
        lora_strings=lora_strings,
        trigger_words=trigger_words,
        use_break=True
    )

    # Check that BREAK and LoRA are present
    has_break = "BREAK" in composed
    has_lora = any("<lora:" in token for token in composed)

    if has_break and has_lora and len(composed) >= 10:
        print("  ✅ LoRA mode composition successful")
        print(f"     - BREAK present: {has_break}")
        print(f"     - LoRA present: {has_lora}")
        print(f"     - Total tokens: {len(composed)}")
        return True
    else:
        print("  ❌ LoRA mode composition failed")
        print(f"     - BREAK present: {has_break}")
        print(f"     - LoRA present: {has_lora}")
        print(f"     - Total tokens: {len(composed)}")
        print(f"     Result: {composed}")
        return False


def run_all_tests():
    """Run all test suites."""
    db = SessionLocal()
    try:
        # Initialize caches
        print("\n🔧 Initializing caches...")
        TagCategoryCache.initialize(db)
        TagAliasCache.initialize(db)
        TagRuleCache.initialize(db)
        print("✅ Caches initialized\n")

        # Run tests
        results = []
        results.append(("Category Mapping", test_category_mapping()))
        results.append(("Conflict Filtering", test_conflict_filtering()))
        results.append(("No False Positives", test_no_false_positives()))
        results.append(("Standard Mode Compose", test_compose_standard_mode()))
        results.append(("LoRA Mode Compose", test_compose_lora_mode()))

        # Summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} - {name}")

        print(f"\n  Total: {passed}/{total} test suites passed")

        if passed == total:
            print("\n🎉 All tests passed!")
            return 0
        else:
            print(f"\n⚠️  {total - passed} test suite(s) failed")
            return 1

    finally:
        db.close()


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
