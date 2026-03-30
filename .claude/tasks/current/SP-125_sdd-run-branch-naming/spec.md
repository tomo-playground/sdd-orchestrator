# SP-125: sdd-run 브랜치 네이밍 표준화

- **branch**: feat/SP-125_sdd-run-branch-naming
- **priority**: P1
- **scope**: .claude/commands
- **assignee**: AI
- **created**: 2026-03-31

## 배경

sdd-run이 worktree 브랜치(`worktree-SP-NNN`)에서 바로 커밋+push하여 PR 브랜치명이 비표준.
spec.md에 `branch: feat/SP-NNN_slug` 필드가 있지만, sdd-run이 이걸 읽어서 feat 브랜치를 만드는 로직이 없음.

### 현상

| PR | 브랜치 | 형식 |
|----|--------|------|
| #383 | `feat/SP-122_new-storyboard-group-select` | 표준 (수동) |
| #384 | `worktree-SP-123` | 비표준 (sdd-run 자동) |
| #363 | `worktree-SP-111` | 비표준 (sdd-run 자동) |

### 표준

`feat/SP-NNN_slug` (언더바 구분). spec.md의 `branch:` 필드에 정의.

## DoD (Definition of Done)

- [ ] sdd-run Step 7에서 spec.md의 `branch:` 필드를 읽어 `git checkout -b ${BRANCH}` 실행
- [ ] branch 필드 없으면 `feat/SP-NNN_${slug}` 자동 생성 (디렉토리명에서 추출)
- [ ] PR 생성 시 해당 브랜치로 push
- [ ] worktree 브랜치(`worktree-SP-NNN`)에서 직접 push 금지 명시

## 수정 대상 파일

- `.claude/commands/sdd-run.md` — Step 7에 브랜치 생성 규칙 추가
