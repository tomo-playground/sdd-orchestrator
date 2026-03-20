# 환경 설정 가이드

**최종 업데이트**: 2026-03-18

---

## 1. 서비스 구성

```
┌─────────────┐  ┌──────────────┐  ┌─────────────┐
│  Frontend    │  │   Backend    │  │  Audio       │
│  Next.js     │  │   FastAPI    │  │  TTS/BGM     │
│  :3000       │  │   :8000      │  │  :8001       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                  │
       ├─────────────────┼──────────────────┘
       │                 │
┌──────┴───────┐  ┌──────┴───────┐  ┌─────────────┐
│  PostgreSQL  │  │  MinIO (S3)  │  │  SD Forge    │
│  :5432       │  │  :9000       │  │  :7860       │
└──────────────┘  └──────────────┘  └─────────────┘
       │
┌──────┴───────┐
│  LangFuse    │
│  :3001       │
└──────────────┘
```

## 2. 환경별 설정

| 환경 | `LANGFUSE_TRACING_ENVIRONMENT` | `LOG_LEVEL` | `GEMINI_AUTO_EDIT_ENABLED` |
|------|-------------------------------|-------------|---------------------------|
| **development** | `development` | `DEBUG` | `false` |
| **staging** | `staging` | `INFO` | `true` |
| **production** | `production` | `WARNING` | `true` |

## 3. 필수 환경 변수

### Backend (.env)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `DATABASE_URL` | **필수** | — | PostgreSQL 연결 문자열 |
| `GEMINI_API_KEY` | **필수** | — | Gemini API 키 |
| `SD_BASE_URL` | 권장 | `http://127.0.0.1:7860` | SD Forge WebUI |
| `AUDIO_SERVER_URL` | 권장 | `http://127.0.0.1:8001` | TTS/BGM 서버 |
| `LANGFUSE_ENABLED` | 권장 | `false` | LangFuse 활성화 |
| `LANGFUSE_PUBLIC_KEY` | 조건부 | — | LangFuse 활성화 시 필수 |
| `LANGFUSE_SECRET_KEY` | 조건부 | — | LangFuse 활성화 시 필수 |

> 전체 목록: `backend/.env.example` 참조

### Frontend (.env.local)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `BACKEND_ORIGIN` | 선택 | `http://127.0.0.1:8000` | Backend API URL (Next.js rewrite 프록시 경유) |

## 4. 서비스 시작 순서

```bash
# 1. 인프라 (Docker)
docker compose up -d                    # PostgreSQL + MinIO + LangFuse

# 2. SD Forge WebUI
cd forge && ./webui.sh --api --listen   # GPU 필요

# 3. Audio Server
cd audio && ./run_audio.sh start        # GPU 필요 (CUDA)

# 4. Backend
cd backend && source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 5. Frontend
cd frontend && npm run dev
```

## 5. LangFuse 환경 분리

LangFuse SDK는 `LANGFUSE_TRACING_ENVIRONMENT` 환경 변수로 trace를 환경별로 분리합니다.

```bash
# .env
LANGFUSE_TRACING_ENVIRONMENT=development
```

| 값 | 용도 |
|-----|------|
| `development` | 로컬 개발 |
| `staging` | 스테이징 테스트 |
| `production` | 운영 환경 |

LangFuse UI에서 Environment 필터로 환경별 trace/score를 분리 조회할 수 있습니다.

## 6. GPU 서비스 관리

| 서비스 | GPU | 포트 | 시작 |
|--------|-----|------|------|
| SD Forge | CUDA | 7860 | `./webui.sh --api` |
| Audio (TTS) | CUDA | 8001 | `./run_audio.sh start` |
| Audio (MusicGen) | CPU | 8001 | Audio 서버에 포함 (상주) |

> TTS는 on-demand 로드 + idle 2분 자동 언로드. MusicGen은 CPU 상주.

## 7. 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `GEMINI_API_KEY` 없음 에러 | `.env` 미설정 | `cp .env.example .env` 후 키 입력 |
| LangFuse Score 미기록 | `LANGFUSE_ENABLED=false` | `.env`에서 `true`로 변경 + 키 설정 |
| SD 이미지 생성 실패 | Forge WebUI 미실행 | `./webui.sh --api` 실행 확인 |
| TTS 503 에러 | Audio 서버 모델 로딩 중 | 10초 대기 후 재시도 (자동 retry 내장) |
| `MINIO_SECRET_KEY` 경고 | 12자 미만 | 12자 이상 키로 변경 |
| `client has been closed` | 서버 재시작 중 파이프라인 실행 | 자동 재연결 (Phase 38 수정 완료) |
