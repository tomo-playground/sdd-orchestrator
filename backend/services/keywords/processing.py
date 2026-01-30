from __future__ import annotations

from config import TAG_EFFECTIVENESS_THRESHOLD, TAG_MIN_USE_COUNT_FOR_FILTERING

from .core import (
    IGNORE_TOKENS,
    _get_logger,
    _get_normalize_prompt_tokens,
    _get_split_prompt_tokens,
    normalize_prompt_token,
)


def replace_deprecated_tags(tokens: list[str]) -> tuple[list[str], dict[str, str]]:
    """Replace deprecated tags with their active replacements.

    Args:
        tokens: List of prompt tokens

    Returns:
        Tuple of (replaced_tokens, replacement_map)
        replacement_map: {deprecated_tag: replacement_tag}

    Example:
        >>> replace_deprecated_tags(["1girl", "room", "sitting"])
        (["1girl", "indoors", "sitting"], {"room": "indoors"})
    """
    from database import SessionLocal
    from models.tag import Tag

    db = SessionLocal()
    try:
        # Get all deprecated tags and their replacements in one query
        deprecated_tags = db.query(Tag).filter(
            Tag.is_active == False,
            Tag.replacement_tag_id.isnot(None)
        ).all()

        # Build replacement map: {deprecated_name: replacement_name}
        replacement_map = {}
        for tag in deprecated_tags:
            if tag.replacement_tag_id:
                replacement = db.query(Tag).filter(Tag.id == tag.replacement_tag_id).first()
                if replacement:
                    replacement_map[tag.name.lower()] = replacement.name

        # Replace tokens
        result = []
        replacements_made = {}

        for token in tokens:
            normalized = normalize_prompt_token(token)
            if normalized in replacement_map:
                replacement = replacement_map[normalized]
                result.append(replacement)
                replacements_made[normalized] = replacement
                _get_logger().info(
                    f"[TagReplacement] Deprecated tag '{normalized}' → '{replacement}'"
                )
            else:
                result.append(token)

        return result, replacements_made

    finally:
        db.close()


def expand_synonyms(tokens: list[str]) -> set[str]:
    """Expand a list of tokens to include all known synonyms (bidirectional)."""
    import services.keywords as kw
    synonym_lookup = kw.load_synonyms_from_db()
    reverse_map: dict[str, set[str]] = {}
    for syn, tag in synonym_lookup.items():
        if tag not in reverse_map: reverse_map[tag] = set()
        reverse_map[tag].add(syn)

    expanded: set[str] = set()
    for token in tokens:
        if not token: continue
        normalized = normalize_prompt_token(token)
        expanded.add(normalized)
        if normalized in reverse_map: expanded.update(reverse_map[normalized])
        if normalized in synonym_lookup: expanded.add(synonym_lookup[normalized])
    return expanded


def filter_prompt_tokens(prompt: str) -> str:
    """Filter prompt tokens to only include known/allowed keywords (DB-based)."""
    import services.keywords as kw
    from services.keywords.db_cache import TagAliasCache

    allowed = kw.load_allowed_tags_from_db()
    synonym_lookup = kw.load_synonyms_from_db()
    eff_map = kw.load_tag_effectiveness_map()

    if not allowed:
        return _get_normalize_prompt_tokens()(prompt)

    tokens = _get_split_prompt_tokens()(prompt)
    cleaned, seen = [], set()
    filtered_count, replaced_count = 0, 0

    for token in tokens:
        normalized = normalize_prompt_token(token)
        if not normalized or normalized in IGNORE_TOKENS or normalized in seen:
            continue

        # 1. Check for Aliases first (Always apply replacements if defined)
        replacement = TagAliasCache.get_replacement(normalized)
        if replacement is not ...:
            _get_logger().info(f"🔄 [Filter] Auto-replacing Alias: '{normalized}' -> '{replacement}'")
            # If replacement contains multiple tags (e.g. "tag, <lora:...>"), we need to re-process them?
            # normalize_prompt_token handles single token. If replacement is "a, b", it might need splitting?
            # But here we are appending to 'cleaned'. Ideally we append the replacement string directly.
            # But wait, 'cleaned' is joined by ", " at the end.

            # Simple replacement
            cleaned.append(replacement)
            replaced_count += 1
            seen.add(normalized) # Mark original as seen
            continue

        eff_data = eff_map.get(normalized)
        if eff_data:
            eff_score, use_count = eff_data
            if eff_score is not None and use_count >= TAG_MIN_USE_COUNT_FOR_FILTERING and eff_score < TAG_EFFECTIVENESS_THRESHOLD:
                # Low effectiveness tag -> Skip
                _get_logger().warning(f"⚠️  [Filter] Skipping low-effectiveness tag: '{normalized}' (score: {eff_score:.2f})")
                filtered_count += 1
                continue

        if normalized in allowed:
            if normalized not in seen:
                cleaned.append(normalized)
                seen.add(normalized)
        elif normalized in synonym_lookup:
            canonical = synonym_lookup[normalized]
            if canonical not in seen:
                cleaned.append(canonical)
                seen.add(canonical)
        else:
            filtered_count += 1

    if filtered_count > 0 or replaced_count > 0:
        _get_logger().info(f"✨ [Filter] Prompt refined: filtered {filtered_count} tags, replaced {replaced_count} tags")

    return ", ".join(cleaned)
