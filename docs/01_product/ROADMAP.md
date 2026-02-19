# Shorts Factory Master Roadmap

**원칙**: 안정성 → 리팩토링 → 안정성 → 신규 개발 사이클. 영상 품질 100% 일관성(Zero Variance) 유지.

---

## Phase 1-4: Foundation & Refactoring - ARCHIVED

완료. [Phase 1-4 아카이브](../99_archive/archive/ROADMAP_PHASE_1_4.md) 참조.

---

## Phase 5: High-End Production - ARCHIVED

검증된 안정적인 기반 위에 프로덕션 기능을 구축. **전체 완료**.

| 섹션 | 핵심 성과 | 상태 |
|------|----------|------|
| 5-1. 운영 효율화 | Resume/Checkpoint, Smart AutoRun, Secure Config | [x] |
| 5-2. 영상 품질 강화 | Ken Burns, Scene Text Animation, 13개 전환 효과, Full/Post Layout | [x] |
| 5-3. 콘텐츠 확장 | Preset System, Sample Topics, 일본어/수학 템플릿 | [x] |
| 5-4. Prompt Analytics | 정량적 품질 지표, Gemini 프롬프트 검증 | [x] |
| 5-5. UI/UX 개선 | SD 파라미터 Advanced 이동, Media Defaults, Render UX | [x] |
| 5-6. UI Polish | Loading/Error UI, Character Image Modal | [x] |
| 5-7. QA | Backend 335 + Frontend 67 = **총 402개** 테스트 | [x] |

미완료 항목은 Feature Backlog 또는 Phase 7-1로 이동.

---

## Phase 6: Character & Prompt System (v2.0) - ARCHIVED

다중 캐릭터 지원 및 프롬프트 빌더 시스템 구축. **전체 완료**.

**환경**: animagine-xl (SDXL), eureka_v9/chibi-laugh LoRA, 9종 Preset

| 섹션 | 핵심 성과 | 상태 |
|------|----------|------|
| 6-1~6-4. Core Architecture | PostgreSQL/Alembic, 12-Layer PromptBuilder, Gender/Pose/Expression, Civitai/ControlNet/IP-Adapter | [x] |
| 6-5. Stability & Integrity | P0/P1 25건 수정 (DB FK/인덱스, Session Leak, FFmpeg FPS, Gemini 파싱) | [x] |
| 6-6. Code Health & Testing | 대형 파일 5건 분리, Router/Service 분리, 비동기 Gemini, 786개 테스트 | [x] |
| 6-7. Infrastructure & DX | CI, Soft Delete, Common UI, WD14 Feedback, Voice/TTS, Batch Gen, Schema Cleanup | [x] |
| 6-8. Local AI Engine | Qwen3-TTS 로컬 (MPS), Stable Audio BGM, Voice/Music Presets CRUD | [x] |

미완료 항목은 Feature Backlog 또는 후속 Phase로 이동. 상세: [Phase 6 아카이브](../99_archive/archive/ROADMAP_PHASE_6.md)

---

## Phase 7-0: ControlNet & Pose Control - ARCHIVED

완료. ControlNet 포즈 제어, IP-Adapter 캐릭터 일관성 시스템 구축.
- 2026-02-02: thumbs_up 포즈 추가 (28번째 포즈, 포즈 에셋 + synonyms)

---

## Phase 7-1: UX & Feature Expansion - ARCHIVED

사용자 경험 개선 및 핵심 신규 기능 **27건 완료**. Quick Start, Multi-Character, Scene Builder, Character Builder, Creative Lab V2, YouTube Upload, Production Workspace 네비게이션 등. 상세: [Phase 7-1 아카이브](../99_archive/archive/ROADMAP_PHASE_7_1.md)

---

## Phase 7-2: Project/Group System - ARCHIVED

채널(Project) + 시리즈(Group) 계층 구조 구현 완료. DB 마이그레이션, CRUD API, 설정 상속 엔진(System Default → GroupConfig), 렌더 프리셋 분리, Channel DNA(톤/세계관 자동 주입). 미구현 잔여(Tag/Series Intelligence, 배치 렌더링, 브랜딩, 분석)는 Feature Backlog로 이동. 상세: [기능 명세](FEATURES/PROJECT_GROUP.md)

---

## Phase 7-3: Production Workspace - ARCHIVED

재료 독립 페이지 **4건 완료** (2026-02-11). /voices, /music, /backgrounds 페이지 + 네비게이션 재구성. #4~#5는 7-4로 이관. 상세: [Phase 7-3 아카이브](../99_archive/archive/ROADMAP_PHASE_7_3.md)

---

## Phase 7-4: Studio Coordinator + Script Vertical - ARCHIVED

Studio 코디네이터 전환 + Script 버티컬 분리. Zustand 4-Store 분할, `/scripts` 페이지, 칸반/타임라인 뷰, 레거시 정리. **Phase A~D 전체 완료** (2026-02-11). [명세](FEATURES/STUDIO_VERTICAL_ARCHITECTURE.md)

---

