---
id: SP-009
priority: P1
scope: fullstack
branch: feat/SP-009-environment-standardization
created: 2026-03-20
status: pending
depends_on:
---

## 무엇을
프로젝트 전체 환경(development/staging/production) 설정 표준화

## 왜
- Langfuse environment가 `default`, `development`, `langfuse-llm-as-a-judge` 3종으로 파편화
- Backend에 `APP_ENV` 개념 자체가 없어 환경별 분기 불가
- CI(`ENVIRONMENT: "test"`)와 Langfuse(`LANGFUSE_TRACING_ENVIRONMENT`)가 각자 환경 변수를 사용
- Frontend `.env` 구조가 Next.js 표준(`.env.development` / `.env.production`)을 따르지 않음
- `ConnectionGuard.tsx`에서 `:8000` → `:9000` 포트 치환 해킹 (현재도 broken — 404)
- `next.config.ts` rewrites 3개 전부 dead code (Frontend가 절대 URL로 직접 호출)

## 분석 이력
- 6회차: 외부 시스템 14개 + 인프라 8개 전수 조사
- 7회차: 기계적 IP:PORT/localhost 전수 스캔, `validation.py` 버킷 하드코딩, 죽은 변수 발견
- 8회차: 코드 영향도 — 순환 import 위험, `config.py:890` wildcard import 구조 파악
- 9회차: 시나리오 기반 — 온보딩/테스트/빌드/마이그레이션/실패 모드 검증

## 외부 연동 시스템 전수 조사

### 외부 시스템 목록 및 환경별 영향

| # | 시스템 | 환경변수 | 환경별 변경 | 현재 상태 |
|---|--------|---------|-----------|----------|
| 1 | **PostgreSQL** | `DATABASE_URL` | Yes | `.env`에서 관리, pool 설정 없음 |
| 2 | **MinIO/S3** | `MINIO_ENDPOINT`, `STORAGE_PUBLIC_URL` 등 5개 | Yes | 기본값 `localhost:9000` |
| 3 | **SD WebUI** | `SD_BASE_URL` | Dev only | 기본값 `127.0.0.1:7860` |
| 4 | **Audio Server** | `AUDIO_SERVER_URL` | Dev only | 기본값 `127.0.0.1:8001`, 로컬 CUDA 전용 |
| 5 | **Langfuse** | `LANGFUSE_*` 5개 | Yes | environment 기본값 수정 완료 |
| 6 | **Gemini API** | `GEMINI_API_KEY` + 모델명 | No | 환경 무관 |
| 7 | **YouTube API** | `YOUTUBE_*` 5개 | Yes | `REDIRECT_URI`=`localhost:3000` — 프로덕션 변경 필수 |
| 8 | **Danbooru API** | `DANBOORU_*` 3개 | No | 외부 공개 API |
| 9 | **Civitai API** | `CIVITAI_*` 2개 | No | 외부 공개 API |
| 10 | **Ollama** | `OLLAMA_*` 3개 | Dev only | 기본값 `localhost:11434` |
| 11 | **HuggingFace** | `HF_TOKEN` | No | 환경 무관 |
| 12 | **Redis** | 없음 | N/A | Backend 미사용 (Langfuse 내부 전용) |
| 13 | **SMTP/Email** | 없음 | N/A | 미사용 |
| 14 | **CDN** | 없음 | N/A | 미사용 |

### 인프라 레벨 환경별 차이

| 항목 | Development | Production | 이번 스코프? |
|------|------------|------------|------------|
| **DB Pool** | pool_size=5 (기본) | pool_size=20 권장 | No |
| **Uvicorn** | `--reload` 1 worker | `--workers 4` | No |
| **Logging** | INFO | WARNING 권장 | No (env로 제어 가능) |
| **Swagger** | 활성화 | 비활성화 권장 | No (커스텀 route 제어 가능) |
| **CORS** | `localhost:3000` | 프로덕션 도메인 | No (env로 제어 가능) |
| **SSL/TLS** | http | https (Nginx) | No |

## 코드 영향도 분석

### APP_ENV 배치 — 순환 import 구조

```
config.py:890 → from config_pipelines import *   (wildcard re-export)
config_pipelines.py → config.py import 없음       (단방향)
```

