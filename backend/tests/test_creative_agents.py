"""TDD tests for Creative Engine agents -- LLM provider abstraction layer.

These tests define the expected interface for services/creative_agents.py
which does NOT exist yet. Implementation should satisfy these tests.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


def _make_agent_list() -> list[dict]:
    """Build a 3-agent config list reused across parallel-execution tests."""
    return [
        {
            "role": "storyteller",
            "preset_id": 1,
            "provider": "gemini",
            "model_name": "gemini-2.0-flash",
            "system_prompt": "You are a storyteller.",
            "temperature": 0.9,
        },
        {
            "role": "critic",
            "preset_id": 2,
            "provider": "ollama",
            "model_name": "exaone3.5:7.8b",
            "system_prompt": "You are a critic.",
            "temperature": 0.3,
        },
        {
            "role": "editor",
            "preset_id": 3,
            "provider": "gemini",
            "model_name": "gemini-2.0-flash",
            "system_prompt": "You are an editor.",
            "temperature": 0.5,
        },
    ]


def _make_ollama_async_client(post_side_effect=None, get_side_effect=None):
    """Build a mock httpx.AsyncClient for Ollama tests (context-manager safe)."""
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    if post_side_effect is not None:
        mock_client.post = AsyncMock(side_effect=post_side_effect)
    if get_side_effect is not None:
        mock_client.get = AsyncMock(side_effect=get_side_effect)
    return mock_client


# ---------------------------------------------------------------------------
# 1. GeminiProvider
# ---------------------------------------------------------------------------
class TestGeminiProvider:
    """GeminiProvider wraps services.llm.GeminiProvider for text generation."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Successful Gemini call returns content + token_usage + model_id."""
        mock_llm_response = MagicMock()
        mock_llm_response.text = "Once upon a time..."
        mock_llm_response.usage = {"input": 10, "output": 25, "total": 35}

        mock_inner_provider = AsyncMock()
        mock_inner_provider.generate = AsyncMock(return_value=mock_llm_response)

        with patch("services.creative_agents._get_llm_provider", return_value=mock_inner_provider):
            from services.creative_agents import GeminiProvider

            provider = GeminiProvider(model_name="gemini-2.0-flash", api_key="fake-key")
            result = await provider.generate(
                prompt="Write a story",
                system_prompt="You are a storyteller.",
                temperature=0.9,
            )

        assert result["content"] == "Once upon a time..."
        assert result["token_usage"] == {"prompt_tokens": 10, "completion_tokens": 25, "total_tokens": 35}
        assert result["model_id"] == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_generate_api_error_raises_runtime_error(self):
        """Gemini API failure is wrapped in RuntimeError."""
        mock_inner_provider = AsyncMock()
        mock_inner_provider.generate = AsyncMock(side_effect=Exception("quota exceeded"))

        with patch("services.creative_agents._get_llm_provider", return_value=mock_inner_provider):
            from services.creative_agents import GeminiProvider

            provider = GeminiProvider(model_name="gemini-2.0-flash", api_key="fake-key")
            with pytest.raises(RuntimeError, match="Gemini"):
                await provider.generate(
                    prompt="Write a story",
                    system_prompt="You are a storyteller.",
                    temperature=0.9,
                )


