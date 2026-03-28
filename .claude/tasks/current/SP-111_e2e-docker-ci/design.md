# SP-111: Docker E2E 자동화 파이프라인 — 상세 설계

## 설계 결정

| 항목 | 결정 | 근거 |
|------|------|------|
| Playwright 위치 | Docker 컨테이너 안 | 호스트 무의존, 범용 분리 대비 |
| 외부 API (Gemini 등) | 미포함 (mock 불필요, 단순 미설정) | UI CUD 테스트만, AI 플로우 제외 |
| 시드 데이터 | SQL 파일 | 빠르고 이식 가능 |
| 워크플로우 트리거 | PR opened/synchronize | sdd-review와 동일 |

## 변경 파일 요약

| 파일 | 유형 | 설명 |
|------|------|------|
| `docker-compose.e2e.yml` | 신규 | E2E 전용 환경 (DB + MinIO + Backend + Frontend + Playwright) |
| `backend/Dockerfile.e2e` | 신규 | Backend 컨테이너 (Python 3.13 + uv + FastAPI) |
| `frontend/Dockerfile.e2e` | 신규 | Frontend 컨테이너 (Node + Next.js build + serve) |
| `scripts/e2e-seed.sql` | 신규 | 테스트 전제조건 시드 데이터 |
| `scripts/run-e2e.sh` | 신규 | E2E 실행 래퍼 (compose up → test → down) |
| `.github/workflows/sdd-e2e.yml` | 신규 | PR E2E 워크플로우 |

기존 코드 변경 없음.

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
    volumes:
      - ./scripts/e2e-seed.sql:/docker-entrypoint-initdb.d/02-seed.sql
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
      test: mc ready local
      interval: 3s
      retries: 5

  e2e-backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.e2e
    depends_on:
      e2e-db: { condition: service_healthy }
      e2e-minio: { condition: service_healthy }
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
      test: python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')"
      interval: 5s
      retries: 15
      start_period: 15s

  e2e-frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.e2e
      args:
        NEXT_PUBLIC_API_URL: http://e2e-backend:8000/api/v1
    depends_on:
      e2e-backend: { condition: service_healthy }
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
    entrypoint: >
      bash -c "
        npm ci --ignore-scripts &&
        npx playwright test e2e/
          --config=playwright.e2e.config.ts
          --reporter=json
          --output=/results/artifacts
          > /results/results.json 2>&1;
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
- Backend 기동 실패 (의존성 누락): healthcheck로 감지, e2e-runner 기동 안 됨
- Frontend 빌드 실패: 같은 메커니즘
- Playwright timeout: `--timeout` 플래그로 제어

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
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy app
COPY . .

# Run migrations + start server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn main:app --host 0.0.0.0 --port 8000"]
```

**동작 정의**:
- before: Backend Dockerfile 없음
- after: 컨테이너 기동 시 마이그레이션 자동 실행 → API 서버 시작

**엣지 케이스**:
- 마이그레이션 실패: CMD에서 `&&`로 연결, 실패 시 컨테이너 비정상 종료 → healthcheck 실패
- 무거운 의존성 (mediapipe, opencv, rembg): E2E에서 이미지 생성 안 하므로 import error가 발생해도 API 라우팅에는 영향 없음 (lazy import 패턴). 빌드 시간 단축이 필요하면 추후 `--no-install` 옵션으로 제외.

**Out of Scope**: 프로덕션 Dockerfile, 멀티스테이지 빌드 최적화

---

### 3. Frontend Dockerfile.e2e

**구현 방법**: `frontend/Dockerfile.e2e`

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

CMD ["npm", "start"]
```

**동작 정의**:
- before: Frontend Dockerfile 없음
- after: Next.js 프로덕션 빌드 + 서빙. `NEXT_PUBLIC_API_URL`은 빌드 타임에 주입.

