"""Prompt processing functions for Shorts Producer Backend."""

from __future__ import annotations

import re


def split_prompt_tokens(prompt: str) -> list[str]:
    """Split a comma-separated prompt into individual tokens."""
    return [token.strip() for token in prompt.split(",") if token.strip()]


def merge_prompt_tokens(primary: list[str], secondary: list[str]) -> str:
    """Merge two lists of prompt tokens, removing duplicates while preserving order."""
    seen = set()
    merged: list[str] = []
    for token in primary + secondary:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(token)
    return ", ".join(merged)


# Scene-specific keywords for detecting scene tokens
SCENE_KEYWORDS = [
    "sitting", "standing", "walking", "running", "jumping", "kneeling", "crouching", "lying",
    "from above", "top-down", "low angle", "high angle", "close-up", "wide shot", "full body",
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
    "multiple girls", "multiple boys",
    "solo", "duo", "trio", "group",
    "male focus", "female focus",
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
