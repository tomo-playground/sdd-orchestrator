# SP-087: Slack 워크플로우 강화 — 상세 설계

> 난이도: 중 | Gemini 2라운드 + 에이전트 리뷰 2라운드

## 변경 파일 요약

| 파일 | 액션 | 변경 내용 |
|------|------|-----------|
| `orchestrator/tools/backlog.py` | 수정 | status 파싱 → 공통 헬퍼 호출로 교체 |
| `orchestrator/tools/task_utils.py` | **신규** | status 파싱/업데이트 공통 헬퍼, SP 번호 채번, slug 생성 |
| `orchestrator/tools/tasks.py` | **신규** | `read_task`, `approve_design`, `create_task` MCP 도구 |
| `orchestrator/tools/design.py` | 수정 | `_read_spec_status`, `_update_spec_status` → 공통 헬퍼로 교체 |
| `orchestrator/tools/__init__.py` | 수정 | MCP 서버에 3개 도구 등록 |
| `orchestrator/agents.py` | 수정 | `_SLACK_BOT_TOOLS`에 3개 도구 등록 |
| `orchestrator/config.py` | 수정 | `TASKS_DONE_DIR` 추가, 모델 환경변수화, 타임아웃 조정, 프롬프트 강화 |
| `orchestrator/tests/test_backlog.py` | 수정 | blockquote status 파싱 테스트 추가 |
| `orchestrator/tests/test_task_utils.py` | **신규** | 공통 헬퍼 단위 테스트 |
| `orchestrator/tests/test_tasks.py` | **신규** | 신규 도구 단위 테스트 |

---

## 공통 설계 원칙

### 에러 반환 키: `isError` (camelCase)

기존 코드에서 `isError`가 표준 (github.py, worktree.py, slack_bot.py). backlog.py의 `is_error`는 예외. 신규 코드는 모두 `isError` 사용.

### 헬퍼 패턴: `_ok()` + `_error()`

worktree.py 패턴을 따른다:
```python
def _ok(message: str) -> dict:
    return {"content": [{"type": "text", "text": message}]}

def _error(message: str) -> dict:
    return {"content": [{"type": "text", "text": f"Error: {message}"}], "isError": True}
```

### Git 동시성: 공유 Lock

`design.py`에 이미 `_git_lock = asyncio.Lock()`이 존재. 이를 `task_utils.py`로 추출하여 design.py + tasks.py에서 공유.

```python
# task_utils.py
import asyncio
git_lock = asyncio.Lock()

async def git_commit_files(files: list[str], message: str) -> str | None:
    """Lock-protected git add + commit + push. Returns error message or None."""
    async with git_lock:
        # git add <files>
        # git commit -m <message>
        # git push (rebase retry 1회)
    ...
```

### Git Push 포함

design.py의 `_git_commit_and_push` 패턴을 따라 push까지 수행. 로컬에만 커밋이 남으면 worktree pull 시 충돌 발생하므로 push 필수.

---

## DoD 1: scan_backlog blockquote status 파싱

### 구현 방법

#### 공통 헬퍼 추출: `task_utils.py`

```python
# orchestrator/tools/task_utils.py

import re

# blockquote + frontmatter 모두 매칭
_STATUS_RE = re.compile(r"^(?:>\s*)?status:\s*(\w+)", re.MULTILINE)

def parse_spec_status(content: str) -> str:
    """Parse status from spec.md content (supports frontmatter and blockquote)."""
    match = _STATUS_RE.search(content)
    return match.group(1) if match else "pending"

def update_spec_status(content: str, new_status: str, metadata: str = "") -> str:
    """Replace status line in spec.md content. Handles frontmatter and blockquote."""
    status_line = f"> status: {new_status}"
    if metadata:
        status_line += f" | {metadata}"
    if _STATUS_RE.search(content):
        return _STATUS_RE.sub(status_line, content, count=1)
    # 없으면 제목 다음 줄에 삽입
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("# "):
            lines.insert(i + 1, f"\n{status_line}")
            break
    return "\n".join(lines)
```

#### `backlog.py` 수정 (2곳)