**엣지 케이스**:
- `NEXT_PUBLIC_*`는 빌드 타임 변수. Docker Compose에서 `args`로 전달해야 함 (environment 아님).

**Out of Scope**: standalone output 최적화, 이미지 크기 최적화

---

### 4. 시드 데이터 (scripts/e2e-seed.sql)

**구현 방법**: Alembic 마이그레이션이 스키마를 생성한 후, PostgreSQL initdb가 시드 삽입.

단, `docker-entrypoint-initdb.d/`는 DB 초기화 시에만 실행되므로, **마이그레이션은 Backend CMD에서, 시드는 Backend 기동 후 별도 실행**하는 구조가 필요.

수정: `e2e-backend` CMD를 `alembic upgrade head && python scripts/e2e_seed.py && uvicorn ...` 으로 변경. 시드를 Python 스크립트로 작성하여 ORM 활용.

**시드 데이터 (scripts/e2e_seed.py)**:
- `Project` 1개 (name: "E2E Test Channel")
- `Group` 1개 (name: "E2E Test Series")
- `Character` 2개 (speaker A/B)
- `StyleProfile` 2개
- `VoicePreset` 2개
- `Storyboard` 1개 (title: "E2E Test Storyboard", scenes 3개)
- `LoRA` 1개
- `MediaAsset` 필요한 만큼 (참조 이미지 등은 placeholder)

**엣지 케이스**:
- 중복 실행: `INSERT ... ON CONFLICT DO NOTHING` 또는 스크립트 시작 시 기존 데이터 확인
- FK 순서: Project → Group → Character/Style → Storyboard → Scene 순서 준수

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
  contents: write
  pull-requests: write
  issues: write
  id-token: write
  actions: read

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
            3. baseURL은 환경변수 `BASE_URL` 또는 `http://e2e-frontend:3000` 사용
            4. 테스트는 읽기 + CUD 동작만. 외부 AI API 호출은 하지 않음.
            5. 파일 생성만 하고 실행하지 마세요.

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

            $([ "$FAILED" -gt 0 ] && echo '스크린샷/트레이스: `e2e-results/artifacts/`' || echo '모든 테스트 통과')

            *Auto-generated by sdd-e2e*"
          fi
```

**동작 정의**:
- PR에 `## Test plan` 없으면 스킵
- Claude가 test plan → Playwright 코드 생성
- Docker Compose로 전체 환경 기동 + 테스트 실행
- 결과를 PR 코멘트로 보고

**엣지 케이스**:
- Test plan 없는 PR: 스킵 (코멘트 없음)
- Docker 빌드 실패: run-e2e.sh가 비정상 종료 → GitHub Actions failure
- 테스트 전체 실패: results.json 파싱 실패 시 fallback 메시지

**sdd-fix 연동**: 실패 시 sdd-fix가 `synchronize` 이벤트로 자동 트리거되어 수정 → 재실행 루프 형성

**Out of Scope**: 수동 재실행 UI, 테스트 선택 실행, 병렬 PR 동시 실행 격리

---

### 7. Playwright baseURL 설정

**구현 방법**: `playwright.e2e.config.ts`에서 환경변수 우선 사용하도록 수정.

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
  ├─ sdd-review.yml (코드 리뷰)
  │
  └─ sdd-e2e.yml
       ├─ test plan 감지
       ├─ Claude → Playwright 코드 생성
       ├─ docker compose up (DB + MinIO + Backend + Frontend + Playwright)
       │   ├─ e2e-db: PostgreSQL 기동
       │   ├─ e2e-minio: MinIO 기동
       │   ├─ e2e-backend: migration + seed + API 서버
       │   ├─ e2e-frontend: Next.js build + serve
       │   └─ e2e-runner: Playwright 실행
       ├─ 결과 PR 코멘트
       └─ docker compose down -v
            │
            └─ 실패 시 → sdd-fix 트리거 → push → sdd-e2e 재실행
```
