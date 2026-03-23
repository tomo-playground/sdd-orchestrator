# SP-066 상세 설계: SDD 오케스트레이터 뼈대

> 작성: 2026-03-23 | status: design
> 리뷰: Claude 자체분석 + Gemini 교차리뷰 반영 (BLOCKER 3 + WARNING 4 수정)

## 기술 스택 확정

| 항목 | 선택 | 근거 |
|------|------|------|
| SDK | `claude-agent-sdk` (PyPI) / import `claude_agent_sdk` | Claude Code CLI 래퍼 — $200/월 Max 구독에 포함, 별도 API 과금 없음 |
| 런타임 | Python 3.12+ (시스템 Python) | backend와 독립 venv |
| 상태 저장 | SQLite3 (stdlib) | 외부 의존성 0, 단일 프로세스 충분 |
| CLI 래퍼 | `gh` (GitHub CLI) | 이미 설치됨, JSON 출력 지원 |
| 비동기 | `asyncio` (stdlib) | SDK가 async 기반 |
| 로깅 | `logging` (stdlib) | 파일+콘솔 동시 출력, 데몬 디버깅 필수 |

## 디렉토리 구조

```
orchestrator/
├── __init__.py
├── __main__.py           # python -m orchestrator 진입점
├── main.py               # OrchestratorDaemon 클래스 (이벤트 루프)
├── config.py             # 설정 상수 (CYCLE_INTERVAL, DB_PATH 등)
├── agents.py             # Lead Agent 정의 (system prompt + options)
├── state.py              # SQLite 상태 저장소 (StateStore 클래스)
├── tools/
│   ├── __init__.py       # create_orchestrator_mcp_server() 팩토리
│   ├── backlog.py        # scan_backlog 도구
│   └── github.py         # check_prs, check_workflows 도구
├── tests/
│   ├── __init__.py
│   ├── test_backlog.py   # backlog 파서 단위 테스트
│   ├── test_github.py    # gh CLI 래퍼 단위 테스트
│   └── test_state.py     # StateStore 단위 테스트
├── pyproject.toml        # 의존성 + 메타데이터
└── .gitignore            # state.db, *.log 제외
```

## DoD별 상세 설계

---

### 1. 프로젝트 구조

#### DoD: `orchestrator/` 디렉토리에 Agent SDK 기반 Python 프로젝트 생성

**구현방법**: `orchestrator/` 최상위 디렉토리 생성. backend/frontend와 완전 독립된 Python 패키지. `__init__.py`에 버전 정보만.

**동작정의**: `orchestrator/` 는 standalone 패키지. backend의 `requirements.txt`나 venv에 영향 없음.

**엣지케이스**: 없음 (신규 디렉토리)

**영향범위**: 없음. 기존 코드와 완전 격리.

#### DoD: `pyproject.toml`에 `claude-agent-sdk` 의존성 정의

**구현방법**:
```toml
[project]
name = "shorts-producer-orchestrator"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "claude-agent-sdk>=0.0.20",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[project.scripts]
orchestrator = "orchestrator.main:cli_entry"
```

**동작정의**: `pip install -e orchestrator/` 또는 `pip install claude-agent-sdk` 후 `python -m orchestrator`로 실행.

**엣지케이스**: SDK 버전 호환성 — `>=0.0.20` 하한만 지정, 상한 없음 (빠르게 진화 중).

**테스트전략**: `pip install -e .` 성공 확인.

#### DoD: `orchestrator/main.py`에 이벤트 루프 진입점 구현 (10분 주기)

**구현방법**:
```python
class OrchestratorDaemon:
    def __init__(self, interval: int = CYCLE_INTERVAL):
        self.interval = interval
        self.cycle = 0
        self.stop_event = asyncio.Event()
        self.state = StateStore()

    async def run(self):
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.stop_event.set)

        self._preflight_check()  # 환경변수/CLI 검증

        while not self.stop_event.is_set():
            self.cycle += 1
            await self._run_cycle()
            # stop_event가 set되면 즉시 탈출, 아니면 interval 대기
            try:
                await asyncio.wait_for(
                    self.stop_event.wait(), timeout=self.interval
                )
            except asyncio.TimeoutError:
                pass  # 정상 — 다음 사이클

        self.state.close()
        logger.info("Shutdown complete")

    def _preflight_check(self):
        """기동 시 필수 조건 검증 (fail-fast)"""
        # 1. gh CLI 설치 + 인증 확인
        # 2. Claude Code CLI 확인
        # 3. backlog.md 존재 확인
        # 실패 시 명확한 에러 메시지 + sys.exit(1)

    async def _run_cycle(self):
        # 1. Lead Agent에게 현재 상태 전달
        # 2. Agent가 도구로 backlog/PR/workflow 조회
        # 3. Agent 판단 결과를 state에 기록 + 콘솔 출력
```

