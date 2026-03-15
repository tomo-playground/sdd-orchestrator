"""LLMProvider Protocol — 모든 LLM 제공자가 구현해야 하는 인터페이스."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from services.llm.types import LLMConfig, LLMResponse


@runtime_checkable
class LLMProvider(Protocol):
    """LLM 호출 인터페이스.

    구현체: GeminiProvider, OllamaProvider(향후)
    @runtime_checkable: isinstance(provider, LLMProvider) 런타임 체크 허용.
    structural subtyping이므로 명시적 상속 불필요.
    """

    async def generate(
        self,
        step_name: str,
        contents: str,
        config: LLMConfig,
        model: str | None = None,
    ) -> LLMResponse:
        """LLM을 호출하고 응답을 반환한다.

        Args:
            step_name: Langfuse generation 이름 (예: "writer_planning")
            contents: 사용자 프롬프트
            config: provider-agnostic 설정
            model: 모델 ID. None이면 provider 기본값 사용.

        Returns:
            LLMResponse(text, usage, raw)
        """
        ...
