# Shorts Factory Master Roadmap (Strategic Fidelity Guard)

이 로드맵은 **안정성 → 리팩토링 → 안정성 → 신규 개발** 사이클을 따릅니다.
리팩토링 및 기능 추가 시 **영상 품질의 100% 일관성(Zero Variance)**을 유지하는 것을 최우선 목표로 합니다.

---

## 🏗️ Phase 1: Foundation & Stability - **COMPLETE**
기본 기능 구현 완료.
- [x] Version Control 초기화
- [x] Backend Core Logic (FastAPI + AI Integration)
- [x] Frontend Studio UI (Next.js + Autopilot State Machine)
- [x] Image Validation Pipeline (WD14 + Gemini)
- [x] FFmpeg Rendering Pipeline (Overlays, Subtitles, Audio)
- [x] 9:16(Full) 및 1:1(Post) 레이아웃 지원

---

## 🛡️ Phase 2: 안정성 기반 구축 (Visual Regression Test) - **COMPLETE**
영상 생성 코드가 수정되어도 결과물이 변하지 않도록 하는 근본적인 안전 장치를 구축합니다.

### 2-1. Golden Master & VRT Engine
| 작업 | 설명 | 상태 |
|------|------|------|
| Golden Master Storage | 현재 안정적인 영상의 기준 프레임을 `tests/golden_masters/`에 저장 | [x] |
| Pixel-by-Pixel Comparison | OpenCV + SSIM으로 95% 일치 검증 엔진 구축 | [x] |
| Diff Reporting | 불일치 시 시각적 Diff 이미지 자동 생성 | [x] |

### 2-2. Deterministic Environment
| 작업 | 설명 | 상태 |
|------|------|------|
| Fixed Seed Testing | 테스트 시 AI 생성(이미지, 음성) 시드 고정 | [x] |
| Layout Spec Extraction | Pillow/FFmpeg 좌표/비율을 `constants/layout.py`로 분리 | [x] |

---

## 🔧 Phase 3: 리팩토링 (안정성 기반 코드 개선) - **COMPLETE**
Phase 2의 VRT를 **매 커밋마다 실행**하며 안전하게 리팩토링합니다.

### 3-1. Backend 리팩토링
| 작업 | 설명 | 상태 |
|------|------|------|
| Router 분리 | `main.py` → `routers/` (API 엔드포인트) | [x] |
| Service 분리 | `logic.py` → `services/` (비즈니스 로직) | [x] |
| Keyword/Asset 분리 | 영향도 적은 조회 로직부터 분리 (Quick Win) | [x] |
| Config 분리 | 설정/상수를 `config.py`로 중앙화 | [x] |
| VideoBuilder 추출 | 비디오 생성 로직을 클래스로 캡슐화 | [x] |

**Backend 진행 현황**: `logic.py` ~2,300줄 → 279줄 (**88% 감소**)

추출된 서비스 (8개):
- `services/keywords.py`: 키워드 관련 함수
- `services/validation.py`: 이미지 검증 함수 (WD14, Gemini)
- `services/rendering.py`: 렌더링 관련 함수 (오버레이, 자막, 포스트 카드, 레이아웃 메트릭스)
- `services/image.py`: 이미지 유틸리티 함수
- `services/avatar.py`: 아바타 생성 및 관리
- `services/prompt.py`: 프롬프트 처리 함수
- `services/utils.py`: 일반 유틸리티 함수 (JSON, 텍스트, 오디오)
- `services/video.py`: 비디오 생성 헬퍼 + **VideoBuilder 클래스**

추가 모듈:
- `config.py`: 설정, 상수, 전역 객체 (logger, gemini_client, template_env)

### 3-2. Frontend 리팩토링
| 작업 | 설명 | 상태 |
|------|------|------|
| Types/Constants 분리 | `types/`, `constants/` 디렉토리로 분리 | [x] |
| Components 분리 | SetupPanel, SceneCard, RenderSettingsPanel 등 21개 | [x] |
| useAutopilot Hook | `page.tsx`에서 Autopilot 상태 머신 추출 | [x] |

**Frontend 진행 현황**: `page.tsx` 4,222줄 → 1,832줄 (2,390줄 감소, 57%)

