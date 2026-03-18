# Storyboard Data Integrity (씬 데이터 무결성 보장)

**상태**: 계획 완료
**우선순위**: P0 (최우선)
**발단**: Storyboard 1128 — UI에 7개 씬이 보이지만 DB에 0개. 수동 저장 시 500 에러 (FK 위반). 칸반 상태도 draft로 표시 (2026-03-19)

---

## 문제 분석

### 증상
1. 새 스토리보드 생성 후 AutoRun으로 씬/이미지/TTS 생성 완료
2. UI(Direct 탭)에는 7개 씬이 정상 표시 (localStorage/Zustand)
3. DB에는 씬 0개, media_assets 0개 → 칸반 "초안" 표시
4. 수동 저장(Ctrl+S) → PUT /storyboards/{id} 500 에러 (FK 위반)

### 근본 원인 3가지

#### 원인 1: Frontend 상태 오염 (localStorage 누수)
- `useStoryboardStore` persist 키가 `sb_{id}`로 분리됨 (03-19 수정)
- 그러나 새 스토리보드 생성 시 `:new` 키에 이전 씬 데이터가 잔류
- `resetAllStores()` 호출 시점과 씬 생성 시점의 경쟁 조건

#### 원인 2: Auto-Save 스킵 후 미복구
- `autoSave.ts` 스킵 조건 6가지 중 `isAutoRunning=true`가 핵심
- AutoRun은 자체 persist를 호출하지만, 실패 시 복구 경로 없음
- AutoRun 종료 후 `isDirty` 변경 구독(line 85-89)이 있으나, `isDirty`가 이미 `true`면 변경 이벤트가 발생하지 않아 save 트리거 누락

#### 원인 3: Backend FK 무방비
- `create_scenes()`에서 `image_asset_id`, `tts_asset_id`, `background_id` FK 유효성 검증 없이 INSERT
- 존재하지 않는 asset ID → PostgreSQL IntegrityError → 500 (사용자에게 무의미한 에러)
- `update_storyboard_in_db()`에서도 동일 — 예외 미처리

---

## 구현 계획

### Sprint A: Backend 방어 (FK 검증 + 에러 처리)

#### A-1. `create_scenes()` FK 유효성 검증
- `scene_builder.py`에서 INSERT 전 FK 존재 여부 확인
- 존재하지 않는 `image_asset_id`/`tts_asset_id`/`background_id` → `null`로 치환 + 경고 로그
- 기존 데이터는 보존, 깨진 참조만 제거

```python
# 검증 대상 FK 필드
FK_FIELDS = ["image_asset_id", "tts_asset_id", "background_id", "environment_reference_id"]

def _validate_scene_fks(db: Session, scenes: list[StoryboardScene]) -> list[StoryboardScene]:
    """존재하지 않는 FK 참조를 null로 치환."""
    # 모든 참조 ID를 수집 → 한 번의 IN 쿼리로 존재 확인
    # 미존재 ID → null 치환 + logger.warning
```

#### A-2. `update_storyboard_in_db()` IntegrityError 처리
- `db.commit()` 시 IntegrityError catch → 400 응답 + 구체적 에러 메시지
- Frontend가 에러를 이해하고 대응할 수 있도록 (예: "이미지 에셋이 삭제되었습니다. 재생성해주세요")

#### A-3. 테스트
- `test_scene_builder.py`: 잘못된 FK로 create_scenes 호출 → null 치환 확인
- `test_storyboard_crud.py`: PUT with invalid FK → 정상 저장 (null 치환) 확인

**예상 파일 변경**: `scene_builder.py`, `crud.py`, + 테스트 2개
**예상 공수**: 소

---

### Sprint B: Auto-Save 복구 경로 강화

#### B-1. AutoRun 종료 시 강제 save 트리거
- `autoSave.ts` line 85-89: `isAutoRunning false→true` 전환 시 `isDirty` 상태와 무관하게 `scheduleSave()` 호출
- 현재: `if (isDirty) scheduleSave()` — isDirty가 변경 이벤트 없이 이미 true면 누락
- 수정: isDirty true면 즉시 `scheduleSave()`, false여도 `setIsDirty(true)` 후 `scheduleSave()`

