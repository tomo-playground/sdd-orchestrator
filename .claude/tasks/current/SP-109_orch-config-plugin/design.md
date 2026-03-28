Now let me read the remaining files that reference config values:
Now let me check the remaining files that import from config:
Now let me check the existing tests and the rules module:
Now I have a thorough understanding of the codebase. Let me check the existing pyproject.toml for dependencies:
Now I have a complete understanding of the codebase. Let me write the design.md:
The design.md content is ready. Since I can't write to the sensitive path directly, here is the complete design.md content:

# SP-109: 오케스트레이터 Config Plugin 분리 — 상세 설계

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `orchestrator/config.py` | **수정** | ProjectConfig dataclass 추출 + YAML 로드 로직 + 기존 상수를 ProjectConfig 경유로 변경 |
| `orchestrator/prompts/lead_agent.md` | **신규** | Lead Agent 시스템 프롬프트 외부 파일 |
| `orchestrator/prompts/designer.md` | **신규** | Designer Agent 시스템 프롬프트 외부 파일 |
| `orchestrator/prompts/slack_bot.md` | **신규** | Slack Bot Agent 시스템 프롬프트 외부 파일 |
| `sdd.config.yaml` | **신규** | 프로젝트 전용 설정 파일 (shorts-producer용) |
| `orchestrator/pyproject.toml` | **수정** | `pyyaml>=6.0` 의존성 추가 |
| `orchestrator/tests/test_config.py` | **신규** | ProjectConfig + YAML 로드 테스트 |

## BLOCKER

### PyYAML 의존성 추가
- `pyproject.toml`에 `pyyaml>=6.0` 추가 필요
- YAML은 사실상 표준이고 PyYAML은 경량 패키지이므로 리스크 낮음
- 대안: TOML (`tomllib`, 3.11+ stdlib) — 그러나 YAML이 nested config에 더 자연스럽고, `sdd.config.yaml` 네이밍이 spec에 명시되어 있음
- **판단**: PyYAML 추가 진행 (사람 확인 필요)

---

## DoD 상세 설계

### P0-1: 프로젝트 전용 상수를 `ProjectConfig` dataclass로 추출

#### 구현 방법

`orchestrator/config.py` 상단에 `ProjectConfig` dataclass 정의. 현재 하드코딩된 프로젝트 전용 값을 필드로 추출:

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class ProjectConfig:
    """프로젝트별 설정 — sdd.config.yaml 또는 기본값에서 로드."""

    # ── GitHub ──
    gh_repo_owner: str = "tomo-playground"
    gh_repo_name: str = "shorts-producer"
    gh_issue_assignee: str = "stopper2008"

    # ── Sentry ──
    sentry_org: str = "tomo-playground"
    sentry_projects: tuple[str, ...] = (
        "shorts-producer-backend",
        "shorts-producer-frontend",
        "shorts-producer-audio",
    )

    # ── Paths (PROJECT_ROOT 기준 상대 경로) ──
    tasks_base: str = ".claude/tasks"
    backlog_file: str = "backlog.md"

    # ── Git Bot ──
    git_bot_name: str = "orchestrator[bot]"
    git_bot_email: str = "orchestrator[bot]@users.noreply.github.com"

    # ── Operational ──
    cycle_interval: int = 180
    max_parallel_runs: int = 2
    max_agent_turns: int = 15
    agent_query_timeout: int = 600
    design_timeout: int = 600
    max_auto_approve_files: int = 6

    # ── Derived (computed) ──
    @property
    def gh_repo_url(self) -> str:
        return f"https://github.com/{self.gh_repo_owner}/{self.gh_repo_name}"

    @property
    def repo_ssh_url(self) -> str:
        return f"git@github.com:{self.gh_repo_owner}/{self.gh_repo_name}.git"

    @property
    def repo_full_name(self) -> str:
        return f"{self.gh_repo_owner}/{self.gh_repo_name}"
```

> **Note**: `frozen=True`이지만 `@property`는 정상 동작. `tuple`을 사용하여 immutable 보장.

#### 기존 상수 마이그레이션 전략

**핵심 원칙**: 기존 모듈-레벨 상수를 즉시 제거하지 않는다. 대신 `ProjectConfig` 인스턴스에서 파생하여 동일한 이름으로 재할당한다.

```python
# config.py 하단 — 하위 호환 브릿지
_project = load_project_config()  # 아래 P0-2에서 구현