**동작정의**:
- 시작 시 `_preflight_check()`로 환경 검증 (fail-fast)
- 10분(600초) 간격으로 사이클 반복
- 각 사이클: Lead Agent 호출 → 도구 실행 → 결과 기록
- Ctrl+C → `stop_event.set()` → sleep 즉시 탈출 → 상태 저장 → 종료

**엣지케이스**:
- 사이클 중 Agent 타임아웃: `max_turns=10` 제한
- Agent SDK 연결 실패: try/except로 에러 로깅 후 다음 사이클 대기
- 첫 사이클에서 바로 Ctrl+C: `asyncio.wait_for`가 즉시 탈출

**테스트전략**: 단위 테스트 — `interval=0`으로 1사이클 실행 후 자동 종료 확인.

---

### 2. 커스텀 도구

#### DoD: `scan_backlog` — backlog.md 파싱

**구현방법**:
```python
@tool("scan_backlog", "Parse .claude/tasks/backlog.md and return task queue", {})
async def scan_backlog(args: dict) -> dict:
    # 1. backlog.md 읽기
    # 2. 섹션 기반 파싱: ## P0 / ## P1 / ## P2 등 헤더로 분할
    # 3. ## 완료 섹션은 스킵
    # 4. 각 섹션 내 체크박스 파싱:
    #    r"- \[ \] (SP-\d+)\s*—\s*(.+)" (미완료)
    #    파이프(|) 구분 메타데이터: depends, scope, approved 등
    # 5. .claude/tasks/current/ 스캔하여 spec.md frontmatter 병합
    # 반환: [{id, priority, status, depends_on, description, has_design}]
```

**동작정의**:
- 섹션 헤더(`## P0`, `## P1` 등)로 우선순위 결정
- `## 완료` 섹션은 전체 스킵
- 파이프(`|`) 구분 메타데이터 파싱: `depends: SP-NNN`, `scope: backend`, `**approved**`
- 마크다운 링크(`[명세](...)`)는 보존하되 파싱에 영향 없음
- 각 태스크에 대해 `current/SP-NNN_*/spec.md` 존재 여부 + frontmatter `status` 확인
- `design.md` 존재 여부 → `has_design: true/false`

**엣지케이스**:
- backlog.md 없음 → 빈 리스트 반환 + 경고 메시지
- spec.md 없는 backlog 항목 → `status: "backlog_only"` (아직 current에 미등록)
- frontmatter 파싱 실패 → 해당 태스크 스킵 + 경고
- 한 줄에 다수 태스크 (완료 섹션 스타일) → 스킵 (완료 섹션이므로)

**테스트전략**: 샘플 backlog.md + spec.md 픽스처로 파싱 결과 검증. 엣지케이스 3종 포함.

#### DoD: `check_prs` — gh pr list 래퍼

**구현방법**:
```python
@tool("check_prs", "List open GitHub PRs with CI/review status", {})
async def check_prs(args: dict) -> dict:
    try:
        proc = await asyncio.create_subprocess_exec(
            "gh", "pr", "list", "--state", "open", "--json",
            "number,title,headRefName,state,reviewDecision,statusCheckRollup,labels",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode != 0:
            return {"content": [{"type": "text", "text": f"gh error: {stderr.decode()}"}]}
        prs = json.loads(stdout.decode())
        # SP-NNN 매칭, 상태 요약
        return {"content": [{"type": "text", "text": json.dumps(summarize_prs(prs))}]}
    except asyncio.TimeoutError:
        return {"content": [{"type": "text", "text": "GitHub API timeout (15s). Skip this cycle."}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error: {e}"}]}
```

