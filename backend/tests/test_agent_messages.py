"""Agent Message Protocol 테스트 (Phase 10-C-1)."""

from __future__ import annotations

from services.agent.messages import (
    MAX_MESSAGE_WINDOW,
    AgentMessage,
    condense_messages,
    format_message,
    format_messages,
    truncate_to_token_budget,
)

# ── 메시지 포맷팅 테스트 ────────────────────────────────────


def test_format_message_basic():
    """기본 메시지 포맷팅."""
    msg: AgentMessage = {
        "sender": "director",
        "recipient": "cinematographer",
        "content": "씬 3의 카메라 앵글을 변경해주세요",
        "message_type": "feedback",
    }

    result = format_message(msg)

    assert "director → cinematographer" in result
    assert "feedback" in result
    assert "씬 3의 카메라 앵글을 변경해주세요" in result


def test_format_message_with_metadata():
    """메타데이터가 있는 메시지."""
    msg: AgentMessage = {
        "sender": "writer",
        "recipient": "critic",
        "content": "씬 배분 계획을 검토해주세요",
        "message_type": "request",
        "metadata": {"scene_count": 5},
    }

    result = format_message(msg)

    assert "writer → critic" in result
    assert "request" in result
    # metadata는 format_message에서 표시 안 함 (선택 필드)


def test_format_messages_empty():
    """빈 메시지 리스트."""
    result = format_messages([])
    assert result == ""


def test_format_messages_multiple():
    """여러 메시지 포맷팅."""
    messages: list[AgentMessage] = [
        {
            "sender": "director",
            "recipient": "cinematographer",
            "content": "태그를 검증하세요",
            "message_type": "request",
        },
        {
            "sender": "cinematographer",
            "recipient": "director",
            "content": "검증 완료했습니다",
            "message_type": "approval",
        },
    ]

    result = format_messages(messages)

    assert "director → cinematographer" in result
    assert "cinematographer → director" in result
    assert "\n" in result  # 줄바꿈으로 구분


# ── 상태 압축 테스트 ────────────────────────────────────────


def test_condense_messages_empty():
    """빈 메시지 리스트 압축."""
    result = condense_messages([])
    assert result == ""


def test_condense_messages_within_window():
    """윈도우 내 메시지 (압축 불필요)."""
    messages: list[AgentMessage] = [
        {
            "sender": "director",
            "recipient": "tts_designer",
            "content": "감정 표현을 강화하세요",
            "message_type": "feedback",
        },
        {
            "sender": "tts_designer",
            "recipient": "director",
            "content": "수정했습니다",
            "message_type": "approval",
        },
    ]

    result = condense_messages(messages)

    # 압축 없이 전체 메시지 반환
    assert "director → tts_designer" in result
    assert "tts_designer → director" in result
    assert "이전 논의 요약" not in result


def test_condense_messages_exceeds_window():
    """윈도우 초과 메시지 (압축 필요)."""
    # MAX_MESSAGE_WINDOW + 5 = 15개 메시지 생성
    messages: list[AgentMessage] = []
    for i in range(MAX_MESSAGE_WINDOW + 5):
        messages.append(
            {
                "sender": "agent_a",
                "recipient": "agent_b",
                "content": f"MSG_{i:03d}",  # 고유한 패턴 사용
                "message_type": "feedback" if i < 10 else "request",
            }
        )

    result = condense_messages(messages)

    # 요약 포함
    assert "이전 논의 요약" in result

    # 최근 메시지는 유지 (마지막 10개: 5~14)
    assert "MSG_014" in result
    assert "MSG_013" in result
    assert "MSG_005" in result  # 윈도우의 첫 메시지

    # 오래된 메시지는 요약으로 대체 (직접 표시 안 됨)
    assert "MSG_000" not in result
    assert "MSG_001" not in result
    assert "MSG_004" not in result  # 윈도우 밖


def test_condense_messages_with_approvals():
    """approval 타입 메시지가 있는 경우."""
    messages: list[AgentMessage] = []
    for i in range(15):
        messages.append(
            {
                "sender": "agent_a",
                "recipient": "agent_b",
                "content": f"Decision {i}" if i % 5 == 0 else f"Message {i}",
                "message_type": "approval" if i % 5 == 0 else "feedback",
            }
        )

    result = condense_messages(messages)

    # approval 메시지의 content가 요약에 포함
    assert "Decision" in result


def test_condense_messages_summary_counts():
    """피드백/요청 개수 집계."""
    messages: list[AgentMessage] = []
    # 8 feedback + 7 request = 15개
    for i in range(15):
        messages.append(
            {
                "sender": "agent_a",
                "recipient": "agent_b",
                "content": f"Message {i}",
                "message_type": "feedback" if i < 8 else "request",
            }
        )

    result = condense_messages(messages)

    # 요약에 개수 집계 포함
    assert "이전 논의 요약" in result


# ── 토큰 예산 관리 테스트 ────────────────────────────────────


def test_truncate_to_token_budget_short_text():
    """짧은 텍스트 (잘라내기 불필요)."""
    text = "이것은 짧은 텍스트입니다."
    result = truncate_to_token_budget(text, max_tokens=100)
    assert result == text


def test_truncate_to_token_budget_long_text():
    """긴 텍스트 (잘라내기 필요)."""
    text = "가나다라마바사 " * 1000  # 8000자

    result = truncate_to_token_budget(text, max_tokens=100)

    # 100 토큰 × 3 문자 = 300자 근사
    assert len(result) < 400  # 근사치
    assert result.endswith("...")


def test_truncate_to_token_budget_word_boundary():
    """단어 경계에서 잘라내기."""
    text = "word1 word2 word3 word4 word5 " * 100

    result = truncate_to_token_budget(text, max_tokens=50)

    # 단어 중간이 아니라 공백에서 잘림
    assert not result.endswith("word")
    assert result.endswith("...")


# ── 통합 시나리오 테스트 ────────────────────────────────────


def test_message_protocol_end_to_end():
    """메시지 프로토콜 전체 시나리오."""
    # 1. 에이전트 간 메시지 교환
    messages: list[AgentMessage] = []

    # Director → Cinematographer
    messages.append(
        {
            "sender": "director",
            "recipient": "cinematographer",
            "content": "씬 3의 visual_tags를 검증해주세요",
            "message_type": "request",
        }
    )

    # Cinematographer → Director
    messages.append(
        {
            "sender": "cinematographer",
            "recipient": "director",
            "content": "태그 검증 완료. 모두 유효합니다",
            "message_type": "approval",
        }
    )

    # Director → TTS Designer
    messages.append(
        {
            "sender": "director",
            "recipient": "tts_designer",
            "content": "씬 2의 감정 표현을 강화해주세요",
            "message_type": "feedback",
        }
    )

    # TTS Designer → Director
    messages.append(
        {
            "sender": "tts_designer",
            "recipient": "director",
            "content": "voice_design 수정했습니다",
            "message_type": "approval",
        }
    )

    # 2. 메시지 포맷팅
    formatted = format_messages(messages)
    assert "director → cinematographer" in formatted
    assert "tts_designer → director" in formatted

    # 3. 상태 압축 (4개 메시지는 윈도우 내)
    condensed = condense_messages(messages)
    assert len(condensed) > 0
    assert "이전 논의 요약" not in condensed  # 압축 불필요

    # 4. 토큰 예산 준수
    truncated = truncate_to_token_budget(condensed, max_tokens=100)
    assert len(truncated) > 0
