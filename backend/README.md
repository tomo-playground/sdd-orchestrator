# Backend

FastAPI + LangGraph 기반 API 서버. 스토리보드 생성, 이미지/영상 렌더링, Agentic Pipeline을 담당합니다.

> 프로젝트 전체 개요: [README.md](../README.md) / 개발 가이드: [CONTRIBUTING.md](../docs/guides/CONTRIBUTING.md)

---

## 구조

```
backend/
├── routers/           # API 엔드포인트 (33개)
├── services/
│   ├── agent/         # LangGraph Agentic Pipeline (15개 노드, 9개 도구)
│   │   ├── nodes/     #   Director, Writer, Critic, Research, Cinematographer 등
│   │   ├── tools/     #   Gemini Function Calling 도구
│   │   ├── state.py   #   Graph State
│   │   └── routing.py #   조건부 라우팅
│   ├── video/         # FFmpeg 렌더링 파이프라인
│   ├── prompt/        # 프롬프트 엔진 (12-Layer Builder)
│   ├── keywords/      # 태그 시스템 (core, db, cache, validation)
│   ├── storyboard/    # 스토리보드 CRUD, Scene Builder
│   ├── characters/    # 캐릭터 관리, LoRA 연동
│   └── youtube/       # YouTube OAuth + 업로드
├── models/            # SQLAlchemy ORM (26개 모델)
├── templates/         # Jinja2 프롬프트 템플릿 (25개)
├── schemas.py         # Pydantic Request/Response 스키마
├── config.py          # 환경변수 + 상수 SSOT
├── database.py        # DB 연결
├── main.py            # FastAPI 앱 진입점
├── alembic/           # DB 마이그레이션
├── assets/            # 폰트, 오버레이, 오디오
├── tests/             # 1,862개 테스트 (143 파일)
└── pyproject.toml     # uv 프로젝트 정의
```

---

## 실행

```bash
cp .env.example .env          # 환경변수 설정
uv sync                       # 의존성 설치
uv run alembic upgrade head   # DB 마이그레이션
uv run uvicorn main:app --reload --port 8000
```

- API Docs: http://localhost:8000/docs
- 설정 SSOT: `config.py` (하드코딩 금지)

---

## 환경변수

| 카테고리 | 주요 변수 | 필수 |
|----------|----------|------|
| **DB** | `DATABASE_URL` | Y |
| **AI** | `GEMINI_API_KEY` | Y |
| **Storage** | `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` | Y |
| **SD WebUI** | `SD_BASE_URL` (default: `http://localhost:7860`) | Y |
| **TTS** | `TTS_MODEL_NAME`, `TTS_DEVICE` | N |
| **BGM** | `SAO_MODEL_NAME`, `SAO_DEVICE` | N |
| **Logging** | `LOG_FILE`, `LOG_LEVEL`, `LOG_TO_FILE` | N |

전체 목록: `config.py` 참조.

---

## 테스트

```bash
uv run pytest -v                          # 전체
uv run pytest tests/api/ -v               # Integration
uv run pytest tests/test_router_*.py -v   # Router
uv run pytest tests/vrt/ -v               # VRT
uv run pytest --testmon -v                # 변경분만
uv run pytest --lf -v                     # 마지막 실패만
uv run ruff check .                       # 린트
```

상세: [TEST_STRATEGY.md](../docs/03_engineering/testing/TEST_STRATEGY.md)

---

## 관련 문서

| 문서 | 설명 |
|------|------|
| [AGENT_SPEC.md](../docs/03_engineering/backend/AGENT_SPEC.md) | Agentic Pipeline 설계 |
| [PROMPT_SPEC.md](../docs/03_engineering/backend/PROMPT_SPEC.md) | 프롬프트 엔진 명세 |
| [RENDER_PIPELINE.md](../docs/03_engineering/backend/RENDER_PIPELINE.md) | 렌더링 파이프라인 |
| [REST_API.md](../docs/03_engineering/api/REST_API.md) | API 명세 |
| [DB_SCHEMA.md](../docs/03_engineering/architecture/DB_SCHEMA.md) | DB 스키마 |
