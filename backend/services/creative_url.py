"""URL extraction and content fetching for Creative Engine objectives."""

from __future__ import annotations

import ipaddress
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx

from config import (
    CREATIVE_URL_FETCH_TIMEOUT,
    CREATIVE_URL_MAX_CONTENT_LENGTH,
    CREATIVE_URL_MAX_RESPONSE_BYTES,
    logger,
)

# Match URLs but require the last char to not be common trailing punctuation
_URL_RE = re.compile(r"https?://[^\s)<>\"']+[^\s)<>\"'.,;:!?]")

_BLOCKED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})  # noqa: S104


class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML-to-text converter using only stdlib."""

    _skip_tags = frozenset({"script", "style", "noscript", "head"})

    def __init__(self) -> None:
        super().__init__()
        self._pieces: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
        if tag in self._skip_tags:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._pieces.append(text)

    def get_text(self) -> str:
        return " ".join(self._pieces)


def _html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


def _is_private_url(url: str) -> bool:
    """Block requests to private/internal network addresses (SSRF prevention)."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if hostname in _BLOCKED_HOSTS:
        return True

    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_link_local
    except ValueError:
        pass

    # Block common internal TLDs
    return hostname.endswith(".local") or hostname.endswith(".internal")


def extract_urls(text: str) -> list[str]:
    """Extract HTTP/HTTPS URLs from text."""
    return _URL_RE.findall(text)


async def fetch_url_content(url: str) -> str:
    """Fetch a URL and return plain-text content (truncated to config limit).

    Returns empty string on any failure (timeout, HTTP error, SSRF block, etc.).
    """
    if _is_private_url(url):
        logger.warning("[CreativeURL] Blocked private URL: %s", url)
        return ""

    try:
        async with httpx.AsyncClient(timeout=CREATIVE_URL_FETCH_TIMEOUT) as client:
            resp = await client.get(url, follow_redirects=False)
            # Manual redirect with SSRF check
            if resp.is_redirect:
                location = resp.headers.get("location", "")
                if _is_private_url(location):
                    logger.warning("[CreativeURL] Blocked redirect to private URL: %s", location)
                    return ""
                resp = await client.get(location, follow_redirects=False)
            resp.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        logger.warning("[CreativeURL] Fetch failed for %s: %s", url, e)
        return ""

    content_type = resp.headers.get("content-type", "")
    content_length = resp.headers.get("content-length")
    if content_length and int(content_length) > CREATIVE_URL_MAX_RESPONSE_BYTES:
        logger.warning("[CreativeURL] Response too large (%s bytes): %s", content_length, url)
        return ""

    raw = resp.text[:CREATIVE_URL_MAX_RESPONSE_BYTES]

    if "html" in content_type:
        raw = _html_to_text(raw)

    return raw[:CREATIVE_URL_MAX_CONTENT_LENGTH]
