"""Prompt processing functions for Shorts Producer Backend."""

from __future__ import annotations

import hashlib
import json
import re
import time

from fastapi import HTTPException

from config import CACHE_DIR, CACHE_TTL_SECONDS, GEMINI_TEXT_MODEL, gemini_client, logger
from schemas import PromptRewriteRequest, PromptSplitRequest


def split_prompt_tokens(prompt: str) -> list[str]:
    """Split a comma-separated prompt into individual tokens."""
    return [token.strip() for token in prompt.split(",") if token.strip()]


def merge_prompt_tokens(primary: list[str], secondary: list[str]) -> str:
    """Merge two lists of prompt tokens, removing duplicates while preserving order.
    
    Uses normalize_prompt_token for deduplication, so "tag" and "(tag:1.2)" 
    are treated as the same tag. The last occurrence wins (override).
    """
    from services.keywords.core import normalize_prompt_token

    unique_map: dict[str, str] = {}
    
    for token in primary + secondary:
        t_strip = token.strip()
        if not t_strip:
            continue
            
        # Special case: LoRA and BREAK
        # normalize_prompt_token returns empty for <lora:...>, so handle separately
        if t_strip == "BREAK" or (t_strip.startswith("<") and t_strip.endswith(">")):
            # Deduplicate exact string matches for special tokens
            key = t_strip.lower()
            unique_map[key] = token
            continue

        # Normal tags: use normalized base for key
        key = normalize_prompt_token(t_strip)
        if not key:
            # Fallback if normalization fails (should be rare)
            unique_map[t_strip.lower()] = token
            continue
            
        unique_map[key] = token
        
    return ", ".join(unique_map.values())


# Scene-specific keywords for detecting scene tokens
SCENE_KEYWORDS = [
    "sitting", "standing", "walking", "running", "jumping", "kneeling", "crouching", "lying",
    "from_above", "top-down", "low_angle", "high_angle", "close-up", "wide_shot", "full_body",
    "library", "cafe", "street", "room", "bedroom", "office", "classroom", "park", "forest",
    "beach", "city", "night", "sunset", "sunrise", "rain", "snow", "background", "lighting",
    "indoors", "outdoors"
]


def is_scene_token(token: str) -> bool:
    """Check if a token represents a scene-related keyword."""
    lower = token.lower()
    return any(keyword in lower for keyword in SCENE_KEYWORDS)


def normalize_prompt_tokens(prompt: str) -> str:
    """Normalize prompt tokens by deduplicating and preserving LoRA/model tags."""
    lora_tags = re.findall(r"<lora:[^>]+>", prompt, flags=re.IGNORECASE)
    model_tags = re.findall(r"<model:[^>]+>", prompt, flags=re.IGNORECASE)

    def unique_tags(tags: list[str]) -> list[str]:
        # Deduplicate by LoRA/model name only (ignore weight differences)
        # Last occurrence wins (has the latest/correct weight)
        name_pattern = re.compile(r"<(?:lora|model):([^:>]+)", re.IGNORECASE)
        seen_names: dict[str, str] = {}  # name → full tag
        for tag in tags:
            match = name_pattern.search(tag)
            if match:
                name = match.group(1).lower()
                seen_names[name] = tag  # Last one wins
            else:
                seen_names[tag.lower()] = tag
        return list(seen_names.values())

    unique_lora = unique_tags(lora_tags)
    unique_model = unique_tags(model_tags)
    cleaned = re.sub(r"<lora:[^>]+>", "", prompt, flags=re.IGNORECASE)
    cleaned = re.sub(r"<model:[^>]+>", "", cleaned, flags=re.IGNORECASE)
    tokens = split_prompt_tokens(cleaned)

    # Normalize tag format (space → underscore) for SD compatibility
    tokens = normalize_tag_spaces(tokens)

    seen = set()
    merged: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(token)
    merged.extend(unique_lora)
    merged.extend(unique_model)
    return ", ".join(merged)


