# SDD (Spec-Driven Development) 워크플로우 가이드

> 사람은 설계·기동·판단·정리, AI가 구현~PR까지 자율 실행하는 업무 플로우.
> 최종 업데이트: 2026-03-21

---

## 역할 정의

### 사람 (SDD 오케스트레이터)

| 책임 | 산출물 |
|------|--------|
| 제품 방향 설정 | `ROADMAP.md` |
| 태스크 작성 | `.claude/tasks/current/SP-NNN_*.md` |
| 기동 | `sdd-run SP-NNN` |
| 품질 판단 | Claude + CodeRabbit 리뷰 결과 종합 → 머지/거절 |
| 정리 | `/sdd-sync` |
| 규칙 유지보수 | `CLAUDE.md` |

### AI (Claude Code — 워크트리 세션)

| 활동 | 자율 여부 |
|------|----------|
| 코드 구현 | 풀 자율 |
| 테스트 작성 | 풀 자율 |
| 린트 + 포맷팅 | 자동 (Hook) |
| 품질 게이트 통과 | 자동 (Stop Hook) |
| self-heal (실패 수정) | 최대 3회 |
| 커밋 + 푸시 + PR 생성 | 풀 자율 |
| 셀프 리뷰 + 이슈 수정 | 풀 자율 |

### AI (CodeRabbit — 독립 리뷰어)

| 활동 | 동작 |
|------|------|
| PR 자동 리뷰 | PR 생성/push 시 자동 실행, CLAUDE.md 기반 |
| request_changes | 심각 이슈 시 commit status fail → 사람에게 알림 |
| incremental review | push 후 자동 재리뷰 (핑퐁) |

---

## 실행 흐름

```
[사람] task.md 작성 → main 커밋 (태스크 파일은 main 직접 커밋 허용)
  ↓
[사람] sdd-run SP-NNN → 워크트리 기동 (자동 rebase main → 태스크 파일 동기화)
  ↓
[워크트리] 태스크 읽기 → 구현 → Stop Hook 5단계 품질 게이트
  ↓  실패 시 → self-heal (최대 3회) → 재검증
  ↓
[워크트리] 커밋 → 푸시 → PR 생성 → /code-review 셀프 리뷰
  ↓  셀프 리뷰 이슈 발견 시 → 자동 수정 → push
  ↓
[CodeRabbit] PR 생성 시 자동 독립 리뷰 (CLAUDE.md 기반)
  ↓  request_changes 시 → sdd-review가 자동 대응
  ↓
[워크트리 종료]
  ↓
[GitHub Actions] 코멘트 감지 → 호스트 runner → Claude 수정 → push → CodeRabbit 재리뷰 (핑퐁)
  ↓
[사람] PR 확인 — Claude 셀프 리뷰 + CodeRabbit 독립 리뷰 결과 종합 후 판단
  ├─ 머지 → GitHub Actions sdd-sync 자동 실행 (태스크 → done/, 브랜치 삭제, rebase)
  └─ 수정 요청 → sdd-run 재실행 또는 sdd-review가 자동 대응
```

---

## 운영 명령어

| 주체 | 명령어 | 언제 | 동작 |
|------|--------|------|------|
| 사람 | `sdd-run SP-NNN` | 태스크 시작/재개 | 워크트리 생성 → 구현 → PR → 셀프 리뷰 |
| 사람 | `/sdd-review` | PR 열린 상태 | Phase 1: Claude 독립 리뷰, Phase 2: 코멘트 자동 대응 |
| 사람 | `/sdd-sync` | 비상용 수동 실행 | 태스크 → done/, 브랜치·워크트리 삭제 |
| 자동 | GitHub Actions (sdd-sync) | PR 머지 시 | 태스크 → done/, 브랜치 삭제, 열린 PR rebase |
| 자동 | CodeRabbit | PR 생성/push 시 | 독립 AI 리뷰 (CLAUDE.md 기반) |
| 자동 | GitHub Actions (sdd-review) | PR 코멘트 시 | 이벤트 드리븐 — Claude 자동 수정 |

### 터미널 명령어 (bash)

```bash
# 태스크 기동 (별도 터미널)
sdd-run SP-NNN

# 병렬 실행 (터미널 여러 개)
sdd-run SP-007  # 터미널 1
sdd-run SP-008  # 터미널 2
```

> `/sdd-sync`는 비상용 수동 실행. 일반적으로 GitHub Actions가 PR 머지 시 자동 처리.
> unstaged 변경이 있으면 자동 stash → sync → stash pop 수행.

---

## 3중 리뷰 체계

