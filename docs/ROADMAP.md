# Shorts Factory Master Roadmap (Strategic Fidelity Guard)

이 로드맵은 **안정성 → 리팩토링 → 안정성 → 신규 개발** 사이클을 따릅니다.
리팩토링 및 기능 추가 시 **영상 품질의 100% 일관성(Zero Variance)**을 유지하는 것을 최우선 목표로 합니다.

---

## 📦 Phase 1-4: Foundation & Refactoring - **ARCHIVED**

완료된 주요 성과:
- **Phase 1**: 기본 기능 구현 (FastAPI + Next.js + FFmpeg + WD14/Gemini 검증)
- **Phase 2**: VRT 안정성 기반 구축 (Golden Master + SSIM 95% 검증)
- **Phase 3**: Backend/Frontend 리팩토링
  - Backend: `logic.py` 2,300줄 → 279줄 (88% 감소), 8개 서비스 모듈 추출
  - Frontend: `page.tsx` 4,222줄 → 1,832줄 (57% 감소), 20개 컴포넌트 추출
- **Phase 4**: 안정성 검증 완료 (VRT 36/36 통과, PRD DoD 4개 항목 충족)

> 상세 이력: `git log --oneline docs/ROADMAP.md` 참조

---

## 🚀 Phase 5: 신규 개발 (High-End Production)
검증된 안정적인 기반 위에서 새로운 기능을 추가합니다.

### 5-1. 운영 효율화
| 작업 | 설명 | 상태 |
|------|------|------|
| Resume/Checkpoint | 중단된 작업 이어하기 | [x] |
| Storage Cleanup | outputs/ 자동 정리 로직 | [x] |
| Project DB (PostgreSQL) | 프로젝트 설정 및 히스토리 관리 (Phase 6-1 통합) | [x] |

### 5-1-1. Security & Infrastructure (Hardcoding Removal)
| 작업 | 설명 | 상태 |
|------|------|------|
| **Secure Config** | `DATABASE_URL` 등 민감정보 .env 이동 | [x] |
| **Dynamic URLs** | API/SD URL 및 경로 하드코딩 제거 및 중앙화 | [x] |
| **Logic Sync** | 프론트/백엔드 로직 중복 제거 (Priority 중앙화) | [x] |
| **Frontend Config** | `next.config.ts` IP 등 하드코딩 제거 | [x] |

### 5-2. 영상 품질 강화
| 작업 | 설명 | 상태 |
|------|------|------|
| Pixel-based Subtitle Wrapping | 폰트 기반 자막 줄바꿈 및 동적 크기 조절 | [x] |
| Professional Audio Ducking | 내레이션-BGM 볼륨 자동 조절 (sidechaincompress) | [x] |
| Ken Burns Effect | 정지 이미지에 줌/팬 효과 | [ ] |
| Character Consistency | → Phase 6 (LoRA 기반) → Phase 7 (IP-Adapter) | [-] |

### 5-3. 콘텐츠 확장
| 작업 | 설명 | 상태 |
|------|------|------|
| Preset System | 구조별 템플릿 및 샘플 토픽 시스템 | [x] |
| Sample Topics UI | Structure별 샘플 토픽 선택 UI | [x] |
| Japanese Language Course | 일본어 강좌 전용 템플릿 | [x] |
| Math Lesson Course | 초/중/고 수학 공식 강좌 템플릿 | [x] |

### 5-4. 확장 기능 (v1.x Backlog)
| 작업 | 설명 | 상태 |
|------|------|------|
| VEO Clip | Video Generation 통합 | [ ] |
| 정량적 품질 지표 | Match Rate 자동화 | [ ] |

### 5-5. UI/UX 개선
| 작업 | 설명 | 상태 |
|------|------|------|
| SetupPanel 제거 | 간소화 진입점 제거, Custom Start로 통합 | [x] |
| SD 파라미터 Advanced 이동 | steps, cfg_scale 등 고급 설정화 | [x] |
| 간소화 진입점 재설계 | Phase 6 완료 후 Quick Start 재정의 | [ ] |

