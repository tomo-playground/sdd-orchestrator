---
id: SP-112
title: Director 공회전 방지 — ReAct loop 반복 제한 + 점수 정체 조기 종료
priority: P1
scope: backend
branch: feat/SP-112-director-loop-guard
created: 2026-03-28
approved_at: 2026-03-28
label: optimization
---

## 배경

Storyboard 1202 파이프라인에서 Director가 cinematographer에 "Hook 씬 duration 초과" 피드백을 반복하여 CineTeam이 10회 이상 공회전. $0.20+ 비용 낭비.

프롬프트 수정(v6→v7)으로 예방했으나, LLM이 여전히 잘못된 라우팅을 할 가능성 있음. 코드 가드레일 추가 필요.

## DoD (Definition of Done)

### 1. Director ReAct loop 전체 반복 제한
- `route_after_director`에서 Director가 최대 스텝 도달 후 다시 cinematographer를 호출하는 loop 반복 횟수 제한
- 현재: MAX_REACT_STEPS(3) × MAX_DIRECTOR_REVISIONS(3) = 최대 9회 CineTeam 호출 가능
- 목표: 전체 Director→cinematographer 왕복 2회 이내로 제한 (CineTeam 최대 3회: 초기 1 + revise 2)

### 2. director_checkpoint 점수 정체 조기 종료
- checkpoint가 연속 2회 동일 점수(±0.05) → 강제 proceed (cinematographer 진행)
- writer 재생성이 품질 개선 없이 반복되는 것 방지

### 3. 테스트
- Director loop 반복 제한 단위 테스트
- checkpoint 점수 정체 조기 종료 단위 테스트
- 기존 테스트 통과 확인

## 참조 파일

- `backend/services/agent/routing.py` (라인 174-210: route_after_director)
- `backend/services/agent/nodes/director.py`
- `backend/services/agent/nodes/director_checkpoint.py`
- `backend/config_pipelines.py` (LANGGRAPH_MAX_* 상수)
