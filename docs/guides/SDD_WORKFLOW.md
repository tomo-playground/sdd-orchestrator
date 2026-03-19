# SDD (Spec-Driven Development) 워크플로우 가이드

> 사람은 플래닝만, AI가 구현~PR까지 자율 실행하는 업무 플로우.
> 확정일: 2026-03-19

---

## 역할 정의

### 사람 (Product Architect + Quality Judge)

| 활동 | 산출물 |
|------|--------|
| 제품 방향 설정 | `ROADMAP.md` |
| 태스크 큐 관리 | `backlog.md` |
| 태스크 계약서 작성 | `current/태스크명.md` |
| PR 리뷰 + 최종 판단 | GitHub PR |
| AI 규칙 유지보수 | `CLAUDE.md` |

### AI (Claude Code)

| 활동 | 자율 여부 |
|------|----------|
| 코드 구현 | 풀 자율 |
| 테스트 작성 | 풀 자율 |
| 린트 + 포맷팅 | 자동 (Hook) |
| 품질 게이트 통과 | 자동 (Stop Hook) |
| self-heal (실패 수정) | 최대 3회 |
| 커밋 + 푸시 | 풀 자율 |
| PR 생성 | 풀 자율 |

---

## 실행 흐름

```
[사람] ROADMAP에서 방향 확인
  ↓
[사람] backlog.md에서 다음 태스크 선택
  ↓
[사람] current/태스크명.md에 상세 작성 (2~3분)
  ↓
[Claude] 부팅: 브랜치명 → current/태스크명.md → CLAUDE.md → 작업 시작
  ↓
[Claude] worktree + feat/xxx 브랜치에서 구현
  ↓
[Claude] Stop Hook 자동 실행
         Lint → pytest → vitest → VRT → E2E (5단계)
         실패 → self-heal (최대 3회) → 재검증
  ↓
[Claude] 커밋 → 푸시 → PR 생성 (label/reviewer/assignee 자동)
  ↓
[사람] PR 리뷰
       승인 → 머지
       거절 → PR 코멘트 → Claude가 읽고 수정 → push
  ↓
[자동] current/태스크명.md → done/NNN_태스크명.md로 이동 (Stop Hook)
       backlog.md에서 해당 항목 제거
```

---

## 용어 사전 (혼용 금지)

| 용어 | 역할 | 위치 | 절대 아닌 것 |
|------|------|------|------------|
| **Roadmap** | 제품 방향, Phase, 마일스톤 | `docs/01_product/ROADMAP.md` | 태스크 목록 아님 |
| **Backlog** | 실행 가능한 태스크 큐 (우선순위) | `.claude/tasks/backlog.md` | 로드맵 아님, 상세 명세 아님 |
| **Task** | 실행 중인 계약서 (브랜치별 1개) | `.claude/tasks/current/브랜치명.md` | 백로그 아님, 완료 기록 아님 |
| **Done** | 완료된 태스크 + 품질 게이트 결과 | `.claude/tasks/done/NNN_브랜치.md` | 별도 로그 파일 없음 |

---

## 디렉토리 구조

```
.claude/
├── tasks/
│   ├── _template.md          ← 태스크 작성 템플릿
│   ├── backlog.md            ← 실행 대기 큐 (우선순위 순)
│   ├── current/              ← 실행 중 태스크 (브랜치별 1개)
│   │   ├── enum-id-normalization.md
│   │   ├── speaker-dynamic-role.md
│   │   └── ...
│   └── done/                 ← 완료 이력
│       ├── 001_feat-xxx.md
│       ├── 002_feat-yyy.md
│       └── ...
├── hooks/
│   ├── auto-lint.sh          ← PostToolUse: Edit/Write 시 자동 린트
│   └── on-stop.sh            ← Stop: 5단계 품질 게이트 + self-heal
└── settings.json             ← Hook 설정 + Agent Teams
```

---

## Task 작성 규칙

### 템플릿 (`.claude/tasks/_template.md`)

```markdown
---
id:                          # kebab-case (브랜치명과 동일)
priority:                    # P0 / P1 / P2 / P3
scope:                       # backend / frontend / fullstack / infra / docs
branch: feat/                # feat/{id}
created:                     # YYYY-MM-DD
status: pending              # pending → running → done / failed
depends_on:                  # 선행 태스크 id (없으면 비움)
---

## 무엇을
[구현할 기능 한 줄 설명]

## 왜
[이유/배경]

## 완료 기준 (DoD)
- [ ] 핵심 기능 동작
- [ ] 테스트 통과
- [ ] 기존 기능 regression 없음

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것:
- 의존성 추가 금지:

## 힌트 (선택)
- 관련 파일:
- 참고:
```

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

