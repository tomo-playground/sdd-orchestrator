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
| **Smart AutoRun** | Pre-flight 검증 + 선택적 실행 | [x] |

#### 5-1-2. Smart AutoRun System (🟢 완료 - 테스트 검증됨)
**목표**: 오토런 실행 전 사전 점검 및 필요한 단계만 선택적 실행

| # | 작업 | 설명 | 상태 |
|---|------|------|------|
| 1 | `runPreflight()` 함수 | 설정 검증 + 상태 분석 로직 | [x] |
| 2 | `PreflightModal` 컴포넌트 | 3섹션 UI (설정/파라미터/단계) | [x] |
| 3 | 필수/권장 검증 로직 | Topic, Character 등 필수 체크 | [x] |
| 4 | `useAutopilot` 확장 | 선택적 단계 실행 지원 | [x] |
| 5 | 진행 UI 개선 | 건너뜀/완료 상태 표시 | [x] |
| 6 | 브라우저 테스트 | Playwright 기반 E2E 검증 | [x] |

**Pre-flight 검증 항목**:
- 필수: Topic, Character
- 권장: Voice, BGM, ControlNet
- 정보: SD 파라미터, IP-Adapter

**실행 단계 최적화**:
- Storyboard: 씬 존재 시 건너뛰기
- Images: 이미지 없는 씬만 생성
- Validate: 미검증 이미지만 검증
- Render: 콘텐츠 변경 시만 재렌더

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
| Ken Burns Effect | 정지 이미지에 줌/팬 효과 (10개 프리셋) | [x] |
| **Random BGM** | `bgm_file: "random"` → Backend에서 랜덤 선택 | [x] |
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
| **Render UX 개선** | 컴팩트 레이아웃 토글 + 단일 Render 버튼, Video+Audio→Media Settings 통합 | [x] |

### 5-6. UI Polish (완성도 향상)
| 작업 | 설명 | 상태 |
|------|------|------|
| **Loading/Error UI** | 스피너, 프로그레스 바, 에러 메시지 디자인 개선 | [x] |
| **Character Image Modal** | Manage > Characters 섬네일 클릭 시 확대 모달 | [x] |
| Setup Wizard | 초기 설정 및 에셋 상태 확인 UI | [ ] |

### 5-7. Quality Assurance (Test Coverage)
**Goal**: Core Rule #9, #10 (TDD)에 따라 테스트 커버리지 80% 달성.

| 작업 | 설명 | 상태 |
|------|------|------|
| **Backend API Test** | FastAPI 라우터 통합 테스트 (TestClient) | [x] |
| **Frontend Test Init** | Vitest + React Testing Library + Playwright VRT 환경 구축 | [x] |
| **Ken Burns Unit Test** | `services/motion.py` 27개 테스트 (TDD) | [x] |
| **Core Hooks Test** | `useAutopilot` 27개 테스트 (~95% 커버리지) | [x] |
| **CI Script** | 로컬 테스트 자동화 스크립트 (`./run_tests.sh`) | [x] |

**현재 테스트 현황** (2026-01-27):
- Backend: 286 passed, 5 skipped (validation 18개 추가)
- Frontend: 60 passed (validation 30개, useAutopilot 27개, LoadingSpinner 3개)
- **총 346개 테스트**
- 주요 테스트: VRT (36개), API (키워드/프리셋/IP-Adapter), 프롬프트 품질, Ken Burns (27개), BGM (9개)
- IP-Adapter 테스트 (16개): CLIP 모델 선택, Reference 이미지 로드, 페이로드 구성, 상수 검증
- **useAutopilot 테스트** (27개): 상태 관리, 로그, 취소/재개, 체크포인트, 진행률 계산, 통합 플로우
- **Validation 테스트** (48개):
  - Frontend (30개): 씬 검증, 수정 제안, 프롬프트 품질 체크
  - Backend (18개): 태그 비교, match rate 계산, skip 로직

---

## 🎭 Phase 6: Character & Prompt System (v2.0)
다중 캐릭터 지원 및 프롬프트 빌더 시스템 구축.

**현재 사용 환경**:
- **Model**: `animagine-xl.safetensors` (SDXL anime)
- **LoRA**: `eureka_v9`, `chibi-laugh`
- **Negative Embeddings**: `verybadimagenegative_v1.3`, `easynegative`
- **Presets**: 9종 (Generic Girl/Boy, Eureka, Midoriya, Chibi, Blindbox 계열)

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

### 6-3. Scene Expression & Multi-Character (🟡 확장)