```
PR 생성 → 병렬 리뷰
  ├─ Claude 셀프 리뷰 (워크트리) ← 코드 작성자가 즉시 리뷰
  ├─ CodeRabbit (자동)           ← 독립 AI가 CLAUDE.md 기준 검증
  └─ GitHub Actions (호스트 runner) ← 코멘트 이벤트 시 자동 수정
```

| 리뷰어 | 강점 | 약점 |
|--------|------|------|
| Claude 셀프 리뷰 | 구현 맥락 이해, 즉시 수정 | 자기 코드 편향 |
| CodeRabbit | 독립적, 자동, 빠름 | 프로젝트 깊은 맥락 부족 |
| GitHub Actions | 이벤트 드리븐, 호스트 환경 | Claude CLI 의존 |

### 핑퐁 자동화 (GitHub Actions → CodeRabbit)

```
CodeRabbit/사람: 코멘트 게시
  ↓ GitHub Webhook (즉시)
GitHub Actions: sdd-review.yml 트리거 → 호스트 runner
  ↓
Claude: 코멘트 읽기 → 판단 → 수정 → push → "수정했습니다" 코멘트
  ↓ push 트리거
CodeRabbit: incremental review → 재리뷰
  ↓ 이슈 남으면
다음 코멘트 이벤트에서 반복
```

---

## 용어 사전 (혼용 금지)

| 용어 | 역할 | 위치 | 절대 아닌 것 |
|------|------|------|------------|
| **Roadmap** | 제품 방향, Phase, 마일스톤 | `docs/01_product/ROADMAP.md` | 태스크 목록 아님 |
| **Backlog** | 실행 가능한 태스크 큐 (우선순위) | `.claude/tasks/backlog.md` | 로드맵 아님 |
| **Task** | 실행 중인 계약서 (브랜치별 1개) | `.claude/tasks/current/SP-NNN_*.md` | 백로그 아님 |
| **Done** | 완료된 태스크 + 품질 게이트 결과 | `.claude/tasks/done/SP-NNN_*.md` | 별도 로그 없음 |

---

## 디렉토리 구조

```
.claude/
├── tasks/
│   ├── _template.md          ← 태스크 작성 템플릿
│   ├── backlog.md            ← 실행 대기 큐 (우선순위 순)
│   ├── current/              ← 실행 중 태스크
│   │   └── SP-NNN_설명.md
│   └── done/                 ← 완료 이력
│       └── SP-NNN_설명.md
├── commands/
│   ├── sdd-run.md            ← /sdd-run 커맨드 정의
│   ├── sdd-sync.md           ← /sdd-sync 커맨드 정의
│   └── sdd-review.md         ← /sdd-review 커맨드 정의
├── scripts/
│   ├── sdd-sync.sh           ← 머지 후 정리 (GitHub Actions + 비상 수동)
│   └── sdd-review.sh         ← 리뷰 + 자동 수정 (수동 /sdd-review 시 사용)
├── hooks/
│   ├── auto-lint.sh          ← PostToolUse: Edit/Write 시 자동 린트
│   └── on-stop.sh            ← Stop: 5단계 품질 게이트 + self-heal
├── worktrees/                ← 워크트리 작업 디렉토리 (자동 생성/삭제)
└── settings.json             ← Hook 설정
```

---

## Task 작성 규칙

### 좋은 Task vs 나쁜 Task

```markdown
# ❌ 나쁜 Task
## 무엇을
렌더링 품질 개선
## 완료 기준
- [ ] 품질이 좋아짐
```

```markdown
# ✅ 좋은 Task
## 무엇을
Post Type 렌더링에서 긴 텍스트(60자+) 잘림 방지

## 왜
현재 고정 폰트 48px → 3줄 넘으면 영역 밖으로 벗어남

## 완료 기준 (DoD)
- [ ] 60자 이상 텍스트에서 폰트 32px로 축소
- [ ] 기존 짧은 텍스트 동작 변경 없음
- [ ] 테스트 추가: 20자/40자/60자/80자 케이스

## 제약
- services/rendering.py만 수정
- 기존 calculate_optimal_font_size() 함수 활용
```

**핵심**: 완료 기준이 **검증 가능한 조건**이어야 AI가 self-check할 수 있다.

---

## 품질 게이트 (Stop Hook)

### 5단계 파이프라인

```
Step 1. Lint     → ruff (Python) + prettier (TypeScript)
Step 2. pytest   → Backend 단위 테스트
Step 3. vitest   → Frontend 단위 테스트
Step 4. VRT      → Visual Regression Test
Step 5. E2E      → Playwright (서버 실행 중일 때만)
```

### Self-Heal 메커니즘

```
실패 → exit 2 → Claude에게 에러 전달 → 수정 시도
→ 재검증 → 실패 시 재시도 (최대 3회)
→ 3회 초과 → 종료 + 실패 보고
```

