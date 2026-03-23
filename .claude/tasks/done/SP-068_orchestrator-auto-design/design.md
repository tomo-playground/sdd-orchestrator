# SP-068 상세 설계: 오케스트레이터 Phase 3 — 자동 설계

> 간소화 설계 (변경 파일 4~7, DB/API 변경 없음)

## 변경 파일 요약

| 파일 | 변경 | 신규 |
|------|------|------|
| `orchestrator/config.py` | 상수 추가 (DESIGNER_MODEL, ENABLE_AUTO_DESIGN) | |
| `orchestrator/agents.py` | designer 서브에이전트 정의 + Lead prompt 확장 | |
| `orchestrator/rules.py` | `can_auto_approve()` 추가 | |
| `orchestrator/tools/design.py` | | 신규 |
| `orchestrator/utils.py` | | 신규 (_query_agent 텍스트 수집 로직 추출) |
| `orchestrator/tools/__init__.py` | design 도구 등록 | |
| `orchestrator/tests/test_design.py` | | 신규 |
| `orchestrator/tests/test_rules.py` | auto_approve 테스트 추가 | |

---

## DoD별 구현 방법 + 테스트 전략

### 1. Designer 서브에이전트

**구현 방법:**
- `orchestrator/config.py`에 추가:
  - `DESIGNER_MODEL = "claude-opus-4-6"` — 설계 품질 확보
  - `ENABLE_AUTO_DESIGN: bool` — 환경변수 `ORCH_AUTO_DESIGN=1`로 제어
  - `DESIGN_TIMEOUT = 600` — designer 타임아웃 (10분)
- `orchestrator/agents.py`에 `create_designer_options(task_dir: Path) -> ClaudeAgentOptions` 추가
  - system prompt: `/sdd-design` Phase 2~4 로직을 텍스트로 포함
    - 코드 탐색 (Read/Grep/Glob 허용)
    - 소크라테스 질문 생략 (FEATURES + CLAUDE.md + 코드 패턴으로 자율 결정)
    - 6항목 설계 (구현방법/동작정의/엣지케이스/영향범위/테스트전략/Out of Scope)
  - allowed_tools: `Read`, `Glob`, `Grep`, `Bash(cat:*)` — 읽기 전용
  - model: `DESIGNER_MODEL`
  - cwd: `PROJECT_ROOT`
- `orchestrator/tools/design.py` 신규 파일
  - `run_auto_design(task_id: str) -> dict` — MCP 도구
    1. `current/{task_id}_*/spec.md` 로드
    2. status가 `pending`인지 확인 (아니면 스킵)
    3. Claude SDK로 designer 서브에이전트 실행
    4. 응답에서 design.md 내용 추출
    5. `current/{task_id}_*/design.md`에 저장
    6. spec.md의 `status: pending` → `status: design` 변경
    7. `git add + commit + push` — **`asyncio.Lock()`으로 커밋 직렬화** (여러 태스크 동시 설계 시 push 충돌 방지). 커밋 메시지: `chore(auto): SP-NNN 자동 설계 — status: design`
    8. 자동 승인 규칙 평가 → 조건 충족 시 `status: approved` + 커밋 (`chore(auto): SP-NNN 자동 승인`)

**엣지 케이스:**
- designer 타임아웃 → state에 로그 + 다음 사이클에서 재시도
- design.md 생성 실패 → status 변경하지 않음 (pending 유지)
- 동시에 같은 태스크 설계 시도 → runs 테이블에 `status='designing'` 레코드로 중복 방지 (SP-067 runs 테이블 status ENUM 확장: `running | designing | failed | done`)
- **git push 충돌** → `asyncio.Lock()`으로 직렬화. 그래도 실패 시 `git pull --rebase && git push` 재시도 1회

**Claude SDK 재사용:** `main.py`의 `_query_agent` 텍스트 수집 로직을 `orchestrator/utils.py`로 추출하여 `run_auto_design`에서도 호출. 코드 중복 방지.

