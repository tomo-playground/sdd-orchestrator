import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from services.prompt.prompt_composition import filter_conflicting_tokens

from database import SessionLocal
from models.tag import Tag
from services.prompt.prompt import normalize_tag_spaces
from services.tag_classifier import TagClassifier


def verify_db_data(db):
    print("\n=== 1. DB Data Verification ===")
    targets = ["best_quality", "anime_style", "looking_at_viewer", "thinking", "full_body"]
    all_pass = True

    for name in targets:
        tag = db.query(Tag).filter(Tag.name == name).first()
        if not tag:
            print(f"❌ {name}: Not found in DB")
            all_pass = False
            continue

        status = "✅" if tag.category and tag.group_name else "❌"
        if not tag.group_name or tag.group_name == "unknown":
            status = "❌"
            all_pass = False

        print(f"{status} {name}: category='{tag.category}', group='{tag.group_name}'")

    if all_pass:
        print("✅ All target tags have valid category and group data.")
    else:
        print("❌ Some tags are missing category or group data.")


def verify_classification(db):
    print("\n=== 2. Classification Logic Verification ===")
    classifier = TagClassifier(db)

    test_tags = ["best_quality", "anime_style", "looking_at_viewer"]
    all_pass = True

    classification, _ = classifier.classify_batch(test_tags, sync_danbooru=True)

    for tag, result in classification.items():
        group = result.get("group")
        status = "✅" if group and group != "unknown" else "❌"
        if status == "❌":
            all_pass = False
        print(f"{status} {tag} -> group='{group}', source='{result.get('source')}'")

    if all_pass:
        print("✅ Classifier is returning correct groups.")
    else:
        print("❌ Classifier returned unknown or missing groups.")


def verify_prompt_logic():
    print("\n=== 3. Prompt Normalization & Deduplication Verification ===")

    # Test 1: Underscore normalization
    raw_tags = [" _day ", "day", "__bright", "sun__", "flower_field"]
    normalized = normalize_tag_spaces(raw_tags)
    expected = ["day", "day", "bright", "sun", "flower_field"]

    print(f"Input: {raw_tags}")
    print(f"Output: {normalized}")

    if normalized == expected:
        print("✅ Underscore normalization passed.")
    else:
        print(f"❌ Underscore normalization failed. Expected {expected}")

    # Test 2: Weighted tag deduplication
    # (happy:1.2) vs happy -> should keep first? or filter conflicts?
    # filter_conflicting_tokens logic: simple dedupe

    tokens = ["(happy:1.2)", "happy", "smile", "(smile:0.8)"]
    # We need to mock get_token_category for filter_conflicting_tokens to work fully,
    # but here we focus on the duplicate check logic we added (normalize_prompt_token)

    filtered = filter_conflicting_tokens(tokens)
    print(f"\nInput: {tokens}")
    print(f"Filtered: {filtered}")

    # We expect "(happy:1.2)" to stay, and "happy" to be removed because (happy:1.2) normalizes to 'happy'
    # Same for smile.
    # Note: 'smile' comes before '(smile:0.8)' so 'smile' stays if we iterate in order and 'smile' is first seen?
    # Wait, filter_conflicting_tokens iterates and adds to seen.
    # 1. (happy:1.2) -> seen 'happy'
    # 2. happy -> normalized 'happy' in seen -> SKIP
    # 3. smile -> seen 'smile'
    # 4. (smile:0.8) -> normalized 'smile' in seen -> SKIP

    if len(filtered) == 2 and filtered[0] == "(happy:1.2)" and filtered[1] == "smile":
        print("✅ Weighted tag deduplication passed.")
    else:
        print(f"❌ Deduplication failed or different behavior. Got: {filtered}")


if __name__ == "__main__":
    try:
        db = SessionLocal()
        verify_db_data(db)
        verify_classification(db)
        verify_prompt_logic()
    finally:
        db.close()
