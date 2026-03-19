from services.prompt.prompt_composition import compose_prompt_string, get_token_category

from database import SessionLocal
from services.keywords.db_cache import LoRATriggerCache, TagAliasCache, TagCategoryCache, TagRuleCache


def test_composition():
    db = SessionLocal()

    # Refresh cache
    TagCategoryCache._initialized = False
    TagCategoryCache.initialize(db)
    TagRuleCache._initialized = False
    TagRuleCache.initialize(db)
    TagAliasCache._initialized = False
    TagAliasCache.initialize(db)
    LoRATriggerCache._initialized = False
    LoRATriggerCache.initialize(db)

    # Clear lru_cache for get_token_category
    get_token_category.cache_clear()

    tokens = [
        "amazing_quality",
        "masterpiece",
        "1girl",
        "pink_hair",
        "doremi",
        "full_body",
        "outdoors",
        "_day",
        "_sun",
        "day",
        "bright",
        "soft_light",
        "anime_style",
        "casual_outfit",
        "smile",
        "standing",
        "holding_flower",
        "sun",
        "blush",
        "open_mouth",
        "anime",
    ]

    print("--- Token Categories ---")
    for t in tokens:
        cat = get_token_category(t)
        print(f"Token: {t}, Category: {cat}")

    lora_strings = ["<lora:harukaze-doremi-casual:0.61>"]

    # Mode A (Standard)
    prompt_a = compose_prompt_string(tokens, mode="standard", lora_strings=lora_strings)
    print("\n--- Mode A (Standard) ---")
    print(prompt_a)

    # Mode B (LoRA)
    prompt_b = compose_prompt_string(tokens, mode="lora", lora_strings=lora_strings)
    print("\n--- Mode B (LoRA) ---")
    print(prompt_b)

    db.close()


if __name__ == "__main__":
    test_composition()
