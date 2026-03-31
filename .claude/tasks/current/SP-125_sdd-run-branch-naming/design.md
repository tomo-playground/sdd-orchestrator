Now let me check a few more things to understand the worktree branch naming and existing patterns.
Now I have enough context. Let me write the design.


# SP-125: sdd-run 브랜치 네이밍 표준화 — 상세 설계

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `.claude/commands/sdd-run.md` | 수정 | Step 7에 브랜치 생성 로직 추가, Step 8에 push 규칙 명시 |

---

## DoD 1: sdd-run Step 7에서 spec.md의 `branch:` 필드를 읽어 `git checkout -b ${BRANCH}` 실행

### 구현 방법

`sdd-run.md`의 **Step 7 (태스크 실행)** 앞에 새로운 **Step 7: feat 브랜치 생성**을 삽입한다. 기존 Step 7~8은 Step 8~9로 번호가 밀린다.

새 Step 7 내용:

1. spec.md 파일에서 `- **branch**: ` 줄을 파싱하여 브랜치명 추출
2. 추출된 브랜치명으로 `git checkout -b ${BRANCH}` 실행
3. 이미 해당 브랜치가 존재하면 `git checkout ${BRANCH}` (재실행 시나리오)

구체적으로 Step 7에 아래 로직을 명시:

```
1. spec.md에서 `branch:` 필드 읽기 → BRANCH 변수에 저장
2. git checkout -b ${BRANCH} 실행 (worktree-SP-NNN에서 분기)
3. 이미 존재하면 git checkout ${BRANCH}
```

### 동작 정의

- worktree 진입 후(Step 6 완료), 태스크 실행 전에 feat 브랜치로 전환
- 모든 커밋은 feat 브랜치 위에 쌓임
- worktree 자체의 `worktree-SP-NNN` 브랜치는 base로만 사용되고, 직접 push되지 않음

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| 이미 feat 브랜치에 있음 (재실행) | `git branch --show-current`로 확인, 이미 feat 브랜치면 스킵 |
| `branch:` 필드에 공백/따옴표 포함 | trim 처리. `feat/SP-125_sdd-run-branch-naming` 형식만 유효 |
| worktree가 아닌 main에서 실행 | Step 5에서 이미 worktree 안내 후 중단되므로 이 단계에 도달 불가 |

### 영향 범위

- `.claude/commands/sdd-run.md` Step 7 위치에 새 단계 삽입
- 기존 Step 7 → Step 8, Step 8 → Step 9로 번호 시프트

---

## DoD 2: branch 필드 없으면 `feat/SP-NNN_${slug}` 자동 생성 (디렉토리명에서 추출)

### 구현 방법

새 Step 7에 fallback 로직 추가:

1. `branch:` 필드가 없거나 비어있으면 → 디렉토리명에서 자동 생성
2. 디렉토리명 패턴: `SP-NNN_slug-here` → 브랜치명: `feat/SP-NNN_slug-here`
3. 예: 디렉토리 `SP-125_sdd-run-branch-naming` → `feat/SP-125_sdd-run-branch-naming`

구체적 로직:

```
BRANCH 비어있으면:
  TASK_DIR = 매칭된 태스크 디렉토리명 (예: SP-125_sdd-run-branch-naming)
  BRANCH = "feat/${TASK_DIR}"
```

### 동작 정의

- 디렉토리명이 이미 `SP-NNN_slug` 형식이므로 `feat/` prefix만 추가
- 기존 spec.md에 `branch:` 필드가 있는 태스크(SP-122~126 모두 있음)는 이 fallback에 도달하지 않음
- 레거시 파일 방식(`SP-NNN_*.md`)의 경우 파일명에서 추출: `SP-NNN_slug.md` → `feat/SP-NNN_slug`

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| 디렉토리명에 slug 없음 (`SP-125/`) | `feat/SP-NNN` 으로 생성 (slug 부분 없이) |
| 레거시 파일 방식 | 파일명 `.md` 확장자 제거 후 `feat/` prefix 추가 |

### 영향 범위

- 동일 Step 7 내 분기 로직

---

## DoD 3: PR 생성 시 해당 브랜치로 push

### 구현 방법

기존 Step 8 (→ 새 Step 9: PR 생성)에 push 명령을 명시:

```bash
git push -u origin ${BRANCH}
```

현재 sdd-run.md Step 8에는 `gh pr create` 명령만 있고, push 명령이 명시되어 있지 않다. push를 PR 생성 직전에 명시적으로 추가.

### 동작 정의

