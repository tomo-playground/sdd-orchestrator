# SP-096 설계: SceneCard Props 40개 → 5개 축소 + useSceneContext() 전환

> 선행: SP-095 (SceneProvider 래핑 완료, Context 타입 정의 완료)

## 전제 조건

SP-095에서 다음이 완료된 상태:
- `SceneContext.tsx`에 `SceneDataContext` / `SceneCallbacksContext` 타입 정의
- `ScenesTab.tsx`에서 `<SceneProvider value={...}>` 래핑
- SceneCard props는 그대로 유지 (래핑만 추가)

SP-096은 실제 props를 context 소비로 전환하는 태스크.

---

## Props 분석

### SceneCard 현재 props (38개)

| # | prop | 분류 | 소비처 |
|---|------|------|--------|
| 1 | `scene` | core | SceneCard + 모든 서브 |
| 2 | `sceneIndex` | core | SceneActionBar |
| 3 | `imageValidationResult` | data | SceneImagePanel |
| 4 | `qualityScore` | data | SceneActionBar, SceneGeminiModals |
| 5 | `sceneMenuOpen` | ui-state | SceneActionBar |
| 6 | `onSceneMenuToggle` | callback | SceneActionBar |
| 7 | `onSceneMenuClose` | callback | SceneActionBar |
| 8 | `loraTriggerWords` | data | ScenePromptFields |
| 9 | `characterLoras` | data | ScenePromptFields |
| 10 | `tagsByGroup` | data | SceneEnvironmentPicker, SceneSettingsFields |
| 11 | `sceneTagGroups` | data | SceneSettingsFields |
| 12 | `isExclusiveGroup` | data (fn) | SceneSettingsFields |
| 13 | `onUpdateScene` | callback | SceneCard(내부) + 5개 서브 |
| 14 | `onRemoveScene` | callback | SceneActionBar |
| 15 | `onSpeakerChange` | callback | SceneEssentialFields |
| 16 | `onImageUpload` | callback | SceneEssentialFields |
| 17 | `onGenerateImage` | callback | SceneImagePanel, SceneActionBar |
| 18 | `onApplyMissingTags` | callback | SceneImagePanel |
| 19 | `onImagePreview` | callback | SceneCard(내부 래핑) |
| 20 | `onMarkSuccess` | callback | SceneCard(내부 Advanced) |
| 21 | `onMarkFail` | callback | SceneCard(내부 Advanced) |
| 22 | `isMarkingStatus` | data | SceneCard(내부 Advanced) |
| 23 | `selectedCharacterId` | data | ScenePromptFields, SceneSettingsFields, SceneGeminiModals |
| 24 | `basePromptA` | data | ScenePromptFields |
| 25 | `structure` | data | SceneCard(내부 계산), SceneEssentialFields |
| 26 | `characterAName` | data | SceneSettingsFields |
| 27 | `characterBName` | data | SceneSettingsFields |
| 28 | `selectedCharacterBId` | data | SceneSettingsFields |
| 29 | `genProgress` | data | SceneImagePanel |
| 30 | `buildNegativePrompt` | callback | SceneSettingsFields |
| 31 | `buildScenePrompt` | callback | SceneSettingsFields |
| 32 | `showToast` | callback | SceneActionBar, SceneSettingsFields, SceneGeminiModals, SceneClothingModal |
| 33 | `ttsState` | data | SceneEssentialFields |
| 34 | `onTTSPreview` | callback | SceneEssentialFields |
| 35 | `onTTSRegenerate` | callback | SceneEssentialFields |
| 36 | `audioPlayer` | data | SceneEssentialFields |

> 실제 카운트: 36개 고유 props. spec의 "40개"는 서브 전달 포함 카운트.

### 축소 후 SceneCard props (5개 이하 목표)

| # | prop | 이유 |
|---|------|------|
| 1 | `scene` | 핵심 데이터. key prop으로도 사용 |
| 2 | `sceneIndex` | 리스트 위치. Provider data에 포함해도 되나 key와 함께 전달이 자연스러움 |

> `scene`과 `sceneIndex`만 props로 유지. 나머지 34개는 모두 context로 이동.

rationale: `scene`은 SceneCard의 존재 이유이자 모든 서브컴포넌트의 기본 데이터. Provider에 넣으면 scene 변경 시 context 전체 리렌더가 발생하므로 props 유지가 적절. `sceneIndex`는 SceneActionBar의 "Scene #N" 표시 등 위치 정보로, scene과 함께 전달이 자연스럽다.

