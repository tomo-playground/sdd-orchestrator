def format_keyword_context(filter_by_effectiveness: bool = True) -> str:
    """Format keyword categories for use in Gemini prompts (DB-based)."""
    import services.keywords as kw
    from config import (
        RECOMMENDATION_EFFECTIVENESS_THRESHOLD,
        RECOMMENDATION_MIN_USE_COUNT,
        TAG_EFFECTIVENESS_THRESHOLD,
        TAG_MIN_USE_COUNT_FOR_FILTERING,
        logger,
    )
    from services.keywords.db import _DB_GROUP_TO_GEMINI_CATEGORY, _SCENE_GROUPS

    from .core import normalize_prompt_token

    grouped = kw.load_tags_from_db()
    if not grouped:
        logger.warning("No tags found in database")
        return ""

    eff_map = kw.load_tag_effectiveness_map() if filter_by_effectiveness else {}

    category_tags: dict[str, list[tuple[str, float, int]]] = {}
    recommended_tags: dict[str, list[str]] = {}

    for group in _SCENE_GROUPS:
        if group not in grouped: continue
        category_name = _DB_GROUP_TO_GEMINI_CATEGORY.get(group, group)
        if category_name is None: continue

        values = grouped[group]
        if not values: continue

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
                elif eff_score < TAG_EFFECTIVENESS_THRESHOLD:
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

    # Sort tags within each category
    for category_name in category_tags:
        category_tags[category_name].sort(key=lambda x: (-x[1], x[0]))

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
