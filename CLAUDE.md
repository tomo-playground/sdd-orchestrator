# 프로젝트: Shorts Producer (V3)

AI 기반 쇼츠 영상 자동화 워크스페이스. Gemini (스토리보드) + Stable Diffusion (이미지) + FFmpeg (렌더링).

## 아키텍처

| 레이어 | 기술 | 핵심 |
|--------|------|------|
| Backend | FastAPI | `routers/` (API), `services/` (로직) |
| Frontend | Next.js 15 | `app/page.tsx` (스튜디오), `hooks/useAutopilot.ts` |
| DB | PostgreSQL | Storyboard → Scene → CharacterAction 계층 구조 |

### V3 Backend 구조
```
backend/
├── routers/          # API 엔드포인트 (storyboard, characters, admin, activity_logs 등)
├── services/
│   ├── keywords/     # 태그 시스템 패키지 (core, db, db_cache, processing, validation 등)
│   └── prompt/       # 프롬프트 엔진 (v3_composition.py: 12-Layer Builder)
├── models/           # SQLAlchemy ORM (associations.py: V3 relational tags)
└── config.py         # 모든 상수/환경변수 SSOT
```

## 문서 구조
```
docs/
├── 00_meta/          # 문서 관리 규칙
├── 01_product/       # 제품 (PRD, 로드맵, 기능 명세)
│   ├── PRD.md
│   ├── ROADMAP.md
│   └── FEATURES/     # 미구현 기능별 명세 (what/why)
├── 02_design/        # UI/UX 설계
├── 03_engineering/   # 기술 설계 (how)
│   ├── api/          # REST API 명세
│   ├── architecture/ # DB 스키마, 시스템 개요
│   ├── backend/      # 프롬프트, 렌더링, Soft Delete 등
│   ├── frontend/     # 상태 관리
│   └── testing/      # 테스트 전략, 시나리오
├── 04_operations/    # 운영 (배포, SD WebUI, 트러블슈팅)
├── 99_archive/       # 완료된 문서 아카이브
└── guides/           # 개발 가이드 (CONTRIBUTING)
```

### 주요 문서
- **로드맵**: `docs/01_product/ROADMAP.md`
- **기능 명세**: `docs/01_product/FEATURES/*.md`
- **제품 스펙**: `docs/01_product/PRD.md`
- **API 명세**: `docs/03_engineering/api/REST_API.md`
- **DB 스키마**: `docs/03_engineering/architecture/DB_SCHEMA.md`
- **프롬프트 설계**: `docs/03_engineering/backend/PROMPT_SPEC_V2.md`
- **테스트 전략**: `docs/03_engineering/testing/TEST_STRATEGY.md`
- **테스트 시나리오**: `docs/03_engineering/testing/TEST_SCENARIOS.md`
- **개발 가이드**: `docs/guides/CONTRIBUTING.md`

## 코드 및 문서 크기 가이드라인
| 단위 | 권장 | 최대 |
|------|------|------|
| 함수/메서드 | 30줄 | 50줄 |
| 클래스/컴포넌트 | 150줄 | 200줄 |
| 코드 파일 | 300줄 | 400줄 |
| 문서 파일 (.md) | 500줄 | 800줄 |

**원칙**: Single Responsibility, 중첩 3단계 이하, 매개변수 4개 이하
**문서 관리**: 800줄 초과 시 히스토리 추출(Archive) 또는 관심사 분리(Sub-Roadmap) 필수.

## 사전 요구사항
- **SD WebUI**: API 모드 실행 (`--api` 옵션)
- **환경 변수**: `backend/.env` 파일 필수 (`DATABASE_URL`, `GEMINI_API_KEY` 등)

## Configuration Principles (SSOT)
- **설정 값**: 모든 환경 변수 및 상수는 `backend/config.py`에서 관리합니다. 개별 파일 하드코딩 금지.
- **옵션 목록**: Language, Structure 등 도메인 옵션은 **Backend가 SSOT**. Frontend는 API 응답을 소비만 한다. `frontend/constants/`에 도메인 옵션 하드코딩 금지.
  - Language: `config.py` → `STORYBOARD_LANGUAGES` → `/presets` API 응답의 `languages` 필드
  - Structure: `services/presets.py` → `PRESETS` dict → `/presets` API 응답의 `presets[].structure`
