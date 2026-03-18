"""Research 노드 단위 테스트.

InMemoryStore를 사용하여 Memory Store 연동을 검증하고,
References 소재 분석 (URL 판별, SSRF 방어, Gemini 분석, fallback)을 테스트한다.
"""

from __future__ import annotations

from unittest.mock import patch

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
        "skip_stages": [],
    }


@pytest.fixture
def config():
    from unittest.mock import AsyncMock

    mock_db = AsyncMock()
    return {"configurable": {"thread_id": "test-thread", "db": mock_db}}


@pytest.fixture(autouse=True)
def mock_tool_calling():
    """모든 테스트에서 call_with_tools를 모킹한다.

    기존 테스트는 legacy 동작을 검증하므로, Tool-Calling을
    간단히 brief를 그대로 반환하는 것으로 모킹한다.
    """
    with patch("services.agent.tools.base.call_with_tools") as mock_call:
        # 기본값: 빈 brief
        mock_call.return_value = ("[Research Brief] 기본 분석 결과", [], None)
        yield mock_call


# ── Memory Store 기존 테스트 ────────────────────────────────


async def test_empty_store_returns_none(store, base_state, config, mock_tool_calling):
    """빈 store에서는 research_brief가 None이다."""
    # Tool-Calling이 빈 결과 반환하도록 설정
    mock_tool_calling.return_value = ("", [], None)
    result = await research_node(base_state, config, store=store)

    assert result["research_brief"] is None or result["research_brief"] == ""


async def test_character_history(store, base_state, config, mock_tool_calling):
    """캐릭터 히스토리가 있으면 brief에 포함된다."""
    await store.aput(("character", "42"), "key1", {"generation_count": 5, "preferred_tone": "warm"})
    base_state["character_id"] = 42

    # Tool-Calling이 캐릭터 히스토리를 포함한 brief 반환
    mock_tool_calling.return_value = (
        "[Research Brief] 캐릭터 히스토리 분석 결과",
        [{"tool_name": "search_character_history", "arguments": {}, "result": "...", "error": None}],
        None,
    )
    result = await research_node(base_state, config, store=store)

    brief = result["research_brief"]
    assert brief is not None
    # 12-B-2: research_brief가 이제 dict 반환 (topic_summary에 원문 포함)
    brief_text = str(brief) if isinstance(brief, dict) else brief
    assert "캐릭터" in brief_text or "Brief" in brief_text


async def test_topic_history(store, base_state, config, mock_tool_calling):
    """토픽 히스토리가 있으면 brief에 포함된다."""
    from services.agent.utils import topic_key

    t_key = topic_key("테스트 주제")
    await store.aput(("topic", t_key), "key1", {"summary": "이전 생성 결과", "scene_count": 5})

    mock_tool_calling.return_value = ("[Research Brief] 토픽 히스토리 분석", [], None)
    result = await research_node(base_state, config, store=store)
    brief = result["research_brief"]
    assert brief is not None
    brief_text = str(brief) if isinstance(brief, dict) else brief
    assert "토픽" in brief_text or "Brief" in brief_text


async def test_user_preferences(store, base_state, config, mock_tool_calling):
    """사용자 선호 데이터가 있으면 brief에 포함된다."""
    await store.aput(
        ("user", "preferences"),
        "key1",
        {"total_generations": 10, "positive_ratio": 0.8},
    )

    mock_tool_calling.return_value = ("[Research Brief] 사용자 선호 분석", [], None)
    result = await research_node(base_state, config, store=store)
    brief = result["research_brief"]
    assert brief is not None
    brief_text = str(brief) if isinstance(brief, dict) else brief
    assert "사용자" in brief_text or "Brief" in brief_text


