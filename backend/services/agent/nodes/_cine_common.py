"""Cinematographer 서브 에이전트 공통 유틸리티.

JSON 파싱 로직을 공유하여 코드 중복을 방지한다.
"""

from __future__ import annotations

import json
import re

from config import pipeline_logger as logger
from services.creative_utils import parse_json_response


def parse_sub_agent_result(response: str) -> dict | None:
    """서브 에이전트 응답에서 {"scenes": [...]} dict를 파싱한다.

    Framing, Action, Atmosphere 3개 에이전트가 공유한다.
    """
    if not response or not response.strip():
        return None
    try:
        match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
        text = match.group(1) if match else response
        data = parse_json_response(text)
        if isinstance(data, dict) and isinstance(data.get("scenes"), list):
            return data
    except (json.JSONDecodeError, ValueError, TypeError):
        pass
    # Fallback: {"scenes" 패턴 추출
    idx = response.find('{"scenes"')
    if idx >= 0:
        try:
            data = parse_json_response(response[idx:])
            if isinstance(data, dict) and isinstance(data.get("scenes"), list):
                return data
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
    return None


def parse_scenes(response: str) -> list[dict] | None:
    """LLM 응답에서 scenes 배열을 추출한다.

    추출 전략 (우선순위):
    1. ```json 코드블록 내부
    2. 응답 전체를 parse_json_response()로 시도
    3. {"scenes" 패턴 위치부터 끝까지 추출
    빈 응답 시 즉시 None 반환.
    """
    if not response or not response.strip():
        logger.warning("[Cinematographer] 빈 응답 수신, 파싱 스킵")
        return None

    # 전략 1: ```json 코드블록 추출
    match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if match:
        parsed = _try_parse_json_dict(match.group(1))
        if parsed is not None:
            return parsed

    # 전략 2: 응답 전체를 직접 파싱
    parsed = _try_parse_json_dict(response)
    if parsed is not None:
        return parsed

    # 전략 3: {"scenes" 패턴부터 매칭 중괄호까지 추출
    scenes_idx = response.find('{"scenes"')
    if scenes_idx == -1:
        scenes_idx = response.find("{'scenes")  # single-quote fallback
    if scenes_idx >= 0:
        json_candidate = _extract_balanced_braces(response, scenes_idx)
        if json_candidate:
            parsed = _try_parse_json_dict(json_candidate)
            if parsed is not None:
                return parsed
        parsed = _try_parse_json_dict(response[scenes_idx:])
        if parsed is not None:
            return parsed

    logger.warning(
        "[Cinematographer] JSON 파싱 실패: 유효한 scenes JSON을 찾을 수 없음 (응답 길이=%d, 앞 100자=%r)",
        len(response),
        response[:100],
    )
    return None


def _extract_balanced_braces(text: str, start: int) -> str | None:
    """start 위치의 '{'부터 대응하는 '}'까지 추출한다. 실패 시 None."""
    if start >= len(text) or text[start] != "{":
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _try_parse_json_dict(text: str) -> list[dict] | None:
    """텍스트에서 scenes 배열을 가진 dict를 파싱. 실패 시 None."""
    if not text or not text.strip():
        return None
    try:
        result_data = parse_json_response(text)
        if not isinstance(result_data, dict):
            return None
        scenes = result_data.get("scenes")
        return scenes if isinstance(scenes, list) else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