- **로직 기준**: 태그 우선순위 등의 비즈니스 로직은 **Backend**(`backend/services/keywords/` 패키지)가 Single Source of Truth입니다.
- **태그 규칙**: 충돌(`tag_rules`), 별칭(`tag_aliases`), 필터(`tag_filters`) 모두 **DB 테이블**에서 관리. 코드 하드코딩 금지.
- **런타임 캐시**: `TagCategoryCache`, `TagAliasCache`, `TagRuleCache`, `LoRATriggerCache` — startup 시 DB에서 로드, 변경 시 `/admin/refresh-caches`.

## DB Schema Design Principles
- **관심사 분리**: 콘텐츠 테이블(storyboards)과 설정 테이블(group_config)을 혼합하지 않는다.
- **`default_` prefix 금지**: 실제 값에 `default_` 붙이지 않는다. cascade/fallback 문맥에서만 사용.
- **Boolean은 Boolean**: `Integer`로 boolean 저장 금지. `Boolean` 타입 + `is_`/`_enabled` 네이밍.
- **JSON은 JSONB**: `Text`에 JSON 문자열 저장 금지. 구조화 데이터는 반드시 `JSONB`.
- **설정 소유권**: `System Default < Project Config < Group Config`. 콘텐츠 엔티티는 설정을 소유하지 않는다.
- **미디어 참조는 media_asset_id 필수**: 이미지/비디오/오디오 URL을 직접 저장하지 않는다.
  - ❌ `image_url: "http://localhost:9000/..."` — 환경 종속, 이동 불가
  - ✅ `media_asset_id: 123` — `media_assets` 테이블 FK 참조
  - Backend GET 응답에서 `media_asset_id` → `url` 변환 (serialize 시점)
  - Frontend는 저장 시 URL 제거, 조회 시 Backend가 채워준 URL 사용
- **상세**: `.claude/agents/dba.md` "스키마 설계 철학" 섹션 참조.

## API Contract Principles (Backend ↔ Frontend)
- **response_model 필수**: 모든 FastAPI 라우터 엔드포인트에 `response_model=` 지정. raw dict 반환 금지.
- **응답 스키마 구체화**: `dict | None` 금지. 반드시 Pydantic 모델로 필드를 명시한다. (예: `data: SceneGenerateResponse | None`)
- **Frontend 타입 동기화**: Backend 스키마의 필드명을 그대로 사용. Frontend에서 필드명을 추측하여 작성하지 않는다.
  - Backend가 `image` (base64)를 반환하면 Frontend도 `result.data.image`로 접근.
  - `image_url` 등 존재하지 않는 필드를 가정하지 않는다.
- **신규 엔드포인트 체크리스트**:
  1. `schemas.py`에 Request + Response 모델 정의
  2. 라우터에 `response_model=` 지정
  3. Frontend 타입(interface)을 Backend 스키마와 일치시킴
  4. REST API 명세 (`docs/03_engineering/api/REST_API.md`) 업데이트

## Code Modularization Principles (중복 로직 금지)
- **변환 로직 모듈화**: 동일한 데이터 변환이 여러 곳에서 필요하면 **반드시 헬퍼 함수로 추출**한다.
  - 예: `sanitizeCandidatesForDb()` — candidates 저장 시 `image_url` 제거
  - 예: `mapGeminiScenes()` — Gemini 응답 → Scene 타입 변환
- **복사-붙여넣기 금지**: 같은 로직이 2곳 이상에서 사용되면 즉시 공통 함수로 추출한다.
- **완전성 검증**: 새 기능 추가 시 **모든 호출 경로**에서 해당 로직이 적용되는지 확인한다.
  - ❌ `autoSaveStoryboard()`에만 적용하고 `persistStoryboard()`에서 누락하는 실수 방지
- **테스트 케이스 필수**: 공통 헬퍼 함수는 **단위 테스트로 방어**한다.

## Frontend State Sync Principles (Active Entity Deletion)
- **삭제 = 즉시 정리**: 현재 활성 엔티티(스토리보드, 씬 등)를 삭제하면 **스토어 전체 리셋** + 안전한 화면으로 리다이렉트. `storyboardId: null`만 설정하고 나머지 데이터를 방치하지 않는다.
- **404 = 삭제된 것으로 간주**: API에서 404 반환 시 에러를 무시하지 않는다. 토스트 메시지 표시 + 스토어 리셋 + URL 정리.
- **useRef 가드 리셋**: `useRef`로 중복 실행을 방지할 때, 조건이 해제되면 **반드시 ref를 리셋**한다. (예: `?new=true` → `?id=X` 이동 시 ref 초기화)
- **Soft Delete 일관성**: Backend의 모든 GET/PUT/PATCH 쿼리에 `deleted_at.is_(None)` 필터 적용. DELETE만 soft delete 필터하고 UPDATE에서 빠뜨리지 않는다.