---

## DoD 1: SceneCard props 40개 → 5개 이하

### 구현 방법

**파일**: `frontend/app/components/storyboard/SceneCard.tsx`

1. `SceneCardProps` 타입을 2개 필드로 축소:
```
type SceneCardProps = {
  scene: Scene;
  sceneIndex: number;
};
```

2. 함수 시그니처 변경: 기존 36개 destructuring → 2개만 destructuring

3. 함수 본문 상단에 context 호출 추가:
```tsx
const { data, callbacks } = useSceneContext();
```

4. 기존 props 참조를 context 참조로 치환:
   - `imageValidationResult` → `data.imageValidationResult`
   - `qualityScore` → `data.qualityScore`
   - `onUpdateScene` → `callbacks.onUpdateScene`
   - 등등... (전체 매핑은 아래 "변환 매핑 테이블" 참조)

5. SceneCard 내부에서 직접 사용하는 값들의 치환:
   - `onImagePreview(url, candidates)` → `callbacks.onImagePreview(url, candidates)`
   - `onMarkSuccess` / `onMarkFail` → `callbacks.onMarkSuccess` / `callbacks.onMarkFail`
   - `isMarkingStatus` → `data.isMarkingStatus`
   - `structure` → `data.structure`
   - `showToast` → `callbacks.showToast`

6. import 변경: `useSceneContext` import 추가, 불필요해진 타입 import 제거 (`ImageValidation`, `ImageGenProgress`, `Tag`, `TTSPreviewState`, `AudioPlayer`)

### 변환 매핑 테이블

| 기존 prop | Context 경로 | 비고 |
|-----------|-------------|------|
| `imageValidationResult` | `data.imageValidationResult` | |
| `qualityScore` | `data.qualityScore` | |
| `sceneMenuOpen` | local 제거 | 아래 "sceneMenuOpen 처리" 참조 |
| `onSceneMenuToggle` | `callbacks.onSceneMenuToggle` | |
| `onSceneMenuClose` | `callbacks.onSceneMenuClose` | |
| `loraTriggerWords` | `data.loraTriggerWords` | |
| `characterLoras` | `data.characterLoras` | |
| `tagsByGroup` | `data.tagsByGroup` | |
| `sceneTagGroups` | `data.sceneTagGroups` | |
| `isExclusiveGroup` | `data.isExclusiveGroup` | |
| `onUpdateScene` | `callbacks.onUpdateScene` | |
| `onRemoveScene` | `callbacks.onRemoveScene` | |
| `onSpeakerChange` | `callbacks.onSpeakerChange` | |
| `onImageUpload` | `callbacks.onImageUpload` | |
| `onGenerateImage` | `callbacks.onGenerateImage` | |
| `onApplyMissingTags` | `callbacks.onApplyMissingTags` | |
| `onImagePreview` | `callbacks.onImagePreview` | |
| `onMarkSuccess` | `callbacks.onMarkSuccess` | |
| `onMarkFail` | `callbacks.onMarkFail` | |
| `isMarkingStatus` | `data.isMarkingStatus` | |
| `selectedCharacterId` | `data.selectedCharacterId` | |
| `basePromptA` | `data.basePromptA` | |
| `structure` | `data.structure` | |
| `characterAName` | `data.characterAName` | |
| `characterBName` | `data.characterBName` | |
| `selectedCharacterBId` | `data.selectedCharacterBId` | |
| `genProgress` | `data.genProgress` | |
| `buildNegativePrompt` | `callbacks.buildNegativePrompt` | |
| `buildScenePrompt` | `callbacks.buildScenePrompt` | |
| `showToast` | `callbacks.showToast` | |
| `ttsState` | `data.ttsState` | SP-095에서 추가 |
| `onTTSPreview` | `callbacks.onTTSPreview` | SP-095에서 추가 |
| `onTTSRegenerate` | `callbacks.onTTSRegenerate` | SP-095에서 추가 |
| `audioPlayer` | `callbacks.audioPlayer` | SP-095에서 추가 |

### sceneMenuOpen 처리

`sceneMenuOpen: boolean`은 현재 SceneCard props로 전달되지만 SceneContext에는 정의되어 있지 않다. 이 값은 ScenesTab에서 `sceneMenuOpen === currentScene.client_id`로 계산된 boolean.

