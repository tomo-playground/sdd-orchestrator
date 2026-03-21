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
AI QA 자동 순찰 + 자동 수정 — Playwright headless 정기 실행 → 이상 감지 → Sentry(qa 프로젝트) 이벤트 → GitHub Issue 자동 생성 → Claude 자동 수정 PR

## 왜
- 사람이 직접 서비스를 사용하며 버그를 찾는 건 비효율적
- 발견 → 리포트 → 수정까지 전자동 루프가 목표
- 사람은 Slack 알림만 확인

## 아키텍처

```
cron (30분 간격)
  → Playwright headless 핵심 플로우 실행
  → 이상 감지 시 Sentry(shorts-producer-qa) 이벤트 전송
  → Sentry Alert Rule → GitHub Issue 자동 생성 (label: qa-patrol)
  → GitHub Actions sdd-autofix.yml 트리거
  → Claude가 Issue 읽고 자동 수정 PR 생성
  → Slack 알림
```

## 구현 범위

### 1. 순찰 스크립트 (`scripts/qa-patrol.sh`)
- Playwright headless로 핵심 플로우 실행
- 감지 항목: 콘솔 에러, API 4xx/5xx, DOM 요소 부재, 로딩 timeout
- 이상 시 스크린샷 + 에러 로그 수집
- Sentry `capture_message()` 로 qa 프로젝트에 전송

### 2. 순찰 플로우 (최소 MVP)
- 홈 접속 → 페이지 로드 확인
- Studio 접속 → 칸반 보드 로드 확인
- 새 영상 → 첫 메시지 전송 → 응답 수신 확인
- 기존 영상 열기 → 씬 데이터 표시 확인
- 설정 페이지 → 로드 확인

### 3. Sentry qa 프로젝트 설정
- `shorts-producer-qa` 프로젝트 생성 (app과 분리)
- Alert Rule: 새 이벤트 → GitHub Issue 자동 생성 (label: qa-patrol)

### 4. GitHub Actions (`sdd-autofix.yml`)
- `issues.opened` 이벤트 + label `sentry` 또는 `qa-patrol`
- Claude가 Issue 읽고 원인 분석 → 수정 PR 생성
- timeout 10분 안전장치

### 5. cron 등록
- 30분 간격 실행 (조정 가능)

## Sentry 프로젝트 분리
- `shorts-producer-app`: 어플리케이션 런타임 에러 (SP-018)
- `shorts-producer-qa`: AI QA 순찰 감지 이슈 (SP-019)

## 완료 기준 (DoD)
- [ ] 순찰 스크립트 작동 (headless Playwright)
- [ ] 이상 감지 시 Sentry qa 프로젝트에 이벤트 전송
- [ ] Sentry → GitHub Issue 자동 생성
- [ ] sdd-autofix.yml 워크플로우 추가 + 테스트
- [ ] cron 등록 (30분 간격)
- [ ] 정상 상태에서 false positive 미발생
- [ ] Slack 알림 동작 확인

## 제약
- SP-018 (Sentry 연동) 완료 후 착수
- Sentry 무료 플랜 한도 고려 (5K events/월) — 순찰 이벤트는 이상 시에만 전송
- 실제 API 호출 (Gemini/SD) 테스트는 제외 — UI + API 응답 레벨만 검사
