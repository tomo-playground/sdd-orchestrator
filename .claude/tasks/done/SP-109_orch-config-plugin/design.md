# SP-109: 오케스트레이터 Config Plugin 분리 — 상세 설계

## 난이도: 중 (변경 파일 ~10개, DB/API 변경 없음)

## 상수 분류

| 분류 | 예시 | 현재 | 목표 |
|------|------|------|------|
| **A. 프로젝트 전용** | GH_REPO_OWNER, SENTRY_PROJECTS, 시스템 프롬프트 | config.py 하드코딩 | `ProjectConfig` → sdd.config.yaml |
| **B. 엔진 운영 파라미터** | CYCLE_INTERVAL, MAX_PARALLEL_RUNS | config.py + env | config.py 유지 + YAML override 가능 |
| **C. 시크릿** | SENTRY_AUTH_TOKEN, SLACK_BOT_TOKEN | env only | 변경 없음 |
| **D. 프로토콜 상수** | GH_PR_FIELDS, SLACK_BLOCK_TEXT_MAX | config.py 고정 | 변경 없음 |

### A. 프로젝트 전용 상수 (ProjectConfig로 추출)

| 상수 | 현재 값 |
|------|---------|
| `GH_REPO_OWNER` | `tomo-playground` |
| `GH_REPO_NAME` | `shorts-producer` |
| `GH_ISSUE_ASSIGNEE` | `stopper2008` |
| `SENTRY_ORG` | `tomo-playground` |
| `SENTRY_PROJECTS` | `[shorts-producer-backend, ...]` |
| `BACKLOG_PATH` | `.claude/tasks/backlog.md` |
| `TASKS_CURRENT_DIR` | `.claude/tasks/current` |
| `TASKS_DONE_DIR` | `.claude/tasks/done` |
| `LEAD_AGENT_SYSTEM_PROMPT` | 인라인 (~170행) |
| `DESIGNER_SYSTEM_PROMPT` | 인라인 (~30행) |
| `SLACK_BOT_AGENT_PROMPT` | 인라인 (~30행) |

## 변경 파일 요약

| 파일 | 유형 | 설명 |
|------|------|------|
| `orchestrator/project_config.py` | 신규 | `ProjectConfig` dataclass + `get_project_config()` 로더 |
| `orchestrator/prompts/lead_agent.md` | 신규 | Lead Agent 시스템 프롬프트 외부 파일 |
| `orchestrator/prompts/designer.md` | 신규 | Designer 시스템 프롬프트 외부 파일 |
| `orchestrator/prompts/slack_bot.md` | 신규 | Slack Bot 시스템 프롬프트 외부 파일 |
| `sdd.config.yaml` | 신규 | 프로젝트별 설정 파일 (shorts-producer용) |
| `orchestrator/config.py` | 수정 | 프로젝트 전용 상수 제거, `__getattr__` 호환 레이어 추가 |

---

## DoD 항목별 설계

### 1. ProjectConfig dataclass + get_project_config()

**구현 방법**: `orchestrator/project_config.py` 신규 생성

```python
@dataclass(frozen=True)
class ProjectConfig:
    gh_repo_owner: str
    gh_repo_name: str
    gh_issue_assignee: str
    sentry_org: str
    sentry_projects: list[str]
    tasks_dir: str  # 상대 경로 (.claude/tasks)
    backlog_file: str  # tasks_dir 기준 (backlog.md)

    @property
    def gh_repo_url(self) -> str: ...
    @property
    def repo_full_name(self) -> str: ...
    @property
    def repo_ssh_url(self) -> str: ...

def get_project_config() -> ProjectConfig:
    """sdd.config.yaml 로드 → ProjectConfig 반환. 미존재 시 기본값 fallback."""
```

**동작 정의**:
- before: 모든 프로젝트 전용 값이 config.py에 하드코딩
- after: `sdd.config.yaml` → `ProjectConfig` → 소비자가 `get_project_config()`로 접근

**우선순위**: env > YAML > 코드 기본값

**엣지 케이스**:
- `sdd.config.yaml` 미존재: 기존 하드코딩 값으로 fallback (하위 호환)
- YAML 파싱 오류: 경고 로그 + fallback
- 필드 누락: dataclass 기본값으로 보완

**테스트 전략**:
- YAML 로드 성공 → 값 검증
- YAML 미존재 → fallback 값 검증
- 환경변수 override → env 우선 확인

**Out of Scope**: 다중 프로젝트 동시 관리, 동적 config reload

---

### 2. sdd.config.yaml

**구현 방법**: 프로젝트 루트에 생성

```yaml
# SDD Orchestrator — 프로젝트 설정
project:
  github:
    owner: tomo-playground
    repo: shorts-producer
    assignee: stopper2008
  sentry:
    org: tomo-playground
    projects:
      - shorts-producer-backend
      - shorts-producer-frontend
      - shorts-producer-audio
  tasks:
    dir: .claude/tasks
    backlog: backlog.md
```

**동작 정의**:
- before: 프로젝트 전용 설정이 Python 코드에 하드코딩
- after: YAML 파일 하나로 프로젝트 설정 관리. 새 프로젝트는 이 파일만 수정.

---

### 3. 시스템 프롬프트 외부 파일 분리

**구현 방법**: `orchestrator/prompts/` 디렉토리에 3개 .md 파일 생성

| 파일 | 원본 상수 |
|------|----------|
| `lead_agent.md` | `LEAD_AGENT_SYSTEM_PROMPT` (~170행) |
| `designer.md` | `DESIGNER_SYSTEM_PROMPT` (~30행) |
| `slack_bot.md` | `SLACK_BOT_AGENT_PROMPT` (~30행) |

`project_config.py`에 로드 함수 추가:
```python
def load_prompt(name: str) -> str:
    """orchestrator/prompts/{name}.md 로드. 미존재 시 내장 fallback."""
```

프롬프트 내 프로젝트 전용 값(`tomo-playground`, `shorts-producer` 등)은 `{project.gh_repo_owner}` 템플릿 변수로 치환.

**동작 정의**:
- before: 200행+ 프롬프트가 config.py에 인라인
- after: .md 파일로 분리, 프롬프트 수정 시 Python 코드 변경 불필요

**엣지 케이스**:
- .md 파일 누락: 내장 fallback 문자열 사용 (기존 값)
- 템플릿 변수 치환 실패: 원본 그대로 사용

---

### 4. config.py 호환 레이어

**구현 방법**: config.py에 모듈 레벨 `__getattr__` 추가

```python
def __getattr__(name: str):
    _PROJECT_ATTRS = {"GH_REPO_OWNER", "GH_REPO_NAME", ...}
    if name in _PROJECT_ATTRS:
        cfg = get_project_config()
        return getattr(cfg, _ATTR_MAP[name])
    raise AttributeError(name)
```

**동작 정의**:
- before: `from orchestrator.config import GH_REPO_OWNER` 직접 사용
- after: 동일 import가 동작하지만 내부적으로 ProjectConfig에서 값을 가져옴

**영향 범위**: 기존 코드 변경 없이 동작. 소비자 코드는 점진적 전환.

**Out of Scope**: 소비자 코드 일괄 전환 (호환 레이어로 충분)

---

### 5. 운영 파라미터 YAML override (P1)

**구현 방법**: `sdd.config.yaml`에 선택적 `engine` 섹션

```yaml
engine:
  cycle_interval: 180
  max_parallel_runs: 2
```

config.py에서 YAML 값이 있으면 override, 없으면 기존 기본값 유지.

**Out of Scope**: 런타임 동적 변경, hot reload