**방안**: `SceneDataContext`에 `sceneMenuOpen: boolean` 필드 추가. ScenesTab의 Provider value에서 기존 계산 그대로 전달.

### qualityScore 정합성

현재 `qualityScore`는 ScenesTab에서 `imageValidationResults`로부터 가공하여 전달. Context에도 `qualityScore` 필드가 이미 있으므로 그대로 사용.

### 동작 정의

**Before**: SceneCard가 36개 props를 받아 서브컴포넌트에 전달. ScenesTab에 거대한 props 나열.
**After**: SceneCard는 `scene` + `sceneIndex`만 받고, 내부에서 `useSceneContext()`로 나머지 획득. 서브컴포넌트에 전달 시에도 context 값 사용.

### 엣지 케이스

1. **default 값 처리**: 기존 `loraTriggerWords = []`, `basePromptA = ""`, `isMarkingStatus = false` 등의 default. Context 타입에서 이미 non-optional로 정의됨(SP-095). ScenesTab Provider value에서 기본값 보장.
2. **optional callback**: `onMarkSuccess`, `onMarkFail`은 optional. Context에서도 optional 유지.

### 영향 범위

- `SceneCard.tsx`: props 타입 축소 + context 참조 전환 (주요 변경)
- `ScenesTab.tsx`: SceneCard JSX에서 34개 props 제거 (간소화)
- `SceneContext.tsx`: `sceneMenuOpen` 필드 1개 추가

### 테스트 전략

- 기존 SceneCard 관련 테스트가 있으면 props 전달 방식 변경에 맞춰 Provider 래핑 추가
- VRT로 시각적 변경 없음 확인

### Out of Scope

- SceneCard 내부 로직 변경 (단순 참조 경로만 변경)
- SceneCard 이외의 위치에서 SceneCard를 사용하는 곳 (현재 ScenesTab만 사용)

---

## DoD 2: 서브컴포넌트 6개 이상이 useSceneContext()로 데이터/콜백 소비

### 구현 방법

6개 서브컴포넌트를 context 소비로 전환. 각 서브컴포넌트에서 SceneCard로부터 전달받던 props 중 context로 제공 가능한 것들을 `useSceneContext()`로 교체.

#### 2-1. SceneImagePanel.tsx

**현재 props**: `scene, onImageClick, onCandidateSelect, onGenerateImage, validationResult, onApplyMissingTags, genProgress`

**context 전환 대상**:
- `onGenerateImage` → `callbacks.onGenerateImage`
- `validationResult` → `data.imageValidationResult`
- `onApplyMissingTags` → `callbacks.onApplyMissingTags`
- `genProgress` → `data.genProgress`

**props 유지**:
- `scene` — 핵심 데이터, props 유지
- `onImageClick` — SceneCard 내부에서 `callbacks.onImagePreview`를 래핑한 로컬 함수. 서브에서 직접 context 호출하려면 scene.candidates 접근이 필요하므로, 대안으로 context 소비 전환 가능. 그러나 candidates 필터링 로직이 SceneCard에 있으므로 props 유지가 깔끔함.
- `onCandidateSelect` — `callbacks.onUpdateScene({ image_url: imageUrl })` 래핑. context로 전환 가능하나, 의미적으로 SceneImagePanel 전용 콜백이므로 props 유지.

**변경**: SceneImagePanel 함수 상단에 `useSceneContext()` 호출. 4개 props 제거, context에서 소비. `SceneImagePanelProps` 타입에서 해당 4개 필드 제거.

SceneCard에서 SceneImagePanel 호출 부분도 4개 props 전달 제거.

**축소**: 7개 → 3개 props

#### 2-2. SceneActionBar.tsx

**현재 props**: `scene, sceneIndex, qualityScore, sceneMenuOpen, isMarkingStatus, onGenerateImage, onGeminiEditOpen, onClothingOpen, onMarkSuccess, onMarkFail, onSceneMenuToggle, onSceneMenuClose, onUpdateScene, onRemoveScene, showToast, compact`