### 5-6. UI Polish (완성도 향상)
| 작업 | 설명 | 상태 |
|------|------|------|
| **Loading/Error UI** | 스피너, 프로그레스 바, 에러 메시지 디자인 개선 | [x] |
| Setup Wizard | 초기 설정 및 에셋 상태 확인 UI | [ ] |

### 5-7. Quality Assurance (Test Coverage)
**Goal**: Core Rule #9에 따라 테스트 커버리지 80% 달성.

| 작업 | 설명 | 상태 |
|------|------|------|
| **Backend API Test** | FastAPI 라우터 통합 테스트 (TestClient) | [x] |
| **Frontend Test Init** | Vitest + React Testing Library 환경 구축 | [x] |
| **Core Hooks Test** | `useAutopilot` 등 핵심 로직 테스트 작성 | [ ] |
| **CI Script** | 로컬 테스트 자동화 스크립트 (`./run_tests.sh`) | [ ] |

---

## 🎭 Phase 6: Character & Prompt System (v2.0)
다중 캐릭터 지원 및 프롬프트 빌더 시스템 구축.

**현재 사용 환경**:
- **Model**: `anythingV3_fp16.safetensors` (SD 1.5 애니메)
- **LoRA**: `eureka_v9`, `chibi-laugh`, `blindbox_v1_mix`, `mha_midoriya-10`
- **Negative Embeddings**: `verybadimagenegative_v1.3`, `easynegative`
- **Presets**: Eureka, Eureka Chibi, Eureka Blindbox, Chibi, Blindbox, Midoriya, Midoriya Chibi

### 6-1. Data Foundation - **COMPLETE**
| 작업 | 설명 | 상태 |
|------|------|------|
| DB 스키마 설정 | PostgreSQL + SQLAlchemy + Alembic | [x] |
| 태그 마이그레이션 | 262개 태그 (identity, clothing, scene, meta) | [x] |
| Backend CRUD API | /tags, /loras, /characters, /sd-models 엔드포인트 | [x] |

### 6-2. Studio Integration - **COMPLETE**
| 작업 | 설명 | 상태 |
|------|------|------|
| Character Preset UI | 드롭다운 → Identity + Clothing + LoRA + Negative 자동 적용 | [x] |
| Multi-LoRA 지원 | 캐릭터당 여러 LoRA 조합 (eureka + chibi) | [x] |
| Style Profile 통합 | Character Preset으로 단일화, UI 제거 | [x] |

**Character Preset 구조**:
```
Character Preset
├── Identity Tags (1girl, aqua_hair, purple_eyes, short_hair)
├── Clothing Tags (t-shirt, hairclip)
├── LoRAs[] (eureka_v9:1.0, chibi-laugh:0.6)
└── Recommended Negative (easynegative)
```

### 6-3. Scene Expression & Multi-Character (🟡 확장)

**8.x Gender System - ARCHIVED** (6개 완료):
Character gender 필드, LoRA gender_locked, Gender 기반 UI 잠금/필터링, Preview UI

**9.x Scene Expression System - ARCHIVED** (25개 완료):
- 9.1~9.5: DB 태그 통합, 포즈/표정/구도 확장, Gemini 템플릿, Scene Context Tags UI, 프롬프트 품질 검증
- 9.6 Prompt Sanity Check: LoRA 존재 검증, Positive-Negative 충돌 검출, 필수 태그 검증
- 9.7 Scene-Prompt Quality: 토큰 정렬, 태그 확장(+27), context_tags 7그룹, WD14 동의어 매핑(75-86%)
- 9.8 Prompt Composition: Mode A/B 분리, BREAK 토큰, 동적 LoRA weight, /prompt/compose API, Preview UI
- 상세: `docs/PROMPT_SPEC.md`, 통합 테스트 35개 (100% pass)

| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 10 | Multi-Character 지원 | A, B, C... 다중 캐릭터 구조 | [ ] |
| 11 | Scene Builder UI | 장면별 배경/시간/날씨 컨텍스트 태그 선택 | [ ] |
| 12 | Tag Autocomplete | Danbooru 스타일 태그 자동완성 | [ ] |