`_enrich_from_specs()` (L135):
```python
# before
status_match = re.search(r"^status:\s*(\w+)", content, re.MULTILINE)
if status_match:
    task.spec_status = status_match.group(1)

# after
from orchestrator.tools.task_utils import parse_spec_status
task.spec_status = parse_spec_status(content)
```

`_discover_current_tasks()` (L168):
```python
# before
if line.startswith("status:"):
    status = line.split(":", 1)[1].strip()

# after
from orchestrator.tools.task_utils import parse_spec_status
status = parse_spec_status(content)  # content 전체를 한번에 파싱
```

#### `design.py` 수정

`_read_spec_status()` + `_STATUS_RE` + `_update_spec_status()` → `task_utils` import로 교체.

### 동작 정의

- before: `> status: approved | approved_at: 2026-03-26` → 파싱 실패 → 기본값 `"pending"`
- after: → `"approved"` 정확 반환 (backlog.py + design.py 모두)

### 엣지 케이스

- `> status: approved | approved_at: ...` → `"approved"` (`\w+`로 첫 단어만 캡처)
- `status: design` (기존 frontmatter) → 여전히 동작
- status 줄 없음 → 기본값 `"pending"`

### 영향 범위

- `scan_backlog` + `auto_design_task` 정확도 개선
- design.py의 `_update_spec_status`도 blockquote 형식 대응

### 테스트 전략

- `test_task_utils.py`: `parse_spec_status` — frontmatter, blockquote, pipe 메타데이터, 미존재
- `test_task_utils.py`: `update_spec_status` — 교체, 삽입
- `test_backlog.py` 추가: blockquote 형식 spec.md 파싱 검증
- 기존 frontmatter 테스트 유지 (회귀 방지)

### 추가 수정

- `backlog.py` L211: `is_error` → `isError` 통일 (camelCase 표준, 이 파일이 이미 수정 대상이므로 함께 처리)

### Out of Scope

- backlog.md 파싱 로직 변경
- `_discover_current_tasks`의 priority/scope/depends_on blockquote 대응 (현재 해당 필드는 blockquote 형식 사용 안 함)

---

## DoD 2: Agent 프롬프트 강화

### 구현 방법

`orchestrator/config.py`의 `SLACK_BOT_AGENT_PROMPT` 확장. 기존 47줄 → ~80줄.

추가 섹션:

```
## SDD 워크플로우 이해
태스크 라이프사이클: backlog → current(pending) → design → approved → running → done
- scan_backlog의 spec_status 필드가 현재 상태
- approved인 태스크만 launch_sdd_run 가능
- running인 태스크는 check_running_worktrees로 확인

## 도구 판단 기준
- "상태/진척/현황" → scan_backlog
- "SP-NNN 상세/내용" → read_task
- "진행해줘/실행해줘" → launch_sdd_run (approved 확인 후)
- "승인해줘" → approve_design
- "태스크 만들어줘" → create_task
- "PR 머지해줘" → merge_pr
- "일시정지/재개" → pause/resume_orchestrator

## 새 도구
- read_task: 태스크 상세 조회 (task_id 필요)
- approve_design: 설계 승인 (task_id 필요, design.md 존재 필수)
- create_task: 새 태스크 생성 (title 필요, description 선택)
```

### 동작 정의

- before: Agent가 도구 선택을 추측 → 부정확한 응답
- after: 자연어 패턴 → 도구 매핑 가이드라인 → 정확한 도구 호출

### 엣지 케이스

- 프롬프트 토큰 증가 → Sonnet 충분한 컨텍스트 윈도우

### 영향 범위

- SlackBot Agent 응답 품질 전반 개선
- Lead Agent에는 영향 없음 (별도 프롬프트)

### 테스트 전략

- 프롬프트 내 도구명이 `_SLACK_BOT_TOOLS`와 일치하는지 정적 검증

### Out of Scope

- Lead Agent 프롬프트

---

## DoD 3: `read_task` 도구

### 구현 방법

`orchestrator/tools/tasks.py` 신규 파일.

```python
from orchestrator.config import TASKS_CURRENT_DIR, TASKS_DONE_DIR
from orchestrator.tools.task_utils import parse_spec_status

async def do_read_task(task_id: str) -> dict:
    """Read spec.md + design.md content for a task."""
    ...

@tool(
    "read_task",
    "Read task spec and design details",
    {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
)
async def read_task(args: dict) -> dict: ...
```

