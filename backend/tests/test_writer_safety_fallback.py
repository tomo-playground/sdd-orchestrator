"""Writer PROHIBITED_CONTENT fallback 시 sanitization 적용 테스트 (SP-043 Part C).

안전 필터 차단 → 재시도 경로에서 _sanitize_for_gemini_prompt가 적용되는지 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from services.agent.state import ScriptState


def _make_state(**overrides) -> ScriptState:
    """테스트용 기본 ScriptState를 생성한다."""
    base: ScriptState = {
        "topic": "BTS 방탄소년단 소녀들의 이야기",
        "description": "소녀들이 꿈을 이루는 과정",
        "duration": 10,
        "language": "korean",
        "structure": "monologue",
        "actor_a_gender": "female",
        "skip_stages": [],
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


@pytest.mark.asyncio
@patch("services.agent.nodes.writer._create_plan", new_callable=AsyncMock, return_value=None)
async def test_writer_fallback_applies_sanitization(mock_plan):
    """PROHIBITED_CONTENT fallback 시 _sanitize_for_gemini_prompt가 topic과 description에 적용되는지 확인."""
    from services.agent.nodes.writer import writer_node

    sanitize_calls: list[str] = []
    original_sanitize = None

    # 원본 함수를 가져와서 실제 치환도 수행하면서 호출 기록
    from services.script.gemini_generator import _sanitize_for_gemini_prompt as _orig

    original_sanitize = _orig

    def capture_sanitize(text: str) -> str:
        sanitize_calls.append(text)
        return original_sanitize(text)

    # 1차: safety error 발생, 2차: 성공
    safety_error = ValueError("🛡️ Gemini 안전 필터가 콘텐츠를 차단했습니다 (PROHIBITED_CONTENT)")
    success_result = {
        "scenes": [{"scene_id": 1, "script": "결과 텍스트", "speaker": "A", "duration": 3, "image_prompt": "smile"}],
    }
    mock_generate = AsyncMock(side_effect=[safety_error, success_result])

    with (
        patch("services.agent.nodes.writer.generate_script", mock_generate),
        patch("services.script.gemini_generator._sanitize_for_gemini_prompt", side_effect=capture_sanitize),
    ):
        result = await writer_node(_make_state())

    # 오류 없이 완료
    assert "error" not in result
    assert result["draft_scenes"]

    # sanitization이 fallback 경로에서 호출됨 (topic + description)
    assert len(sanitize_calls) >= 2, f"topic과 description 모두 sanitize 필요, 실제 호출: {len(sanitize_calls)}"

    # generate_script가 2번 호출됨 (1차 실패 + 2차 재시도)
    assert mock_generate.call_count == 2


@pytest.mark.asyncio
@patch("services.agent.nodes.writer._create_plan", new_callable=AsyncMock, return_value=None)
async def test_writer_fallback_sanitizes_topic_content(mock_plan):
    """fallback 시 topic의 미성년자 연상 단어가 실제로 치환되는지 확인."""
    from services.agent.nodes.writer import writer_node

    safety_error = ValueError("PROHIBITED_CONTENT 차단")
    success_result = {
        "scenes": [{"scene_id": 1, "script": "결과", "speaker": "A", "duration": 3, "image_prompt": "test"}],
    }

    captured_requests: list = []

    async def capture_generate(request, db, **kwargs):
        captured_requests.append(request)
        if len(captured_requests) == 1:
            raise safety_error
        return success_result

    with patch("services.agent.nodes.writer.generate_script", side_effect=capture_generate):
        result = await writer_node(_make_state(topic="소녀들의 꿈"))

    assert "error" not in result
    assert len(captured_requests) == 2

    # 재시도 시 topic이 치환됨 ("소녀들" → "여성들" 등)
    retry_request = captured_requests[1]
    assert "소녀" not in retry_request.topic, f"topic에 미성년자 연상 단어가 남아있음: {retry_request.topic}"