### 6-4. Advanced Features (🔵 고급)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 13 | Civitai 연동 | LoRA 메타데이터 자동 가져오기 (MCP 활용) | [x] |
| 14 | Visual Tag Browser | 태그별 예시 이미지 표시 | [ ] |
| 15 | Tag Usage Analytics | 사용 빈도, 성공/실패 패턴 추적 (기본 구현: 9.1.1) | [~] |
| 15.1 | Batch Tag Approval | confidence >= 0.7 태그 일괄 승인 (미리보기 + 선택적 승인) | [x] |
| 15.2 | **Tag Categorization V2** | SD Priority 기반 분류체계 개편 (24개 카테고리, environment 세분화) | [x] |
| 15.3 | **Tag Conflict/Requires Rules** | 태그 충돌(57쌍)/의존성(29개) 규칙 + 검증 API | [x] |
| 15.4 | **LoRA Trigger Sync** | LoRA trigger words → tags 테이블 자동 동기화 API | [x] |
| 15.5 | **Tag Gap Analysis & Expansion** | CATEGORY_PATTERNS→DB 동기화 (515→924개, +409) | [x] |
| 15.6 | **Quality Evaluation System** | Mode A/B 비교 검증 시스템 | [ ] |
| 15.6.1 | 표준 테스트 프롬프트 세트 | 장면 유형별 고정 프롬프트 | [ ] |
| 15.6.2 | evaluation_runs 테이블 | 결과 저장 스키마 | [ ] |
| 15.6.3 | /eval/run API | 테스트 실행 엔드포인트 | [ ] |
| 15.6.4 | /eval/results API | 결과 조회/비교 | [ ] |
| 15.6.5 | 대시보드 시각화 | Mode A vs B 차트 | [ ] |
| **15.7** | **Dynamic Tag Classification** | 하드코딩 제거, DB+Danbooru+LLM 하이브리드 분류 | [x] |
| 15.7.1 | classification_rules 테이블 | 패턴 규칙 DB화 (CATEGORY_PATTERNS 이관) | [x] |
| 15.7.2 | /tags/classify API | 배치 분류 엔드포인트 (DB→Rules fallback) | [x] |
| 15.7.3 | Danbooru API 연동 | 태그 카테고리 조회 (General 세분화용 LLM 호출) | [x] |
| 15.7.4 | Frontend 통합 | useTagClassifier 훅 + API 호출 (로컬 패턴 fallback) | [x] |
| 15.7.5 | 승인 워크플로우 | LLM 분류 결과 검토/승인 UI | [x] |
| 15.7.6 | WD14 피드백 루프 | 생성 이미지 태그 vs 프롬프트 태그 비교 → 분류 정확도 검증 | [ ] |
| 16 | Prompt History | 성공한 프롬프트 저장/재사용 | [ ] |
| 17 | Feedback Loop | WD14 기반 태그 효과성 피드백 (기본 구현: 9.1.1) | [~] |
| 18 | Profile Export/Import | Style Profile 공유 | [ ] |
| 19 | Character Builder UI | 조합형 캐릭터 생성 (Gender + Appearance + LoRA) | [ ] |
| 20 | Scene Clothing Override | 장면별 의상 변경 기능 | [ ] |

---

## 🔮 Phase 7: ControlNet & Pose Control (P0 품질)
포즈/표정 정확도 향상으로 장면묘사 품질 근본 해결.

**환경 확인 완료**:
- ControlNet v3 ✅
- OpenPose 모델 ✅
- Depth 모델 ✅
- IP-Adapter FaceID ✅

**7-1 완료 요약**:
- `services/controlnet.py`: 포즈 매핑 + API 빌더
- `routers/controlnet.py`: `/controlnet/status`, `/controlnet/poses` API
- Frontend: ControlNet 토글 + Weight 슬라이더 (SceneListHeader)
- 11개 포즈 참조 정의 (standing, waving, sitting, arms up 등)
- 프롬프트 → 포즈 자동 감지 (`detect_pose_from_prompt`)

