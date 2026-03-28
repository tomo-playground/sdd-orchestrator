# SP-097 설계

## 구현 방법

### 신규 파일

**`frontend/app/components/storyboard/ScenePropertyPanel.tsx`** (약 120줄)

SceneCard에서 Tier 2~4 (Customize, Scene Tags, Advanced) 섹션을 추출한 독립 컴포넌트.
`useSceneContext()`로 데이터/콜백을 소비한다 (SP-096 의존).

```
구조:
ScenePropertyPanel
├── [기본] 탭 (defaultOpen)
│   ├── ScenePromptFields — 프롬프트 입력/미리보기
│   ├── SceneEnvironmentPicker — 환경 태그 (environment, time, weather, particle)
│   └── SpeakerBadge (읽기전용 요약) — 현재 스피커 표시
└── [고급] 탭 (기본 접힘)
    ├── SceneSettingsFields — Scene Context Tags + Character Actions + Debug
    ├── SceneToolsContent — ControlNet, IP-Adapter, LoRA 오버라이드
    └── Success/Fail 버튼 (리뷰 모드)
```

**탭 전환**: `useState<"basic" | "advanced">("basic")`. 탭 버튼 2개를 상단에 배치.
고급 탭은 `showAdvancedSettings`(UIStore) 활성화 시에만 탭 버튼 노출. 비활성화 시 기본 탭만 표시.

**Context 소비**: `useSceneContext()`에서 `data` + `callbacks` 디스트럭처링.
scene 객체는 부모(SceneProvider)가 주입하므로 별도 props 불필요.

### 변경 파일

**`frontend/app/components/storyboard/SceneCard.tsx`**

Tier 2~4 JSX를 제거하고 `<ScenePropertyPanel />` 하나로 대체.
SceneCard는 Tier 1(Essential: 이미지 + 스크립트 + 액션바)만 유지.

변경 전:
```
SceneCard
├── Tier 1: SceneImagePanel + SceneActionBar + SceneEssentialFields
├── Tier 2: CollapsibleSection "Customize" (ScenePromptFields + SceneEnvironmentPicker)
├── Tier 3: CollapsibleSection "Scene Tags" (SceneSettingsFields) — showAdvancedSettings 조건
├── Tier 4: CollapsibleSection "Advanced" (SceneToolsContent + 리뷰 버튼) — showAdvancedSettings 조건
└── Modals (Gemini, Clothing)
```

변경 후:
```
SceneCard
├── Tier 1: SceneImagePanel + SceneActionBar + SceneEssentialFields
├── ScenePropertyPanel (Tier 2~4 통합)
└── Modals (Gemini, Clothing)
```

SceneCard에서 제거되는 import: `CollapsibleSection`, `ScenePromptFields`, `SceneEnvironmentPicker`, `SceneSettingsFields`, `SceneToolsContent`.
추가되는 import: `ScenePropertyPanel`.

SP-057(3패널 통합) 시 `<ScenePropertyPanel />`을 SceneCard 밖으로 이동하면 우측 패널이 된다.
현 단계에서는 SceneCard 내부에 인라인 배치하여 기존 동작을 유지한다.

**`frontend/app/components/storyboard/SceneContext.tsx`** (SP-096 완료 후 필요 시)

ScenePropertyPanel이 필요로 하는 데이터가 SceneDataContext에 이미 포함되어 있는지 검증.
현재 `SceneDataContext` 타입에 `showAdvancedSettings` 없음 -- UIStore에서 직접 소비하므로 추가 불필요.

### 변경하지 않는 파일

- `ScenePromptFields.tsx` — 그대로 재사용 (ScenePropertyPanel 기본 탭 내부)
- `SceneEnvironmentPicker.tsx` — 그대로 재사용
- `SceneSettingsFields.tsx` — 그대로 재사용 (ScenePropertyPanel 고급 탭 내부)
- `SceneToolsContent.tsx` — 그대로 재사용
- `SceneEssentialFields.tsx` — SceneCard Tier 1에 잔류

---

## 테스트 전략

### 단위 테스트 (Vitest + React Testing Library)

**`frontend/app/components/storyboard/__tests__/ScenePropertyPanel.test.tsx`**

1. **독립 렌더링**: SceneProvider로 감싼 상태에서 ScenePropertyPanel이 에러 없이 렌더링되는지 확인
2. **기본 탭 표시**: 기본 탭 활성 시 ScenePromptFields, SceneEnvironmentPicker 영역이 DOM에 존재
3. **고급 탭 표시**: 고급 탭 클릭 시 SceneToolsContent 영역이 DOM에 존재
4. **고급 탭 숨김**: `showAdvancedSettings=false`(UIStore mock) 시 고급 탭 버튼이 렌더링되지 않음
5. **Context 미제공 에러**: SceneProvider 없이 렌더링 시 `useSceneContext must be used within a SceneProvider` 에러 throw

### VRT (Playwright)

- SceneCard 내부에 ScenePropertyPanel을 인라인 배치한 상태에서 기존 Direct 탭 스크린샷과 비교
- 시각적 차이 0이 목표 (레이아웃 변경 없음, 내부 구조만 리팩터링)

### 수동 검증

- Direct 탭에서 Customize 펼침/접힘 동작 확인
- 고급 모드 토글(showAdvancedSettings) 시 고급 탭 노출/숨김 확인
- ControlNet/IP-Adapter 오버라이드 조작 후 이미지 생성 정상 동작 확인
