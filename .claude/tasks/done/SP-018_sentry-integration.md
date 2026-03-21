---
id: SP-018
priority: P1
scope: fullstack
branch: feat/SP-018-sentry-integration
created: 2026-03-21
status: done
depends_on:
label: enhancement
assignee: stopper2008
---

## 무엇을
Sentry Cloud 연동 — Backend/Frontend/Audio 3개 서비스에 에러 모니터링 도입

## 왜
- 파이프라인 에러 발생 시 자동 수집/그룹핑/알림 없음 — 로그 파일 수동 확인 의존
- 에러 빈도, 패턴, 재현 조건 추적 불가
- Frontend 에러 수집 체계 전무

## Sentry 프로젝트 (생성 완료)
| 프로젝트 | slug | DSN |
|----------|------|-----|
| Backend | shorts-producer-backend | `https://bdd1e5acf1e1e78696a1a2c685efd5e2@o4510366627725312.ingest.us.sentry.io/4511080166129664` |
| Frontend | shorts-producer-frontend | `https://a807beff1f8075b65803afeb967f80fa@o4510366627725312.ingest.us.sentry.io/4511080166195200` |
| Audio | shorts-producer-audio | `https://d1e3bd66d63a2f6c0c888bb32d2d62d1@o4510366627725312.ingest.us.sentry.io/4511080168620032` |

## 구현 범위

### 1. Backend (FastAPI :8000)
- `sentry-sdk[fastapi]` 설치
- `sentry_sdk.init()` — DSN, environment, traces_sample_rate
- LangGraph 파이프라인 커스텀 context: node_name, storyboard_id, trace_id(LangFuse)
- 환경변수: `SENTRY_DSN_BACKEND`, `SENTRY_ENVIRONMENT`

### 2. Frontend (Next.js :3000)
- `@sentry/nextjs` 설치
- `sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`
- `next.config.ts`에 `withSentryConfig` 래핑
- Error Boundary 연동
- 환경변수: `NEXT_PUBLIC_SENTRY_DSN`

### 3. Audio (FastAPI :8001)
- `sentry-sdk[fastapi]` 설치
- `sentry_sdk.init()` — DSN, environment
- 환경변수: `SENTRY_DSN_AUDIO`

### 4. GitHub Integration
- Sentry 대시보드에서 GitHub Integration 연결 (사용자 OAuth 필요)
- 이슈 → GitHub Issue 자동 생성 설정

## 완료 기준 (DoD)
- [ ] Backend sentry_sdk.init() + 테스트 에러 전송 확인
- [ ] Frontend @sentry/nextjs + 테스트 에러 전송 확인
- [ ] Audio sentry_sdk.init() + 테스트 에러 전송 확인
- [ ] LangGraph 노드 에러 시 storyboard_id, node_name context 포함 확인
- [ ] DSN은 .env에만 저장, 코드 하드코딩 금지
- [ ] 기존 기능 regression 없음 (빌드 + 테스트 통과)

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것: 기존 에러 핸들링 로직, LangFuse 연동
- Sentry는 LangFuse를 대체하지 않음 — LangFuse(파이프라인 트레이싱) + Sentry(에러 모니터링) 공존
- 무료 플랜 한도: 5K events/월 — sample_rate 조정으로 대응

## 힌트
- Backend 진입점: `backend/main.py`
- Audio 진입점: `audio/main.py`
- Frontend 진입점: `frontend/next.config.ts`
- Sentry org: `tomo-playground`
- GitHub Integration은 사용자 OAuth 필요 — 코드로 불가, 대시보드에서 수동