### 7-1. ControlNet 기반 포즈 제어 (🟢 완료)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 7.1.1 | ControlNet 서비스 | `services/controlnet.py` 생성 | [x] |
| 7.1.2 | 포즈 참조 이미지 | 5개 기본 포즈 생성 (standing, waving, sitting 등) | [x] |
| 7.1.3 | 포즈 이미지 검증 | WD14로 포즈 품질 확인 (4/5 성공) | [x] |
| 7.1.4 | Router 추가 | `/controlnet/*` API 엔드포인트 | [x] |
| 7.1.5 | 씬 생성 통합 | 장면 태그 → 포즈 자동 선택 로직 | [x] |
| 7.1.6 | Frontend 옵션 | ControlNet 토글 + Weight 슬라이더 UI | [x] |
| 7.1.7 | 품질 테스트 | 67% 달성 (WD14 "waving" 미인식 한계) | [~] |

### 7-2. IP-Adapter (캐릭터 일관성) (🟢 완료)
| 작업 | 설명 | 상태 |
|------|------|------|
| IP-Adapter 지원 | 참조 이미지 기반 캐릭터 일관성 | [x] |
| LoRA + IP 조합 | LoRA 베이스 + IP-Adapter 포즈/표정 | [x] |
| Reference Image Manager | 참조 이미지 관리 API | [x] |
| Frontend UI | IP-Adapter 토글 + Reference 선택 + Weight | [x] |

**7-2 완료 요약**:
- Backend: `build_ip_adapter_args()`, `save/load_reference_image()` 함수
- API: `/ip-adapter/status`, `/ip-adapter/references`, `/ip-adapter/reference` CRUD
- Frontend: IP-Adapter 체크박스 + Reference 드롭다운 + Weight 슬라이더
- ControlNet + IP-Adapter 동시 사용 가능 (포즈 + 얼굴 일관성)

### 7-3. LoRA 캘리브레이션 시스템 (🟢 완료)
| 작업 | 설명 | 상태 |
|------|------|------|
| 캘리브레이션 서비스 | 최적 LoRA weight 자동 탐색 (0.5~1.0) | [x] |
| WD14 기반 평가 | 프롬프트 표현력 점수 측정 | [x] |
| DB 저장 | optimal_weight, calibration_score 필드 | [x] |
| 자동 적용 | 캐릭터 선택 시 최적 weight 자동 적용 | [x] |
| /manage UI | LoRA 목록에 캘리브레이션 정보 표시 | [x] |

**7-3 완료 요약**:
- `services/lora_calibration.py`: 캘리브레이션 로직
- `services/prompt.py`: `apply_optimal_lora_weights()` 자동 교체
- `logic.py`: 이미지 생성 시 DB에서 optimal_weight 조회 및 적용
- `routers/characters.py`: 캐릭터 API에서 optimal_weight 우선 반환 (2026-01-25 수정)
- 4개 LoRA 캘리브레이션 완료 (eureka, chibi, blindbox, midoriya → 모두 0.5 최적)
- UI에서 캐릭터 선택 시 캘리브레이션된 weight 자동 표시

### 7-4. 다중 캐릭터 렌더링 실험 (🟡 실험 완료)
| 작업 | 설명 | 상태 |
|------|------|------|
| 대화 장면 테스트 | 분리 생성 + 합성 방식 검증 | [x] |
| 상호작용 장면 테스트 | 포옹/손잡기 - 단일 생성 vs 분리 합성 | [x] |
| Reference-only 테스트 | 캐릭터 일관성 유지 방법 검증 | [x] |
| 치비 포즈 테스트 | LoRA + Reference-only 조합 | [x] |

**7-4 실험 결론** (상세: `docs/reports/CHARACTER_RENDERING_REPORT.md`):
- **상호작용 장면** → ControlNet 단일 생성 권장
- **대화 장면** → 분리 생성 + 합성 권장
- **캐릭터 일관성** → Reference-only (weight 0.5, guidance_end 0.8) 권장

---