**테스트 전략:**
- `test_run_auto_design_creates_file` — design.md 생성 확인
- `test_run_auto_design_skips_non_pending` — pending 아니면 스킵
- `test_run_auto_design_timeout` — 타임아웃 시 status 유지

### 2. 자동 승인 규칙

**구현 방법:**
- `orchestrator/rules.py`에 `can_auto_approve(design_md: str, spec_md: str) -> tuple[bool, str]` 추가
  - 조건 (모두 충족 시 자동 승인):
    1. BLOCKER 마커 없음 (`re.search(r"(?:^|\n).*\*\*BLOCKER\*\*", design_md)` — 단순 문자열 매칭 대신 마크다운 볼드 패턴으로 오탐 방지)
    2. 변경 파일 6개 이하 (design.md의 변경 파일 요약 테이블 파싱)
    3. DB 스키마 변경 없음 (`models/*.py`, `alembic/` 패턴 미포함)
    4. 외부 의존성 추가 없음 (`pyproject.toml`, `package.json`, `requirements*.txt`, `*.lock` 패턴 미포함)
  - 반환: `(True, "auto-approved: N files, no blocker")` 또는 `(False, "reason")`
- `run_auto_design` 내에서 design.md 생성 후 즉시 `can_auto_approve()` 호출
  - True → `status: approved` + `approved_at` + 커밋
  - False → `status: design` 유지 + 콘솔 로그로 사유 출력

**테스트 전략:**
- `test_auto_approve_simple_task` — 3파일 변경, BLOCKER 없음 → True
- `test_reject_blocker` — BLOCKER 포함 → False
- `test_reject_db_change` — models/ 포함 → False
- `test_reject_too_many_files` — 7파일 → False
- `test_reject_new_dependency` — pyproject.toml 포함 → False

### 3. 리뷰어 서브에이전트

**구현 방법:**
- `run_auto_design` 내에서 design.md 생성 후, 자동 승인 전에 리뷰 실행
- 리뷰어 결정 로직 (design.md의 변경 파일에서 파싱):
  - `state.py` 변경 → Tech Lead 리뷰
  - `models/`, `alembic/` → DBA 리뷰
  - 그 외 → 리뷰 스킵 (변경 파일 3개 이하)
- 리뷰어 실행: Claude SDK로 서브에이전트 호출 (Sonnet 모델)
  - 입력: design.md + spec.md
  - 출력: PASS / WARNING / BLOCKER + 피드백
- BLOCKER → `status: design` 유지 + 다음 사이클에서 1회 재시도 (사이클 점유 방지). 총 3회 실패 → "사람 리뷰 필요" 로그
- 변경 파일 수 파싱 실패 → 보수적으로 7파일 이상으로 간주 (자동 승인 거부)

**테스트 전략:**
- `test_reviewer_called_for_state_change` — state.py 포함 시 Tech Lead 호출
- `test_reviewer_skipped_for_small_change` — 3파일 이하 스킵

### 4. 통합 — Lead Agent 확장

**구현 방법:**
- `config.py` system prompt 확장:
  - Decision Rules에 추가: "pending 태스크 + spec 있음 + ENABLE_AUTO_DESIGN → `run_auto_design` 호출"
- `agents.py`의 `allowed_tools`에 조건부 추가:
  - `ENABLE_AUTO_DESIGN=True` → `mcp__orch__run_auto_design` 추가
- `tools/__init__.py`에 `run_auto_design` 등록

**테스트 전략:**
- `test_auto_design_disabled_by_default` — ENABLE_AUTO_DESIGN=False면 도구 미등록

---

## Out of Scope
- Slack/외부 알림 (SP-069)
- 사람 승인 UI (현재 `/sdd-design SP-NNN approved` CLI로 충분)
- designer가 소크라테스 질문을 사람에게 하는 기능 (질문 없이 자율 결정)