def normalize_negative_prompt(negative: str) -> str:
    """Normalize negative prompt by deduplicating tokens."""
    tokens = split_prompt_tokens(negative)
    seen = set()
    merged: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(token)
    return ", ".join(merged)


def extract_lora_names(prompt: str) -> list[str]:
    """Extract LoRA names from prompt.

    Args:
        prompt: Full prompt string containing <lora:name:weight> tags

    Returns:
        List of LoRA names found in the prompt
    """
    matches = re.findall(r"<lora:([^:>]+):[^>]+>", prompt, flags=re.IGNORECASE)
    return [m.strip() for m in matches if m.strip()]


def validate_loras(prompt: str, available_loras: list[str]) -> dict:
    """Validate that all LoRAs in prompt exist in SD WebUI.

    Args:
        prompt: Full prompt string containing <lora:name:weight> tags
        available_loras: List of LoRA names available in SD WebUI

    Returns:
        Dict with validation result:
        {
            "valid": bool,
            "prompt_loras": list[str],  # LoRAs found in prompt
            "missing": list[str],        # LoRAs not found in SD WebUI
            "available": list[str],      # Available LoRAs (for reference)
        }
    """
    prompt_loras = extract_lora_names(prompt)
    if not prompt_loras:
        return {
            "valid": True,
            "prompt_loras": [],
            "missing": [],
            "available": available_loras,
        }

    # Normalize names for comparison (lowercase, no extension)
    available_set = {name.lower().replace(".safetensors", "") for name in available_loras}

    missing = []
    for lora_name in prompt_loras:
        normalized = lora_name.lower().replace(".safetensors", "")
        if normalized not in available_set:
            missing.append(lora_name)

    return {
        "valid": len(missing) == 0,
        "prompt_loras": prompt_loras,
        "missing": missing,
        "available": available_loras,
    }


def detect_prompt_conflicts(positive: str, negative: str) -> dict:
    """Detect conflicts between positive and negative prompts.

    Args:
        positive: Positive prompt string
        negative: Negative prompt string

    Returns:
        Dict with conflict detection result:
        {
            "has_conflicts": bool,
            "conflicts": list[str],  # Tags present in both prompts
        }
    """
    # Extract tokens (excluding LoRA/model tags)
    pos_cleaned = re.sub(r"<lora:[^>]+>", "", positive, flags=re.IGNORECASE)
    pos_cleaned = re.sub(r"<model:[^>]+>", "", pos_cleaned, flags=re.IGNORECASE)
    neg_cleaned = re.sub(r"<lora:[^>]+>", "", negative, flags=re.IGNORECASE)
    neg_cleaned = re.sub(r"<model:[^>]+>", "", neg_cleaned, flags=re.IGNORECASE)

    pos_tokens = {t.lower().strip() for t in split_prompt_tokens(pos_cleaned)}
    neg_tokens = {t.lower().strip() for t in split_prompt_tokens(neg_cleaned)}

    conflicts = list(pos_tokens & neg_tokens)

    return {
        "has_conflicts": len(conflicts) > 0,
        "conflicts": conflicts,
    }


# Identity tags that indicate character presence
IDENTITY_TAGS = [
    "1girl", "1boy", "2girls", "2boys", "3girls", "3boys",
    "multiple_girls", "multiple_boys",
    "solo", "duo", "trio", "group",
    "male_focus", "female_focus",
]


def validate_identity_tags(prompt: str) -> dict:
    """Validate that prompt contains at least one identity tag.

    Identity tags (1girl, 1boy, etc.) are essential for SD to understand
    who/what should be in the image. Missing these often leads to
    generation failures or unexpected results.

    Args:
        prompt: Positive prompt string

    Returns:
        Dict with validation result:
        {
            "valid": bool,
            "found_tags": list[str],  # Identity tags found in prompt
            "suggested": str,         # Suggestion if missing
        }
    """
    # Clean prompt (remove LoRA/model tags)
    cleaned = re.sub(r"<lora:[^>]+>", "", prompt, flags=re.IGNORECASE)
    cleaned = re.sub(r"<model:[^>]+>", "", cleaned, flags=re.IGNORECASE)
    tokens = {t.lower().strip() for t in split_prompt_tokens(cleaned)}

    found_tags = [tag for tag in IDENTITY_TAGS if tag in tokens]

    return {
        "valid": len(found_tags) > 0,
        "found_tags": found_tags,
        "suggested": "Add identity tag like '1girl' or '1boy' at the start of your prompt"
        if not found_tags
        else "",
    }


