"""Cinematographer Agent용 도구 (Phase 10-B-3).

LLM이 태그 검증, 레퍼런스 검색, 호환성 체크 도구를 선택적으로 호출하여
비주얼 디자인 품질을 향상시킨다.
"""

from __future__ import annotations

from typing import Any

from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import logger

from .base import define_tool

# ── 도구 정의 ──────────────────────────────────────────────


def get_cinematographer_tools() -> list[types.Tool]:
    """Cinematographer Agent가 사용할 수 있는 도구 목록을 반환한다."""
    return [
        define_tool(
            name="validate_danbooru_tag",
            description="Danbooru에 존재하는 유효한 태그인지 검증합니다. WD14 Tagger CSV 데이터를 기반으로 검증합니다.",
            parameters={
                "tag": {
                    "type": "string",
                    "description": "검증할 태그 (언더바 형식, 예: 'brown_hair', 'looking_at_viewer')",
                },
            },
            required=["tag"],
        ),
        define_tool(
            name="search_similar_compositions",
            description="유사한 구도/분위기의 레퍼런스 이미지 태그 조합을 검색합니다. 과거 성공한 태그 조합을 찾아 재사용할 수 있습니다.",
            parameters={
                "mood": {
                    "type": "string",
                    "description": "씬의 분위기 (예: 'cheerful', 'melancholic', 'dramatic')",
                },
                "scene_type": {
                    "type": "string",
                    "description": "씬 타입 (예: 'portrait', 'landscape', 'action')",
                },
            },
            required=["mood", "scene_type"],
        ),
        define_tool(
            name="get_character_visual_tags",
            description="캐릭터의 비주얼 태그(identity, costume, LoRA)를 조회합니다. 캐릭터 일관성 유지에 필수적입니다.",
            parameters={
                "character_id": {
                    "type": "integer",
                    "description": "캐릭터 ID",
                },
            },
            required=["character_id"],
        ),
        define_tool(
            name="check_tag_compatibility",
            description="두 태그의 호환성을 검증합니다 (충돌 규칙 확인). tag_rules 테이블의 충돌 규칙을 검사합니다.",
            parameters={
                "tag_a": {
                    "type": "string",
                    "description": "첫 번째 태그",
                },
                "tag_b": {
                    "type": "string",
                    "description": "두 번째 태그",
                },
            },
            required=["tag_a", "tag_b"],
        ),
    ]


# ── 도구 실행 함수 ─────────────────────────────────────────