**동작정의**:
- `reviewDecision`: APPROVED / CHANGES_REQUESTED / REVIEW_REQUIRED / null
- `statusCheckRollup`: SUCCESS / FAILURE / PENDING 종합 판정
- SP-NNN 태스크와 PR 매칭 (브랜치명에서 추출)
- 에러 시 Agent에게 구조화된 에러 메시지 반환 (도구가 뻗지 않음)

**엣지케이스**:
- `gh` CLI 미설치/미인증 → preflight에서 사전 차단
- 네트워크 타임아웃 (15초) → 에러 dict 반환, Agent가 스킵 판단
- PR 0개 → 빈 리스트 (정상)
- Rate limit → stderr에 메시지 포함, Agent에게 전달

**테스트전략**: `asyncio.create_subprocess_exec` mock + JSON 파싱 검증.

#### DoD: `check_workflows` — gh run list 래퍼

**구현방법**: `check_prs`와 동일한 비동기 subprocess 패턴.
```python
@tool("check_workflows", "List recent GitHub Actions runs", {"limit": int})
async def check_workflows(args: dict) -> dict:
    limit = args.get("limit", 10)
    proc = await asyncio.create_subprocess_exec(
        "gh", "run", "list", "--limit", str(limit), "--json",
        "databaseId,workflowName,status,conclusion,headBranch,createdAt",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    # 파싱: stuck 감지 (status=in_progress + 30분 초과), 실패 감지
```

**동작정의**:
- `status`: completed / in_progress / queued
- `conclusion`: success / failure / skipped / cancelled
- stuck 판정: `in_progress` + `createdAt` > 30분 전

**엣지케이스**: check_prs와 동일 (비동기 subprocess + 에러 dict 반환)

**테스트전략**: subprocess mock + stuck 판정 로직 단위 테스트.

---

### 3. 상태 관리

#### DoD: SQLite 기반 상태 저장소

**구현방법**:
```python
class StateStore:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS cycles (
                id INTEGER PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT DEFAULT 'running',  -- running/success/error
                summary TEXT                     -- Agent 요약 텍스트
            );
            CREATE TABLE IF NOT EXISTS decision_log (
                id INTEGER PRIMARY KEY,
                cycle_id INTEGER REFERENCES cycles(id),
                action TEXT NOT NULL,            -- scan/check_pr/delegate/skip
                target TEXT,                     -- SP-NNN or PR#
                reason TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()
```

**동작정의**:
- `cycles`: 각 10분 사이클의 시작/종료/결과 기록
- `decision_log`: Agent의 판단 근거 기록 (감사 추적용)
- `active_runs` 테이블은 SP-067에서 추가 (Phase 1은 읽기 전용 — YAGNI)

**엣지케이스**:
- DB 파일 없음 → 자동 생성 (sqlite3 기본 동작)
- 동시 접근 → 단일 프로세스이므로 문제 없음
- 디스크 풀 → sqlite3.OperationalError 캐치 + 로깅

#### DoD: 시작 시 이전 상태 로드, 종료 시 상태 저장

**구현방법**: SQLite는 트랜잭션 기반이므로 별도 "로드/저장" 불필요. `StateStore.__init__`에서 연결 + WAL 모드 설정, `close()`에서 커밋+종료.

**동작정의**:
- 시작: `StateStore()` 생성 시 기존 DB 연결 (이전 사이클 데이터 보존)
- 종료: `self.conn.commit()` → `self.conn.close()`
- 비정상 종료(kill -9): WAL 모드가 데이터 안전 보장

**테스트전략**: 상태 기록 → StateStore 재생성 → 이전 상태 조회 검증.

---

### 4. Lead Agent

#### DoD: Lead Agent 정의

**구현방법**:
```python
def create_lead_agent_options(mcp_server) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model="claude-sonnet-4-5",
        system_prompt=LEAD_AGENT_SYSTEM_PROMPT,
        mcp_servers={"orch": mcp_server},
        allowed_tools=[
            "mcp__orch__scan_backlog",
            "mcp__orch__check_prs",
            "mcp__orch__check_workflows",
        ],
        permission_mode="default",
        max_turns=10,
        cwd=Path(PROJECT_ROOT),
    )
```