**context 전환 대상**:
- `qualityScore` → `data.qualityScore`
- `sceneMenuOpen` → `data.sceneMenuOpen`
- `isMarkingStatus` → `data.isMarkingStatus`
- `onGenerateImage` → `callbacks.onGenerateImage`
- `onMarkSuccess` → `callbacks.onMarkSuccess`
- `onMarkFail` → `callbacks.onMarkFail`
- `onSceneMenuToggle` → `callbacks.onSceneMenuToggle`
- `onSceneMenuClose` → `callbacks.onSceneMenuClose`
- `onUpdateScene` → `callbacks.onUpdateScene`
- `onRemoveScene` → `callbacks.onRemoveScene`
- `showToast` → `callbacks.showToast`

**props 유지**:
- `scene` — 핵심 데이터
- `sceneIndex` — 표시 용도. 대안: context data에 추가. 그러나 SceneCard props에서 직접 전달하는 게 자연스러움. **context data에 `sceneIndex` 추가**하여 통일.
- `onGeminiEditOpen` — SceneCard 로컬 state setter. context에 넣기 부적절 (모달 open은 SceneCard 내부 관심사)
- `onClothingOpen` — 동일. SceneCard 로컬 state
- `compact` — UI 레이아웃 힌트. SceneCard에서만 사용하는 로컬 결정

**변경**: 11개 props 제거, context 소비. `SceneActionBarProps`에서 해당 필드 제거.

**축소**: 16개 → 5개 props (`scene, sceneIndex, onGeminiEditOpen, onClothingOpen, compact`)

> `sceneIndex`는 context data에도 추가하지만, SceneActionBar에서는 직접 context에서 가져와도 됨. 설계 일관성을 위해 context 소비로 통일하면 4개.

**최종 결정**: `sceneIndex`도 context data에 추가. SceneActionBar는 context에서 소비. props 4개: `scene, onGeminiEditOpen, onClothingOpen, compact`.

#### 2-3. SceneEssentialFields.tsx

**현재 props**: `scene, structure, onUpdateScene, onSpeakerChange, onImageUpload, ttsState, onTTSPreview, onTTSRegenerate, audioPlayer`

**context 전환 대상**:
- `structure` → `data.structure`
- `onUpdateScene` → `callbacks.onUpdateScene`
- `onSpeakerChange` → `callbacks.onSpeakerChange`
- `onImageUpload` → `callbacks.onImageUpload`
- `ttsState` → `data.ttsState`
- `onTTSPreview` → `callbacks.onTTSPreview`
- `onTTSRegenerate` → `callbacks.onTTSRegenerate`
- `audioPlayer` → `callbacks.audioPlayer`

**props 유지**:
- `scene` — 핵심 데이터

**축소**: 9개 → 1개 prop

#### 2-4. ScenePromptFields.tsx

**현재 props**: `scene, loraTriggerWords, characterLoras, selectedCharacterId, basePromptA, onUpdateScene, showAdvancedSettings`

**context 전환 대상**:
- `loraTriggerWords` → `data.loraTriggerWords`
- `characterLoras` → `data.characterLoras`
- `selectedCharacterId` → `data.selectedCharacterId`
- `basePromptA` → `data.basePromptA`
- `onUpdateScene` → `callbacks.onUpdateScene`

**props 유지**:
- `scene` — 핵심 데이터
- `showAdvancedSettings` — UIStore에서 직접 가져올 수도 있으나, 이 값은 SceneCard가 이미 UIStore에서 구독 중. context에 넣기엔 범위가 다름 (Scene context가 아닌 UI context). **ScenePromptFields 내부에서 직접 `useUIStore` 구독**으로 변경. 이미 SceneEssentialFields가 이 패턴을 사용 중.

**축소**: 7개 → 1개 prop

#### 2-5. SceneSettingsFields.tsx

**현재 props**: `scene, hasMultipleSpeakers, tagsByGroup, sceneTagGroups, isExclusiveGroup, onUpdateScene, characterAName, characterBName, selectedCharacterId, selectedCharacterBId, buildNegativePrompt, buildScenePrompt, showToast`

**context 전환 대상**:
- `tagsByGroup` → `data.tagsByGroup`
- `sceneTagGroups` → `data.sceneTagGroups`
- `isExclusiveGroup` → `data.isExclusiveGroup`
- `onUpdateScene` → `callbacks.onUpdateScene`
- `characterAName` → `data.characterAName`
- `characterBName` → `data.characterBName`
- `selectedCharacterId` → `data.selectedCharacterId`
- `selectedCharacterBId` → `data.selectedCharacterBId`
- `buildNegativePrompt` → `callbacks.buildNegativePrompt`
- `buildScenePrompt` → `callbacks.buildScenePrompt`
- `showToast` → `callbacks.showToast`

