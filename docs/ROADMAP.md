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
| Service 분리 | `logic.py` → `services/` (비즈니스 로직) | [~] |
| Keyword/Asset 분리 | 영향도 적은 조회 로직부터 분리 (Quick Win) | [x] |

**Backend 진행 현황**: `logic.py` ~2,300줄 → 758줄 (~67% 감소)

추출된 서비스 (7개):
- `services/keywords.py`: 키워드 관련 함수
- `services/validation.py`: 이미지 검증 함수 (WD14, Gemini)
- `services/rendering.py`: 렌더링 관련 함수 (오버레이, 자막, 포스트 카드)
- `services/image.py`: 이미지 유틸리티 함수
- `services/avatar.py`: 아바타 생성 및 관리
- `services/prompt.py`: 프롬프트 처리 함수
- `services/utils.py`: 일반 유틸리티 함수 (JSON, 텍스트, 오디오)

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
| Resume/Checkpoint | 중단된 작업 이어하기 | [ ] |
| Storage Cleanup | outputs/ 자동 정리 로직 | [ ] |
| Project DB (SQLite) | 프로젝트 설정 및 히스토리 관리 | [ ] |

### 5-2. 영상 품질 강화
| 작업 | 설명 | 상태 |
|------|------|------|
| Ken Burns Effect | 정지 이미지에 줌/팬 효과 | [ ] |
| Professional Audio Ducking | 내레이션-BGM 볼륨 자동 조절 | [ ] |
| Character Consistency (ControlNet) | IP-Adapter 기반 얼굴 고정 | [ ] |

### 5-3. 확장 기능 (v1.x Backlog)
| 작업 | 설명 | 상태 |
|------|------|------|
| VEO Clip | Video Generation 통합 | [ ] |
| 정량적 품질 지표 | Match Rate 자동화 | [ ] |

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

**Latest Status**: 2026-01-24 Phase 4 완료. VRT 36/36 통과, DoD 4/4 통과. Phase 5 (신규 개발) 준비 완료.