**동작정의**: Sonnet 모델. 커스텀 MCP 도구 3개만 허용. `permission_mode="default"` — 읽기 전용 Phase이므로 파일 편집 권한 불필요.

#### DoD: 시스템 프롬프트에 SDD 워크플로우 규칙 포함

**구현방법**: `config.py`에 `LEAD_AGENT_SYSTEM_PROMPT` 상수 정의. 포함 내용:
- 역할: "SDD 오케스트레이터 Lead Agent"
- 태스크 상태 머신: pending → design → approved → running → done
- 판단 기준: depends_on 충족 여부, status별 다음 행동
- 출력 형식: 대시보드 형태 (현재 상태 + 다음 행동 제안)
- 제약: Phase 1은 읽기 전용. 실행/머지 판단만 제안, 실제 실행 안 함.

**동작정의**: Agent가 도구를 호출하여 현재 상태를 수집하고, 대시보드 + 다음 행동 제안을 텍스트로 출력.

**엣지케이스**:
- 도구 호출 실패 시 Agent가 자체 판단으로 스킵 (시스템 프롬프트에 명시)
- 판단 불가 시 "사람 확인 필요" 출력

#### DoD: 10분마다 현재 상태를 Lead Agent에 전달

**구현방법**:
```python
async def _run_cycle(self):
    options = create_lead_agent_options(self.mcp_server)
    try:
        async with ClaudeSDKClient(options=options) as client:
            prev = self.state.get_last_cycle_summary()
            prompt = f"""사이클 #{self.cycle} 점검을 시작합니다.
이전 사이클 요약: {prev or '첫 사이클'}

도구를 사용하여:
1. scan_backlog → 백로그 + 태스크 상태 확인
2. check_prs → 열린 PR 상태 확인
3. check_workflows → GitHub Actions 상태 확인
4. 종합 판단 → 대시보드 출력 + 다음 행동 제안"""

            await client.query(prompt)
            async for msg in client.receive_response():
                # 텍스트 수집 → 콘솔 출력 + state 기록
    except Exception as e:
        logger.error(f"Cycle #{self.cycle} failed: {e}")
        self.state.record_cycle_error(self.cycle, str(e))
```

**동작정의**: 매 사이클마다 새 `ClaudeSDKClient` 생성 (stateless per cycle). 이전 사이클 요약만 프롬프트로 전달하여 연속성 유지. 실패 시 로깅 후 다음 사이클 계속.

**테스트전략**: Mock SDK client + 프롬프트 구성 검증.

---

### 5. 실행 가능성

#### DoD: `python -m orchestrator.main`으로 실행

**구현방법**:
```python
# orchestrator/__main__.py
from orchestrator.main import cli_entry
cli_entry()

# orchestrator/main.py
def cli_entry():
    import asyncio
    daemon = OrchestratorDaemon()
    asyncio.run(daemon.run())
```

**동작정의**: `python -m orchestrator` 또는 `python -m orchestrator.main` 모두 동작.

#### DoD: 첫 실행 시 backlog 읽고 대시보드 콘솔 출력

**동작정의**: 첫 사이클에서 Lead Agent가 도구를 호출하고, 결과를 대시보드 형태로 출력.

#### DoD: Ctrl+C로 graceful shutdown

**구현방법**: `loop.add_signal_handler()` + `asyncio.Event` 기반 즉시 탈출.

**동작정의**:
- Ctrl+C → `stop_event.set()` → `asyncio.wait_for` 즉시 탈출
- Agent 호출 중이면 `ClaudeSDKClient.__aexit__` 정리 후 종료
- 종료 전 `state.close()`로 DB 커밋

---

### 6. 품질

#### DoD: 기존 테스트 영향 없음

**검증**: orchestrator/는 독립 패키지. backend/frontend import 없음. CI 파이프라인에 orchestrator 테스트 미포함.

#### DoD: orchestrator 자체 단위 테스트 통과

