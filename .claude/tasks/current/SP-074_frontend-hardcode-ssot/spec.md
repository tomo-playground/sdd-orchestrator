---
id: SP-074
priority: P2
scope: fullstack
branch: feat/SP-074-frontend-ssot
created: 2026-03-23
status: approved
approved_at: 2026-03-23
depends_on:
label: chore
---

## 무엇을 (What)
Frontend에 하드코딩된 도메인 옵션/프리셋을 Backend SSOT로 전환한다.

## 왜 (Why)
CLAUDE.md의 Configuration Principles에 따라 도메인 옵션은 Backend가 SSOT이고 Frontend는 API 응답을 소비만 해야 한다. 현재 Frontend에 도메인 지식이 하드코딩된 곳이 다수 존재하여, Backend 변경 시 Frontend 동기화가 누락될 위험이 있다.

## 하드코딩 전수 조사 결과

### A. 도메인 옵션 (Backend SSOT 전환 필수)

| 파일 | 상수 | 내용 | 비고 |
|------|------|------|------|
| `DirectorControlPanel.tsx` | `EMOTION_PRESETS` | 밝게/차분/긴장/감성 4종 | 기존 SP-050 범위 |
| `DirectorControlPanel.tsx` | `BGM_MOOD_PRESETS` | 경쾌/잔잔/긴장/감성 4종 | 기존 SP-050 범위 |
| `constants/index.ts` | `CATEGORY_DESCRIPTIONS` | 태그 카테고리 한국어 설명 23종 | tags API에서 제공해야 함 |
| `constants/index.ts` | `AUTO_RUN_STEPS` | stage/images/tts/render 4단계 | 파이프라인 단계 |
| `constants/index.ts` | `OVERLAY_STYLES` | overlay_minimal 1종 | 확장 시 이관 필요 |
| `CharacterDetailSections.tsx` | `IP_ADAPTER_MODELS` | clip_face/clip 2종 | SD 모델 의존 |
| `useStudioKanban.ts` | `COLUMN_ORDER` | draft/in_prod/rendered/published | 칸반 상태 |

### B. UI 편의 프리셋 (SSOT 위반 아님, 확장성 검토)

| 파일 | 상수 | 내용 |
|------|------|------|
| `SceneClothingModal.tsx` | `CLOTHING_PRESETS` | school_uniform 등 태그 퀵입력 |
| `SceneEditImageModal.tsx` | `EDIT_PRESETS` | "밝게 웃으면서" 등 지시문 퀵입력 |
| `GeminiEditModal.tsx` | `EXAMPLES` | "Smile brightly" 등 6종 |
| `constants/glossary.ts` | `GLOSSARY` | SD 용어 설명 11종 |

### C. 정상 (Frontend 로컬 설정 — 전환 불필요)

| 상수 | 용도 |
|------|------|
| `API_BASE`, `ADMIN_API_BASE` | API 엔드포인트 |
| `API_TIMEOUT.*` | 타임아웃 설정 |
| `Z_INDEX.*` | CSS 레이어 |
| `DEFAULT_IMAGE_WIDTH/HEIGHT` | Backend 폴백 (주석에 명시) |
| `MAX_RETRIES`, `BACKOFF_BASE_MS` | 재시도 로직 |
| `HEART_EMOJIS`, `ASCII_HEARTS` | 장식용 |
| `DEFAULT_BGM`, `DEFAULT_SCENE_TEXT_FONT` | 기본값 (Backend에도 동일) |
| Store keys (`STORYBOARD_STORE_KEY` 등) | localStorage 키 |

## 완료 기준 (DoD)

### A군 (Backend SSOT 전환)
- [ ] `EMOTION_PRESETS` + `BGM_MOOD_PRESETS` → `/presets` API 응답에서 소비 (SP-050 흡수)
- [ ] `CATEGORY_DESCRIPTIONS` → tags API 또는 `/presets` 응답에 `ko_description` 포함
- [ ] `IP_ADAPTER_MODELS` → SD 설정 API에서 제공
- [ ] `AUTO_RUN_STEPS` → 파이프라인 단계 목록을 Backend에서 제공 또는 정당성 문서화
- [ ] `OVERLAY_STYLES` → 오버레이 에셋 목록 API 또는 정당성 문서화
- [ ] `COLUMN_ORDER` → 칸반 상태 목록 Backend 제공 또는 정당성 문서화

### B군 (확장성 검토)
- [ ] `CLOTHING_PRESETS`, `EDIT_PRESETS`, `EXAMPLES`, `GLOSSARY` — Backend 이관 여부 판단 + 결정 기록

### 공통
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 제약 (Boundaries)
- C군(정상)은 건드리지 않음
- A군 중 파이프라인 단계나 칸반 상태처럼 변경 가능성 낮은 것은 "정당성 문서화"로 대체 허용
- B군은 판단 + 기록만, 전환은 후속 태스크

## 힌트 (선택)
- SP-050 (DirectorControlPanel 프리셋 SSOT 전환) 흡수 — backlog에서 제거
- 관련 규칙: CLAUDE.md "Configuration Principles (SSOT)" 섹션