**props 유지**:
- `scene` — 핵심 데이터
- `hasMultipleSpeakers` — SceneCard에서 `isMultiCharStructure(structure)` 계산. **context에 추가하지 않고** SceneSettingsFields 내부에서 직접 계산하도록 변경. `data.structure`에서 파생 가능.

**축소**: 13개 → 1개 prop

#### 2-6. SceneGeminiModals.tsx

**현재 props (SceneCard에서 전달)**: `scene, qualityScore, geminiEditOpen, setGeminiEditOpen, geminiTargetChange, setGeminiTargetChange, onApplyPromptEdit, showToast, selectedCharacterId`

**context 전환 대상**:
- `qualityScore` → `data.qualityScore`
- `showToast` → `callbacks.showToast`
- `selectedCharacterId` → `data.selectedCharacterId`

**props 유지**:
- `scene` — 핵심 데이터
- `geminiEditOpen`, `setGeminiEditOpen` — SceneCard 로컬 state
- `geminiTargetChange`, `setGeminiTargetChange` — SceneCard 로컬 state
- `onApplyPromptEdit` — `callbacks.onUpdateScene` 래핑. 그러나 매핑 로직(`{ image_prompt: edited }`)이 있으므로 props 유지가 명확.

**축소**: 9개 → 6개 props

#### 2-7. SceneEnvironmentPicker.tsx (보너스)

**현재 props**: `contextTags, tagsByGroup, onUpdate`

SceneCard에서 호출 시:
```tsx
<SceneEnvironmentPicker
  contextTags={scene.context_tags}
  tagsByGroup={tagsByGroup}
  onUpdate={(tags) => onUpdateScene({ context_tags: tags })}
/>
```

**context 전환 대상**:
- `tagsByGroup` → `data.tagsByGroup`

**props 유지**:
- `contextTags` — scene에서 파생
- `onUpdate` — onUpdateScene 래핑

**축소**: 3개 → 2개 props (미미하지만 정합성)

#### 2-8. SceneClothingModal.tsx (보너스)

**현재 props**: `scene, onClose, onSave, showToast`

**context 전환 대상**:
- `showToast` → `callbacks.showToast`

**props 유지**:
- `scene`, `onClose`, `onSave` — 모달 제어는 로컬 관심사

**축소**: 4개 → 3개 props

### context 전환 서브컴포넌트 요약

| 서브컴포넌트 | Before props | After props | context 소비 수 |
|------------|-------------|-------------|----------------|
| SceneImagePanel | 7 | 3 | 4 |
| SceneActionBar | 16 | 4 | 12 |
| SceneEssentialFields | 9 | 1 | 8 |
| ScenePromptFields | 7 | 1 | 6 |
| SceneSettingsFields | 13 | 1 | 11 |
| SceneGeminiModals | 9 | 6 | 3 |
| SceneEnvironmentPicker | 3 | 2 | 1 |
| SceneClothingModal | 4 | 3 | 1 |
| **합계** | **68** | **21** | **46** |

> DoD "6개 이상" 충족: 8개 서브컴포넌트 모두 전환.

### 동작 정의

**Before**: SceneCard가 props를 받아 서브컴포넌트에 개별 전달. 서브컴포넌트는 자신의 props만 소비.
**After**: 서브컴포넌트가 `useSceneContext()`로 직접 context 소비. SceneCard는 서브에 최소 props(scene + 로컬 state)만 전달.

### 엣지 케이스

1. **SceneToolsContent**: 이미 자체적으로 store 구독. context 전환 대상 아님 (props 없음).
2. **showAdvancedSettings**: ScenePromptFields에서 기존 props → `useUIStore` 직접 구독으로 변경. SceneCard 내부 `showAdvancedSettings` 사용은 유지 (이미 UIStore 구독).
3. **hasMultipleSpeakers**: SceneSettingsFields에서 props 대신 `data.structure`에서 직접 계산.

### 영향 범위

- `SceneImagePanel.tsx`: props 타입 축소 + context 호출 추가
- `SceneActionBar.tsx`: props 타입 축소 + context 호출 추가
- `SceneEssentialFields.tsx`: props 타입 축소 + context 호출 추가
- `ScenePromptFields.tsx`: props 타입 축소 + context 호출 추가 + `useUIStore` 직접 구독
- `SceneSettingsFields.tsx`: props 타입 축소 + context 호출 추가 + `hasMultipleSpeakers` 내부 계산
- `SceneGeminiModals.tsx`: props 타입 축소 + context 호출 추가
- `SceneEnvironmentPicker.tsx`: props 타입 축소 + context 호출 추가
- `SceneClothingModal.tsx`: props 타입 축소 + context 호출 추가