- 재시도 카운터: `/tmp/claude-stop-hook-retry-*` 파일 기반
- `stop_hook_active` 필드로 재시도 상태 감지

---

## 브랜치 전략

- **worktree + feature 브랜치** 사용
- main 브랜치는 항상 깨끗하게 유지
- PR이 유일한 머지 경로
- **PR 전 리베이스**: 머지 충돌 방지를 위해 push 전에 `git rebase main` 수행. 충돌 시 Claude가 자율 해결, 해결 불가하면 사용자에게 보고.

### 실행 명령어

```bash
# 단일 실행 (alias 사용)
sdd-run feat/SP-002-tts-warning-frontend-toast

# 직접 실행
claude --worktree feat/SP-NNN-설명 --dangerously-skip-permissions -p "시작"
```

> `-p "시작"` 필수: 없으면 Claude가 사용자 입력 대기 상태로 멈춤.

### alias 설정 (~/.bashrc)
```bash
sdd-run() { claude --worktree "$1" --dangerously-skip-permissions -p "시작"; }
```

---

## PR 생성 규칙

Claude가 PR 생성 시 태스크 frontmatter에서 메타 정보를 추출하여 자동 설정:

```bash
gh pr create \
  --title "feat: 설명 (SP-NNN)" \
  --label "SP-NNN,{scope},{priority}" \
  --reviewer stopper2008 \
  --assignee stopper2008 \
  --project "shorts producer" \
  --body "..."
```

| frontmatter | PR 메타 | 예시 |
|-------------|---------|------|
| `id: SP-002` | label | `SP-002` |
| `scope: frontend` | label | `frontend` |
| `priority: P1` | label | `P1` |
| (고정) | project | `shorts producer` |
| (고정) | reviewer | `stopper2008` |
| (고정) | assignee | `stopper2008` |

PR body는 `.github/pull_request_template.md` 템플릿 기반.

---

## PR 거절 시 재시도

```
1. GitHub에서 PR 리뷰, 코멘트 남김
2. Claude 실행: sdd-run feat/SP-NNN-설명
3. Claude → gh pr view #NNN → 코멘트 읽음
4. 기존 브랜치에서 수정 → push → PR 자동 업데이트
```

---

## 머지 후 자동 정리

```bash
# 자동: cron 5분 간격으로 sdd-sync.sh 실행
# 수동: 즉시 정리
sdd-sync
```

동작: main pull → 로컬/원격 feat 브랜치 삭제 → current/ → done/ 이동 → 커밋+푸시

---

## 병렬 실행

### 매칭 규칙
```
브랜치: feat/SP-NNN-xxx → 태스크: .claude/tasks/current/SP-NNN_xxx.md
```

### 병렬 실행 흐름
```bash
# 사람: backlog에서 3개 태스크를 current/에 작성
# 터미널 1 (또는 tmux 패널)
sdd-run feat/SP-003-storyboard-integrity
# 터미널 2
sdd-run feat/SP-004-enum-id-normalization
# 터미널 3
sdd-run feat/SP-005-speaker-dynamic-role
```

### 병렬 제약
- **파일 범위 겹침 금지**: 같은 파일을 수정하는 태스크는 동시 실행 불가
- **DB 마이그레이션 직렬**: 마이그레이션 생성 태스크는 1개씩만
- **테스트 자원 공유**: PostgreSQL, SD WebUI 등 동시 접근 주의

---

## 즉시 중단 조건

아래 상황에서는 Claude가 작업을 중단하고 사람에게 알린다:

- DB 스키마 변경이 필요한 경우
- 외부 의존성(패키지) 추가가 필요한 경우
- task.md의 제약 조건을 위반해야 하는 경우
- 변경 파일이 10개를 초과할 것으로 예상되는 경우

---

## 확정 결정 요약

| # | 항목 | 결정 |
|---|------|------|
| 0 | 브랜치 전략 | worktree + feature 브랜치 |
| 1 | 품질 게이트 | Lint → pytest → vitest → VRT → E2E (5단계) |
| 2 | 실패 행동 | self-heal 최대 3회, 이후 실패 보고 |
| 3 | 자율 범위 | 구현 → 커밋 → 푸시 → PR까지 풀 자율 |
| 4 | 태스크 단위 | 기능 단위, 파일 10개 이하, 크면 분할 |
| 5 | 세션 부팅 | current.md → CLAUDE.md → git status → 시작 |
| 5b | PR 거절 시 | PR 코멘트 기반 수정 |
| 6 | 진행 가시성 | 보류 (운용 후 필요 시 추가) |
