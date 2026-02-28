# Scene Builder UI

> 상태: **대부분 완료** (Scene 편집 UI 구현됨, 컨텍스트 태그 Picker 미구현)
> 최종 갱신: 2026-02-28 (소스 코드 기준 최신화)

---

## 배경

장면별 프롬프트/태그/설정을 사용자가 직접 편집하는 UI. 초기에는 "미착수"였으나, Studio Edit Tab 구현 과정에서 핵심 Scene 편집 기능이 이미 구현됨.

## 구현 완료

### Scene 편집 UI (Studio Edit Tab)
| # | 항목 | 상태 | 소스 위치 |
|---|------|------|----------|
| 1 | SceneCard (메인 에디터) | ✅ | `components/storyboard/SceneCard.tsx` |
| 2 | SceneListPanel (씬 목록 + 드래그 정렬) | ✅ | `components/storyboard/SceneListPanel.tsx` |
| 3 | ScenePromptFields (프롬프트 편집) | ✅ | `components/storyboard/ScenePromptFields.tsx` |
| 4 | SceneEssentialFields (스크립트/화자/길이) | ✅ | `components/storyboard/SceneEssentialFields.tsx` |
| 5 | SceneSettingsFields (ControlNet/IP-Adapter/배경) | ✅ | `components/storyboard/SceneSettingsFields.tsx` |
| 6 | SceneCharacterActions (캐릭터별 표정/포즈/액션) | ✅ | `components/storyboard/SceneCharacterActions.tsx` |
| 7 | SceneClothingModal (씬별 의상 오버라이드) | ✅ | `components/storyboard/SceneClothingModal.tsx` |
| 8 | SceneImagePanel (이미지 생성/검증/후보) | ✅ | `components/storyboard/SceneImagePanel.tsx` |
| 9 | SceneGeminiModals (Gemini 편집/제안) | ✅ | `components/storyboard/SceneGeminiModals.tsx` |
| 10 | SceneActionBar (생성/편집/검증 버튼) | ✅ | `components/storyboard/SceneActionBar.tsx` |

### Backend
| # | 항목 | 상태 | 소스 위치 |
|---|------|------|----------|
| 1 | Scene 모델 (context_tags JSONB, clothing_tags 등) | ✅ | `models/scene.py` |
| 2 | SceneTag 연관 테이블 | ✅ | `models/associations.py` |
| 3 | SceneCharacterAction 모델 | ✅ | `models/scene.py` |
| 4 | scene_builder 서비스 (직렬화/생성) | ✅ | `services/storyboard/scene_builder.py` |
| 5 | 이미지 생성/검증/편집 API | ✅ | `routers/scene.py` |

## 미구현 — 컨텍스트 태그 Picker

Gemini가 자동 생성한 환경/시간/날씨 태그를 사용자가 **시각적으로 선택/수정**하는 전용 UI.

| # | 항목 | 설명 | 우선순위 |
|---|------|------|---------|
| A | Environment Picker | 실내/실외 + 구체 장소 (cafe, school, park 등) 태그 선택 | P2 |
| B | Time/Weather Selector | 시간대 (night, sunset 등) + 날씨 (rain, snow 등) 태그 | P2 |
| C | Manual Override 플로우 | Gemini 자동 태그 표시 → 수동 덮어쓰기 → 수동 우선 | P2 |
| D | Tag Autocomplete 연동 | 기존 Tag Autocomplete 컴포넌트 재사용 | P2 |

### 현재 대안

- `context_tags` JSONB에 environment/mood 등이 저장됨
- ScenePromptFields에서 `image_prompt` 직접 편집으로 환경 태그 수동 제어 가능
- Gemini가 스토리보드 생성 시 환경 태그 자동 배정

### 구현 시 참고

- DB: `scene_tags` 테이블 + `context_tags` JSONB 이미 존재
- Tag 소분류: `group_name` = `location_indoor`, `location_outdoor`, `weather`, `time` 등
- Frontend: `TagAutocomplete` 컴포넌트 재사용 가능

## 수락 기준

| # | 기준 | 상태 |
|---|------|------|
| 1 | 장면별 프롬프트/태그/설정 수동 편집 가능 | ✅ 완료 |
| 2 | 캐릭터별 표정/포즈/액션 편집 | ✅ 완료 |
| 3 | 이미지 생성/검증/Gemini 편집 | ✅ 완료 |
| 4 | 장면별 배경/시간/날씨 태그 Picker | ❌ 미구현 (P2) |
| 5 | Gemini 자동 태그와 수동 태그 공존 (수동 우선) | ❌ 미구현 (P2) |
| 6 | 선택된 태그가 프롬프트에 정확히 반영 | ✅ 완료 (context_tags → 프롬프트 빌더) |
