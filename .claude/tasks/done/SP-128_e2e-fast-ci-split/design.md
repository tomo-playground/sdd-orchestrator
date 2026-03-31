Now let me check the orchestrator's rules for auto-merge to understand how CI checks are evaluated:
Now I have a clear picture. Let me look at how the `_aggregate_check_status` function interacts with individual check names to understand if the orchestrator filters by check name:
Now I have everything needed. Let me write the design.


# SP-128: E2E CI 분리 — Fast(dev 서버) + Docker(빌드 검증) 상세 설계

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `.github/workflows/sdd-e2e-fast.yml` | 신규 | dev 서버 대상 Fast E2E (smoke + qa-patrol) |
| `.github/workflows/sdd-e2e.yml` | 수정 | paths 필터 추가 (Docker/인프라 변경 시만 트리거) |
| `sdd-orchestrator/src/sdd_orchestrator/tools/github.py` | 수정 | `_aggregate_check_status`에서 Docker E2E 체크 제외 |
| `sdd-orchestrator/src/sdd_orchestrator/config.py` | 수정 | Docker E2E 스킵 대상 상수 추가 |

---

## DoD 1: `sdd-e2e-fast.yml` 신규 — PR push → dev 서버 대상 Playwright

### 구현 방법

`.github/workflows/sdd-e2e-fast.yml` 파일을 신규 생성한다.

**워크플로우 구조:**

```yaml
name: SDD E2E — Fast

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read

concurrency:
  group: sdd-e2e-fast-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  e2e-fast:
    runs-on: [self-hosted, sdd]
    timeout-minutes: 5

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup PATH
        run: echo "$HOME/.bun/bin" >> "$GITHUB_PATH"

      - name: Wait for dev servers
        run: |
          # dev 서버 health check (이미 돌고 있어야 함)
          for i in $(seq 1 10); do
            if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
              echo "✅ Backend ready"; break
            fi
            [ "$i" -eq 10 ] && { echo "❌ Backend not available"; exit 1; }
            sleep 1
          done
          for i in $(seq 1 10); do
            if curl -sf http://localhost:3000 > /dev/null 2>&1; then
              echo "✅ Frontend ready"; break
            fi
            [ "$i" -eq 10 ] && { echo "❌ Frontend not available"; exit 1; }
            sleep 1
          done

      - name: Run E2E (smoke + qa-patrol)
        working-directory: frontend
        run: |
          npx playwright test e2e/smoke.spec.ts e2e/qa-patrol.spec.ts \
            --config=playwright.e2e.config.ts \
            --reporter=list

      - name: Collect artifacts
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: e2e-fast-results-${{ github.event.pull_request.number }}
          path: |
            frontend/test-results/
            frontend/playwright-report/
          retention-days: 3
          if-no-files-found: ignore
```

**핵심 설계 결정:**

1. **dev 서버 직접 사용**: `playwright.e2e.config.ts`는 `E2E_DOCKER` 미설정 시 `baseURL=http://localhost:3000`을 사용하며, `webServer`로 서버 기동을 시도한다. self-hosted runner에 이미 서버가 돌고 있으므로 `reuseExistingServer: !process.env.CI`가 CI 환경에서는 `false`가 되어 새 서버를 기동하려 한다.
   → **해결**: 환경변수 `PLAYWRIGHT_BASE_URL=http://localhost:3000`과 `E2E_DOCKER=1`을 설정하여 webServer 기동을 비활성화하고, 이미 실행 중인 dev 서버(포트 3000)를 직접 사용한다.

2. **테스트 대상**: `smoke.spec.ts` + `qa-patrol.spec.ts` — 기존 E2E 테스트 파일을 그대로 활용. PR별 동적 테스트(`pr-test.spec.ts`)는 Docker E2E에서만 실행.

3. **permissions 최소화**: `contents: read`만. Docker E2E처럼 PR comment를 남기지 않으므로 `pull-requests: write` 불필요.

4. **timeout**: 5분 (dev 서버 대상이므로 빌드 없이 ~10초 내 완료 예상, 여유 확보).

5. **concurrency**: PR 번호 기반 그룹으로 동일 PR 중복 실행 방지.

### 동작 정의

- PR이 열리거나 push될 때마다 실행
- self-hosted runner의 dev 서버(backend:8000, frontend:3000) health check 후 Playwright 실행
- smoke 테스트(홈/스튜디오/스토리보드) + qa-patrol(Core/Extended/Random/Studio Tabs) 순찰
- 실패 시 GitHub Actions 빨간불 → PR 머지 블로킹
- 아티팩트는 실패 시에만 업로드 (성공 시 불필요)

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| dev 서버 다운 | health check 10초 대기 후 실패 → 워크플로우 실패 (CI 빨간불) |
| Playwright 미설치 | self-hosted runner에 `npx playwright install`이 사전 필요. 워크플로우에서 별도 설치 스텝은 추가하지 않음 (self-hosted 전제) |
| 병렬 PR 실행 | `concurrency` 그룹으로 동일 PR은 최신만. 서로 다른 PR은 같은 dev 서버를 공유하지만 읽기 전용 테스트이므로 충돌 없음 |

