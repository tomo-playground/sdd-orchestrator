# Scene Builder UI

> 상태: **완료**
> 최종 갱신: 2026-02-28 (SceneEnvironmentPicker 구현으로 전 항목 완료)

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

## 컨텍스트 태그 Picker (구현 완료)

> 커밋: `e4355d0` (2026-02-28) — SceneEnvironmentPicker UI 추가 (Tier 2 Customize)

환경/시간/날씨/파티클 태그를 Scene 편집 화면에서 바로 확인·수정하는 전용 Picker.

| # | 항목 | 상태 | 소스 위치 |
|---|------|------|----------|
| A | Environment Picker | ✅ | `SceneEnvironmentPicker.tsx` — `environment` 그룹 |
| B | Time/Weather Selector | ✅ | `SceneEnvironmentPicker.tsx` — `time_of_day`, `weather`, `particle` 그룹 |
| C | Manual Override 플로우 | ✅ | 선택 태그 칩 표시 + 추가/삭제로 Gemini 자동 태그 수동 덮어쓰기 |
| D | Tag Autocomplete 연동 | ✅ | `TagSuggestInput` 컴포넌트 재사용 (10개 초과 그룹) |

## 수락 기준

| # | 기준 | 상태 |
|---|------|------|
| 1 | 장면별 프롬프트/태그/설정 수동 편집 가능 | ✅ 완료 |
| 2 | 캐릭터별 표정/포즈/액션 편집 | ✅ 완료 |
| 3 | 이미지 생성/검증/Gemini 편집 | ✅ 완료 |
| 4 | 장면별 배경/시간/날씨 태그 Picker | ✅ 완료 (SceneEnvironmentPicker) |
| 5 | Gemini 자동 태그와 수동 태그 공존 (수동 우선) | ✅ 완료 (Manual Override 플로우) |
| 6 | 선택된 태그가 프롬프트에 정확히 반영 | ✅ 완료 (context_tags → 프롬프트 빌더) |
