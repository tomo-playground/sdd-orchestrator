"""Research 노드 단위 테스트.

InMemoryStore를 사용하여 Memory Store 연동을 검증하고,
References 소재 분석 (URL 판별, SSRF 방어, Gemini 분석, fallback)을 테스트한다.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langgraph.store.memory import InMemoryStore

from services.agent.nodes.research import (
    _fallback_brief,
    _html_to_text,
    _is_safe_url,
    _is_url,
    _parse_gemini_json,
    research_node,
)


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def base_state():
    return {
        "topic": "테스트 주제",
        "character_id": None,
        "group_id": None,
        "mode": "full",
    }


@pytest.fixture
def config():
    return {"configurable": {"thread_id": "test-thread"}}


# ── Memory Store 기존 테스트 ────────────────────────────────


async def test_empty_store_returns_none(store, base_state, config):
    """빈 store에서는 research_brief가 None이다."""
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is None


async def test_character_history(store, base_state, config):
    """캐릭터 히스토리가 있으면 brief에 포함된다."""
    await store.aput(("character", "42"), "key1", {"generation_count": 5, "preferred_tone": "warm"})
    base_state["character_id"] = 42
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is not None
    assert "캐릭터" in result["research_brief"]


async def test_topic_history(store, base_state, config):
    """토픽 히스토리가 있으면 brief에 포함된다."""
    from services.agent.nodes.research import _topic_key

    topic_key = _topic_key("테스트 주제")
    await store.aput(("topic", topic_key), "key1", {"summary": "이전 생성 결과", "scene_count": 5})
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is not None
    assert "토픽" in result["research_brief"]


async def test_user_preferences(store, base_state, config):
    """사용자 선호 데이터가 있으면 brief에 포함된다."""
    await store.aput(
        ("user", "preferences"),
        "key1",
        {"total_generations": 10, "positive_ratio": 0.8},
    )
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is not None
    assert "사용자 선호" in result["research_brief"]


async def test_combined_sources(store, base_state, config):
    """여러 소스가 모두 있으면 합쳐서 brief를 구성한다."""
    from services.agent.nodes.research import _topic_key

    # Character
    await store.aput(("character", "1"), "k1", {"generation_count": 3})
    base_state["character_id"] = 1

    # Topic
    topic_key = _topic_key("테스트 주제")
    await store.aput(("topic", topic_key), "k2", {"summary": "prev"})

    # User
    await store.aput(("user", "preferences"), "k3", {"total_generations": 5})

    # Group
    await store.aput(("group", "10"), "k4", {"tone": "serious"})
    base_state["group_id"] = 10

    result = await research_node(base_state, config, store=store)
    brief = result["research_brief"]
    assert brief is not None
    assert "캐릭터" in brief
    assert "토픽" in brief
    assert "사용자 선호" in brief
    assert "그룹" in brief


# ── _is_url ────────────────────────────────────────────────


class TestIsUrl:
    def test_http(self):
        assert _is_url("http://example.com") is True

    def test_https(self):
        assert _is_url("https://example.com/path") is True

    def test_plain_text(self):
        assert _is_url("그냥 텍스트 소재") is False

    def test_ftp(self):
        assert _is_url("ftp://example.com") is False

    def test_empty(self):
        assert _is_url("") is False


# ── _is_safe_url (SSRF 방어) ──────────────────────────────


class TestIsSafeUrl:
    def test_public_url(self):
        assert _is_safe_url("https://example.com/article") is True

    def test_localhost(self):
        assert _is_safe_url("http://localhost:8000/api") is False

    def test_127(self):
        assert _is_safe_url("http://127.0.0.1:9000/data") is False

    def test_private_10(self):
        assert _is_safe_url("http://10.0.0.1/internal") is False

    def test_private_172(self):
        assert _is_safe_url("http://172.16.0.1/internal") is False

    def test_private_192(self):
        assert _is_safe_url("http://192.168.1.1/internal") is False

    def test_link_local(self):
        assert _is_safe_url("http://169.254.169.254/metadata") is False

    def test_zero(self):
        assert _is_safe_url("http://0.0.0.0/") is False

    def test_non_http_scheme(self):
        assert _is_safe_url("file:///etc/passwd") is False

    def test_empty(self):
        assert _is_safe_url("") is False


# ── _html_to_text ──────────────────────────────────────────


class TestHtmlToText:
    def test_strips_tags(self):
        html = "<p>Hello <b>World</b></p>"
        assert _html_to_text(html) == "Hello World"

    def test_collapses_newlines(self):
        html = "line1\n\n\n\n\nline2"
        assert _html_to_text(html) == "line1\n\nline2"


# ── _parse_gemini_json ─────────────────────────────────────


class TestParseGeminiJson:
    def test_json_block(self):
        raw = 'Some text\n```json\n{"key": "value"}\n```\nMore text'
        result = _parse_gemini_json(raw)
        assert result == {"key": "value"}

    def test_plain_json(self):
        raw = '{"key": "value"}'
        result = _parse_gemini_json(raw)
        assert result == {"key": "value"}

    def test_invalid(self):
        raw = "This is not JSON"
        assert _parse_gemini_json(raw) is None


# ── _fallback_brief ────────────────────────────────────────


class TestFallbackBrief:
    def test_basic(self):
        materials = [{"url": "http://x.com", "content": "Hello world"}]
        result = _fallback_brief(materials)
        assert "[소재 참고]" in result
        assert "Hello world" in result

    def test_truncates(self):
        materials = [{"url": "(직접 입력)", "content": "A" * 300}]
        result = _fallback_brief(materials)
        # "- " prefix + 200 chars max
        lines = result.split("\n")
        assert len(lines[1]) <= 202


# ── research_node + References 통합 ────────────────────────


async def test_no_references_returns_none_brief(store, base_state, config):
    """references 없을 때 기존 동작 유지 (빈 brief)."""
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is None


async def test_text_reference_with_gemini(store, config):
    """텍스트 소재 → Gemini 분석 → brief 구성."""
    state = {
        "topic": "test",
        "mode": "full",
        "references": ["일본 도쿄에서 벚꽃이 만개했습니다"],
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
    }

    mock_response = MagicMock()
    mock_response.text = (
        '```json\n{"research_brief": {"recommended_angle": "감성 여행",'
        ' "key_elements": ["벚꽃", "도쿄"], "audience_hook": "올해 최고의 벚꽃 명소"}}\n```'
    )

    with patch("services.agent.nodes.research.gemini_client") as mock_client:
        mock_client.models.generate_content.return_value = mock_response
        result = await research_node(state, config, store=store)

    brief = result["research_brief"]
    assert brief is not None
    assert "소재 분석" in brief
    assert "감성 여행" in brief


async def test_gemini_failure_fallback(store, config):
    """Gemini 실패 시 원문 fallback."""
    state = {
        "topic": "test",
        "mode": "full",
        "references": ["소재 텍스트입니다"],
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
    }

    with patch("services.agent.nodes.research.gemini_client") as mock_client:
        mock_client.models.generate_content.side_effect = Exception("API Error")
        result = await research_node(state, config, store=store)

    brief = result["research_brief"]
    assert brief is not None
    assert "소재 참고" in brief
    assert "소재 텍스트입니다" in brief


async def test_unsafe_url_blocked(store, config):
    """안전하지 않은 URL은 차단되고 fetch 실패로 처리."""
    state = {
        "topic": "test",
        "mode": "full",
        "references": ["http://localhost:9000/secret"],
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
    }

    with patch("services.agent.nodes.research.gemini_client") as mock_client:
        mock_response = MagicMock()
        mock_response.text = '{"research_brief": {"recommended_angle": "x", "key_elements": [], "audience_hook": "y"}}'
        mock_client.models.generate_content.return_value = mock_response
        result = await research_node(state, config, store=store)

    # brief는 생성되지만 URL 내용은 "(fetch 실패)"
    assert result["research_brief"] is not None


async def test_no_gemini_client_fallback(store, config):
    """Gemini 클라이언트 없을 때 원문 fallback."""
    state = {
        "topic": "test",
        "mode": "full",
        "references": ["참고 소재"],
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
    }

    with patch("services.agent.nodes.research.gemini_client", None):
        result = await research_node(state, config, store=store)

    brief = result["research_brief"]
    assert brief is not None
    assert "소재 참고" in brief