### 테스트 전략

- 서브컴포넌트별 기존 테스트가 있으면 Provider 래핑 추가
- 신규: `SceneContext.test.tsx`에 "서브컴포넌트에서 context 소비 시 정상 동작" 통합 테스트 추가

### Out of Scope

- SceneCard 하위의 3차 컴포넌트 (예: `DebugTabContent`, `SceneCharacterActions`, `ComposedPromptPreview`) — 이들은 서브컴포넌트가 직접 props로 전달. 추후 태스크에서 필요 시 전환.
- `SceneToolsContent` — 이미 store 직접 구독 패턴.

---

## DoD 3: ScenesTab의 action handler glue code가 SceneProvider 내부로 이동

### 구현 방법

**파일**: `frontend/app/components/studio/ScenesTab.tsx`

SP-095에서 이미 `<SceneProvider value={...}>` 래핑이 완료됨. SP-096에서는:

1. **SceneCard JSX에서 34개 props 제거**: SceneCard에 `scene`과 `sceneIndex`만 전달.

```tsx
<SceneCard
  key={currentScene.client_id}
  scene={currentScene}
  sceneIndex={currentSceneIndex}
/>
```

2. **Provider value는 SP-095에서 구성한 그대로 유지**. 추가로:
   - `sceneMenuOpen: sceneMenuOpen === currentScene.client_id` (boolean) 추가
   - `sceneIndex: currentSceneIndex` 추가

3. **glue code 정의**: ScenesTab에서 SceneCard에 전달하기 위해 존재하는 중간 콜백들. SP-095 Provider value에 이미 이동됨. SP-096에서 SceneCard props 제거로 glue code의 이유가 사라짐.

구체적 glue code (ScenesTab L290~L349에서 inline 정의됨):
- `() => handleRemoveScene(currentScene.client_id)` → Provider callbacks.onRemoveScene
- `(speaker) => handleSpeakerChange(currentScene, speaker)` → Provider callbacks.onSpeakerChange
- `(file) => handleImageUpload(currentScene.client_id, file)` → Provider callbacks.onImageUpload
- `() => handleGenerateImage(currentScene)` → Provider callbacks.onGenerateImage
- `(tags) => applyMissingImageTags(currentScene, tags)` → Provider callbacks.onApplyMissingTags
- `(src, candidates) => useUIStore.getState().set({...})` → Provider callbacks.onImagePreview
- `() => handleMarkSuccess(currentScene)` → Provider callbacks.onMarkSuccess
- `() => handleMarkFail(currentScene)` → Provider callbacks.onMarkFail

이 glue code들은 이미 Provider value에 있으므로, SceneCard에서 props를 제거하면 ScenesTab에서 중복 전달이 사라진다.

### 동작 정의

**Before**: ScenesTab에서 13개+ inline 콜백을 SceneCard props로 전달. 50줄 이상의 JSX props 나열.
**After**: ScenesTab에서 SceneCard에 2개 props만 전달. Provider value 구성은 SP-095에서 이미 완료.

### 엣지 케이스

1. **ScenesTab에서 SceneCard 외 다른 곳이 동일 handler를 사용하는 경우**: `SceneListPanel`, `SceneNavHeader` 등은 별도 props를 받고 있어 영향 없음.
2. **Provider value 구성 시점**: `currentScene`이 null이면 Provider 렌더링 자체가 안 됨 (`currentScene &&` 조건 내부). 안전.

### 영향 범위

- `ScenesTab.tsx`: SceneCard JSX 간소화 (50줄 → 5줄)

### 테스트 전략

- 기존 ScenesTab 테스트에서 SceneCard props 검증 부분이 있으면 Provider + 2 props로 변경
- E2E: Direct 탭 전체 기능 동작 확인

### Out of Scope

- SceneListPanel, SceneNavHeader 등 ScenesTab 내 다른 컴포넌트의 props 구조 변경
- Provider value 구성 로직의 리팩토링 (이미 SP-095에서 정의)

---

## DoD 4: 기존 Direct 탭 모든 기능 동일 동작 (E2E 통과)

