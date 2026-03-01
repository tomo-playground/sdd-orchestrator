# Script 탭 협업형 UX (Phase 26)

> 상태: IN_PROGRESS
> 시작일: 2026-03-01
> 선행: Phase 24 (하이브리드 채팅 AI), Phase 25 (Director 자율 실행)

---

## 1. 배경 및 목표

### 현재 문제
Phase 24에서 Script 탭을 챗봇 형태로 전환했으나, **"AI와 대화하며 스토리를 만드는 느낌"**이 부족하다.

| 문제 | 원인 |
|------|------|
| 생성 과정이 블랙박스 | 17개 노드 결과가 ProgressBar 한 줄로만 표시 |
| 사용자 개입 기회 부족 | `auto_approve=True` 하드코딩, human_gate 비활성 |
| 생성 후 대화 끊김 | CompletionCard 이후 ChatInput 비활성 |

### 목표
- 사용자가 **AI의 사고 과정을 실시간으로 보고**, **방향을 조정**할 수 있는 협업형 UX
- 외부 사례 벤치마크: Cursor(단계별 로그), Gamma(아웃라인 검토), Canvas(부분 수정)

---

## 2. 구현 항목

### P0-1: 파이프라인 스트리밍 메시지

**목표**: 각 노드 완료 시 채팅 메시지로 표시 (ProgressBar 유지 + 메시지 추가)

**구현 범위**:
- `useChatScriptEditor.onNodeEvent`에서 `running`/`completed` status일 때 채팅 메시지 추가
- 새 메시지 타입: `pipeline_step` — 노드명, 레이블, 요약 텍스트 표시
- `PipelineStepCard` 컴포넌트: 접기/펼치기, 노드 아이콘, 결과 요약
- 표시할 노드: director(구조), writer(씬 수), critic(피드백), cinematographer(프롬프트 수)
- 중간 노드(research, title_gen 등): 간단한 한줄 메시지

**참고 패턴**: Cursor Agent "파일 분석 중 → 수정 적용 중"

### P0-2: auto_approve 3단계 모드

**목표**: 사용자가 생성 과정에 개입하는 수준을 선택

**모드 정의**:
| 모드 | concept_gate | director_plan (신규) | human_gate |
|------|-------------|---------------------|------------|
| Full Auto | 건너뜀 | 건너뜀 | 건너뜀 |
| Guided (기본값) | **사용자 선택** | **사용자 검토** | 건너뜀 |
| Hands-on | **사용자 선택** | **사용자 검토** | **사용자 승인** |

**구현 범위**:
- Backend: `scripts.py`의 `auto_approve` 하드코딩 제거 → 요청 파라미터로 수신
- Backend: `director_plan` 노드 완료 시 interrupt 포인트 추가 (Guided/Hands-on)
- Backend: `human_gate` 라우팅 경로 복원 (Hands-on 전용)
- Frontend: ChatInput 영역에 모드 선택 UI (칩 또는 드롭다운)
- Frontend: SSE `waiting_for_input` status에 `director_plan` 타입 추가

### P0-3: Director Plan 검토 카드

**목표**: Director 분석 결과를 사용자가 검토/수정할 수 있는 카드

**구현 범위**:
- `PlanReviewCard` 컴포넌트: 구조 요약, 씬 수, 예상 길이, 캐릭터 배치
- [진행] / [수정할게요] 버튼
- "수정할게요" → ChatInput 활성화 → 사용자 피드백 → `resume("revise_plan", feedback)`
- Backend: `director_plan_gate` interrupt 노드 추가 → `Command(resume=...)` 처리

---

## 3. P1 (후속)

### 생성 후 대화형 수정 루프
- CompletionCard 이후 ChatInput 계속 활성화
- "3번 씬 대사를 더 감성적으로" → 부분 재생성 API
- Before/After diff 표시 + Accept/Reject

### Canvas형 Split View (P2)
- Script 탭 내 좌측 채팅 + 우측 씬 미리보기
- 레이아웃 전면 변경이므로 별도 Phase로 분리

---

## 4. 외부 사례 참조

상세 벤치마크: `docs/02_design/CHATBOT_UX_RESEARCH.md`

| 패턴 | 참고 도구 | 적용 항목 |
|------|----------|----------|
| 단계별 텍스트 스트리밍 | Cursor Agent | P0-1 |
| 아웃라인 검토 단계 | Gamma.app | P0-3 |
| diff 승인 (Accept/Reject) | Cursor Composer | P1 |
| 부분 수정 루프 | Canvas, v0.dev | P1 |
| n개 선택지 | Midjourney 4-grid | 기존 ConceptCard |