# 기존 상수명 유지 (import하는 모든 모듈이 변경 없이 동작)
GH_REPO_OWNER = _project.gh_repo_owner
GH_REPO_NAME = _project.gh_repo_name
GH_REPO_URL = _project.gh_repo_url
GH_ISSUE_ASSIGNEE = _project.gh_issue_assignee
REPO_SSH_URL = _project.repo_ssh_url
REPO_FULL_NAME = _project.repo_full_name
SENTRY_ORG = _project.sentry_org
SENTRY_PROJECTS = list(_project.sentry_projects)

BACKLOG_PATH = PROJECT_ROOT / _project.tasks_base / _project.backlog_file
TASKS_CURRENT_DIR = PROJECT_ROOT / _project.tasks_base / "current"
TASKS_DONE_DIR = PROJECT_ROOT / _project.tasks_base / "done"

GIT_BOT_NAME = _project.git_bot_name
GIT_BOT_EMAIL = _project.git_bot_email

CYCLE_INTERVAL = _project.cycle_interval
MAX_PARALLEL_RUNS = int(os.environ.get("ORCH_MAX_PARALLEL", str(_project.max_parallel_runs)))
MAX_AGENT_TURNS = _project.max_agent_turns
AGENT_QUERY_TIMEOUT = _project.agent_query_timeout
DESIGN_TIMEOUT = _project.design_timeout
MAX_AUTO_APPROVE_FILES = _project.max_auto_approve_files
```

이 방식으로 **다른 모듈은 일절 변경 불필요**. `from orchestrator.config import GH_REPO_OWNER` 등 기존 import가 그대로 동작한다.

#### 동작 정의
- `ProjectConfig`는 순수 데이터 컨테이너 (no side effects)
- 기본값은 현재 shorts-producer 하드코딩 값과 동일 → 하위 호환 100%
- `_project` 싱글턴을 모듈 로드 시 1회 생성

#### 엣지 케이스
- `frozen=True`이므로 런타임 변경 불가 → 의도적 제약
- `sentry_projects`를 `tuple`로 선언하지만 기존 코드는 `list`로 사용 → 브릿지에서 `list()` 변환
- 환경변수 오버라이드(`ORCH_MAX_PARALLEL` 등)는 브릿지 레벨에서 유지 → YAML 값 < 환경변수 우선순위

---

### P0-2: `sdd.config.yaml` 로드 로직 추가

#### 구현 방법

`config.py`에 `load_project_config()` 함수 추가:

```python
import yaml  # PyYAML

_CONFIG_SEARCH_PATHS = [
    "sdd.config.yaml",
    ".sdd/config.yaml",
]

def load_project_config(project_root: Path | None = None) -> ProjectConfig:
    """YAML 설정 파일을 탐색하여 ProjectConfig 생성.

    탐색 순서: sdd.config.yaml → .sdd/config.yaml → 기본값 fallback.
    """
    root = project_root or PROJECT_ROOT

    for rel_path in _CONFIG_SEARCH_PATHS:
        config_path = root / rel_path
        if config_path.exists():
            return _parse_yaml_config(config_path)

    # 파일 없음 → 기본값 (하위 호환)
    return ProjectConfig()


