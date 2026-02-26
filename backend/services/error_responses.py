"""Structured error responses with Korean user-facing messages.

Usage:
    from services.error_responses import raise_user_error

    try:
        result = await some_operation()
    except Exception as exc:
        raise_user_error("image_generate", exc)
"""

from __future__ import annotations

import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Operation → Korean user-facing message
_USER_MESSAGES: dict[str, str] = {
    "image_generate": "이미지 생성에 실패했습니다.",
    "image_store": "이미지 저장에 실패했습니다.",
    "image_edit": "이미지 편집에 실패했습니다.",
    "image_suggest": "편집 제안 생성에 실패했습니다.",
    "prompt_compose": "프롬프트 조합에 실패했습니다.",
    "video_delete": "영상 삭제에 실패했습니다.",
    "video_render": "영상 렌더링에 실패했습니다.",
    "storyboard_generate": "스토리보드 생성에 실패했습니다.",
    "youtube_auth": "YouTube 인증에 실패했습니다.",
    "youtube_upload": "YouTube 업로드에 실패했습니다.",
    "character_update": "캐릭터 업데이트에 실패했습니다.",
    "scene_edit_image": "씬 이미지 편집에 실패했습니다.",
    "batch_validate": "일괄 검증에 실패했습니다.",
    "quality_summary": "품질 요약 조회에 실패했습니다.",
    "consistency_analysis": "일관성 분석에 실패했습니다.",
    "quality_alerts": "품질 알림 조회에 실패했습니다.",
    "preview_generate": "미리보기 생성에 실패했습니다.",
}


def raise_user_error(
    operation: str,
    exc: Exception,
    *,
    status_code: int = 500,
) -> None:
    """Log the technical error and raise HTTPException with structured detail.

    Args:
        operation: Key in _USER_MESSAGES (e.g. "image_generate").
        exc: The original exception.
        status_code: HTTP status code (default 500).

    Raises:
        HTTPException with structured detail dict.
    """
    message = _USER_MESSAGES.get(operation, "요청 처리에 실패했습니다.")
    logger.exception("[%s] %s", operation, exc)
    raise HTTPException(
        status_code=status_code,
        detail={"message": message, "code": operation},
    ) from exc