## Phase 7-5: UX/UI Quality & Reliability - ARCHIVED

8개 에이전트 크로스 분석 기반 **30건 완료** (2026-02-12). Phase A(Quick Wins 9건: Toast, useConfirm, dirty guard, 폰트 수정 등) + Phase B(피드백/에러 11건: SSE 진행률, 보안 강화, ETA 표시 등) + Phase C(구조적 개선 10건: Client-Side UUID, Optimistic Locking, 페이지네이션, Path Traversal 방어 등). 상세: [Phase 7-5 아카이브](../99_archive/archive/ROADMAP_PHASE_7_5.md)

---

## Phase 7-6: Scene UX Enhancement (Figma Prototype Analysis) - ARCHIVED

Figma 프로토타입 기반 씬 편집 UX 개선. 씬 완성도 dot, 3탭 분리, DnD, 3-Column, 네비 4탭, Publish 통합, 레이아웃 통일. **Phase A~G 전체 완료** (2026-02-13). [명세](FEATURES/SCENE_UX_ENHANCEMENT.md)

---

## Phase 7-Y: Layout Standardization & Navigation Simplification - ARCHIVED

Manage→Library+Settings 분리, 공유 레이아웃 시스템(AppThreeColumnLayout/AppSidebar/AppMobileTabBar), Home 리디자인(HomeVideoFeed), 네비 4탭(Home/Studio/Library/Settings), Unified Setup Wizard 추가. 테스트 39건 수정. **알려진 제한사항**: 캐릭터 편집 임시 비활성, Lab 숨김, 스토리보드 삭제 UI 누락. 상세: [Phase 7-Y 아카이브](../99_archive/archive/ROADMAP_PHASE_7_Y.md)

---

## Phase 7-Z: Home Dashboard & Publish UX Redesign - ARCHIVED

Home 페이지 "창작 대시보드" 전환 완료. **전체 5개 항목 완료** (2026-02-15).

| 섹션 | 핵심 성과 | 상태 |
|------|----------|------|
| Phase A: Home Dashboard | 2-Column 레이아웃, Continue Working 섹션, Video Gallery 컴팩트화 | [x] |
| Phase B: Publish 레이아웃 | 3-Column 재배치 (비디오 프리뷰 중심), Render Settings 접힘 | [x] |

상세: [Phase 7-Z 아카이브](../99_archive/archive/ROADMAP_PHASE_7_Z.md)

---

## Phase 9: Agentic AI Pipeline (LangGraph Migration) - ARCHIVED

LangGraph 기반 에이전틱 AI 파이프라인. **15-노드** 조건 분기 그래프 (Quick 6 / Full 14), AsyncPostgresStore Memory, LangFuse Observability, Concept Gate, NarrativeScore, Research References. Phase 0~5E **전체 완료** (2026-02-19). 잔여 1건(PipelineControl/분산 큐) Feature Backlog 이동. 상세: [Phase 9 아카이브](../99_archive/archive/ROADMAP_PHASE_9.md), [명세](FEATURES/AGENTIC_PIPELINE.md)

---

## Phase 10: True Agentic Architecture - ARCHIVED

DAG Workflow → Agentic AI 전환 완료. **전체 10개 항목 완료** (2026-02-18).
**명세**: [AGENTIC_PIPELINE.md](FEATURES/AGENTIC_PIPELINE.md) (Phase 10 섹션)

| 섹션 | 핵심 성과 | 상태 |
|------|----------|------|
| Phase 0: Benchmark | 벤치마크 샘플 10건 + 자동화 스크립트, TDD 18개 테스트 | [x] |
| Phase A: ReAct Loop | Director 3-step ReAct, Review Self-Reflection, Writer Planning Step | [x] |
| Phase B: Tool-Calling | Gemini Function Calling 인프라, Research 5 tools, Cinematographer 4 tools | [x] |
| Phase C: Communication | Agent Message Protocol, Director↔Production 양방향, Critic 실시간 토론 + KPI 수렴 | [x] |

**5대 Agentic 요건 충족**: 자율 의사결정, Tool Use, Planning, Self-Reflection, 에이전트 소통. 상세: [Phase 10 아카이브](../99_archive/archive/ROADMAP_PHASE_10.md)

---

## Phase 8: Multi-Style Architecture (Future)

**목표**: Anime, Realistic, 3D 등 다양한 화풍 지원을 위한 유연한 파이프라인 구축.

---

## Feature Backlog

Phase 9 이후 또는 우선순위 미정 항목.

### Creative Lab 개선 — 전체 완료 (7-4 Script 버티컬로 이관, Lab 제거)

