# Phase 7-5: UX/UI Quality & Reliability (Archived)

**기간**: ~2026-02-12 완료
**목표**: 8개 에이전트 크로스 분석 기반 전체 UX 품질 향상.
**선행**: Phase 7-4 완료 (4-Store 분할, 디자인 토큰, 접근성 기반).
**분석 출처**: UI/UX Engineer, Frontend Dev, Backend Dev, QA Validator, Security Engineer, FFmpeg Expert, DBA, Prompt Engineer (총 89건 발견)

## Phase A: Quick Wins (9/9) — 2026-02-12

| # | 작업 | 분류 | 발견자 |
|---|------|------|--------|
| 1 | Toast 큐 시스템 (useUIStore toasts 배열) | UX | QA, UI/UX |
| 2 | `window.confirm`/`window.prompt` → `useConfirm` 전면 교체 (6곳) | UX | QA, UI/UX, FE |
| 3 | Studio dirty state `beforeunload` 가드 | 안정성 | QA |
| 4 | `text-[8px]` → `text-[11px]` 폰트 위반 수정 7곳 | 접근성 | UI/UX |
| 5 | Suspense fallback 통일 3곳 | UX | UI/UX |
| 6 | `inputCls`/`labelCls` → variants.ts 토큰 + 7곳 교체 | 일관성 | UI/UX |
| 7 | TagValidationWarning → SceneFormFields 연결 | 품질 | Prompt |
| 8 | 후보 이미지 match_rate 뱃지 표시 | UX | Prompt |
| 9 | 렌더링 catch `err.message` → `getErrorMsg()` | UX | FFmpeg |

## Phase B: 피드백 품질 + 에러 복구 + 성능 (11/11) — 2026-02-12

| # | 작업 | 분류 | 발견자 |
|---|------|------|--------|
| 10 | 에러 메시지 구조화 (`error_responses.py` + 6개 라우터) | 보안/UX | BE, Security |
| 11 | 이미지 생성 SSE 진행률 (`/scene/generate-async`) | UX | BE, FFmpeg, Prompt |
| 12 | ScenesTab `useShallow` + 4그룹 selector 분리 | 성능 | FE |
| 13 | Frontend 에러 헬퍼 통일 `getErrorMsg()` | 안정성 | FE, QA |
| 14 | 파일 업로드 MIME + 매직 바이트 검증 + 10MB 제한 | 보안 | Security |
| 15 | MinIO 기본 credential 제거 + startup 검증 | 보안 | Security |
| 16 | Pydantic `max_length` 추가 (8필드) | 보안 | Security |
| 17 | 렌더링 ETA 표시 | UX | FFmpeg |
| 18 | Duration 입력 JS 검증 (NaN + 1~10 클램핑) | 안정성 | QA |
| 19 | 스토리보드 재생성 시 경고 ConfirmDialog | 안정성 | QA |
| 20 | SSE 재연결 (MAX_RETRIES=3, 지수 백오프) | 안정성 | FFmpeg |

## Phase C: 구조적 개선 (10/10)

| # | 작업 | 분류 | 발견자 |
|---|------|------|--------|
| 21 | 씬 Client-Side UUID (레이스 컨디션 해결) | 안정성 | QA, FE |
| 22 | Optimistic Locking (`version` 컬럼 + 409 Conflict) | 안정성 | DBA |
| 23 | 핵심 엔드포인트 `response_model` 정리 | API 품질 | BE |
| 24 | 페이지네이션 통일 (스토리보드/태그/캐릭터) | 성능 | BE, DBA |
| 25 | Skeleton 로딩 컴포넌트 도입 | UX | UI/UX |
| 26 | Soft Delete 복원 정합성 (batch_id) | 안정성 | DBA |
| 27 | Active 상태 스타일 토큰 통일 | 일관성 | UI/UX |
| 28 | `list_storyboards` selectinload 전환 | 성능 | DBA |
| 29 | Backgrounds N+1 해결 | 성능 | BE |
| 30 | LocalStorage Path Traversal 방어 | 보안 | Security |
