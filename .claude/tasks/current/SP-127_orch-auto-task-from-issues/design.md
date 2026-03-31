Now let me check a few more files to understand the spec template pattern and the backlog scanning:
Now let me check an existing spec.md for the template pattern:
Now let me check existing tests for the tools pattern:
Now I have enough context. Let me write the design.md:


Now I have all the context needed. Let me write the design.md:
The file write was blocked due to permission restrictions on the task directory. Here is the complete design.md content:

---

# SP-127: 오케스트레이터 — GitHub Issue → 태스크 자동 생성 (설계)

## 변경 파일 요약

| 파일 | 변경 | 설명 |
|------|------|------|
| `sdd-orchestrator/src/sdd_orchestrator/tools/issues.py` | **신규** | `scan_issues`, `auto_create_task` 도구 |
| `sdd-orchestrator/src/sdd_orchestrator/tools/__init__.py` | 수정 | 신규 도구 등록 + state_store 주입 |
| `sdd-orchestrator/src/sdd_orchestrator/prompts/lead_agent.md` | 수정 | 사이클에 scan_issues 단계 추가 |
| `sdd-orchestrator/src/sdd_orchestrator/main.py` | 수정 | state_store 주입 1줄 추가 |
| `sdd-orchestrator/tests/test_issues.py` | **신규** | issues.py 유닛 테스트 |

---

## DoD 1: `scan_issues` 도구 추가

### 구현 방법

**파일**: `sdd-orchestrator/src/sdd_orchestrator/tools/issues.py` (신규)

기존 `sentry.py`가 Sentry → GitHub Issue 생성을, `github.py`가 `gh` CLI 래퍼를 담당한다. 이 도구는 **GitHub Issue → SDD Task** 방향의 브릿지.

```python
# 핵심 구조
ALLOWED_LABELS = frozenset({"sentry", "bug"})
ISSUE_FIELDS = "number,title,body,labels,createdAt"

async def do_scan_issues() -> dict:
    """GitHub Issue 중 태스크 미연결 건 감지."""
    # 1. gh issue list --label sentry,bug --state open --json ...
    # 2. 기존 SP-NNN ↔ Issue 매핑 조회 (current/ + done/ spec.md에서 gh_issue: N 파싱)
    # 3. 매핑 없는 Issue만 반환
```

**gh CLI 호출**: `github.py`의 `_run_gh_command()` 재사용. 이미 `--repo` 자동 주입, 타임아웃, JSON 파싱이 구현되어 있음.

**Issue 조회 전략**: `--label` 플래그로 `sentry`, `bug` 라벨 필터. GitHub CLI는 `--label`을 AND로 처리하므로, 두 라벨을 **별도 호출**하여 합집합 구성. 중복 제거는 issue number 기준.

```python
async def _fetch_labeled_issues(label: str) -> list[dict]:
    """단일 라벨로 열린 Issue 조회."""
    result = await _run_gh_command(
        "issue", "list",
        "--label", label,
        "--state", "open",
        "--json", ISSUE_FIELDS,
        "--limit", "50",
    )
    if "error" in result:
        logger.warning("Failed to fetch issues with label=%s: %s", label, result["error"])
        return []
    return result.get("data", [])
```

**기존 매핑 조회**: `current/` + `done/` 디렉터리의 spec.md를 스캔하여 `gh_issue: #N` 메타데이터 파싱. state.db에는 별도 테이블 추가하지 않고 **spec.md 파일 기반**으로 매핑 (DB 스키마 변경 회피, spec.md가 SSOT).

```python
GH_ISSUE_RE = re.compile(r"gh_issue:\s*#?(\d+)")

def _get_existing_issue_mappings() -> set[int]:
    """current/ + done/ spec.md에서 gh_issue: N 추출."""
    mapped: set[int] = set()
    for tasks_dir in (TASKS_CURRENT_DIR, TASKS_DONE_DIR):
        if not tasks_dir.exists():
            continue
        for spec in tasks_dir.glob("SP-*_*/spec.md"):
            try:
                text = spec.read_text(encoding="utf-8")
                match = GH_ISSUE_RE.search(text)
                if match:
                    mapped.add(int(match.group(1)))
            except OSError:
                continue
    return mapped
```

### 동작 정의

