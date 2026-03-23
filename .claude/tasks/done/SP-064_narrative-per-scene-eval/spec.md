---
id: SP-064
priority: P2
scope: backend
branch: feat/SP-064-narrative-per-scene-eval
created: 2026-03-23
status: done
depends_on: SP-061
label: feat
---

## 무엇을 (What)
Review Unified의 Narrative 평가를 aggregate 점수에서 per-scene 단위로 확장하여, Revise 노드에 구체적 씬 번호와 개선 방향을 전달한다.

## 왜 (Why)
현재 Narrative Score는 전체 스크립트에 대한 단일 aggregate 점수다. 11씬 중 2씬에 문제가 있어도 나머지 9씬이 좋으면 aggregate가 threshold를 넘겨 통과한다. Revise 노드는 "어떤 씬을 어떻게 고쳐야 하는지" 모른 채 전체를 재생성하게 된다.

## 완료 기준 (DoD)

### per-scene 피드백 구조

- [x] `NarrativeScoreOutput`에 `scene_issues: list[dict]` 필드를 추가한다. 각 항목은 `{"scene_id": int, "issue": str, "dimension": str, "severity": "error"|"warning"}` 형식이다
- [x] LangFuse `pipeline/review/unified` 프롬프트의 Narrative 섹션에 "각 차원에서 문제가 있는 씬 번호를 scene_issues에 명시하라" 지시를 추가한다

### 전환 자연성 평가

- [x] LangFuse 프롬프트에 "인접 씬 페어(N→N+1)의 전환 자연성을 평가하고, 어색한 전환 씬 번호를 scene_issues에 포함하라" 지시를 추가한다

### Revise 피드백 전달

- [x] Revise 노드의 `_build_feedback()`에서 `scene_issues`를 파싱하여 "씬 N: {issue}" 형태의 구체적 피드백을 생성한다
- [x] Revise Tier 3(재생성) 시 `pipeline_context["revision_feedback"]`에 씬 번호가 포함된 피드백이 전달된다

### 통합

- [x] 기존 테스트 regression 없음
- [x] 린트 통과

## 영향 분석
- 관련 파일: `backend/services/agent/nodes/review.py`, `backend/services/agent/llm_models.py`, `backend/services/agent/nodes/revise.py`, LangFuse `pipeline/review/unified`
- 상호작용: Gemini 응답 스키마 변경 → 파싱 로직 수정 필요
- Gemini 토큰 소비 소폭 증가 (scene_issues 추가 출력)

## 제약
- 변경 파일 5개 이하
- SP-061의 L2 검증이 먼저 적용되어야 Gemini 평가 부하를 줄일 수 있음 (depends_on)
- 별도 노드 추가는 하지 않음 — Review Unified 프롬프트 확장 방식

## 힌트
- `UnifiedReviewOutput` (llm_models.py)에 `scene_issues` 필드 추가
- `_build_narrative_score()` (review.py)에서 scene_issues를 review_result에 포함
- Revise의 `_build_feedback()` (revise.py)에서 scene_issues → 문자열 피드백 변환
