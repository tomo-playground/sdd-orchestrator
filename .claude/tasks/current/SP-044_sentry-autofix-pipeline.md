---
id: SP-044
priority: P1
scope: infra
branch: feat/SP-044-sentry-autofix
created: 2026-03-21
status: pending
depends_on:
label: enhancement
reviewer: stopper2008
assignee: stopper2008
---

## 무엇을
Sentry 에러 → 자동 수정 → PR → 사람은 머지만 하는 완전 자동화 파이프라인

## 왜
현재: Sentry 에러 → GitHub Issue (자동) → 사람이 태스크 작성 → /sdd-run → PR
목표: Sentry 에러 → GitHub Issue → Claude가 분석 + 테스트 + 수정 → PR → 사람은 머지만

사람이 개입하는 구간을 **머지 판단 1곳**으로 줄인다.

## 전체 흐름

```
sentry-patrol (매일 cron)
  → Sentry 에러 감지 → GitHub Issue 생성 (label: sentry, bug)
  ↓
sentry-autofix.yml (issue created 트리거)
  → Claude가 Issue 읽기
  → 스택트레이스 분석 → 원인 파악
  → 실패 테스트 작성 (TDD)
  → 코드 수정 → 테스트 GREEN 확인
  → PR 생성 (Issue 링크)
  ↓
claude-review + CodeRabbit (자동 리뷰)
  ↓
사람: PR 확인 → 머지
```

## 실패 테스트 (TDD)

```python
# backend/tests/test_sentry_autofix.py

def test_sentry_issue_triggers_autofix_workflow():
    """GitHub Issue(label:sentry) 생성 시 sentry-autofix.yml이 트리거되는지"""
    # workflow 파일에 issues.labeled 트리거 존재 확인
    import yaml
    with open(".github/workflows/sentry-autofix.yml") as f:
        wf = yaml.safe_load(f)
    assert "issues" in wf["on"]

def test_autofix_creates_pr_for_sentry_issue():
    """Claude가 Issue를 읽고 PR을 생성하는지 (E2E — 수동 검증)"""
    # 이 테스트는 실제 GitHub API 호출이 필요하므로
    # workflow 실행 후 PR 존재 여부로 검증
    pass
```

## 완료 기준 (DoD)
- [ ] `sentry-autofix.yml` 워크플로우 생성
  - 트리거: `issues` labeled `sentry`
  - Claude가 Issue 본문(스택트레이스) 읽기
  - 원인 분석 → 실패 테스트 작성 → 코드 수정 → PR 생성
- [ ] PR 본문에 원본 Issue 링크 포함 (`Fixes #NNN`)
- [ ] PR 생성 시 Claude 리뷰 + CodeRabbit 리뷰 자동 실행
- [ ] 실제 Sentry 에러로 E2E 테스트 (수동)
- [ ] 기존 sentry-patrol, sdd-review 워크플로우와 충돌 없음

## Git 워크플로우

- **브랜치**: `fix/sentry-{issue번호}` 자동 생성 (예: `fix/sentry-106`)
- **동시성**: `concurrency: group: sentry-autofix, cancel-in-progress: false` — 순차 실행
- **보호**: main 직접 push 불가 — PR 필수 (현행 유지)
- **자동 머지 금지**: 리뷰 통과해도 사람이 머지 판단
- **실패 처리**: 수정 불가 시 Issue에 `needs-manual-fix` 라벨 추가, PR 생성 안 함

## 제약
- `sentry-autofix.yml` + 필요 시 `sentry-patrol.sh` 수정 = 최대 3개 파일
- Claude가 수정 불가능한 에러(외부 서비스 장애 등)는 Issue에 코멘트만 남기고 PR 생성 안 함
- DB 스키마 변경이 필요한 에러는 자동 수정 대상에서 제외 (Issue에 "수동 대응 필요" 라벨)

## 힌트

### sentry-autofix.yml 구조
```yaml
name: Sentry Autofix

on:
  issues:
    types: [labeled]

jobs:
  autofix:
    if: contains(github.event.label.name, 'sentry')
    runs-on: [self-hosted, sdd]
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          prompt: |
            GitHub Issue #${{ github.event.issue.number }}를 읽고 버그를 수정하세요.

            1. Issue 본문의 스택트레이스를 분석하세요
            2. 원인이 되는 코드를 찾으세요
            3. 실패 테스트를 먼저 작성하세요 (TDD)
            4. 테스트가 통과하도록 코드를 수정하세요
            5. fix/ 브랜치에서 커밋 + push + PR 생성
            6. PR 본문에 "Fixes #${{ github.event.issue.number }}" 포함
            7. 수정 불가(외부 장애, DB 변경 필요)면 Issue에 코멘트만 남기세요
```
