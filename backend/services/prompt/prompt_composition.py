"""Prompt Composition Service.

This module implements the Mode A/B prompt composition system
as defined in docs/PROMPT_SPEC.md.

Mode A (Standard): No LoRA or style-only LoRA
  - Token order: Quality → Subject → Character → Appearance → Scene → Lighting
  - Full appearance tags included

Mode B (LoRA): Character LoRA present
  - Token order: Quality → Subject → Scene Core → LoRA → BREAK → Character → Extras
  - Scene tags prioritized, LoRA weight dynamically adjusted
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Literal

from config import logger
from services.keywords import CATEGORY_PATTERNS, CATEGORY_PRIORITY

if TYPE_CHECKING:
    from models.character import Character
    from models.lora import LoRA

# Type alias
PromptMode = Literal["auto", "standard", "lora"]
EffectiveMode = Literal["standard", "lora"]
TokenCategory = str  # e.g., "quality", "subject", "expression", etc.

# Build reverse lookup: token → category (cached at module load)
_TOKEN_TO_CATEGORY: dict[str, str] = {}
for _category, _tokens in CATEGORY_PATTERNS.items():
    for _token in _tokens:
        _TOKEN_TO_CATEGORY[_token.lower()] = _category


from services.keywords.db_cache import TagCategoryCache, TagRuleCache


@lru_cache(maxsize=1024)
def get_token_category(token: str) -> TokenCategory | None:
    """Get the category for a prompt token.

    Priority:
    1. DB Cache (if initialized)
    2. Exact match in patterns
    3. Partial match in patterns

    Args:
        token: A prompt token (e.g., "smiling", "blue hair", "from above")

    Returns:
        Category name (e.g., "expression", "hair_color", "camera") or None if unknown
    """
    from services.keywords.core import normalize_prompt_token
    normalized = normalize_prompt_token(token)

    if not normalized:
        return None

    # 1. Check DB Cache first
    if TagCategoryCache._initialized:
        db_category = TagCategoryCache.get_category(normalized)
        if db_category:
            return db_category

    # 2. Exact match in patterns
    if normalized in _TOKEN_TO_CATEGORY:
        return _TOKEN_TO_CATEGORY[normalized]

    # 3. Partial match for compound tokens (e.g., "long blue hair" → "hair_color")
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            p_lower = pattern.lower()
            if p_lower in normalized or normalized in p_lower:
                return category

    return None


def get_token_priority(token: str) -> int:
    """Get the priority for a prompt token.

    Lower priority = earlier in prompt (more important).

    Args:
        token: A prompt token

    Returns:
        Priority number (1-15) or 99 for unknown tokens
    """
    category = get_token_category(token)
    if category:
        return CATEGORY_PRIORITY.get(category, 99)
    return 99


# ============================================================
# 9.8.3: Scene Complexity Detection
# ============================================================

# Scene-related categories that contribute to complexity
SCENE_CATEGORIES = frozenset([
    "expression", "gaze", "pose", "action", "camera",
    "location_indoor", "location_outdoor", "background_type",
    "time_weather", "lighting", "mood",
])


SceneComplexity = Literal["simple", "moderate", "complex"]


def detect_scene_complexity(tokens: list[str]) -> SceneComplexity:
    """Detect scene complexity based on token count per category.

    Complexity levels:
    - simple: 0-3 scene tokens
    - moderate: 4-6 scene tokens
    - complex: 7+ scene tokens

    Args:
        tokens: List of prompt tokens

    Returns:
        'simple', 'moderate', or 'complex'
    """
    scene_token_count = 0

    for token in tokens:
        category = get_token_category(token)
        if category in SCENE_CATEGORIES:
            scene_token_count += 1

    if scene_token_count <= 3:
        return "simple"
    elif scene_token_count <= 6:
        return "moderate"
    else:
        return "complex"


# ============================================================
# 9.8.4: LoRA Weight Calculation
# ============================================================

# LoRA weight table by type and complexity
# Based on PROMPT_SPEC.md Section 4
LORA_WEIGHTS: dict[str, dict[SceneComplexity, float]] = {
    "style": {
        "simple": 0.6,
        "moderate": 0.5,
        "complex": 0.4,
    },
    "character": {
        "simple": 0.6,
        "moderate": 0.5,
        "complex": 0.4,
    },
    "concept": {
        "simple": 0.5,
        "moderate": 0.4,
        "complex": 0.3,
    },
}


def calculate_lora_weight(
    lora_type: str | None,
    complexity: SceneComplexity,
    optimal_weight: float | None = None,
) -> float:
    """Calculate dynamic LoRA weight based on type and scene complexity.

    Args:
        lora_type: LoRA type ('style', 'character', 'concept', or None)
        complexity: Scene complexity level
        optimal_weight: Pre-calibrated optimal weight (takes precedence)

    Returns:
        LoRA weight (0.3-0.7)

    Logic:
        1. If optimal_weight is provided and lower than table value, use it
        2. Otherwise use table value based on type and complexity
    """
    # Default to character type if not specified
    lora_type = lora_type or "character"

    # Get base weight from table
    type_weights = LORA_WEIGHTS.get(lora_type, LORA_WEIGHTS["character"])
    base_weight = type_weights.get(complexity, 0.5)

    # Use optimal weight if provided and lower
    if optimal_weight is not None:
        return min(optimal_weight, base_weight)

    return base_weight


def calculate_lora_weight_for_scene(
    lora: dict,
    scene_tokens: list[str],
) -> float:
    """Calculate LoRA weight for a specific scene.

    Convenience wrapper that detects complexity and calculates weight.

    Args:
        lora: LoRA dict with 'lora_type' and optional 'optimal_weight'
        scene_tokens: List of tokens in the scene

    Returns:
        Calculated LoRA weight
    """
    complexity = detect_scene_complexity(scene_tokens)
    return calculate_lora_weight(
        lora_type=lora.get("lora_type"),
        complexity=complexity,
        optimal_weight=lora.get("optimal_weight"),
    )


# ============================================================
# 9.8.5: Conflict Filtering + Trigger Deduplication
# ============================================================

# Mutually exclusive category groups
# When tokens from the same group appear, keep only the first one
MUTUALLY_EXCLUSIVE_GROUPS = {
    "location": ["location_indoor", "location_outdoor"],
    "background": ["background_type"],  # Can only have one background
}

# Conflicting category pairs are now managed in the database (tag_rules table)
# and accessed via TagRuleCache.is_category_conflicting()

# CONFLICTING_TAG_PAIRS is now managed in the database (tag_rules table)
# and accessed via TagRuleCache


def filter_conflicting_tokens(
    tokens: list[str],
    trigger_words: list[str] | None = None,
) -> list[str]:
    """Filter out conflicting tokens and deduplicate triggers.

    Args:
        tokens: List of prompt tokens (in order)
        trigger_words: LoRA trigger words to deduplicate

    Returns:
        Filtered list with conflicts removed and triggers deduplicated

    Rules:
        1. Remove duplicate tokens (case-insensitive)
        2. For mutually exclusive categories (location_indoor vs outdoor),
           keep only the first occurrence
        3. Remove LoRA trigger words if they already appear in tokens
        4. Remove specific conflicting tag pairs (crying vs laughing, etc.)
    """
    seen_tokens: set[str] = set()
    seen_categories: dict[str, str] = {}  # group → first category
    seen_tag_conflicts: set[str] = set()  # Track tags for pair conflicts
    result: list[str] = []

    # Normalize trigger words for comparison
    trigger_set: set[str] = set()
    if trigger_words:
        trigger_set = {t.lower().strip() for t in trigger_words}

    # Conflict checking is now done via TagRuleCache.is_conflicting()
    from services.keywords.core import normalize_prompt_token

    for token in tokens:
        # Use robust normalization (ignores weights/parentheses) for deduplication
        # e.g. "(happy:1.2)" -> "happy", so it conflicts with "happy"
        normalized = normalize_prompt_token(token)
        if not normalized:
            # Fallback for special tokens that might return empty (shouldn't happen for normal tags)
            # But normalize_prompt_token returns "" for LoRAs/BREAK, which we want to keep?
            # Actually filter_conflicting_tokens usually runs on normal tokens.
            # LoRAs are extracted before this step in compose_prompt_tokens (Step 0b).
            # So tokens here are mostly normal tags.
            normalized = token.lower().strip()


        # Skip duplicates
        if normalized in seen_tokens:
            continue

        # Skip if token is a trigger word that's already been seen
        # (This handles the case where trigger appears both in character tags and LoRA)
        if normalized in trigger_set and normalized in seen_tokens:
            continue

        # Get token category
        category = get_token_category(token)

        # Check mutually exclusive groups
        # Check mutually exclusive groups
        # (This logic checks if we already have a token from this group)
        skip = False
        matching_group = None

        for group_name, group_categories in MUTUALLY_EXCLUSIVE_GROUPS.items():
            if category in group_categories:
                if group_name in seen_categories:
                    # Already have a token from this group, skip
                    skip = True
                    break
                matching_group = group_name

        if skip:
            continue

        # Check conflicting category pairs using DB cache
        # We only check against categories seen in PREVIOUS tokens
        if TagRuleCache._initialized and category:
            for seen_cat in seen_categories.values():
                if TagRuleCache.is_category_conflicting(category, seen_cat):
                    skip = True
                    break

        if skip:
            continue

        # If passed all checks, update tracking
        if matching_group:
            seen_categories[matching_group] = category

        # Check specific tag pair conflicts using DB cache
        if TagRuleCache._initialized:
            has_conflict = False
            for seen_tag in seen_tag_conflicts:
                if TagRuleCache.is_conflicting(normalized, seen_tag):
                    has_conflict = True
                    break

            if has_conflict:
                continue

        # Track this tag for future conflict checks
        seen_tag_conflicts.add(normalized)

        # Track this category for future conflict checks
        if category:
            seen_categories[category] = category

        seen_tokens.add(normalized)
        result.append(token)

    return result


def deduplicate_triggers(
    tokens: list[str],
    trigger_words: list[str],
) -> list[str]:
    """Remove trigger words that already exist in tokens.

    Args:
        tokens: Existing prompt tokens
        trigger_words: LoRA trigger words

    Returns:
        Trigger words that are not already in tokens
    """
    token_set = {t.lower().strip() for t in tokens}
    return [t for t in trigger_words if t.lower().strip() not in token_set]


# ============================================================
# 9.8.5.1: Ensure Quality Tags
# ============================================================

# Default quality tags (added if none present)
DEFAULT_QUALITY_TAGS = ["masterpiece", "best_quality", "high_quality"]


def ensure_quality_tags(tokens: list[str]) -> list[str]:
    """Ensure quality tags are present at the beginning of the prompt.

    Args:
        tokens: List of prompt tokens

    Returns:
        List with quality tags prepended if none were present

    Note:
        If any quality tag is already present, no changes are made.
        This preserves user's explicit quality tag choices.
    """
    # Check if any quality tag already exists
    for token in tokens:
        if get_token_category(token) == "quality":
            return tokens  # Already has quality tag

    # Prepend default quality tags
    return DEFAULT_QUALITY_TAGS + tokens


# ============================================================
# 9.8.2.1: BREAK Token Support
# ============================================================

BREAK_TOKEN = "BREAK"


def insert_break_token(
    tokens: list[str],
    after_category: str = "action",
    mode: EffectiveMode = "lora",
) -> list[str]:
    """Insert BREAK token after the specified category.

    BREAK separates tokens into different CLIP chunks, reducing
    LoRA influence on later tokens (typically scene descriptions).

    Args:
        tokens: Sorted list of prompt tokens
        after_category: Insert BREAK after tokens of this category
        mode: Effective mode for priority lookup

    Returns:
        List with BREAK token inserted
    """
    result: list[str] = []
    break_inserted = False
    last_priority = 0

    # Use mode-appropriate priority map
    priority_map = MODE_B_PRIORITY if mode == "lora" else CATEGORY_PRIORITY

    # Get the priority threshold for the break point
    break_after_priority = priority_map.get(after_category, 12)

    def get_priority_for_mode(token: str) -> int:
        category = get_token_category(token)
        if category:
            return priority_map.get(category, 99)
        return 99

    for token in tokens:
        priority = get_priority_for_mode(token)

        # Insert BREAK when transitioning past the threshold
        if not break_inserted and last_priority <= break_after_priority < priority:
            result.append(BREAK_TOKEN)
            break_inserted = True

        result.append(token)
        last_priority = priority

    return result


# ============================================================
# 9.8.6: Token Sorting
# ============================================================

# Mode A (Standard) priority order - as defined in CATEGORY_PRIORITY
# Quality → Subject → Identity → Appearance → Clothing → Expression → ...

# Mode B (LoRA) priority order - scene-first for better LoRA control
MODE_B_PRIORITY: dict[str, int] = {
    # Higher priority (earlier in prompt)
    "quality": 1,
    "subject": 2,
    # Scene core (before LoRA to establish scene)
    "expression": 3,
    "gaze": 4,
    "pose": 5,
    "action": 6,
    "camera": 7,
    # LoRA trigger inserted here (priority ~8)
    # Character appearance (after LoRA)
    "identity": 10,
    "hair_color": 11,
    "hair_length": 11,
    "hair_style": 11,
    "hair_accessory": 11,
    "eye_color": 11,
    "skin_color": 11,
    "body_feature": 11,
    "appearance": 11,
    "clothing": 12,
    # Scene extras (lowest priority, after BREAK)
    "location_indoor": 13,
    "location_outdoor": 13,
    "background_type": 13,
    "time_weather": 14,
    "lighting": 15,
    "mood": 16,
    "style": 17,
}


def sort_prompt_tokens(
    tokens: list[str],
    mode: EffectiveMode = "standard",
) -> list[str]:
    """Sort prompt tokens by priority based on mode.

    Args:
        tokens: List of prompt tokens (unsorted)
        mode: 'standard' or 'lora'

    Returns:
        Sorted list of tokens

    Mode A (Standard):
        Quality → Subject → Character → Appearance → Scene → Extras

    Mode B (LoRA):
        Quality → Subject → Scene Core → (LoRA) → Character → Scene Extras
    """
    priority_map = CATEGORY_PRIORITY if mode == "standard" else MODE_B_PRIORITY

    def get_priority(token: str) -> int:
        category = get_token_category(token)
        if category:
            return priority_map.get(category, 99)
        return 99

    # Stable sort - preserves order of equal-priority tokens
    return sorted(tokens, key=get_priority)


def _deduplicate_loras(lora_strings: list[str] | None) -> list[str]:
    """Deduplicate LoRA strings by name, keeping the last weight.

    Args:
        lora_strings: List of LoRA syntax strings (e.g., ["<lora:name:0.4>", "<lora:name:0.5>"])

    Returns:
        Deduplicated list with last weight preserved
    """
    if not lora_strings:
        return []

    import re
    lora_pattern = re.compile(r"<lora:([^:>]+):([^>]+)>")
    lora_map: dict[str, str] = {}  # name → full string (keeps last)

    for lora_str in lora_strings:
        match = lora_pattern.match(lora_str)
        if match:
            lora_name = match.group(1)
            lora_map[lora_name] = lora_str
        else:
            # Non-standard format, keep as-is
            lora_map[lora_str] = lora_str

    return list(lora_map.values())


def _normalize_break_tokens(tokens: list[str]) -> list[str]:
    """Normalize and deduplicate BREAK tokens.

    - Converts 'break' (lowercase) to 'BREAK'
    - Removes duplicate BREAK tokens

    Args:
        tokens: List of prompt tokens

    Returns:
        Normalized list with single BREAK tokens
    """
    result: list[str] = []
    has_break = False

    for token in tokens:
        if token.lower().strip() == "break":
            if not has_break:
                result.append(BREAK_TOKEN)
                has_break = True
            # Skip duplicate BREAK tokens
        else:
            result.append(token)

    return result


def _extract_loras_from_tokens(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Extract LoRA strings from tokens.

    Args:
        tokens: List of prompt tokens (may contain LoRA strings)

    Returns:
        Tuple of (remaining_tokens, extracted_lora_strings)
    """
    remaining: list[str] = []
    loras: list[str] = []

    for token in tokens:
        if token.startswith("<lora:"):
            loras.append(token)
        else:
            remaining.append(token)

    return remaining, loras