def _parse_yaml_config(path: Path) -> ProjectConfig:
    """YAML 파일 파싱 → ProjectConfig 생성."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return ProjectConfig()

    kwargs = {}

    # github 섹션
    gh = raw.get("github", {})
    if "repo_owner" in gh:
        kwargs["gh_repo_owner"] = gh["repo_owner"]
    if "repo_name" in gh:
        kwargs["gh_repo_name"] = gh["repo_name"]
    if "issue_assignee" in gh:
        kwargs["gh_issue_assignee"] = gh["issue_assignee"]

    # sentry 섹션
    sentry = raw.get("sentry", {})
    if "org" in sentry:
        kwargs["sentry_org"] = sentry["org"]
    if "projects" in sentry and isinstance(sentry["projects"], list):
        kwargs["sentry_projects"] = tuple(sentry["projects"])

    # paths 섹션
    paths = raw.get("paths", {})
    if "tasks_base" in paths:
        kwargs["tasks_base"] = paths["tasks_base"]
    if "backlog_file" in paths:
        kwargs["backlog_file"] = paths["backlog_file"]

    # git_bot 섹션
    git_bot = raw.get("git_bot", {})
    if "name" in git_bot:
        kwargs["git_bot_name"] = git_bot["name"]
    if "email" in git_bot:
        kwargs["git_bot_email"] = git_bot["email"]

    # daemon 섹션
    daemon = raw.get("daemon", {})
    _int_field(daemon, "cycle_interval", kwargs)
    _int_field(daemon, "max_parallel_runs", kwargs)
    _int_field(daemon, "max_agent_turns", kwargs)
    _int_field(daemon, "agent_query_timeout", kwargs)
    _int_field(daemon, "design_timeout", kwargs)
    _int_field(daemon, "max_auto_approve_files", kwargs)

    return ProjectConfig(**kwargs)


def _int_field(section: dict, key: str, kwargs: dict) -> None:
    """정수 필드를 안전하게 파싱."""
    if key in section:
        try:
            kwargs[key] = int(section[key])
        except (ValueError, TypeError):
            pass  # 잘못된 값은 무시 → 기본값 유지
```

#### sdd.config.yaml 파일 형식 (프로젝트 루트에 생성)

```yaml
# SDD Orchestrator — Project Configuration
# 프로젝트별 설정. 오케스트레이터가 기동 시 자동 로드.

github:
  repo_owner: tomo-playground
  repo_name: shorts-producer
  issue_assignee: stopper2008

sentry:
  org: tomo-playground
  projects:
    - shorts-producer-backend
    - shorts-producer-frontend
    - shorts-producer-audio

paths:
  tasks_base: .claude/tasks
  backlog_file: backlog.md

git_bot:
  name: "orchestrator[bot]"
  email: "orchestrator[bot]@users.noreply.github.com"

daemon:
  cycle_interval: 180
  max_parallel_runs: 2
  max_agent_turns: 15
  agent_query_timeout: 600
  design_timeout: 600
  max_auto_approve_files: 6
```

#### 동작 정의
- `sdd.config.yaml` 탐색: `PROJECT_ROOT/sdd.config.yaml` → `PROJECT_ROOT/.sdd/config.yaml`
- 파일 없으면 `ProjectConfig()` 기본값 (현재 하드코딩과 동일)
- YAML 파싱 실패 시에도 기본값 fallback (에러 로그 출력)
- 부분 설정 지원: 일부 섹션만 작성해도 나머지는 기본값

#### 엣지 케이스
- YAML 파일이 비어있음 (`None` 반환) → `ProjectConfig()` fallback
- YAML 값 타입 오류 (예: `cycle_interval: "abc"`) → 해당 필드만 기본값, 에러 무시
- YAML에 알 수 없는 키 → 무시 (forward compatible)
- `sentry_projects`가 리스트가 아닌 문자열 → `isinstance(v, list)` 체크로 방어 → 기본값 유지

---

### P0-3: config 미존재 시 기존 기본값으로 fallback (하위 호환)

#### 구현 방법

위 P0-2 설계에 이미 포함. `load_project_config()`의 fallback 동작:

```python
# sdd.config.yaml 없는 경우
_project = load_project_config()
# → ProjectConfig() 기본값 = 현재 하드코딩 값과 100% 동일
```

#### 동작 정의
- `sdd.config.yaml` 미존재 → 모든 상수가 현재와 동일한 값
- 기존 테스트 전부 변경 없이 통과해야 함

#### 테스트 전략
- 기존 테스트 실행 → 전부 그린 확인 (regression 없음)
- `sdd.config.yaml` 없는 환경에서 `load_project_config()` 호출 → 기본값 검증

---

### P0-4: Sentry 프로젝트명, GitHub repo, 태스크 경로가 config에서 주입

#### 구현 방법

P0-1의 브릿지 패턴으로 자동 달성. 실제 값의 출처가 `ProjectConfig`로 변경되지만, 모듈-레벨 상수명이 동일하므로 기존 import는 모두 정상 동작.

검증 포인트:
- `SENTRY_PROJECTS` → `sentry.py`에서 사용 → `config._project.sentry_projects`에서 파생
- `GH_REPO_OWNER`, `GH_REPO_NAME` → `config.py` 내부에서 URL 조합 → `_project.gh_repo_owner`
- `BACKLOG_PATH`, `TASKS_CURRENT_DIR`, `TASKS_DONE_DIR` → `_project.tasks_base`에서 파생

#### 동작 정의
- YAML에서 `github.repo_owner: my-org` 설정 시 → `GH_REPO_OWNER == "my-org"`, `GH_REPO_URL`에 반영
- YAML에서 `sentry.projects` 변경 시 → `SENTRY_PROJECTS` 리스트 변경
- YAML에서 `paths.tasks_base: .sdd/tasks` 설정 시 → 모든 태스크 경로 변경

---

### P1-1: LLM 시스템 프롬프트를 외부 파일로 분리

#### 구현 방법

`orchestrator/prompts/` 디렉토리 생성, 3개 마크다운 파일로 분리:

```
orchestrator/
├── prompts/
│   ├── lead_agent.md        # LEAD_AGENT_SYSTEM_PROMPT 내용
│   ├── designer.md          # DESIGNER_SYSTEM_PROMPT 내용
│   └── slack_bot.md         # SLACK_BOT_AGENT_PROMPT 내용
```

> `prompts/`는 Python 패키지가 아닌 데이터 디렉토리. `Path(__file__).parent / "prompts"` 경로로 접근.

`config.py`에 프롬프트 로드 함수 추가:

```python
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

def _load_prompt(name: str, fallback: str, prompts_dir: Path | None = None) -> str:
    """prompts/ 디렉토리에서 .md 파일 로드. 실패 시 fallback 반환."""
    base = prompts_dir or _PROMPTS_DIR
    path = base / f"{name}.md"
    try:
        content = path.read_text(encoding="utf-8").strip()
        return content if content else fallback
    except (FileNotFoundError, UnicodeDecodeError):
        logger.warning("Prompt file not found or unreadable: %s — using inline fallback", path)
        return fallback
```

기존 인라인 프롬프트를 `_FALLBACK_*` 변수로 이동하고, 모듈-레벨 상수는 파일 로드 결과로 대체:

```python
_FALLBACK_LEAD = """..."""  # 현재 LEAD_AGENT_SYSTEM_PROMPT 전체 내용
_FALLBACK_DESIGNER = """..."""  # 현재 DESIGNER_SYSTEM_PROMPT 전체 내용
_FALLBACK_SLACK_BOT = """..."""  # 현재 SLACK_BOT_AGENT_PROMPT 전체 내용

LEAD_AGENT_SYSTEM_PROMPT = _load_prompt("lead_agent", _FALLBACK_LEAD)
DESIGNER_SYSTEM_PROMPT = _load_prompt("designer", _FALLBACK_DESIGNER)
SLACK_BOT_AGENT_PROMPT = _load_prompt("slack_bot", _FALLBACK_SLACK_BOT)
```

#### 동작 정의
- `prompts/lead_agent.md` 존재 → 파일 내용이 `LEAD_AGENT_SYSTEM_PROMPT`
- 파일 누락 → 기존 인라인 문자열(fallback) 사용 + warning 로그
- 프롬프트 수정 시 config.py 변경 불필요 — `.md` 파일만 편집

#### 엣지 케이스
- 빈 파일 → `"".strip()` = `""` → fallback 사용
- 파일 인코딩 오류 → `UnicodeDecodeError` catch → fallback

#### 영향 범위
- `config.py` 내 3개 프롬프트 상수의 출처 변경
- `agents.py`는 변경 없음 (동일 상수명 import)

---

### P1-2: `MAX_PARALLEL_RUNS`, `CYCLE_INTERVAL` 등 운영 파라미터도 config로 이동

#### 구현 방법

P0-1의 `ProjectConfig` dataclass에 이미 포함. 브릿지 상수에서 환경변수 오버라이드 우선순위 유지:

```python
# 우선순위: 환경변수 > YAML > 기본값
CYCLE_INTERVAL = _project.cycle_interval
MAX_PARALLEL_RUNS = int(os.environ.get("ORCH_MAX_PARALLEL", str(_project.max_parallel_runs)))
MAX_AGENT_TURNS = _project.max_agent_turns
AGENT_QUERY_TIMEOUT = _project.agent_query_timeout
DESIGN_TIMEOUT = _project.design_timeout
MAX_AUTO_APPROVE_FILES = _project.max_auto_approve_files
```

#### 동작 정의
- YAML에서 `daemon.cycle_interval: 300` → `CYCLE_INTERVAL == 300`
- 환경변수 `ORCH_MAX_PARALLEL=4` + YAML `max_parallel_runs: 2` → `MAX_PARALLEL_RUNS == 4` (환경변수 우선)
- YAML 없음 + 환경변수 없음 → 기존 기본값

---

## config.py 최종 구조 (리팩터링 후)

```
# 1. imports + dotenv
# 2. PROJECT_ROOT (YAML 로드 전 필요)
# 3. ProjectConfig dataclass
# 4. YAML loader (load_project_config, _parse_yaml_config, _int_field)
# 5. _project = load_project_config()  ← 싱글턴
# 6. 하위 호환 브릿지 상수 (GH_REPO_OWNER, SENTRY_PROJECTS, ...)
# 7. Prompt loader + fallback strings + 프롬프트 상수
# 8. 기존 상수 (변경 없음: DB_PATH, feature flags, timeouts, ...)
```

**변경하지 않는 상수** (프로젝트 전용이 아닌 범용/인프라 상수):
- `DEFAULT_DB_PATH` (로컬 경로)
- `LEAD_AGENT_MODEL`, `DESIGNER_MODEL` (모델 선택)
- `ENABLE_AUTO_DESIGN`, `ENABLE_AUTO_RUN` (feature flag — 환경변수 전용)
- `SENTRY_AUTH_TOKEN`, `SLACK_BOT_TOKEN` 등 (시크릿 — `.env` 전용)
- `SENTRY_TIMEOUT_*`, `SLACK_TIMEOUT_*`, `GH_TIMEOUT` 등 (인프라 튜닝)
- `GH_PR_FIELDS`, `GH_RUN_FIELDS` (API 스키마)
- `GH_MONITORED_WORKFLOWS` (보안 허용 목록)

---

## 테스트 전략

### `orchestrator/tests/test_config.py` (신규)

| # | 테스트 | 검증 내용 |
|---|--------|-----------|
| 1 | `test_project_config_defaults` | 기본값이 현재 하드코딩 값과 동일 |
| 2 | `test_project_config_derived` | `gh_repo_url`, `repo_ssh_url`, `repo_full_name` 파생 |
| 3 | `test_load_yaml_config` | 정상 YAML → 필드 오버라이드 + 미지정 필드 기본값 유지 |
| 4 | `test_load_config_no_file` | YAML 미존재 → 전체 기본값 |
| 5 | `test_load_config_empty_yaml` | 빈 YAML → 전체 기본값 |
| 6 | `test_load_config_invalid_type` | 타입 오류 → 해당 필드만 기본값 |
| 7 | `test_load_config_sentry_projects_string` | `projects`가 문자열 → 기본값 유지 |
| 8 | `test_load_prompt_from_file` | 프롬프트 파일 로드 정상 |
| 9 | `test_load_prompt_fallback` | 파일 누락 → fallback 반환 |
| 10 | `test_load_config_sdd_subdir` | `.sdd/config.yaml` 경로 탐색 |
| 11 | `test_load_prompt_empty_file` | 빈 프롬프트 파일 → fallback |
| 12 | `test_search_path_priority` | `sdd.config.yaml`이 `.sdd/config.yaml`보다 우선 |

### 기존 테스트 Regression
- `pytest orchestrator/tests/` 전체 실행 → 전부 그린 확인
- 특히 `test_sentry.py`, `test_github.py`, `test_worktree.py`, `test_rules.py`

---

## Out of Scope

- **다른 모듈의 import 변경**: 브릿지 패턴으로 기존 import 100% 유지
- **환경변수 오버라이드 확장**: 기존 환경변수만 유지, 새 환경변수 추가 안 함
- **시크릿/토큰의 YAML 이동**: `.env` 유지 (보안상 YAML에 넣지 않음)
- **인프라 튜닝 상수의 YAML 이동**: `SENTRY_TIMEOUT_*`, `SLACK_TIMEOUT_*` 등은 범용 상수
- **`GH_MONITORED_WORKFLOWS`의 YAML 이동**: 보안 허용 목록이므로 코드 유지
- **범용 패키지 분리**: 이 태스크는 분리의 전제 조건만 수행