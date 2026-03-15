"""LLM Provider 싱글턴 레지스트리."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.llm.provider import LLMProvider

_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """앱 시작 시 결정된 LLM Provider 싱글턴을 반환한다."""
    global _provider
    if _provider is None:
        from config_pipelines import LLM_PROVIDER  # noqa: PLC0415

        if LLM_PROVIDER == "ollama":
            from config_pipelines import OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL  # noqa: PLC0415
            from services.llm.ollama_provider import OllamaProvider  # noqa: PLC0415

            _provider = OllamaProvider(OLLAMA_BASE_URL, OLLAMA_DEFAULT_MODEL)
        else:
            from services.llm.gemini_provider import GeminiProvider  # noqa: PLC0415

            _provider = GeminiProvider()
    return _provider  # type: ignore[return-value]
