# SP-110: 오케스트레이터 패키지 분리 — 상세 설계

> 전제 조건: SP-109 (config plugin 분리) 완료

## 난이도: 상 (새 리포 생성, 전체 패키지 이관, 28개 파일 import 리네이밍)

## 분석 결과

- 소스 12개 + tools/ 11개, 테스트 16개 (3,779줄), 총 ~10,000줄
- **shorts-producer 코드 커플링: 없음** (import 0건)
- orchestrator는 독립 프로세스 실행 — 코드 수준 결합 없음
- 프로젝트 전용 하드코딩은 SP-109에서 ProjectConfig로 추출 전제

## 변경 파일 요약

| 파일 | 유형 | 설명 |
|------|------|------|
| `sdd-orchestrator/` (새 리포) | 신규 | 독립 패키지 전체 |
| `sdd-orchestrator/pyproject.toml` | 신규 | hatchling, CLI, 의존성 |
| `sdd-orchestrator/src/sdd_orchestrator/` | 이관 | 현 orchestrator/ 소스 (import 리네이밍) |
| `sdd-orchestrator/src/sdd_orchestrator/cli/` | 신규 | `sdd init` 명령어 |
| `sdd-orchestrator/src/sdd_orchestrator/templates/` | 신규 | init 시 복사할 템플릿 |
| `sdd-orchestrator/tests/` | 이관 | 기존 테스트 전체 |
| `shorts-producer/orchestrator/` | 삭제 | 전체 디렉토리 제거 |

---

## DoD 항목별 설계

### P0-1. 별도 Git 리포지토리 생성

```
sdd-orchestrator/
├── src/sdd_orchestrator/
│   ├── __init__.py, main.py, config.py, agents.py
│   ├── state.py, rules.py, utils.py
│   ├── cli/          # sdd init
│   ├── templates/    # init 시 복사할 파일
│   └── tools/        # 11개 파일 이관
├── tests/            # 16개 파일 이관
├── pyproject.toml
└── README.md, LICENSE (MIT)
```

### P0-2. pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sdd-orchestrator"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "claude-agent-sdk>=0.0.20", "httpx>=0.27",
    "slack-bolt>=1.18", "aiohttp>=3.9",
    "python-dotenv>=1.0", "pyyaml>=6.0",
]

[project.scripts]
sdd-orchestrator = "sdd_orchestrator.main:cli_entry"
sdd = "sdd_orchestrator.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/sdd_orchestrator"]
```

### P0-3. shorts-producer에서 orchestrator/ 제거

- `orchestrator/` 전체 삭제
- shorts-producer에서 import 0건 — 영향 없음
- `.claude/skills/` 실행 명령어를 `sdd-orchestrator` CLI로 변경
- `sdd.config.yaml`은 shorts-producer 루트에 유지

### P0-4. `sdd init` CLI

```python
def run_init(*, preset: str = "default", force: bool = False) -> int:
    """sdd.config.yaml + .claude/tasks/ 구조 자동 생성"""
```

- 이미 존재하면 스킵 (`--force`로 덮어쓰기)
- 테스트: tmp_path에서 init → 파일 존재/스킵/force 검증

### P0-5. 기존 테스트 전부 통과

- `from orchestrator.` → `from sdd_orchestrator.` 일괄 치환 (28개 파일)
- `pytest -v` 전체 통과 확인

### P1. README, GitHub Actions 템플릿, agents/skills 템플릿

- README: What / Quick Start / Architecture / Configuration
- `sdd init` 시 `.github/workflows/` 템플릿 생성
- `.claude/agents/`, `.claude/skills/` 범용 골격 템플릿

---

## Import 리네이밍

| Before | After |
|--------|-------|
| `from orchestrator.` | `from sdd_orchestrator.` |
| `import orchestrator.` | `import sdd_orchestrator.` |

## BLOCKER: 없음
