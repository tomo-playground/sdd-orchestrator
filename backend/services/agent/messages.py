"""Agent Communication Protocol (Phase 10-C-1).

에이전트 간 구조화된 메시지 교환 및 상태 압축 유틸리티.
"""

from __future__ import annotations

from typing import TypedDict


class AgentMessage(TypedDict, total=False):
    """에이전트 간 메시지 프로토콜.

    Attributes:
        sender: 발신 에이전트명 (예: "director", "cinematographer")
        recipient: 수신 에이전트명
        content: 자연어 메시지 내용
        message_type: 메시지 유형 ("feedback" | "request" | "suggestion" | "approval")
        metadata: 구조화된 추가 데이터 (선택)
    """

    sender: str
    recipient: str
    content: str
    message_type: str  # "feedback" | "request" | "suggestion" | "approval"
    metadata: dict | None


# ── 상수 ──────────────────────────────────────────────────

MAX_MESSAGE_WINDOW = 10  # 슬라이딩 윈도우: 최근 N개 메시지만 유지
MAX_CONTEXT_TOKENS = 2000  # 노드별 컨텍스트 주입 시 최대 토큰 수


# ── 메시지 포맷팅 ──────────────────────────────────────────


def format_message(msg: AgentMessage) -> str:
    """단일 메시지를 읽기 쉬운 문자열로 포맷팅한다.

    Args:
        msg: AgentMessage 딕셔너리

    Returns:
        "[sender → recipient] (type): content" 형식 문자열
    """
    sender = msg.get("sender", "unknown")
    recipient = msg.get("recipient", "unknown")
    msg_type = msg.get("message_type", "message")
    content = msg.get("content", "")

    return f"[{sender} → {recipient}] ({msg_type}): {content}"


def format_messages(messages: list[AgentMessage]) -> str:
    """메시지 리스트를 줄바꿈으로 구분된 문자열로 포맷팅한다.

    Args:
        messages: AgentMessage 리스트

    Returns:
        각 메시지를 줄바꿈으로 구분한 문자열
    """
    if not messages:
        return ""
    return "\n".join(format_message(msg) for msg in messages)


# ── 상태 압축 (State Condensation) ────────────────────────


def condense_messages(messages: list[AgentMessage]) -> str:
    """에이전트 메시지 로그를 핵심 결론으로 압축한다.

    슬라이딩 윈도우 방식: 최근 MAX_MESSAGE_WINDOW개 메시지만 유지하고,
    오래된 메시지는 요약으로 대체한다.

    Args:
        messages: 전체 메시지 리스트

    Returns:
        압축된 메시지 문자열 (요약 + 최근 메시지)
    """
    if not messages:
        return ""

    if len(messages) <= MAX_MESSAGE_WINDOW:
        # 메시지가 적으면 전체 반환
        return format_messages(messages)

    # 오래된 메시지와 최근 메시지 분리
    old_messages = messages[:-MAX_MESSAGE_WINDOW]
    recent_messages = messages[-MAX_MESSAGE_WINDOW:]

    # 오래된 메시지 요약
    summary = _summarize_decisions(old_messages)

    # 요약 + 최근 메시지 조합
    if summary:
        return f"[이전 논의 요약] {summary}\n\n[최근 메시지]\n{format_messages(recent_messages)}"
    else:
        return format_messages(recent_messages)


def _summarize_decisions(messages: list[AgentMessage]) -> str:
    """메시지 목록에서 핵심 결정사항만 추출한다.

    Args:
        messages: 요약할 메시지 리스트

    Returns:
        핵심 결정사항 요약 문자열
    """
    if not messages:
        return ""

    # approval 타입 메시지 추출
    approvals = [msg for msg in messages if msg.get("message_type") == "approval"]
    if approvals:
        decisions = [msg.get("content", "") for msg in approvals]
        return ", ".join(decisions)

    # feedback/request 타입 메시지 수 집계
    feedback_count = sum(1 for msg in messages if msg.get("message_type") == "feedback")
    request_count = sum(1 for msg in messages if msg.get("message_type") == "request")

    parts = []
    if feedback_count > 0:
        parts.append(f"피드백 {feedback_count}건")
    if request_count > 0:
        parts.append(f"요청 {request_count}건")

    return ", ".join(parts) if parts else f"{len(messages)}개 메시지 교환"


# ── 토큰 예산 관리 ─────────────────────────────────────────


def truncate_to_token_budget(text: str, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
    """텍스트를 최대 토큰 수에 맞춰 잘라낸다.

    간단한 휴리스틱: 1 토큰 ≈ 4 문자 (영어 기준), 한국어는 1 토큰 ≈ 2-3 문자

    Args:
        text: 잘라낼 텍스트
        max_tokens: 최대 토큰 수

    Returns:
        잘려진 텍스트
    """
    # 간단한 문자 수 기반 근사 (한국어/영어 혼합 가정: 1 토큰 ≈ 3 문자)
    max_chars = max_tokens * 3

    if len(text) <= max_chars:
        return text

    # 잘라내고 "..." 추가
    truncated = text[:max_chars]
    return truncated.rsplit(" ", 1)[0] + "..."  # 단어 경계에서 자르기