추출된 모듈:
- Types: `types/index.ts`
- Constants: `constants/index.ts` (SCENE_SPECIFIC_KEYWORDS 추가)
- Utils:
  - `utils/index.ts` (slugifyAvatarKey, normalize*, prompt 유틸리티, 채널명 생성)
  - `utils/validation.ts` (computeValidationResults)
- Hooks:
  - `hooks/useAutopilot.ts` (Autopilot 상태 관리)
  - `hooks/useDraftPersistence.ts` (Draft 저장/복원 - 통합 완료)
- Components (20개):
  - Setup: `SetupPanel`, `StoryboardGeneratorPanel`, `PromptSetupPanel`
  - Actions: `StoryboardActionsBar`, `AutoRunStatus`
  - Scene: `SceneListHeader`, `SceneFilmstrip`, `SceneCard`, `SceneImagePanel`, `ValidationTabContent`, `DebugTabContent`
  - Render: `RenderSettingsPanel`, `RenderedVideosSection`, `LayoutSelector`
  - Modals: `AutoRunProgressModal`, `PreviewModal`, `PromptHelperSidebar`
  - UI: `WorkingModeHeader`, `SectionDivider`, `Toast`

---

## ✅ Phase 4: 안정성 검증 (리팩토링 완료 확인) - **COMPLETE**
리팩토링 완료 후 전체 시스템 안정성을 검증합니다.

| 작업 | 설명 | 상태 |
|------|------|------|
| VRT 전체 통과 | 리팩토링 전후 영상 100% 일치 확인 (36/36) | [x] |
| E2E 테스트 | Autopilot 전체 파이프라인 수동 테스트 | [x] |
| DoD 체크리스트 | PRD §4 완료 기준 4개 항목 모두 통과 | [x] |

### DoD 체크리스트 상세 (PRD §4)
| 항목 | 설명 | 상태 |
|------|------|------|
| Autopilot | 주제 입력 → 이미지 생성 완료까지 멈춤 없이 진행 | [x] |
| Consistency | 3개 이상 장면에서 캐릭터 머리색/옷 유지 | [x] |
| Rendering | 최종 비디오 생성, TTS+BGM 정상 재생 | [x] |
| UI Resilience | F5 새로고침 후 Draft 복구 | [x] |

---

## 🚀 Phase 5: 신규 개발 (High-End Production)
검증된 안정적인 기반 위에서 새로운 기능을 추가합니다.

### 5-1. 운영 효율화
| 작업 | 설명 | 상태 |
|------|------|------|
| Resume/Checkpoint | 중단된 작업 이어하기 | [x] |
| Storage Cleanup | outputs/ 자동 정리 로직 | [x] |
| Project DB (SQLite) | 프로젝트 설정 및 히스토리 관리 | [ ] |

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

---

## 🎭 Phase 6: Character & Prompt System (v2.0)
다중 캐릭터 지원 및 프롬프트 빌더 시스템 구축.

**현재 사용 환경**:
- **Model**: `animagine-xl.safetensors` (SDXL 애니메)
- **LoRA**: `eureka_v9` (캐릭터), `chibi-laugh` (스타일)
- **Negative Embeddings**: `verybadimagenegative_v1.3`, `easynegative`

**의존성 구조**:
```
keywords.json v2.0 구조 개편 → DB 마이그레이션
        ↓
Character Builder → Style Profile → Multi-Character
        ↓
Scene Builder → Tag Autocomplete
        ↓
Civitai 연동, Analytics (고급 기능)
```

### 6-1. Data Foundation (🔴 필수 선행)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 0 | DB 스키마 설정 | PostgreSQL + SQLAlchemy + Alembic | [x] |
| 1 | keywords.json v2.0 구조 설계 | 아래 스펙 참조 | [x] |
| 2 | 기존 데이터 마이그레이션 | v1 → v2 변환 + 신규 태그 추가 | [x] |
| 3 | Danbooru Identity 태그 수집 | hair_color, eye_color, hair_style | [x] |
| 4 | Backend CRUD API | /tags, /loras, /characters 엔드포인트 | [x] |

#### keywords.json v2.0 스펙

