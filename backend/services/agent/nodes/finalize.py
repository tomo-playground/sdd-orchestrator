"""Finalize 노드 — Quick은 패스스루, Full은 Production 결과를 병합한다."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from config import (
    DEFAULT_GAZE_TAG,
    DEFAULT_MOOD_TAG,
    DEFAULT_POSE_TAG,
    DEFAULT_SCENE_NEGATIVE_PROMPT,
    DURATION_DEFICIT_THRESHOLD,
    DURATION_OVERFLOW_THRESHOLD,
    logger,
)
from database import get_db_session
from services.agent.state import ScriptState

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig


_QUALITY_TAG_FIXES = {"high_quality": "best_quality"}


def _sanitize_quality_tags(scenes: list[dict]) -> None:
    """비표준 quality 태그를 Danbooru 표준으로 치환한다 (e.g. high_quality → best_quality)."""
    for scene in scenes:
        prompt = scene.get("image_prompt", "")
        if not prompt:
            continue
        tokens = [t.strip() for t in prompt.split(",")]
        scene["image_prompt"] = ", ".join(_QUALITY_TAG_FIXES[t] if t in _QUALITY_TAG_FIXES else t for t in tokens)


def _apply_tag_aliases(scenes: list[dict]) -> None:
    """DB tag_aliases 기반 자동 교정 — 비표준/모호 태그를 Danbooru 표준으로 치환/제거."""
    from services.keywords.db_cache import TagAliasCache

    # TagAliasCache는 startup 시 초기화됨. 미초기화 시에만 DB 세션 열기.
    if not TagAliasCache._initialized:
        with get_db_session() as db:
            TagAliasCache.initialize(db)

    replaced_count = 0
    removed_count = 0
    split_count = 0
    for scene in scenes:
        prompt = scene.get("image_prompt", "")
        if not prompt:
            continue
        tokens = [t.strip() for t in prompt.split(",")]
        result = []
        for t in tokens:
            if not t:
                continue
            replacement = TagAliasCache.get_replacement(t)
            if replacement is ...:
                result.append(t)
            elif replacement is None:
                removed_count += 1
            else:
                parts = [p.strip() for p in replacement.split(",") if p.strip()]
                result.extend(parts)
                replaced_count += 1
                if len(parts) > 1:
                    split_count += 1
        scene["image_prompt"] = ", ".join(result)

    if replaced_count or removed_count:
        logger.info(
            "[Finalize] TagAlias: %d replaced (%d split), %d removed",
            replaced_count,
            split_count,
            removed_count,
        )


def _inject_negative_prompts(scenes: list[dict]) -> None:
    """빈 negative_prompt에 기본값을 주입하고, LLM의 negative_prompt_extra를 병합한다."""
    for scene in scenes:
        base = (scene.get("negative_prompt") or "").strip()
        if not base:
            base = DEFAULT_SCENE_NEGATIVE_PROMPT
        extra = scene.get("negative_prompt_extra")
        if extra:
            base = f"{base}, {extra}"
        scene["negative_prompt"] = base


def _merge_production_results(state: ScriptState) -> tuple[list[dict], dict | None, dict | None]:
    """cinematographer_result.scenes에 tts 결과를 병합하고, sound/copyright를 별도 반환."""
    import copy  # noqa: PLC0415

    cinema = state.get("cinematographer_result") or {}
    scenes = [copy.deepcopy(s) for s in cinema.get("scenes", [])]

    tts_designs = (state.get("tts_designer_result") or {}).get("tts_designs", [])
    sound_rec = (state.get("sound_designer_result") or {}).get("recommendation")
    copyright_result = state.get("copyright_reviewer_result")

    # TTS 디자인을 씬별로 병합
    for i, scene in enumerate(scenes):
        if i < len(tts_designs):
            scene["tts_design"] = tts_designs[i]

    logger.info("[LangGraph] Finalize (Full): %d scenes 병합 완료", len(scenes))
    return scenes, sound_rec, copyright_result


def _inject_default_context_tags(scenes: list[dict]) -> None:
    """캐릭터 씬의 context_tags에 pose/gaze/expression/mood 기본값을 주입한다.

    expression은 항상 emotion에서 파생을 시도한다 (Cinematographer가 단일 expression으로
    모든 씬을 채우는 monotony 문제 방지). 파생 실패 시에만 기존값 또는 기본값 사용.
    mood는 빈 경우 emotion에서 자동 생성한다.
    Narrator 씬(배경샷)은 캐릭터가 없으므로 건너뛴다.
    """
    from config import DEFAULT_EXPRESSION_TAG  # noqa: PLC0415

    from ._context_tag_utils import derive_expression_from_emotion, derive_mood_from_emotion

    for scene in scenes:
        speaker = scene.get("speaker", "")
        if speaker == "Narrator":
            continue

        ctx = scene.get("context_tags")
        if ctx is None:
            scene["context_tags"] = {
                "pose": DEFAULT_POSE_TAG,
                "gaze": DEFAULT_GAZE_TAG,
                "expression": DEFAULT_EXPRESSION_TAG,
            }
            continue

        if ctx.get("pose") is None:
            ctx["pose"] = DEFAULT_POSE_TAG
        if ctx.get("gaze") is None:
            ctx["gaze"] = DEFAULT_GAZE_TAG

        # expression: emotion에서 항상 파생 시도 (monotony 방지)
        emotion = ctx.get("emotion")
        derived_expr = derive_expression_from_emotion(emotion) if emotion else None
        if derived_expr:
            ctx["expression"] = derived_expr
        elif ctx.get("expression") is None:
            ctx["expression"] = DEFAULT_EXPRESSION_TAG

        # mood: emotion에서 자동 생성, 파생 실패 시 기본값 (빈 mood 방지)
        if ctx.get("mood") is None:
            derived_mood = derive_mood_from_emotion(emotion) if emotion else None
            ctx["mood"] = derived_mood or DEFAULT_MOOD_TAG


def _inject_writer_plan_emotions(scenes: list[dict], writer_plan: dict | None) -> None:
    """writer_plan.emotional_arc에서 빈 context_tags.emotion을 채운다."""
    if not writer_plan:
        return
    arc = writer_plan.get("emotional_arc", [])
    if not arc:
        return
    for i, scene in enumerate(scenes):
        if i >= len(arc):
            break
        ctx = scene.get("context_tags")
        if ctx is None:
            scene["context_tags"] = {"emotion": arc[i]}
        elif not ctx.get("emotion"):
            ctx["emotion"] = arc[i]


def _normalize_environment_tags(scenes: list[dict]) -> None:
    """context_tags.setting → context_tags.environment 정규화."""
    for scene in scenes:
        ctx = scene.get("context_tags")
        if not ctx:
            continue
        if "setting" in ctx and "environment" not in ctx:
            ctx["environment"] = ctx.pop("setting")


def _copy_scene_level_to_context_tags(scenes: list[dict]) -> None:
    """Cinematographer가 scene-level에 출력한 camera/environment를 context_tags로 복사한다."""
    for scene in scenes:
        ctx = scene.get("context_tags")
        if ctx is None:
            scene["context_tags"] = {}
            ctx = scene["context_tags"]

        # camera: scene["camera"] → context_tags["camera"]
        if ctx.get("camera") is None and scene.get("camera"):
            ctx["camera"] = scene["camera"]


def _build_scene_to_tags_map(writer_plan: dict) -> dict[int, list[str]]:
    """writer_plan.locations에서 scene_idx → tags 매핑을 구축한다."""
    from services.agent.state import get_loc_field

    idx_to_tags: dict[int, list[str]] = {}
    for loc in writer_plan.get("locations", []):
        for idx in get_loc_field(loc, "scenes", []):  # type: ignore[union-attr]
            idx_to_tags[idx] = get_loc_field(loc, "tags", [])  # type: ignore[assignment]
    return idx_to_tags


def _inject_location_map_tags(scenes: list[dict], writer_plan: dict | None) -> None:
    """writer_plan.locations 기반으로 각 씬의 context_tags.environment를 교정한다.

    Location Map이 환경 태그의 SSOT. LLM이 생성한 environment 태그 중
    Location Map에 속하지 않는 태그는 할루시네이션으로 간주하여 제거한다.
    """
    from config_prompt import GENERIC_LOCATION_TAGS  # noqa: PLC0415

    if not writer_plan or not writer_plan.get("locations"):
        return

    def _norm(tag: str) -> str:
        return tag.lower().replace(" ", "_").strip()

    idx_to_tags = _build_scene_to_tags_map(writer_plan)

    # Location Map의 모든 유효 환경 태그 수집 (할루시네이션 필터용)
    from services.agent.state import get_loc_field

    all_valid_env: set[str] = set()
    for loc in writer_plan.get("locations", []):
        for t in get_loc_field(loc, "tags", []):  # type: ignore[union-attr]
            all_valid_env.add(_norm(t))
    all_valid_env |= GENERIC_LOCATION_TAGS  # indoors/outdoors 등 generic은 항상 허용

    for i, scene in enumerate(scenes):
        loc_tags = idx_to_tags.get(i)
        if not loc_tags and idx_to_tags:
            # Revise로 씬 수가 변경된 경우: 범위 초과 씬은 마지막 위치 태그 상속
            max_planned_idx = max(idx_to_tags.keys())
            if i > max_planned_idx:
                loc_tags = idx_to_tags.get(max_planned_idx)
        if not loc_tags:
            continue

        ctx = scene.get("context_tags")
        if ctx is None:
            scene["context_tags"] = {"environment": list(loc_tags)}
            continue

        env = ctx.get("environment")
        if env is None:
            env = []
        elif isinstance(env, str):
            env = [env]
        else:
            env = list(env)

        loc_norms = {_norm(t) for t in loc_tags}

        # LLM이 생성한 environment 중 Location Map에 없는 태그 제거 (할루시네이션 방지)
        dropped = [t for t in env if _norm(t) not in all_valid_env]
        if dropped:
            logger.info(
                "[Finalize] Scene %d: 환경 태그 교정 — dropped %s (Location Map에 없음)",
                i,
                dropped,
            )

        kept = [t for t in env if _norm(t) in loc_norms]

        # kept도 specific/generic 분리 (구체 태그 우선 원칙 일관 적용)
        kept_norms = {_norm(k) for k in kept}
        kept_specific = [t for t in kept if _norm(t) not in GENERIC_LOCATION_TAGS]
        kept_generic = [t for t in kept if _norm(t) in GENERIC_LOCATION_TAGS]

        # Location Map 태그 중 아직 없는 것 추가 (구체 → generic 순)
        new_specific = [t for t in loc_tags if _norm(t) not in kept_norms and _norm(t) not in GENERIC_LOCATION_TAGS]
        new_generic = [t for t in loc_tags if _norm(t) not in kept_norms and _norm(t) in GENERIC_LOCATION_TAGS]

        ctx["environment"] = kept_specific + new_specific + kept_generic + new_generic

        # image_prompt에서도 할루시네이션 환경 태그 제거
        if dropped:
            dropped_norms = {_norm(t) for t in dropped}
            prompt = scene.get("image_prompt", "")
            if prompt:
                tokens = [t.strip() for t in prompt.split(",")]
                cleaned = [t for t in tokens if _norm(t) not in dropped_norms]
                if len(cleaned) < len(tokens):
                    scene["image_prompt"] = ", ".join(cleaned)
                    logger.info(
                        "[Finalize] Scene %d: image_prompt에서 환경 태그 %d개 제거",
                        i,
                        len(tokens) - len(cleaned),
                    )


def _inject_location_negative_tags(scenes: list[dict], writer_plan: dict | None) -> None:
    """Location Map 기반으로 indoor/outdoor 씬의 negative_prompt에 반대 태그를 추가한다.

    indoor 장소 씬 → negative에 'outdoors', outdoor 장소 씬 → negative에 'indoors'.
    _inject_negative_prompts() 이후 실행되므로 negative_prompt에 직접 append한다.
    """
    from config_prompt import INDOOR_LOCATION_TAGS, OUTDOOR_LOCATION_TAGS  # noqa: PLC0415

    if not writer_plan or not writer_plan.get("locations"):
        return

    idx_to_tags = _build_scene_to_tags_map(writer_plan)

    for i, scene in enumerate(scenes):
        loc_tags = idx_to_tags.get(i)
        if not loc_tags:
            continue

        tag_norms = {t.lower().replace(" ", "_").strip() for t in loc_tags}
        is_indoor = bool(tag_norms & INDOOR_LOCATION_TAGS)
        is_outdoor = bool(tag_norms & OUTDOOR_LOCATION_TAGS)

        if is_indoor and not is_outdoor:
            neg_tag = "outdoors"
        elif is_outdoor and not is_indoor:
            neg_tag = "indoors"
        else:
            continue

        existing_neg = scene.get("negative_prompt") or ""
        existing_norms = {t.strip().lower() for t in existing_neg.split(",") if t.strip()}
        if neg_tag not in existing_norms:
            scene["negative_prompt"] = f"{existing_neg}, {neg_tag}" if existing_neg else neg_tag


def _collect_cinematic_palette(scenes: list[dict], indices: list[int]) -> set[str]:
    """처음 2개 씬에서 cinematic 태그 팔레트를 수집한다."""
    palette: set[str] = set()
    for idx in indices[:2]:
        ctx = scenes[idx].get("context_tags") or {}
        palette.update(ctx.get("cinematic") or [])
    return palette


def _pick_anchor(scenes: list[dict], indices: list[int], palette: set[str]) -> str:
    """팔레트에서 출현 빈도가 가장 높은 태그를 anchor로 선택한다."""
    counter: Counter[str] = Counter()
    for idx in indices[:2]:
        ctx = scenes[idx].get("context_tags") or {}
        for tag in ctx.get("cinematic") or []:
            if tag in palette:
                counter[tag] += 1
    # 빈도 내림차순, 동점 시 알파벳 순
    return min(palette, key=lambda t: (-counter[t], t))


def _stabilize_location_cinematic(scenes: list[dict], writer_plan: dict | None) -> None:
    """같은 location 그룹 내 cinematic 태그를 안정화한다.

    Location 그룹의 처음 2개 씬 cinematic을 기준 팔레트로 삼고
    나머지 씬(마지막 씬 제외)은 팔레트 태그 최소 1개 포함을 보장한다.
    """
    if not writer_plan or not writer_plan.get("locations"):
        return

    locations = writer_plan["locations"]
    loc_groups: dict[str, list[int]] = {
        loc["name"]: loc["scenes"] for loc in locations if loc.get("name") and loc.get("scenes")
    }

    for loc_name, scene_indices in loc_groups.items():
        valid = [i for i in scene_indices if i < len(scenes)]
        if len(valid) < 3:
            continue

        palette_tags = _collect_cinematic_palette(scenes, valid)
        if not palette_tags:
            continue

        anchor = _pick_anchor(scenes, valid, palette_tags)

        stable_count = 0
        for idx in valid[:-1]:
            ctx = scenes[idx].get("context_tags")
            if ctx is None:
                scenes[idx]["context_tags"] = {}
                ctx = scenes[idx]["context_tags"]
            cinematic = ctx.get("cinematic") or []
            if not any(c in palette_tags for c in cinematic):
                ctx["cinematic"] = [anchor] + [c for c in cinematic if c != anchor][:1]
                stable_count += 1

        if stable_count:
            logger.info(
                "[Finalize] Location '%s': cinematic 안정화 %d씬 (팔레트=%s)",
                loc_name,
                stable_count,
                sorted(palette_tags),
            )


def _load_char_exclusive_tags(character_id: int, db) -> dict[str, set[str]]:
    """캐릭터의 EXCLUSIVE 그룹 태그를 {group_name: {tag_names}} 형태로 반환."""
    from sqlalchemy.orm import joinedload  # noqa: PLC0415

    from config_prompt import EXCLUSIVE_TAG_GROUPS  # noqa: PLC0415
    from models.associations import CharacterTag  # noqa: PLC0415
    from models.character import Character  # noqa: PLC0415

    char = (
        db.query(Character)
        .options(joinedload(Character.tags).joinedload(CharacterTag.tag))
        .filter(Character.id == character_id)
        .first()
    )
    if not char:
        return {}

    result: dict[str, set[str]] = {}
    for char_tag in char.tags:
        tag = char_tag.tag
        if tag.group_name in EXCLUSIVE_TAG_GROUPS:
            result.setdefault(tag.group_name, set()).add(tag.name.lower().replace(" ", "_").strip())
    return result


def _strip_token_weight(token: str) -> str:
    """SD 가중치 구문 제거: (tag:1.15) → tag, bare → bare."""
    norm = token.lower().replace(" ", "_").strip()
    if norm.startswith("(") and ":" in norm:
        return norm[1:].split(":")[0]
    return norm


def _filter_exclusive_identity_tags(
    scenes: list[dict],
    character_id: int | None,
    character_b_id: int | None,
    db,
) -> None:
    """image_prompt에서 캐릭터 DB 태그와 충돌하는 EXCLUSIVE 그룹 태그를 제거.

    Cinematographer가 캐릭터의 identity를 모호하게 출력한 경우
    (예: DB=black_hair인데 dark_hair 출력) 해당 태그를 제거하여
    V3 compose가 DB 태그만 사용하도록 보장한다.
    """
    if not character_id:
        return

    char_a_exclusive = _load_char_exclusive_tags(character_id, db)
    char_b_exclusive = _load_char_exclusive_tags(character_b_id, db) if character_b_id else {}

    if not char_a_exclusive and not char_b_exclusive:
        return

    from models.tag import Tag  # noqa: PLC0415

    # 전체 씬에서 bare 토큰을 수집 → IN 쿼리 1회로 그룹 정보 일괄 조회
    all_bare: set[str] = set()
    for scene in scenes:
        if scene.get("speaker") == "Narrator":
            continue
        for t in (scene.get("image_prompt") or "").split(","):
            bare = _strip_token_weight(t.strip())
            if bare:
                all_bare.add(bare)

    if not all_bare:
        return

    tag_rows = db.query(Tag.name, Tag.group_name).filter(Tag.name.in_(all_bare)).all()
    tag_group_map: dict[str, str | None] = {row.name: row.group_name for row in tag_rows}

    # alias 해소: DB에서 직접 못 찾은 토큰을 TagAliasCache로 표준 태그 일괄 조회 (N+1 방지)
    unresolved = all_bare - set(tag_group_map.keys())
    if unresolved:
        from services.keywords.db_cache import TagAliasCache  # noqa: PLC0415

        alias_map: dict[str, str] = {}
        for token in unresolved:
            replacement = TagAliasCache.get_replacement(token)
            if replacement is ... or replacement is None:
                continue
            alias_map[token] = replacement.split(",")[0].strip()

        if alias_map:
            std_names = set(alias_map.values())
            std_rows = db.query(Tag.name, Tag.group_name).filter(Tag.name.in_(std_names)).all()
            std_group_map = {r.name: r.group_name for r in std_rows}
            for token, std_name in alias_map.items():
                if std_name in std_group_map:
                    tag_group_map[token] = std_group_map[std_name]

    removed_total = 0
    for scene in scenes:
        speaker = scene.get("speaker", "")
        if speaker == "Narrator":
            continue
        prompt = scene.get("image_prompt", "")
        if not prompt:
            continue

        exclusive = char_b_exclusive if speaker == "B" else char_a_exclusive
        if not exclusive:
            continue

        tokens = [t.strip() for t in prompt.split(",")]
        filtered = []
        for token in tokens:
            if not token:
                continue
            bare = _strip_token_weight(token)
            group = tag_group_map.get(bare)
            if group and group in exclusive and bare not in exclusive[group]:
                removed_total += 1
                continue
            filtered.append(token)
        scene["image_prompt"] = ", ".join(filtered)

    if removed_total:
        logger.info("[Finalize] EXCLUSIVE identity 태그 %d개 제거 (캐릭터 DB 태그 우선)", removed_total)


_CLOTHING_GROUPS = frozenset({"clothing", "clothing_top", "clothing_bottom", "clothing_outfit", "clothing_detail"})
_ACCESSORY_GROUPS = frozenset({"accessory", "hair_accessory", "legwear", "footwear"})
_IDENTITY_GROUPS = frozenset(
    {"hair_color", "hair_length", "hair_style", "eye_color", "skin_color", "body_feature", "body_type"}
)
# context_tags 표준 필드 — 하나라도 있으면 image_prompt 재조립 대상
_CONTEXT_TAG_FIELDS = frozenset({"camera", "pose", "gaze", "action", "expression", "environment", "cinematic", "props"})


def _load_tags_by_groups(cid: int, groups: frozenset[str], db) -> set[str]:
    """캐릭터 태그 중 지정 그룹에 속하는 태그 이름 집합을 반환."""
    from sqlalchemy.orm import joinedload  # noqa: PLC0415

    from models.associations import CharacterTag  # noqa: PLC0415
    from models.character import Character  # noqa: PLC0415

    char = (
        db.query(Character)
        .options(joinedload(Character.tags).joinedload(CharacterTag.tag))
        .filter(Character.id == cid, Character.deleted_at.is_(None))
        .first()
    )
    if not char:
        return set()
    return {ct.tag.name.lower().replace(" ", "_").strip() for ct in char.tags if ct.tag and ct.tag.group_name in groups}


def _enforce_character_clothing(
    scenes: list[dict],
    character_id: int | None,
    character_b_id: int | None,
    db,
) -> None:
    """캐릭터 DB의 clothing/accessory/identity 태그로 image_prompt를 교정.

    1단계: Gemini가 추가한 비-DB 복장/액세서리 태그를 제거
    2단계: DB 복장 태그가 누락되었으면 보강
    3단계: Gemini가 추가한 비-DB identity 태그(헤어/눈색/체형 등)를 제거
           (identity 태그는 V3 compose에서 DB 기준으로 주입되므로 보강 불필요)
    clothing_override가 있는 씬은 건너뛴다 (의도적 변경).
    """
    if not character_id:
        return

    from models.tag import Tag  # noqa: PLC0415

    clothing_and_accessory = _CLOTHING_GROUPS | _ACCESSORY_GROUPS
    char_a_clothing = _load_tags_by_groups(character_id, clothing_and_accessory, db)
    char_b_clothing = _load_tags_by_groups(character_b_id, clothing_and_accessory, db) if character_b_id else set()
    char_a_identity = _load_tags_by_groups(character_id, _IDENTITY_GROUPS, db)
    char_b_identity = _load_tags_by_groups(character_b_id, _IDENTITY_GROUPS, db) if character_b_id else set()

    if not char_a_clothing and not char_b_clothing and not char_a_identity and not char_b_identity:
        return

    # 전체 씬의 토큰을 수집하여 DB tag 테이블에서 group_name 일괄 조회 (N+1 방지)
    all_tokens: set[str] = set()
    for scene in scenes:
        if scene.get("speaker") == "Narrator":
            continue
        for t in (scene.get("image_prompt") or "").split(","):
            bare = _strip_token_weight(t.strip())
            if bare:
                all_tokens.add(bare)

    if not all_tokens:
        return

    tag_rows = db.query(Tag.name, Tag.group_name).filter(Tag.name.in_(all_tokens)).all()
    tag_group_map: dict[str, str | None] = {row.name: row.group_name for row in tag_rows}

    removed_total = 0
    injected_total = 0
    identity_removed_total = 0

    for scene in scenes:
        speaker = scene.get("speaker", "")
        if speaker == "Narrator":
            continue
        if scene.get("clothing_override"):
            continue

        clothing_tags = char_b_clothing if speaker == "B" else char_a_clothing
        identity_tags = char_b_identity if speaker == "B" else char_a_identity

        prompt = scene.get("image_prompt", "")
        tokens = [t.strip() for t in prompt.split(",")]

        # 1단계: 비-DB 복장 태그 제거
        filtered: list[str] = []
        for token in tokens:
            if not token:
                continue
            bare = _strip_token_weight(token)
            group = tag_group_map.get(bare)
            if clothing_tags and group and group in clothing_and_accessory and bare not in clothing_tags:
                removed_total += 1
                continue
            filtered.append(token)

        # 2단계: DB 복장 태그 누락 보강
        if clothing_tags:
            filtered_set = {_strip_token_weight(t.strip()).lower().replace(" ", "_") for t in filtered}
            missing = [t for t in clothing_tags if t not in filtered_set]
            if missing:
                filtered.extend(missing)
                injected_total += len(missing)

        # 3단계: 비-DB identity 태그 제거 (헤어/눈색/체형 등 — V3 compose가 DB 기준으로 주입)
        if identity_tags:
            identity_filtered: list[str] = []
            for token in filtered:
                if not token:
                    continue
                bare = _strip_token_weight(token)
                group = tag_group_map.get(bare)
                if group and group in _IDENTITY_GROUPS and bare not in identity_tags:
                    identity_removed_total += 1
                    continue
                identity_filtered.append(token)
            filtered = identity_filtered

        scene["image_prompt"] = ", ".join(filtered)

    if removed_total:
        logger.info("[Finalize] 비-DB 복장 태그 %d개 제거 (Gemini 자의적 추가분)", removed_total)
    if injected_total:
        logger.info("[Finalize] DB 복장 태그 %d개 보강 (누락분)", injected_total)
    if identity_removed_total:
        logger.info(
            "[Finalize] 비-DB identity 태그 %d개 제거 (헤어/눈색/체형 — DB 기준 자동 주입)", identity_removed_total
        )


# ── context_tags 구조화: cross-field 검증 + image_prompt 재조립 ──────

_CAMERA_GAZE_CONFLICTS: dict[str, dict[str, str]] = {
    "from_behind": {"looking_at_viewer": "looking_back"},
    "from_below": {"looking_down": "looking_up"},
    "from_above": {"looking_up": "looking_down"},
}


def _validate_cross_field_consistency(scenes: list[dict]) -> None:
    """context_tags의 camera↔gaze 물리적 모순을 감지하고 교정한다."""
    for i, scene in enumerate(scenes):
        ctx = scene.get("context_tags")
        if not ctx:
            continue

        camera = ctx.get("camera", "")
        gaze = ctx.get("gaze", "")

        cameras = camera if isinstance(camera, list) else [camera]
        for cam in cameras:
            if cam in _CAMERA_GAZE_CONFLICTS:
                fix_map = _CAMERA_GAZE_CONFLICTS[cam]
                if gaze in fix_map:
                    fixed = fix_map[gaze]
                    logger.info(
                        "[Finalize] Scene %d: camera-gaze conflict %s+%s → gaze=%s",
                        i,
                        cam,
                        gaze,
                        fixed,
                    )
                    ctx["gaze"] = fixed


def _rebuild_image_prompt_from_context_tags(scenes: list[dict]) -> None:
    """context_tags에서 image_prompt를 재조립하여 복장/identity 오염을 차단한다.

    context_tags 표준 필드(camera/pose/gaze/action/expression/environment/cinematic/props)
    중 하나라도 있으면 재조립 실행 — Gemini가 image_prompt에 임의 삽입한 복장·identity 태그
    를 제거하는 효과. context_tags가 완전히 비어있는 구 스토리보드만 건너뛴다 (후방 호환).
    재조립 순서는 PromptBuilder 12-Layer와 매핑된다:
      camera(L9) → pose+gaze(L7/L8) → action(L8) → props(L8)
      → expression(L7) → environment(L10) → cinematic(L11)
    """
    rebuilt_count = 0
    for scene in scenes:
        ctx = scene.get("context_tags")
        if not ctx:
            continue
        # context_tags에 표준 필드가 하나라도 있으면 재조립 (B-1: 조건 완화)
        # 구 스토리보드(context_tags 완전 비어있음)는 skip하여 후방 호환 유지
        if not any(ctx.get(f) for f in _CONTEXT_TAG_FIELDS):
            continue

        tags: list[str] = []
        speaker = scene.get("speaker", "")
        is_narrator = speaker == "Narrator"

        if is_narrator:
            tags.extend(["no_humans", "scenery"])

        # L7: camera
        camera = ctx.get("camera") or scene.get("camera")
        if camera:
            tags.append(camera)

        if not is_narrator:
            # L8: pose + gaze
            if ctx.get("pose"):
                tags.append(ctx["pose"])
            if ctx.get("gaze"):
                tags.append(ctx["gaze"])

        # L8: action
        if ctx.get("action"):
            tags.append(ctx["action"])

        # L8: props
        for p in ctx.get("props") or []:
            tags.append(p)

        # L9: expression (non-Narrator)
        if not is_narrator and ctx.get("expression"):
            tags.append(ctx["expression"])

        # L10: environment
        env = ctx.get("environment")
        if isinstance(env, str):
            tags.append(env)
        elif isinstance(env, list):
            tags.extend(env)

        # L11: cinematic
        for c in ctx.get("cinematic") or []:
            tags.append(c)

        if tags:
            scene["image_prompt"] = ", ".join(tags)
            rebuilt_count += 1

    if rebuilt_count:
        logger.info("[Finalize] image_prompt rebuilt from context_tags: %d scenes", rebuilt_count)


# Action 포즈: 골격 정밀도가 중요 → 높은 weight
_ACTION_POSES: frozenset[str] = frozenset(
    {
        "running",
        "jumping",
        "pointing_forward",
        "pointing",
        "arms_up",
    }
)

# 감성/서정 mood: SD 자유 구성 허용 → 낮은 weight
_EMOTIONAL_MOODS: frozenset[str] = frozenset(
    {
        # EMOTION_VOCAB 파생 mood (_context_tag_utils.py SSOT)
        "melancholic",  # sad, grieving, guilty → melancholic
        "lonely",  # lonely → lonely
        "gloomy",  # tired → gloomy
        "somber",  # resigned → somber
        "bittersweet",  # bittersweet → bittersweet
        # cinematographer가 자유롭게 생성하는 감성 mood
        "serene",
        "reflective",
        "nostalgic",
        "romantic",
        "peaceful",
        "pensive",
        "quiet",
    }
)


def _resolve_controlnet_weight(scene: dict, default: float) -> float:
    """씬 맥락(포즈 타입 + mood)에 따라 ControlNet weight 동적 결정.

    - Action 포즈 → 0.80 (포즈 정밀도 우선)
    - 감성/서정 mood → 0.45 (SD 자유 구성 허용)
    - 일반 → default
    """
    pose = scene.get("controlnet_pose", "")
    mood = (scene.get("context_tags") or {}).get("mood", "")
    if pose in _ACTION_POSES:
        return 0.80
    moods = mood if isinstance(mood, list) else [mood]
    for m in moods:
        if m in _EMOTIONAL_MOODS:
            return 0.45
    return default


def _validate_scene_modes(scenes: list[dict], structure: str, state: dict) -> None:
    """O-2: scene_mode 검증/보정 (multi 씬 유효성 확인)."""
    # O-2c: Dialogue 외 구조에서 multi 차단
    if structure.replace("_", " ") not in ("dialogue", "narrated dialogue"):
        for scene in scenes:
            if scene.get("scene_mode") == "multi":
                scene["scene_mode"] = "single"
                logger.warning("[Finalize] Non-dialogue structure, forcing scene_mode=single")

    # O-2e: Narrator + multi 모순 보정
    for scene in scenes:
        if scene.get("speaker") == "Narrator" and scene.get("scene_mode") == "multi":
            scene["scene_mode"] = "single"
            logger.warning("[Finalize] Narrator scene cannot be multi, forcing single")

    # O-2b: multi인데 character_b_id 없으면 single로 보정
    state_char_b = state.get("character_b_id") or state.get("draft_character_b_id")
    if not state_char_b:
        for scene in scenes:
            if scene.get("scene_mode") == "multi":
                scene["scene_mode"] = "single"
                logger.warning("[Finalize] scene_mode=multi but character_b_id=None, forcing single")

    # O-2d: multi 씬 상한 경고
    multi_count = sum(1 for s in scenes if s.get("scene_mode") == "multi")
    if multi_count > 2:
        logger.warning("[Finalize] %d multi scenes detected (max recommended: 2)", multi_count)


def _auto_populate_scene_flags(
    scenes: list[dict],
    character_id: int | None,
    character_b_id: int | None = None,
) -> None:
    """씬별 생성 플래그(use_controlnet, use_ip_adapter, multi_gen_enabled) 자동 할당.

    이미 값이 있는 필드는 덮어쓰지 않는다 (Cinematographer 명시값 보존).
    Express 모드처럼 Cinematographer가 스킵된 경우, context_tags.pose에서
    controlnet_pose를 자동 할당하여 ControlNet을 활성화한다.
    Dialogue 구조에서는 speaker B도 character_b_id 기반으로 ControlNet/IP-Adapter 활성화.
    """
    from config import (  # noqa: PLC0415
        DEFAULT_CONTROLNET_WEIGHT,
        DEFAULT_IP_ADAPTER_WEIGHT,
        DEFAULT_MULTI_GEN_ENABLED,
        DEFAULT_POSE_TAG,
    )
    from services.controlnet import POSE_MAPPING, SITTING_EXCLUDED_POSES  # noqa: PLC0415

    valid_poses = set(POSE_MAPPING.keys())

    for scene in scenes:
        # O-2a: multi 씬은 ControlNet/IP-Adapter 미지원 + 후보 3장 자동 활성화
        if scene.get("scene_mode") == "multi":
            scene["use_controlnet"] = False
            scene["use_ip_adapter"] = False
            scene["multi_gen_enabled"] = True
            continue

        is_narrator = scene.get("speaker") == "Narrator"
        # Dialogue: speaker B uses character_b_id, others use character_id
        scene_char_id = character_b_id if scene.get("speaker") == "B" else character_id

        # controlnet_pose 자동 할당: Cinematographer 미실행 시 context_tags.pose에서 파생
        # sitting 계열은 ControlNet 자동 활성화 제외 (하체 왜곡 문제)
        if not scene.get("controlnet_pose") and not is_narrator and scene_char_id:
            ctx_pose_raw = (scene.get("context_tags") or {}).get("pose", DEFAULT_POSE_TAG)
            ctx_pose = (
                (ctx_pose_raw[0] if ctx_pose_raw else DEFAULT_POSE_TAG)
                if isinstance(ctx_pose_raw, list)
                else ctx_pose_raw
            )
            if ctx_pose in SITTING_EXCLUDED_POSES:
                scene["controlnet_pose"] = ctx_pose  # pose 기록은 하되 use_controlnet은 False
            elif ctx_pose in valid_poses:
                scene["controlnet_pose"] = ctx_pose
            elif ctx_pose and ctx_pose.replace("_", " ") in valid_poses:
                scene["controlnet_pose"] = ctx_pose.replace("_", " ")
            else:
                scene["controlnet_pose"] = DEFAULT_POSE_TAG

        assigned_pose = scene.get("controlnet_pose")
        is_sitting_pose = assigned_pose in SITTING_EXCLUDED_POSES
        has_pose = bool(assigned_pose) and not is_sitting_pose

        if scene.get("use_controlnet") is None:
            scene["use_controlnet"] = has_pose and not is_narrator
        if scene.get("controlnet_weight") is None and scene["use_controlnet"]:
            scene["controlnet_weight"] = _resolve_controlnet_weight(scene, DEFAULT_CONTROLNET_WEIGHT)

        if scene.get("use_ip_adapter") is None:
            scene["use_ip_adapter"] = bool(scene_char_id) and not is_narrator
        if scene.get("ip_adapter_weight") is None and scene["use_ip_adapter"]:
            scene["ip_adapter_weight"] = DEFAULT_IP_ADAPTER_WEIGHT

        if scene.get("multi_gen_enabled") is None:
            scene["multi_gen_enabled"] = DEFAULT_MULTI_GEN_ENABLED

    populated = sum(1 for s in scenes if s.get("use_controlnet") or s.get("use_ip_adapter"))
    logger.info("[Finalize] Scene flags populated: %d/%d scenes with generation overrides", populated, len(scenes))


def _flatten_tts_designs(scenes: list[dict]) -> None:
    """tts_design dict → voice_design_prompt, head_padding, tail_padding, scene_emotion 분해."""
    for scene in scenes:
        tts = scene.pop("tts_design", None)
        if not tts or tts.get("skip"):
            continue
        if vdp := tts.get("voice_design_prompt"):
            scene["voice_design_prompt"] = vdp
        if emotion := tts.get("emotion"):
            scene["scene_emotion"] = emotion
        pacing = tts.get("pacing") or {}
        if (hp := pacing.get("head_padding")) is not None:
            scene["head_padding"] = hp
        if (tp := pacing.get("tail_padding")) is not None:
            scene["tail_padding"] = tp


def _ensure_minimum_duration(scenes: list[dict], target_duration: int, language: str) -> None:
    """총 duration을 target 범위(85%~130%)로 보정한다.

    - deficit (< 85%): 비례 재분배로 늘림
    - overflow (> 130%): 비례 스케일 다운
    """
    total = sum(s.get("duration", 0) for s in scenes)
    if total <= 0 or not scenes:
        return

    if total < target_duration * DURATION_DEFICIT_THRESHOLD:
        from services.agent.nodes._revise_expand import redistribute_durations

        redistribute_durations(scenes, target_duration, language)
        new_total = sum(s.get("duration", 0) for s in scenes)
        logger.info("[Finalize] Duration deficit 보정: %.1fs → %.1fs (target=%ds)", total, new_total, target_duration)

    elif total > target_duration * DURATION_OVERFLOW_THRESHOLD:
        scale = (target_duration * DURATION_OVERFLOW_THRESHOLD) / total
        for scene in scenes:
            scene["duration"] = round(scene.get("duration", 0) * scale, 1)
        new_total = sum(s.get("duration", 0) for s in scenes)
        logger.info("[Finalize] Duration overflow 보정: %.1fs → %.1fs (target=%ds)", total, new_total, target_duration)


async def finalize_node(state: ScriptState, config: RunnableConfig) -> dict:
    """Quick: draft → final 패스스루. Full: Production 결과 병합 + character_actions 변환."""
    # 에러 상태이면 즉시 반환 (에러 메시지 보존)
    if state.get("error"):
        logger.warning("[LangGraph] Finalize: 에러 상태 전파 → %s", state.get("error"))
        return {"error": state.get("error")}

    import copy  # noqa: PLC0415

    sound_rec: dict | None = None
    copyright_result: dict | None = None

    if state.get("cinematographer_result"):
        # Full 모드 또는 FastTrack(cinematographer만 실행) — 공통으로 cinematographer 결과 사용
        scenes, sound_rec, copyright_result = _merge_production_results(state)
    else:
        scenes = [copy.deepcopy(s) for s in (state.get("draft_scenes") or [])]

    # BGM fallback: sound_designer 미실행 시 기본 BGM 추천
    if not sound_rec:
        topic = state.get("topic", "")
        sound_rec = {
            "prompt": f"soft background music for short video about {topic}",
            "mood": "neutral",
            "duration": state.get("duration", 30),
        }

    # Defense: Cinematographer may overwrite speaker assignments → re-enforce A/B alternation
    structure = (state.get("structure") or "").lower()
    if structure.replace("_", " ") in ("dialogue", "narrated dialogue"):
        from services.script.scene_postprocess import ensure_dialogue_speakers  # noqa: PLC0415

        ensure_dialogue_speakers(scenes)

    _validate_scene_modes(scenes, structure, state)

    _sanitize_quality_tags(scenes)

    from ._finalize_validators import (
        filter_style_modifiers,
        normalize_ip_adapter_weights,
        validate_controlnet_poses,
        validate_ip_adapter_weights,
        validate_ken_burns_presets,
    )

    # Phase 28-B: 논리 그룹별 try/except 래핑 (non-fatal)
    # 그룹 1: 태그 정규화
    try:
        filter_style_modifiers(scenes)
        _apply_tag_aliases(scenes)
        _inject_negative_prompts(scenes)
        from ._prompt_conflict_resolver import resolve_prompt_conflicts

        resolve_prompt_conflicts(scenes)
    except Exception:
        logger.warning("[Finalize] 태그 정규화 일부 실패 (non-fatal)", exc_info=True)

    _copy_scene_level_to_context_tags(scenes)

    from ._context_tag_utils import (
        diversify_expressions,
        validate_context_tag_categories,
    )
    from ._diversify_utils import (
        diversify_actions,
        diversify_cameras,
        diversify_gazes,
        diversify_poses,
    )

    # 그룹 2: context_tags 주입 + 다양성 처리
    try:
        validate_context_tag_categories(scenes)
        _inject_writer_plan_emotions(scenes, state.get("writer_plan"))
        _inject_default_context_tags(scenes)
        diversify_expressions(scenes)
        diversify_gazes(scenes)
        diversify_actions(scenes)
        diversify_cameras(scenes)
        diversify_poses(scenes)
    except Exception:
        logger.warning("[Finalize] context_tags/다양성 처리 실패 (non-fatal)", exc_info=True)

    # 그룹 3: 환경/로케이션 태그
    try:
        _normalize_environment_tags(scenes)
        _inject_location_map_tags(scenes, state.get("writer_plan"))
        _inject_location_negative_tags(scenes, state.get("writer_plan"))
        _stabilize_location_cinematic(scenes, state.get("writer_plan"))
        from ._prompt_conflict_resolver import _resolve_positive_negative_conflicts

        _resolve_positive_negative_conflicts(scenes)
    except Exception:
        logger.warning("[Finalize] 환경/로케이션 태그 처리 실패 (non-fatal)", exc_info=True)

    # 그룹 3.5: context_tags 구조화 — cross-field 검증 + image_prompt 재조립
    # 재조립 후 alias 재적용 필수: context_tags에 비표준 태그(daytime 등)가 있을 수 있음
    try:
        _validate_cross_field_consistency(scenes)
        _rebuild_image_prompt_from_context_tags(scenes)
        _apply_tag_aliases(scenes)  # 재조립된 image_prompt에 alias 재적용
    except Exception:
        logger.warning("[Finalize] context_tags 구조화 처리 실패 (non-fatal)", exc_info=True)

    # 미분류 태그 LLM 사전 분류 (이미지 생성 전)
    from config_pipelines import FEATURE_TAG_LLM_CLASSIFICATION

    if FEATURE_TAG_LLM_CLASSIFICATION:
        from ._tag_classification import classify_unknown_scene_tags

        try:
            with get_db_session() as db_session:
                await classify_unknown_scene_tags(scenes, db_session)
        except Exception:
            logger.warning("[Finalize] LLM tag classification failed (non-fatal)", exc_info=True)

    # 그룹 4: 검증 (개별 래핑)
    try:
        validate_controlnet_poses(scenes)
    except Exception:
        logger.warning("[Finalize] controlnet pose 검증 실패 (non-fatal)", exc_info=True)
    try:
        validate_ken_burns_presets(scenes)
    except Exception:
        logger.warning("[Finalize] ken_burns preset 검증 실패 (non-fatal)", exc_info=True)

    # DB 세션 1회로 IP-Adapter 정규화 + character_actions 변환
    character_id = (
        state.get("character_id") if state.get("character_id") is not None else state.get("draft_character_id")
    )
    character_b_id = (
        state.get("character_b_id") if state.get("character_b_id") is not None else state.get("draft_character_b_id")
    )
    with get_db_session() as db_session:
        # group_id fallback: 캐릭터 미지정 시 그룹의 캐릭터에서 해결
        group_id = state.get("group_id")
        if not character_id and group_id:
            character_id, character_b_id = _resolve_characters_from_group(
                group_id,
                state.get("structure", ""),
                db_session,
            )

        _filter_exclusive_identity_tags(scenes, character_id, character_b_id, db_session)
        _enforce_character_clothing(scenes, character_id, character_b_id, db_session)
        normalize_ip_adapter_weights(scenes, character_id, character_b_id, db=db_session)
        validate_ip_adapter_weights(scenes)
        _auto_populate_scene_flags(scenes, character_id, character_b_id)
        _flatten_tts_designs(scenes)

        # Duration 최종 보정 (Review/Revise 경유 후에도 부족할 수 있음)
        target_duration = state.get("duration", 0)
        if target_duration > 0:
            _ensure_minimum_duration(scenes, target_duration, state.get("language", "Korean"))

        if character_id or character_b_id:
            _populate_character_actions(scenes, character_id, character_b_id, db_session)

    return {
        "final_scenes": scenes,
        "sound_recommendation": sound_rec,
        "copyright_result": copyright_result,
    }


def _resolve_characters_from_group(
    group_id: int,
    structure: str,
    db,
) -> tuple[int | None, int | None]:
    """group_id → 그룹의 캐릭터에서 character_id/character_b_id 해결."""
    from models.character import Character

    chars = (
        db.query(Character.id)
        .filter(Character.group_id == group_id, Character.deleted_at.is_(None))
        .order_by(Character.id)
        .limit(2)
        .all()
    )
    if not chars:
        logger.warning("[Finalize] Group %d에 캐릭터 없음, character_id=None 유지", group_id)
        return None, None
    char_a = chars[0].id
    _DIALOGUE_STRUCTURES = {"Dialogue", "Narrated Dialogue", "Narrated_Dialogue"}
    char_b = chars[1].id if len(chars) > 1 and structure in _DIALOGUE_STRUCTURES else None
    logger.info("[Finalize] Resolved characters from group %d: A=%s, B=%s", group_id, char_a, char_b)
    return char_a, char_b


def _populate_character_actions(
    scenes: list[dict],
    character_id: int | None,
    character_b_id: int | None,
    db,
) -> None:
    """context_tags → character_actions 변환 (finalize 단계)."""
    try:
        from services.characters import auto_populate_character_actions

        auto_populate_character_actions(scenes, character_id, character_b_id, db)
        actions_count = sum(1 for s in scenes if s.get("character_actions"))
        logger.info("[LangGraph] Finalize: character_actions populated for %d/%d scenes", actions_count, len(scenes))
    except Exception:
        logger.warning("[LangGraph] Finalize: character_actions 변환 실패 (non-fatal)", exc_info=True)