탐색 순서: `TASKS_CURRENT_DIR / f"{task_id}_*/"` → `TASKS_DONE_DIR / f"{task_id}_*"` (디렉토리 + .md 파일 모두 대응)

반환 JSON:
```json
{
  "task_id": "SP-086",
  "status": "approved",
  "has_design": true,
  "directory": "SP-086_slack-message-templates",
  "spec": "... spec.md 전문 (최대 8000자) ...",
  "design": "... design.md 전문 (최대 8000자) ..."
}
```

### 동작 정의

- task_id로 current/ → done/ 순서 탐색
- spec.md 읽기 + `parse_spec_status()` 호출
- design.md 존재 시 함께 반환
- 미발견 시 에러 반환

### 엣지 케이스

- 태스크 미발견 → `isError: true`, "Task SP-NNN not found"
- 긴 파일 → 8000자 truncation + `\n\n[TRUNCATED — use read_task for full text]` 경고
- design.md 없음 → `design: null`
- done/ 내 레거시 .md 파일 (디렉토리 아닌 단일 파일) → 파일 내용 직접 읽기

### 영향 범위

- 신규 도구, 기존 코드 영향 없음

### 테스트 전략

- 정상 케이스: spec + design 모두 존재
- spec만 존재 (design 없음)
- 태스크 미발견
- done/ 디렉토리에서 발견
- done/ 레거시 .md 파일에서 발견
- 8000자 초과 truncation

### Out of Scope

- 태스크 수정/삭제

---

## DoD 4: `approve_design` 도구

### 구현 방법

동일 파일 (`tasks.py`). 공통 헬퍼 재사용.

```python
from orchestrator.tools.task_utils import (
    git_commit_files,
    parse_spec_status,
    update_spec_status,
)

async def do_approve_design(task_id: str) -> dict:
    """Approve task design: update status + git commit + push."""
    ...

@tool(
    "approve_design",
    "Approve a task design (updates status to approved and commits)",
    {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]},
)
async def approve_design(args: dict) -> dict: ...
```

로직:
1. current/ 에서 태스크 디렉토리 찾기
2. design.md 존재 확인 (없으면 에러)
3. spec.md 읽기 → `parse_spec_status()` 호출
4. status 검증: `pending`/`design`만 승인 가능. `approved`/`running`/`done`이면 에러
5. `update_spec_status(content, "approved", "approved_at: YYYY-MM-DD")` 호출
6. spec.md 저장
7. `git_commit_files([spec.md, design.md], "chore: {task_id} 설계 승인")` — lock 보호 + push 포함

### 동작 정의

- before: Slack에서 설계 승인 불가 → 터미널 필요
- after: `@bot SP-086 승인해줘` → status 업데이트 + 커밋 + 푸시 완료

### 엣지 케이스

- design.md 미존재 → 에러: "설계 파일이 없습니다"
- 이미 approved/running/done → 에러: "이미 승인된 태스크입니다 (status: {current})"
- git commit/push 실패 → 에러 메시지 반환 (구조화된 stderr 포함)
- 태스크 미발견 → 에러: "Task not found"

### 영향 범위

- `.claude/tasks/` 파일 수정 + main 커밋/푸시 (CLAUDE.md 허용 범위)
- design.py의 `_update_spec_status` 제거 → `task_utils.update_spec_status` 재사용 (중복 제거)

### 테스트 전략

- 정상 승인: spec.md status 변경 + git 호출 확인
- design.md 없음 → 에러
- 이미 approved → 에러
- 태스크 미발견 → 에러
- git 명령은 mock

### Out of Scope

- 설계 reject
- 자동 /sdd-run 실행

---

## DoD 5: `create_task` 도구

### 구현 방법

동일 파일 (`tasks.py`).

```python
from orchestrator.tools.task_utils import (
    generate_slug,
    git_commit_files,
    next_sp_number,
)

async def do_create_task(title: str, description: str = "") -> dict:
    """Create a new task: auto-assign SP number + directory + spec.md."""
    ...

@tool(
    "create_task",
    "Create a new SDD task with auto-assigned SP number",
    {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Task title (Korean or English)"},
            "description": {"type": "string", "description": "Brief background/goal"},
        },
        "required": ["title"],
    },
)
async def create_task(args: dict) -> dict: ...
```

