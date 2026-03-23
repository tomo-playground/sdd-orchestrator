# SDD Orchestrator 사용 가이드

## 개요

오케스트레이터는 SDD 워크플로우를 자동화하는 상주 프로세스입니다.
10분마다 backlog/PR/워크플로우를 스캔하고, 태스크 실행/리뷰/머지를 자동 수행합니다.

---

## 기동/중지

```bash
# 시작
.claude/scripts/sdd-orch.sh start

# 중지
.claude/scripts/sdd-orch.sh stop

# 상태 확인
.claude/scripts/sdd-orch.sh status

# 재시작
.claude/scripts/sdd-orch.sh restart
```

로그: `/tmp/orchestrator.log`

---

## 태스크 등록 방법

### Step 1: backlog에 한 줄 추가

`.claude/tasks/backlog.md`:
```markdown
## P1 (최우선)

- [ ] SP-076 — 캐릭터 프리뷰 자동 갱신 | scope: backend
```

### Step 2: spec.md 작성

```bash
mkdir -p .claude/tasks/current/SP-076_preview-auto-regen
```

`.claude/tasks/current/SP-076_preview-auto-regen/spec.md`:
```markdown
---
id: SP-076
priority: P1
scope: backend
branch: feat/SP-076-preview-auto-regen
created: 2026-03-24
status: pending
depends_on:
label: feat
---

## 무엇을 (What)
캐릭터 태그 변경 시 프리뷰 이미지 자동 재생성

## 왜 (Why)
태그 변경 후 수동으로 프리뷰를 재생성해야 하는 번거로움 제거

## 완료 기준 (DoD)
- [ ] 태그 변경 감지 → 프리뷰 큐 등록
- [ ] 큐 소비 → SD 이미지 생성 → media_asset 저장
- [ ] 기존 테스트 영향 없음
```

### Step 3: main에 커밋

```bash
git add .claude/tasks/
git commit -m "chore: SP-076 태스크 등록"
git push
```

### Step 4: 기다리기

오케스트레이터가 10분 내에 자동으로:
1. `pending` 감지 → 설계 작성 (design.md)
2. 조건 충족 → 자동 승인 (`status: approved`)
3. 워크트리에서 `/sdd-run` 실행
4. PR 생성 → CI/리뷰 → 자동 머지

---

## 수동 개입이 필요한 경우

| 상황 | Slack 알림 | 대응 |
|------|-----------|------|
| 설계에 BLOCKER | O | `/sdd-design SP-076 approved` 또는 `reject` |
| DB 스키마 변경 포함 | O | 설계 확인 후 수동 승인 |
| CI 3회 연속 실패 | O | 로그 확인 후 수동 수정 |
| Sentry critical 에러 | O | autofix PR 검수 + 머지 |

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ORCH_AUTO_RUN` | `0` | `1`이면 자동 실행 활성화 |
| `ORCH_AUTO_DESIGN` | `0` | `1`이면 자동 설계 활성화 |
| `ORCH_MAX_PARALLEL` | `2` | 동시 워크트리 실행 수 |
| `SLACK_WEBHOOK_URL` | - | Slack 알림 Webhook URL |

---

## 직접 실행 (오케스트레이터 없이)

오케스트레이터 없이도 기존 CLI로 동일한 작업 가능:

```bash
# 설계
/sdd-design SP-076

# 승인
/sdd-design SP-076 approved

# 실행 (워크트리)
! claude --worktree SP-076 --dangerously-skip-permissions -p "/sdd-run SP-076"

# 리뷰
/sdd-review

# 수정
/sdd-fix

# 정리
/sdd-sync
```

오케스트레이터는 이 과정을 **자동 반복**하는 것뿐입니다.

---

## 모니터링

```bash
# 오케스트레이터 상태
.claude/scripts/sdd-orch.sh status

# 실시간 로그
tail -f /tmp/orchestrator.log

# 열린 PR 확인
gh pr list --state open

# 워크트리 확인
git worktree list
```
