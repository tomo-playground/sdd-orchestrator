# 프로젝트: Shorts Producer (V3)

AI 기반 쇼츠 영상 자동화 워크스페이스. Gemini (스토리보드) + Stable Diffusion (이미지) + FFmpeg (렌더링).

## 아키텍처

| 레이어 | 기술 | 핵심 |
|--------|------|------|
| Backend | FastAPI | `routers/` (API), `services/` (로직) |
| Frontend | Next.js 14 | `app/page.tsx` (스튜디오), `hooks/useAutopilot.ts` |
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

## 문서 참조
- **작업 선택**: `docs/ROADMAP.md`
- **제품 스펙**: `docs/PRD.md`
- **API 명세**: `docs/specs/API_SPEC.md`
- **DB 스키마**: `docs/specs/DB_SCHEMA.md`
- **프롬프트 설계**: `docs/specs/PROMPT_SPEC.md`
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
- **로직 기준**: 태그 우선순위 등의 비즈니스 로직은 **Backend**(`backend/services/keywords/` 패키지)가 Single Source of Truth입니다.
- **태그 규칙**: 충돌(`tag_rules`), 별칭(`tag_aliases`), 필터(`tag_filters`) 모두 **DB 테이블**에서 관리. 코드 하드코딩 금지.
- **런타임 캐시**: `TagCategoryCache`, `TagAliasCache`, `TagRuleCache`, `LoRATriggerCache` — startup 시 DB에서 로드, 변경 시 `/admin/refresh-caches`.

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
| **PM Agent** | 로드맵/우선순위/문서 관리 | `/roadmap`, `/vrt` |
| **Prompt Engineer** | SD 프롬프트 최적화 + **적극적 품질 제안** | `/prompt-validate`, `/sd-status` |
| **Storyboard Writer** | 스토리보드/스크립트 작성 | `/roadmap` |
| **QA Validator** | 품질 체크/TROUBLESHOOTING 관리 | `/vrt`, `/sd-status`, `/prompt-validate` |
| **FFmpeg Expert** | 렌더링/비디오 효과 | `/vrt`, `/roadmap` |

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
| `/roadmap` | 로드맵 조회/업데이트 |
| `/vrt` | Visual Regression Test 실행 |
| `/sd-status` | SD WebUI 상태 확인 |
| `/prompt-validate` | 프롬프트 문법 검증 |

> Agents/Commands 관리 규칙은 `docs/guides/CONTRIBUTING.md` 참조
