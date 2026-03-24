---
id: SP-076
priority: P1
scope: infra
branch: feat/SP-076-slack-bot
created: 2026-03-24
status: done
approved_at: 2026-03-24
depends_on:
label: feat
---

## 무엇을 (What)
Slack Bot으로 코딩머신과 양방향 대화. Slack에서 명령 수신 → 오케스트레이터 실행.

## 왜 (Why)
현재 코딩머신 제어는 터미널(Claude Code CLI)에서만 가능. Slack Bot이 있으면 모바일에서도 태스크 등록/실행/머지/상태 확인 가능.

## 완료 기준 (DoD)

### Slack App 설정
- [ ] Slack App 생성 (Bot Token + Event Subscriptions)
- [ ] `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET` 환경변수 추가
- [ ] Event: `app_mention`, `message.channels` 수신

### 명령 처리
- [ ] `orchestrator/tools/slack_bot.py` — Slack 이벤트 수신 + 명령 파싱
- [ ] 지원 명령:
  - `상태` → 현재 태스크/PR/워크트리 상태 응답
  - `실행 SP-NNN` → launch_sdd_run 트리거
  - `머지 #NNN` → merge_pr 트리거
  - `중지` / `시작` → 코딩머신 일시정지/재개
  - `백로그` → backlog 상위 5개 표시
- [ ] 미인식 명령 → "사용 가능한 명령: ..." 안내

### 알림 품질 개선 (notify_human + shell 스크립트)
- [ ] **메시지 형식 표준화**: shell 3곳(플레인 텍스트) + notify.py(Block Kit) → 전부 Block Kit 통합
  - 방안 A: shell에서 `notify.py`를 CLI로 호출 (`uv run python -m orchestrator.tools.notify ...`)
  - 방안 B: 공통 shell 함수(`_notify_slack()`)에 Block Kit JSON 템플릿 적용
- [ ] `notify_human` 도구에 optional `links` 필드 추가 → Block Kit 버튼으로 렌더링
- [ ] 오케스트레이터 시스템 프롬프트에 "알림 시 관련 링크 필수 포함" 규칙 추가
- [ ] shell 스크립트 알림(sdd-health/sentry/qa)에 GitHub Actions run URL 추가
- [ ] 좀비 워크트리 등 액션 필요 알림 → 조치 명령어 코드 블록 + 관련 PR 링크 포함

### 응답 포맷
- [ ] Block Kit으로 깔끔한 응답 (기존 notify.py 패턴 재사용)
- [ ] 명령 실행 결과를 스레드로 응답

### 통합
- [ ] 코딩머신 사이클에 Slack 이벤트 폴링 통합 (또는 별도 웹서버)
- [ ] 기존 Webhook 알림과 공존
- [ ] 린트 통과

## 제약
- Slack 무료 플랜 호환 (Bot + Webhook)
- 복잡한 대화(멀티턴)는 Out of Scope — 단일 명령 + 응답
- 보안: Slack Signing Secret 검증 필수

## 상세 설계 (How)
> [design.md](./design.md) 참조

## 힌트
- Slack Bolt (Python SDK): `pip install slack-bolt`
- Socket Mode 사용 시 웹서버 불필요 (무료 플랜 호환)
- 기존 `orchestrator/tools/notify.py`의 Block Kit 패턴 재사용