**결정: APP_ENV는 `config_pipelines.py`에 정의**
- `config.py`가 `config_pipelines`를 wildcard import하므로, `config_pipelines.py`에 넣으면 어디서든 `from config import APP_ENV` 가능
- `config.py`에 넣으면 `config_pipelines.py`에서 참조 시 순환 import 발생
- `LANGFUSE_TRACING_ENVIRONMENT`도 같은 파일에 있으므로 파생 로직 자연스러움

### config_pipelines.py 직접 import — 35개 파일

`config_pipelines.py`를 `config.py` 경유 없이 직접 import하는 파일 35개:
- `services/agent/` 노드들 (routing, observability, director, writer 등)
- `routers/` (presets, scripts)
- `services/llm/` (registry)
- `tests/` (test_model_upgrade, test_langfuse_scoring 등)

**영향**: `config_pipelines.py`에 `APP_ENV` 추가는 신규 변수 추가이므로 기존 import에 영향 없음. `LANGFUSE_TRACING_ENVIRONMENT` 정의 변경(기본값을 `APP_ENV`에서 파생)도 기존 `os.getenv` 우선순위가 유지되어 하위 호환.

### load_dotenv 타이밍

- `config.py:18` → `load_dotenv(BASE_DIR / ".env")` 실행
- `config.py:890` → `from config_pipelines import *` → `config_pipelines.py` 로드
- **순서 보장**: `load_dotenv`가 먼저 실행된 후 `config_pipelines.py`의 `os.getenv` 호출
- **테스트 직접 import**: `config_pipelines.py`를 직접 import하면 `load_dotenv` 미실행 → 기본값 사용. 현재도 동일 동작이므로 **신규 위험 아님**

### next.config.ts rewrites — 확정 dead code

Frontend 코드에서 상대경로 사용처 전수 스캔 결과:
- `/api/...` 상대경로 fetch/axios 호출: **0건** (전부 `API_BASE` 절대 URL)
- `/outputs/...` 참조: **0건** (`resolveImageUrl()`이 `API_ROOT` prefix 추가)
- `/assets/...` 참조: **0건** (Backend에 `/assets` StaticFiles mount 자체가 없음)
- **제거해도 런타임 동작 변화 없음**

### ConnectionGuard VIDEO_URL — 이중 broken

1. URL 구성 오류: `API_BASE.replace(":8000", ":9000")` → `http://localhost:9000/api/v1` (MinIO에 `/api/v1` 경로 없음)
2. 리소스 부재: MinIO `shared/video/` 디렉토리 자체가 없음 (fonts, overlay, poses만 존재)
- **현재도 404 → dead feature → VIDEO_URL 라인 제거가 답**

### Frontend .env.local 죽은 변수

- `NEXT_PUBLIC_API_BASE`: 코드에서 참조 0건. `NEXT_PUBLIC_API_URL`만 사용 중
- 정리 대상

## 시나리오별 안전성 검증

| 시나리오 | 결과 |
|---------|------|
| **신규 개발자 클론** | `.env.development` git 포함 → .env.local 없이 개발 시작 가능 |
| **기존 개발자 PR 머지** | `.env.local` 우선순위 > `.env.development` → 기존 동작 유지 |
| **pytest 실행** | APP_ENV 기본값 `development` → 기존과 동일 |
| **CI 실행** | `.env` 없음 → 기본값 사용 → 기존과 동일. `APP_ENV: test` 설정하면 Langfuse env만 변경 |
| **next build** | `.env.development` 미로드 → fallback `localhost:8000` → 빌드는 성공. 프로덕션 배포 시 `.env.production` 필요 |
| **APP_ENV 오타** | Langfuse에 이상한 환경명 기록됨. 유효성 검증 없음 (위험: 낮) |
| **rewrites 제거** | dead code 제거 → 동작 변화 0 |

## 완료 기준 (DoD)

