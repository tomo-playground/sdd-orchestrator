---
id: SP-108
priority: P0
scope: orchestrator
branch: feat/SP-108-orch-slack-unify
created: 2026-03-28
status: done
approved_at: 2026-03-28
depends_on:
label: refactor
---

## 무엇을 (What)
오케스트레이터의 Slack 발송 경로를 SlackBot 단일 경로로 통일.

## 왜 (Why)
현재 2개 경로가 공존:
1. `SlackBot._post_message()` (Socket Mode, `_active_threads` 등록 → 스레드 답글 대화 가능)
2. `notify.py:_send_slack_message()` (httpx REST, `_active_threads` 미등록 → 일방향)

문제:
- 알림/리포트에 스레드 답글로 명령할 수 없음 (Bot이 스레드를 인식 못함)
- rate limit, 에러 핸들링이 2곳에서 각각 구현 — 중복 + 불일치
- `set_slack_bot()` 브릿지로 임시 패치했지만 근본 해결이 아님

## 완료 기준 (DoD)

### Must (P0)
- [ ] `notify.py:_send_slack_message()` (httpx) 제거
- [ ] 모든 발송이 `SlackBot._post_message()` 경유
- [ ] `do_notify_human()`, `send_daily_report()` → SlackBot 인스턴스 메서드 호출
- [ ] 발송된 모든 메시지가 자동으로 `_active_threads` 등록 → 스레드 답글 대화 가능
- [ ] 기존 테스트 통과 + notify 테스트 업데이트

### Should (P1)
- [ ] SlackBot 미연결 시 fallback (로그 출력) 유지
- [ ] rate limit 로직 SlackBot._post_message() 하나로 통합

## 힌트
- `SlackBot`을 싱글턴으로 유지, `notify.py`에서 import해서 사용
- SlackBot이 아직 start 안 됐을 때(토큰 미설정 등) → `_post_message`가 no-op + 로그 fallback
- `_send_slack_message()`의 httpx 로직은 제거, `SlackBot._post_message()`의 `AsyncWebClient.chat_postMessage`로 대체
- `set_slack_bot()` 브릿지도 제거 (직접 참조)
