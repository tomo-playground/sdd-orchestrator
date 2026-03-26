# SP-086: Slack 메시지 템플릿 모듈화

> status: approved | approved_at: 2026-03-26

## 상세 설계 (How)

> [design.md](./design.md) 참조

## 배경

현재 Slack 메시지 Block Kit 구조가 두 파일에 분산·인라인 하드코딩:
- `notify.py` — `do_notify_human()` 알림 블록(15줄), `send_daily_report()` 리포트 블록(40줄) 인라인
- `slack_bot.py` — `_header_block()`, `_section_block()` 등 헬퍼 존재하나 notify.py와 비공유

메시지 종류가 늘어날수록(SP-081 서비스 알림 등) 인라인 복붙이 반복될 구조.

## 목표

Block Kit 헬퍼와 메시지 템플릿을 단일 모듈(`slack_templates.py`)로 추출하여:
1. 메시지 **구성**(what)과 **전송**(how)을 분리
2. 공용 헬퍼 중복 제거
3. 새 메시지 타입 추가 시 템플릿 함수 하나만 작성

## 스코프

- `orchestrator/tools/slack_templates.py` 신규 생성
- `orchestrator/tools/notify.py` — 템플릿 소비로 리팩토링
- `orchestrator/tools/slack_bot.py` — 헬퍼를 templates로 이관, import 변경
- 기존 테스트 유지/업데이트

## 스코프 밖

- 메시지 내용·레이아웃 변경 (동작 동일 유지)
- 새 메시지 타입 추가 (SP-081에서 처리)
- Slack API 전송 로직 변경

## DoD (Definition of Done)

1. `slack_templates.py`에 공용 헬퍼(`header_block`, `section_block`, `divider`, `context_block`, `link_buttons`, `blocks_to_fallback`) 존재
2. `slack_templates.py`에 메시지 템플릿 함수 존재: `notification_blocks()`, `daily_report_blocks()`, `error_blocks()`, `agent_response_blocks()`
3. `notify.py`에서 Block Kit 인라인 구성 코드 제거, 템플릿 함수 호출로 대체
4. `slack_bot.py`에서 로컬 헬퍼(`_header_block` 등) 제거, templates import로 대체
5. 기존 테스트(`test_notify.py`, `test_slack_bot.py`) 통과
6. `slack_templates.py` 단위 테스트 추가