def compose_prompt_tokens(
    tokens: list[str],
    mode: EffectiveMode,
    lora_strings: list[str] | None = None,
    trigger_words: list[str] | None = None,
    use_break: bool = True,
) -> list[str]:
    """Compose a complete prompt with all tokens properly ordered.

    This is the main entry point for prompt composition.

    Args:
        tokens: Raw prompt tokens (unsorted, may have conflicts, may contain LoRAs)
        mode: 'standard' or 'lora'
        lora_strings: LoRA syntax strings (e.g., "<lora:name:0.5>")
        trigger_words: LoRA trigger words for deduplication
        use_break: Whether to insert BREAK token (Mode B only)

    Returns:
        Composed list of tokens ready to join into prompt string

    Note:
        If tokens contain LoRA strings (e.g., from user input), they are
        extracted and merged with lora_strings, then deduplicated.
    """
    # Step 0: Robust normalization and deduplication
    # Ensures all tags follow SD format and ignores malformed ones like _day or __sun
    from services.keywords.core import normalize_prompt_token

    unique_tokens = []
    seen_normalized = set()

    for t in tokens:
        norm = normalize_prompt_token(t)
        if norm and norm not in seen_normalized:
            # If the original has weights or parens, keep it to preserve emphasis
            # Otherwise, use the clean normalized version to fix typos like _day
            clean_tag = t
            if ":" not in t and "(" not in t:
                clean_tag = norm

            unique_tokens.append(clean_tag)
            seen_normalized.add(norm)

    tokens = unique_tokens

    if trigger_words:
        trigger_words = [normalize_prompt_token(t) for t in trigger_words if normalize_prompt_token(t)]

    # Step 0a: Normalize BREAK tokens (convert lowercase, remove duplicates)
    tokens = _normalize_break_tokens(tokens)

    # Step 0b: Extract LoRAs from tokens (user may have included them directly)
    tokens, tokens_loras = _extract_loras_from_tokens(tokens)

    # Step 0c: Merge and deduplicate all LoRA strings
    # Order: lora_strings first (API-provided), then tokens_loras (user-provided)
    # _deduplicate_loras keeps the LAST occurrence, so tokens_loras wins if duplicate
    all_loras = (lora_strings or []) + tokens_loras
    lora_strings = _deduplicate_loras(all_loras)

    # Step 0c: Extract trigger words from tokens (they'll be placed near LoRA)
    # Only keep unique triggers (deduplicate)
    trigger_set = {t.lower().strip() for t in (trigger_words or [])}
    extracted_triggers: list[str] = []
    extracted_triggers_seen: set[str] = set()
    remaining_tokens: list[str] = []

    for token in tokens:
        lower_token = token.lower().strip()
        if lower_token in trigger_set:
            # Only add if not already extracted (deduplicate)
            if lower_token not in extracted_triggers_seen:
                extracted_triggers.append(token)
                extracted_triggers_seen.add(lower_token)
        else:
            remaining_tokens.append(token)

    tokens = remaining_tokens

    # Step 1: Ensure quality tags
    tokens = ensure_quality_tags(tokens)

    # Step 2: Filter conflicts and deduplicate
    tokens = filter_conflicting_tokens(tokens, trigger_words)

    # Step 2a: Emphasize key categories (Expression, Pose, Action)
    # Wrap important tags in (tag:1.2) to ensure they are respected
    emphasized_tokens = []
    for token in tokens:
        category = get_token_category(token)
        if category in ["expression", "pose", "action", "gaze"]:
            # Check if already emphasized (contains parenthesis or colon)
            if "(" not in token and ":" not in token:
                emphasized_tokens.append(f"({token}:1.2)")
            else:
                emphasized_tokens.append(token)
        else:
            emphasized_tokens.append(token)
    tokens = emphasized_tokens

    # Step 3: Sort by mode-specific priority
    tokens = sort_prompt_tokens(tokens, mode)

    # Step 4: Insert trigger words and LoRA strings (for Mode B, after scene core)
    if mode == "lora":
        # Find insertion point (after camera, before identity)
        insert_idx = 0
        for i, token in enumerate(tokens):
            category = get_token_category(token)
            priority = MODE_B_PRIORITY.get(category, 99) if category else 99
            if priority >= 10:  # identity or later
                insert_idx = i
                break
        else:
            insert_idx = len(tokens)

        # Insert trigger words first
        for trigger in extracted_triggers:
            tokens.insert(insert_idx, trigger)
            insert_idx += 1

        # Then LoRA strings
        if lora_strings:
            for lora_str in lora_strings:
                tokens.insert(insert_idx, lora_str)
                insert_idx += 1

    elif mode == "standard":
        # For standard mode, insert trigger + LoRA after identity
        insert_idx = 0
        for i, token in enumerate(tokens):
            category = get_token_category(token)
            priority = CATEGORY_PRIORITY.get(category, 99) if category else 99
            if priority > 3:  # after identity
                insert_idx = i
                break
        else:
            insert_idx = len(tokens)

        # Insert trigger words first
        for trigger in extracted_triggers:
            tokens.insert(insert_idx, trigger)
            insert_idx += 1

        # Then LoRA strings
        if lora_strings:
            for lora_str in lora_strings:
                tokens.insert(insert_idx, lora_str)
                insert_idx += 1

    # Step 5: Insert BREAK token (Mode B only)
    # Insert after clothing tokens, before location/lighting/mood
    # Skip if BREAK already exists (from user input)
    has_break = BREAK_TOKEN in tokens
    if use_break and mode == "lora" and not has_break:
        # Find the last clothing token position
        last_clothing_idx = -1
        for i, token in enumerate(tokens):
            # Skip LoRA tags
            if token.startswith("<lora:"):
                continue
            category = get_token_category(token)
            if category == "clothing":
                last_clothing_idx = i

        # If no clothing found, insert after the last non-location/mood token
        if last_clothing_idx == -1:
            for i, token in enumerate(tokens):
                if token.startswith("<lora:"):
                    continue
                category = get_token_category(token)
                priority = MODE_B_PRIORITY.get(category, 99) if category else 99
                if priority >= 13:  # location_indoor or later
                    last_clothing_idx = i - 1
                    break
            else:
                last_clothing_idx = len(tokens) - 1

        # Insert BREAK after the clothing token
        if last_clothing_idx >= 0 and last_clothing_idx < len(tokens) - 1:
            tokens.insert(last_clothing_idx + 1, BREAK_TOKEN)

    return tokens


