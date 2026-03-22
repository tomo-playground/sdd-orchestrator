# SP-048 상세 설계 (How)

> 설계 승인 후 구현 착수. 적정 깊이: 시그니처+상호작용 레벨.

## DoD-1: 음성 톤 토스트
- **구현**: `DirectorControlPanel.tsx` — Props에 `showToast` 추가. `handleEmotionClick(p)`에서 `selectedEmotionPreset === p.id`면 무시(재클릭), 다르면 `setGlobalEmotion` 호출 + `showToast("음성 톤: ${p.label} 적용", "success")`
- **동작**: 미선택→밝게 클릭 = 활성화+토스트. 밝게→차분 클릭 = 전환+토스트. 밝게→밝게 재클릭 = 무시(토스트 없음)
- **엣지**: 캐릭터 미선택 상태에서도 프리셋 저장 허용 (기존 동작 유지). showToast가 null이면 호출 안 함 (안전가드)
- **영향**: `ScenesTab.tsx`에서 `showToast`를 DirectorControlPanel에 props로 전달해야 함. autoSave 트리거 시점 변경 없음
- **테스트**: DirectorControlPanel 렌더 → emotion 버튼 클릭 → showToast 호출 검증. 같은 버튼 재클릭 → showToast 미호출 검증
- **OoS**: `setGlobalEmotion` 내부 로직 변경 금지. EMOTION_PRESETS 데이터 수정 금지

## DoD-2: BGM 분위기 토스트
- **구현**: `DirectorControlPanel.tsx` — `handleBgmClick(p)`에서 `selectedBgmPreset === p.id`면 무시, 다르면 `setRender(...)` 호출 + `showToast("BGM: ${p.label} 적용", "success")`
- **동작**: DoD-1과 동일 패턴. 재클릭 무시, 변경 시에만 토스트
- **엣지**: DoD-1과 동일
- **영향**: DoD-1과 동일 (showToast props 공유)
- **테스트**: BGM 버튼 클릭 → showToast 호출 검증. 재클릭 → 미호출 검증
- **OoS**: BGM_MOOD_PRESETS 데이터 수정 금지. setRender 내부 변경 금지

## DoD-3: 전체 적용 레이블 변경
- **구현**: `DirectorControlPanel.tsx:146` — 버튼 텍스트를 `전체 적용 ({sceneCount}씬)` → `TTS 전체 재생성 ({sceneCount}씬)`으로 변경
- **동작**: 버튼 텍스트만 변경. 기능 동작 동일
- **엣지**: 없음
- **영향**: 없음 (텍스트만)
- **테스트**: DirectorControlPanel 렌더 → 버튼 텍스트에 "TTS 전체 재생성" 포함 검증
- **OoS**: handleApplyAll 로직 변경 금지 (DoD-4에서 처리)

## DoD-4: 전체 적용 로딩 상태
- **구현**: `DirectorControlPanel.tsx` — Props에 `isApplying: boolean` 추가. 버튼에 `disabled={isApplying}` + 로딩 시 스피너+텍스트 변경. `ScenesTab.tsx`의 `handleApplyAll`에 `useState(isApplying)` 추가: confirm 후 true, finally에서 false
- **동작**: 전체 적용 클릭 → confirm 다이얼로그 → 확인 → 버튼 disabled + 스피너 "재생성 중..." → API 완료 → 버튼 복원 + 완료 토스트(기존)
- **엣지**: 실행 중 씬 전환은 허용 (백그라운드 작업). confirm에서 취소 시 로딩 시작 안 함
- **영향**: ScenesTab → DirectorControlPanel으로 `isApplying` props 전달 추가. 기존 `onApplyAll` props는 유지
- **테스트**: isApplying=true → 버튼 disabled + 스피너 표시 검증. isApplying=false → 정상 버튼 검증
- **OoS**: handleApplyAll의 API 호출 로직/에러 처리 변경 금지. confirm 다이얼로그 변경 금지

