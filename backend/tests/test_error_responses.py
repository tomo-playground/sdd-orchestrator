"""Test structured error response service."""

import pytest
from fastapi import HTTPException

from services.error_responses import raise_user_error


class TestRaiseUserError:
    def test_known_operation_returns_korean_message(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_user_error("image_generate", RuntimeError("SD WebUI timeout"))
        detail = exc_info.value.detail
        assert isinstance(detail, dict)
        assert detail["message"] == "이미지 생성에 실패했습니다."
        assert detail["code"] == "image_generate"
        assert "SD WebUI timeout" in detail["debug"]
        assert exc_info.value.status_code == 500

    def test_unknown_operation_returns_fallback_message(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_user_error("unknown_op", ValueError("bad"))
        detail = exc_info.value.detail
        assert detail["message"] == "요청 처리에 실패했습니다."
        assert detail["code"] == "unknown_op"

    def test_custom_status_code(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_user_error("video_delete", OSError("disk"), status_code=503)
        assert exc_info.value.status_code == 503

    def test_all_operations_have_korean_messages(self):
        """Verify all registered operations produce Korean messages."""
        from services.error_responses import _USER_MESSAGES

        for op, msg in _USER_MESSAGES.items():
            assert msg, f"Empty message for operation: {op}"
            # Korean messages should contain at least one Korean character
            assert any("\uac00" <= c <= "\ud7a3" for c in msg), f"Non-Korean message for {op}: {msg}"

    def test_preserves_exception_chain(self):
        """Ensure the original exception is chained."""
        original = ValueError("original error")
        with pytest.raises(HTTPException) as exc_info:
            raise_user_error("image_generate", original)
        assert exc_info.value.__cause__ is original

    def test_prompt_compose_error(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_user_error("prompt_compose", RuntimeError("token overflow"))
        detail = exc_info.value.detail
        assert detail["message"] == "프롬프트 조합에 실패했습니다."

    def test_video_delete_error(self):
        with pytest.raises(HTTPException) as exc_info:
            raise_user_error("video_delete", OSError("permission denied"))
        detail = exc_info.value.detail
        assert detail["message"] == "영상 삭제에 실패했습니다."
