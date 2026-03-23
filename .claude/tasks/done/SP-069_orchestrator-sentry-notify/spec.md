---
id: SP-069
priority: P0
scope: infra
branch: feat/SP-069-orchestrator-sentry-notify
created: 2026-03-23
status: done
approved_at: 2026-03-23
depends_on: SP-068
label: feat
---

## 무엇을 (What)
오케스트레이터에 Sentry 에러 자동 수집/수정 + Slack 알림 + GitHub Actions 제어를 통합한다.

## 왜 (Why)
Phase 3까지 완성되면 태스크 실행은 자동이지만, Sentry 에러 대응과 사람 알림이 빠져있다. 이 단계에서 기존 GitHub Actions(sentry-patrol, sentry-autofix)를 오케스트레이터가 제어하고, 사람에게는 판단 필요 시에만 알림을 보낸다.

## 완료 기준 (DoD)

### Sentry 연동

- [x] `orchestrator/tools/sentry.py` — `sentry_scan` 도구: Sentry API로 미해결 에러 목록 조회
- [x] 1시간마다 Sentry 스캔 → 신규 에러 발견 시 GitHub Issue 자동 생성 (기존 sentry-patrol 로직)
- [x] Issue 생성 후 `gh workflow run sentry-autofix.yml` 자동 트리거
- [x] autofix PR 생성 → SP-067의 PR 모니터링/자동 머지 파이프라인에 합류

### GitHub Actions 제어

- [x] `orchestrator/tools/github.py` — `trigger_workflow` 도구: 워크플로우 수동 트리거
- [x] `cancel_workflow` 도구: stuck 워크플로우 취소 (30분 초과 시)
- [x] 오케스트레이터가 기존 GHA(claude-review, sdd-review, sdd-sync)의 상태를 모니터링하고, stuck/실패 시 재실행 또는 취소 판단

### Slack 알림

- [x] `orchestrator/tools/notify.py` — `notify_human` 도구: Slack Webhook으로 메시지 전송
- [x] 알림 조건:
  - 설계에 BLOCKER 발견 (자동 승인 불가)
  - CI 3회 연속 실패
  - Sentry critical 에러
  - DB 스키마 변경 감지
  - PR에 사람이 changes_requested
- [x] 일일 요약 리포트 (완료 태스크, 진행 중, 블로커)

### 일일 리포트

- [x] 매일 09:00에 전일 활동 요약을 Slack으로 전송:
  - 완료된 PR/태스크
  - 진행 중인 작업
  - 블로커/실패 항목
  - Sentry 에러 현황

### 통합

- [x] 전체 파이프라인: spec 작성 → 자동 설계 → 자동 승인 → 자동 구현 → 자동 리뷰 → 자동 머지 → Sentry 모니터링
- [x] 사람은 spec 작성 + BLOCKER 알림 대응만
- [x] 린트 통과

## 제약
- Slack Webhook URL은 환경변수로 관리
- Sentry API Token은 기존 backend/.env의 `SENTRY_API_TOKEN` 재활용
- 기존 GitHub Actions 워크플로우 파일은 수정하지 않음 (트리거만)

## 힌트
- Slack Webhook: `curl -X POST -H 'Content-type: application/json' --data '{"text":"..."}' $SLACK_WEBHOOK_URL`
- Sentry API: `curl -H "Authorization: Bearer $SENTRY_API_TOKEN" https://sentry.io/api/0/projects/.../issues/`
- 기존 sentry-patrol.yml, sentry-autofix.yml 로직 참조