- feat 브랜치에서 작업 완료 후, `git push -u origin ${BRANCH}` 실행
- `gh pr create`는 해당 feat 브랜치 기준으로 PR 생성
- PR 브랜치명이 `feat/SP-NNN_slug` 형식으로 표시됨

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| remote에 이미 같은 브랜치 존재 | `git push -u origin ${BRANCH}` 는 기존 remote 브랜치에 push (정상) |
| push 실패 (권한/네트워크) | 에러 메시지 출력 후 사용자에게 보고 |

### 영향 범위

- `.claude/commands/sdd-run.md` Step 9 (기존 Step 8) PR 생성 섹션

---

## DoD 4: worktree 브랜치(`worktree-SP-NNN`)에서 직접 push 금지 명시

### 구현 방법

새 Step 7에 **금지 규칙**을 명확히 기술:

> **⚠️ worktree 브랜치(`worktree-SP-NNN`)에서 직접 push 금지.**
> 반드시 feat 브랜치를 생성한 후 push한다.

또한 Step 9 (PR 생성)에도 가드 조건 추가:

```
PR 생성 전 현재 브랜치 확인:
- `worktree-` prefix면 → "feat 브랜치가 생성되지 않았습니다" 에러 후 중단
- `feat/` prefix면 → 정상 진행
```

### 동작 정의

- sdd-run 에이전트가 PR 생성 시점에서 현재 브랜치를 검증
- `worktree-SP-NNN` 브랜치에서의 push/PR 시도를 차단
- 명시적 규칙으로 sdd-run을 따르는 다른 에이전트에게도 전파

### 영향 범위

- `.claude/commands/sdd-run.md` Step 7 (금지 규칙 명시) + Step 9 (가드 조건)

---

## 전체 수정 계획

### `.claude/commands/sdd-run.md` 수정 내역

**변경 1**: 기존 Step 7 앞에 새 Step 7 삽입

새 **Step 7: feat 브랜치 생성** 내용:

```markdown
### 7. feat 브랜치 생성
- spec.md에서 `branch:` 필드 읽기 → BRANCH 변수
- branch 필드가 없으면 디렉토리명에서 자동 생성: `feat/${TASK_DIR}` (예: `feat/SP-125_sdd-run-branch-naming`)
- 현재 브랜치가 이미 BRANCH면 스킵
- 아니면 `git checkout -b ${BRANCH}` 실행 (이미 존재하면 `git checkout ${BRANCH}`)
- **⚠️ `worktree-SP-NNN` 브랜치에서 직접 push/PR 금지. 반드시 feat 브랜치에서 작업.**
```

**변경 2**: 기존 Step 7 → Step 8로 번호 변경 (내용 동일)

**변경 3**: 기존 Step 8 → Step 9로 번호 변경 + push 명령 추가

Step 9 수정 내용:

```markdown
### 9. PR 생성

구현 + 테스트 완료 후:

1. 현재 브랜치 확인 — `worktree-` prefix면 에러 중단
2. `git push -u origin ${BRANCH}`
3. PR 생성:

\```bash
gh pr create --title "..." --body "..." --assignee stopper2008
\```
```

---

## 테스트 전략

이 태스크는 `.claude/commands/sdd-run.md` (마크다운 명령 문서) 수정이므로 자동화 테스트 대상이 아님. 검증은 수동으로 수행:

| # | 검증 항목 | 방법 |
|---|----------|------|
| 1 | `branch:` 필드 있는 spec으로 sdd-run 실행 시 해당 브랜치 생성 | SP-125 자체로 검증 가능 |
| 2 | `branch:` 필드 없는 spec으로 실행 시 디렉토리명 기반 자동 생성 | branch 필드 제거한 테스트 spec으로 검증 |
| 3 | PR 브랜치명이 `feat/SP-NNN_slug` 형식 | PR 생성 후 GitHub에서 확인 |
| 4 | worktree 브랜치에서 push 시도 시 차단 | Step 9 가드 조건 동작 확인 |
| 5 | 재실행 시 기존 feat 브랜치로 checkout | 동일 태스크 재실행으로 확인 |

---

## Out of Scope

- `sdd-sync.md` 수정 (feat 브랜치 삭제 로직은 이미 존재)
- `sdd-design.md` 수정
- worktree 자동 정리 (SP-124 범위)
- 기존 PR의 브랜치명 소급 변경
- `branch:` 필드 포맷 검증 (정규식 validation 등)

---

## BLOCKER

없음. 단일 마크다운 파일 수정이며, 외부 의존성/DB 변경/아키텍처 결정 불필요.