**8.x Gender System - ARCHIVED** (6개 완료):
Character gender 필드, LoRA gender_locked, Gender 기반 UI 잠금/필터링, Preview UI

**9.x Scene Expression System - ARCHIVED** (25개 완료):
- DB 태그 통합, 포즈/표정/구도 확장, Gemini 템플릿, Prompt Quality
- Prompt Sanity Check, Prompt Composition Mode A/B

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
| 15.6 | **Quality Evaluation System** | Mode A/B 비교 검증 시스템 | [x] |
| 15.6.1 | 표준 테스트 프롬프트 세트 | 6개 테스트 시나리오 정의 | [x] |
| 15.6.2 | evaluation_runs 테이블 | 결과 저장 스키마 + 마이그레이션 | [x] |
| 15.6.3 | /eval/run API | 테스트 실행 엔드포인트 | [x] |
| 15.6.4 | /eval/results, /eval/summary API | 결과 조회/비교 | [x] |
| 15.6.5 | 대시보드 시각화 | /manage Eval 탭 (Mode A vs B 차트) | [x] |
| **15.7** | **Dynamic Tag Classification** | 하드코딩 제거, DB+Danbooru+LLM 하이브리드 분류 | [x] |
| 15.7.1 | classification_rules 테이블 | 패턴 규칙 DB화 (CATEGORY_PATTERNS 이관) | [x] |
| 15.7.2 | /tags/classify API | 배치 분류 엔드포인트 (DB→Rules fallback) | [x] |
| 15.7.3 | Danbooru API 연동 | 태그 카테고리 조회 (General 세분화용 LLM 호출) | [x] |
| 15.7.4 | Frontend 통합 | useTagClassifier 훅 + API 호출 (로컬 패턴 fallback) | [x] |
| 15.7.5 | 승인 워크플로우 | LLM 분류 결과 검토/승인 UI | [x] |
| 15.7.6 | WD14 피드백 루프 | 생성 이미지 태그 vs 프롬프트 태그 비교 → 분류 정확도 검증 | [x] |
| 15.7.7 | **카테고리 한국어 설명** | CATEGORY_DESCRIPTIONS 상수, UI 메타정보 표시 | [x] |
| 15.7.8 | **분류 테스트 케이스** | 109개 회귀 방지 테스트 (clothing, hair, camera 등) | [x] |
| 16 | Prompt History | 성공한 프롬프트 저장/재사용 | [x] |
| 16.1 | DB 모델 | `prompt_histories` 테이블 (JSONB: lora_settings, context_tags) | [x] |
| 16.2 | CRUD API | `/prompt-histories` 엔드포인트 (목록/상세/생성/수정/삭제) | [x] |
| 16.3 | 특수 API | toggle-favorite, apply (use_count++), update-score (WD14 연동) | [x] |
| 16.4 | /manage 탭 | Prompts 탭 UI (필터: 즐겨찾기/캐릭터/검색, 정렬: 최신/사용횟수/점수) | [x] |
| 16.5 | Save 버튼 | SceneCard에서 현재 프롬프트 저장 기능 | [x] |
| 16.6 | Apply 기능 | 저장된 프롬프트를 씬에 적용 (localStorage → 메인 페이지) | [x] |
| 16.7 | WD14 피드백 | 이미지 검증 시 match_rate 자동 업데이트 (avg_match_rate 누적) | [x] |
| 16.8 | Draft 영속성 | prompt_history_id 저장/복원 지원 | [x] |
| 17 | Feedback Loop | WD14 기반 태그 효과성 피드백 → **16.7에서 구현 완료** | [x] |
| 18 | Profile Export/Import | Style Profile 공유 | [ ] |
| 19 | Character Builder UI | 조합형 캐릭터 생성 (Gender + Appearance + LoRA) | [ ] |
| 20 | Scene Clothing Override | 장면별 의상 변경 기능 | [ ] |
| 21 | **Generation Log Analytics** | 이미지 생성 메타 로깅 → 충돌 규칙/품질 패턴 자동 발견 | [ ] |

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
| **Character Presets** | 캐릭터별 최적 IP-Adapter weight 자동 적용 | [x] |

