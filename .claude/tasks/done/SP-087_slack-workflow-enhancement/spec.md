# SP-087: Slack 워크플로우 강화 — Slack에서 SDD 업무 전체 수행

branch: worktree-SP-087
> status: approved | approved_at: 2026-03-26

## 상세 설계 (How)

> [design.md](./design.md) 참조

## 배경

SlackBot Agent가 12개 MCP 도구를 갖추고 있지만 실전 활용에 3가지 문제:

1. **정확도 문제 (A)**: `scan_backlog`이 blockquote 형식의 status를 파싱 못함 (`> status: approved` → 기본값 `pending` 반환). Agent 프롬프트가 SDD 워크플로우 맥락을 이해하지 못해 도구를 부정확하게 사용.
2. **도구 부재 (B)**: 태스크 상세 조회(`read_task`), 설계 승인(`approve_design`), 태스크 생성(`create_task`) 도구 없음 → Slack에서 SDD 워크플로우 전체를 수행할 수 없음.
3. **모델 한계 (C)**: Haiku 모델이 복잡한 상황 판단에서 부정확한 응답 생성. 모델 선택이 하드코딩.

## 목표

Slack을 SDD 워크플로우의 **1급 인터페이스**로 만들어, 터미널 없이 Slack만으로:
- 태스크 상태 정확히 조회
- 태스크 생성 → 설계 승인 → 구현 실행 → PR 머지까지 전체 흐름 수행
- 모델 품질에 맞는 정확한 응답 제공

## 스코프

### A. 기존 정확도 개선
- `backlog.py` — status 파싱 정규식 수정 (blockquote `>` prefix 허용)
- `config.py` — `SLACK_BOT_AGENT_PROMPT` 강화 (SDD 워크플로우 상태 머신, 도구 사용 판단 기준, 태스크 라이프사이클 설명)

### B. 신규 MCP 도구 추가
- `read_task` — 특정 태스크의 spec.md/design.md 내용 반환
- `approve_design` — 설계 승인 (status 업데이트 + git commit)
- `create_task` — 태스크 디렉토리 + spec.md 생성
- `agents.py` — `_SLACK_BOT_TOOLS`에 신규 도구 등록

### C. 모델 업그레이드
- `SLACK_BOT_AGENT_MODEL` 환경변수화 (기본값 Sonnet)
- `SLACK_BOT_MAX_TURNS` 조정 검토
- `SLACK_BOT_AGENT_TIMEOUT` 조정 (Sonnet은 Haiku보다 느림)

## 스코프 밖

- SlackBot UI 변경 (Block Kit 레이아웃은 SP-086에서)
- Lead Agent 도구 변경
- 새 Slack 이벤트 핸들러 추가

## DoD (Definition of Done)

1. `scan_backlog`이 `> status: approved` blockquote 형식을 정확히 파싱
2. Agent 프롬프트에 SDD 워크플로우 상태 머신 + 도구 판단 기준 포함
3. `read_task` 도구: task_id → spec.md + design.md 내용 반환
4. `approve_design` 도구: task_id → status 업데이트 + git commit + 결과 반환
5. `create_task` 도구: task_id + title + description → 디렉토리 + spec.md 생성
6. `_SLACK_BOT_TOOLS`에 3개 도구 등록, 프롬프트에 사용법 추가
7. `SLACK_BOT_AGENT_MODEL` 환경변수 대응, 기본값 Sonnet
8. 타임아웃/턴 수 Sonnet 기준 조정
9. 기존 테스트 통과 + 신규 도구 단위 테스트 추가