### 구현 방법

코드 변경이 아닌 검증 항목.

### 테스트 전략

기존 Playwright E2E 테스트 스위트 실행:
- Direct 탭 로딩
- 씬 선택/이동
- 이미지 생성 버튼 클릭
- AI Edit 모달 열기/닫기
- 씬 삭제
- 프롬프트 필드 편집
- 설정 필드 편집
- TTS 미리듣기
- Clothing 모달

### Out of Scope

- 새 E2E 테스트 작성 (기존 테스트로 충분)

---

## DoD 5: 시각적 변경 없음 (VRT 차이 0)

### 구현 방법

코드 변경이 아닌 검증 항목. 모든 변경은 props → context 참조 경로만 변경하므로 렌더 출력은 동일해야 함.

### 테스트 전략

Playwright VRT 실행: Direct 탭 스냅샷 비교, 차이 0px 확인.

### Out of Scope

- UI 개선/디자인 변경

---

## SceneContext.tsx 타입 변경 요약

SP-095 완료 후 현재 `SceneDataContext`에 없는 필드 2개를 추가해야 함:

```diff
export type SceneDataContext = {
+ sceneMenuOpen: boolean;
+ sceneIndex: number;
  imageValidationResult?: ImageValidation;
  qualityScore?: { match_rate: number; missing_tags: string[] } | null;
  // ... 기존 필드 유지
};
```

SP-095에서 추가된 TTS 필드(`ttsState`)는 이미 반영됨. callbacks에도 TTS 3개 필드 이미 반영됨.

---

## 변경 파일 전체 목록

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `SceneContext.tsx` | 타입 추가 | `sceneMenuOpen`, `sceneIndex` 2필드 |
| `SceneCard.tsx` | props 축소 + context 소비 | 36개 → 2개 props |
| `ScenesTab.tsx` | SceneCard JSX 간소화 | 50줄 → 5줄 |
| `SceneImagePanel.tsx` | context 소비 전환 | 4개 props 제거 |
| `SceneActionBar.tsx` | context 소비 전환 | 12개 props 제거 |
| `SceneEssentialFields.tsx` | context 소비 전환 | 8개 props 제거 |
| `ScenePromptFields.tsx` | context 소비 전환 | 5개 props 제거 + useUIStore |
| `SceneSettingsFields.tsx` | context 소비 전환 | 11개 props 제거 + 내부 계산 |
| `SceneGeminiModals.tsx` | context 소비 전환 | 3개 props 제거 |
| `SceneEnvironmentPicker.tsx` | context 소비 전환 | 1개 props 제거 |
| `SceneClothingModal.tsx` | context 소비 전환 | 1개 props 제거 |

총 11개 파일 변경.

---

## 리렌더링 영향 분석

### 현재 (Props)
- ScenesTab에서 state 변경 → SceneCard 리렌더 → 모든 서브 리렌더

### After (Context)
- ScenesTab에서 state 변경 → Provider value 변경 → context 소비 서브컴포넌트 리렌더
- SceneCard 자체는 `scene` + `sceneIndex`만 의존하므로 다른 context 값 변경 시에도 리렌더 발생 (Provider children)
- **결론**: 리렌더 범위는 동일하거나 약간 넓어질 수 있으나, 현재 SceneCard 내부에 memo가 없으므로 실질적 차이 없음. 성능 최적화(memo/selector)는 후속 태스크.

### Context 분할 고려

현재 `data` + `callbacks` 2개 context로 이미 분리됨 (SP-095 설계). callbacks는 참조 안정적(handleUpdateScene 등은 ScenesTab에서 안정적 참조), data는 scene 변경마다 갱신. 이 구조로 충분.

---

## 구현 순서 (권장)

1. `SceneContext.tsx` — `sceneMenuOpen`, `sceneIndex` 필드 추가
2. `ScenesTab.tsx` — Provider value에 신규 필드 반영
3. `SceneCard.tsx` — props 축소 + context 소비 전환
4. 서브컴포넌트 6개 — 각각 context 소비 전환 (병렬 가능)
5. 보너스 서브 2개 — SceneEnvironmentPicker, SceneClothingModal
6. 테스트 실행 + VRT

> 3과 4는 의존 관계 있음 (SceneCard가 서브에 전달하는 props 제거 ↔ 서브가 context에서 소비). **동시에** 진행해야 함.
