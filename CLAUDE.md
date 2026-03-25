# 프로젝트: Shorts Producer

AI 기반 쇼츠 영상 자동화 워크스페이스. LangGraph Agentic Pipeline (Gemini) + Stable Diffusion (이미지) + Qwen3-TTS (12Hz) + MusicGen (BGM) + FFmpeg (렌더링).

## Agent 공통 규칙

이 문서는 모든 AI 에이전트(Claude, Gemini 등)의 **SSOT 컨텍스트**입니다.

- **언어**: 모든 응답은 **한국어**로 작성합니다.
- **DB 스키마**: DB 관련 질문 시 `docs/03_engineering/architecture/DB_SCHEMA.md`를 최우선으로 참조합니다.
- **아키텍처/규칙**: 이 파일(`CLAUDE.md`)의 원칙을 항상 준수합니다. 에이전트별 컨텍스트 파일(`GEMINI.md` 등)은 역할 정의만 포함하며, 세부 규칙은 이 파일을 참조합니다.

## Invariants (절대 위반 금지)

아래 규칙은 예외 없이 준수. 상세 이유는 `.claude/adr/` ADR 참조.

- **INV-1**: 404 응답 시 자동 재생성 금지 — 삭제된 엔티티 부활 금지 (ADR-001)
- **INV-2**: autoSave는 UPDATE만 — CREATE(POST) 호출 금지 (ADR-001)
- **INV-3**: soft delete 엔티티에 PUT/PATCH → 스토어 전체 리셋 (ADR-001)
- **INV-4**: config.py 상수를 문자열 리터럴 하드코딩 금지

## 아키텍처

| 레이어 | 기술 | 핵심 |
|--------|------|------|
| Backend | FastAPI + LangGraph | `routers/` (API), `services/` (로직), `services/agent/` (Agentic Pipeline) |
| Frontend | Next.js 16, React 19 | `app/(app)/` (Home, Studio, Scripts, Library, Settings), Zustand 4-Store |
| DB | PostgreSQL | Storyboard → Scene → CharacterAction 계층 구조 |
| AI | LangGraph + Gemini | 21개 노드 (Director, Writer, Critic, Research, Cinematographer 등), Gemini Function Calling |
| Observability | LangFuse | 셀프호스팅, 파이프라인 트레이싱 |

### Backend 구조
```
backend/
├── routers/          # API 엔드포인트 (29개 라우터)
├── services/
│   ├── agent/        # LangGraph Agentic Pipeline
│   │   ├── nodes/    #   21개 노드
│   │   ├── tools/    #   Gemini Function Calling 도구
│   │   ├── state.py  #   Graph State
│   │   └── routing.py#   조건부 라우팅
│   ├── video/        # FFmpeg 렌더링 파이프라인
│   ├── prompt/       # 프롬프트 엔진 (composition.py: 12-Layer Builder)
│   ├── keywords/     # 태그 시스템 패키지
│   ├── storyboard/   # 스토리보드 CRUD, Scene Builder
│   └── characters/   # 캐릭터 관리, LoRA 연동
├── models/           # SQLAlchemy ORM (associations.py: relational tags)
├── templates/        # (비어 있음 — 프롬프트는 LangFuse에서 관리)
└── config.py         # 모든 상수/환경변수 SSOT
```

## 문서 구조
```
docs/
├── 01_product/       # 제품 (PRD, 로드맵, 기능 명세)
├── 02_design/        # UI/UX 설계
├── 03_engineering/   # 기술 설계 (api/, architecture/, backend/, frontend/, testing/)
├── 04_operations/    # 운영 (배포, SD, TTS, 스토리지, 트러블슈팅)
├── 99_archive/       # 완료된 문서 아카이브
└── guides/           # 개발 가이드 (CONTRIBUTING, SDD_WORKFLOW)
```

### 주요 문서
- **로드맵**: `docs/01_product/ROADMAP.md`
- **기능 명세**: `docs/01_product/FEATURES/*.md`
- **API 명세**: `docs/03_engineering/api/REST_API.md` (+ DOMAIN/PRESETS/ANALYTICS/CREATIVE)
- **DB 스키마**: `docs/03_engineering/architecture/DB_SCHEMA.md`
- **SDD 워크플로우**: `docs/guides/SDD_WORKFLOW.md`
- **개발 가이드**: `docs/guides/CONTRIBUTING.md`

## 코드 및 문서 크기 가이드라인
| 단위 | 권장 | 최대 |
|------|------|------|
| 함수/메서드 | 30줄 | 50줄 |
| 클래스/컴포넌트 | 150줄 | 200줄 |
| 코드 파일 | 300줄 | 400줄 |
| 문서 파일 (.md) | 500줄 | 800줄 |

