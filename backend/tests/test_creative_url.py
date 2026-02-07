"""Tests for URL extraction and content fetching (services/creative_url.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from services.creative_url import _is_private_url, extract_urls, fetch_url_content


def _mock_response(text: str, content_type: str = "text/plain", is_redirect: bool = False):
    """Helper to build a mock httpx response."""
    resp = AsyncMock()
    resp.status_code = 200
    resp.text = text
    resp.headers = {"content-type": content_type}
    resp.raise_for_status = lambda: None
    resp.is_redirect = is_redirect
    return resp


def _mock_client(resp):
    """Helper to build a mock httpx.AsyncClient context manager."""
    client = AsyncMock()
    client.get.return_value = resp
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


class TestExtractUrls:
    def test_single_https(self):
        assert extract_urls("Check https://example.com for details") == ["https://example.com"]

    def test_single_http(self):
        assert extract_urls("Visit http://example.com/page") == ["http://example.com/page"]

    def test_multiple_urls(self):
        text = "See https://a.com and https://b.com/page?q=1"
        result = extract_urls(text)
        assert result == ["https://a.com", "https://b.com/page?q=1"]

    def test_url_with_path_and_query(self):
        urls = extract_urls("Ref: https://example.com/path/to/page?key=val&x=1")
        assert len(urls) == 1
        assert "key=val&x=1" in urls[0]

    def test_no_urls(self):
        assert extract_urls("No links here, just text.") == []

    def test_empty_string(self):
        assert extract_urls("") == []

    def test_trailing_period_stripped(self):
        urls = extract_urls("See https://example.com/page.")
        assert urls == ["https://example.com/page"]

    def test_trailing_comma_stripped(self):
        urls = extract_urls("Check https://example.com, ok?")
        assert urls == ["https://example.com"]


class TestIsPrivateUrl:
    def test_localhost_blocked(self):
        assert _is_private_url("http://localhost:8000/admin") is True

    def test_127_blocked(self):
        assert _is_private_url("http://127.0.0.1/secret") is True

    def test_private_ip_blocked(self):
        assert _is_private_url("http://10.0.0.1/internal") is True
        assert _is_private_url("http://192.168.1.1/api") is True
        assert _is_private_url("http://172.16.0.1/data") is True

    def test_link_local_blocked(self):
        assert _is_private_url("http://169.254.169.254/latest/meta-data/") is True

    def test_public_url_allowed(self):
        assert _is_private_url("https://example.com") is False
        assert _is_private_url("https://news.ycombinator.com") is False

    def test_internal_tld_blocked(self):
        assert _is_private_url("http://myapp.local/api") is True
        assert _is_private_url("http://service.internal/health") is True


class TestFetchUrlContent:
    @pytest.mark.asyncio
    async def test_html_tag_removal(self):
        html = "<html><head><title>T</title></head><body><p>Hello</p><script>bad();</script><p>World</p></body></html>"
        resp = _mock_response(html, "text/html; charset=utf-8")
        client = _mock_client(resp)

        with patch("services.creative_url.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = client
            result = await fetch_url_content("https://example.com")

        assert "Hello" in result
        assert "World" in result
        assert "<p>" not in result
        assert "bad();" not in result

    @pytest.mark.asyncio
    async def test_plain_text_passthrough(self):
        resp = _mock_response("Plain text content")
        client = _mock_client(resp)

        with patch("services.creative_url.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = client
            result = await fetch_url_content("https://example.com/text")

        assert result == "Plain text content"

    @pytest.mark.asyncio
    async def test_truncates_long_content(self):
        resp = _mock_response("A" * 10000)
        client = _mock_client(resp)

        with patch("services.creative_url.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = client
            result = await fetch_url_content("https://example.com/long")

        assert len(result) == 5000

    @pytest.mark.asyncio
    async def test_timeout_returns_empty(self):
        client = AsyncMock()
        client.get.side_effect = httpx.TimeoutException("timeout")
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.creative_url.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = client
            result = await fetch_url_content("https://example.com/slow")

        assert result == ""

    @pytest.mark.asyncio
    async def test_http_error_returns_empty(self):
        client = AsyncMock()
        client.get.side_effect = httpx.HTTPStatusError("404", request=AsyncMock(), response=AsyncMock())
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("services.creative_url.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = client
            result = await fetch_url_content("https://example.com/404")

        assert result == ""

    @pytest.mark.asyncio
    async def test_private_url_blocked(self):
        """SSRF: private/internal URLs return empty without making HTTP request."""
        result = await fetch_url_content("http://169.254.169.254/latest/meta-data/")
        assert result == ""

    @pytest.mark.asyncio
    async def test_localhost_blocked(self):
        result = await fetch_url_content("http://localhost:8000/admin")
        assert result == ""

    @pytest.mark.asyncio
    async def test_redirect_to_private_blocked(self):
        """SSRF: redirect to internal IP is blocked."""
        redirect_resp = AsyncMock()
        redirect_resp.is_redirect = True
        redirect_resp.headers = {"location": "http://169.254.169.254/latest/meta-data/"}

        client = _mock_client(redirect_resp)

        with patch("services.creative_url.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = client
            result = await fetch_url_content("https://evil.com/redirect")

        assert result == ""
        # Should NOT have made a second GET to the private URL
        assert client.get.call_count == 1


class TestBuildInstruction:
    """Test _build_instruction with url_content in context."""

    def test_url_content_wrapped_in_reference_tags(self):
        from services.creative_engine import _build_instruction

        session = AsyncMock()
        session.task_type = "scenario"
        session.objective = "Write about https://example.com"
        session.max_rounds = 3
        session.context = {
            "url_content": {"https://example.com": "Example page content"},
        }

        result = _build_instruction(session, round_number=1)

        assert '<reference url="https://example.com">' in result
        assert "Example page content" in result
        assert "</reference>" in result

    def test_url_content_with_other_context(self):
        from services.creative_engine import _build_instruction

        session = AsyncMock()
        session.task_type = "scenario"
        session.objective = "Test"
        session.max_rounds = 3
        session.context = {
            "url_content": {"https://a.com": "Content A"},
            "character": "hero",
        }

        result = _build_instruction(session, round_number=1)

        assert '<reference url="https://a.com">' in result
        assert "Content A" in result
        assert "Context:" in result
        assert "'character': 'hero'" in result
        # url_content should NOT appear in Context line
        assert "url_content" not in result.split("Context:")[-1]

    def test_no_url_content(self):
        from services.creative_engine import _build_instruction

        session = AsyncMock()
        session.task_type = "scenario"
        session.objective = "Plain objective"
        session.max_rounds = 3
        session.context = {"key": "value"}

        result = _build_instruction(session, round_number=1)

        assert "<reference" not in result
        assert "Context:" in result
