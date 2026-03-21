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

아래 단계를 **순서대로 자동 수행**한다. 사용자에게 묻지 않고 끝까지 진행.

### 1. 태스크 파일 매칭
- `SP-NNN` 형태: `.claude/tasks/current/SP-NNN_*.md` 패턴으로 매칭
- `feat/SP-NNN-*` 형태: 브랜치명에서 SP-NNN 추출 후 동일 매칭
- 매칭 실패 시 태스크 파일 생성 안내 후 중단

### 2. 의존성 체크
- 태스크 파일의 `depends_on:` 필드 확인
- 선행 태스크 ID가 있으면 → `.claude/tasks/done/` 에 해당 SP-NNN 파일이 존재하는지 확인
- **존재하면**: 의존성 충족 → 계속 진행
- **존재하지 않으면**: "선행 태스크 SP-NNN이 아직 완료되지 않았습니다" 메시지 출력 후 **중단**

### 3. 태스크 파일 main 커밋 확인
- `git status`로 태스크 파일이 untracked/unstaged인지 확인
- **미커밋 상태면 자동 커밋**: `git add .claude/tasks/current/SP-NNN_*.md && git commit`
- 이미 커밋되어 있으면 스킵

### 4. 워크트리 확인 및 생성
- 이미 해당 SP-NNN 워크트리에서 실행 중이면 → 바로 5단계로
- main에서 실행 중이면 → 아래 명령어를 사용자에게 안내:

```bash
claude --worktree $ARGUMENTS --dangerously-skip-permissions -p "/sdd-run $ARGUMENTS"
```

> ⚠️ 이 명령은 **별도 터미널**에서 실행해야 합니다.

### 5. 워크트리 동기화
- `git rebase main` 수행 → 태스크 파일이 워크트리에 반영됨
- 충돌 시 자율 해결, 불가하면 사용자 보고

### 6. 태스크 실행
1. 태스크 파일(`.claude/tasks/current/SP-NNN_*.md`) 읽기
2. `status: pending` → `status: running` 업데이트
3. 태스크의 DoD에 따라 자율 구현 시작
4. CLAUDE.md의 SDD 자율 실행 규칙 준수
