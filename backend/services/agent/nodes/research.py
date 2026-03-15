"""Research 노드 — Memory Store 히스토리 + 소재(References) 분석.

character, topic, user, group 네임스페이스를 검색하고,
사용자가 제공한 URL/텍스트 소재를 Gemini로 분석하여
draft/debate 노드에 전달할 research_brief를 구성한다.
"""

from __future__ import annotations

import asyncio
import html as html_mod
import ipaddress
import json
import re
from urllib.parse import urlparse

import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore

from config import (
    RESEARCH_MAX_REFERENCES,
    RESEARCH_URL_FETCH_TIMEOUT,
    RESEARCH_URL_MAX_BYTES,
    logger,
    template_env,
)
from database import get_db_session
from services.agent.state import ScriptState
from services.llm import LLMConfig, get_llm_provider


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


_STRIP_TAGS_RE = re.compile(
    r"<\s*(script|style|noscript|svg|iframe)[^>]*>.*?</\s*\1\s*>",
    re.DOTALL | re.IGNORECASE,
)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")
_BLANK_LINES_RE = re.compile(r"\n{3,}")


def _html_to_text(html: str) -> str:
    """HTML → 텍스트 변환. script/style/comment 제거 후 태그 strip."""
    text = _STRIP_TAGS_RE.sub("", html)
    text = _HTML_COMMENT_RE.sub("", text)
    text = _HTML_TAG_RE.sub("", text)
    # HTML 엔티티 디코딩
    text = html_mod.unescape(text)
    # 연속 공백/줄바꿈 정리
    text = _WHITESPACE_RE.sub(" ", text)
    text = _BLANK_LINES_RE.sub("\n\n", text)
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

    # URL과 텍스트 소재를 분리하여 URL은 병렬 fetch
    url_refs: list[str] = []
    text_materials: list[dict[str, str]] = []
    for ref in refs:
        ref = ref.strip()
        if not ref:
            continue
        if _is_url(ref):
            url_refs.append(ref)
        else:
            text_materials.append({"url": "(직접 입력)", "content": ref[:3000]})

    # URL들을 병렬로 fetch
    materials: list[dict[str, str]] = []
    if url_refs:
        results = await asyncio.gather(
            *[_fetch_url(url) for url in url_refs],
            return_exceptions=True,
        )
        for url, result in zip(url_refs, results, strict=True):
            if isinstance(result, Exception):
                logger.warning("[Research] URL fetch 예외 (%s): %s", url, result)
                materials.append({"url": url, "content": "(fetch 실패)"})
            elif result:
                materials.append({"url": url, "content": result[:3000]})
            else:
                materials.append({"url": url, "content": "(fetch 실패)"})

    materials.extend(text_materials)

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

        llm_response = await get_llm_provider().generate(
            step_name="research_analyze_references",
            contents=prompt,
            config=LLMConfig(
                system_instruction="You are a content analyst for short-form video production. Analyze reference materials and extract key insights.",
            ),
        )
        raw = llm_response.text

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


# ── 구조화 brief 파싱 ─────────────────────────────────────────


_STRUCTURED_BRIEF_INSTRUCTION = """

위 내용을 바탕으로 아래 JSON 형식으로 정리하세요:
{"topic_summary": "주제 요약", "recommended_angle": "추천 각도", "key_elements": ["핵심 요소1", "핵심 요소2"], "emotional_arc_suggestion": "감정 곡선 제안", "audience_hook": "시청자 훅"}
JSON만 출력하세요."""


def _parse_structured_brief(raw: str) -> dict:
    """Research 결과를 구조화 dict로 파싱한다. 실패 시 topic_summary 폴백."""
    if not raw:
        return {"topic_summary": ""}
    parsed = _parse_gemini_json(raw)
    if parsed and isinstance(parsed, dict) and "topic_summary" in parsed:
        return parsed
    # JSON이 아닌 경우: raw text를 topic_summary로 감싸기
    return {"topic_summary": raw}


# ── 메인 노드 ───────────────────────────────────────────────


async def research_node(state: ScriptState, config: RunnableConfig, *, store: BaseStore) -> dict:
    """Tool-Calling Agent로 research brief를 구성한다.

    LLM이 주제를 분석하여 필요한 정보원만 선택적으로 호출한다.
    """
    from services.agent.nodes._skip_guard import should_skip  # noqa: PLC0415

    if should_skip(state, "research"):
        return {"research_brief": None, "research_tool_logs": [], "research_score": None, "research_retry_count": 0}

    # DB 세션: config 주입 우선, 없으면 자체 생성 (Writer/Revise와 동일 패턴)
    db_session = config.get("configurable", {}).get("db") if config else None
    if not db_session:
        with get_db_session() as db_session:
            return await _run_research(state, store, db_session)
    return await _run_research(state, store, db_session)


async def _run_research(state: ScriptState, store: BaseStore, db_session: object) -> dict:
    """Research 핵심 로직. DB 세션이 보장된 상태에서 실행."""
    from ..tools.base import call_with_tools  # noqa: PLC0415
    from ..tools.research_tools import create_research_executors, get_research_tools  # noqa: PLC0415

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

    # 12-B-1: Director Plan 컨텍스트 주입
    director_plan = state.get("director_plan")
    if director_plan:
        prompt_parts.append("")
        prompt_parts.append("## 크리에이티브 방향 (Director)")
        prompt_parts.append(f"목표: {director_plan.get('creative_goal', '')}")
        prompt_parts.append(f"타겟 감정: {director_plan.get('target_emotion', '')}")
        prompt_parts.append("리서치 시 이 방향에 맞는 정보를 우선 수집하세요.")

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
    prompt_parts.append(_STRUCTURED_BRIEF_INSTRUCTION)

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
            system_instruction="당신은 쇼츠 대본 작성을 위한 Research Agent입니다.",
        )

        raw_brief = response.strip() if response else None
        if raw_brief:
            logger.info("[Research] Tool-Calling 완료 (%d 도구 호출)", len(tool_logs))
        else:
            logger.info("[Research] Tool-Calling 완료, brief 없음")

        # 12-B-2: 구조화 brief 파싱 (dict 또는 str → dict)
        structured_brief = _parse_structured_brief(raw_brief) if raw_brief else None

        from .research_scoring import calculate_research_score  # noqa: PLC0415

        score = calculate_research_score(state, tool_logs, raw_brief)

        return {
            "research_brief": structured_brief,
            "research_tool_logs": tool_logs,
            "research_score": score,
            "research_retry_count": state.get("research_retry_count", 0) + 1,
        }

    except Exception as e:
        logger.error("[Research] Tool-Calling 실패: %s", e)
        # Fallback: 빈 brief 반환
        return {
            "research_brief": None,
            "research_tool_logs": [],
            "research_score": None,
            "research_retry_count": state.get("research_retry_count", 0) + 1,
        }