## Tag Format Standard (Danbooru 표준)
**원칙**: 모든 태그는 **언더바(_) 형식**을 사용합니다. 공백 형식 절대 금지.

**근거**:
- **Danbooru 표준**: `brown_hair`, `looking_at_viewer`, `cowboy_shot`
- **WD14 Tagger CSV**: 언더바 형식 사용
- **SD 프롬프트**: 언더바 형식 사용
- **DB 저장**: 언더바 형식 통일 (Phase 6-4.21 완료)

**적용 범위**:
- DB 저장 (tags 테이블, tag_effectiveness 테이블)
- API 응답 (JSON 포맷)
- 프롬프트 생성 (`normalize_prompt_token()` 보존)
- Gemini 템플릿 예시 (create_storyboard.j2)
- WD14 검증 결과

**금지 사항**:
- ❌ 공백 형식 변환 (`tag.replace("_", " ")`)
- ❌ 혼용 (일부는 언더바, 일부는 공백)
- ❌ 사용자 입력 자동 변환 (입력은 그대로, DB 조회 시에만 정규화)

**예외**:
- 하이픈 태그는 유지: `close-up`, `full-body`
- 복합어 태그는 언더바로 연결: `light_brown_hair`, `school_uniform`
- **치비(Chibi) 특화**: 반드시 `super_deformed`, `small_body`, `big_head` 형식을 사용 (공백 금지)
- **LoRA 트리거 워드**: Civitai 원본 형식 그대로 유지 (Danbooru 규칙 적용 안 함)
  - 공백 허용: `"flat color"`, `"cubism style"`
  - 언더스코어 허용: `"Midoriya_Izuku"`, `"hrkzdrm_cs"`
  - 이유: LoRA 제작자가 정의한 원본 형식 존중, 캐릭터명 가독성

> 관련 커밋: Phase 6-4.21 (2026-01-27) - DB 공백 태그 554개 → 언더바 통일

## Sub Agents

| Agent | 역할 | Commands |
|-------|------|----------|
| **Tech Lead** | 개발 총괄, 코드 리뷰, 크로스 에이전트 조율 | `/roadmap`, `/test`, `/review`, `/db`, `/docs` |
| **PM Agent** | 로드맵/우선순위/문서 구조 관리 | `/roadmap`, `/docs`, `/vrt`, `/test` |
| **Prompt Engineer** | SD 프롬프트 최적화 + 데이터 기반 고도화 | `/prompt-validate`, `/sd-status` |
| **Storyboard Writer** | 스토리보드/스크립트 작성 | `/roadmap` |
| **QA Validator** | 품질 체크/테스트 검증/TROUBLESHOOTING | `/test`, `/review`, `/vrt`, `/sd-status`, `/prompt-validate` |
| **FFmpeg Expert** | 렌더링/비디오 효과 | `/vrt`, `/roadmap` |
| **UI/UX Engineer** | UI 설계/와이어프레임/사용성 개선 | `/vrt`, `/test` |
| **Frontend Dev** | Next.js/React 개발, Zustand 상태 관리 | `/test frontend`, `/review frontend`, `/vrt` |
| **Backend Dev** | FastAPI 개발, 서비스 로직, 스토리지 | `/test backend`, `/review backend`, `/sd-status`, `/db` |
| **DBA** | DB 설계, Alembic 마이그레이션, 쿼리 최적화 | `/db`, `/test backend` |
| **Security Engineer** | 보안 취약점 분석, 인증/인가, 시크릿 관리 | `/review`, `/test` |

### Prompt Engineer 역할 상세
**핵심 원칙**: "프롬프트 기준 정확한 장면 생성"이 최우선 목표. 수동적 대응이 아닌 **적극적 제안**으로 품질을 선제적으로 개선합니다.

**책임**:
1. **위험 태그 모니터링**: Danbooru에 없는 태그(medium shot 등) 발견 시 즉시 지적 및 대체 제안
2. **프롬프트 품질 분석**: Match Rate 낮은 프롬프트 패턴 분석 및 개선안 제시
3. **Gemini 템플릿 개선**: 템플릿 예시가 부적절하면 Danbooru 검증된 태그로 교체 제안
4. **성공 조합 추출**: 과거 성공 케이스 분석 → 재사용 가능한 태그 조합 추천
5. **자동화 제안**: 반복되는 품질 문제 발견 시 자동 검증/수정 시스템 구축 제안

