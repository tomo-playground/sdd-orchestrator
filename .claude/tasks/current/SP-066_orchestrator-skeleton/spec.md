---
id: SP-066
priority: P0
scope: infra
branch: feat/SP-066-orchestrator-skeleton
created: 2026-03-23
status: approved
depends_on:
label: feat
---

## 무엇을 (What)
Claude Agent SDK 기반 SDD 오케스트레이터의 뼈대를 만든다. 상주 프로세스로 실행되며, backlog를 읽고, 상태를 추적하고, 사람에게 보고하는 최소 루프를 구현한다.

## 왜 (Why)
현재 SDD 워크플로우는 사람이 매 세션마다 부팅 → 태스크 선택 → 설계 승인 → /sdd-run 기동 → PR 확인을 수동으로 한다. 오케스트레이터가 이 판단 루프를 자동화하면 사람은 "뭘 만들지"만 결정하면 된다.

## 완료 기준 (DoD)

### 프로젝트 구조

- [ ] `orchestrator/` 디렉토리에 Agent SDK 기반 Python 프로젝트를 생성한다
- [ ] `pyproject.toml` 또는 `requirements.txt`에 `claude-agent-sdk` 의존성을 정의한다
- [ ] `orchestrator/main.py`에 이벤트 루프 진입점을 구현한다 (10분 주기 루프)

### 커스텀 도구

- [ ] `orchestrator/tools/backlog.py` — `scan_backlog` 도구: `.claude/tasks/backlog.md`를 파싱하여 태스크 목록(id, status, priority, depends_on) 반환
- [ ] `orchestrator/tools/github.py` — `check_pr` 도구: `gh pr list --json` 래퍼, PR 상태/리뷰/CI 체크 반환
- [ ] `orchestrator/tools/github.py` — `check_workflows` 도구: `gh run list --json` 래퍼, 실행 중/실패 워크플로우 반환

### 상태 관리

- [ ] `orchestrator/state.py` — SQLite 기반 상태 저장소 (cycles, decision_log 테이블)
- [ ] 오케스트레이터 시작 시 이전 상태를 로드하고, 종료 시 상태를 저장한다

### Lead Agent

- [ ] `orchestrator/agents.py` — Lead Agent 정의: Sonnet 모델, 커스텀 도구 연결, 시스템 프롬프트
- [ ] Lead Agent 시스템 프롬프트에 SDD 워크플로우 규칙(CLAUDE.md 핵심 규칙)을 포함한다
- [ ] 10분마다 현재 상태를 Lead Agent에 전달하고, 다음 행동 판단을 받는다

### 실행 가능성

- [ ] `python -m orchestrator.main` 으로 실행 가능하다
- [ ] 첫 실행 시 backlog를 읽고 현재 상태를 콘솔에 출력한다 (대시보드 형태)
- [ ] Ctrl+C로 graceful shutdown된다 (상태 저장 후 종료)

### 품질

- [ ] 기존 프로젝트(backend/frontend) 테스트에 영향 없음
- [ ] orchestrator 자체 단위 테스트 통과 (backlog 파서, gh CLI 래퍼, StateStore)
- [ ] 린트 통과 (ruff)

## 영향 분석
- `orchestrator/` 디렉토리 신규 생성 — 기존 코드와 완전 독립
- Agent SDK 의존성 추가 — 오케스트레이터 전용, backend/frontend에 영향 없음

## 제약
- Phase 1에서는 **읽기 전용** — backlog 읽기, PR 상태 확인만. 자동 실행/머지는 SP-067
- 서브에이전트(designer, implementer) 정의 및 기동은 SP-067~068 (Phase 1은 Lead Agent만)
- Slack 알림은 SP-069

## 힌트
- Agent SDK: `claude_agent_sdk.query()`, `ClaudeAgentOptions`, `@tool`, `create_sdk_mcp_server`
- backlog 파싱: 마크다운 체크박스 `- [ ] SP-NNN — ...` 패턴
- gh CLI: `gh pr list --json number,title,state,reviews,statusCheckRollup`