| 기능 | 참조 |
|------|------|
| VEO Clip (Video Generation 통합) | [명세](FEATURES/VEO_CLIP.md) |
| Visual Tag Browser (태그별 예시 이미지) | [명세](FEATURES/VISUAL_TAG_BROWSER.md) |
| Profile Export/Import (Style Profile 공유) | [명세](FEATURES/PROFILE_EXPORT_IMPORT.md) |
| Scene Clothing Override (장면별 의상 변경) | [명세](FEATURES/SCENE_CLOTHING_OVERRIDE.md) |
| Scene 단위 자연어 이미지 편집 | [명세](FEATURES/SCENE_IMAGE_EDIT.md) |
| Tag Intelligence (채널별 태그 정책 + 데이터 기반 추천) | [명세](FEATURES/PROJECT_GROUP.md) §2-2 |
| Series Intelligence (에피소드 연결 + 성공 패턴 학습) | [명세](FEATURES/PROJECT_GROUP.md) §2-3 |
| 배치 렌더링 + 큐 (그룹 일괄 렌더, WebSocket 진행률) | [명세](FEATURES/PROJECT_GROUP.md) §3-1 |
| 브랜딩 시스템 (로고/워터마크, 인트로/아웃트로, 플랫폼별 출력) | [명세](FEATURES/PROJECT_GROUP.md) §3-2 |
| 분석 대시보드 (Match Rate 추이, 프로젝트 간 비교) | [명세](FEATURES/PROJECT_GROUP.md) §3-3 |
| Storyboard Version History | - |
| LoRA Calibration Automation | - |
| v3_composition.py 하드코딩 프롬프트 DB/config 이동 | - |
| Real-time Prompt Preview (12-Layer) | - |
| Studio 초기 로딩 최적화 (useEffect 워터폴 제거, API 병렬화) | - |
| PipelineControl 커스텀 (노드 on/off) + 분산 큐 (Celery/Redis) | Phase 9-4 잔여 |

---

## Development Cycle

```
Phase 6-5 (Stability) → 6-6 (Code Health) → 6-7 (Infra/DX) → 6-8 (Local AI) → 7-0 (ControlNet) → 7-1 (UX/Feature)
     P0/P1 Fixes          Refactoring          CI + Soft Delete    TTS/Voice/BGM     Pose Control      New Features
                                                                                                       + Creative Lab
                                                                                                            ↓
               7-2 (Project/Group) → 7-3 (Production Workspace) → 7-4 (Studio + Script Vertical) → 7-5 (UX Quality)
                Cascading Config      재료 독립 페이지              Studio 코디네이터 + 대본 버티컬    피드백/안전성/일관성
                                                                                                            ↓
                              7-6 (Scene UX Enhancement) → 7-X (UI Polish) → 7-Y (Layout Standardization) → 7-Z (Home & Publish UX)
                               Figma 기반 씬 편집 개선       공통 컴포넌트/단축키   Manage→Library+Settings 분리    대시보드+Publish 재설계
                                                                                                                          ↓
                                                                                                                    9 (Agentic Pipeline)
                                                                                                                     LangGraph 전환
                                                                                                                          ↓
                                                                                                                    10 (True Agentic) ★최우선
                                                                                                                     ReAct+Tools+Communication
                                                                                                                          ↓
                                                                                                                    8 (Multi-Style)
                                                                                                                        Future
```

**현재 진행 상태** (2026-02-19):
- Phase 5~7 계열: **전체 완료 (ARCHIVED)**
- Phase 9 (Agentic Pipeline): **전체 완료 (ARCHIVED)** — [아카이브](../99_archive/archive/ROADMAP_PHASE_9.md)
- Phase 10 (True Agentic): **전체 완료 (ARCHIVED)** — [아카이브](../99_archive/archive/ROADMAP_PHASE_10.md)
- 렌더링 품질 개선 (02-14~17): Scene Text 동적 높이/폰트, Safe Zone, 얼굴 감지, TTS 정규화. 52개 테스트
- Studio UX 개선 (02-19): 1-column 레이아웃(Script/Publish), 프로덕션 에이전트 4종 SSE 노출, Generate 중복 제거, 이미지 클릭 팝업 프리뷰(오버레이 클릭 관통 fix), Scene 번호 1-based 표준화, 파이프라인 노드 메타정보 tooltip
- QA 전체 TC 매트릭스 작성 (02-19): 18개 카테고리 130+ TC ID, P1 라우터 테스트 4건 57개 추가 (Projects/Groups/VoicePresets/RenderPresets), 커버리지 62%→74%
- **테스트**: Backend 1,862 + Frontend 352 = **총 2,214개**
- **다음**: Phase 8 (Multi-Style) 또는 Feature Backlog 항목

### 잔여 작업 우선순위

**Tier 0~1 — 전체 완료** (2026-02-18). Phase 10 5대 Agentic 요건 충족 + Tier 1 서사 품질 3건 완료. 상세: [Phase 9 아카이브](../99_archive/archive/ROADMAP_PHASE_9.md), [Phase 10 아카이브](../99_archive/archive/ROADMAP_PHASE_10.md)

**Tier 3 — 장기**
| 순위 | 작업 | 근거 |
|------|------|------|
| 1 | PipelineControl 커스텀, 분산 큐 | 규모 확장 시 |
| 2 | 배치 렌더링, 브랜딩, 분석 대시보드 | Feature Backlog |
| 3 | Multi-Style Architecture | Anime 외 화풍 확장 |