**원칙**: Single Responsibility, 중첩 3단계 이하, 매개변수 4개 이하
**문서 관리**: 800줄 초과 시 히스토리 추출(Archive) 또는 관심사 분리 필수.

## UI Typography Rules (최소 가독성 기준)
- **최소 폰트 사이즈**: `11px` (text-[11px]). `text-[9px]`, `text-[10px]` 사용 금지.
- **본문/버튼/탭**: `text-xs` (13px) 이상.
- **입력 필드/제목**: `text-sm` (15px) 이상.
- **커스텀 픽셀 사이즈**: `text-[11px]`(배지), `text-[12px]`(라벨), `text-[13px]`(섹션 헤더)만 허용.

## 사전 요구사항
- **ComfyUI**: `http://localhost:8188` (Docker 또는 로컬 실행)
- **환경 변수**: `backend/.env` 파일 필수 (`DATABASE_URL`, `GEMINI_API_KEY` 등)

## Service vs Admin API 분리 기준
- **Service API** (`/api/v1`): 일반 사용자 기능 (캐릭터, 프롬프트, 스토리보드 등)
- **Admin API** (`/api/admin`): 시스템 관리, 일괄 작업, Back-office 전용
- **Frontend**: 서비스 화면은 `API_BASE`, 어드민은 `ADMIN_API_BASE`
- **Backend**: 라우터에서 `service_router`와 `admin_router` 분리

## Configuration Principles (SSOT)
- **설정 값**: 모든 환경 변수 및 상수는 `backend/config.py`에서 관리. 하드코딩 금지.
- **옵션 목록**: Language, Structure 등 도메인 옵션은 **Backend가 SSOT**. Frontend는 API 응답 소비만.
- **태그 규칙**: 충돌/별칭/필터 모두 **DB 테이블**에서 관리. 코드 하드코딩 금지.
- **런타임 캐시**: `TagCategoryCache`, `TagAliasCache`, `TagRuleCache`, `LoRATriggerCache` — startup 시 DB 로드.
- **SD 생성 파라미터**: `config.py` 전역 기본값 < `StyleProfile.default_*` (화풍별 최적값). `_adjust_parameters()`에서 최종 적용.
- **원천 UI 수정 원칙**: SSOT 소유 UI에서만 수정. 다른 화면은 읽기 전용.
- **캐릭터 프롬프트 SSOT**: `positive_prompt` + `negative_prompt` 2필드. 공통 태그는 상수(`config.py`, `config_prompt.py`), 캐릭터 고유만 DB. 공통 태그 DB 중복 저장 금지.

## DB Schema Design Principles
- **관심사 분리**: 콘텐츠 테이블(storyboards)과 설정 필드(groups) 구분.
- **`default_` prefix 금지**: 실제 값에 `default_` 붙이지 않는다.
- **Boolean은 Boolean**: `Integer`로 boolean 저장 금지. `Boolean` + `is_`/`_enabled`.
- **JSON은 JSONB**: `Text`에 JSON 문자열 저장 금지.
- **설정 소유권**: `System Default < Group` (2단계). Character는 Group에 종속 (`group_id` NOT NULL FK).
- **미디어 참조는 media_asset_id 필수**: URL 직접 저장 금지. `media_assets` FK 참조.
- **URL 필드**: DB 저장 안 함. ORM `@property`가 런타임 파생. Pydantic 스키마에 용도 주석 필수.
- **상세**: `.claude/agents/dba.md` 참조.

## API Contract Principles (Backend ↔ Frontend)
- **response_model 필수**: 모든 FastAPI 엔드포인트에 `response_model=` 지정. raw dict 반환 금지.
- **응답 스키마 구체화**: `dict | None` 금지. Pydantic 모델로 필드 명시.
- **Frontend 타입 동기화**: Backend 스키마 필드명 그대로 사용. 존재하지 않는 필드 가정 금지.
- **신규 엔드포인트**: schemas.py 정의 → response_model 지정 → Frontend 타입 일치 → REST API 문서 업데이트

## LangFuse 프롬프트 vs Prompt Builder 역할 분리
- **정적 규칙/지시문**: LangFuse 프롬프트에서 관리. 코드 하드코딩 금지.
- **동적 데이터**: `prompt_builders*.py`가 런타임 포맷팅 → template 변수 주입.
- **판단 기준**: "프롬프트 버전 변경 없이 바뀌는가?" Yes → 빌더, No → LangFuse.

## Gemini API 호출 규칙
- `system_instruction`은 반드시 `GenerateContentConfig.system_instruction`으로 전달. `contents`에 합치기 금지.
- 모든 호출에 `GEMINI_SAFETY_SETTINGS` (config.py) 적용. 인라인 정의 금지.
- `PROHIBITED_CONTENT` 감지 시 `GEMINI_FALLBACK_MODEL`로 자동 1회 재시도 + 로그 기록.
- `_sanitize_for_gemini_prompt()` / `_restore_danbooru_tags()` 치환 파이프라인 유지.

