from __future__ import annotations

from .core import (
    _get_logger,
    _get_normalize_prompt_tokens,
    _get_split_prompt_tokens,
    get_ignore_tokens,
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
        deprecated_tags = db.query(Tag).filter(Tag.is_active.is_(False), Tag.replacement_tag_id.isnot(None)).all()

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
                _get_logger().info(f"[TagReplacement] Deprecated tag '{normalized}' → '{replacement}'")
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
        if tag not in reverse_map:
            reverse_map[tag] = set()
        reverse_map[tag].add(syn)

    expanded: set[str] = set()
    for token in tokens:
        if not token:
            continue
        normalized = normalize_prompt_token(token)
        expanded.add(normalized)
        if normalized in reverse_map:
            expanded.update(reverse_map[normalized])
        if normalized in synonym_lookup:
            expanded.add(synonym_lookup[normalized])
    return expanded


def filter_prompt_tokens(prompt: str) -> str:
    """Filter prompt tokens to only include known/allowed keywords (DB-based)."""
    import services.keywords as kw
    from services.keywords.db_cache import TagAliasCache

    allowed = kw.load_allowed_tags_from_db()
    synonym_lookup = kw.load_synonyms_from_db()

    if not allowed:
        return _get_normalize_prompt_tokens()(prompt)

    tokens = _get_split_prompt_tokens()(prompt)

    # Replace deprecated tags with active replacements before filtering
    tokens, dep_replacements = replace_deprecated_tags(tokens)

    cleaned, seen = [], set()
    filtered_count, replaced_count = 0, len(dep_replacements)

    for token in tokens:
        normalized = normalize_prompt_token(token)
        if not normalized or normalized in get_ignore_tokens() or normalized in seen:
            continue

        # 1. Check for Aliases first (Always apply replacements if defined)
        replacement = TagAliasCache.get_replacement(normalized)
        if replacement is not ...:
            if not replacement:
                # Alias maps to empty/None → skip this token
                seen.add(normalized)
                continue
            _get_logger().info(f"🔄 [Filter] Auto-replacing Alias: '{normalized}' -> '{replacement}'")
            cleaned.append(replacement)
            replaced_count += 1
            seen.add(normalized)  # Mark original as seen
            continue

        # NOTE: Effectiveness-based filtering disabled (2026-02-24).
        # WD14 can only detect ~15% of tags reliably (clothing, subject, hair).
        # Using WD14 match data to remove tags caused a "death spiral" —
        # valid tags like blue_eyes, close-up, backlighting were deleted
        # because WD14 couldn't detect them, not because they were ineffective.
        # See: Phase 16 roadmap for WD14 Smart Validation redesign.

        if normalized in allowed:
            if normalized not in seen:
                cleaned.append(normalized)
                seen.add(normalized)
        elif normalized in synonym_lookup:
            canonical = synonym_lookup[normalized]
            if canonical and canonical not in seen:
                cleaned.append(canonical)
                seen.add(canonical)
        else:
            filtered_count += 1

    if filtered_count > 0 or replaced_count > 0:
        _get_logger().info(
            f"✨ [Filter] Prompt refined: filtered {filtered_count} tags, replaced {replaced_count} tags"
        )

    return ", ".join(cleaned)