**SD 프롬프트 권장 순서** (앞쪽 태그가 더 중요):
| Priority | Category | 설명 | 고정/가변 |
|----------|----------|------|-----------|
| 1 | Quality | masterpiece, best quality | Meta |
| 2 | Subject | 1girl, solo | Character |
| 3 | Identity | hair_color, eye_color, hair_style | Character 고정 |
| 4 | Clothing | outfit, accessories | Character 고정 |
| 5 | Pose/Camera | action, expression, shot_type, angle | Scene 가변 |
| 6 | Environment | location, time, weather, lighting | Scene 가변 |
| 7 | Style | anime style (보통 모델/LoRA가 처리) | Meta |
| 99 | LoRA | `<lora:name:weight>` | 항상 마지막 |

**구조 개요**:
```json
{
  "version": "2.0",
  "prompt_order": ["quality", "subject", "identity", "clothing", "pose", "camera", "environment", "mood", "style", "lora"],
  "character": {
    "subject": { "priority": 2, "tags": ["1girl", "1boy", "solo", ...] },
    "identity": {
      "priority": 3,
      "groups": {
        "hair_color": { "exclusive": true, "tags": ["black hair", "blonde hair", ...] },
        "eye_color": { "exclusive": true, "tags": ["blue eyes", "brown eyes", ...] },
        "hair_style": { "tags": ["long hair", "short hair", "ponytail", ...] }
      }
    },
    "clothing": { "priority": 4, "groups": { "outfit": {...}, "accessories": {...} } }
  },
  "scene": {
    "pose": { "priority": 5, "groups": { "action": {...}, "expression": {...}, "gaze": {...} } },
    "camera": { "priority": 5, "groups": { "shot_type": {...}, "angle": {...} } },
    "environment": { "priority": 6, "groups": { "location": {...}, "time": {...}, "weather": {...}, "lighting": {...} } },
    "mood": { "priority": 6, "tags": [...] }
  },
  "meta": {
    "quality": { "priority": 1, "tags": ["masterpiece", "best quality", ...] },
    "style": { "priority": 7, "tags": ["anime style", ...] }
  },
  "lora": [
    {
      "name": "eureka_v9",
      "display_name": "Eureka",
      "trigger_words": ["eureka"],
      "default_weight": 1.0,
      "weight_range": [0.5, 1.5],
      "base_models": ["animagine-xl"],
      "character_defaults": { "hair_color": "aqua hair", "eye_color": "purple eyes", "hair_style": "short hair" },
      "recommended_tags": ["hairclip", "glasses"],
      "recommended_negative": "verybadimagenegative_v1.3"
    },
    {
      "name": "chibi-laugh",
      "display_name": "Chibi Laugh",
      "trigger_words": ["chibi", "eyebrow", "laughing", "eyebrow down"],
      "default_weight": 0.6,
      "weight_range": [0.3, 0.8],
      "base_models": ["*"],
      "recommended_negative": "easynegative"
    }
  ],
  "embeddings": {
    "negative": [
      { "name": "verybadimagenegative_v1.3", "type": "quality" },
      { "name": "easynegative", "type": "quality" }
    ]
  },
  "rules": {
    "conflicts": [["long hair", "short hair", "medium hair"], ["day", "night"]],
    "requires": { "twintails": ["long hair"], "ponytail": ["long hair", "medium hair"] },
    "weight_defaults": { "hair_color": 1.0, "outfit": 1.2 }
  },
  "synonyms": {...},
  "ignore": [...],
  "_legacy_categories": {...}
}
```

**핵심 설계 원칙**:
- `priority`: 프롬프트 조합 시 자동 정렬 순서
- `exclusive`: true면 그룹 내 하나만 선택 (예: hair_color)
- `conflicts/requires`: 충돌 태그 경고, 의존성 자동 추가
- `lora[].character_defaults`: LoRA 선택 시 캐릭터 태그 자동 설정
- `_legacy_categories`: 하위 호환성 유지

### 6-2. Studio Integration (🔴 핵심 - 다음 단계)
**목표**: DB의 Style/Character 데이터를 메인 Studio 워크플로우에 연결

| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 4 | Character Builder UI | 고정 아이덴티티 태그 선택 (priority 2-4), Manage/Style 탭 | [x] |
| 5 | Style Profile | SD Model + LoRA + Embedding 번들 | [x] |
| 6 | LoRA 메타데이터 관리 | Weight Range, 호환 모델, Trigger Words, Civitai 연동 | [x] |
| **7** | **Style Profile 연동** | 기본 프로필을 Studio에서 자동 로드, 프롬프트 자동 구성 | [ ] |
| **8** | **Character 선택 UI** | Actor A에 캐릭터 프리셋 적용, 태그 자동 주입 | [ ] |

