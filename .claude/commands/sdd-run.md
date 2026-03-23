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
- `SP-NNN` 형태: `.claude/tasks/current/SP-NNN_*/spec.md` 패턴으로 매칭 (디렉토리 방식)
- 디렉토리 미발견 시 fallback: `.claude/tasks/current/SP-NNN_*.md` (레거시 파일 방식)
- `feat/SP-NNN-*` 형태: 브랜치명에서 SP-NNN 추출 후 동일 매칭
- 매칭 실패 시 태스크 파일 생성 안내 후 중단
- 설계 파일이 있으면 함께 로드: `SP-NNN_*/design.md`

### 2. 설계 승인 확인
- 태스크 파일의 `status` 확인
- `approved` 또는 `running` → 계속 진행
- `design` → "설계가 아직 승인되지 않았습니다. /sdd-design SP-NNN approved 실행" 안내 후 **중단**
- `pending` → "설계가 작성되지 않았습니다. /sdd-design SP-NNN 실행" 안내 후 **중단**
- 예외: 버그 수정(Hotfix/Sentry) 태스크는 설계 없이 실행 허용

### 3. 의존성 체크
- 태스크 파일의 `depends_on:` 필드 확인
- 선행 태스크 ID가 있으면 → 3단계 판정:
  1. `.claude/tasks/done/`에 해당 SP-NNN 존재 → **통과**
  2. `gh pr list --state merged`로 선행 태스크 PR 머지 확인 → **통과** (sdd-sync 전이라도)
  3. 위 2개 모두 아님 → 현황 표시 + 옵션 제안 후 **중단**
     - 옵션 1: 선행 태스크 PR 먼저 머지 → sdd-sync → 재실행
     - 옵션 2: `depends_on` 제거 (코드 레벨 독립인 경우)
     - 옵션 3: 선행 태스크 브랜치 위에서 작업 (머지 순서 의존)

### 4. 태스크 파일 main 커밋 확인
- `git status`로 태스크 파일이 untracked/unstaged인지 확인
- **미커밋 상태면 자동 커밋**: `git add .claude/tasks/current/SP-NNN_*/ && git commit`
- 이미 커밋되어 있으면 스킵

### 5. 워크트리 확인 및 생성
- 이미 해당 SP-NNN 워크트리에서 실행 중이면 → 바로 6단계로
- main에서 실행 중이면 → 아래 명령어를 사용자에게 안내:

```bash
claude --worktree $ARGUMENTS --dangerously-skip-permissions -p "/sdd-run $ARGUMENTS"
```

> 이 명령은 **별도 터미널**에서 실행해야 합니다.

### 6. 워크트리 동기화
- `git rebase main` 수행 → 태스크 파일이 워크트리에 반영됨
- 충돌 시 자율 해결, 불가하면 사용자 보고

### 7. 태스크 실행
1. 태스크 파일(`spec.md`) + 설계 파일(`design.md`) 읽기
2. `status: approved` → `status: running` 업데이트
3. **설계 파일의 각 DoD 상세 설계를 기반으로** 자율 구현 시작
4. CLAUDE.md의 SDD 자율 실행 규칙 준수
