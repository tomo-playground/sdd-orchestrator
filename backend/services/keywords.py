"""Keyword management service.

Handles keyword normalization, synonyms, categories, and suggestions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from config import BASE_DIR, CACHE_DIR, logger

# --- Lazy imports for circular dependency avoidance ---
_split_prompt_tokens = None
_normalize_prompt_tokens = None


def _get_base_dir() -> Path:
    return BASE_DIR


def _get_cache_dir() -> Path:
    return CACHE_DIR


def _get_logger():
    return logger


def _get_split_prompt_tokens():
    global _split_prompt_tokens
    if _split_prompt_tokens is None:
        from services.prompt import split_prompt_tokens
        _split_prompt_tokens = split_prompt_tokens
    return _split_prompt_tokens


def _get_normalize_prompt_tokens():
    global _normalize_prompt_tokens
    if _normalize_prompt_tokens is None:
        from services.prompt import normalize_prompt_tokens
        _normalize_prompt_tokens = normalize_prompt_tokens
    return _normalize_prompt_tokens


# --- Keyword cache ---
_KEYWORD_SYNONYMS: dict[str, set[str]] = {}
_KEYWORD_IGNORE: set[str] = set()
_KEYWORD_CATEGORIES: dict[str, list[str]] = {}


def normalize_prompt_token(token: str) -> str:
    """Normalize a single prompt token for comparison."""
    cleaned = token.strip()
    if not cleaned:
        return ""
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return ""
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = cleaned[1:-1]
    cleaned = re.sub(r":[0-9.]*$", "", cleaned)
    cleaned = cleaned.replace("_", " ")
    return cleaned.strip().lower()


def load_keyword_map() -> tuple[dict[str, set[str]], set[str], dict[str, list[str]]]:
    """Load keyword synonyms, ignore list, and categories from keywords.json."""
    global _KEYWORD_SYNONYMS, _KEYWORD_IGNORE, _KEYWORD_CATEGORIES
    if _KEYWORD_SYNONYMS or _KEYWORD_IGNORE or _KEYWORD_CATEGORIES:
        return _KEYWORD_SYNONYMS, _KEYWORD_IGNORE, _KEYWORD_CATEGORIES

    keyword_path = _get_base_dir() / "keywords.json"
    if not keyword_path.exists():
        return {}, set(), {}
    data = json.loads(keyword_path.read_text(encoding="utf-8"))
    synonyms: dict[str, set[str]] = {}
    for key, values in (data.get("synonyms") or {}).items():
        base = normalize_prompt_token(key)
        if not base:
            continue
        entries = {base}
        for value in values or []:
            normalized = normalize_prompt_token(value)
            if normalized:
                entries.add(normalized)
        synonyms[base] = entries
    ignore = {normalize_prompt_token(item) for item in data.get("ignore", [])}
    categories = {}
    for key, values in (data.get("categories") or {}).items():
        normalized = [normalize_prompt_token(item) for item in (values or [])]
        categories[key] = [item for item in normalized if item]
    _KEYWORD_SYNONYMS = synonyms
    _KEYWORD_IGNORE = {item for item in ignore if item}
    _KEYWORD_CATEGORIES = categories
    return _KEYWORD_SYNONYMS, _KEYWORD_IGNORE, _KEYWORD_CATEGORIES


def expand_synonyms(tokens: list[str]) -> set[str]:
    """Expand a list of tokens to include all known synonyms."""
    synonyms_map, _, _ = load_keyword_map()
    expanded: set[str] = set()
    for token in tokens:
        if not token:
            continue
        expanded.add(token)
        if token in synonyms_map:
            expanded.update(synonyms_map[token])
    return expanded


def load_known_keywords() -> set[str]:
    """Load all known keywords (from categories, synonyms, and ignore list)."""
    synonyms_map, ignore_tokens, categories = load_keyword_map()
    known: set[str] = set(ignore_tokens)
    for values in categories.values():
        known.update(values)
    for key, values in synonyms_map.items():
        known.add(key)
        known.update(values)
    return {token for token in known if token}


def update_keyword_suggestions(unknown_tags: list[str]) -> None:
    """Update the keyword suggestions cache with newly encountered unknown tags."""
    if not unknown_tags:
        return
    suggestions_path = _get_cache_dir() / "keyword_suggestions.json"
    try:
        if suggestions_path.exists():
            data = json.loads(suggestions_path.read_text(encoding="utf-8"))
        else:
            data = {}
        for tag in unknown_tags:
            data[tag] = int(data.get(tag, 0)) + 1
        suggestions_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        _get_logger().exception("Failed to update keyword suggestions")


def reset_keyword_cache() -> None:
    """Reset the in-memory keyword cache to force reload on next access."""
    global _KEYWORD_SYNONYMS, _KEYWORD_IGNORE, _KEYWORD_CATEGORIES
    _KEYWORD_SYNONYMS = {}
    _KEYWORD_IGNORE = set()
    _KEYWORD_CATEGORIES = {}


def load_keywords_file() -> dict[str, Any]:
    """Load the raw keywords.json file."""
    keyword_path = _get_base_dir() / "keywords.json"
    if not keyword_path.exists():
        raise FileNotFoundError("keywords.json not found")
    return json.loads(keyword_path.read_text(encoding="utf-8"))


def save_keywords_file(data: dict[str, Any]) -> None:
    """Save data to keywords.json file."""
    keyword_path = _get_base_dir() / "keywords.json"
    keyword_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def load_keyword_suggestions(min_count: int = 1, limit: int = 50) -> list[dict[str, Any]]:
    """Load keyword suggestions filtered by minimum count."""
    suggestions_path = _get_cache_dir() / "keyword_suggestions.json"
    if not suggestions_path.exists():
        return []
    try:
        data = json.loads(suggestions_path.read_text(encoding="utf-8"))
    except Exception:
        _get_logger().exception("Failed to read keyword suggestions")
        return []
    known = load_known_keywords()
    items = [
        {"tag": tag, "count": int(count)}
        for tag, count in data.items()
        if int(count) >= min_count and tag not in known
    ]
    items.sort(key=lambda item: (-item["count"], item["tag"]))
    return items[:max(1, limit)]


def format_keyword_context() -> str:
    """Format keyword categories for use in prompts."""
    _, _, categories = load_keyword_map()
    if not categories:
        return ""
    lines = ["Allowed Keywords (use exactly as written):"]
    for key in sorted(categories.keys()):
        values = categories[key]
        if not values:
            continue
        lines.append(f"- {key}: {', '.join(values)}")
    return "\n".join(lines)


def filter_prompt_tokens(prompt: str) -> str:
    """Filter prompt tokens to only include known/allowed keywords."""
    synonyms_map, ignore_tokens, categories = load_keyword_map()
    allowed = {token for values in categories.values() for token in values}
    if not allowed:
        return _get_normalize_prompt_tokens()(prompt)
    synonym_lookup = {
        variant: base
        for base, variants in synonyms_map.items()
        for variant in variants
    }
    tokens = _get_split_prompt_tokens()(prompt)
    cleaned: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        normalized = normalize_prompt_token(token)
        if not normalized or normalized in ignore_tokens:
            continue
        base = None
        if normalized in allowed:
            base = normalized
        elif normalized in synonym_lookup and synonym_lookup[normalized] in allowed:
            base = synonym_lookup[normalized]
        if base and base not in seen:
            cleaned.append(base)
            seen.add(base)
    return ", ".join(cleaned)
