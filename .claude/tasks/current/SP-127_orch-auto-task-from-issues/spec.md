# SP-127: 오케스트레이터 — GitHub Issue → 태스크 자동 생성

- **branch**: feat/SP-127_orch-auto-task-from-issues
- **priority**: P2
- **scope**: sdd-orchestrator
- **assignee**: AI
- **created**: 2026-03-31

## 배경

현재 GitHub Issue가 생성되어도 수동으로 태스크(spec.md)를 만들어야 함.
오케스트레이터가 열린 Issue를 스캔하고 태스크를 자동 생성하면 PM 역할 자동화.

### 현재 흐름 (수동)
```
Sentry → Issue 자동 생성 → [사람이 태스크 수동 생성] → 오케스트레이터 실행
```

### 목표 흐름 (자동)
```
Sentry → Issue 자동 생성 → 오케스트레이터가 태스크 자동 생성 → auto-design → 실행
```

## DoD (Definition of Done)

- [ ] 오케스트레이터 도구 `scan_issues` 추가: 열린 GitHub Issue 중 태스크 미연결 건 감지
- [ ] `auto_create_task` 도구 추가: Issue 본문에서 정보 추출 → spec.md 생성 + state.db 등록
- [ ] 이미 태스크가 있는 Issue는 스킵 (Issue 번호 ↔ SP-NNN 매핑)
- [ ] label 기반 필터: `sentry`, `bug` 라벨만 대상 (feature request 등 제외)
- [ ] 사이클에 scan_issues 단계 추가
- [ ] 우선순위 자동 판정: sentry=P1, bug=P2

## 수정 대상 파일

- `sdd-orchestrator/src/sdd_orchestrator/tools/issues.py` (신규)
- `sdd-orchestrator/src/sdd_orchestrator/tools/__init__.py`
- `sdd-orchestrator/src/sdd_orchestrator/prompts/lead_agent.md`
