"""Finalize 노드 — 프롬프트 충돌 감지 및 자동 제거."""

from __future__ import annotations

from config import pipeline_logger as logger
from services.keywords.core import normalize_prompt_token


def resolve_prompt_conflicts(scenes: list[dict]) -> None:
    """씬별 프롬프트 충돌을 감지하고 자동 제거한다.

    1) Positive 내부 상호배타 태그 제거 (TagRuleCache 기반)
    2) Expression↔Mood valence 교차 충돌 제거
    3) Positive↔Negative 교차 태그 제거 (positive에서 제거)
    """
    _resolve_positive_internal_conflicts(scenes)
    _resolve_valence_conflicts(scenes)
    _resolve_positive_negative_conflicts(scenes)


def _resolve_positive_internal_conflicts(scenes: list[dict]) -> None:
    """TagRuleCache 기반: positive 내부 상호배타 태그 중 후자를 제거한다."""
    from services.keywords.db_cache import TagRuleCache

    if not TagRuleCache._initialized:
        from database import get_db_session

        with get_db_session() as db:
            TagRuleCache.initialize(db)

    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", "")
        if not prompt:
            continue

        tokens = [t.strip() for t in prompt.split(",") if t.strip()]
        seen: dict[str, str] = {}  # norm_key → original token
        result: list[str] = []
        removed: list[str] = []

        for token in tokens:
            norm = normalize_prompt_token(token)
            if not norm:  # LoRA, empty
                result.append(token)
                continue

            conflict_with = _find_conflict(norm, seen, TagRuleCache)
            if conflict_with:
                removed.append(f"{token}↔{conflict_with}")
            else:
                seen[norm] = token
                result.append(token)

        if removed:
            scene["image_prompt"] = ", ".join(result)
            logger.info("[Finalize] Scene %d: positive 내부 충돌 %d개 제거 — %s", i, len(removed), removed)


def _find_conflict(norm: str, seen: dict[str, str], cache) -> str | None:
    """seen에 있는 태그 중 norm과 충돌하는 것을 찾는다."""
    for existing_norm, existing_token in seen.items():
        if cache.is_conflicting(norm, existing_norm):
            return existing_token
    return None


# Group pairs that participate in valence cross-checking
_VALENCE_CROSS_PAIRS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset({"expression", "mood"}),
        frozenset({"gaze", "mood"}),
    }
)


def _is_cross_group_pair(group1: str | None, group2: str | None) -> bool:
    """Check if two groups form a valence cross-check pair."""
    if not group1 or not group2:
        return False
    return frozenset({group1, group2}) in _VALENCE_CROSS_PAIRS


def _resolve_valence_conflicts(scenes: list[dict]) -> None:
    """Expression/Gaze ↔ Mood valence 충돌을 감지하고 후자를 제거한다."""
    from services.keywords.db_cache import TagCategoryCache, TagValenceCache

    if not TagValenceCache._initialized or not TagCategoryCache._initialized:
        from database import get_db_session

        with get_db_session() as db:
            TagValenceCache.initialize(db)
            TagCategoryCache.initialize(db)

    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", "")
        if not prompt:
            continue

        tokens = [t.strip() for t in prompt.split(",") if t.strip()]
        # Track: (norm_key, original_token, group_name) for each accepted token
        accepted: list[tuple[str, str, str | None]] = []
        result: list[str] = []
        removed: list[str] = []

        for token in tokens:
            norm = normalize_prompt_token(token)
            if not norm:  # LoRA, empty
                result.append(token)
                continue

            group = TagCategoryCache.get_category(norm)
            has_valence_conflict = False

            for prev_norm, prev_token, prev_group in accepted:
                if _is_cross_group_pair(group, prev_group):
                    if TagValenceCache.is_valence_conflicting(norm, prev_norm):
                        has_valence_conflict = True
                        removed.append(f"{token}(valence↔{prev_token})")
                        break

            if not has_valence_conflict:
                accepted.append((norm, token, group))
                result.append(token)

        if removed:
            scene["image_prompt"] = ", ".join(result)
            logger.info("[Finalize] Scene %d: valence 충돌 %d개 제거 — %s", i, len(removed), removed)


def _resolve_positive_negative_conflicts(scenes: list[dict]) -> None:
    """positive와 negative에 동시 존재하는 태그를 positive에서 제거한다."""
    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", "")
        negative = scene.get("negative_prompt", "")
        if not prompt or not negative:
            continue

        neg_norms = {normalize_prompt_token(t.strip()) for t in negative.split(",") if t.strip()}
        neg_norms.discard("")  # LoRA 등 빈 결과 제거

        tokens = [t.strip() for t in prompt.split(",") if t.strip()]
        result: list[str] = []
        removed: list[str] = []

        for token in tokens:
            norm = normalize_prompt_token(token)
            if not norm:  # LoRA, empty
                result.append(token)
                continue
            if norm in neg_norms:
                removed.append(token)
            else:
                result.append(token)

        if removed:
            scene["image_prompt"] = ", ".join(result)
            logger.info("[Finalize] Scene %d: positive↔negative 충돌 %d개 제거 — %s", i, len(removed), removed)