## DoD-5: Speaker 드롭다운 캐릭터 이름
- **구현**: `SceneEssentialFields.tsx` — 컴포넌트 내부에서 `useStoryboardStore`로 `selectedCharacterName`, `selectedCharacterBName` 직접 읽기. `<option value="A">`의 텍스트를 `selectedCharacterName ? "A: ${selectedCharacterName}" : "Actor A"`로 변경. B도 동일 패턴
- **동작**: 캐릭터 이름 있음 → "A: 재민" / "B: 하은" 표시. 캐릭터 미선택 → "Actor A" / "Actor B" fallback
- **엣지**: Narrator 옵션은 변경 없음 ("Narrator" 유지). 캐릭터 이름이 매우 긴 경우 → select 자체가 늘어나지만 허용 (CSS truncate 불필요, select 특성상)
- **영향**: SceneEssentialFields에 store import 추가. SceneCard props 변경 없음
- **테스트**: selectedCharacterName="재민" 상태에서 렌더 → option 텍스트 "A: 재민" 검증. null 상태 → "Actor A" 검증
- **OoS**: SceneCard props 구조 변경 금지. speaker 변경 로직 변경 금지. select UI 스타일 변경 금지

## DoD-6: Consistency 데이터 없을 때 "--" 표시
- **구현**: `ConsistencyPanel.tsx:51-54` — `data.scenes.length === 0`이면 overall 표시를 `{Math.round(data.overall_consistency * 100)}%` 대신 `"--"` 표시
- **동작**: API가 scenes 빈 배열 반환 → overall "--" + "No consistency data yet." 메시지. scenes 있음 → 기존대로 퍼센트 표시
- **엣지**: scenes=[] 이지만 overall_consistency > 0인 경우(현재 발생 중) → "--"으로 오버라이드 (프론트 판단 우선)
- **영향**: ConsistencyPanel만 수정. StoryboardInsights의 Avg Match는 이미 "--" 처리되어 있어 영향 없음
- **테스트**: data.scenes=[] → "--" 표시 검증. data.scenes=[{...}] → 퍼센트 표시 검증
- **OoS**: Backend API 응답 변경 금지. useConsistency hook 변경 금지. DriftHeatmap/DriftDetailView 변경 금지

## DoD-7: 화풍 섹션 제거
- **구현**: `DirectorControlPanel.tsx:127-138` — Style Profile 읽기전용 블록 전체 삭제. `Palette` import 및 `currentStyleProfile` 관련 store 구독도 제거
- **동작**: DirectorControlPanel에서 화풍 표시 사라짐. Context Strip의 `플랫 애니메` 배지는 유지 (ScenesTab.tsx:221-227)
- **엣지**: currentStyleProfile이 null인 경우에도 원래 조건부 렌더라 영향 없음
- **영향**: DirectorControlPanel에서 `useRenderStore` 구독 필드가 `selectedBgmPreset`만 남음. `currentStyleProfile` 제거. `Palette` icon import 제거
- **테스트**: DirectorControlPanel 렌더 → "화풍" 텍스트가 DOM에 없음 검증
- **OoS**: Context Strip(ScenesTab.tsx)의 화풍 배지 변경 금지. useRenderStore의 다른 구독 변경 금지

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|---------|
| `DirectorControlPanel.tsx` | Props에 showToast/isApplying 추가, 토스트 호출, 레이블 변경, 로딩 상태, 화풍 섹션 삭제 |
| `ScenesTab.tsx` | isApplying state 추가, showToast/isApplying를 DirectorControlPanel에 전달 |
| `SceneEssentialFields.tsx` | useStoryboardStore에서 캐릭터 이름 읽기, option 텍스트 변경 |
| `ConsistencyPanel.tsx` | scenes 빈 배열일 때 overall "--" 표시 |

**총 4개 파일** (제약 6개 이하 충족)