**테스트 범위**:
- `test_backlog.py`: backlog.md 파서 — 정상 파싱, 빈 파일, 메타데이터 추출, 엣지케이스 (4+개)
- `test_github.py`: gh CLI 래퍼 — subprocess mock, JSON 파싱, 타임아웃, stuck 판정 (4+개)
- `test_state.py`: StateStore — 테이블 생성, 사이클 기록, 재시작 후 조회, WAL 모드 (4+개)

**실행**: `cd orchestrator && pytest tests/`

#### DoD: 린트 통과 (ruff)

**구현방법**: `orchestrator/pyproject.toml`에 ruff 설정 추가. 기존 프로젝트 ruff 설정과 동일 규칙.

---

## Out of Scope (SP-066에서 하지 않는 것)

- 워크트리 자동 기동 / `/sdd-run` 실행 → SP-067
- 자동 머지 → SP-067
- `active_runs` 테이블 → SP-067 (Phase 1은 읽기 전용)
- 서브에이전트 (designer, implementer) 정의 및 기동 → SP-067~068
- 설계 자동 작성 / 자동 승인 → SP-068
- Slack 알림 / Sentry 연동 → SP-069
- orchestrator 전용 테스트 CI 파이프라인 → 후속
- systemd/supervisord 서비스 등록 → 후속

## 의존성 / 사전 조건

- `claude-agent-sdk` PyPI 패키지 설치 가능 (Claude Code CLI 번들 포함)
- `gh` CLI 인증 완료 (현재 OK) — `_preflight_check()`에서 검증
- Claude Code Max 구독 인증 완료 (SDK가 번들 CLI 인증 사용, 별도 API 키 불필요)

## 파일 변경 목록 (예상 14개)

| 파일 | 변경 |
|------|------|
| `orchestrator/__init__.py` | 신규 |
| `orchestrator/__main__.py` | 신규 |
| `orchestrator/main.py` | 신규 — OrchestratorDaemon |
| `orchestrator/config.py` | 신규 — 상수 + 시스템 프롬프트 |
| `orchestrator/agents.py` | 신규 — Lead Agent 옵션 팩토리 |
| `orchestrator/state.py` | 신규 — StateStore (SQLite) |
| `orchestrator/tools/__init__.py` | 신규 — MCP 서버 팩토리 |
| `orchestrator/tools/backlog.py` | 신규 — scan_backlog 도구 |
| `orchestrator/tools/github.py` | 신규 — check_prs, check_workflows 도구 |
| `orchestrator/tests/__init__.py` | 신규 |
| `orchestrator/tests/test_backlog.py` | 신규 — 파서 단위 테스트 |
| `orchestrator/tests/test_github.py` | 신규 — CLI 래퍼 단위 테스트 |
| `orchestrator/tests/test_state.py` | 신규 — StateStore 단위 테스트 |
| `orchestrator/pyproject.toml` | 신규 — 의존성 + ruff + pytest 설정 |
| `orchestrator/.gitignore` | 신규 — state.db, *.log 제외 |

## 리뷰 반영 이력

| 지적 | 등급 | 수정 |
|------|------|------|
| subprocess.run async 블로킹 | BLOCKER | `asyncio.create_subprocess_exec` 전환 |
| 단위 테스트 DoD 누락 | BLOCKER | `tests/` 디렉토리 + 테스트 3파일 추가 |
| 환경변수/CLI 검증 누락 | BLOCKER | `_preflight_check()` fail-fast 추가 |
| asyncio.sleep 중 종료 지연 | WARNING | `asyncio.Event` + `wait_for` 패턴 전환 |
| signal.signal() 충돌 | WARNING | `loop.add_signal_handler()` 전환 |
| active_runs YAGNI | WARNING | SP-067로 이동, Phase 1은 cycles+decision_log만 |
| 서브에이전트 YAGNI | WARNING | SP-067~068로 이동 |
| permission_mode 과잉 | WARNING | `acceptEdits` → `default` 변경 |
| WAL 모드 미설정 | MINOR | `PRAGMA journal_mode=WAL` 추가 |
| 로깅 프레임워크 누락 | SUGGESTION | logging stdlib 추가 |
| 도구 에러 방어 | SUGGESTION | try/except + 구조화된 에러 dict 반환 |
| backlog 정규식 | SUGGESTION | 섹션 기반 파싱 + 파이프 메타데이터 |
