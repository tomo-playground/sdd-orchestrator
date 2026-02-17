"""Research 노드 — Memory Store 히스토리 + 소재(References) 분석.

character, topic, user, group 네임스페이스를 검색하고,
사용자가 제공한 URL/텍스트 소재를 Gemini로 분석하여
draft/debate 노드에 전달할 research_brief를 구성한다.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
from urllib.parse import urlparse

import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from config import (
    GEMINI_TEXT_MODEL,
    RESEARCH_MAX_REFERENCES,
    RESEARCH_URL_FETCH_TIMEOUT,
    RESEARCH_URL_MAX_BYTES,
    gemini_client,
    logger,
    template_env,
)
from services.agent.state import ScriptState


def _topic_key(topic: str) -> str:
    """토픽 문자열을 12자리 MD5 해시로 변환한다."""
    return hashlib.md5(topic.encode()).hexdigest()[:12]


async def _search_namespace(store: BaseStore, namespace: tuple, label: str) -> str | None:
    """네임스페이스를 검색하여 요약 문자열을 반환한다."""
    try:
        items = await store.asearch(namespace, limit=5)
        if not items:
            return None
        summaries = []
        for item in items:
            val = item.value
            if isinstance(val, dict):
                summaries.append(str(val))
        if summaries:
            return f"[{label}] " + " | ".join(summaries[:3])
    except Exception as e:
        logger.warning("[Research] %s 검색 실패: %s", label, e)
    return None


# ── References 분석 헬퍼 ────────────────────────────────────


def _is_url(text: str) -> bool:
    """http:// 또는 https://로 시작하면 URL로 판별."""
    return text.startswith("http://") or text.startswith("https://")


_PRIVATE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
]


def _is_safe_url(url: str) -> bool:
    """SSRF 방어: localhost/private IP/비표준 스킴 차단."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname or ""
        if hostname in ("localhost", ""):
            return False
        # IP 주소 직접 입력 체크
        try:
            addr = ipaddress.ip_address(hostname)
            for net in _PRIVATE_NETWORKS:
                if addr in net:
                    return False
        except ValueError:
            pass  # hostname은 도메인명 — OK
        return True
    except Exception:
        return False


_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _html_to_text(html: str) -> str:
    """간단한 HTML → 텍스트 변환."""
    text = _HTML_TAG_RE.sub("", html)
    # 연속 공백/줄바꿈 정리
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def _fetch_url(url: str) -> str | None:
    """URL에서 텍스트 콘텐츠를 가져온다."""
    if not _is_safe_url(url):
        logger.warning("[Research] 안전하지 않은 URL 차단: %s", url)
        return None
    try:
        async with httpx.AsyncClient(
            timeout=RESEARCH_URL_FETCH_TIMEOUT,
            follow_redirects=True,
            max_redirects=3,
        ) as client:
            resp = await client.get(url, headers={"User-Agent": "ShortsProducer/1.0"})
            resp.raise_for_status()
            content = resp.text[:RESEARCH_URL_MAX_BYTES]
            content_type = resp.headers.get("content-type", "")
            if "html" in content_type:
                return _html_to_text(content)
            return content
    except Exception as e:
        logger.warning("[Research] URL fetch 실패 (%s): %s", url, e)
        return None


async def _analyze_references(refs: list[str], state: ScriptState) -> str | None:
    """소재 목록을 Gemini로 분석하여 brief 문자열을 반환한다."""
    refs = refs[:RESEARCH_MAX_REFERENCES]

    # 소재 수집
    materials: list[dict[str, str]] = []
    for ref in refs:
        ref = ref.strip()
        if not ref:
            continue
        if _is_url(ref):
            content = await _fetch_url(ref)
            if content:
                materials.append({"url": ref, "content": content[:3000]})
            else:
                materials.append({"url": ref, "content": "(fetch 실패)"})
        else:
            materials.append({"url": "(직접 입력)", "content": ref[:3000]})

    if not materials:
        return None

    # Gemini 분석
    try:
        tmpl = template_env.get_template("creative/material_analyst.j2")
        prompt = tmpl.render(
            materials=materials,
            duration=state.get("duration", 30),
            structure=state.get("structure", "Monologue"),
            language=state.get("language", "Korean"),
        )

        if not gemini_client:
            logger.warning("[Research] Gemini 클라이언트 없음 — 원문 fallback")
            return _fallback_brief(materials)

        response = gemini_client.models.generate_content(
            model=GEMINI_TEXT_MODEL,
            contents=prompt,
        )
        raw = response.text or ""

        # JSON 파싱
        brief_data = _parse_gemini_json(raw)
        if brief_data and "research_brief" in brief_data:
            rb = brief_data["research_brief"]
            parts = []
            if rb.get("recommended_angle"):
                parts.append(f"추천 각도: {rb['recommended_angle']}")
            if rb.get("key_elements"):
                elems = ", ".join(rb["key_elements"][:5])
                parts.append(f"핵심 요소: {elems}")
            if rb.get("audience_hook"):
                parts.append(f"Hook: {rb['audience_hook']}")
            if parts:
                return "[소재 분석] " + " | ".join(parts)

        # JSON 파싱 실패 시 원문 텍스트 요약으로 fallback
        logger.warning("[Research] Gemini JSON 파싱 실패 — 원문 fallback")
        return _fallback_brief(materials)

    except Exception as e:
        logger.warning("[Research] Gemini 소재 분석 실패: %s — 원문 fallback", e)
        return _fallback_brief(materials)


def _parse_gemini_json(raw: str) -> dict | None:
    """Gemini 응답에서 JSON 블록을 추출하여 파싱한다."""
    # ```json ... ``` 블록 추출
    match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    text = match.group(1) if match else raw
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _fallback_brief(materials: list[dict[str, str]]) -> str:
    """Gemini 실패 시 원문 요약으로 fallback."""
    snippets = []
    for m in materials[:3]:
        content = m["content"][:200]
        snippets.append(f"- {content}")
    return "[소재 참고]\n" + "\n".join(snippets)


# ── 메인 노드 ───────────────────────────────────────────────


async def research_node(state: ScriptState, config: RunnableConfig, *, store: BaseStore) -> dict:
    """Memory Store에서 관련 히스토리를 수집하여 research_brief를 구성한다."""
    brief_parts: list[str] = []

    # 1) Character history
    char_id = state.get("character_id")
    if char_id:
        result = await _search_namespace(store, ("character", str(char_id)), "캐릭터")
        if result:
            brief_parts.append(result)

    # 2) Topic history
    topic = state.get("topic", "")
    if topic:
        topic_key = _topic_key(topic)
        result = await _search_namespace(store, ("topic", topic_key), "토픽")
        if result:
            brief_parts.append(result)

    # 3) User preferences
    result = await _search_namespace(store, ("user", "preferences"), "사용자 선호")
    if result:
        brief_parts.append(result)

    # 4) Group history
    group_id = state.get("group_id")
    if group_id:
        result = await _search_namespace(store, ("group", str(group_id)), "그룹")
        if result:
            brief_parts.append(result)

    # 5) References 소재 분석 (신규)
    refs = state.get("references") or []
    if refs:
        material_brief = await _analyze_references(refs, state)
        if material_brief:
            brief_parts.append(material_brief)

    brief = "\n".join(brief_parts) if brief_parts else None
    if brief:
        logger.info("[Research] brief 구성 완료 (%d 섹션)", len(brief_parts))
    else:
        logger.info("[Research] 저장된 히스토리 없음 — 빈 brief")

    return {"research_brief": brief}
