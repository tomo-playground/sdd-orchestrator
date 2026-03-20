# Deployment Guide

Shorts Producer 시스템을 프로덕션 환경에 배포하고 운영하기 위한 전체 프로세스 안내입니다.

## 1. 전체 배포 아키텍처

```mermaid
graph TD
    subgraph Infrastructure
        Proxy[Nginx / Reverse Proxy]
        Frontend["Frontend: Next.js 16"]
        Backend["Backend: FastAPI (Python 3.13+)"]
        DB[(PostgreSQL)]
        S3[(MinIO / S3)]
    end

    subgraph Observability_Optional ["Observability (선택)"]
        LangFuse["LangFuse v3"]
    end

    subgraph External_AI
        Gemini["Google Gemini 2.5 Flash"]
    end

    subgraph Local_AI_Services
        SD[SD WebUI API]
        TTS["Qwen3-TTS Engine"]
        WD14["WD14 ONNX Tagger"]
        Ollama["Ollama (선택)"]
    end

    Proxy --> Frontend
    Proxy --> Backend
    Backend --> DB
    Backend --> S3
    Backend --> Gemini
    Backend --> SD
    Backend --> TTS
    Backend --> WD14
    Backend -.-> LangFuse
    Backend -.-> Ollama
```

## 2. 필수 서비스 구축 (Setup Guides)

본 시스템은 다수의 AI 모듈과 인프라를 연동합니다. 각 모듈의 상세 구축 방법은 아래 가이드를 참조하세요.

1.  **인프라 구축**: [Storage & DB Setup](STORAGE_SETUP.md) (PostgreSQL, MinIO)
2.  **이미지 생성 서버**: [SD WebUI Setup](SD_WEBUI_SETUP.md) (Stable Diffusion, ControlNet)
3.  **음성 생성 엔진**: [TTS Setup](TTS_SETUP.md) (Qwen3-TTS)
4.  **이미지 검증 모델**: [WD14 Setup](WD14_SETUP.md) (ONNX Tagger)

## 3. 백엔드 배포 단계

### 3.1 환경 변수 설정
`backend/.env` 파일을 작성합니다. [STORAGE_POLICY.md](STORAGE_POLICY.md)를 참조하여 저장소 모드를 결정하세요.

**필수 환경 변수**:
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/shorts_producer
GEMINI_API_KEY=your-gemini-api-key
```

**스토리지 (MinIO/S3)**:
```bash
STORAGE_MODE=s3           # 's3' 또는 'local'
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=xxx
MINIO_SECRET_KEY=xxx
MINIO_BUCKET=shorts-producer
```

**AI 서비스**:
```bash
SD_BASE_URL=http://127.0.0.1:7860
TTS_MODEL_NAME=Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign
TTS_DEVICE=auto           # auto | mps | cpu
```

**선택 항목**:
```bash
LANGFUSE_ENABLED=false    # LangFuse Observability
YOUTUBE_CLIENT_ID=        # YouTube 업로드 (OAuth 2.0)
YOUTUBE_CLIENT_SECRET=
OLLAMA_BASE_URL=http://localhost:11434
```

> 전체 설정 항목은 `backend/config.py` + `backend/config_pipelines.py` 참조.

### 3.2 의존성 설치 및 실행
```bash
cd backend

# uv를 사용한 의존성 설치 (권장)
uv sync

# DB 마이그레이션
uv run alembic upgrade head

# 서버 실행 (개발)
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 서버 실행 (Production)
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

> **참고**: 프로젝트는 `uv` + `pyproject.toml` 기반입니다. `requirements.txt`는 사용하지 않습니다. Python 3.13+ 필요.

## 4. 프론트엔드 배포 단계

```bash
cd frontend
npm install
npm run build
npm run start
```

**환경 변수** (`frontend/.env.local`, 선택):
```bash
BACKEND_ORIGIN=http://127.0.0.1:8000  # 기본값, 변경 시에만 설정
```

> Next.js 16 + React 19 + Tailwind CSS 4 사용. Vitest (단위 테스트), Playwright (VRT/E2E) 지원.

## 5. LangFuse Observability (선택)

LangGraph Agentic Pipeline의 트레이스를 수집/분석하는 셀프호스팅 옵저빌리티 스택입니다.

```bash
# 시작 (6개 서비스: PostgreSQL + ClickHouse + Redis + MinIO + Web + Worker)
docker compose -f docker-compose.langfuse.yml up -d

# Web UI 접속 → 회원가입 → API 키 발급
open http://localhost:3001
```

**환경 변수** (`backend/.env`):
```
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-xxx
LANGFUSE_SECRET_KEY=sk-lf-xxx
LANGFUSE_BASE_URL=http://localhost:3001
```

**비활성화**: `LANGFUSE_ENABLED=false` (기본값) — 서비스 정상 동작에 영향 없음.

**포트 매핑**:

| 서비스 | 포트 | 용도 |
|--------|------|------|
| langfuse-web | 3001 | Web UI |
| langfuse-db | 5433 | LangFuse 전용 PostgreSQL (앱 DB와 별도) |
| langfuse-redis | 6380 | 캐시 |
| langfuse-minio | 9002 (API) / 9091 (콘솔) | 미디어 저장 |

## 6. 지속적 유지보수

-   **포즈 데이터 보강**: [Pose Maintenance](POSE_MAINTENANCE.md)
-   **에셋 관리 정책**: [Storage Policy](STORAGE_POLICY.md)
-   **캐릭터 고도화**: [Character Control Guide](CHARACTER_CONTROL_GUIDE.md)
-   **트러블슈팅**: [Troubleshooting Guide](TROUBLESHOOTING.md)

### 캐시 갱신
태그/카테고리 변경 후 런타임 캐시를 갱신합니다:
```bash
curl -X POST http://localhost:8000/admin/refresh-caches
```

### 테스트 실행
```bash
# Backend
cd backend && uv run pytest

# Frontend 단위 테스트
cd frontend && npm test

# Frontend VRT (Visual Regression Test)
cd frontend && npm run test:vrt
```
