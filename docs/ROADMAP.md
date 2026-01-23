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

## 🔧 Phase 3: 리팩토링 (안정성 기반 코드 개선) - **CURRENT**
Phase 2의 VRT를 **매 커밋마다 실행**하며 안전하게 리팩토링합니다.

### 3-1. Backend 리팩토링
| 작업 | 설명 | 상태 |
|------|------|------|
| Router 분리 | `main.py` → `routers/` (API 엔드포인트) | [x] |
| Service 분리 | `main.py` → `services/` (비즈니스 로직) | [~] |
| Keyword/Asset 분리 | 영향도 적은 조회 로직부터 분리 (Quick Win) | [x] |

### 3-2. Frontend 리팩토링
| 작업 | 설명 | 상태 |
|------|------|------|
| Types/Constants 분리 | `types/`, `constants/` 디렉토리로 분리 | [x] |
| Components 분리 | SetupPanel, SceneCard, RenderSettingsPanel 등 21개 | [x] |
| useAutopilot Hook | `page.tsx`에서 Autopilot 상태 머신 추출 | [ ] |

**Frontend 진행 현황**: `page.tsx` 4,222줄 → 2,324줄 (1,898줄 감소, 45%)

추출된 컴포넌트 (21개):
- Types: `types/index.ts`, Constants: `constants/index.ts`
- Setup: `SetupPanel`, `StoryboardGeneratorPanel`, `PromptSetupPanel`
- Actions: `StoryboardActionsBar`, `AutoRunStatus`
- Scene: `SceneListHeader`, `SceneFilmstrip`, `SceneCard`, `SceneImagePanel`, `ValidationTabContent`, `DebugTabContent`
- Render: `RenderSettingsPanel`, `RenderedVideosSection`, `LayoutSelector`
- Modals: `AutoRunProgressModal`, `PreviewModal`, `PromptHelperSidebar`
- UI: `WorkingModeHeader`, `SectionDivider`, `Toast`

---

## ✅ Phase 4: 안정성 검증 (리팩토링 완료 확인)
리팩토링 완료 후 전체 시스템 안정성을 검증합니다.

| 작업 | 설명 | 상태 |
|------|------|------|
| VRT 전체 통과 | 리팩토링 전후 영상 100% 일치 확인 | [ ] |
| E2E 테스트 | Autopilot 전체 파이프라인 자동 테스트 | [ ] |
| DoD 체크리스트 | PRD §4 완료 기준 4개 항목 모두 통과 | [ ] |

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

**Latest Status**: 2026-01-23 Phase 3 진행 중. Frontend 리팩토링 45% 완료 (page.tsx: 4,222 → 2,324줄). 21개 컴포넌트 추출.