def create_cinematographer_executors(
    db: AsyncSession,
    state: dict[str, Any],
) -> dict[str, Any]:
    """Cinematographer Agent용 도구 실행 함수 맵을 생성한다.

    Args:
        db: DB 세션
        state: 현재 ScriptState

    Returns:
        도구 이름 → 실행 함수 매핑
    """

    async def validate_danbooru_tag(tag: str) -> str:
        """Danbooru 태그 유효성 검증.

        WD14 Tagger CSV 데이터(tags 테이블)를 기반으로 검증한다.
        """
        try:
            from models import Tag

            # 언더바 형식으로 정규화
            normalized_tag = tag.strip().lower().replace(" ", "_")

            stmt = select(Tag).where(Tag.name == normalized_tag)
            result = await db.execute(stmt) if isinstance(db, AsyncSession) else db.execute(stmt)
            tag_obj = result.scalar_one_or_none()

            if tag_obj:
                logger.info("[CinematographerTool] 태그 검증 성공: %s (category=%s)", tag, tag_obj.category)
                return f"✓ '{tag}'는 유효한 Danbooru 태그입니다 (카테고리: {tag_obj.category})"
            else:
                logger.warning("[CinematographerTool] 태그 검증 실패: %s (Danbooru에 없음)", tag)
                return f"✗ '{tag}'는 Danbooru에 존재하지 않는 태그입니다. 유사한 유효 태그로 교체하세요."

        except Exception as e:
            logger.error("[CinematographerTool] 태그 검증 에러: %s", e)
            return f"⚠ 태그 검증 중 에러 발생: {e}"

    async def search_similar_compositions(mood: str, scene_type: str) -> str:
        """유사한 구도/분위기의 레퍼런스 태그 조합 검색.

        tag_effectiveness 테이블에서 높은 effectiveness를 가진 태그를 우선 검색하고,
        결과가 없으면 정적 데이터로 fallback한다.
        """
        logger.info("[CinematographerTool] 유사 구도 검색: mood=%s, scene_type=%s", mood, scene_type)

        # DB 기반 추천 시도
        try:
            from models.tag import TagEffectiveness

            stmt = (
                select(TagEffectiveness)
                .where(TagEffectiveness.effectiveness >= 0.7)
                .order_by(TagEffectiveness.effectiveness.desc())
                .limit(5)
            )
            result = await db.execute(stmt) if isinstance(db, AsyncSession) else db.execute(stmt)
            rows = result.scalars().all()
            if rows:
                tag_items = []
                for row in rows:
                    tag_name = row.tag.name if row.tag else "unknown"
                    tag_items.append(f"{tag_name}({row.effectiveness:.0%})")
                db_result = ", ".join(tag_items)
                logger.info("[CinematographerTool] DB 기반 추천: %d개 태그", len(rows))
                return f"[DB 기반 고효율 태그] {db_result}"
        except Exception as e:
            logger.warning("[CinematographerTool] DB 조회 실패, fallback 사용: %s", e)

        # Fallback: mood × scene_type 정적 매트릭스 (모든 태그 Danbooru 검증 완료)
        _COMPOSITION_MATRIX: dict[tuple[str, str], str] = {
            ("cheerful", "portrait"): "close-up, looking_at_viewer, smile, sunlight, depth_of_field",
            ("cheerful", "landscape"): "wide_shot, bright, outdoors, light_rays, scenery",
            ("melancholic", "portrait"): "looking_down, moonlight, from_above, depth_of_field, shadow",
            ("melancholic", "landscape"): "wide_shot, rain, dark, scenery, no_humans",
            ("dramatic", "portrait"): "from_below, backlighting, dutch_angle, shadow, high_contrast",
            ("dramatic", "action"): "dutch_angle, motion_blur, backlighting, from_side",
            ("tense", "portrait"): "close-up, clenched_teeth, shadow, dark, sweat",
            ("tense", "action"): "dutch_angle, from_behind, dark, motion_blur, silhouette",
            ("peaceful", "portrait"): "sunlight, closed_eyes, bokeh, golden_hour, head_tilt",
            ("peaceful", "landscape"): "wide_shot, golden_hour, scenery, dappled_sunlight, light_rays",
            ("hopeful", "portrait"): "from_below, looking_up, backlighting, bright, light_rays",
            ("lonely", "portrait"): "wide_shot, from_behind, depth_of_field, silhouette, dusk",
            ("romantic", "portrait"): "close-up, sunlight, bokeh, blush, sidelighting",
            ("angry", "portrait"): "close-up, from_below, shadow, clenched_teeth, high_contrast",
            ("nostalgic", "portrait"): "golden_hour, looking_afar, bokeh, dusk, depth_of_field",
            ("curious", "portrait"): "dutch_angle, looking_to_the_side, from_side, lens_flare",
        }

        # 정확한 (mood, scene_type) 매칭 → mood만 매칭 → 기본값
        mood_lower = mood.lower().strip()
        scene_lower = scene_type.lower().strip()

        exact = _COMPOSITION_MATRIX.get((mood_lower, scene_lower))
        if exact:
            return f"[레퍼런스 태그 조합] {exact}"

        # Fuzzy: mood만으로 검색
        mood_matches = [v for k, v in _COMPOSITION_MATRIX.items() if k[0] == mood_lower]
        if mood_matches:
            return f"[레퍼런스 태그 조합 (mood={mood})] {mood_matches[0]}"

        return "[레퍼런스 태그 조합] depth_of_field, backlighting, cowboy_shot"

    async def get_character_visual_tags(character_id: int) -> str:
        """캐릭터의 비주얼 태그 조회."""
        try:
            from models.character import Character

            stmt = select(Character).where(Character.id == character_id)
            result = await db.execute(stmt) if isinstance(db, AsyncSession) else db.execute(stmt)
            char = result.scalar_one_or_none()

            if not char:
                logger.warning("[CinematographerTool] 캐릭터 없음: character_id=%d", character_id)
                return f"✗ character_id={character_id}를 찾을 수 없습니다"

            # 캐릭터 태그 로드
            tags = [ct.tag.name for ct in char.tags if ct.tag]
            if not tags:
                logger.info("[CinematographerTool] 캐릭터 태그 없음: character_id=%d", character_id)
                return f"캐릭터 '{char.name}'에 설정된 비주얼 태그가 없습니다"

            logger.info("[CinematographerTool] 캐릭터 태그 조회 완료: %d개", len(tags))
            return f"[캐릭터 '{char.name}' 비주얼 태그] {', '.join(tags[:20])}"

        except Exception as e:
            logger.error("[CinematographerTool] 캐릭터 태그 조회 실패: %s", e)
            return f"⚠ 캐릭터 태그 조회 중 에러 발생: {e}"

    async def check_tag_compatibility(tag_a: str, tag_b: str) -> str:
        """태그 호환성 검증 (충돌 규칙 확인)."""
        try:
            from models import Tag, TagRule

            # 태그 이름 → ID 변환
            stmt_a = select(Tag.id).where(Tag.name == tag_a.strip().lower().replace(" ", "_"))
            result_a = await db.execute(stmt_a) if isinstance(db, AsyncSession) else db.execute(stmt_a)
            tag_a_id = result_a.scalar_one_or_none()

            stmt_b = select(Tag.id).where(Tag.name == tag_b.strip().lower().replace(" ", "_"))
            result_b = await db.execute(stmt_b) if isinstance(db, AsyncSession) else db.execute(stmt_b)
            tag_b_id = result_b.scalar_one_or_none()

            if not tag_a_id or not tag_b_id:
                missing = []
                if not tag_a_id:
                    missing.append(tag_a)
                if not tag_b_id:
                    missing.append(tag_b)
                return f"⚠ 태그를 찾을 수 없음: {', '.join(missing)}"

            # 양방향 충돌 검사
            stmt = select(TagRule).where(
                TagRule.rule_type == "conflict",
                TagRule.is_active.is_(True),
                (
                    ((TagRule.source_tag_id == tag_a_id) & (TagRule.target_tag_id == tag_b_id))
                    | ((TagRule.source_tag_id == tag_b_id) & (TagRule.target_tag_id == tag_a_id))
                ),
            )
            result = await db.execute(stmt) if isinstance(db, AsyncSession) else db.execute(stmt)
            rule = result.scalar_one_or_none()

            if rule:
                logger.warning(
                    "[CinematographerTool] 태그 충돌 감지: %s ↔ %s (%s)",
                    tag_a,
                    tag_b,
                    rule.message,
                )
                return f"✗ '{tag_a}'와 '{tag_b}'는 충돌합니다. 이유: {rule.message or '알 수 없음'}"

            logger.info("[CinematographerTool] 태그 호환성 OK: %s ↔ %s", tag_a, tag_b)
            return f"✓ '{tag_a}'와 '{tag_b}'는 호환됩니다"

        except Exception as e:
            logger.error("[CinematographerTool] 호환성 검증 에러: %s", e)
            return f"⚠ 호환성 검증 중 에러 발생: {e}"

    return {
        "validate_danbooru_tag": validate_danbooru_tag,
        "search_similar_compositions": search_similar_compositions,
        "get_character_visual_tags": get_character_visual_tags,
        "check_tag_compatibility": check_tag_compatibility,
    }