```typescript
// Before
if (prevState.isAutoRunning && !state.isAutoRunning) {
  const { isDirty } = useStoryboardStore.getState();
  if (isDirty) scheduleSave();
}

// After
if (prevState.isAutoRunning && !state.isAutoRunning) {
  // AutoRun 종료 시 항상 save 시도 (AutoRun이 persist 실패했을 수 있음)
  const { scenes } = useStoryboardStore.getState();
  if (scenes.length > 0) {
    useStoryboardStore.getState().setIsDirty(true);
    scheduleSave();
  }
}
```

#### B-2. AutoRun 자체 persist 실패 시 로깅 + isDirty 유지
- `autopilotActions.ts`에서 `persistStoryboard()` 호출 후 실패 시 `isDirty=true` 유지
- 현재: persist 실패해도 isDirty가 false로 설정될 수 있음

#### B-3. 3회 실패 후 사용자 알림 강화
- `consecutiveFailures >= MAX_FAILURES` 시 Toast만 표시 → **UI 배너로 승격**
- "자동 저장에 실패했습니다. 수동으로 저장해주세요" 배너 + 수동 저장 버튼

**예상 파일 변경**: `autoSave.ts`, `autopilotActions.ts`, UI 컴포넌트 1개
**예상 공수**: 소

---

### Sprint C: Frontend 상태 오염 방어

#### C-1. 새 스토리보드 진입 시 localStorage 정리
- `useStudioInitialization`에서 `?new=true` 진입 시:
  - `:new` 키의 localStorage 데이터 완전 삭제
  - `resetAllStores()` 후 씬 데이터가 비어있는지 assert

#### C-2. 스토리보드 전환 시 stale 데이터 감지
- `?id=X`로 진입 시 DB에서 가져온 씬과 localStorage 씬을 비교
- localStorage에 씬이 있지만 DB에 없으면 → "저장되지 않은 씬이 있습니다" 확인 다이얼로그
  - "저장" → persistStoryboard() 호출
  - "삭제" → localStorage 정리 + DB 데이터로 복원

#### C-3. 씬 생성 후 즉시 dirty 플래그 보장
- `syncToGlobalStore()` 호출 시 `isDirty=true` 설정 보장 (현재도 setScenes가 isDirty를 설정하지만, 타이밍 이슈 확인)

**예상 파일 변경**: `useStudioInitialization.ts`, `storyboardActions.ts`, `page.tsx`
**예상 공수**: 중

---

## 검증 시나리오

| # | 시나리오 | 기대 결과 |
|---|---------|----------|
| 1 | 새 영상 → Script 생성 → 페이지 새로고침 | 씬이 DB에 저장됨 (auto-save) |
| 2 | 새 영상 → AutoRun 완료 → 칸반 확인 | "제작 중" 또는 "렌더 완료" 표시 |
| 3 | PUT with invalid image_asset_id | 500 아닌 정상 저장 (null 치환) |
| 4 | AutoRun persist 실패 → AutoRun 종료 | 자동 재시도 → save 완료 |
| 5 | 스토리보드 전환 (A→B) → B로 돌아옴 | A의 씬 데이터가 B에 오염 안 됨 |
| 6 | 3회 연속 save 실패 | UI 배너 "수동 저장 필요" 표시 |

---

## 우선순위 근거

- **데이터 유실 위험**: 사용자가 생성한 콘텐츠(씬, 이미지, TTS)가 DB에 저장되지 않으면 페이지 새로고침 시 영구 소실
- **500 에러**: FK 미검증으로 수동 저장도 실패 → 사용자 복구 수단 없음
- **칸반 오표시**: 실제 작업 상태와 UI 불일치 → 워크플로우 혼란
- Enum ID 정규화/ComfyUI 전환보다 선행 필수 (데이터 안전성 > 기능 개선)