**7-2 완료 요약**:
- Backend: `build_ip_adapter_args()`, `save/load_reference_image()` 함수
- API: `/ip-adapter/status`, `/ip-adapter/references`, `/ip-adapter/reference` CRUD
- Frontend: IP-Adapter 체크박스 + Reference 드롭다운 + Weight 슬라이더
- ControlNet + IP-Adapter 동시 사용 가능 (포즈 + 얼굴 일관성)
- **CLIP 모델 지원**: 애니메이션 캐릭터용 CLIP 기반 IP-Adapter (`ip-adapter-plus_sd15`)
- **디버깅 로그**: Frontend/Backend 양측에 IP-Adapter 상태 로그 추가
- **테스트 커버리지**: 16개 단위 테스트 (`tests/api/test_ip_adapter.py`)
- **Character Presets**: 캐릭터별 최적 weight/model 자동 적용 (`config.py`)

### 7-3. LoRA 캘리브레이션 시스템 (🟢 완료)
| 작업 | 설명 | 상태 |
|------|------|------|
| 캘리브레이션 서비스 | 최적 LoRA weight 자동 탐색 (0.5~1.0) | [x] |
| WD14 기반 평가 | 프롬프트 표현력 점수 측정 | [x] |
| DB 저장 | optimal_weight, calibration_score 필드 | [x] |
| 자동 적용 | 캐릭터 선택 시 최적 weight 자동 적용 | [x] |
| /manage UI | LoRA 목록에 캘리브레이션 정보 표시 | [x] |

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

**Last Updated**: 2026-01-28 (01:00)

| Phase | 상태 | 진행률 | 비고 |
|-------|------|--------|------|
| 1-4 | ARCHIVED | 100% | |
| 5 | IN PROGRESS | 88% | VEO, 품질지표, Setup Wizard 잔여 |
| 6-1 | COMPLETE | 100% | |
| 6-2 | COMPLETE | 100% | |
| 6-3 | IN PROGRESS | 90% | 8.x+9.x 아카이브, 10/11/12 잔여 |
| 6-4 | COMPLETE | 100% | 15.2~15.7 + 15.6 완료 |
| 7-1 | COMPLETE | 100% | |
| 7-2 | COMPLETE | 100% | IP-Adapter CLIP 모델 지원 |
| 7-3 | COMPLETE | 100% | |
| 7-4 | EXPERIMENT DONE | 100% | |

**Chibi 스타일 & Composition 안전성 수정 (2026-01-28 01:00)**:
- **문제 1**: Chibi 캐릭터 이미지가 치비 스타일이 아닌 일반 애니메 스타일로 생성
- **원인**: identity_tags에 `chibi` 태그(ID 153) 누락
- **해결**: Chibi(ID 4), Eureka Chibi(ID 2), Midoriya Chibi(ID 7)에 chibi 태그 추가
- **문제 2**: `medium shot` + `standing` 조합 시 머리가 프레임에서 잘림
- **원인**: Negative prompt에 composition 보호 태그 없음
- **해결**: 모든 캐릭터 `recommended_negative`에 `cropped, head out of frame, out of frame` 추가
- **권장 대안**: `medium shot` 대신 `cowboy shot` (Danbooru 729K posts, 명확한 정의)

**IP-Adapter Character Presets (2026-01-27 22:30)**:
- **기능**: 캐릭터별 최적 IP-Adapter weight 자동 적용
- **프리셋**: Standard(0.75), Character(0.80), Chibi(0.85), Blindbox(0.90)
- **Backend**: `config.py`에 `CHARACTER_PRESETS` 설정 추가
- **API**: `/ip-adapter/presets`, `/ip-adapter/preset/{key}` 엔드포인트
- **Frontend**: Reference 선택 시 프리셋 weight 자동 적용 + 드롭다운에 weight 표시
- **슬라이더**: step 0.1→0.05로 변경 (0.85 등 정밀 값 지원)

**프롬프트 성별 태그 충돌 수정 (2026-01-27 13:30)**:
- **문제**: Scene 프롬프트의 `1girl`과 Character 프롬프트의 `1boy`가 동시에 포함되는 버그
- **해결**: `mergePromptTokens`에 `CONFLICTING_TAG_GROUPS` 충돌 필터링 추가
- **규칙**: Base 프롬프트(캐릭터) 우선, Scene 프롬프트에서 충돌 태그 자동 제거
- **대상 태그 그룹**: `1girl/1boy/1other`, `2girls/2boys`, `female/male` 등

**Character Image Modal 추가 (2026-01-27 13:30)**:
- Manage > Characters 탭에서 섬네일 클릭 시 확대 모달 표시
- 배경 블러 + 캐릭터 이름 표시, 닫기 버튼 및 외부 클릭으로 닫기