### 6-3. Multi-Character & Scene (🟡 확장)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 9 | Multi-Character 지원 | A, B, C... 다중 캐릭터 구조 | [ ] |
| 10 | Scene Builder UI | 장면별 가변 컨텍스트 태그 선택 (priority 5-6) | [ ] |
| 11 | Tag Autocomplete | Danbooru 스타일 태그 자동완성 | [ ] |
| 12 | Character Preview | 캐릭터 설정 시 미리보기 생성 | [ ] |

### 6-4. Advanced Features (🔵 고급)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 13 | Civitai 연동 | LoRA 메타데이터 자동 가져오기 (MCP 활용) | [x] |
| 14 | Visual Tag Browser | 태그별 예시 이미지 표시 | [ ] |
| 15 | Tag Usage Analytics | 사용 빈도, 성공/실패 패턴 추적 | [ ] |
| 16 | Prompt History | 성공한 프롬프트 저장/재사용 | [ ] |
| 17 | Feedback Loop | 사용자 태그 제안 시스템 | [ ] |
| 18 | Profile Export/Import | Style Profile 공유 | [ ] |

---

## 🔮 Phase 7: Advanced Consistency (IP-Adapter)
Phase 6의 LoRA 기반 시스템 안정화 후 진행.

**전제 조건**:
- ControlNet 확장 설치
- IP-Adapter 모델 (anime 전용)
- VRAM 8GB+

| 작업 | 설명 | 상태 |
|------|------|------|
| ControlNet 연동 | SD WebUI ControlNet API 통합 | [ ] |
| IP-Adapter 지원 | 참조 이미지 기반 캐릭터 일관성 | [ ] |
| LoRA + IP 조합 | LoRA 베이스 + IP-Adapter 포즈/표정 | [ ] |
| Reference Image Manager | 참조 이미지 관리 UI | [ ] |

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

**Latest Status**: 2026-01-24
- **Phase 6-1 완료**: PostgreSQL + SQLAlchemy + Alembic, 262개 태그 마이그레이션
- **Phase 6-2 부분 완료**: Style Profile, LoRA 관리, Character Builder UI, Civitai 연동
- **다음 작업**: Style Profile 연동 (#7) → Character 선택 UI (#8)
- Storage Cleanup 기능 구현 완료 (`/storage/stats`, `/storage/cleanup` API)
- Pixel-based Subtitle Wrapping 구현 완료 (폰트 기반 줄바꿈, 균형 맞추기, 동적 폰트 크기 조절)
- Preset System 구현 완료 (`/presets` API, 9개 프리셋)
- 일본어 강좌 및 수학 공식 강좌 템플릿 추가
- Frontend: Structure 선택 메뉴 확장 (7개 옵션) + 샘플 토픽 선택 UI 추가
- VRT Golden Master 업데이트 완료 (36/36 테스트 통과)
- Audio Ducking 구현 완료 (FFmpeg sidechaincompress, BGM Volume 조절 UI)
- **Phase 6 로드맵 재조정**: Data → **Integration** → Multi-Character → Scene 순서
- **SetupPanel 제거**: 간소화 진입점 제거, Custom Start (Working Mode)로 직접 진입
- **SD 파라미터 Advanced 이동**: Steps, CFG, Sampler 등 기본 숨김, 토글로 펼침
- **VEO "Coming Soon"**: 비활성화 + 라벨 추가
- **Character Consistency 전략 수립**: LoRA 기반 (Phase 6) → IP-Adapter (Phase 7) 단계적 접근
- **Phase 7 추가**: IP-Adapter 기반 Advanced Consistency
- **keywords.json v2.0 스펙 정의**: SD 프롬프트 최적화 구조 설계
  - Priority 기반 태그 정렬 (Quality → Subject → Identity → Clothing → Pose → Environment → LoRA)
  - Character/Scene 태그 분리, exclusive 그룹, conflicts/requires 규칙
  - LoRA 메타데이터 (trigger_words, weight_range, character_defaults, recommended_negative)
  - 현재 환경 최적화: animagine-xl + eureka_v9 + chibi-laugh
