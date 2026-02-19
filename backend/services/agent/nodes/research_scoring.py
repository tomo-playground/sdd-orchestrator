"""Research 노드 품질 점수 — 규칙 기반 산출.

LLM 추가 호출 없이 tool_logs + brief에서 4개 메트릭을 계산한다.
"""

from __future__ import annotations

from config import logger
from config_pipelines import RESEARCH_QUALITY_THRESHOLD
from services.agent.state import ResearchScore, ScriptState

# analyze_trending은 placeholder이므로 성공률/다양성 계산에서 제외
_EXCLUDED_TOOLS = {"analyze_trending"}

# source_diversity 계산 시 유효 도구 수 (analyze_trending 제외)
# search_topic_history, search_character_history, fetch_url_content, get_group_dna
_VALID_TOOL_COUNT = 4

# 실패 판별 키워드 (result 문자열에 포함 시 실패로 간주)
_FAILURE_KEYWORDS = ("없음", "실패", "가져오기 실패", "이력 없음", "DNA 없음")

# 가중치
_WEIGHTS = {
    "tool_success_rate": 0.35,
    "information_density": 0.30,
    "source_diversity": 0.15,
    "topic_coverage": 0.20,
}


def _tool_success_rate(tool_logs: list[dict]) -> float:
    """성공 도구 호출 비율. analyze_trending 제외."""
    filtered = [log for log in tool_logs if log.get("tool_name") not in _EXCLUDED_TOOLS]
    if not filtered:
        return 0.0
    success = 0
    for log in filtered:
        if log.get("error"):
            continue
        result_str = str(log.get("result", ""))
        if any(kw in result_str for kw in _FAILURE_KEYWORDS):
            continue
        success += 1
    return round(success / len(filtered), 3)


def _information_density(brief: str | None) -> float:
    """brief 길이 기반 정보 밀도. 0→0.0, <100→선형(0~0.5), 100-400→선형(0.5~1.0), ≥400→1.0."""
    if not brief:
        return 0.0
    length = len(brief)
    if length >= 400:
        return 1.0
    if length >= 100:
        return round(0.5 + 0.5 * (length - 100) / 300, 3)
    return round(0.5 * length / 100, 3)


def _source_diversity(tool_logs: list[dict]) -> float:
    """호출된 고유 도구 종류 수 / 유효 도구 수. analyze_trending 제외."""
    unique = {log.get("tool_name") for log in tool_logs if log.get("tool_name") not in _EXCLUDED_TOOLS}
    return round(len(unique) / _VALID_TOOL_COUNT, 3) if unique else 0.0


def _topic_coverage(brief: str | None, state: ScriptState) -> float:
    """brief에 topic/character/group/references 관련 신호 포함 여부."""
    if not brief:
        return 0.0
    brief_lower = brief.lower()
    signals = 0
    total = 0

    # topic 단어 포함 여부
    topic = state.get("topic", "")
    if topic:
        total += 1
        topic_words = [w for w in topic.lower().split() if len(w) >= 2]
        if topic_words and any(w in brief_lower for w in topic_words):
            signals += 1

    # character 관련 신호
    if state.get("character_id"):
        total += 1
        if "캐릭터" in brief_lower or "character" in brief_lower or "히스토리" in brief_lower:
            signals += 1

    # group 관련 신호
    if state.get("group_id"):
        total += 1
        if "그룹" in brief_lower or "group" in brief_lower or "채널" in brief_lower or "dna" in brief_lower:
            signals += 1

    # references 관련 신호
    if state.get("references"):
        total += 1
        if "소재" in brief_lower or "url" in brief_lower or "레퍼런스" in brief_lower or "참고" in brief_lower:
            signals += 1

    if total == 0:
        return 0.5  # 신호 기준 없으면 중간값
    return round(signals / total, 3)


def _generate_feedback(scores: dict[str, float]) -> str:
    """점수 기반 피드백 메시지 생성."""
    parts: list[str] = []
    if scores["tool_success_rate"] < 0.5:
        parts.append("도구 호출 성공률이 낮습니다")
    if scores["information_density"] < 0.3:
        parts.append("수집된 정보가 부족합니다")
    if scores["source_diversity"] < 0.3:
        parts.append("정보원 다양성이 낮습니다")
    if scores["topic_coverage"] < 0.5:
        parts.append("주제 관련 정보가 부족합니다")
    if not parts:
        return "리서치 품질 양호"
    return " / ".join(parts)


def calculate_research_score(
    state: ScriptState,
    tool_logs: list[dict],
    brief: str | None,
) -> ResearchScore | None:
    """Research 노드 품질 점수를 산출한다.

    모든 예외를 catch하여 None을 반환 (graceful degradation).
    """
    try:
        scores = {
            "tool_success_rate": _tool_success_rate(tool_logs),
            "information_density": _information_density(brief),
            "source_diversity": _source_diversity(tool_logs),
            "topic_coverage": _topic_coverage(brief, state),
        }
        overall = round(
            sum(scores[k] * _WEIGHTS[k] for k in _WEIGHTS),
            3,
        )
        feedback = _generate_feedback(scores)

        if overall < RESEARCH_QUALITY_THRESHOLD:
            logger.warning("[Research Score] 품질 낮음: %.3f — %s", overall, feedback)

        return ResearchScore(
            tool_success_rate=scores["tool_success_rate"],
            information_density=scores["information_density"],
            source_diversity=scores["source_diversity"],
            topic_coverage=scores["topic_coverage"],
            overall=overall,
            feedback=feedback,
        )
    except Exception as e:
        logger.error("[Research Score] 점수 계산 실패: %s", e)
        return None
