# Chat System UX & Architecture Enhancement (Phase 27)

> 상태: 전체 완료
> 시작일: 2026-03-03
> 완료일: 2026-03-03
> 선행: Phase 26 (Script 협업형 UX)

---

## 1. 배경 및 목표

### 현재 문제

Phase 24~26에서 Script 탭을 하이브리드 채팅 AI로 전환하고, 3단계 모드 + 대화형 씬 수정까지 구현했으나, **기본 UX 안정성과 코드 품질에 개선이 필요**하다.

| 문제 | 영향 |
|------|------|
| 로딩/대기 피드백 부재 | 토픽 분석(2-5초), 씬 수정 중 화면 정적 → 시스템 멈춤 인식 |
| 채팅 히스토리 소실 | 새로고침/탭 전환 시 전체 대화 소실 |
| 접근성(a11y) 부재 | aria-*, role 속성 0개. 스크린리더 미지원 |
| ChatMessage bag 타입 | 11종 contentType 필드가 모두 optional → 타입 안전성 없음 |
| AbortController 미사용 | 언마운트 후 응답 처리, 메모리 누수 가능 |
| 에러 복구 UX 미흡 | SettingsCard "생성 시작됨" 고정, PROHIBITED_CONTENT 안내 없음 |
| AutoScroll 의존성 불완전 | upsert(PipelineStep 갱신) 시 스크롤 미작동 |
| 헬퍼 함수 중복 | nextId(), assistantMsg() 2파일 중복 |

### 목표
- **P0**: 사용자 체감 즉시 개선 (로딩 피드백, 히스토리 영속, 접근성)
- **P1**: 코드 품질·안정성 개선 (타입 안전성, 에러 복구, AbortController)
- **P2**: 세부 UX 폴리시 (헬퍼 통합, 모드 설명)

---

## 2. P0 — 즉시 개선 (기본 UX 안정성)

### P0-1: 타이핑 인디케이터 ✅

API 호출 직전 임시 AssistantBubble("분석 중..." / "수정 사항 분석 중...") 추가, 응답 수신 후 제거.

- `addTypingIndicator()` / `removeTypingIndicator()` 헬퍼 패턴
- `useChatScriptEditor.ts`, `useSceneEditActions.ts` 양쪽 적용

### P0-2: 채팅 히스토리 영속화 ✅

독립 `useChatStore` (Zustand persist) 신규 생성. 스토리보드 ID별 localStorage 저장.

- `frontend/app/store/useChatStore.ts` (신규)
- MAX_MESSAGES_PER_STORYBOARD=50, MAX_STORYBOARD_ENTRIES=10
- 오래된 엔트리 자동 eviction (timestamp 기준)
- `useChatScriptEditor.ts`에서 store 연동 (저장/복원/초기화)

### P0-3: 접근성(a11y) 기본 속성 ✅

| 컴포넌트 | 추가 속성 |
|----------|----------|
| ChatMessageList | `role="log"` `aria-live="polite"` `aria-label="채팅 메시지"` |
| ChatInput textarea | `aria-label="메시지 입력"` / `aria-label="씬 수정 입력"` |
| ChatInput 전송 버튼 | `aria-label="메시지 전송"` |
| ProgressBar | `role="progressbar"` `aria-valuenow` `aria-valuemin` `aria-valuemax` |
| PipelineStepCard | `aria-expanded` |

---

## 3. P1 — 단기 개선 (코드 품질·안정성)

### P1-1: ChatMessage Discriminated Union ✅

bag 타입(11개 optional) → 11개 variant 타입으로 전환. 각 카드 컴포넌트가 자신의 variant만 받도록 수정.

- `types/chat.ts`: `ChatMessageBase` + 11개 variant union
- 각 카드 컴포넌트 import/props 타입 변경

### P1-2: useChatScriptEditor 책임 분리 — 미뤄짐

현재 403줄. 추후 `useChatMessages` / `useTopicAnalysis` / `useSseToChat` 분리 예정.

### P1-3: AbortController ✅