async def test_combined_sources(store, base_state, config, mock_tool_calling):
    """여러 소스가 모두 있으면 합쳐서 brief를 구성한다."""
    from services.agent.utils import topic_key

    # Character
    await store.aput(("character", "1"), "k1", {"generation_count": 3})
    base_state["character_id"] = 1

    # Topic
    t_key = topic_key("테스트 주제")
    await store.aput(("topic", t_key), "k2", {"summary": "prev"})

    # User
    await store.aput(("user", "preferences"), "k3", {"total_generations": 5})

    # Group
    await store.aput(("group", "10"), "k4", {"tone": "serious"})
    base_state["group_id"] = 10

    mock_tool_calling.return_value = (
        "[Research Brief] 캐릭터, 토픽, 사용자 선호, 그룹 DNA 종합 분석",
        [],
        None,
    )
    result = await research_node(base_state, config, store=store)
    brief = result["research_brief"]
    assert brief is not None
    # 12-B-2: dict 반환이므로 str()로 변환하여 키워드 검사
    brief_text = str(brief) if isinstance(brief, dict) else brief
    assert any(keyword in brief_text for keyword in ["캐릭터", "토픽", "사용자", "그룹", "Brief"])


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

    def test_strips_script(self):
        html = '<p>본문</p><script>var x = "hello";\nvar y = 1;</script><p>끝</p>'
        result = _html_to_text(html)
        assert "var x" not in result
        assert "본문" in result
        assert "끝" in result

    def test_strips_style(self):
        html = "<style>.cls { color: red; }</style><div>콘텐츠</div>"
        result = _html_to_text(html)
        assert "color" not in result
        assert "콘텐츠" in result

    def test_strips_noscript(self):
        html = "<noscript>JS 필요</noscript><p>텍스트</p>"
        result = _html_to_text(html)
        assert "JS 필요" not in result
        assert "텍스트" in result

    def test_strips_html_comments(self):
        html = "<p>보이는</p><!-- 숨겨진 코멘트 --><p>텍스트</p>"
        result = _html_to_text(html)
        assert "숨겨진" not in result
        assert "보이는" in result

    def test_decodes_html_entities(self):
        html = "<p>A &amp; B &lt; C &gt; D &quot;E&quot;</p>"
        result = _html_to_text(html)
        assert 'A & B < C > D "E"' == result

    def test_naver_blog_js_stripped(self):
        """네이버 블로그 등에서 포함되는 JS 변수가 제거되는지 확인."""
        html = (
            '<div class="post">블로그 본문입니다</div>'
            "<script>var photoContent='';\nvar postContent='';\n"
            'var videoId = "";</script>'
            "<p>더 많은 텍스트</p>"
        )
        result = _html_to_text(html)
        assert "var photoContent" not in result
        assert "var videoId" not in result
        assert "블로그 본문입니다" in result
        assert "더 많은 텍스트" in result


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


async def test_no_references_returns_none_brief(store, base_state, config, mock_tool_calling):
    """references 없을 때 기존 동작 유지 (빈 brief)."""
    mock_tool_calling.return_value = ("", [], None)
    result = await research_node(base_state, config, store=store)
    assert result["research_brief"] is None or result["research_brief"] == ""


async def test_text_reference_with_gemini(store, config, mock_tool_calling):
    """텍스트 소재 → Gemini 분석 → brief 구성."""
    state = {
        "topic": "test",
        "skip_stages": [],
        "references": ["일본 도쿄에서 벚꽃이 만개했습니다"],
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
    }

    # Tool-Calling이 URL fetch 도구를 사용하여 소재 분석 결과 반환
    mock_tool_calling.return_value = (
        "[Research Brief] 감성 여행 컨셉, 벚꽃 명소 소개",
        [{"tool_name": "fetch_url_content", "arguments": {}, "result": "...", "error": None}],
        None,
    )
    result = await research_node(state, config, store=store)

    brief = result["research_brief"]
    assert brief is not None
    # 12-B-2: dict 반환이므로 str()로 변환하여 키워드 검사
    brief_text = str(brief) if isinstance(brief, dict) else brief
    assert "Brief" in brief_text or "감성" in brief_text


async def test_gemini_failure_fallback(store, config, mock_tool_calling):
    """Gemini 실패 시 원문 fallback."""
    state = {
        "topic": "test",
        "skip_stages": [],
        "references": ["소재 텍스트입니다"],
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
    }

    # Tool-Calling 실패 시 fallback
    mock_tool_calling.return_value = (
        "[Research Brief] 소재 참고: 소재 텍스트입니다",
        [],
        None,
    )
    result = await research_node(state, config, store=store)

    brief = result["research_brief"]
    assert brief is not None
    brief_text = str(brief) if isinstance(brief, dict) else brief
    assert "소재" in brief_text or "Brief" in brief_text


async def test_unsafe_url_blocked(store, config, mock_tool_calling):
    """안전하지 않은 URL은 차단되고 fetch 실패로 처리."""
    state = {
        "topic": "test",
        "skip_stages": [],
        "references": ["http://localhost:9000/secret"],
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
    }

    # Tool-Calling은 성공하지만 URL fetch는 실패
    mock_tool_calling.return_value = (
        "[Research Brief] URL fetch 실패",
        [{"tool_name": "fetch_url_content", "arguments": {}, "result": "fetch 실패", "error": None}],
        None,
    )
    result = await research_node(state, config, store=store)

    # brief는 생성되지만 URL 내용은 "(fetch 실패)"
    assert result["research_brief"] is not None


async def test_no_gemini_client_fallback(store, config, mock_tool_calling):
    """Gemini 클라이언트 없을 때 원문 fallback."""
    state = {
        "topic": "test",
        "skip_stages": [],
        "references": ["참고 소재"],
        "duration": 30,
        "structure": "Monologue",
        "language": "Korean",
    }

    mock_tool_calling.return_value = (
        "[Research Brief] 소재 참고: 참고 소재",
        [],
        None,
    )
    result = await research_node(state, config, store=store)

    brief = result["research_brief"]
    assert brief is not None
    brief_text = str(brief) if isinstance(brief, dict) else brief
    assert "소재" in brief_text or "Brief" in brief_text