#### SP 번호 채번: `task_utils.next_sp_number()`

```python
def next_sp_number() -> int:
    """Scan current/ + done/ + backlog.md for max SP number, return max+1."""
    ...
```

current/ + done/ glob `SP-*` → 정규식으로 번호 추출 (디렉토리명 + .md 파일명 모두 대응). backlog.md도 스캔.

#### Slug 생성: `task_utils.generate_slug(title)`

```python
def generate_slug(title: str, max_len: int = 40) -> str:
    """Generate filesystem-safe slug from title. Handles Korean-only titles."""
    # 1. lowercase
    # 2. 영문/숫자/하이픈만 유지 (한글+특수문자 제거)
    # 3. 연속 하이픈 정리
    # 4. 빈 결과면 "task" fallback
    # 5. max_len 절단
    ...
```

로직:
1. `next_sp_number()` 호출 (lock 내부에서)
2. `generate_slug(title)` 호출
3. 디렉토리 생성: `TASKS_CURRENT_DIR / f"SP-{num:03d}_{slug}/"`
4. spec.md 스켈레톤 생성
5. `git_commit_files(...)` — lock 보호 + push

### 동작 정의

- before: 터미널에서 수동 생성 필요
- after: `@bot 태스크 만들어줘: Slack 메시지 템플릿화` → 자동 생성 + 커밋 + 푸시

### 엣지 케이스

- 한글 only 제목 → slug `"task"` fallback (예: `SP-088_task/`)
- title 빈 문자열 → 에러
- 동시 호출 → `git_lock`으로 번호 충돌 방지
- done/ 내 .md 파일과 디렉토리 혼재 → 번호 추출 시 양쪽 모두 처리

### 영향 범위

- `.claude/tasks/current/` 디렉토리에 파일 생성 + main 커밋/푸시
- 기존 코드 영향 없음

### 테스트 전략

- 정상 생성: 디렉토리 + spec.md 존재 확인
- SP 번호 자동 증가 검증
- slug 생성: 영문, 한글 only, 특수문자, 공백, 빈 문자열
- git 명령은 mock

### Out of Scope

- backlog.md 자동 업데이트 (SDD 규칙: 착수 = current/)
- DoD 자동 생성

---

## DoD 6: MCP 서버 + Agent 도구 등록

### 구현 방법

#### `orchestrator/tools/__init__.py`

```python
from orchestrator.tools.tasks import approve_design, create_task, read_task

def create_orchestrator_mcp_server():
    ...
    tools = [
        # ... 기존 도구 ...
        read_task,
        approve_design,
        create_task,
    ]
```

#### `orchestrator/agents.py`

```python
_SLACK_BOT_TOOLS = [
    # ... 기존 11개 ...
    "mcp__orch__read_task",
    "mcp__orch__approve_design",
    "mcp__orch__create_task",
]
```

`config.py` 프롬프트의 `## 사용 가능 도구` 섹션에 3줄 추가.

### 동작 정의

- before: 3개 도구 미등록 → Agent 호출 불가
- after: MCP 서버 등록 + Agent allowed_tools 등록 → 호출 가능

### 엣지 케이스

없음

### 영향 범위

- SlackBot Agent의 도구 목록 확장 (11 → 14)
- Lead Agent에는 영향 없음

### 테스트 전략

- agents.py의 `_SLACK_BOT_TOOLS` 길이 검증
- __init__.py에서 import 성공 확인

### 참고: 무조건 등록 근거

`read_task`(읽기 전용), `approve_design`/`create_task`(`.claude/tasks/` 조작)은 CLAUDE.md 커밋 경로 규칙상 main 직접 허용 범위. Lead Agent의 write 도구(코드 실행)와 성격이 다르므로 `ENABLE_AUTO_RUN` 플래그 없이 항상 등록.

### Out of Scope

- Lead Agent 도구 동기화

---

## DoD 7: 모델 환경변수화 (기본값 Sonnet)

### 구현 방법

