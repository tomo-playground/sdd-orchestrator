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
from services.agent.observability import trace_llm_call  # noqa: E402
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

        async with trace_llm_call(name="research_analyze_references", input_text=prompt[:2000]) as llm:
            response = await gemini_client.aio.models.generate_content(
                model=GEMINI_TEXT_MODEL,
                contents=prompt,
            )
            llm.record(response)
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
    """Tool-Calling Agent로 research brief를 구성한다.

    LLM이 주제를 분석하여 필요한 정보원만 선택적으로 호출한다.
    """
    from ..tools.base import call_with_tools
    from ..tools.research_tools import create_research_executors, get_research_tools

    # DB 세션 추출
    db_session = config.get("configurable", {}).get("db") if config else None
    if not db_session:
        logger.warning("[Research] DB 세션 없음 — Tool-Calling 불가, 빈 brief 반환")
        return {"research_brief": None, "research_tool_logs": []}

    # 도구 및 실행 함수 준비
    tools = get_research_tools()
    executors = create_research_executors(store, db_session, state)

    # LLM에게 전달할 초기 프롬프트
    topic = state.get("topic", "")
    description = state.get("description", "")
    character_id = state.get("character_id")
    group_id = state.get("group_id")
    language = state.get("language", "Korean")
    references = state.get("references") or []

    prompt_parts = [
        "당신은 쇼츠 대본 작성을 위한 Research Agent입니다.",
        f"주제: {topic}",
    ]
    if description:
        prompt_parts.append(f"설명: {description}")
    if character_id:
        prompt_parts.append(f"캐릭터 ID: {character_id}")
    if group_id:
        prompt_parts.append(f"그룹 ID: {group_id}")
    if language:
        prompt_parts.append(f"언어: {language}")
    if references:
        prompt_parts.append(f"사용자 제공 소재: {', '.join(references[:3])}")

    prompt_parts.append("")
    prompt_parts.append("목표: 이 주제에 대한 최적의 대본 작성을 위해 필요한 정보를 수집하세요.")
    prompt_parts.append("사용 가능한 도구를 활용하여 필요한 정보만 선택적으로 수집합니다.")
    prompt_parts.append("")
    prompt_parts.append("도구 사용 가이드:")
    prompt_parts.append("- 새 주제이거나 과거 이력이 없을 것 같으면 히스토리 검색을 스킵하세요.")
    prompt_parts.append("- 사용자가 URL을 제공했을 때만 fetch_url_content를 호출하세요.")
    prompt_parts.append("- 트렌딩 분석은 최신 이슈/인기 주제일 때만 유용합니다.")
    prompt_parts.append("- 그룹 ID가 있고 채널 톤/세계관이 중요하다면 get_group_dna를 호출하세요.")
    prompt_parts.append("")
    prompt_parts.append("수집한 정보를 바탕으로 대본 작성에 도움이 되는 research brief를 작성하세요.")

    prompt = "\n".join(prompt_parts)

    # Tool-Calling 실행
    try:
        logger.info("[Research] Tool-Calling Agent 시작")
        response, tool_logs = await call_with_tools(
            prompt=prompt,
            tools=tools,
            tool_executors=executors,
            max_calls=5,  # 최대 5번 도구 호출
            trace_name="research_tool_calling",
        )

        brief = response.strip() if response else None
        if brief:
            logger.info("[Research] Tool-Calling 완료 (%d 도구 호출)", len(tool_logs))
        else:
            logger.info("[Research] Tool-Calling 완료, brief 없음")

        return {
            "research_brief": brief,
            "research_tool_logs": tool_logs,
        }

    except Exception as e:
        logger.error("[Research] Tool-Calling 실패: %s", e)
        # Fallback: 빈 brief 반환
        return {
            "research_brief": None,
            "research_tool_logs": [],
        }