def apply_optimal_lora_weights(prompt: str, lora_weights: dict[str, float]) -> str:
    """Apply optimal weights to LoRA tags in prompt.

    Replaces weights in <lora:name:weight> tags with optimal weights from DB.
    Preserves original weight if no optimal weight is available.

    Args:
        prompt: Prompt string with LoRA tags
        lora_weights: Dict mapping LoRA names to optimal weights

    Returns:
        Prompt with optimized LoRA weights
    """
    if not lora_weights:
        return prompt

    def replace_weight(match: re.Match) -> str:
        lora_name = match.group(1)
        # Normalize name for lookup (lowercase, no extension)
        normalized = lora_name.lower().replace(".safetensors", "")
        if normalized in lora_weights:
            return f"<lora:{lora_name}:{lora_weights[normalized]}>"
        return match.group(0)  # Keep original

    return re.sub(r"<lora:([^:>]+):[^>]+>", replace_weight, prompt, flags=re.IGNORECASE)

def rewrite_prompt(request: PromptRewriteRequest) -> dict:
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    if not request.base_prompt or not request.scene_prompt:
        raise HTTPException(status_code=400, detail="Base prompt and scene prompt are required")

    cache_key = hashlib.sha256(
        f"{request.base_prompt}|{request.scene_prompt}|{request.style}|{request.mode}".encode()
    ).hexdigest()
    cache_file = CACHE_DIR / f"prompt_{cache_key}.json"
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < CACHE_TTL_SECONDS:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            return {"prompt": cached.get("prompt", "")}

    if request.mode == "scene":
        instruction = (
            "Convert SCENE into Stable Diffusion tag-style prompt. "
            "Use comma-separated short tags, no full sentences. "
            "Include camera/shot keywords if implied. Return ONLY the tags."
        )
    else:
        instruction = (
            "Rewrite a Stable Diffusion prompt. Keep the identity/style tokens from BASE. "
            "Replace scene/action/pose with SCENE. Preserve any <lora:...> tags. "
            "Return ONLY the final comma-separated prompt, no explanations."
        )
    user_input = (
        f"BASE: {request.base_prompt}\n"
        f"SCENE: {request.scene_prompt}\n"
        f"STYLE: {request.style}\n"
    )
    try:
        res = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=f"{instruction}\n\n{user_input}",
        )
        text = res.text.strip().replace("```", "")
        if request.mode == "scene":
            cache_file.write_text(json.dumps({"prompt": text}, ensure_ascii=False))
            return {"prompt": text}
        base_tokens = split_prompt_tokens(request.base_prompt)
        base_core = [
            token for token in base_tokens
            if "<lora:" in token.lower() or not is_scene_token(token)
        ]
        rewritten_tokens = split_prompt_tokens(text)
        final_prompt = merge_prompt_tokens(base_core, rewritten_tokens)
        cache_file.write_text(json.dumps({"prompt": final_prompt}, ensure_ascii=False))
        return {"prompt": final_prompt}
    except Exception as exc:
        logger.exception("Prompt rewrite failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

def split_prompt_example(request: PromptSplitRequest) -> dict:
    if not gemini_client:
        raise HTTPException(status_code=503, detail="Gemini key missing")
    if not request.example_prompt:
        raise HTTPException(status_code=400, detail="Example prompt is required")

    instruction = (
        "Split the EXAMPLE prompt into BASE and SCENE for Stable Diffusion. "
        "BASE should keep identity/style/LoRA tokens. SCENE should keep action, pose, "
        "camera, and background. Return ONLY JSON with keys base_prompt and scene_prompt."
    )
    user_input = f"EXAMPLE: {request.example_prompt}\nSTYLE: {request.style}\n"
    try:
        res = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=f"{instruction}\n\n{user_input}",
        )
        text = res.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
        return {
            "base_prompt": data.get("base_prompt", ""),
            "scene_prompt": data.get("scene_prompt", ""),
        }
    except Exception as exc:
        logger.exception("Prompt split failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def normalize_tag_spaces(tags: list[str]) -> list[str]:
    """Normalize tag format: spaces to underscores.

    Stable Diffusion uses underscores, not spaces.
    Example:
    - "thumbs up" → "thumbs_up"
    - " _day " → "day" (strips leading/trailing underscores)
    - "tag__1" → "tag_1" (deduplicates underscores)
    """
    normalized = []
    for tag in tags:
        # 1. Strip whitespace
        t = tag.strip()
        if not t:
            continue
        
        # 2. Replace spaces with underscores
        t = t.replace(" ", "_")
        
        # 3. Strip leading/trailing underscores (Fix for _day, _sun)
        t = t.strip("_")
        
        # 4. Collapse multiple underscores
        while "__" in t:
            t = t.replace("__", "_")
            
        if t:
            normalized.append(t)
            
    return normalized



def fix_compound_adjectives(tags: list[str]) -> list[str]:
    """Fix compound adjective tags by separating them.

    Gemini often generates invalid compound tags not in Danbooru:
    - "short green hair" (0 posts) → "short_hair, green_hair" (2.7M + 519K posts)
    - "white blue dress" (0 posts) → "white_dress, blue_dress"

    This function detects common patterns and splits them into valid tags.

    Args:
        tags: List of normalized tags (underscores)

    Returns:
        List of fixed tags with compounds separated
    """
    import re

    # Pattern: (adj1)_(adj2)_(noun)
    # Common nouns that get compound adjectives
    COMPOUND_PATTERNS = [
        # Hair: "short_green_hair" → "short_hair", "green_hair"
        (
            r"^(short|long|medium)_([\w]+)_hair$",
            lambda m: [f"{m.group(1)}_hair", f"{m.group(2)}_hair"],
        ),
        # Clothing: "white_blue_dress" → "white_dress", "blue_dress"
        (
            r"^([\w]+)_([\w]+)_(dress|shirt|skirt|pants|shorts|hoodie)$",
            lambda m: [f"{m.group(1)}_{m.group(3)}", f"{m.group(2)}_{m.group(3)}"],
        ),
        # Accessories: "black_white_ribbon" → "black_ribbon", "white_ribbon"
        (
            r"^([\w]+)_([\w]+)_(ribbon|bow|tie|hat|cap)$",
            lambda m: [f"{m.group(1)}_{m.group(3)}", f"{m.group(2)}_{m.group(3)}"],
        ),
    ]

    fixed_tags = []
    for tag in tags:
        matched = False
        for pattern, replacer in COMPOUND_PATTERNS:
            match = re.match(pattern, tag)
            if match:
                # Split compound into separate tags
                fixed_tags.extend(replacer(match))
                matched = True
                break

        if not matched:
            # Keep original tag
            fixed_tags.append(tag)

    return fixed_tags


def validate_tags_with_danbooru(tags: list[str]) -> list[str]:
    """Validate tags against Danbooru and fix invalid ones (smart caching).

    Efficient validation strategy:
    1. Fast path (99% cases): Check local DB - if tag exists, accept immediately (0ms)
    2. Slow path (1% cases): Query Danbooru API only for unknown tags
    3. Cache results: Add validated tags to DB for next time

    This avoids unnecessary API calls. Typical storyboard:
    - 120 tags total
    - 115 in DB (fast path, 0ms)
    - 5 new tags (Danbooru API, ~2.5s)

    Args:
        tags: List of normalized tags (already underscore-formatted)

    Returns:
        List of validated tags with invalid ones fixed
    """
    from database import SessionLocal
    from models.tag import Tag

    db = SessionLocal()
    validated = []
    session_cache = {}  # Cache within this function call

    try:
        # Load all existing tags from DB (fast)
        existing_tags = {tag.name for tag in db.query(Tag.name).all()}
        from config import logger

        for tag in tags:
            # Fast path: Tag already in DB (try both formats)
            if tag in existing_tags:
                validated.append(tag)
                logger.debug(f"[Danbooru] Fast path (exact): {tag}")
                continue
            # Try space format for legacy DB tags
            elif tag.replace("_", " ") in existing_tags:
                validated.append(tag)  # Keep underscore format
                logger.debug(f"[Danbooru] Fast path (space): {tag.replace('_', ' ')} → {tag}")
                continue

            # Session cache: Already checked in this call
            if tag in session_cache:
                result = session_cache[tag]
                if result:
                    validated.extend(result if isinstance(result, list) else [result])
                continue

            # Slow path: New tag - check Danbooru
            try:
                from services.danbooru import get_tag_info_sync

                # Try underscore format first (SD standard)
                tag_info = get_tag_info_sync(tag)

                # If not found, try space format (Danbooru may prefer spaces)
                if not tag_info or tag_info.get("post_count", 0) == 0:
                    space_tag = tag.replace("_", " ")
                    if space_tag != tag:
                        logger.debug(f"[Danbooru] Trying space format: {space_tag}")
                        tag_info = get_tag_info_sync(space_tag)

                if tag_info and tag_info.get("post_count", 0) > 0:
                    # Valid tag - add to DB and validated list
                    validated.append(tag)
                    session_cache[tag] = tag

                    post_count = tag_info.get("post_count", 0)
                    logger.info(f"[Danbooru] ✅ Valid: {tag} ({post_count:,} posts)")

                    # Add to DB for next time (fast path)
                    category = tag_info.get("category", "unknown")
                    new_tag = Tag(
                        name=tag,
                        category=category,
                        group_name="danbooru_validated",
                    )
                    db.add(new_tag)
                    db.commit()

                else:
                    # Invalid tag (0 posts) - try to fix
                    logger.warning(f"[Danbooru] ❌ Invalid: {tag} (0 posts)")

                    # Attempt to split compound adjectives
                    fixed = fix_compound_adjectives([tag])
                    if len(fixed) > 1:
                        # Successfully split - use the parts
                        validated.extend(fixed)
                        session_cache[tag] = fixed
                        logger.info(f"[Danbooru] 🔧 Split: {tag} → {fixed}")
                    else:
                        # Can't fix - log and skip
                        logger.warning(f"[Danbooru] ⚠️  Skipping: {tag} (unfixable)")
                        session_cache[tag] = None

            except Exception as exc:
                logger.error(f"[Danbooru] 🚨 API Error for {tag}: {exc}")
                # On error, keep the tag (fail-open)
                validated.append(tag)
                session_cache[tag] = tag

        return validated

    finally:
        db.close()


def normalize_and_fix_tags(prompt: str) -> str:
    """Full pipeline: normalize spaces + fix compound adjectives.

    This is the main entry point for cleaning Gemini-generated prompts.

    Pipeline:
    1. Split prompt into tags
    2. Normalize spaces → underscores
    3. Fix compound adjective patterns
    4. Join back into prompt string

    Args:
        prompt: Raw prompt string from Gemini (may have spaces, compounds)

    Returns:
        Cleaned prompt string ready for SD

    Example:
        >>> normalize_and_fix_tags("short green hair, thumbs up, smiling")
        "short_hair, green_hair, thumbs_up, smiling"
    """
    if not prompt or not prompt.strip():
        return ""

    # Split into individual tags
    tags = [t.strip() for t in prompt.split(",") if t.strip()]

    # Step 1: Normalize spaces
    tags = normalize_tag_spaces(tags)

    # Step 2: Fix compound adjectives
    tags = fix_compound_adjectives(tags)

    # Join back into prompt
    return ", ".join(tags)