## 📋 Development Cycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   안정성      │ ──▶ │   리팩토링    │ ──▶ │   안정성      │ ──▶ │   신규 개발   │
│   구축       │     │   (VRT 통과)  │     │   검증       │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                     ◀──────────────────────────────────────────────────
                                    (반복)
```

---

## 🤖 Agent Evolution Guidelines

현재 에이전트 구성이 충분하지 않은 시점을 정의합니다.

### Test Engineer Agent 추가 시점

**트리거 조건** (하나 이상 충족 시 추가 검토):
| 조건 | 설명 | 현재 상태 |
|------|------|----------|
| Unit Test 구축 | Backend/Frontend unit test 30개 이상 | ❌ 미구축 |
| E2E Test 구축 | Playwright E2E 시나리오 10개 이상 | ❌ 미구축 |
| CI/CD 도입 | GitHub Actions 테스트 파이프라인 | ❌ 미구축 |
| 테스트 복잡도 | 테스트 파일 총 1,000줄 초과 | ❌ 해당없음 |

**역할 정의** (추가 시):
- 테스트 코드 작성/유지보수
- 테스트 커버리지 관리 (목표: 80%+)
- CI/CD 파이프라인 테스트 설정
- 테스트 관련 commands 관리 (`/test`, `/coverage`)

**현재 대안**:
- VRT: `/vrt` command + qa-validator
- 이미지 품질: qa-validator
- 수동 테스트: 일반 개발 과정에서 처리

### 기타 Agent 추가 고려

| Agent | 트리거 조건 | 현재 필요성 |
|-------|------------|------------|
| **DevOps Engineer** | Docker/K8s 배포, 모니터링 시스템 구축 시 | ❌ 불필요 |
| **Security Auditor** | 외부 사용자 접근, 인증 시스템 도입 시 | ❌ 불필요 |
| **Data Engineer** | 대용량 데이터 파이프라인, 분석 시스템 구축 시 | ❌ 불필요 |

### Claude Squad 도입 시점

**Claude Squad**: 여러 Claude Code 인스턴스를 병렬로 관리하는 도구 (tmux + git worktree 기반)

**트리거 조건** (하나 이상 충족 시 도입 검토):
| 조건 | 설명 | 현재 상태 |
|------|------|----------|
| 팀 확장 | 2명 이상 동시 개발 | ❌ 솔로 |
| 독립 작업 | Backend/Frontend 완전 분리 작업 필요 | ❌ 순차 진행 |
| 대규모 리팩토링 | 10+ 파일 동시 수정 필요 | ❌ 해당없음 |
| 긴급 핫픽스 | 메인 작업 중 별도 브랜치 작업 빈번 | ❌ 해당없음 |
| Phase 병렬화 | 의존성 없는 Phase 동시 진행 | ❌ 순차 의존성 |

**도입 시 이점**:
- 여러 작업 병렬 실행 (대기 시간 감소)
- git worktree로 브랜치 충돌 방지
- 백그라운드 자동 완료 (yolo 모드)

**현재 대안**:
- Sub Agents: 전문성 분리 (단일 세션 내)
- 순차 작업: 의존성 있는 Phase는 순서대로

**설치** (도입 시):
```bash
brew install claude-squad  # 명령어: cs
```

**참조**: https://github.com/smtg-ai/claude-squad

---

**Core Mandate**: "No changes in output without explicit intention."
(의도하지 않은 결과물의 변화는 허용하지 않는다.)

---

## 📊 Current Status

**Last Updated**: 2026-01-26 (09:30)

| Phase | 상태 | 진행률 | 비고 |
|-------|------|--------|------|
| 1-4 | ARCHIVED | 100% | |
| 5 | IN PROGRESS | 73% | Ken Burns 잔여 |
| 6-1 | COMPLETE | 100% | |
| 6-2 | COMPLETE | 100% | |
| 6-3 | IN PROGRESS | 90% | 8.x+9.x 아카이브, 10/11/12 잔여 |
| 6-4 | IN PROGRESS | 80% | 15.7 완료 |
| 7-1 | COMPLETE | 100% | |
| 7-2 | COMPLETE | 100% | |
| 7-3 | COMPLETE | 100% | |
| 7-4 | EXPERIMENT DONE | 100% | |

**7-3 LoRA 캘리브레이션 완료 (2026-01-25)**:
- 4개 LoRA 캘리브레이션: eureka, chibi, blindbox, midoriya
- 최적 weight: 모두 0.5 (프롬프트 표현력 유지)
- 캐릭터 선택 시 자동 적용 구현
- /manage 페이지에 캘리브레이션 정보 표시

**7-4 다중 캐릭터 실험 완료 (2026-01-25)**:
- 상호작용 장면: ControlNet 단일 생성 권장
- 대화 장면: 분리 합성 권장
- 캐릭터 일관성: Reference-only 효과적

**6-4.15.2 Tag Categorization V2 완료 (2026-01-25)**:
- SD Priority 기반 24개 카테고리 정의 (quality→subject→appearance→clothing→expression→...→style)
- environment 그룹 세분화: location_indoor, location_outdoor, background_type, time_weather, lighting
- DB 481개 태그 priority 업데이트 (1=quality ~ 16=style)
- Frontend TOKEN_PRIORITY 수정: Quality Priority 8→1로 이동
- CATEGORY_PATTERNS 확장: 누락된 quality, subject, body_feature 등 추가

**6-4.15.3 Tag Rules 완료 (2026-01-25)**:
- 태그 충돌 규칙 57쌍 (hair length, time, weather, camera, pose 등)
- 태그 의존성 규칙 29개 (twintails→long hair, cat ears→animal ears 등)
- 검증 API: POST /keywords/validate, GET /keywords/rules
- body_feature 카테고리 26개 태그 추가 (animal ears, horns, wings, tail 등)

**6-4.15.4 LoRA Trigger Sync 완료 (2026-01-25)**:
- LoRA trigger words → tags 테이블 자동 동기화
- 패턴 기반 자동 분류: *eyes→eye_color, *hair→hair_color/hair_style, 기본→identity
- API: POST /keywords/sync-lora-triggers
- 4개 LoRA에서 11개 트리거 워드 동기화 (midoriya izuku, eureka 등)
- 하드코딩 제거: CATEGORY_PATTERNS에서 캐릭터명 패턴 삭제

**6-4.15.5 Tag Gap Analysis & Expansion 완료 (2026-01-25)**:
- CATEGORY_PATTERNS → DB 동기화 API 추가 (POST /keywords/sync-category-patterns)
- 총 태그: 515개 → 952개 (+437개 확장, 최신 동기화)
- 주요 확장 카테고리:
  - location_indoor: 13→31개, location_outdoor: 10→38개
  - lighting: 12→29개, mood: 14→33개
  - action: 55→64개 (holding X 패턴 추가)
  - time_weather: 38→46개 (환경 효과 추가)
- 중복 체크 로직 개선 (batch 처리 + 사전 필터링)

**다음 우선순위** (2026-01-25 갱신):

| 순위 | 작업 | Phase | 가치 | 난이도 | 이유 |
|------|------|-------|------|--------|------|
| 1 | **Multi-Character 구현** | 6-3.10 | 높음 | 중 | 9.8 완료, 콘텐츠 다양성 핵심 |
| 2 | **Ken Burns Effect** | 5-2 | 높음 | 낮음 | FFmpeg 기반, 시각적 품질 향상 |
| 3 | **Scene Builder UI** | 6-3.11 | 중 | 중 | 924개 태그 활용 UX |
| 4 | **Tag Autocomplete** | 6-3.12 | 중 | 낮음 | 태그 입력 효율성 |
| 5 | **Quality Evaluation** | 6-4.15.6 | 중 | 중 | Mode A/B 품질 검증 (Backlog) |

**Phase 6 태그 시스템 현황**: 55% -> 75% (15.2~15.5 완료로 대폭 진전)
- 태그 952개 (515개에서 +437 확장, 최신 동기화)
- 충돌 규칙 57쌍, 의존성 규칙 29개 구축
- LoRA Trigger 자동 동기화 완료
- Action 태그 64개 (holding X 패턴), Time/Weather 46개 (환경 효과)

**9.8 Prompt Composition System 완료 (2026-01-25)**:
- 문제: LoRA 사용 시 장면 표현(pose, action, camera)이 LoRA 학습 편향에 의해 무시됨
- 해결: Mode A (Standard) / Mode B (LoRA) 분리
  - Mode A: 표준 순서 (캐릭터 → 장면), LoRA 미사용 또는 스타일 LoRA만
  - Mode B: 장면 우선 순서, LoRA weight 동적 조절, BREAK 활용
- **완료된 작업** (13/13):
  - 9.8.0: DB Schema (characters.prompt_mode)
  - 9.8.1: Character Mode 자동 감지
  - 9.8.2: get_token_category() + CATEGORY_PATTERNS 연동
  - 9.8.2.1: BREAK Token 지원
  - 9.8.3: detect_scene_complexity() (simple/moderate/complex)
  - 9.8.4: calculate_lora_weight() (타입+복잡도 기반)
  - 9.8.5: filter_conflicting_tokens() + 트리거 중복 제거
  - 9.8.5.1: ensure_quality_tags()
  - 9.8.6: sort_prompt_tokens() (Mode별 정렬)
  - 9.8.7: POST /prompt/compose API
  - 9.8.8: ComposedPromptPreview.tsx (카테고리별 그룹 + Toggle)
  - 9.8.9: 통합 테스트 35개 (100% pass)
- 상세 스펙: `docs/specs/PROMPT_SPEC.md` 참조

**9.8 버그 수정 (2026-01-25 17:15)**:
- **buildScenePrompt 통합**: Frontend에서 단순 연결 → `/prompt/compose` API 호출로 수정
- **BREAK 위치 수정**: priority 기반 → 마지막 clothing 토큰 후 삽입 (position 기반)
- **Trigger 위치 수정**: 프롬프트 끝 → LoRA 문자열 직전으로 이동
- **태그 분류 수정**:
  - `holding bag` → ACTION (CLOTHING에서 수정)
  - `falling leaves` → TIME_WEATHER (ACTION에서 수정)
  - Backend: CATEGORY_PATTERNS에 "holding X" 패턴(55개), 환경 효과(38개) 추가
  - Frontend: getTokenCategory()에 clothing 패턴, 환경 효과 패턴 추가

**15.7 Dynamic Tag Classification (2026-01-25 21:00)**:
- 15.7.1~15.7.5 완료: classification_rules 테이블, /tags/classify API, Danbooru API 연동, Frontend 통합, 승인 워크플로우
- TagClassifier: DB Cache → Pattern Rules → Danbooru API → Unknown 순서로 분류
- `backend/services/danbooru.py`: Danbooru API 서비스 (카테고리 매핑: artist→style, character→identity, meta→quality)
- `backend/services/tag_classifier.py`: 하이브리드 분류 로직
- `frontend/app/hooks/useTagClassifier.ts`: API 기반 분류 + 세션 캐싱
- Danbooru API 연결 문제(TLS) 시 graceful fallback으로 unknown 반환
- 15.7.5 승인 워크플로우: `/tags/pending` API, `/tags/approve-classification` API, /manage Tags 탭에 Pending Classifications UI

**9.8 버그 수정 V (2026-01-26)**:
- **LoRA 중복 제거**: `_deduplicate_loras()` 함수 추가 - 동일 LoRA 다른 weight 시 마지막 weight 유지
- **BREAK 정규화**: `_normalize_break_tokens()` 함수 추가 - 소문자 `break` → `BREAK` 변환, 중복 제거
- **Camera 충돌**: `medium shot` 패턴 추가, 동일 카테고리 첫 번째만 유지
- **중복 BREAK 방지**: 사용자 입력 BREAK 있으면 자동 삽입 스킵
- **테스트 강화**: 38개 → 54개 (+16개)
  - TestLoRADeduplication (5), TestBreakNormalization (4), TestCameraConflict (4), TestFullCompositionBugFixes (3)

**9.8 버그 수정 IV (2026-01-25 23:00)**:
- **COMPOSED PREVIEW 자동 업데이트**: 토큰 변경 시 자동으로 `/prompt/compose` API 호출
  - 300ms 디바운스로 과도한 API 호출 방지
  - 상태 표시: "Composing...", "Filtered", "Raw"
  - 버튼 텍스트: 결과 있으면 "Refresh", 없으면 "Compose"
  - 이제 사용자가 필터링된 결과를 실시간으로 확인 가능

**9.8 버그 수정 III (2026-01-25 22:30)**:
- **Debug 탭 프롬프트 불일치**: Debug 탭이 `/prompt/compose` API를 사용하지 않아 충돌 필터링, Quality 태그 추가, 트리거 중복 제거 미적용
  - 문제: `buildPositivePrompt` (동기, 단순 연결) vs `buildScenePrompt` (비동기, /prompt/compose API)
  - 해결: Debug 탭에서 `buildScenePrompt` 사용하도록 수정
  - SceneCard에 `buildScenePrompt` prop 추가, DebugTabContent async 지원 + 로딩 상태 추가
- **테스트 추가**: `test_ocean_with_indoor_locations` - ocean + library/room/street/cafe 충돌 케이스

**9.8 버그 수정 II (2026-01-25 19:30)**:
- **Trigger 워드 중복 수정**: `compose_prompt_tokens`에서 trigger words 추출 시 중복 발생 → `extracted_triggers_seen` 집합으로 dedup
- **동일 카테고리 충돌 필터링**: `CONFLICTING_CATEGORY_PAIRS`에 same-category 규칙 추가 (location_indoor, location_outdoor, camera 등)
- **LoRA Type 수정**: `mha_midoriya-10`의 `lora_type`이 "style"로 잘못 설정되어 Mode B 미작동 → "character"로 DB 업데이트
- **LoRA 중복 제거 수정**: `normalize_prompt_tokens`에서 weight 포함 전체 태그로 비교 → LoRA 이름만으로 dedup (마지막 weight 유지)
- **결과**: Mode B 정상 활성화 (BREAK 토큰, 트리거 배치, LoRA 순서 모두 정상), 중복 LoRA 제거 완료
- **프론트엔드 태그 분류 확장**: `getTokenCategory()`에 누락된 패턴 추가
  - quality: "anime coloring", "official art"
  - location: "bed", "chair", "sofa", "room", "library", "cafe" 등 30+개
  - time_weather: "starry", "sky", "clouds", "moon", "stars" 등
  - mood: "comfortable", "cozy", "warm", "lonely", "gloomy" 등

---

## 15.7 Dynamic Tag Classification System

**목표**: 하드코딩 기반 태그 분류 완전 제거, 동적 분류 시스템 구축

### 아키텍처
```
태그 입력 → DB 캐시 → Danbooru API → LLM Fallback → DB 저장
                              ↓
                    General(0) → LLM 세분화
                    Character(4) → identity
                    Artist(1) → style
                    Meta(5) → quality
```

### DB 스키마
```sql
-- 분류 규칙 (패턴 기반, 하드코딩 대체)
CREATE TABLE classification_rules (
    id SERIAL PRIMARY KEY,
    rule_type VARCHAR(20) NOT NULL,  -- 'suffix', 'prefix', 'contains', 'exact'
    pattern VARCHAR(100) NOT NULL,
    target_group VARCHAR(50) NOT NULL,
    priority INT DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- tags 테이블 확장
ALTER TABLE tags ADD COLUMN classification_source VARCHAR(20) DEFAULT 'pattern';
ALTER TABLE tags ADD COLUMN classification_confidence FLOAT DEFAULT 1.0;
```

### API
- `POST /tags/classify` - 배치 분류 (최대 50개)
- `GET /tags/pending` - 승인 대기 목록
- `POST /tags/approve` - 분류 승인

### 구현 순서
1. classification_rules 테이블 + CATEGORY_PATTERNS 이관
2. /tags/classify API (DB → Rule → Danbooru → LLM)
3. Frontend getTokenCategory() → API 호출로 교체
4. 승인 워크플로우 UI
