---
id: SP-082
priority: P1
scope: infra
branch: feat/SP-082-slack-bot-claude-agent
created: 2026-03-26
approved_at: 2026-03-26
depends_on:
label: feature
---

## 무엇을 (What)
Slack Bot의 키워드 매칭 방식을 제거하고, 모든 메시지를 Claude Agent SDK(구독 기반)로 처리. 자연어로 오케스트레이터를 제어.

## 왜 (Why)
현재 Slack Bot은 `상태`, `실행`, `머지` 등 6개 키워드만 인식. "SP-084 어떻게 되고 있어?", "머지할 수 있는 PR 있어?" 같은 자연어를 처리 못 함. Claude Agent SDK를 활용하면 자연어 이해 + 도구 자율 호출이 가능하고, 추가 API 비용 없이 구독으로 동작.

## 완료 기준 (DoD)

### Phase A: Claude Agent 통합
- [ ] `_dispatch_command`의 키워드 매칭 → Claude Agent 단일 경로로 전환
- [ ] 기존 명령 함수들(`_cmd_status`, `_cmd_launch` 등)을 MCP tool로 래핑
- [ ] Claude Agent에 시스템 프롬프트 설정 (역할 + 사용 가능 도구 + 응답 규칙)
- [ ] Agent 응답을 Block Kit 포맷으로 변환하여 Slack 전송

### Phase B: 도구 정의
- [ ] 기존 Slack Bot 명령을 도구로 변환:
  - `get_status` — 현재 태스크/PR/워크트리 상태
  - `launch_task` — SDD 태스크 실행 (SP-NNN)
  - `merge_pr` — PR 머지 (#NNN)
  - `pause_orchestrator` / `resume_orchestrator` — 일시정지/재개
  - `get_backlog` — 백로그 조회
- [ ] 오케스트레이터 기존 도구 재사용 (scan_backlog, check_prs 등)

### Phase C: 응답 품질
- [ ] 한국어 응답 강제
- [ ] Block Kit 포맷 (header + section + actions)
- [ ] 응답 길이 제한 (Slack 4000자)
- [ ] 에러 시 사용자 친화적 메시지

### 공통
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과
- [ ] 채널/사용자 allowlist 기존 로직 유지

## 상세 설계 (How)

> [design.md](./design.md) 참조

## 힌트
- `claude_agent_sdk`가 이미 오케스트레이터에서 사용 중 (`orchestrator/utils.py`)
- `query_agent()` 패턴 재사용 가능
- Lead Agent(config.py 시스템 프롬프트)와 유사한 구조
- 기존 `_cmd_*` 함수의 로직은 그대로 — 래핑만 변경
- `ClaudeAgentOptions`에 `allowed_tools` 지정 가능

## 참고
- 현재 Slack Bot: `orchestrator/tools/slack_bot.py`
- Agent SDK 사용 예: `orchestrator/utils.py`, `orchestrator/agents.py`
- 시스템 프롬프트 예: `orchestrator/config.py` LEAD_AGENT_SYSTEM_PROMPT
