# Observability Guide

> "옵저버빌리티는 생명이다" — 문제를 모르면 고칠 수 없다.

## 원칙

1. **모든 장애는 알림이 와야 한다** — 사람이 발견하면 이미 늦다
2. **정상도 알린다** — 알림이 안 오면 크론 장애인지 정상인지 구분 불가
3. **알림 채널 단일화** — Slack `#alarm-github` 채널로 통합
4. **실시간 + 배치 이중 감시** — Sentry 실시간 + Patrol 배치 순찰 병행

## 현재 알림 체계

### Slack 알림 (#alarm-github)

| 이벤트 | 소스 | 주기 | 상태 |
|--------|------|------|------|
| Sentry 새 에러 감지 | `sdd-sentry.sh` | 매일 09:03 | **활성** |
| Sentry 이상 없음 | `sdd-sentry.sh` | 매일 09:03 | **활성** |
| QA 테스트 실패 | `sdd-qa.sh` | 매일 09:08 | **활성** |
| QA 전체 통과 | `sdd-qa.sh` | 매일 09:08 | **활성** |
| 서비스 다운 (QA 시점) | `sdd-qa.sh` | 매일 09:08 | **활성** |
| PR/Issue 생성 | GitHub Slack 앱 | 실시간 | **활성** |

### 감시 시스템

| 시스템 | 용도 | 대시보드 |
|--------|------|---------|
| Sentry | 런타임 에러 추적 | tomo-playground.sentry.io |
| LangFuse | AI 파이프라인 트레이싱 | 셀프호스팅 |
| sdd-health.sh | 서비스 헬스체크 | 크론 5분 (로그만) |

### 크론 작업

| 크론 | 스케줄 | 로그 |
|------|--------|------|
| `sdd-health.sh` | */5 * * * * | stdout (로그 없음) |
| `sdd-sentry.sh` | 03 9 * * * | `/tmp/sentry-patrol.log` |
| `sdd-qa.sh` | 08 9 * * * | `/tmp/qa-patrol.log` |

## 알림 구멍 (미해결)

### P0 — 즉시 필요

| 구멍 | 위험도 | 해결 방안 |
|------|--------|----------|
| 서비스 다운 실시간 감지 없음 | **높음** | `sdd-health.sh`에 Slack 알림 추가 (다운 시만) |
| 크론 자체 실패 | **높음** | 크론 wrapper에 `|| notify_slack "CRON FAIL"` 추가 |
| Sentry 실시간 알림 없음 | **중간** | Sentry → Slack 네이티브 연동 (Sentry 웹 설정) |

### P1 — 단기

| 구멍 | 위험도 | 해결 방안 |
|------|--------|----------|
| GitHub Actions 실패 | **중간** | 워크플로우에 Slack 알림 step 추가 |
| Runner 장시간 busy | **중간** | health-check에 runner 상태 체크 추가 |
| 디스크 사용량 경고 | **중간** | health-check에 `df` 임계값 체크 추가 |

### P2 — 중기

| 구멍 | 위험도 | 해결 방안 |
|------|--------|----------|
| GPU 메모리 부족 | **낮음** | `nvidia-smi` 모니터링 추가 |
| 렌더링 큐 적체 | **낮음** | 렌더링 작업 수/대기 시간 모니터링 |

## 환경 변수

| 변수 | 위치 | 용도 |
|------|------|------|
| `SLACK_WEBHOOK_URL` | `backend/.env` | Slack Incoming Webhook |
| `SENTRY_AUTH_TOKEN` | `backend/.env` | Sentry API 인증 |

## 알림 메시지 포맷

```
성공: ✅ *{서비스명}* — 정상 메시지
실패: 🚨 *{서비스명}* — 에러 상세
다운: 🔥 *{서비스명}* — 서비스 다운
경고: ⚠️ *{서비스명}* — 경고 메시지
```

## Slack 알림 함수 (스크립트용)

```bash
notify_slack() {
  local text="$1"
  if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    curl -sf -X POST "$SLACK_WEBHOOK_URL" \
      -H 'Content-Type: application/json' \
      -d "{\"text\": \"${text}\"}" >/dev/null 2>&1 || true
  fi
}
```

## 트러블슈팅

### 알림이 안 올 때
1. `backend/.env`에 `SLACK_WEBHOOK_URL` 확인
2. `crontab -l`로 크론 등록 확인
3. 크론 로그 확인: `cat /tmp/sentry-patrol.log`
4. Webhook 테스트: `curl -X POST "$SLACK_WEBHOOK_URL" -d '{"text":"test"}'`

### 알림이 너무 많을 때
- Sentry: Issue grouping 설정으로 중복 줄이기
- QA: 테스트 locator 업데이트 (UI 변경 후 필수)
- health-check: 다운 시에만 알림 (정상은 무시)