**Frontend 디버깅 로그 추가 (2026-01-27 11:45)**:
- 캐릭터 선택 시 로그: charFull, charPrompt, IP-Adapter 설정
- 프롬프트 빌드 시 로그: baseTokens, filteredBaseTokens, sortedTokens
- API 요청 시 로그: ipAdapterPayload
- 캐릭터 선택 시 `useIpAdapter` 자동 활성화 버그 수정

**IP-Adapter CLIP 모델 지원 (2026-01-27 11:20)**:
- **문제**: FaceID 모델이 애니메이션 얼굴 인식 실패 (InsightFace는 실사 전용)
- **해결**: CLIP 기반 IP-Adapter 모델 추가 (`ip-adapter-plus_sd15`)
- **변경사항**:
  - 기본 모델: `faceid` → `clip` (애니메이션용)
  - 모듈 자동 선택: `ip-adapter_clip_sd15` (CLIP) / `ip-adapter_face_id_plus` (FaceID)
  - SD WebUI 구축 매뉴얼 추가: `docs/SD_WEBUI_SETUP.md`

**IP-Adapter Reference 자동 적용 (2026-01-27 00:30)**:
- 캐릭터 선택 시 해당 캐릭터의 IP-Adapter Reference 자동 설정
- 9개 캐릭터 모두 reference image 매핑 완료 (Generic Anime Boy/Girl 포함)
- 캐릭터 해제(None) 시 reference도 함께 초기화

**Eval 테스트 프롬프트 확장 (2026-01-26 20:30)**:
- 테스트 프롬프트 6개 → 30개 확장
- 카테고리: 표정(4), 포즈(4), 카메라(3), 환경(4), 시간/날씨(4), 의상(3), 소품(2)

**Keywords 일괄 승인 (2026-01-26 20:00)**:
- 15개 태그 카테고리 승인: object(5), environment(4), clothing_detail(4), pose(1), style(1)

**Random BGM 기능 완료 (2026-01-26 19:00)**:
- `bgm_file: "random"` 지원 → Backend에서 `assets/audio/*.mp3` 중 랜덤 선택
- TDD: 9개 테스트 작성 후 구현 (`test_bgm.py`)
- Frontend: BGM 드롭다운에 "Random" 옵션 추가
- 시드 기반 재현성 지원 (동일 시드 → 동일 BGM)

**Ken Burns Effect 구현 완료 (2026-01-26 18:00)**:
- **10개 프리셋**: none, slow_zoom, zoom_in/out_center, pan_left/right/up/down, zoom_pan_left/right
- **Random 모드**: 씬별 랜덤 효과 (재현 가능한 시드 기반)
- **Intensity 조절**: 0.5x ~ 2.0x 효과 강도 슬라이더
- **구현 파일**: `services/motion.py` (신규), `services/video.py`, `schemas.py`, `RenderSettingsPanel.tsx`, `page.tsx`
- **레거시 제거**: `motion_style` 필드 완전 제거, `ken_burns_preset`으로 단일화

**Subtitle & Text System Improvements (2026-01-26)**:
- **특수문자 필터링 버그 수정**: `/`, `~`, `:`, `;`, `"` 등 수식 및 문장 부호가 삭제되던 문제 해결 (`1/10` 등 정상 표시).
- **소수점 줄바꿈 버그 수정**: 마침표(`.`) 기준 강제 줄바꿈 로직에서 `.`을 제외하여 `0.25` 같은 숫자가 잘리지 않도록 개선.
- **캐릭터 재생성 UI**: Manage 페이지에서 버튼 하나로 IP-Adapter용 얼굴 이미지를 즉시 생성/교체하는 기능 구현.
- **Manual Mode UX**: 캐릭터 선택 해제(None) 시 기존 프롬프트를 즉시 비우도록 수정.

**Standard Mode Preset & Reference Setup 완료 (2026-01-25 23:30)**:
- **Generic Anime Girl/Boy** 프리셋 추가 (Standard Mode)
- **IP-Adapter 레퍼런스 일괄 생성**: DB 내 9개 캐릭터(Generic 포함) 전수 생성 완료
- **Prompt Pipeline 검증**: Standard Mode + IP-Adapter + EasyNegative 자동 적용 확인
- 이제 사용자는 LoRA 학습 없이도 "Standard Mode"를 통해 일관성 있는 캐릭터 생성 가능.

**Prompt Composition System (Phase 9.8) 안정화**:
- Mode A (Standard) vs Mode B (LoRA) 분기 로직 검증 완료.
- IP-Adapter와 결합 시 "얼굴 고정 + 자유로운 장면 묘사" 최적 조합 확인.

