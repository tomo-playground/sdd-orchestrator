# SP-111: Docker E2E 자동화 파이프라인 — 상세 설계

## 설계 결정

| 항목 | 결정 | 근거 |
|------|------|------|
| Playwright 위치 | Docker 컨테이너 안 | 호스트 무의존, 범용 분리 대비 |
| 외부 API (Gemini 등) | 미포함 (mock 불필요, 단순 미설정) | UI CUD 테스트만, AI 플로우 제외 |
| 시드 데이터 | Python 스크립트 (ORM 활용) | Alembic 마이그레이션 후 실행, FK 순서 보장 |
| 워크플로우 트리거 | PR opened/synchronize | sdd-review와 동일 |
| Frontend API 라우팅 | `BACKEND_ORIGIN` 런타임 환경변수 (Next.js rewrites 프록시) | 기존 코드 구조 그대로 활용 |

## 변경 파일 요약

| 파일 | 유형 | 설명 |
|------|------|------|
| `docker-compose.e2e.yml` | 신규 | E2E 전용 환경 (DB + MinIO + Backend + Frontend + Playwright) |
| `backend/Dockerfile.e2e` | 신규 | Backend 컨테이너 (Python 3.13 + uv + FastAPI) |
| `frontend/Dockerfile.e2e` | 신규 | Frontend 컨테이너 (Node + Next.js build + serve) |
| `backend/scripts/e2e_seed.py` | 신규 | 테스트 전제조건 시드 데이터 (ORM) |
| `scripts/run-e2e.sh` | 신규 | E2E 실행 래퍼 (compose up → test → down) |
| `.github/workflows/sdd-e2e.yml` | 신규 | PR E2E 워크플로우 |
| `frontend/playwright.e2e.config.ts` | 수정 | baseURL 환경변수 대응 (1행) |

---

## DoD 항목별 설계

### 1. docker-compose.e2e.yml

**구현 방법**: 프로젝트 루트에 생성. 모든 서비스가 같은 Docker 네트워크(`e2e-net`)에 속함.

```yaml
services:
  e2e-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: shorts_e2e
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    healthcheck:
      test: pg_isready -U test -d shorts_e2e
      interval: 3s
      retries: 10

  e2e-minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: password123
    healthcheck:
      test: curl -f http://localhost:9000/minio/health/live
      interval: 3s
      retries: 5

  e2e-minio-init:
    image: minio/mc:latest
    depends_on:
      e2e-minio: { condition: service_healthy }
    entrypoint: >
      sh -c "
        mc alias set e2e http://e2e-minio:9000 admin password123 &&
        mc mb --ignore-existing e2e/shorts-e2e
      "

  e2e-backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.e2e
    depends_on:
      e2e-db: { condition: service_healthy }
      e2e-minio-init: { condition: service_completed_successfully }
    environment:
      DATABASE_URL: postgresql://test:test@e2e-db:5432/shorts_e2e
      APP_ENV: test
      STORAGE_MODE: s3
      MINIO_ENDPOINT: http://e2e-minio:9000
      MINIO_ACCESS_KEY: admin
      MINIO_SECRET_KEY: password123
      MINIO_BUCKET: shorts-e2e
      CORS_ORIGINS: http://e2e-frontend:3000
      COMFYUI_BASE_URL: ""
      AUDIO_SERVER_URL: ""
    healthcheck:
      test: python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/projects')"
      interval: 5s
      retries: 15
      start_period: 15s

  e2e-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.e2e
    depends_on:
      e2e-backend: { condition: service_healthy }
    environment:
      BACKEND_ORIGIN: http://e2e-backend:8000
    healthcheck:
      test: node -e "fetch('http://localhost:3000').then(r => process.exit(r.ok ? 0 : 1))"
      interval: 5s
      retries: 15
      start_period: 30s

  e2e-runner:
    image: mcr.microsoft.com/playwright:v1.58.0-noble
    depends_on:
      e2e-frontend: { condition: service_healthy }
    working_dir: /work
    volumes:
      - ./frontend:/work
      - ./e2e-results:/results
    environment:
      BASE_URL: http://e2e-frontend:3000
      CI: "true"
      PLAYWRIGHT_JSON_OUTPUT_NAME: /results/results.json
    entrypoint: >
      bash -c "
        npm ci --ignore-scripts &&
        npx playwright test e2e/
          --config=playwright.e2e.config.ts
          --reporter=json
          --output=/results/artifacts
          2>/results/stderr.log;
        exit $?
      "

networks:
  default:
    name: e2e-net
```

