---
id: SP-058
priority: P1
scope: backend
branch: feat/SP-058-intake-node
created: 2026-03-22
status: approved
approved_at: 2026-03-23
depends_on: SP-056
label: feat
---

## 무엇을 (What)
Guided 모드에서 Director Plan 앞에 Intake 노드를 추가하여, 소크라테스식 질문으로 사용자의 의도를 파악하고 structure/tone/캐릭터를 확정한다.

## 왜 (Why)
현재 Chat UI에서 structure 선택 경로가 없어 항상 monologue로 생성된다. 사용자가 "monologue", "dialogue" 같은 기술 용어를 몰라도, 자연어 질문-답변을 통해 시스템이 최적 structure를 매칭해야 한다. Director Plan과 책임이 다르므로 (의도 파악 vs 실행 계획) 별도 노드로 분리한다.

## 완료 기준 (DoD)

### Intake 노드 구현
- [ ] `backend/services/agent/nodes/intake.py` 신규 생성
- [ ] LangGraph 그래프에 Intake 노드 등록 (Director Plan 앞)
- [ ] Guided 모드에서 Intake → Director Plan 순서로 실행
- [ ] FastTrack 모드에서 Intake 노드 건너뜀

### 질문 흐름
- [ ] Q1: 영상 형태 파악 (혼자/둘/나레이션+대화) → structure 결정
- [ ] Q2: 분위기/톤 파악 → tone 결정
- [ ] Q3: 2인 구조 시 캐릭터 A/B 선택 (Group 내 캐릭터 목록 제시)
- [ ] 최종 확인 후 state에 structure/tone/character_id/character_b_id 저장
- [ ] 사용자 토픽에서 의도가 명확하면 질문 축소 가능 (LLM 판단)

### interrupt 루프
- [ ] 한 노드 안에서 interrupt() 루프로 다중 Q&A 라운드 지원
- [ ] 충분한 정보 수집 시 루프 탈출 → Director Plan으로 진행

### 출력
- [ ] Intake 결과가 state에 `structure`, `tone`, `character_id`, `character_b_id`, `intake_summary` 저장
- [ ] Director Plan이 Intake 출력을 소비하여 플랜 수립

### 품질 게이트
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과
- [ ] Intake 노드 단위 테스트 추가 (structure 결정 로직)

## 영향 분석
- `backend/services/agent/nodes/intake.py` — 신규
- `backend/services/agent/graph.py` — 노드 등록 + 라우팅
- `backend/services/agent/routing.py` — Intake → Director Plan 라우팅
- `backend/services/agent/state.py` — intake_summary 필드 추가
- `frontend/` — interrupt 응답 UI (기존 plan_review와 유사한 패턴)

## 제약 (Boundaries)
- Intake는 structure/tone/캐릭터 결정만 담당. 크리에이티브 방향 설정은 Director Plan 역할
- 질문은 최대 3라운드. 4라운드 이상 진행하지 않음
- tone 목록은 SP-056에서 정의된 TONE_METADATA 사용

## 상세 설계 (How)
> [design.md](./design.md) 참조
