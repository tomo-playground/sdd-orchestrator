
from database import SessionLocal
from services.keywords.core import normalize_prompt_token
from services.tag_classifier import TagClassifier


def debug_classification():
    tags = ["_day", "_sun", "soft_light", "casual_outfit", "doremi", "sun"]

    print("--- Normalization ---")
    for t in tags:
        norm = normalize_prompt_token(t)
        print(f"'{t}' -> '{norm}'")

    print("\n--- Classification ---")
    db = SessionLocal()
    classifier = TagClassifier(db)

    results, _ = classifier.classify_batch(tags, sync_danbooru=True)
    for t, group in results.items():
        print(f"'{t}': {group}")

    db.close()

if __name__ == "__main__":
    debug_classification()