`orchestrator/config.py`:
```python
# before
SLACK_BOT_AGENT_MODEL = "claude-haiku-4-5-20251001"

# after — Lead Agent 패턴과 동일 (날짜 없이)
SLACK_BOT_AGENT_MODEL = os.environ.get("SLACK_BOT_AGENT_MODEL", "claude-sonnet-4-6")
```

### 동작 정의

- before: Haiku 하드코딩
- after: 환경변수로 오버라이드 가능, 기본값 Sonnet

### 엣지 케이스

- 잘못된 모델 ID → Claude SDK 에러 → Agent timeout → 에러 메시지

### 영향 범위

- 비용 증가 (Sonnet > Haiku) → 환경변수로 다운그레이드 가능

### 테스트 전략

- 환경변수 미설정 → 기본값 확인
- 환경변수 설정 → 오버라이드 확인

### Out of Scope

- 모델별 프롬프트 분기

---

## DoD 8: 타임아웃/턴 수 조정 + TASKS_DONE_DIR 상수

### 구현 방법

`orchestrator/config.py`:
```python
# 신규 상수
TASKS_DONE_DIR = PROJECT_ROOT / ".claude" / "tasks" / "done"

# 변경
SLACK_BOT_MAX_TURNS = 12       # 도구 3개 추가 + Sonnet 다단계 추론
SLACK_BOT_AGENT_TIMEOUT = 120  # Sonnet 응답 시간 여유
```

### 동작 정의

- `TASKS_DONE_DIR`: done/ 탐색에 필요한 경로 상수 (기존 누락)
- 턴/타임아웃: 8→12턴, 60→120초

### 영향 범위

- SlackBot 응답 대기 시간 증가 가능 (최대 120초)
- 체감: Haiku(~5초) → Sonnet(~15초) 정도

### 테스트 전략

- config 값 존재 검증

### Out of Scope

- 프로그레스 표시 (타이핑 인디케이터)

---

## DoD 9: 기존 테스트 통과 + 신규 테스트

### 구현 방법

#### `test_task_utils.py` 신규

```python
class TestParseSpecStatus:
    def test_frontmatter_format(self): ...
    def test_blockquote_format(self): ...
    def test_blockquote_with_pipe_metadata(self): ...
    def test_no_status_returns_pending(self): ...

class TestUpdateSpecStatus:
    def test_replace_existing_blockquote(self): ...
    def test_replace_existing_frontmatter(self): ...
    def test_insert_when_missing(self): ...
    def test_with_metadata(self): ...

class TestGenerateSlug:
    def test_english_title(self): ...
    def test_korean_only_fallback(self): ...
    def test_mixed_korean_english(self): ...
    def test_special_characters(self): ...
    def test_max_length(self): ...

class TestNextSpNumber:
    def test_scan_directories(self, tmp_path): ...
    def test_scan_legacy_md_files(self, tmp_path): ...
    def test_empty_directory(self, tmp_path): ...
```

#### `test_tasks.py` 신규

```python
class TestReadTask:
    async def test_read_existing_task(self, tmp_path): ...
    async def test_read_task_not_found(self, tmp_path): ...
    async def test_read_task_no_design(self, tmp_path): ...
    async def test_read_task_truncation(self, tmp_path): ...
    async def test_read_done_task(self, tmp_path): ...
    async def test_read_legacy_md_file(self, tmp_path): ...

class TestApproveDesign:
    async def test_approve_success(self, tmp_path): ...
    async def test_approve_no_design(self, tmp_path): ...
    async def test_approve_already_approved(self, tmp_path): ...
    async def test_approve_task_not_found(self, tmp_path): ...
    async def test_approve_status_validation(self, tmp_path): ...

class TestCreateTask:
    async def test_create_basic(self, tmp_path): ...
    async def test_auto_increment_sp_number(self, tmp_path): ...
    async def test_korean_only_title_slug(self, tmp_path): ...
    async def test_empty_title_error(self): ...
```

#### `test_backlog.py` 추가

```python
def test_parse_blockquote_status(tmp_path): ...
def test_parse_blockquote_status_with_pipe(tmp_path): ...
```

### 테스트 전략

- 파일 시스템: `tmp_path` fixture
- git 명령: `asyncio.create_subprocess_exec` mock
- 기존 테스트 회귀 확인

### Out of Scope

- 통합 테스트 (Slack API)
