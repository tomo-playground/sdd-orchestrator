"""Critic 토론 유틸리티 (Phase 10-C-3).

KPI 기반 수렴 판단, Groupthink 감지, NarrativeScore 추정 등.
"""

from __future__ import annotations

from config import logger
from config_pipelines import (
    CONVERGENCE_HOOK_THRESHOLD,
    CONVERGENCE_SCORE_THRESHOLD,
    GROUPTHINK_SIMILARITY_THRESHOLD,
    MAX_DEBATE_ROUNDS,
)


def _estimate_narrative_score(concept: dict) -> float:
    """컨셉의 NarrativeScore를 빠르게 추정한다.

    실제 Review 노드를 실행하지 않고, 컨셉의 구조적 요소로 간이 평가.

    Args:
        concept: Architect 컨셉 dict (title, concept, strengths 등)

    Returns:
        추정 NarrativeScore (0.0~1.0)
    """
    score = 0.0

    # 1) Hook 존재 여부 (0.3)
    concept_text = concept.get("concept", "")
    if concept_text and len(concept_text) > 20:
        score += 0.3

    # 2) Key Moments (strengths) 개수 (0.2)
    strengths = concept.get("strengths", [])
    if len(strengths) >= 2:
        score += 0.2
    elif len(strengths) == 1:
        score += 0.1

    # 3) Title 품질 (0.2)
    title = concept.get("title", "")
    if title and len(title) > 5:
        score += 0.2

    # 4) 감정 키워드 존재 (0.15)
    emotional_keywords = ["감동", "놀라", "두려움", "기쁨", "슬픔", "분노", "공포", "설렘"]
    if any(kw in concept_text for kw in emotional_keywords):
        score += 0.15

    # 5) 구조적 완성도 (0.15)
    # 최소한의 서사 구조 (기승전결, 도입-갈등-해결 등)
    if len(concept_text.split(".")) >= 3:  # 최소 3문장
        score += 0.15

    return min(score, 1.0)


def _estimate_hook_strength(concept: dict) -> float:
    """Hook 강도를 빠르게 추정한다.

    Args:
        concept: Architect 컨셉 dict

    Returns:
        Hook 강도 (0.0~1.0)
    """
    concept_text = concept.get("concept", "")
    if not concept_text:
        return 0.0

    strength = 0.0

    # 1) 질문형 (0.3)
    if "?" in concept_text[:100]:  # 첫 100자 내 질문
        strength += 0.3

    # 2) 충격/놀라움 키워드 (0.25)
    shock_keywords = ["놀랍", "충격", "반전", "예상 밖", "의외", "깜짝"]
    if any(kw in concept_text[:100] for kw in shock_keywords):
        strength += 0.25

    # 3) 감정 강도 (0.25)
    emotion_keywords = ["극심한", "강렬한", "압도", "치명적", "위험", "절박"]
    if any(kw in concept_text[:100] for kw in emotion_keywords):
        strength += 0.25

    # 4) 첫 문장 길이 (짧을수록 임팩트) (0.2)
    first_sentence = concept_text.split(".")[0]
    if len(first_sentence) < 30:
        strength += 0.2
    elif len(first_sentence) < 50:
        strength += 0.1

    return min(strength, 1.0)


def _concepts_too_similar(concepts: list[dict], threshold: float = GROUPTHINK_SIMILARITY_THRESHOLD) -> bool:
    """컨셉들이 너무 유사한지 판단 (Groupthink 감지).

    간단한 어휘 기반 유사도로 판단. 실제로는 임베딩 기반이 더 정확하지만,
    레이턴시 증가를 피하기 위해 경량 휴리스틱 사용.

    Args:
        concepts: Architect 컨셉 리스트
        threshold: 유사도 임계값 (기본 0.85)

    Returns:
        True if too similar (Groupthink)
    """
    if len(concepts) < 2:
        return False

    # 각 컨셉의 키워드 집합 추출
    keyword_sets = []
    for c in concepts:
        text = c.get("concept", "") + " " + c.get("title", "")
        # 간단한 단어 토큰화 (공백 기준)
        keywords = set(text.split())
        keyword_sets.append(keywords)

    # 쌍별 Jaccard 유사도 계산
    for i in range(len(keyword_sets)):
        for j in range(i + 1, len(keyword_sets)):
            set_a = keyword_sets[i]
            set_b = keyword_sets[j]
            if not set_a or not set_b:
                continue
            intersection = len(set_a & set_b)
            union = len(set_a | set_b)
            similarity = intersection / union if union > 0 else 0

            if similarity >= threshold:
                logger.warning(
                    "[Debate] Groupthink 감지: concept %d vs %d (similarity=%.2f)",
                    i,
                    j,
                    similarity,
                )
                return True

    return False


async def _check_convergence(concepts: list[dict], messages: list[dict], round_num: int) -> bool:
    """비즈니스 KPI 기반 수렴 판단.

    Args:
        concepts: 현재 라운드의 컨셉 리스트
        messages: 토론 메시지 이력
        round_num: 현재 라운드 번호 (1부터 시작)

    Returns:
        True if 수렴 (토론 종료)
    """
    # 1) NarrativeScore 기반 품질 임계값
    best_score = 0.0
    for c in concepts:
        estimated = _estimate_narrative_score(c)
        c["estimated_score"] = estimated  # 캐시
        best_score = max(best_score, estimated)

    if best_score >= CONVERGENCE_SCORE_THRESHOLD:
        logger.info(
            "[Debate] 수렴: NarrativeScore=%.2f ≥ %.2f (Round %d)",
            best_score,
            CONVERGENCE_SCORE_THRESHOLD,
            round_num,
        )
        return True

    # 2) Hook 강도 체크
    best_hook = 0.0
    for c in concepts:
        hook = _estimate_hook_strength(c)
        best_hook = max(best_hook, hook)

    if best_hook >= CONVERGENCE_HOOK_THRESHOLD:
        logger.info(
            "[Debate] 수렴: Hook 강도=%.2f ≥ %.2f (Round %d)",
            best_hook,
            CONVERGENCE_HOOK_THRESHOLD,
            round_num,
        )
        return True

    # 3) 다양성 붕괴 감지 (Groupthink 방지)
    if _concepts_too_similar(concepts):
        logger.warning("[Debate] Groupthink 감지 — 강제 종료하지 않고 다양성 강제")
        return False  # 추가 라운드에서 다양성 강제

    # 4) Hard round limit
    if round_num >= MAX_DEBATE_ROUNDS:
        logger.info("[Debate] 최대 라운드 도달 (Round %d/%d)", round_num, MAX_DEBATE_ROUNDS)
        return True

    return False