# ---------------------------------------------------------------------------
# 2. OllamaProvider
# ---------------------------------------------------------------------------
class TestOllamaProvider:
    """OllamaProvider calls Ollama REST API via httpx."""

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """Successful Ollama /api/generate returns content + token_usage + model_id."""
        ollama_json = {
            "response": "The hero set out on a journey.",
            "model": "exaone3.5:7.8b",
            "prompt_eval_count": 15,
            "eval_count": 30,
        }
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = ollama_json
        mock_resp.raise_for_status = MagicMock()

        mock_client = _make_ollama_async_client()
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("services.creative_agents.httpx.AsyncClient", return_value=mock_client):
            from services.creative_agents import OllamaProvider

            provider = OllamaProvider(model_name="exaone3.5:7.8b")
            result = await provider.generate(
                prompt="Write a story",
                system_prompt="You are a storyteller.",
                temperature=0.7,
            )

        assert result["content"] == "The hero set out on a journey."
        assert result["token_usage"] == {"prompt_tokens": 15, "completion_tokens": 30, "total_tokens": 45}
        assert result["model_id"] == "exaone3.5:7.8b"

    @pytest.mark.asyncio
    async def test_generate_connection_error_raises_runtime_error(self):
        """Ollama down (connection refused) is wrapped in RuntimeError."""
        mock_client = _make_ollama_async_client(
            post_side_effect=httpx.ConnectError("Connection refused"),
        )
        with patch("services.creative_agents.httpx.AsyncClient", return_value=mock_client):
            from services.creative_agents import OllamaProvider

            provider = OllamaProvider(model_name="exaone3.5:7.8b")
            with pytest.raises(RuntimeError, match="Ollama"):
                await provider.generate(
                    prompt="Write a story",
                    system_prompt="You are a storyteller.",
                    temperature=0.7,
                )

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """health_check returns True when Ollama /api/version responds 200."""
        mock_resp = MagicMock(status_code=200)
        mock_client = _make_ollama_async_client()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("services.creative_agents.httpx.AsyncClient", return_value=mock_client):
            from services.creative_agents import OllamaProvider

            assert await OllamaProvider(model_name="exaone3.5:7.8b").health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """health_check returns False when Ollama is unreachable."""
        mock_client = _make_ollama_async_client(
            get_side_effect=httpx.ConnectError("Connection refused"),
        )
        with patch("services.creative_agents.httpx.AsyncClient", return_value=mock_client):
            from services.creative_agents import OllamaProvider

            assert await OllamaProvider(model_name="exaone3.5:7.8b").health_check() is False


# ---------------------------------------------------------------------------
# 3. get_provider factory
# ---------------------------------------------------------------------------
class TestGetProvider:
    """get_provider() returns the correct LLMProvider by name."""

    def test_gemini_provider(self):
        """'gemini' returns GeminiProvider instance."""
        from services.creative_agents import GeminiProvider, get_provider

        assert isinstance(get_provider("gemini", "gemini-2.0-flash"), GeminiProvider)

    def test_ollama_provider(self):
        """'ollama' returns OllamaProvider instance."""
        from services.creative_agents import OllamaProvider, get_provider

        assert isinstance(get_provider("ollama", "exaone3.5:7.8b"), OllamaProvider)

    def test_unknown_provider_raises_value_error(self):
        """Unknown provider name raises ValueError."""
        from services.creative_agents import get_provider

        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("openai", "gpt-4")


# ---------------------------------------------------------------------------
# 4. generate_parallel
# ---------------------------------------------------------------------------
class TestGenerateParallel:
    """generate_parallel() runs multiple agents concurrently."""

    @pytest.mark.asyncio
    async def test_three_agents_three_results(self):
        """3 agents produce 3 result dicts with content."""
        fake_result = {
            "content": "Generated text",
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "model_id": "mock-model",
        }
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value=fake_result)

        with patch("services.creative_agents.get_provider", return_value=mock_provider):
            from services.creative_agents import generate_parallel

            results = await generate_parallel(agents=_make_agent_list(), objective="Write a short story")

        assert len(results) == 3
        for r in results:
            assert r["agent_role"] in {"storyteller", "critic", "editor"}
            assert r["content"] == "Generated text"
            assert "token_usage" in r

    @pytest.mark.asyncio
    async def test_partial_failure_returns_error_for_failed_agent(self):
        """1 agent fails, other 2 succeed -- failed agent gets error dict."""
        ok_result = {
            "content": "Good text",
            "token_usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            "model_id": "mock",
        }
        call_count = 0

        async def _mock_generate(prompt, system_prompt, temperature):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Ollama connection refused")
            return ok_result

        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(side_effect=_mock_generate)

        with patch("services.creative_agents.get_provider", return_value=mock_provider):
            from services.creative_agents import generate_parallel

            results = await generate_parallel(agents=_make_agent_list(), objective="Write a short story")

        assert len(results) == 3
        error_results = [r for r in results if "error" in r]
        success_results = [r for r in results if "error" not in r]
        assert len(success_results) == 2
        assert len(error_results) == 1
        assert "Ollama" in error_results[0]["error"]
