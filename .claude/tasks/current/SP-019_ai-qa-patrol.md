---
id: SP-019
priority: P1
scope: infra
branch: feat/SP-019-ai-qa-patrol
created: 2026-03-21
status: pending
depends_on: SP-018
label: enhancement
assignee: stopper2008
---

## 무엇을
에러 모니터링 자동화 — Sentry 에러 배치 수집 → 분석 → GitHub Issue 자동 등록 + Playwright QA 순찰

## 왜
- Sentry Cloud 무료 플랜은 Slack/GitHub 연동 불가 → 에러 발생을 능동적으로 알 수 없음
- 에러 → 분석 → 이슈 등록까지 수동 작업 제거
- 사람은 GitHub Issue만 확인하면 됨

## 아키텍처

```
[Phase 1: Sentry 에러 → GitHub Issue]

cron (매일 09:00) 또는 /sentry-patrol 수동 실행
  → Sentry API로 전날 새 에러 조회
  → 중복 체크 (이미 등록된 GitHub Issue?)
  → 에러 분석 (스택트레이스, 빈도, 영향 범위)
  → gh issue create (label: sentry)

[Phase 2: Playwright QA 순찰]

cron (매일 09:00 이후) 또는 /qa-patrol 수동 실행
  → Playwright headless 핵심 플로우 실행
  → 이상 감지 시 gh issue create (label: qa-patrol)
```

## 구현 범위

### Phase 1: Sentry 에러 배치 수집 (MVP)

#### 1-1. 배치 스크립트 (`scripts/sentry-patrol.sh`)
- Sentry API (`/api/0/projects/{org}/{project}/issues/`) 조회
- 필터: `firstSeen` 기준 마지막 실행 이후 새 이슈만
- 3개 프로젝트 순회 (backend, frontend, audio)
- 각 이슈의 최신 이벤트 상세 조회 (스택트레이스, 컨텍스트)

#### 1-2. 중복 체크
- GitHub Issues에서 `label:sentry` + Sentry Issue ID 검색
- 이미 등록된 이슈는 스킵

#### 1-3. GitHub Issue 생성
- 제목: `[Sentry] {project}: {error_title}`
- 본문: 스택트레이스, 발생 횟수, 최초/최근 발생 시간, 영향 서비스
- Labels: `sentry`, `bug`
- Assignee: stopper2008

#### 1-4. 실행 방법
- **자동**: cron 매일 09:00
- **수동**: `/sentry-patrol` 슬래시 커맨드

### Phase 2: Playwright QA 순찰 (Phase 1 이후)

#### 2-1. 순찰 스크립트 (`scripts/qa-patrol.sh`)
- Playwright headless로 핵심 플로우 실행
- 감지 항목: 콘솔 에러, API 4xx/5xx, DOM 요소 부재, 로딩 timeout
- 이상 시 스크린샷 + 에러 로그 수집

#### 2-2. 순찰 플로우 (최소 MVP)
- 홈 접속 → 페이지 로드 확인
- Studio 접속 → 칸반 보드 로드 확인
- 새 영상 → 첫 메시지 전송 → 응답 수신 확인
- 기존 영상 열기 → 씬 데이터 표시 확인

#### 2-3. 실행 방법
- **자동**: cron 매일 09:05 (sentry-patrol 이후)
- **수동**: `/qa-patrol` 슬래시 커맨드

## 완료 기준 (DoD)

### Phase 1 (MVP)
- [ ] `scripts/sentry-patrol.sh` 작동 — Sentry API 조회 + GitHub Issue 생성
- [ ] 중복 이슈 방지 (동일 Sentry Issue ID → 스킵)
- [ ] `/sentry-patrol` 슬래시 커맨드 등록
- [ ] cron 매일 09:00 등록
- [ ] 정상 상태에서 false positive 미발생

### Phase 2
- [ ] Playwright 순찰 스크립트 작동
- [ ] 이상 감지 시 GitHub Issue 자동 생성
- [ ] `/qa-patrol` 슬래시 커맨드 등록
- [ ] cron 등록

## 제약
- SP-018 (Sentry 연동) 완료 후 착수 ✅
- Sentry 무료 플랜 API rate limit: 인증 시 초당 ~20 요청 (배치 1회 충분)
- Sentry API Token 필요 (환경변수: `SENTRY_AUTH_TOKEN`)
- Phase 2는 Phase 1 완료 후 착수

## 힌트
- Sentry API docs: https://docs.sentry.io/api/
- Sentry org: `tomo-playground`
- Sentry projects: `shorts-producer-backend`, `shorts-producer-frontend`, `shorts-producer-audio`
- `gh issue create` 으로 GitHub Issue 생성
- 기존 cron 관리: `.claude/scripts/` 디렉토리