- `scan_issues` 호출 → `sentry` + `bug` 라벨의 열린 Issue 합집합 조회
- 이미 매핑된 Issue 제외 → 미연결 Issue 목록 반환
- 반환 형식: `{"unlinked_issues": [...], "total_open": N, "already_linked": N}`

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| gh CLI 미설치/인증 실패 | `_run_gh_command` 에러 딕트 반환 → isError 응답 |
| Issue가 0건 | 빈 리스트 반환, 정상 응답 |
| sentry + bug 라벨 모두 있는 Issue | issue number 기준 중복 제거 |
| spec.md에 gh_issue 메타데이터 없는 기존 태스크 | 매핑 없음 처리 → 동일 Issue로 중복 태스크 생성 가능. 단, Issue title 기반 중복 방지는 Out of Scope |
| spec.md 읽기 실패 (권한/인코딩) | OSError catch → skip, 로그 경고 |

---

## DoD 2: `auto_create_task` 도구 추가

### 구현 방법

**파일**: `sdd-orchestrator/src/sdd_orchestrator/tools/issues.py`

기존 `tasks.py`의 `do_create_task()`를 **재사용하지 않고** 확장 버전을 구현. 이유: Issue 본문 파싱 + `gh_issue` 메타데이터 + `branch` 필드 + 우선순위 자동 판정이 필요하며, `do_create_task`의 spec 템플릿이 너무 단순함.

```python
async def do_auto_create_task(issue: dict) -> dict:
    """Issue 데이터에서 태스크 자동 생성."""
    # 1. 이미 매핑된 Issue인지 이중 체크
    existing = _get_existing_issue_mappings()
    if issue["number"] in existing:
        return _ok(json.dumps({"skipped": True, "reason": "already linked"}))

    # 2. Issue에서 정보 추출
    issue_number = issue["number"]
    title = _extract_title(issue)
    priority = _determine_priority(issue)
    description = _extract_description(issue)

    # 3. SP 번호 채번 + 디렉터리 생성 (task_utils 재사용)
    slug = generate_slug(title)
    # ... 5회 재시도 루프 (기존 do_create_task 패턴 동일)

    # 4. spec.md 생성 (풍부한 템플릿)
    # 5. state.db에 pending 등록
    # 6. git commit + push
```

**spec.md 템플릿**: 기존 `do_create_task`보다 풍부한 메타데이터 포함. `feedback_spec_branch_field.md` 규칙 준수하여 branch 필드 필수 포함.

```markdown
# {task_id}: {title}

- **branch**: feat/{task_id}_{branch_slug}
- **priority**: {priority}
- **scope**: backend
- **assignee**: AI
- **created**: {today}
- **gh_issue**: #{issue_number}

## 배경

GitHub Issue #{issue_number}에서 자동 생성.

{issue_body_summary}

## DoD (Definition of Done)

1. Issue #{issue_number}에서 보고된 문제 수정
```

**title 추출**: Sentry Issue 제목은 `[Sentry/project] ErrorType` 형식. 접두사 제거 후 사용.

```python
_SENTRY_TITLE_RE = re.compile(r"^\[Sentry/[^\]]+\]\s*")

def _extract_title(issue: dict) -> str:
    raw = issue.get("title", "").strip()
    return _SENTRY_TITLE_RE.sub("", raw) or raw
```

**description 추출**: Issue body에서 전문 포함하되, 4000자로 트렁케이트.

```python
_MAX_BODY_LEN = 4000

def _extract_description(issue: dict) -> str:
    body = issue.get("body", "") or ""
    if len(body) > _MAX_BODY_LEN:
        body = body[:_MAX_BODY_LEN] + "\n\n[truncated]"
    return body
```

**state_store 주입**: `tasks.py`와 동일 패턴 — 모듈 레벨 `_state_store` + `set_state_store()`.

**task_utils 재사용**: `next_sp_number`, `generate_slug`, `git_commit_files`, `_ok`, `_error`, `today_str` 모두 `task_utils.py`에서 import.

### 동작 정의

- LLM이 `scan_issues` 결과의 개별 Issue를 `auto_create_task`에 전달
- spec.md 생성 → state.db에 `pending` 등록 → git commit + push
- 반환: `{"task_id": "SP-NNN", "issue_number": N, "priority": "P1"}`

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| Issue body가 비어있음 | description 빈 문자열, spec 배경에 "상세 정보 없음" 기재 |
| Issue body가 매우 길음 (>4000자) | 4000자 트렁케이트 |
| SP 번호 충돌 | `do_create_task`와 동일한 5회 재시도 루프 |
| git commit 실패 | 디렉터리 삭제 + state.db 롤백 (기존 패턴) |
| state_store 미주입 | _error 반환 |
| Issue title이 한국어만 | `generate_slug` fallback → "task" 슬러그 |