**동작 정의**:
- before: E2E 전용 Docker 환경 없음
- after: `docker compose -f docker-compose.e2e.yml up --abort-on-container-exit e2e-runner` 로 전체 환경 기동 + 테스트 실행 + 종료

**엣지 케이스**:
- Backend 기동 실패: healthcheck 실패 → e2e-runner 기동 안 됨
- Frontend 빌드 실패: 같은 메커니즘
- MinIO 버킷 미존재: `e2e-minio-init` 컨테이너가 자동 생성 후 종료

**테스트 전략**: `scripts/run-e2e.sh` 를 로컬에서 실행하여 전체 사이클 검증

**Out of Scope**: GPU 서비스 (ComfyUI, Audio), LangFuse, Sentry

---

### 2. Backend Dockerfile.e2e

**구현 방법**: `backend/Dockerfile.e2e`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# System deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies (dev 포함 — lazy import 아닌 패키지 존재 가능)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copy app
COPY . .

# Run migrations + seed + start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run python scripts/e2e_seed.py && uv run uvicorn main:app --host 0.0.0.0 --port 8000"]
```

**동작 정의**:
- before: Backend Dockerfile 없음
- after: 컨테이너 기동 시 마이그레이션 → 시드 → API 서버 시작

**엣지 케이스**:
- 마이그레이션 실패: `&&`로 연결, 실패 시 컨테이너 비정상 종료 → healthcheck 실패
- dev 의존성: `--no-dev` 대신 전체 설치. 빌드 시간보다 기동 안정성 우선. 추후 최적화.

**Out of Scope**: 프로덕션 Dockerfile, 멀티스테이지 빌드 최적화

---

### 3. Frontend Dockerfile.e2e

**구현 방법**: `frontend/Dockerfile.e2e`

Frontend는 `BACKEND_ORIGIN` 런타임 환경변수를 사용하여 Next.js rewrites로 API 프록시. `NEXT_PUBLIC_API_URL`은 코드베이스에 존재하지 않으므로 사용하지 않음.

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

CMD ["npm", "start"]
```

**동작 정의**:
- before: Frontend Dockerfile 없음
- after: Next.js 프로덕션 빌드 + 서빙. `BACKEND_ORIGIN`은 런타임 환경변수로 docker-compose.e2e.yml에서 주입.

**엣지 케이스**:
- `BACKEND_ORIGIN` 미설정 시: `next.config.ts`에서 fallback `http://127.0.0.1:8000` 사용 → Docker 내부에서 실패. compose에서 반드시 설정.

**Out of Scope**: standalone output 최적화, 이미지 크기 최적화

---

### 4. 시드 데이터 (backend/scripts/e2e_seed.py)

**구현 방법**: Backend CMD에서 `alembic upgrade head` 후 실행. ORM을 활용하여 FK 순서 보장.

**시드 엔티티**:
- `Project` 1개 (name: "E2E Test Channel")
- `Group` 1개 (name: "E2E Test Series")
- `Character` 2개 (speaker A/B, 최소 필수 필드만)
- `StyleProfile` 2개
- `VoicePreset` 2개
- `Storyboard` 1개 (title: "E2E Test Storyboard", scenes 3개)
- `LoRA` 1개

**중복 방지**: 스크립트 시작 시 `Project` 존재 여부 확인. 이미 있으면 스킵.

**엣지 케이스**:
- FK 순서: Project → Group → Character/Style → Storyboard → Scene
- MediaAsset 참조: 이미지 URL은 placeholder (MinIO에 실제 파일 불필요, DB 레코드만)

**Out of Scope**: 대량 데이터, 성능 테스트용 시드

---

### 5. 실행 래퍼 (scripts/run-e2e.sh)

**구현 방법**: 프로젝트 루트 `scripts/run-e2e.sh`

