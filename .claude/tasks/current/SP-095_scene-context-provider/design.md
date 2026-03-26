# SP-095 설계

## 구현 방법

### 1. `SceneContext.tsx` — TTS 4필드 추가

**파일**: `frontend/app/components/storyboard/SceneContext.tsx`

`SceneDataContext` 타입에 TTS 관련 1필드 추가:
```
ttsState?: TTSPreviewState;
```

`SceneCallbacksContext` 타입에 TTS 관련 3필드 추가:
```
onTTSPreview?: () => void;
onTTSRegenerate?: () => void;
audioPlayer?: AudioPlayer;
```

import에 `TTSPreviewState` (`../../types`), `AudioPlayer` (`../../hooks/useAudioPlayer`) 추가.

> `pinnedSceneOrder` 필드는 이미 `SceneDataContext`에 정의되어 있지만 SceneCard props에는 없다. 이 태스크에서는 건드리지 않는다(기존 호환성 유지).

### 2. `ScenesTab.tsx` — SceneProvider로 SceneCard 래핑

**파일**: `frontend/app/components/studio/ScenesTab.tsx`

변경 사항:
- `SceneProvider`를 `../storyboard/SceneContext`에서 import
- SceneCard 렌더링 부분(L290~L353)에서 `<SceneProvider value={...}>` 래핑 추가
- Context value 구성: 기존 SceneCard에 전달하는 props를 `data`/`callbacks` 2개 객체로 매핑

구체적 구조:
```tsx
<SceneProvider value={{
  data: {
    imageValidationResult,
    qualityScore,
    loraTriggerWords,
    characterLoras: resolvedCharacterLoras,
    tagsByGroup,
    sceneTagGroups,
    isExclusiveGroup,
    selectedCharacterId: resolvedCharacterId,
    basePromptA: resolvedBasePrompt,
    structure,
    characterAName: selectedCharacterName,
    characterBName: selectedCharacterBName,
    selectedCharacterBId,
    genProgress: imageGenProgress[currentScene.client_id] ?? null,
    isMarkingStatus: markingStatusSceneId === currentScene.client_id,
    ttsState: ttsPreview.previewStates.get(currentScene.client_id),
  },
  callbacks: {
    onUpdateScene: handleUpdateScene,
    onRemoveScene: () => handleRemoveScene(currentScene.client_id),
    onSpeakerChange: (speaker) => handleSpeakerChange(currentScene, speaker),
    onImageUpload: (file) => handleImageUpload(currentScene.client_id, file),
    onGenerateImage: () => handleGenerateImage(currentScene),
    onApplyMissingTags: (tags) => applyMissingImageTags(currentScene, tags),
    onImagePreview: (src, candidates) => useUIStore.getState().set({...}),
    onMarkSuccess: () => handleMarkSuccess(currentScene),
    onMarkFail: () => handleMarkFail(currentScene),
    buildNegativePrompt,
    buildScenePrompt,
    showToast,
    onSceneMenuToggle: () => sbSet({...}),
    onSceneMenuClose: () => sbSet({ sceneMenuOpen: null }),
    onTTSPreview: () => ttsPreview.previewScene(currentScene),
    onTTSRegenerate: () => ttsPreview.regenerate(currentScene),
    audioPlayer: ttsPreview.audioPlayer,
  },
}}>
  <SceneCard ... /> {/* props 그대로 유지 */}
</SceneProvider>
```

핵심 원칙: **기존 SceneCard props를 일절 제거하지 않는다**. Provider 래핑만 추가하여 하위 컴포넌트에서 `useSceneContext()` 접근이 가능하도록 한다. 이후 태스크에서 점진적으로 props를 context 소비로 전환.

### 3. `SceneCard.tsx` — 변경 없음

이 태스크에서 SceneCard 자체는 수정하지 않는다. DoD에 "기존 SceneCard props 모두 유지"라고 명시. SceneCard 내부에서 `useSceneContext()`를 호출하지 않아도 Provider 하위에 있으므로 하위 컴포넌트에서 접근 가능하다.

단, DoD "SceneCard 내부에서 useSceneContext() 접근 가능" 검증을 위해, SceneCard 상단에 다음 한 줄을 추가하여 context 접근 가능성을 확인할 수 있도록 한다:

```tsx
// SceneCard 함수 내부 최상단
const _ctx = useSceneContext(); // SP-095: context 접근 검증 (향후 props 대체 시 사용)
void _ctx; // lint unused 방지
```

> 대안: 이 검증 코드가 불필요하다면 테스트에서만 검증하고 SceneCard 코드 변경 없이 진행할 수도 있다. 리뷰어 판단에 따른다.

### 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `SceneContext.tsx` | TTS 4필드 타입 추가 (data 1 + callbacks 3) |
| `ScenesTab.tsx` | SceneProvider import + SceneCard 래핑 |
| `SceneCard.tsx` | useSceneContext import + 접근 검증 1줄 (선택적) |

## 테스트 전략

### 1. 유닛 테스트 (Vitest) — `SceneContext.test.tsx`

**위치**: `frontend/app/components/storyboard/__tests__/SceneContext.test.tsx`

| 테스트 케이스 | 검증 내용 |
|-------------|----------|
| Provider 없이 useSceneContext 호출 시 에러 throw | `"must be used within a SceneProvider"` 메시지 확인 |
| Provider 내부에서 data/callbacks 접근 | TTS 4필드 포함 전체 필드 접근 가능 확인 |
| TTS 필드 optional 동작 | ttsState undefined일 때 정상 렌더 |

### 2. 통합 테스트 (Vitest) — `ScenesTab.test.tsx`

**위치**: `frontend/app/components/studio/__tests__/ScenesTab.test.tsx`

| 테스트 케이스 | 검증 내용 |
|-------------|----------|
| SceneCard가 SceneProvider 내부에서 렌더 | useSceneContext() 호출 시 에러 없음 확인 |
| 기존 SceneCard props 전달 유지 | scene, sceneIndex 등 주요 props가 정상 전달되는지 확인 |

### 3. E2E / VRT (기존 테스트 활용)

| 검증 | 방법 |
|------|------|
| Direct 탭 기능 동일 동작 | 기존 Playwright E2E 스위트 실행 — 새 테스트 추가 불필요 |
| 시각적 변경 없음 | VRT 실행 — 차이 0 확인 |

### 테스트 핵심 원칙

- Provider 래핑은 **런타임 동작에 영향을 주지 않아야** 한다 (props 패스스루 유지)
- Context 접근 가능성만 검증하고, 실제 context 소비로의 전환은 후속 태스크에서 수행
