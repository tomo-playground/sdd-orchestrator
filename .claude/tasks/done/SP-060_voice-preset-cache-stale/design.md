## 상세 설계 (How)

### DoD-1: VoicePresetSelector 마운트 시 항상 최신 데이터

**구현 방법**:
- `useRenderStore.ts`에서 `voicePresetsLoaded` 필드와 `if (get().voicePresetsLoaded) return;` 가드 제거
- `fetchVoicePresets`는 호출될 때마다 항상 API fetch 수행
- `voicePresetsLoaded`를 `TRANSIENT_KEYS`와 `initialState`, 타입 정의에서도 제거

**동작 정의**:
- Before: 세션 내 최초 1회만 fetch → 이후 컴포넌트 재마운트 시 stale 데이터 사용
- After: 컴포넌트 마운트 시마다 fresh fetch → 항상 최신 데이터

**엣지 케이스**:
- 동일 페이지에서 복수 컴포넌트가 동시 마운트 시 (예: `StageTab` + `VoicePresetSelector`) 중복 요청 발생 가능 → 15개 아이템의 경량 GET이므로 무해. 결과가 동일하므로 state도 동일하게 수렴.
- API 실패 시 기존 동작 유지: `catch`에서 `console.warn`, `voicePresets`는 이전 값 유지

**영향 범위**:
- `StageTab.tsx`, `VoiceStyleSection.tsx`도 동일 패턴(`useEffect → fetchVoicePresets`)으로 호출하므로 자동으로 혜택
- `StageCharactersSection`, `StageVoiceSection`은 props로 받으므로 영향 없음

**테스트 전략**:
- 기존 테스트 "skips fetch when already loaded" 제거
- "always fetches on call" 테스트 추가: `voicePresets`에 이전 데이터가 있어도 호출 시 새 데이터로 교체 확인
- 기존 "fetches and stores" / "handles failure" 테스트는 `voicePresetsLoaded` 참조 부분만 제거

**Out of Scope**:
- 중복 요청 방지(in-flight dedup) — 현재 규모(15개 프리셋)에서 불필요
- Voices 관리 페이지(`useVoicePresets` hook) 수정 — 이미 매번 fresh fetch

### DoD-2: Voices 관리 페이지 변경 후 캐릭터 편집 즉시 반영

**구현 방법**: DoD-1의 `voicePresetsLoaded` 제거로 자동 달성. 별도 구현 불필요.

**동작 정의**:
- Before: Voices에서 프리셋 추가/수정/삭제 → 캐릭터 편집 드롭다운 stale
- After: 캐릭터 편집 페이지 진입 시 `useEffect → fetchVoicePresets` → fresh fetch → 최신 반영

**테스트 전략**: DoD-1 테스트로 커버됨

### DoD-3: 기존 기능 regression 없음

**구현 방법**: 변경 없음 — `fetchVoicePresets`의 fetch/set 로직은 동일, 가드만 제거.

**테스트 전략**: 기존 "fetches and stores" / "handles failure" 테스트가 계속 통과하는지 확인

### 변경 파일 요약 (2개)

| 파일 | 변경 |
|------|------|
| `frontend/app/store/useRenderStore.ts` | `voicePresetsLoaded` 필드/가드/TRANSIENT_KEYS 제거 |
| `frontend/app/store/__tests__/useRenderStore.test.ts` | "skips when loaded" 테스트 삭제, `voicePresetsLoaded` 참조 제거 |