def compose_prompt_string(
    tokens: list[str],
    mode: EffectiveMode,
    lora_strings: list[str] | None = None,
    trigger_words: list[str] | None = None,
    use_break: bool = True,
) -> str:
    """Compose a complete prompt string.

    Convenience wrapper around compose_prompt_tokens that joins the result.

    Args:
        (same as compose_prompt_tokens)

    Returns:
        Prompt string with tokens joined by ", "
    """
    tokens = compose_prompt_tokens(
        tokens=tokens,
        mode=mode,
        lora_strings=lora_strings,
        trigger_words=trigger_words,
        use_break=use_break,
    )
    return ", ".join(tokens)


def get_effective_mode(
    character: Character,
    loras: list[LoRA] | None = None,
) -> EffectiveMode:
    """Determine the effective prompt mode for a character.

    Args:
        character: Character model instance
        loras: Optional list of resolved LoRA models (with lora_type field)

    Returns:
        'standard' or 'lora' based on character settings and LoRA presence

    Logic:
        - If prompt_mode is 'standard' → return 'standard'
        - If prompt_mode is 'lora' → return 'lora'
        - If prompt_mode is 'auto':
            - Check if any LoRA has lora_type == 'character'
            - If yes → 'lora'
            - Otherwise → 'standard'
    """
    prompt_mode = getattr(character, "prompt_mode", "auto") or "auto"

    # Explicit mode overrides
    if prompt_mode == "standard":
        logger.debug("[PromptMode] Explicit standard mode for character %s", character.name)
        return "standard"

    if prompt_mode == "lora":
        logger.debug("[PromptMode] Explicit lora mode for character %s", character.name)
        return "lora"

    # Auto mode: detect based on LoRA presence
    if not loras:
        logger.debug("[PromptMode] Auto → standard (no LoRAs) for character %s", character.name)
        return "standard"

    # Check for character-type LoRA
    has_character_lora = any(
        getattr(lora, "lora_type", None) == "character" for lora in loras
    )

    if has_character_lora:
        logger.debug("[PromptMode] Auto → lora (character LoRA found) for character %s", character.name)
        return "lora"

    logger.debug("[PromptMode] Auto → standard (style-only LoRAs) for character %s", character.name)
    return "standard"


def get_effective_mode_from_dict(
    prompt_mode: str,
    loras: list[dict] | None = None,
) -> EffectiveMode:
    """Determine the effective prompt mode from dict data.

    Useful for API endpoints that receive JSON data.

    Args:
        prompt_mode: 'auto', 'standard', or 'lora'
        loras: Optional list of LoRA dicts with 'lora_type' field

    Returns:
        'standard' or 'lora'
    """
    prompt_mode = prompt_mode or "auto"

    if prompt_mode == "standard":
        return "standard"

    if prompt_mode == "lora":
        return "lora"

    # Auto mode
    if not loras:
        return "standard"

    has_character_lora = any(
        lora.get("lora_type") == "character" for lora in loras
    )

    return "lora" if has_character_lora else "standard"
