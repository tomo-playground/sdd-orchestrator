# SDD Orchestrator 사용 가이드

## 개요

오케스트레이터는 SDD 워크플로우를 **완전 자동화**하는 상주 프로세스입니다.
10분마다 backlog/PR/Sentry/워크플로우를 스캔하고, 태스크 설계/실행/리뷰/머지 + 에러 대응을 자동 수행합니다.

---

## 첫 기동 (최초 1회)

### 1. 시스템 의존성

```bash
# sqlite3 CLI (sdd-sync.sh에서 state.db 업데이트에 필요)
sudo apt-get install -y sqlite3
```

### 2. 환경변수 확인

`backend/.env`에 아래가 있어야 합니다:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...  # #sdd-bot 채널
SENTRY_API_TOKEN=...                                     # Sentry API 토큰
```

### 3. 기동

```bash
.claude/scripts/sdd-orch.sh start
```

### 4. 확인

```bash
.claude/scripts/sdd-orch.sh status
tail -f sdd-orchestrator/logs/orchestrator.log
```

Slack `#sdd-bot`에 첫 사이클 리포트가 오면 정상.

### 데이터 저장소

| 파일 | 역할 |
|------|------|
| `.sdd/state.db` | 태스크 상태 SSOT (SQLite). 사이클/실행/롤백/태스크 상태 기록 |
| `sdd-orchestrator/logs/orchestrator.log` | 오케스트레이터 로그 |

---

## 기동/중지

```bash
.claude/scripts/sdd-orch.sh start    # 기동
.claude/scripts/sdd-orch.sh stop     # 중지
.claude/scripts/sdd-orch.sh status   # 상태
.claude/scripts/sdd-orch.sh restart  # 재시작
```

서버 재시작 시 `@reboot` cron으로 자동 기동됨.

---

## 사용 방법

### 새 기능 등록

**Step 1.** backlog에 한 줄 추가 (`.claude/tasks/backlog.md`):
```markdown
- [ ] SP-077 — 기능 설명 | scope: backend
```

**Step 2.** spec.md 작성:
```bash
mkdir -p .claude/tasks/current/SP-077_기능설명
```
```markdown
---
id: SP-077
priority: P1
scope: backend
branch: feat/SP-077-기능설명
status: pending
---

## 무엇을 (What)
한 줄 설명

## 완료 기준 (DoD)
- [ ] 구현 항목 1
- [ ] 구현 항목 2
```

**Step 3.** main에 커밋 + push

**Step 4.** 기다리기 — 오케스트레이터가 자동으로:
```
pending 감지 → 설계 작성 → 자동 승인 → 워크트리 실행 → PR → 리뷰 → 머지
```

### Sentry 에러 대응 (자동)

```
Sentry 에러 감지 → GitHub Issue 생성 → autofix PR → 리뷰 → Slack 알림
```

사람은 Slack 알림 확인 + PR 검수/머지만.

---

## Slack 알림 (#sdd-bot)

| 알림 | 시점 |
|------|------|
| 설계 BLOCKER 발견 | 자동 승인 불가 → 사람 판단 필요 |
| CI 3회 연속 실패 | 태스크 blocked |
| Sentry critical 에러 | autofix PR 생성됨 |
| DB 스키마 변경 감지 | 사람 승인 필수 |
| 사람이 changes_requested | sdd-fix 트리거 |
| APPROVED + WARNING 잔존 | PR에 `@claude` 멘션 → sdd-fix manual job |
| 일일 리포트 (09:00) | 전일 완료/진행/블로커 요약 |

---

## 수동 개입이 필요한 경우

| Slack 알림 | 대응 |
|-----------|------|
| BLOCKER 설계 | `claude` → `/sdd-design SP-NNN approved` 또는 `reject` |
| DB 스키마 변경 | 설계 확인 → 수동 승인 |
| CI 실패 | 로그 확인 → 수동 수정 또는 태스크 스펙 수정 |
| Sentry autofix PR | 동작 검수 → 머지 |

---

## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `ORCH_AUTO_RUN` | `0` | `1`이면 자동 실행 활성화 |
| `ORCH_AUTO_DESIGN` | `0` | `1`이면 자동 설계 활성화 |
| `ORCH_MAX_PARALLEL` | `2` | 동시 워크트리 실행 수 |
| `SLACK_WEBHOOK_URL` | — | Slack Webhook URL (#sdd-bot) |
| `SENTRY_API_TOKEN` | — | Sentry API 인증 토큰 |

---

## 직접 실행 (오케스트레이터 없이)

```bash
/sdd-design SP-077                   # 설계
/sdd-design SP-077 approved          # 승인
! claude --worktree SP-077 ...       # 실행
/sdd-review                          # 리뷰
/sdd-fix                             # 수정
/sdd-sync                            # 정리
```

오케스트레이터는 이 과정을 **자동 반복**하는 것뿐입니다.

---

## Worktree 관리

### 네이밍 규칙
모든 `--worktree` 호출은 **`SP-NNN`** 형식으로 통일.
브랜치 전체명(`feat/SP-NNN_*`)을 넘기지 않는다.

### 생성 전 방어 로직
worktree 생성 4곳(orchestrator, sdd-fix conflict/피드백, sdd-sync rebase) 모두:
1. 기존 디렉토리 존재 확인
2. `pgrep`으로 프로세스 생존 체크
3. 프로세스 없으면 `git worktree remove --force` → 재생성
4. 프로세스 있으면 스킵 (실행 중인 작업 보호)

### PR 브랜치 작업
`claude --worktree SP-NNN`은 새 브랜치(`worktree-SP-NNN`)를 생성.
PR 브랜치에서 작업하려면 프롬프트에 `git checkout ${BRANCH}` 지시 필요.

## 모니터링

```bash
.claude/scripts/sdd-orch.sh status   # 프로세스 상태
tail -f sdd-orchestrator/logs/orchestrator.log  # 실시간 로그
gh pr list --state open              # 열린 PR
git worktree list                    # 워크트리
sqlite3 .sdd/state.db "SELECT task_id, status FROM task_status WHERE status != 'done';"  # 활성 태스크
```

---

## 전체 흐름도

```
[사람] spec 작성 → main push
  ↓ (10분 이내)
[오케스트레이터]
  ├─ pending 감지 → 자동 설계 → 자동 승인
  ├─ approved 감지 → 워크트리 /sdd-run
  ├─ PR 생성 → CI/리뷰 모니터링
  ├─ mergeable → 자동 머지 → sdd-sync
  ├─ changes_requested → sdd-fix 트리거
  ├─ Sentry 에러 → Issue → autofix PR
  └─ 문제 발생 → Slack #sdd-bot 알림
        ↓
[사람] Slack 확인 → 판단 (BLOCKER/머지/검수)
```