```bash
#!/bin/bash
set -euo pipefail

COMPOSE_FILE="docker-compose.e2e.yml"
RESULTS_DIR="./e2e-results"

mkdir -p "$RESULTS_DIR"

# 이전 실행 정리
docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

# 환경 기동 + 테스트 실행 + 결과 수집
docker compose -f "$COMPOSE_FILE" up \
  --build \
  --abort-on-container-exit \
  --exit-code-from e2e-runner

EXIT_CODE=$?

# 정리
docker compose -f "$COMPOSE_FILE" down -v

exit $EXIT_CODE
```

**동작 정의**:
- `./scripts/run-e2e.sh` 한 줄로 전체 사이클 완료
- 종료 코드가 e2e-runner의 종료 코드를 따름
- Volume 포함 정리 (`-v`)로 DB 데이터 잔류 방지

---

### 6. GitHub Actions 워크플로우 (sdd-e2e.yml)

**구현 방법**: `.github/workflows/sdd-e2e.yml`

```yaml
name: SDD E2E — Test Plan 자동 검증

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  contents: read
  pull-requests: write
  issues: write
  id-token: write
  actions: write

concurrency:
  group: sdd-e2e-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  e2e-test:
    runs-on: [self-hosted, sdd]
    timeout-minutes: 30

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.ref }}

      - name: Check test plan exists
        id: check
        run: |
          BODY=$(gh pr view ${{ github.event.pull_request.number }} --json body --jq '.body')
          if echo "$BODY" | grep -q "## Test plan"; then
            echo "has_test_plan=true" >> "$GITHUB_OUTPUT"
          else
            echo "has_test_plan=false" >> "$GITHUB_OUTPUT"
          fi
        env:
          GH_TOKEN: ${{ github.token }}

      - name: Skip if no test plan
        if: steps.check.outputs.has_test_plan != 'true'
        run: echo "No test plan found, skipping E2E"

      - name: Setup PATH
        if: steps.check.outputs.has_test_plan == 'true'
        run: echo "$HOME/.bun/bin" >> "$GITHUB_PATH"

      - name: Generate E2E tests from test plan
        if: steps.check.outputs.has_test_plan == 'true'
        uses: anthropics/claude-code-action@v1
        with:
          claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          prompt: |
            PR #${{ github.event.pull_request.number }} 의 Test Plan을 읽고
            Playwright E2E 테스트를 `frontend/e2e/pr-test.spec.ts`에 생성하세요.

            1. `gh pr view ${{ github.event.pull_request.number }} --json body --jq '.body'` 로 test plan 읽기
            2. 각 체크리스트 항목을 Playwright test()로 변환
            3. baseURL은 환경변수 `BASE_URL` 사용 (Docker 내부: http://e2e-frontend:3000)
            4. 셀렉터는 `getByRole`, `getByText`, `data-testid`만 사용. CSS 셀렉터 금지.
            5. 테스트는 읽기 + CUD 동작만. 외부 AI API 호출은 하지 않음.
            6. 파일 생성만 하고 실행하지 마세요.

          claude_args: |
            --allowedTools "Bash(gh:*),Read,Edit,Write,Glob,Grep"

      - name: Run E2E
        if: steps.check.outputs.has_test_plan == 'true'
        run: bash scripts/run-e2e.sh

      - name: Report results
        if: always() && steps.check.outputs.has_test_plan == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          if [ -f e2e-results/results.json ]; then
            PASSED=$(jq '[.. | objects | select(has("ok")) | select(.ok == true)] | length' e2e-results/results.json 2>/dev/null || echo 0)
            FAILED=$(jq '[.. | objects | select(has("ok")) | select(.ok == false)] | length' e2e-results/results.json 2>/dev/null || echo 0)
            gh pr comment ${{ github.event.pull_request.number }} --body "## E2E Test Results
          | 통과 | 실패 |
          |------|------|
          | ${PASSED} | ${FAILED} |

          $([ "$FAILED" -gt 0 ] && echo '스크린샷/트레이스: \`e2e-results/artifacts/\`' || echo '모든 테스트 통과')

          *Auto-generated by sdd-e2e*"
          fi

      - name: Trigger sdd-fix on failure
        if: failure() && steps.check.outputs.has_test_plan == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh workflow run sdd-fix.yml \
            -f pr_number=${{ github.event.pull_request.number }}
```