---

## 브랜치 전략

### 매칭 규칙

```
브랜치에서 SP-NNN을 추출하여 .claude/tasks/current/SP-NNN_*.md 글로브 매칭
- feat/SP-002-xxx  → SP-002 → .claude/tasks/current/SP-002_*.md
- fix/SP-039-xxx   → SP-039 → .claude/tasks/current/SP-039_*.md
- worktree-SP-009  → SP-009 → .claude/tasks/current/SP-009_*.md
```

지원 브랜치 접두사: `feat/`, `fix/`, `chore/`, `hotfix/`, `worktree-`

### 커밋 경로 규칙

- **main 직접 커밋 허용**: `.claude/`, `CLAUDE.md`, `.github/workflows/`, `docs/`
- **feat/fix 브랜치 + PR 필수**: `backend/`, `frontend/`, `audio/`, 그 외 코드

---

## 병렬 실행

```bash
# 터미널 1
sdd-run SP-007
# 터미널 2
sdd-run SP-008
```

### 병렬 제약
- **파일 범위 겹침 금지**: 같은 파일을 수정하는 태스크는 동시 실행 불가
- **DB 마이그레이션 직렬**: 마이그레이션 태스크는 1개씩만
- **테스트 자원 공유**: PostgreSQL, SD WebUI 등 동시 접근 주의

---

## 즉시 중단 조건

- DB 스키마 변경이 필요한 경우
- 외부 의존성(패키지) 추가가 필요한 경우
- task.md의 제약 조건을 위반해야 하는 경우
- 변경 파일이 10개를 초과할 것으로 예상되는 경우

---

## PR 코멘트 대응 원칙

맹목 수용이 아닌 **시니어 엔지니어 판단**:
- **버그 지적** → 즉시 수정 + "수정했습니다" 코멘트
- **설계 질문/개선 제안** → CLAUDE.md 대조, 동의하면 수정, 비동의하면 "현행 유지 이유" 코멘트
- **스타일/Nit** → 합리적이면 수정, 아니면 스킵

---

## 확정 결정 요약

| # | 항목 | 결정 |
|---|------|------|
| 0 | 브랜치 전략 | worktree + feature 브랜치 |
| 1 | 품질 게이트 | Lint → pytest → vitest → VRT → E2E (5단계) |
| 2 | 실패 행동 | self-heal 최대 3회, 이후 실패 보고 |
| 3 | 자율 범위 | 구현 → 테스트 → 문서 → 커밋 → PR까지 풀 자율 |
| 4 | 태스크 단위 | 기능 단위, 파일 10개 이하, 크면 분할 |
| 5 | 리뷰 체계 | 3중 (Claude 셀프 + CodeRabbit 독립 + /sdd-review 심층) |
| 6 | PR 코멘트 대응 | 판단 기반 (맹목 수용 금지) |
| 7 | 머지 후 정리 | GitHub Actions sdd-sync (PR 머지 트리거) + 비상 수동 |
| 8 | 핑퐁 자동화 | sdd-review Phase 2 → CodeRabbit incremental review 반복 |
| 9 | 커밋 경로 | .claude/docs → main 직접, 코드 → feat/fix/chore/hotfix 브랜치 |
| 10 | 사람 역할 | 설계, 기동, 판단, 정리 (코드 작성 안 함) |

---

## 교훈 (Lessons Learned)

| 변경 | 생긴 구멍 | 교훈 |
|------|----------|------|
| worktree 도입 | 의존성 없어서 테스트 불가 | 새 실행 환경 도입 시 테스트 경로 검증 |
| SP-NNN 도입 | sdd-sync 매칭 로직 불일치 | 네이밍 규칙 변경 시 관련 스크립트 전체 업데이트 |
| worktree 브랜치명 | `worktree-` prefix 자동 추가 | 외부 도구 동작 사전 검증 |
| task.md main 미커밋 | 워크트리에서 태스크 못 찾음 | sdd-run이 자동 커밋+rebase 해야 함 |
| main에서 코드 수정 | SDD 위반, 되돌리기 필요 | 코드 변경은 반드시 워크트리에서만 |
| sdd-sync unstaged | 조용히 스킵 → 사용자 혼란 | 자동 stash 도입 |
| 로컬 브랜치 잔존 | git branch -d로 안 지워짐 | -D 강제 삭제 + worktree prefix 정리 |
| sdd-sync `fix/` 브랜치 미처리 | sed가 `feat/`만 strip → SP_ID 추출 실패 → `set -e` 크래시 | 브랜치 접두사 패턴 확장 + grep 실패 방어 (`\|\| true`) |