`sendMessage()`에 AbortController 추가. 언마운트 시 `cleanup`에서 abort() 호출. catch에서 AbortError 무시.

- 취소 버튼은 미구현 (추후 UX 요건 확정 시)

### P1-4~6: 에러 복구 + SettingsCard + AutoScroll ✅

- **ErrorCard**: PROHIBITED_CONTENT 감지 → "주제를 바꾸거나, 표현을 수정해 보세요" 힌트
- **SettingsRecommendCard**: `hasError` prop으로 에러 시 `applied` 상태 리셋
- **useAutoScroll**: `lastTs` (마지막 메시지 timestamp) 의존성 추가로 upsert 감지

---

## 4. P2 — 세부 UX 폴리시

### P2-1: 중복 헬퍼 함수 통합 ✅

`frontend/app/utils/chatMessageFactory.ts` (신규) — `createMessageId()`, `createAssistantMessage()`, `createUserMessage()`, `createErrorMessage()`, `createWelcomeMessage()` 추출.

### P2-2: 인터랙션 모드 툴팁 ✅

Auto/Guided/Hands-on 칩에 `title` 속성으로 한국어 설명 추가.

### P2-3~4: 미구현

ClarificationCard 응답 유도, PlanReviewCard 시각적 통일은 추후 이터레이션.

---

## 5. 파일 맵 (실제 변경)

| 파일 | 변경 내용 |
|------|----------|
| `types/chat.ts` | Discriminated Union 도입 |
| `store/useChatStore.ts` (신규) | 히스토리 영속 store |
| `utils/chatMessageFactory.ts` (신규) | 헬퍼 함수 추출 |
| `hooks/useChatScriptEditor.ts` | 타이핑 인디케이터, 히스토리 연동, AbortController |
| `hooks/useSceneEditActions.ts` | 타이핑 인디케이터, type narrowing |
| `hooks/useAutoScroll.ts` | lastTs 의존성 |
| `components/chat/ChatMessageList.tsx` | a11y |
| `components/chat/ChatInput.tsx` | a11y, mode tooltips |
| `components/chat/ProgressBar.tsx` | a11y progressbar |
| `components/chat/ChatMessage.tsx` | Discriminated union, hasError |
| `components/chat/ChatArea.tsx` | hasError 감지 |
| `components/chat/messages/ErrorCard.tsx` | PROHIBITED_CONTENT 힌트 |
| `components/chat/messages/SettingsRecommendCard.tsx` | hasError reset |
| `components/chat/messages/PipelineStepCard.tsx` | a11y, typed props |
| `components/chat/messages/ClarificationCard.tsx` | typed props |
| `components/chat/messages/ConceptCard.tsx` | typed props |
| `components/chat/messages/ReviewCard.tsx` | typed props |
| `components/chat/messages/PlanReviewCard.tsx` | typed props, lucide 아이콘 |

---

## 6. DoD (Definition of Done)

- [x] P0: 타이핑 인디케이터 표시 (토픽 분석 + 씬 수정)
- [x] P0: 채팅 히스토리 새로고침 후 복원
- [x] P0: 주요 컴포넌트 aria-* 속성 추가
- [x] P1: ChatMessage discriminated union 적용
- [ ] P1: useChatScriptEditor 150줄 이하 — **미뤄짐** (현재 403줄)
- [ ] P1: 생성 취소 버튼 — **미구현** (AbortController unmount 정리만)
- [x] P1: 에러 시 SettingsCard 복구 + PROHIBITED_CONTENT 힌트
- [x] P1: AutoScroll upsert 감지
- [x] P2: 헬퍼 함수 1곳으로 통합
- [x] P2: 모드 칩 툴팁 표시
- [x] Frontend 빌드 PASS + 코드 리뷰 PASS

### 잔여 항목 (추후 이터레이션)
- P1-2: useChatScriptEditor 책임 분리 (403줄 → 3개 훅)
- P1-3: 취소 버튼 UI
- P2-3: ClarificationCard 응답 유도
- P2-4: PlanReviewCard 시각적 통일