---

## DoD 3: Issue ↔ SP-NNN 매핑으로 중복 스킵

### 구현 방법

`scan_issues` 내부의 `_get_existing_issue_mappings()`이 담당. spec.md의 `gh_issue: #N` 필드가 매핑 키.

`auto_create_task`가 spec.md에 `gh_issue: #{issue_number}`를 기록하므로, 다음 사이클의 `scan_issues`에서 자동으로 스킵됨.

### 동작 정의

- `scan_issues` → `_get_existing_issue_mappings()` → spec.md 파싱 → Issue number set
- 이미 매핑된 Issue는 결과에서 제외
- `auto_create_task` 내부에서도 매핑 존재 **이중 체크** 후 스킵 (같은 사이클 내 race condition 방지)

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| 같은 사이클에서 여러 Issue 동시 처리 | git commit이 순차적(git_lock)이므로 파일시스템 충돌 없음. `auto_create_task` 내부에서 매번 `_get_existing_issue_mappings()` 재호출하여 이전 생성분 감지 |
| spec.md를 수동 편집하여 gh_issue 제거 | 다음 사이클에서 중복 태스크 생성 가능 → 허용 (수동 편집은 의도적 행위) |

---

## DoD 4: label 기반 필터

### 구현 방법

모듈 상수로 허용 라벨 정의:

```python
ALLOWED_LABELS: frozenset[str] = frozenset({"sentry", "bug"})
```

`scan_issues`에서 각 라벨별로 `gh issue list --label {label}` 호출 후 합집합. `feature`, `enhancement` 등 다른 라벨 Issue는 조회 자체를 하지 않으므로 자연스럽게 제외.

### 동작 정의

- `sentry` 라벨 Issue: 조회 대상
- `bug` 라벨 Issue: 조회 대상
- `sentry` + `bug` 모두 있는 Issue: 1건으로 카운트 (number 중복 제거)
- `feature`, `enhancement` 등: 조회 안 함

---

## DoD 5: 사이클에 scan_issues 단계 추가

### 구현 방법

**파일**: `sdd-orchestrator/src/sdd_orchestrator/prompts/lead_agent.md`

Lead Agent 프롬프트에 `scan_issues` + `auto_create_task` 도구 설명 추가 + 사이클 단계에 삽입.

**Your Tools 섹션 추가**:
```
13. **scan_issues** — Scan open GitHub Issues (sentry/bug labels) for unlinked tasks
14. **auto_create_task** — Create SDD task from a GitHub Issue (spec.md + state.db)
```

**Each Cycle 섹션 수정** — 5번 `sentry_scan` 바로 뒤에 추가:
```
6. Call scan_issues to find GitHub Issues without linked tasks
7. For each unlinked issue → call auto_create_task
```
(이후 번호 재조정)

**Decision Rules 추가**:
```
- If scan_issues returns unlinked issues → call auto_create_task for each
```

**파일**: `sdd-orchestrator/src/sdd_orchestrator/tools/__init__.py`

```python
# import 추가
from sdd_orchestrator.tools.issues import auto_create_task, scan_issues

# tools 리스트에 추가 (sentry_scan 바로 뒤)
tools = [
    scan_backlog,
    check_prs,
    check_workflows,
    check_running_worktrees,
    sentry_scan,
    scan_issues,       # 추가
    auto_create_task,  # 추가
    ...
]
```

**파일**: `sdd-orchestrator/src/sdd_orchestrator/main.py`

`OrchestratorDaemon.__init__`에 state_store 주입 추가:

```python
from sdd_orchestrator.tools.issues import set_state_store as set_issues_store
# __init__ 내부, 기존 set_tasks_store(self.state) 뒤에:
set_issues_store(self.state)
```

### 동작 정의

- 매 사이클마다 `scan_issues` 호출 가능 (LLM 판단)
- sentry_scan이 GitHub Issue를 생성 → 다음 사이클(또는 같은 사이클)에서 scan_issues가 감지 → auto_create_task으로 태스크 생성
- 생성된 태스크는 `pending` 상태 → auto_design → approved → sdd-run 파이프라인으로 자동 진행

---

## DoD 6: 우선순위 자동 판정

### 구현 방법

```python
def _determine_priority(issue: dict) -> str:
    """라벨 기반 우선순위 판정. sentry > bug."""
    labels = {lbl.get("name", "") for lbl in (issue.get("labels") or [])}
    if "sentry" in labels:
        return "P1"
    if "bug" in labels:
        return "P2"
    return "P2"  # fallback
```

