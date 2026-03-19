# /sdd-run Command

SDD 태스크를 worktree에서 자율 실행하는 명령입니다.

## 사용법

```
/sdd-run [branch]
```

### 예시
```
/sdd-run feat/SP-005-kanban-card-default-tab
```

## 실행 내용

아래 명령어를 **사용자에게 안내**합니다 (Claude 세션 내에서 worktree 실행 불가):

```bash
claude --worktree $ARGUMENTS --dangerously-skip-permissions -p 시작
```

> ⚠️ 이 명령은 **별도 터미널**에서 실행해야 합니다. 현재 Claude 세션에서는 worktree를 기동할 수 없습니다.

## 실행 전 체크리스트

1. `$ARGUMENTS` 브랜치에 해당하는 태스크 파일이 `.claude/tasks/current/`에 있는지 확인
2. 없으면 사용자에게 태스크 파일 생성을 안내
3. 있으면 명령어를 출력하여 사용자가 복사+실행할 수 있게 안내