**적극적 개입 시점**:
- Gemini가 생성한 프롬프트에 위험 태그 발견 시
- Match Rate < 70% 씬 발견 시
- 동일한 태그 조합이 반복 실패할 때
- 새로운 캐릭터/스타일 추가 시 프롬프트 최적화 필요 시
- Danbooru/Civitai에서 더 나은 대안 태그를 발견했을 때

**금지 사항**:
- 문제 발견 후 사용자 지시 대기 (즉시 제안 필수)
- "괜찮을 것 같습니다" 같은 모호한 답변
- 데이터 없는 추측성 제안

## Commands

| Command | 역할 |
|---------|------|
| `/roadmap` | 로드맵 조회/업데이트/기능 목록 |
| `/test` | 테스트 실행 (전체/backend/frontend/vrt/e2e) |
| `/review` | 코드 리뷰 (lint, 품질, 아키텍처, 테스트 커버리지) |
| `/vrt` | Visual Regression Test 실행 |
| `/sd-status` | SD WebUI 상태 확인 |
| `/prompt-validate` | 프롬프트 문법 검증 |
| `/pose` | 포즈 에셋 분석/동기화 |
| `/db` | DB 마이그레이션 상태/생성/적용/롤백 |
| `/docs` | 문서 구조 조회/정합성 체크/크기 점검 |

> Agents/Commands 관리 규칙은 `docs/guides/CONTRIBUTING.md` 참조

## Hooks (자동화)

| Event | Hook | 동작 |
|-------|------|------|
| `PostToolUse` | `auto-lint.sh` | Edit/Write 후 자동 린트 (ruff → `.py`, prettier → `.ts/.tsx`) |

설정: `.claude/settings.json` / 스크립트: `.claude/hooks/auto-lint.sh`

## Workflow Rules (에이전트 자동 워크플로우)

| 트리거 | 자동 액션 | 설명 |
|--------|----------|------|
| 구현 완료 | Tech Lead 코드 리뷰 | 코드 변경 구현 후, 커밋 전에 자동으로 Tech Lead 에이전트가 리뷰 수행 |

**구현 → 리뷰 → 수정 자동 파이프라인**:
1. 코드 변경(Edit/Write) + 빌드/린트 통과
2. Tech Lead 리뷰 자동 실행 (사용자 보고 전)
3. WARNING/BLOCKER 이슈 발견 시 **즉시 자동 수정** 후 재빌드 확인
4. 최종 결과(변경 요약 + 리뷰 통과)를 사용자에게 보고
- 단, 단순 설정 변경(CLAUDE.md, config 수정 등)이나 문서만 수정한 경우는 리뷰를 생략한다.

## 용어 정의 (Terminology)

### Scene Text vs Caption (2026-01-31 변경)

**혼란 방지를 위한 명확한 용어 구분:**

| 용어 | 설명 | 위치 | 예시 |
|------|------|------|------|
| **Scene Text** | 씬의 스크립트 텍스트 (영상 위 오버레이) | Full: 영상 위 하단<br>Post: 이미지 위 영역 | "처음 칼을 잡았을 때,<br>너무 무서웠어" |
| **Caption** | 게시물 메타데이터 (좋아요, 시간 등) | Post: 카드 하단 | "좋아요 6만개<br>15분 전" |

**변경 사항:**
- `subtitles` → `scene_text` (네이밍 혼란 해소)
- `include_subtitles` → `include_scene_text`
- `subtitle_font` → `scene_text_font`
- `subtitleFont` → `sceneTextFont` (Frontend)
- `DEFAULT_SUBTITLE_FONT` → `DEFAULT_SCENE_TEXT_FONT` (Frontend 상수)
- `SUBTITLE_*` → `SCENE_TEXT_*` (Backend 상수)

**후방 호환성:**
- 기존 `include_subtitles` 필드명은 별칭(alias)으로 작동
- 기존 `subtitle_font` 필드명은 별칭(alias)으로 작동
- Frontend: 마이그레이션 로직에서 `subtitleFont` → `sceneTextFont` 자동 변환
- 기존 코드 수정 없이 동작하지만, 신규 코드는 `scene_text` 사용 권장

