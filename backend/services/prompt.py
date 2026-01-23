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
        seen = set()
        ordered: list[str] = []
        for tag in tags:
            key = tag.lower()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(tag)
        return ordered

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