`sentry` 라벨이 있으면 P1, `bug`만 있으면 P2. 둘 다 있으면 sentry 우선 → P1.

### 동작 정의

- Sentry에서 자동 생성된 Issue (sentry + bug 라벨): **P1**
- 수동 등록 bug Issue (bug 라벨만): **P2**

---

## 영향 범위

| 모듈 | 영향 |
|------|------|
| `tools/issues.py` | 신규 파일 — scan_issues, auto_create_task |
| `tools/__init__.py` | import 추가, tools 리스트 확장 |
| `prompts/lead_agent.md` | 도구 목록 + 사이클 단계 + 결정 규칙 추가 |
| `main.py` | set_state_store 주입 1줄 추가 |
| `state.py` | **변경 없음** (기존 task_status 테이블 그대로 사용) |
| `task_utils.py` | **변경 없음** (기존 함수 재사용) |

---

## 테스트 전략

**파일**: `sdd-orchestrator/tests/test_issues.py` (신규)

기존 `test_tasks.py`, `test_sentry.py` 패턴 준수: `do_*` 코어 함수 직접 테스트, gh CLI는 mock.

### TestScanIssues

| # | 테스트 | 검증 |
|---|--------|------|
| 1 | `test_returns_unlinked_issues` | 미연결 Issue 2건 반환 확인 |
| 2 | `test_skips_linked_issues` | spec.md에 gh_issue 있는 Issue 스킵 |
| 3 | `test_deduplicates_across_labels` | sentry+bug 중복 Issue → 1건 |
| 4 | `test_empty_when_no_issues` | Issue 0건 → 빈 리스트, 정상 응답 |
| 5 | `test_gh_error` | gh CLI 실패 → isError 응답 |

### TestAutoCreateTask

| # | 테스트 | 검증 |
|---|--------|------|
| 1 | `test_create_from_sentry_issue` | spec.md 생성 + state.db pending 등록 |
| 2 | `test_priority_sentry_p1` | sentry 라벨 → P1 |
| 3 | `test_priority_bug_p2` | bug 라벨만 → P2 |
| 4 | `test_skip_already_linked` | 이미 매핑된 Issue → skipped 반환 |
| 5 | `test_git_failure_rollback` | git 실패 → 디렉터리 삭제 + DB 롤백 |
| 6 | `test_sentry_title_cleanup` | `[Sentry/proj]` 접두사 제거 |
| 7 | `test_spec_contains_gh_issue_field` | spec.md에 `gh_issue: #N` 포함 |
| 8 | `test_spec_contains_branch_field` | spec.md에 `branch:` 필드 포함 |
| 9 | `test_empty_body_issue` | body 빈 Issue → 정상 생성 |

### TestHelpers

| # | 테스트 | 검증 |
|---|--------|------|
| 1 | `test_parses_gh_issue_from_spec` | spec.md에 `gh_issue: #42` → {42} |
| 2 | `test_no_gh_issue_field` | gh_issue 없는 spec → 빈 set |
| 3 | `test_scans_both_dirs` | current/ + done/ 양쪽 스캔 |
| 4 | `test_priority_sentry_over_bug` | sentry+bug → P1 |
| 5 | `test_priority_fallback` | 라벨 없음 → P2 |

**Mock 전략**: `_run_gh_command`를 patch하여 gh CLI 호출 차단. `git_commit_files`를 AsyncMock(return_value=None)으로 git 호출 차단. StateStore는 실제 tmp_path SQLite 사용 (기존 test_tasks.py 패턴).

---

## Out of Scope

- **state.db 스키마 변경**: Issue ↔ Task 매핑을 DB 테이블로 관리하지 않음. spec.md 파일 기반으로 충분.
- **Issue 자동 close**: 태스크 완료 시 GitHub Issue를 자동으로 close하는 기능은 별도 태스크.
- **feature/enhancement 라벨 지원**: spec에 명시된 sentry/bug만 대상.
- **Issue 코멘트 파싱**: body만 사용, 코멘트는 무시.
- **Rate limiting**: gh CLI의 기본 rate limit 처리에 의존. 별도 쓰로틀링 미구현.
- **deterministic auto-create**: `_auto_launch_approved`처럼 LLM 판단 없이 자동 실행하는 방식은 이번 스코프 밖. LLM 사이클에서 도구 호출로 처리.