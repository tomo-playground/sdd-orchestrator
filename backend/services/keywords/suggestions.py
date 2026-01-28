from __future__ import annotations

import json
from typing import Any

from .core import _get_cache_dir, _get_logger, normalize_prompt_token
from .db import load_known_keywords
from .patterns import suggest_category_for_tag


def update_keyword_suggestions(unknown_tags: list[str]) -> None:
    """Update the keyword suggestions cache with unknown tags."""
    if not unknown_tags: return
    suggestions_path = _get_cache_dir() / "keyword_suggestions.json"
    try:
        data = json.loads(suggestions_path.read_text(encoding="utf-8")) if suggestions_path.exists() else {}
        for tag in unknown_tags:
            normalized_tag = normalize_prompt_token(tag.replace(" ", "_"))
            if not normalized_tag: continue
            data[normalized_tag] = int(data.get(normalized_tag, 0)) + 1
        suggestions_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception:
        _get_logger().exception("Failed to update keyword suggestions")


def load_keyword_suggestions(min_count: int = 1, limit: int = 50) -> list[dict[str, Any]]:
    """Load keyword suggestions filtered by minimum count."""
    suggestions_path = _get_cache_dir() / "keyword_suggestions.json"
    if not suggestions_path.exists(): return []
    try:
        data = json.loads(suggestions_path.read_text(encoding="utf-8"))
    except Exception:
        _get_logger().exception("Failed to read keyword suggestions")
        return []

    known = load_known_keywords()
    items = []
    for tag, count in data.items():
        normalized_tag = normalize_prompt_token(tag.replace(" ", "_"))
        if not normalized_tag: continue
        if int(count) >= min_count and normalized_tag not in known:
            category, confidence = suggest_category_for_tag(normalized_tag)
            items.append({
                "tag": normalized_tag, "count": int(count),
                "suggested_category": category, "confidence": confidence,
            })
    items.sort(key=lambda item: (-item["count"], item["tag"]))
    return items[:max(1, limit)]