## Agent 노드 추가 체크리스트
1. `langfuse_prompt.py`에 템플릿명 등록 + 매핑
2. LangFuse UI에 프롬프트 생성 (system + user)
3. Fallback 상수 정의
4. `langfuse_prompt` 인자 전달 (observability 연결)

## Image Generation Debug Payload Convention
`debug_payload`는 **`{request, actual}`** 2-레벨 구조. Backend `used_*` 필드 → 스키마 → Frontend `actual.*` 3곳 동기화 필수.

## Code Principles
- **중복 금지**: 같은 로직 2곳 이상이면 헬퍼 함수 추출. 모든 호출 경로에서 적용 확인.
- **Spread Passthrough**: 데이터 변환 시 Whitelist 매핑 금지. `...spread`로 패스스루 + 변환 필드만 오버라이드. UI-only 필드는 destructuring exclude.
- **삭제 = 즉시 정리**: 활성 엔티티 삭제 시 스토어 전체 리셋 + 리다이렉트. 404 = 삭제 간주.
- **Soft Delete 일관성**: 모든 GET/PUT/PATCH 쿼리에 `deleted_at.is_(None)` 필터.

## Tag Format Standard (Danbooru 표준)
- **모든 태그는 언더바(`_`) 형식**. 공백 형식 절대 금지. `tag.replace("_", " ")` 금지.
- **예외**: 하이픈 태그(`close-up`), LoRA 트리거 워드(Civitai 원본 형식 유지).
- **2-Level Hierarchy**: `category` (scene/character/quality/meta) + `group_name` (expression/gaze/pose 등 24종). 소분류 필터는 `Tag.group_name` 사용.

## Sub Agents

| Agent | 역할 | Commands |
|-------|------|----------|
| **Tech Lead** | 개발 총괄, CI/CD, 오케스트레이터 | `/roadmap`, `/test`, `/review`, `/db`, `/docs` |
| **PM Agent** | 로드맵/우선순위/문서 관리 | `/roadmap`, `/docs`, `/vrt`, `/test`, `/pm-check` |
| **Prompt Engineer** | SD 프롬프트 최적화, 태그 시스템 | `/prompt-validate`, `/sd-status` |
| **Storyboard Writer** | 스토리보드/스크립트, LangFuse 프롬프트 | `/roadmap` |
| **QA Validator** | 품질 체크, 테스트 검증 | `/test`, `/review`, `/vrt` |
| **FFmpeg Expert** | 영상 렌더링 + TTS/BGM + 오디오 후처리 | `/vrt`, `/roadmap` |
| **UI/UX Engineer** | UI/UX 설계, 와이어프레임 | `/vrt`, `/test` |
| **Frontend Dev** | Next.js/React, Zustand 상태 관리 | `/test frontend`, `/vrt` |
| **Backend Dev** | FastAPI, 서비스 로직, API, LangFuse 등록 | `/test backend`, `/sd-status`, `/db` |
| **DBA** | DB 설계, 마이그레이션, 쿼리 최적화 | `/db`, `/test backend` |
| **Security Engineer** | 보안 취약점, 인증/인가, 시크릿 관리 | `/review`, `/test` |
| **Video Reviewer** | 영상 품질, 프레임 구성 검토 | `/review`, `/vrt` |
| **Prompt Reviewer** | SD/Gemini 프롬프트, Danbooru 태그 검토 | `/prompt-validate`, `/review` |
| **Voice Reviewer** | TTS 음성 톤/속도/감정 검토 | `/review` |
| **Sound Reviewer** | BGM/효과음/오디오 정규화 검토 | `/review` |
| **Performance Engineer** | 외부 통신 최적화, 인프라/배포 | `/review` |
| **SDD Coach** | SDD 프로세스 감시, 리뷰 자동화 | `/review`, `/pm-check` |

> 에이전트 상세 역할: `.claude/agents/*.md` 참조

## Commands

| Command | 역할 |
|---------|------|
| `/roadmap` | 로드맵 조회/업데이트 |
| `/test` | 테스트 실행 (전체/backend/frontend/vrt/e2e) |
| `/review` | 코드 리뷰 |
| `/vrt` | Visual Regression Test |
| `/sd-status` | ComfyUI 상태 확인 |
| `/prompt-validate` | 프롬프트 문법 검증 |
| `/db` | DB 마이그레이션 상태/생성/적용/롤백 |
| `/docs` | 문서 구조 조회/정합성 체크 |
| `/pm-check` | PM 자율 점검 |
| `/sdd-design` | SDD 상세 설계 자동 작성 |
| `/sentry-patrol` | Sentry 에러 배치 순찰 → Issue 생성 |
| `/qa-patrol` | Playwright QA 순찰 |
| `/sdd-coach` | SDD 코치 점검 |
| `/pose` | 포즈 에셋 분석/동기화 |