### Must (이번 태스크)
- [ ] `config_pipelines.py`에 `APP_ENV` 변수 도입 (development/staging/production/test)
- [ ] `LANGFUSE_TRACING_ENVIRONMENT` 기본값을 `APP_ENV`에서 파생 (별도 오버라이드 가능)
- [ ] `config_pipelines.py` 기본값 변경 검증 (이미 수정됨 — PR에 포함)
- [ ] `observability.py` `trace_context()` environment 주입 검증 (이미 수정됨 — PR에 포함)
- [ ] `ConnectionGuard.tsx` broken VIDEO_URL 제거 (dead feature 정리)
- [ ] `next.config.ts` rewrites 3개 제거 (dead code 확인 완료)
- [ ] Frontend `.env.development` 생성 (`NEXT_PUBLIC_API_URL`)
- [ ] Frontend `.env.local` 죽은 변수 `NEXT_PUBLIC_API_BASE` 제거
- [ ] Frontend `.gitignore` 정리 (`.env.local`/`.env*.local`만 무시, `.env.development` 추적 허용)
- [ ] Backend `.env.example`에 `APP_ENV` 가이드 추가
- [ ] CI `ci.yml`의 `ENVIRONMENT: "test"` → `APP_ENV: "test"` 변경
- [ ] 기존 테스트 전체 통과 (backend pytest + frontend vitest)
- [ ] 로컬에서 이미지/에셋 로딩 정상 동작 확인

### Won't (이번 스코프 아님)
- Docker compose 환경 분리 (프로덕션 인프라 구축 시)
- Audio 서버 환경 설정 (로컬 CUDA 전용)
- MCP/에이전트 설정 파일 변경 (개발 도구)
- staging/production `.env` 파일 생성 (서버 없음)
- `run_backend.sh` 환경 분기 (workers, reload)
- `database.py` pool 설정
- Swagger 환경별 비활성화
- SSL/TLS/Nginx
- YouTube OAuth redirect URI 변경 (프로덕션 도메인 필요)
- `validation.py` 버킷명 하드코딩 수정 (별도 버그)
- APP_ENV 유효성 검증 (enum 체크 — 향후)

## 제약
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것: SD/TTS/파이프라인 설정, database.py pool
- 의존성 추가 금지
- 기존 `.env` 파일의 값이 바뀌면 안 됨 (구조만 변경)
- **`.env.development`에 시크릿 금지** — git 추적되므로 URL/포트 등 비밀 아닌 설정만
- rewrites 제거 후 이미지/에셋 로딩 regression 검증 필수

## 힌트

### 변경 파일 목록 (9개)
| # | 파일 | 변경 | 위험도 |
|---|------|------|--------|
| 1 | `backend/config_pipelines.py` | APP_ENV 추가, LANGFUSE 파생 (기본값 변경은 이미 완료) | 낮 |
| 2 | `backend/services/agent/observability.py` | environment 주입 (이미 완료 — PR 포함만) | 낮 |
| 3 | `frontend/next.config.ts` | rewrites 3개 제거 | 중 (regression 검증) |
| 4 | `frontend/app/components/shell/ConnectionGuard.tsx` | broken VIDEO_URL 제거 | 낮 (이미 404) |
| 5 | `frontend/.env.development` | 신규 생성 | 낮 |
| 6 | `frontend/.env.local` | 죽은 변수 제거 | 낮 |
| 7 | `frontend/.gitignore` | `.env*` → `.env.local`/`.env*.local` | 중 (보안) |
| 8 | `backend/.env.example` | APP_ENV 가이드 추가 | 낮 |
| 9 | `.github/workflows/ci.yml` | ENVIRONMENT → APP_ENV | 낮 (죽은 변수) |

### 구현 순서 권장
1. `config_pipelines.py` — APP_ENV 추가 + LANGFUSE 파생 (Backend 기반)
2. `.env.example` — APP_ENV 가이드
3. `ci.yml` — ENVIRONMENT → APP_ENV
4. `next.config.ts` — rewrites 제거
5. `ConnectionGuard.tsx` — VIDEO_URL 제거
6. `.env.development` — 생성
7. `.env.local` — 죽은 변수 제거
8. `.gitignore` — 규칙 변경
9. 테스트 실행 + 로컬 동작 확인

### 주의사항
- `config_pipelines.py`를 직접 import하는 파일 35개 존재 — APP_ENV는 신규 추가라 영향 없음
- `config.py:890`의 `from config_pipelines import *` — APP_ENV가 자동 re-export됨
- `next build` 시 `.env.development` 미로드 — 프로덕션 배포 시 `.env.production` 필요
- `.gitignore` 변경 후 `.env.development`에 시크릿 넣으면 git에 커밋됨 — URL/포트만 허용
- `ConnectionGuard` VIDEO_URL 제거 시 fallback UI(캐릭터 프리뷰 이미지) 정상 동작 확인 필요
