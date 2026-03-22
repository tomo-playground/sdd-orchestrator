"""Provider-agnostic LLM 요청/응답 타입."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMConfig:
    """Provider-agnostic 요청 설정.

    provider 전용 설정(safety_settings, tools 등)은 각 Provider 내부에서 처리.
    """

    system_instruction: str | None = None
    temperature: float | None = None
    thinking_budget: int | None = None  # Gemini 2.5 thinking token budget (0=disabled, -1=auto)
    response_mime_type: str | None = None  # "application/json" → JSON 강제 출력


@dataclass
class LLMResponse:
    """Provider-agnostic 응답."""

    text: str
    usage: dict[str, int] | None = None  # input/output/total tokens
    raw: Any = None  # provider raw response (디버깅용)
    observation_id: str | None = None  # LangFuse observation ID (Score 부착용)
