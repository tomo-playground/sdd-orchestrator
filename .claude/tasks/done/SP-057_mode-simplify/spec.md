---
id: SP-057
priority: P1
scope: fullstack
branch: feat/SP-057-mode-simplify
created: 2026-03-22
status: done
approved_at: 2026-03-23
depends_on:
label: feat
---

## 무엇을 (What)
Auto 모드를 폐지하고 Guided/FastTrack 2모드로 단순화한다. FastTrack은 노드를 건너뛰지 않고, 모든 노드를 1회 실행 후 자동 승인하는 방식으로 변경한다.

## 왜 (Why)
현재 Auto와 FastTrack의 실질적 차이가 없다. 둘 다 사용자 입력 없이 monologue를 생성한다. Auto가 존재 가치를 갖으려면 트렌드 기반 자율 생성 같은 외부 데이터가 필요하지만, 현 단계에서는 불필요한 복잡성이다. FastTrack의 "노드 스킵"도 품질 저하만 초래하므로, "모든 노드 실행 + 반복 1회 제한"으로 재정의한다.

## 완료 기준 (DoD)

### interaction_mode rename
- [ ] `schemas.py` interaction_mode Literal에서 "auto" → "fast_track" 변경, "hands_on" 제거
- [ ] `coerce_interaction_mode()` 함수 추가: "auto" → "fast_track", "hands_on" → "guided" 매핑 (하위 호환)
- [ ] `routing.py`, `concept_gate.py`, `human_gate.py`, `director_plan_gate.py`에서 mode 분기 갱신
- [ ] Frontend `interactionMode` 타입 및 UI 갱신 (Auto 버튼 제거 또는 FastTrack으로 표시)

### FastTrack 반복 1회 제한
- [ ] FastTrack 모드에서 Critic 피드백 루프를 1회로 제한 (피드백 수신 후 즉시 승인)
- [ ] FastTrack 모드에서 Director 검수 루프를 1회로 제한
- [ ] FastTrack 모드에서 Director Plan Gate를 자동 승인

### 하위 호환
- [ ] DB/localStorage에 저장된 `interaction_mode: "auto"` 값이 `coerce_interaction_mode()`로 자동 변환
- [ ] CLAUDE.md 폐기 용어에 "auto" 추가

### 품질 게이트
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 영향 분석
- `backend/schemas.py` — interaction_mode Literal
- `backend/services/agent/routing.py` — 모드 분기
- `backend/services/agent/nodes/concept_gate.py`, `human_gate.py`, `director_plan_gate.py` — 모드 체크
- `backend/services/agent/state.py` — ScriptState interaction_mode 타입
- `frontend/app/components/chat/ChatInput.tsx` — 모드 선택 UI
- `frontend/app/store/useStoryboardStore.ts` — interactionMode 상태

## 제약 (Boundaries)
- FastTrack에서 Intake 노드 스킵은 SP-058에서 처리 (이 태스크는 모드 rename + 반복 제한만)
- skip_stages 로직 변경 최소화 — 기존 FastTrack 스킵 로직을 "반복 1회 제한"으로 전환

## 상세 설계 (How)
> [design.md](./design.md) 참조 (착수 시 작성)