---

## DoD 2: `sdd-e2e.yml` 수정 — Dockerfile/docker-compose 변경 시만 트리거

### 구현 방법

`.github/workflows/sdd-e2e.yml`의 `on.pull_request` 트리거에 `paths` 필터를 추가한다.

**변경 전:**
```yaml
on:
  pull_request:
    types: [opened, synchronize]
```

**변경 후:**
```yaml
on:
  pull_request:
    types: [opened, synchronize]
    paths:
      - "Dockerfile*"
      - "docker-compose*.yml"
      - ".dockerignore"
      - "backend/Dockerfile*"
      - "frontend/Dockerfile*"
```

### 동작 정의

- PR 변경 파일에 Docker 관련 파일이 포함된 경우에만 Docker E2E 실행
- 일반 코드 변경(backend/*.py, frontend/*.tsx 등)에는 트리거되지 않음
- `workflow_dispatch`는 추가하지 않음 (수동 실행 필요 시 GitHub UI에서 Re-run)

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| Docker 파일과 코드 동시 변경 | paths 필터에 매칭 → Docker E2E 실행됨 (정상) |
| paths 매칭 없는 PR | Docker E2E 워크플로우 자체가 트리거되지 않음 → `statusCheckRollup`에 나타나지 않음 |

### 영향 범위

기존 Docker E2E의 내부 로직(Claude 기반 테스트 생성, Docker Compose 빌드 등)은 변경하지 않는다. 트리거 조건만 변경.

---

## DoD 3: 오케스트레이터 auto-merge 조건에서 Docker E2E 제외

### 구현 방법

**파일: `sdd-orchestrator/src/sdd_orchestrator/config.py`**

Docker E2E 워크플로우명을 스킵 대상 상수로 추가:

```python
# ── CI Check Filtering ────────────────────────────────────
# Auto-merge 판정 시 무시할 check 이름 (정보성 CI — 실패해도 머지 허용)
CI_OPTIONAL_CHECKS = frozenset({
    "e2e",  # sdd-e2e.yml의 job 이름 (Docker E2E)
})
```

> 참고: GitHub `statusCheckRollup`의 check 이름은 워크플로우의 `jobs.<job_id>` 키(여기서는 `e2e`)가 사용된다. 워크플로우 `name`이 아님에 주의.

**파일: `sdd-orchestrator/src/sdd_orchestrator/tools/github.py`**

`_aggregate_check_status` 함수에서 optional check를 필터링하는 로직을 추가한다:

```python
def _aggregate_check_status(checks: list[dict]) -> str:
    """Aggregate status check rollup into a single status string.

    Checks whose name matches CI_OPTIONAL_CHECKS are excluded —
    they are informational and must not block auto-merge.
    """
    from sdd_orchestrator.config import CI_OPTIONAL_CHECKS

    filtered = [
        c for c in checks
        if c.get("name", "") not in CI_OPTIONAL_CHECKS
    ]
    if not filtered:
        return "none"
    # ... 이하 기존 로직 동일 (statuses 집합 연산)
```

**변경 포인트:**
1. `checks` 리스트에서 `CI_OPTIONAL_CHECKS`에 해당하는 체크를 제거한 `filtered`를 사용
2. 나머지 집계 로직(`statuses`, `FAILURE` 감지 등)은 그대로 유지
3. `filtered`가 비어있으면 `"none"` 반환 (기존과 동일)

### 동작 정의

- Docker E2E가 트리거되어 실패해도 `ci_status`는 `"success"`가 될 수 있음 (다른 필수 체크가 모두 통과한 경우)
- Fast E2E(`e2e-fast` job)는 `CI_OPTIONAL_CHECKS`에 없으므로 실패 시 `ci_status="failure"` → 머지 블로킹
- Docker E2E가 트리거되지 않은 경우 → `statusCheckRollup`에 아예 없음 → 기존과 동일하게 동작

### 엣지 케이스

| 케이스 | 처리 |
|--------|------|
| `statusCheckRollup`에 check `name` 필드가 없는 경우 | `c.get("name", "")` → 빈 문자열 → 필터에 걸리지 않음 (안전) |
| Docker E2E만 실행되고 Fast E2E는 없는 PR | Docker E2E가 필터링되어 `filtered=[]` → `"none"` → `can_auto_merge`에서 `ci_status="none"` → 현재 `summarize_prs`에서 `ci_status in ("success", "none")`이면 `mergeable=True`. `can_auto_merge`에서는 `ci != "success"` → 블로킹. 즉 안전 |
| `CI_OPTIONAL_CHECKS` 확장 필요 시 | `config.py`의 `frozenset`에 추가하면 됨 |

### 주의: `statusCheckRollup` 체크 이름 확인 필요

GitHub API의 `statusCheckRollup`에서 반환하는 각 check 객체의 필드 구조:
- `context` (commit status) 또는 `name` (check run)
- `conclusion`, `status`

현재 `_aggregate_check_status`는 `conclusion`과 `status`만 사용하고 이름은 참조하지 않는다. 필터링을 위해 `name` 또는 `context` 필드를 사용해야 한다.

**구현 시 확인 사항**: `gh pr view --json statusCheckRollup`의 실제 응답에서 check 이름이 `name` 필드인지 `context` 필드인지 확인 후, 필터 키를 결정한다. 두 필드 모두 체크하는 방어적 구현을 권장:

```python
filtered = [
    c for c in checks
    if (c.get("name") or c.get("context", "")) not in CI_OPTIONAL_CHECKS
]
```

---

## DoD 4: Fast E2E 실패 시 머지 블로킹 유지

### 구현 방법

별도 코드 변경 불필요 — DoD 1~3의 구현으로 자동 달성된다.

**블로킹 체인:**
1. `sdd-e2e-fast.yml`의 job 이름(`e2e-fast`)은 `CI_OPTIONAL_CHECKS`에 포함되지 않음
2. Fast E2E 실패 → `statusCheckRollup`에 `FAILURE` 포함
3. `_aggregate_check_status`가 `filtered` 체크에서 `FAILURE` 감지 → `"failure"` 반환
4. `can_auto_merge`에서 `ci != "success"` → `False, "CI not passed"` 반환
5. 머지 거부

### 동작 정의

- Fast E2E 실패 = PR 머지 불가 (오케스트레이터 + GitHub branch protection 양쪽)
- GitHub branch protection에서 `e2e-fast` job을 required check로 설정하면 이중 보호 (이것은 GitHub UI 설정이므로 코드 범위 밖, 운영자가 수동 설정)

### 검증 방법

구현 후 아래 시나리오를 검증:

| 시나리오 | Fast E2E | Docker E2E | 기대 결과 |
|----------|----------|------------|----------|
| 일반 PR (코드만 변경) | ✅ pass | 미실행 | auto-merge 가능 |
| 일반 PR (코드만 변경) | ❌ fail | 미실행 | auto-merge 블로킹 |
| Docker 변경 PR | ✅ pass | ✅ pass | auto-merge 가능 |
| Docker 변경 PR | ✅ pass | ❌ fail | auto-merge 가능 (Docker E2E 제외) |
| Docker 변경 PR | ❌ fail | ✅ pass | auto-merge 블로킹 (Fast E2E 필수) |

---

## 테스트 전략

### 단위 테스트 (오케스트레이터)

**파일**: `sdd-orchestrator/tests/test_github.py` (기존 파일 또는 신규)

```python
# 1. Docker E2E 체크가 필터링되는지 확인
def test_aggregate_check_status_ignores_optional_docker_e2e():
    checks = [
        {"name": "e2e-fast", "conclusion": "SUCCESS"},
        {"name": "e2e", "conclusion": "FAILURE"},  # Docker E2E
    ]
    assert _aggregate_check_status(checks) == "success"

# 2. Fast E2E 실패 시 failure 반환
def test_aggregate_check_status_fast_e2e_failure_blocks():
    checks = [
        {"name": "e2e-fast", "conclusion": "FAILURE"},
        {"name": "e2e", "conclusion": "SUCCESS"},
    ]
    assert _aggregate_check_status(checks) == "failure"

# 3. optional check만 있는 경우 none 반환
def test_aggregate_check_status_only_optional_checks():
    checks = [
        {"name": "e2e", "conclusion": "FAILURE"},
    ]
    assert _aggregate_check_status(checks) == "none"

# 4. 빈 체크 리스트
def test_aggregate_check_status_empty():
    assert _aggregate_check_status([]) == "none"

# 5. context 필드 사용 체크 (commit status 형식)
def test_aggregate_check_status_context_field():
    checks = [
        {"context": "e2e-fast", "status": "SUCCESS"},
        {"context": "e2e", "status": "FAILURE"},
    ]
    assert _aggregate_check_status(checks) == "success"
```

### 통합 테스트 (워크플로우)

수동 검증 — 실제 PR을 열어 워크플로우 트리거 확인:
1. 코드만 변경한 PR → Fast E2E만 실행되는지
2. `Dockerfile` 변경 PR → 양쪽 모두 실행되는지
3. Fast E2E 실패 시 오케스트레이터가 머지 거부하는지

---

## Out of Scope

- GitHub branch protection UI 설정 변경 (코드가 아닌 GitHub 관리자 설정)
- `pr-test.spec.ts` (Claude 동적 생성 테스트) — Docker E2E 전용으로 유지
- `playwright.e2e.config.ts` 수정 — 현재 `E2E_DOCKER` / `PLAYWRIGHT_BASE_URL` 환경변수로 이미 양쪽 환경 지원
- Fast E2E에 Claude Code Action 통합 — 정적 테스트(smoke + qa-patrol)만 실행하므로 불필요
- `sdd-e2e.yml` 내부 로직 변경 — 트리거 조건만 변경