**동작 정의**:
- PR에 `## Test plan` 없으면 스킵
- Claude가 test plan → Playwright 코드 생성 (안정적 로케이터만 사용)
- Docker Compose로 전체 환경 기동 + 테스트 실행
- 결과를 PR 코멘트로 보고
- 실패 시 `sdd-fix.yml` workflow_dispatch로 자동 수정 트리거

**엣지 케이스**:
- Test plan 없는 PR: 스킵
- Docker 빌드 실패: run-e2e.sh 비정상 종료 → failure → sdd-fix 트리거
- sdd-fix 무한 루프: sdd-fix.yml 자체에 3회 제한이 있음

**Out of Scope**: 수동 재실행 UI, 테스트 선택 실행, 병렬 PR 동시 실행 격리

---

### 7. Playwright baseURL 설정

**구현 방법**: `playwright.e2e.config.ts`에서 환경변수 우선 사용.

```typescript
// 기존
baseURL: "http://localhost:3000"
// 변경
baseURL: process.env.BASE_URL || "http://localhost:3000"
```

**영향 범위**: 기존 로컬 E2E 동작에 영향 없음 (BASE_URL 미설정 시 localhost 유지)

---

## 실행 흐름 요약

```
PR opened
  │
  ├─ sdd-review.yml (코드 리뷰, 병렬)
  │
  └─ sdd-e2e.yml (E2E 테스트, 병렬)
       ├─ test plan 감지
       ├─ Claude → Playwright 코드 생성
       ├─ docker compose up
       │   ├─ e2e-db: PostgreSQL
       │   ├─ e2e-minio: MinIO + 버킷 자동 생성
       │   ├─ e2e-backend: migration + seed + API 서버
       │   ├─ e2e-frontend: Next.js build + serve (BACKEND_ORIGIN 프록시)
       │   └─ e2e-runner: Playwright 실행
       ├─ 결과 PR 코멘트
       ├─ docker compose down -v
       │
       └─ 실패 시 → sdd-fix workflow_dispatch → 코드 수정 → push → sdd-e2e 재실행

---

## 설계 리뷰 결과 (난이도: 중 — Gemini 2라운드 + 에이전트 1라운드)

### Gemini 자문 (2라운드)
- R1: NEXT_PUBLIC_API_URL 문제 지적 → 기존 rewrites 프록시 구조 활용으로 해결
- R2: Playwright 실행 위치 논의 → A안(Docker 안) 확정, 범용 분리 목표에 부합

### 에이전트 설계 리뷰 결과

#### Round 1
| 리뷰어 | 판정 | 주요 피드백 | 반영 |
|--------|------|------------|------|
| Tech Lead | BLOCKER | `NEXT_PUBLIC_API_URL` 미존재 → `BACKEND_ORIGIN` 사용 | ✅ Dockerfile ARG 제거, compose environment로 변경 |
| Tech Lead | BLOCKER | MinIO healthcheck `mc ready local` 불가 | ✅ `curl -f .../minio/health/live`로 교체 |
| Tech Lead | BLOCKER | MinIO 버킷 자동 생성 누락 | ✅ `e2e-minio-init` 컨테이너 추가 |
| Tech Lead | WARNING | `--no-dev` 빌드 시 import 오류 가능 | ✅ dev 포함 전체 설치로 변경 |
| Tech Lead | WARNING | sdd-fix 자동 트리거 경로 미구현 | ✅ `gh workflow run sdd-fix.yml` 스텝 추가 |
| Tech Lead | WARNING | JSON reporter stdout+stderr 혼합 | ✅ `PLAYWRIGHT_JSON_OUTPUT_NAME` 환경변수 + stderr 분리 |
| Tech Lead | WARNING | `contents: write` 권한 불필요 | ✅ `contents: read`로 축소, `actions: write` 추가 (workflow_dispatch용) |
| Tech Lead | WARNING | `/docs` healthcheck 비활성화 | ✅ `/api/v1/projects`로 변경 |
| Tech Lead | WARNING | SQL 마운트 + Python seed 이중 존재 | ✅ SQL 마운트 제거, Python seed만 사용 |
```
