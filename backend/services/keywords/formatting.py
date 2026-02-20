from __future__ import annotations


def _load_processed_tags(
    filter_by_effectiveness: bool = True,
) -> tuple[dict[str, list[tuple[str, float, int]]], dict[str, list[str]]]:
    """Shared loader: returns (category_tags_with_scores, recommended_tags).

    Loads tags from DB once and applies effectiveness filtering.
    Used internally by both format_keyword_context and get_allowed_tags_by_category.
    """
    import services.keywords as kw
    from config import (
        RECOMMENDATION_EFFECTIVENESS_THRESHOLD,
        RECOMMENDATION_MIN_USE_COUNT,
        TAG_EFFECTIVENESS_THRESHOLD,
        TAG_MIN_USE_COUNT_FOR_FILTERING,
        get_wd14_identity_tags,
    )
    from services.keywords.db import _DB_GROUP_TO_GEMINI_CATEGORY, _SCENE_GROUPS

    from .core import normalize_prompt_token

    grouped = kw.load_tags_from_db()
    if not grouped:
        return {}, {}

    eff_map = kw.load_tag_effectiveness_map() if filter_by_effectiveness else {}

    category_tags: dict[str, list[tuple[str, float, int]]] = {}
    recommended_tags: dict[str, list[str]] = {}

    for group in _SCENE_GROUPS:
        if group not in grouped:
            continue
        category_name = _DB_GROUP_TO_GEMINI_CATEGORY.get(group, group)
        if category_name is None:
            continue

        values = grouped[group]
        if not values:
            continue

        filtered_values, category_recommended = [], []
        for tag in values:
            normalized = normalize_prompt_token(tag)
            eff_data = eff_map.get(normalized) if filter_by_effectiveness else None

            if eff_data is None:
                filtered_values.append((tag, 0.5, 0))
            else:
                eff_score, use_count = eff_data
                if eff_score is None or use_count < TAG_MIN_USE_COUNT_FOR_FILTERING:
                    filtered_values.append((tag, 0.5, use_count))
                elif eff_score < TAG_EFFECTIVENESS_THRESHOLD and normalized not in get_wd14_identity_tags():
                    continue
                else:
                    filtered_values.append((tag, eff_score, use_count))
                    if eff_score >= RECOMMENDATION_EFFECTIVENESS_THRESHOLD and use_count >= RECOMMENDATION_MIN_USE_COUNT:
                        category_recommended.append(tag)

        if category_name not in category_tags:
            category_tags[category_name] = []
        category_tags[category_name].extend(filtered_values)

        if category_recommended:
            if category_name not in recommended_tags:
                recommended_tags[category_name] = []
            recommended_tags[category_name].extend(category_recommended)

    # Sort tags within each category by effectiveness descending
    for category_name in category_tags:
        category_tags[category_name].sort(key=lambda x: (-x[1], x[0]))

    return category_tags, recommended_tags


def get_allowed_tags_by_category(filter_by_effectiveness: bool = True) -> dict[str, list[str]]:
    """Return allowed tags grouped by Gemini category name.

    Returns a dict like:
        {"camera": ["cowboy_shot", "close-up", ...], "expression": [...], ...}

    Useful for injecting category-specific tag lists into templates.
    """
    category_tags, _ = _load_processed_tags(filter_by_effectiveness)

    result: dict[str, list[str]] = {}
    for category_name, tag_tuples in category_tags.items():
        tags = [t[0] for t in tag_tuples[:100]]
        if tags:
            result[category_name] = tags

    return result


def get_keyword_context_and_tags(
    filter_by_effectiveness: bool = True,
) -> tuple[str, dict[str, list[str]]]:
    """Return both formatted keyword context string and category tag dict.

    Single DB load for both outputs. Use this when you need both values
    to avoid duplicate DB queries.
    """
    from config import logger
    from services.keywords.db import _DB_GROUP_TO_GEMINI_CATEGORY, _SCENE_GROUPS

    category_tags, recommended_tags = _load_processed_tags(filter_by_effectiveness)
    if not category_tags:
        logger.warning("No tags found in database")
        return "", {}

    # Build formatted string
    lines = []
    if recommended_tags:
        lines.append("Recommended High-Performance Tags (proven >80% effectiveness):")
        for category_name in _SCENE_GROUPS:
            gemini_category = _DB_GROUP_TO_GEMINI_CATEGORY.get(category_name, category_name)
            if gemini_category in recommended_tags:
                lines.append(f"- {gemini_category}: {', '.join(recommended_tags[gemini_category])}")
        lines.append("")

    lines.append("Allowed Keywords (use exactly as written):")
    for group in _SCENE_GROUPS:
        category_name = _DB_GROUP_TO_GEMINI_CATEGORY.get(group, group)
        if category_name in category_tags:
            values = [v[0] for v in category_tags[category_name]]
            if values:
                lines.append(f"- {category_name}: {', '.join(values[:100])}")

    keyword_context = "\n".join(lines)

    # Build category dict
    tags_by_category: dict[str, list[str]] = {}
    for cat_name, tag_tuples in category_tags.items():
        tags = [t[0] for t in tag_tuples[:100]]
        if tags:
            tags_by_category[cat_name] = tags

    return keyword_context, tags_by_category


def format_keyword_context(filter_by_effectiveness: bool = True) -> str:
    """Format keyword categories for use in Gemini prompts (DB-based)."""
    from config import logger
    from services.keywords.db import _DB_GROUP_TO_GEMINI_CATEGORY, _SCENE_GROUPS

    category_tags, recommended_tags = _load_processed_tags(filter_by_effectiveness)
    if not category_tags:
        logger.warning("No tags found in database")
        return ""

    lines = []
    if recommended_tags:
        lines.append("Recommended High-Performance Tags (proven >80% effectiveness):")
        for category_name in _SCENE_GROUPS:
            gemini_category = _DB_GROUP_TO_GEMINI_CATEGORY.get(category_name, category_name)
            if gemini_category in recommended_tags:
                lines.append(f"- {gemini_category}: {', '.join(recommended_tags[gemini_category])}")
        lines.append("")

    lines.append("Allowed Keywords (use exactly as written):")
    for group in _SCENE_GROUPS:
        category_name = _DB_GROUP_TO_GEMINI_CATEGORY.get(group, group)
        if category_name in category_tags:
            values = [v[0] for v in category_tags[category_name]]
            # Limit tags per category to prevent context overflow and "spam" detection (Prohibited Content)
            # 100 tags per category is usually enough for diversity
            if values:
                lines.append(f"- {category_name}: {', '.join(values[:100])}")

    return "\n".join(lines)