**15.6 Quality Evaluation System 완료 (2026-01-26)**:
- 6개 표준 테스트 프롬프트 정의 (simple_portrait → multi_element)
- `evaluation_runs` 테이블 및 마이그레이션
- `/eval/run`, `/eval/results`, `/eval/summary` API
- `/manage` 페이지 Eval 탭 (Mode A vs B 비교 차트)

**UI Polish (2026-01-26)**:
- Topic textarea 기본 높이 증가 (4→12 rows)
- Prompts 탭 Empty State 개선
- Media Settings: 폰트명(20자), BGM명(28자) 글자수 제한
- `mergePromptTokens` non-string 방어 코드 추가
- BGM 미리듣기 circular reference 에러 수정 (onClick 이벤트 전달 버그)
- Missing 태그 "+ Add" 버튼 Toast 피드백 추가

**TTS 개선 (2026-01-26)**:
- TTS가 정제된 스크립트 사용 (`raw_script` → `clean_script`)
- 스크립트 정제 함수 개선: 말줄임표/대시 정규화, 다중 문장부호 단일화

**Draft & Preset UX 개선 (2026-01-26 11:00)**:
- **Character Preset 영속성**: 페이지 리로드 시 선택된 캐릭터 유지 (DraftData에 추가)
- **Draft 리셋 개선**: 채널 브랜딩 정보(channel_name, avatar_key) 유지, caption만 초기화
- **Post 레이아웃 자막**: 최대 줄 수 3→2로 변경 (이미지 겹침 방지)
- **일본어 프리셋 명확화**: "일본어 강좌" → "일본어 레슨 (학습용)" (학습용임을 명시)
- **스토리보드 언어 강제**: 일본어 등 외국어 생성 시 로마자/번역 혼용 방지 (CRITICAL LANGUAGE RULE 추가)

**일본어 레슨 템플릿 개선 (2026-01-26 11:30)**:
- **로마자 제거**: 스크립트에서 Romaji 표기 삭제 (영어 노출 방지)
- **상황 기반 학습**: 단어 암기 → 실생활 상황 예시 기반 학습으로 전환
  - 이전: `일본어: ありがとう - 감사합니다`
  - 이후: `물건을 받았을 때: ありがとう - 감사합니다`
- **상황 예시**: 카페, 식당, 가게, 역, 길거리 등 실생활 장면 활용
- **후킹 & 코믹 요소**:
  - Scene 1: 후킹 (관심 유도 질문/문제) - "이 표현 모르면 일본에서 굶어요 ㅋㅋ"
  - Final: 코믹 트위스트 (흔한 실수/문화 차이) - "근데 이렇게 말하면 반말이에요 ㅋㅋ"
- **프롬프트 품질 개선**:
  - 비표준 태그 제거: `teaching gesture`, `educational`, `casual_clothes`
  - 실생활 환경 확장: cafe, restaurant, street, station, classroom
  - 표준 액션 태그: `pointing`, `hand up`, `waving`

**15.7 Dynamic Tag Classification System 완료 (2026-01-25)**:
- 15.7.1~15.7.8 전체 완료
- DB 기반 분류 규칙 677개 적용, Danbooru API 연동, 승인 워크플로우 UI 구축
- 태그 충돌(Conflict) 및 의존성(Requires) 규칙 80여 개 적용
- Action(holding X), Time/Weather(환경효과) 등 태그 카테고리 437개 확장

**다음 우선순위** (2026-01-26 20:30 갱신):

| 순위 | 작업 | Phase | 가치 | 난이도 | 이유 |
|------|------|-------|------|--------|------|
| 1 | **Multi-Character 구현** | 6-3.10 | 높음 | 중 | 대화형 콘텐츠 핵심 |
| 2 | **Core Hooks Test** | 5-7 | 중 | 낮음 | TDD 규칙 준수 |
| 3 | **CI Script** | 5-7 | 중 | 낮음 | 테스트 자동화 |
| 4 | Scene Builder UI | 6-3.11 | 중 | 중 | Multi-Character 시너지 |
| 5 | Scene Clothing Override | 6-4.20 | 중 | 중 | 장면별 의상 변경 |
| 6 | VEO Clip | 5-4 | 중 | 높음 | 외부 API 의존 |
| 7 | Generation Log Analytics | 6-4.21 | 중 | 중 | 데이터 1,000건 이후 재검토 |