## Hooks (자동화)

| Event | Hook | 동작 |
|-------|------|------|
| `PostToolUse` | `auto-lint.sh` | Edit/Write 후 자동 린트 (ruff → `.py`, prettier → `.ts/.tsx`) |

## Workflow Rules (에이전트 자동 워크플로우)

| 트리거 | 자동 액션 |
|--------|----------|
| 구현 완료 | Tech Lead 코드 리뷰 (커밋 전) |
| `models/*.py` 또는 `alembic/` 변경 | DBA 리뷰 필수 |
| 외부 API 호출 추가/변경 | Performance Engineer 리뷰 |
| `services/agent/nodes/` 추가/변경 | LangFuse 연동 체크 |
| Phase 완료 / 새 기능 착수 | PM 문서 동기화 / 명세 확인 |

**설계 리뷰 시 담당 에이전트 참여**: `services/agent/nodes/` → Backend Dev + Storyboard Writer, `services/keywords/` → Prompt Engineer, `services/video/` → FFmpeg Expert, `models/` → DBA, `.github/` → Tech Lead, `frontend/` → Frontend Dev, 외부 API → Performance Engineer

**구현→리뷰→수정 파이프라인**: 코드 변경 → Tech Lead 리뷰 자동 → WARNING/BLOCKER 즉시 수정 → 사용자 보고. 단순 설정/문서 변경은 리뷰 생략.

**테스트 실패 수정**: 3개 파일 이상 실패 시 멀티 에이전트 병렬 수정.

## 용어 정의 (Terminology)

### 서비스 언어 정책
**기본 언어: 한국어**. 상세: `docs/02_design/NAMING_CONVENTION.md`

### 도메인 용어 사전

| 코드 (영문) | UI (한국어) | 설명 |
|-------------|------------|------|
| Project | 채널 | 콘텐츠 발행 채널 (최상위) |
| Group | 시리즈 | 같은 화풍의 영상 묶음 |
| Storyboard | 영상 | 개별 쇼츠 영상 단위 |
| Scene | 씬 | 영상 내 개별 장면 |
| Character | 캐릭터 | AI 캐릭터 |
| Style Profile | 화풍 | 생성 스타일 프로필 |

### Studio 워크플로우 탭
`Script` → `Stage` → `Direct` → `Publish` (4탭)

### 칸반 상태
`draft`(초안), `in_prod`(제작 중), `rendered`(렌더 완료), `published`(게시됨)

### AI 실행 모드
`guided`(Guided: AI와 협력), `fast_track`(Fast: 자동 1회 실행)

### Scene Text vs Caption
- **Scene Text**: 씬 스크립트 텍스트 (영상 위 오버레이). 코드: `scene_text`, `include_scene_text`, `scene_text_font`
- **Caption**: 게시물 메타데이터 (좋아요, 시간 등). 카드 하단.

## SDD 자율 실행 워크플로우

**SDD (Spec-Driven Development)**: 사람이 스펙(DoD)을 작성하고, AI가 설계→TDD(RED→GREEN)→PR까지 자율 실행.

### 역할 분리
| 역할 | 사람 | AI |
|------|------|-----|
| 스펙 + DoD | O | |
| 상세 설계 | 승인 | 작성 |
| 테스트 + 구현 + 리뷰 | | O |
| 검수 + 머지 판단 | O | |

### 핵심 흐름
```
태스크(사람) → 설계(AI→사람승인) → /sdd-run → AI TDD + PR → 리뷰(Claude+CodeRabbit) → 머지(사람)
```

### 커밋 경로 규칙
- **main 직접 허용**: `.claude/`, `CLAUDE.md`, `.github/workflows/`, `docs/`
- **feat 브랜치 + PR 필수**: `backend/`, `frontend/`, `audio/`, `scripts/`, 그 외 코드

### 용어 규칙 (혼용 금지)
| 용어 | 역할 | 위치 |
|------|------|------|
| **Roadmap** | 제품 방향, Phase | `docs/01_product/ROADMAP.md` |
| **Backlog** | 미착수 태스크 큐 | `.claude/tasks/backlog.md` |
| **Task** | 착수 중 (spec + design) | `.claude/tasks/current/SP-NNN_*/` |
| **Done** | 완료 이력 | `.claude/tasks/done/SP-NNN_*/` |

> **상세**: 설계 규칙, 자율 실행 규칙, 세션 프로토콜, Hotfix 워크플로우 등은 `docs/guides/SDD_WORKFLOW.md` 참조.
