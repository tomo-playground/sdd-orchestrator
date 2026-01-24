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

**의존성 구조**:
```
keywords.json 구조 개편 → DB 마이그레이션
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
| 1 | keywords.json 구조 개편 | character vs scene 태그 분리 | [ ] |
| 2 | DB 마이그레이션 | keywords.json → SQLite (CRUD 지원) | [ ] |

### 6-2. Character Layer - LoRA 기반 (🟡 핵심)
**전략**: LoRA로 캐릭터 일관성 확보 → 이후 IP-Adapter 추가

| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 3 | Character Builder UI | 고정 아이덴티티 태그 선택 | [ ] |
| 4 | Style Profile | SD Model + LoRA + Trigger Words 번들 | [ ] |
| 5 | LoRA 메타데이터 관리 | Weight, 호환 모델, Trigger Words 저장 | [ ] |
| 6 | Multi-Character 지원 | A, B, C... 다중 캐릭터 구조 | [ ] |
| 7 | Character Preview | 캐릭터 설정 시 미리보기 생성 | [ ] |

### 6-3. Scene Layer (🟢 확장)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 8 | Scene Builder UI | 장면별 가변 컨텍스트 태그 선택 | [ ] |
| 9 | Tag Autocomplete | 태그 자동완성 | [ ] |

### 6-4. Advanced Features (🔵 고급)
| 순서 | 작업 | 설명 | 상태 |
|------|------|------|------|
| 10 | Civitai 연동 | LoRA 메타데이터 자동 가져오기 | [ ] |
| 11 | Visual Tag Browser | 태그별 예시 이미지 표시 | [ ] |
| 12 | Tag Usage Analytics | 사용 빈도, 성공/실패 패턴 추적 | [ ] |
| 13 | Prompt History | 성공한 프롬프트 저장/재사용 | [ ] |
| 14 | Feedback Loop | 사용자 태그 제안 시스템 | [ ] |
| 15 | Profile Export/Import | Style Profile 공유 | [ ] |

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

**Core Mandate**: "No changes in output without explicit intention."
(의도하지 않은 결과물의 변화는 허용하지 않는다.)

**Latest Status**: 2026-01-24
- Storage Cleanup 기능 구현 완료 (`/storage/stats`, `/storage/cleanup` API)
- Pixel-based Subtitle Wrapping 구현 완료 (폰트 기반 줄바꿈, 균형 맞추기, 동적 폰트 크기 조절)
- Preset System 구현 완료 (`/presets` API, 9개 프리셋)
- 일본어 강좌 및 수학 공식 강좌 템플릿 추가
- Frontend: Structure 선택 메뉴 확장 (7개 옵션) + 샘플 토픽 선택 UI 추가
- VRT Golden Master 업데이트 완료 (36/36 테스트 통과)
- Audio Ducking 구현 완료 (FFmpeg sidechaincompress, BGM Volume 조절 UI)
- **Phase 6 로드맵 추가**: 의존성 기반 우선순위 정의 (Data → Character → Scene → Advanced)
- **SetupPanel 제거**: 간소화 진입점 제거, Custom Start (Working Mode)로 직접 진입
- **SD 파라미터 Advanced 이동**: Steps, CFG, Sampler 등 기본 숨김, 토글로 펼침
- **VEO "Coming Soon"**: 비활성화 + 라벨 추가
- **Character Consistency 전략 수립**: LoRA 기반 (Phase 6) → IP-Adapter (Phase 7) 단계적 접근
- **Phase 7 추가**: IP-Adapter 기반 Advanced Consistency
