"""Finalize 노드 — 씬 필드 검증 함수 모음."""

from __future__ import annotations

from config import logger


def validate_controlnet_poses(scenes: list[dict]) -> None:
    """controlnet_pose 값이 POSE_MAPPING 키에 있는지 검증. 무효 시 None 리셋."""
    from services.controlnet import POSE_MAPPING  # noqa: PLC0415

    valid_poses = set(POSE_MAPPING.keys())
    for scene in scenes:
        pose = scene.get("controlnet_pose")
        if not pose:
            continue
        if pose not in valid_poses:
            # Gemini가 언더바 형식으로 반환할 수 있으므로 공백으로 변환 후 재검증
            normalized = pose.replace("_", " ")
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
