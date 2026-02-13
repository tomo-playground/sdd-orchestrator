"""Creative Lab — Material Collection Agent.

Fetches user-provided URLs, extracts text content, and sends to Gemini
for analysis. Produces a structured research_brief for Architects.
"""

from __future__ import annotations

import asyncio
import json
import re
import time

import httpx
from jinja2 import Environment, FileSystemLoader

from config import (
    BASE_DIR,
    CREATIVE_AGENT_TEMPLATES,
    CREATIVE_LEADER_MODEL,
    CREATIVE_URL_FETCH_TIMEOUT,
    CREATIVE_URL_MAX_CONTENT_LENGTH,
    CREATIVE_URL_MAX_FETCH_COUNT,
    CREATIVE_URL_MAX_RESPONSE_BYTES,
    logger,
)
from models.creative import CreativeSession
from services.creative_agents import get_provider
from services.creative_utils import get_next_sequence, load_preset, parse_json_response, record_trace_sync

_template_env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")))

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_BLOCKED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "[::1]"})  # noqa: S104


def _is_safe_url(url: str) -> bool:
    """Block private IPs and internal hosts to prevent SSRF."""
    from ipaddress import ip_address
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname or ""
    if hostname in _BLOCKED_HOSTS:
        return False
    try:
        ip = ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    except ValueError:
        pass  # Not an IP literal, allow domain names
    return True


# ── URL Fetching ──────────────────────────────────────────────


async def _fetch_url(url: str) -> str | None:
    """Fetch a single URL and extract text content."""
    if not _is_safe_url(url):
        logger.warning("[Material] Blocked unsafe URL: %s", url)
        return None
    try:
        async with httpx.AsyncClient(
            timeout=CREATIVE_URL_FETCH_TIMEOUT,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=5),
        ) as client:
            resp = await client.get(url, headers={"User-Agent": "ShortsProducer/1.0"})
            resp.raise_for_status()

            content_length = int(resp.headers.get("content-length", 0))
            if content_length > CREATIVE_URL_MAX_RESPONSE_BYTES:
                logger.warning("[Material] URL too large (%d bytes): %s", content_length, url)
                return None

            raw = resp.text
            text = _strip_html(raw)
            if len(text) > CREATIVE_URL_MAX_CONTENT_LENGTH:
                text = text[:CREATIVE_URL_MAX_CONTENT_LENGTH] + "..."
            return text
    except Exception as e:
        logger.warning("[Material] Failed to fetch %s: %s", url, e)
        return None


def _strip_html(html: str) -> str:
    """Remove HTML tags and normalize whitespace."""
    text = _HTML_TAG_RE.sub(" ", html)
    return _WHITESPACE_RE.sub(" ", text).strip()


async def fetch_materials(urls: list[str]) -> list[dict]:
    """Fetch multiple URLs and return list of {url, content} dicts."""
    urls_to_fetch = urls[:CREATIVE_URL_MAX_FETCH_COUNT]
    tasks = [_fetch_url(url) for url in urls_to_fetch]
    results = await asyncio.gather(*tasks)

    materials = []
    for url, content in zip(urls_to_fetch, results, strict=True):
        if content:
            materials.append({"url": url, "content": content})
            logger.info("[Material] Fetched %s (%d chars)", url, len(content))
        else:
            logger.warning("[Material] Skipped %s (fetch failed)", url)
    return materials


# ── Gemini Analysis ───────────────────────────────────────────


async def analyze_materials(
    db,
    session: CreativeSession,
    materials: list[dict],
    *,
    duration: int,
    structure: str,
    language: str,
) -> dict | None:
    """Send fetched materials to Gemini for analysis. Returns research_brief."""
    template = _template_env.get_template(CREATIVE_AGENT_TEMPLATES["material_analyst"])
    prompt = template.render(
        materials=materials,
        duration=duration,
        structure=structure,
        language=language,
    )

    preset = load_preset(db, "material_analyst")
    sys_prompt = (
        preset.system_prompt
        if preset
        else "You are a Material Analyst. Analyze source materials and produce a research brief. Respond only in valid JSON."
    )
    temp = preset.temperature if preset else 0.5

    provider = get_provider("gemini", CREATIVE_LEADER_MODEL)
    start = time.monotonic()
    try:
        result = await provider.generate(
            prompt=prompt,
            system_prompt=sys_prompt,
            temperature=temp,
        )
    except Exception as e:
        logger.warning("[Material] Analysis failed: %s", e)
        return None
    elapsed_ms = int((time.monotonic() - start) * 1000)

    seq = get_next_sequence(db, session.id)
    record_trace_sync(
        db,
        session_id=session.id,
        round_number=0,
        sequence=seq,
        trace_type="generation",
        agent_role="material_analyst",
        agent_preset_id=preset.id if preset else None,
        input_prompt=prompt,
        output_content=result["content"],
        model_id=result["model_id"],
        token_usage=result["token_usage"],
        latency_ms=elapsed_ms,
        temperature=temp,
        phase="material",
        step_name="material_analyst",
    )

    try:
        parsed = parse_json_response(result["content"])
        return parsed.get("research_brief")
    except (json.JSONDecodeError, KeyError):
        logger.warning("[Material] JSON parse failed")
        return None


# ── Orchestrator ──────────────────────────────────────────────


async def run_material_agent(
    db,
    session: CreativeSession,
    urls: list[str],
    *,
    duration: int,
    structure: str,
    language: str,
) -> dict | None:
    """Full pipeline: fetch URLs → analyze → return research_brief."""
    materials = await fetch_materials(urls)
    if not materials:
        logger.info("[Material] No materials fetched, skipping analysis")
        return None

    return await analyze_materials(
        db,
        session,
        materials,
        duration=duration,
        structure=structure,
        language=language,
    )
