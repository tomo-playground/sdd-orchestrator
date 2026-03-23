---
id: SP-071
priority: P2
scope: backend
branch: feat/SP-071-narrative-specificity-humor
created: 2026-03-23
status: done
approved_at: 2026-03-23
depends_on: SP-064
label: feat
---

## 무엇을 (What)
Narrative 평가에 "상황 구체성(situational_specificity)" 차원을 추가하고, Writer 프롬프트에 "리액션만 나열하지 말고 구체적 상황을 대사에 포함하라" 규칙을 추가한다.

## 왜 (Why)
현재 Narrative 8차원(`hook`, `emotional_arc`, `twist_payoff`, `speaker_tone`, `script_image_sync`, `spoken_naturalness`, `retention_flow`, `pacing_rhythm`)은 서사 구조만 측정한다. 대사의 **상황 구체성**이나 **공감/유머**를 직접 측정하는 차원이 없어, "내 발... 뭐지?" 같은 리액션만 나열된 대사가 통과된다.

storyboard #1176 사례:
- "내 발... 뭐지?" → 뭔 실수인지 안 보임. "짝짝이 구두로 출근했다"처럼 구체적 상황이 있어야 공감
- "모니터엔... 헐!" → 뭐가 떴는지 안 알려주니 시청자 상상 불가
- 전체적으로 **상황 묘사 없이 리액션만** 나열 → "그래서 뭔데?" 느낌

Writer가 생성하고, Review가 통과시키고, Director가 revise 안 하는 구조적 갭.

## 완료 기준 (DoD)

### Narrative 차원 추가

- [x] `_NARRATIVE_WEIGHTS`에 `situational_specificity` 차원 추가 (가중치 0.10, 기존 차원 가중치 재분배하여 합계 1.0 유지)
- [x] `NarrativeScoreOutput` (llm_models.py)에 `situational_specificity: float` 필드 추가
- [x] LangFuse `pipeline/review/unified` 프롬프트 Narrative 섹션에 평가 기준 추가: "각 씬이 구체적 상황/행동/대상을 포함하는지 평가. 리액션만 있고 상황 맥락이 없는 대사는 감점"

### Writer 프롬프트 규칙

- [x] LangFuse `pipeline/writer/script` 프롬프트에 규칙 추가: "대사는 반드시 구체적 상황이나 행동을 포함해야 한다. 감탄사/리액션만으로 구성된 대사 금지. Bad: '내 발... 뭐지?' / Good: '짝짝이 구두 신고 왔잖아!'"

### 통합

- [x] 기존 테스트 regression 없음
- [x] 린트 통과

## 영향 분석
- 관련 파일: `backend/services/agent/nodes/review.py`, `backend/services/agent/llm_models.py`, LangFuse 프롬프트 2개
- 상호작용: SP-064의 per-scene 평가와 결합 시 "씬 N: 상황 구체성 부족" 형태의 구체적 피드백 가능
- Gemini 토큰 소비 미미 (차원 1개 추가)

## 제약
- 변경 파일 4개 이하
- SP-064 per-scene 구조가 먼저 적용되어야 씬 단위 피드백 전달 가능 (depends_on)
- 가중치 재분배 시 기존 차원 점수 하락 가능 — threshold 조정 필요 여부 확인

## 힌트
- 가중치 재분배 후보: `speaker_tone`(0.05→0.05 유지) + `twist_payoff`(0.10→0.05) + 신규(0.10) 등
- Writer 프롬프트 규칙은 Bad/Good 예시 쌍으로 효과 극대화
- storyboard #1176을 before/after 검증 사례로 활용
