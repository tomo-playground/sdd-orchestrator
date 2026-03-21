---
id: SP-017
priority: P1
scope: backend
branch: feat/SP-017-pipeline-logging-coverage
created: 2026-03-21
status: done
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
LangGraph 파이프라인 노드의 로깅 사각지대 해소 — 게이트 노드, 스킵 가드, 정상 라우팅 경로에 로그 추가

## 왜
- 게이트 노드 3개(human_gate, concept_gate, director_plan_gate)가 로그 0개 — interrupt 발행/수신이 완전히 블랙박스
- `_skip_guard`에서 노드 스킵 시 로그 없음 — FastTrack 등에서 어떤 노드가 스킵됐는지 추적 불가
- `routing.py`의 정상 경로에 로그 없음 — warning/에러만 기록되어 정상 흐름 추적 불가
- 다수 노드에 시작 로그 없어 입력 state 확인 불가
- 파이프라인 디버깅 시 로그만으로 흐름 재구성이 어려움

## 변경 범위

### P0 — 블랙박스 해소 (필수)
- `nodes/human_gate.py`: interrupt 발행 전 + 사용자 응답 수신 시 info 로그
- `nodes/concept_gate.py`: auto/guided 분기, 사용자 선택 결과(select/regenerate/custom), regen 횟수 초과 로그
- `nodes/director_plan_gate.py`: 분기 결정, revise 피드백, plan_revision_count 최대치 초과 로그
- `nodes/_skip_guard.py`: should_skip() True 반환 시 `[SkipGuard] {node} skipped (stage={stage})` 로그

### P1 — 정상 흐름 추적성
- `routing.py`: 정상 라우팅 경로에 debug 레벨 로그 추가 (예: `"review -> director_checkpoint"`)
- 아래 노드에 시작 로그 추가 (입력 씬 수, 모드 등):
  - `review.py`, `finalize.py`, `director_plan.py`, `director_checkpoint.py`
  - `sound_designer.py`, `copyright_reviewer.py`, `explain.py`

### P2 — 세부 개선 (여유 시)
- 로그 접두어 통일: `[LangGraph:{NodeName}]` 패턴
- `location_planner.py`: PLANNING_ENABLED 분기 진입 로그

## 완료 기준 (DoD)
- [ ] 게이트 노드 3개 + skip_guard에 로그 추가 (P0)
- [ ] routing.py 정상 경로에 debug 로그 추가 (P1)
- [ ] 노드 시작 로그 7개 추가 (P1)
- [ ] 기존 테스트 통과 (pytest)
- [ ] 실제 파이프라인 1회 실행 → 로그만으로 전체 흐름 재구성 가능 확인

## 제약
- 변경 파일 10개 이하 목표 (nodes/ 7~10개 + routing.py + _skip_guard.py)
- 건드리면 안 되는 것: 노드 로직 자체, state 구조, 라우팅 분기 로직
- 의존성 추가 금지
- info 레벨 남용 금지 — 정상 라우팅은 debug, 의미 있는 상태 변경만 info

## 힌트
- 관련 파일: `backend/services/agent/nodes/` (21개 노드), `backend/services/agent/routing.py`
- 분석 결과: 전체 27파일 185개 logger 호출 중 게이트 3개+skip_guard가 0개
- 참고: `_production_utils.py`가 공통 Gemini 호출 로깅 담당 — 직접 호출 노드만 별도 로그 필요
