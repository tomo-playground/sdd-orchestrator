"""Finalize 노드 — 씬 필드 검증 함수 모음."""

from __future__ import annotations

from config import pipeline_logger as logger

# ---------------------------------------------------------------------------
# Style modifier filter
# ---------------------------------------------------------------------------

_STYLE_MODIFIER_TAGS = frozenset(
    {
        "high_contrast",
        "highly_detailed",
        "vibrant_colors",
        "soft_colors",
        "pastel_colors",
        "muted_colors",
        "flat_color",
        "detailed",
        "very_detailed",
        "ultra_detailed",
    }
)


def filter_style_modifiers(scenes: list[dict]) -> None:
    """image_prompt에서 StyleProfile 영역 수식어를 제거한다.

    이 태그들은 StyleProfile이 composition에서 자동 주입하므로
    Cinematographer가 임의로 추가한 것은 제거한다.
    """
    removed_total = 0
    for scene in scenes:
        prompt = scene.get("image_prompt", "")
        if not prompt:
            continue
        tokens = [t.strip() for t in prompt.split(",")]
        cleaned = [t for t in tokens if t.lower().replace(" ", "_") not in _STYLE_MODIFIER_TAGS]
        removed = len(tokens) - len(cleaned)
        if removed:
            scene["image_prompt"] = ", ".join(cleaned)
            removed_total += removed
    if removed_total:
        logger.info("[Finalize] Style modifier 제거: %d개 태그", removed_total)


# ---------------------------------------------------------------------------
# IP-Adapter weight normalizer
# ---------------------------------------------------------------------------


def _get_character_info(cid: int | None, db=None) -> tuple[float | None, bool]:
    """캐릭터 DB에서 ip_adapter_weight와 character LoRA 보유 여부를 1회 쿼리로 반환한다.

    Returns:
        (ip_adapter_weight or None, has_character_lora)
    """
    if not cid:
        return None, False
    try:
        from sqlalchemy import select  # noqa: PLC0415

        from models.character import Character  # noqa: PLC0415

        if db is None:
            from database import get_db_session  # noqa: PLC0415

            with get_db_session() as db:
                char = db.execute(
                    select(Character).where(Character.id == cid),
                ).scalar_one_or_none()
        else:
            char = db.execute(
                select(Character).where(Character.id == cid),
            ).scalar_one_or_none()

        if not char:
            return None, False

        ip_weight = char.ip_adapter_weight if hasattr(char, "ip_adapter_weight") else None
        has_lora = bool(char.loras and any(lora.get("lora_type") == "character" for lora in char.loras))
        return ip_weight, has_lora
    except Exception:
        return None, False


# Backward-compatible wrappers for tests
def _get_character_ip_weight(cid: int | None, db=None) -> float | None:
    """캐릭터 DB에서 ip_adapter_weight 기본값을 조회한다."""
    return _get_character_info(cid, db)[0]


def _has_character_lora(cid: int | None, db=None) -> bool:
    """캐릭터가 character 타입 LoRA를 보유하는지 확인한다."""
    if not cid or not db:
        return False
    return _get_character_info(cid, db)[1]


def normalize_ip_adapter_weights(
    scenes: list[dict],
    character_id: int | None,
    character_b_id: int | None = None,
    db=None,
) -> None:
    """Cinematographer가 null로 남긴 ip_adapter_weight를 캐릭터 DB 기본값으로 통일한다.

    Narrator 씬은 항상 0.0. Speaker별 캐릭터 기본값 적용.
    LoRA 없는 캐릭터는 IP-Adapter weight 최소 0.5 보장 (일관성 보상).
    """
    from config import DEFAULT_IP_ADAPTER_WEIGHT, MIN_IP_ADAPTER_WEIGHT_NO_LORA  # noqa: PLC0415

    # 1회 쿼리로 ip_weight + LoRA 보유 여부 동시 조회 (N+1 방지)
    weight_a, has_lora_a = _get_character_info(character_id, db) if character_id else (None, False)
    weight_b, has_lora_b = _get_character_info(character_b_id, db) if character_b_id else (None, False)

    for scene in scenes:
        speaker = scene.get("speaker", "")
        if speaker == "Narrator":
            scene["ip_adapter_weight"] = 0.0
            continue

        if scene.get("ip_adapter_weight") is not None:
            has_lora = has_lora_b if speaker == "B" else has_lora_a
            if not has_lora:
                scene["ip_adapter_weight"] = max(scene["ip_adapter_weight"], MIN_IP_ADAPTER_WEIGHT_NO_LORA)
            continue

        if speaker == "B":
            w = weight_b or DEFAULT_IP_ADAPTER_WEIGHT
            if not has_lora_b:
                w = max(w, MIN_IP_ADAPTER_WEIGHT_NO_LORA)
            scene["ip_adapter_weight"] = w
        else:
            w = weight_a or DEFAULT_IP_ADAPTER_WEIGHT
            if not has_lora_a:
                w = max(w, MIN_IP_ADAPTER_WEIGHT_NO_LORA)
            scene["ip_adapter_weight"] = w


def validate_controlnet_poses(scenes: list[dict]) -> None:
    """controlnet_pose 값이 POSE_MAPPING 키에 있는지 검증. 무효 시 None 리셋.

    POSE_MAPPING 키는 Danbooru 언더바 형식 (e.g. "from_behind").
    Gemini가 공백 형식("from behind")으로 반환할 수 있으므로 양쪽 모두 허용.
    """
    from services.controlnet import POSE_MAPPING  # noqa: PLC0415

    valid_poses = set(POSE_MAPPING.keys())
    for scene in scenes:
        pose = scene.get("controlnet_pose")
        if not pose:
            continue
        if pose in valid_poses:
            continue
        # Gemini가 공백 형식으로 반환할 수 있으므로 언더바로 변환 후 재검증
        normalized = pose.replace(" ", "_")
        if normalized in valid_poses:
            scene["controlnet_pose"] = normalized
        else:
            logger.warning("[Finalize] Invalid controlnet_pose '%s' → reset to None", pose)
            scene["controlnet_pose"] = None


def validate_ip_adapter_weights(scenes: list[dict]) -> None:
    """ip_adapter_weight 범위 [0.0, 1.0] 클램프."""
    for scene in scenes:
        w = scene.get("ip_adapter_weight")
        if w is None:
            continue
        clamped = max(0.0, min(1.0, float(w)))
        if clamped != w:
            logger.warning("[Finalize] ip_adapter_weight %.2f → clamped to %.2f", w, clamped)
            scene["ip_adapter_weight"] = clamped


def validate_ken_burns_presets(scenes: list[dict]) -> None:
    """씬별 ken_burns_preset 검증. 무효 시 제거, 누락 시 감정 기반 자동 배정."""
    from services.motion import VALID_PRESET_NAMES, suggest_ken_burns_preset  # noqa: PLC0415

    for i, scene in enumerate(scenes):
        preset = scene.get("ken_burns_preset")
        if preset and preset not in VALID_PRESET_NAMES:
            logger.warning("[Finalize] Invalid ken_burns_preset '%s' → removed", preset)
            scene.pop("ken_burns_preset", None)
            preset = None
        if not preset:
            emotion = (scene.get("context_tags") or {}).get("emotion")
            if emotion:
                scene["ken_burns_preset"] = suggest_ken_burns_preset(emotion, seed=i)
                logger.info(
                    "[Finalize] ken_burns_preset auto-assigned: scene %d → %s (emotion=%s)",
                    i,
                    scene["ken_burns_preset"],
                    emotion,
                )
