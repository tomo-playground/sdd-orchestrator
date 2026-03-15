"""LLM Provider abstraction and parallel agent execution for Creative Engine."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol, runtime_checkable

import httpx

from config import (
    OLLAMA_BASE_URL,
    OLLAMA_TIMEOUT,
    logger,
)
from services.llm import LLMConfig
from services.llm import get_llm_provider as _get_llm_provider

# ── LLM Provider Protocol ───────────────────────────────────


@runtime_checkable
class CreativeAgentProvider(Protocol):
    """Unified interface for LLM providers."""

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        """Generate text completion.

        Returns:
            {
                "content": str,
                "token_usage": {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int},
                "model_id": str,
            }
        """
        ...


# ── Gemini Provider ──────────────────────────────────────────


class GeminiProvider:
    """Google Gemini API provider — services.llm 추상화 위임."""

    def __init__(self, model_name: str | None = None, api_key: str | None = None) -> None:
        self.model_name = model_name
        # api_key는 services.llm.GeminiProvider가 config에서 읽으므로 참조만 보관
        self._api_key = api_key

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        try:
            llm_response = await _get_llm_provider().generate(
                step_name="creative_agent",
                contents=prompt,
                config=LLMConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                ),
                model=self.model_name,
            )
        except Exception as e:
            msg = f"Gemini API error: {e}"
            raise RuntimeError(msg) from e

        content = llm_response.text
        usage = llm_response.usage or {}
        token_usage = {
            "prompt_tokens": usage.get("input", 0),
            "completion_tokens": usage.get("output", 0),
            "total_tokens": usage.get("total", 0),
        }
        return {
            "content": content,
            "token_usage": token_usage,
            "model_id": self.model_name or "gemini",
        }


# ── Ollama Provider ──────────────────────────────────────────


class OllamaProvider:
    """Local Ollama API provider."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.base_url = OLLAMA_BASE_URL

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
        except httpx.ConnectError as e:
            msg = f"Ollama not reachable at {self.base_url}: {e}"
            raise RuntimeError(msg) from e

        if resp.status_code != 200:
            msg = f"Ollama API error: {resp.status_code} {resp.text[:200]}"
            raise RuntimeError(msg)

        data = resp.json()
        token_usage = {
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        }
        return {
            "content": data.get("response", ""),
            "token_usage": token_usage,
            "model_id": self.model_name,
        }

    async def health_check(self) -> bool:
        """Check if Ollama server is running."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/version")
            return resp.status_code == 200
        except Exception:
            return False


# ── Factory ──────────────────────────────────────────────────


def get_provider(provider_name: str, model_name: str) -> CreativeAgentProvider:
    """Create an LLM provider instance by name."""
    if provider_name == "gemini":
        return GeminiProvider(model_name)
    if provider_name == "ollama":
        return OllamaProvider(model_name)
    msg = f"Unknown provider: {provider_name}"
    raise ValueError(msg)


# ── Parallel Execution ───────────────────────────────────────


async def generate_parallel(
    agents: list[dict[str, Any]],
    objective: str,
) -> list[dict[str, Any]]:
    """Run multiple agents in parallel, returning results for each.

    Each agent dict: {
        "role": str, "preset_id": int,
        "provider": str, "model_name": str,
        "system_prompt": str, "temperature": float,
    }

    Returns list of result dicts: {
        "agent_role": str, "preset_id": int,
        "content": str, "token_usage": dict,
        "model_id": str, "latency_ms": int,
        "temperature": float, "error": str | None,
    }
    """

    async def _run_one(agent: dict) -> dict[str, Any]:
        role = agent["role"]
        agent_objective = agent.get("objective")
        base_prompt = f"{objective}\n\n{agent_objective}" if agent_objective else objective

        # Add markdown formatting instruction
        prompt = (
            f"{base_prompt}\n\n"
            "**응답 작성 가이드 (마크다운 사용):**\n"
            "- ## 제목, ### 소제목으로 구조화\n"
            "- 핵심 내용은 **굵게** 강조\n"
            "- 단계별 설명은 * 리스트 활용\n"
            "- 섹션 구분은 --- 사용\n"
            "- 가독성을 위해 단락을 명확히 구분"
        )
        start = time.monotonic()
        try:
            provider = get_provider(agent["provider"], agent["model_name"])
            result = await provider.generate(
                prompt=prompt,
                system_prompt=agent["system_prompt"],
                temperature=agent["temperature"],
            )
            elapsed = int((time.monotonic() - start) * 1000)
            return {
                "agent_role": role,
                "preset_id": agent.get("preset_id"),
                "content": result["content"],
                "token_usage": result["token_usage"],
                "model_id": result["model_id"],
                "latency_ms": elapsed,
                "temperature": agent["temperature"],
            }
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.warning("[Creative] Agent %s failed: %s", role, e)
            return {
                "agent_role": role,
                "preset_id": agent.get("preset_id"),
                "content": "",
                "token_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "model_id": agent.get("model_name", "unknown"),
                "latency_ms": elapsed,
                "temperature": agent.get("temperature", 0.9),
                "error": str(e),
            }

    results = await asyncio.gather(*[_run_one(a) for a in agents])
    return list(results)
