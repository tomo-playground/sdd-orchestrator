# /sdd-run Command

SDD 태스크를 worktree에서 자율 실행하는 명령입니다.

## 사용법

```
/sdd-run [SP-NNN 또는 branch]
```

### 예시
```
/sdd-run SP-009
/sdd-run feat/SP-005-kanban-card-default-tab
```

## 실행 흐름

### 1. 태스크 파일 매칭
- `SP-NNN` 형태: `.claude/tasks/current/SP-NNN_*.md` 패턴으로 매칭
- `feat/SP-NNN-*` 형태: 브랜치명에서 SP-NNN 추출 후 동일 매칭
- 매칭 실패 시 태스크 파일 생성 안내

### 2. 워크트리 확인
- 이미 해당 SP-NNN 워크트리에 있으면 바로 태스크 실행
- 아니면 아래 명령어를 사용자에게 안내:

```bash
claude --worktree $ARGUMENTS --dangerously-skip-permissions -p 시작
```

> ⚠️ 이 명령은 **별도 터미널**에서 실행해야 합니다. 현재 Claude 세션에서는 worktree를 기동할 수 없습니다.

### 3. 태스크 실행
워크트리 내에서 실행 시:
1. 태스크 파일(`.claude/tasks/current/SP-NNN_*.md`) 읽기
2. `status: pending` → `status: running` 업데이트
3. 태스크의 DoD에 따라 자율 구현 시작
4. CLAUDE.md의 SDD 자율 실행 규칙 준수

## 실행 전 체크리스트

1. `$ARGUMENTS`에 해당하는 태스크 파일이 `.claude/tasks/current/`에 있는지 확인
2. 없으면 사용자에게 태스크 파일 생성을 안내
3. 있으면 워크트리 여부에 따라 직접 실행 또는 명령어 안내
