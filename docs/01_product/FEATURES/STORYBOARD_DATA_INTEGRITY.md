# Storyboard Data Integrity (씬 데이터 무결성 보장)

**상태**: 계획 완료 (코드 분석 검증 완료)
**우선순위**: P0 (최우선)
**발단**: Storyboard 1128 — UI에 7개 씬이 보이지만 DB에 0개. 수동 저장 시 500 에러 (FK 위반). 칸반 상태도 draft로 표시 (2026-03-19)
**병렬 작업**: Enum ID 정규화(P1 #2)와 파일 충돌 없음 — 동시 진행 가능

---

## 문제 분석

### 증상
1. 새 스토리보드 생성 후 AutoRun으로 씬/이미지/TTS 생성 완료
2. UI(Direct 탭)에는 7개 씬이 정상 표시 (localStorage/Zustand)
3. DB에는 씬 0개, media_assets 0개 → 칸반 "초안" 표시
4. 수동 저장(Ctrl+S) → PUT /storyboards/{id} 500 에러 (FK 위반)

### 근본 원인 3가지

#### 원인 1: Backend FK 부분 미검증
- `create_scenes()`의 4개 FK 중 **2개만 검증**:
  - ✅ `image_asset_id` — L261에서 `db.query(MediaAsset.id)` 검증 후 할당
  - ✅ `environment_reference_id` — L303에서 deferred 검증
  - ❌ `tts_asset_id` — `_build_scene_kwargs()` L174에서 `_exclude`에 미포함, 검증 없이 통과
  - ❌ `background_id` — 동일하게 검증 없이 통과 (참조: `backgrounds` 테이블)
- Association FK도 미검증: `SceneTag.tag_id`, `SceneCharacterAction.character_id`
- `update_storyboard_in_db()` L361~524에 IntegrityError 처리 전무

#### 원인 2: Auto-Save 3회 실패 후 Silent 중단
- `autoSave.ts` 6가지 스킵 조건 중 `isAutoRunning=true`가 핵심
- Autopilot persist 실패 → throw → isDirty 유지 → `isAutoRunning: false` 전환 시 autoSave 구독 발동 (복구 경로 존재)
- **실제 문제**: `consecutiveFailures >= 3` 도달 시 `console.warn`만 출력, **사용자 알림 없음**
- `cancelPendingSave()`는 debounce 타이머만 취소, 실행 중인 `persistStoryboard()` 미취소

#### 원인 3: localStorage 오염 (5개 누수 벡터)
- **LEAK-1 (CRITICAL)**: 고아 키 GC 부재 — 스토리보드 열 때마다 2개 키 생성, `resetAllStores()`는 현재 키 1세트만 삭제. 장기 사용 시 5MB 한도 도달
- **LEAK-2 (HIGH)**: `:new` 키 잔류 — POST 성공 후 persist 키가 `:sb_{newId}`로 전환되지만 `:new` 키 미삭제. 새로고침 시 이전 데이터 rehydrate
- **LEAK-3 (MEDIUM)**: 전환 시 rehydration 경합 — `setContext({ storyboardId: B })` 후 DB 로드 완료 전에 persist middleware가 `:sb_B`에서 stale 데이터 rehydrate
- **LEAK-4 (MEDIUM)**: `resetTransientStores()` localStorage 미정리 — 메모리만 초기화, `:sb_{이전ID}` 키 잔류
- **LEAK-5 (LOW)**: `setScenes()` 무조건 `isDirty: true` — DB 로드 경로에서도 불필요한 autoSave 트리거

---

## 구현 계획

### Sprint A: Backend FK 검증 + IntegrityError 처리

#### A-1. `tts_asset_id` / `background_id` 검증 추가
- `_build_scene_kwargs()`의 `_exclude`에 `tts_asset_id`, `background_id` 추가
- `create_scenes()` 본문에서 기존 `image_asset_id` 패턴과 동일하게 검증

```python
# 기존 패턴 (image_asset_id — L258~275) 동일 적용:
# _exclude에서 제외 → create_scenes 본문에서 db.query() 검증 → 미존재 시 None + warning
_exclude = {
    "tags", "character_actions", "scene_id",
    "image_asset_id",       # 기존
    "tts_asset_id",         # 추가
    "background_id",        # 추가
    "candidates",
}
```

- `tts_asset_id`: `MediaAsset.id` 참조 → 기존 image_asset_id와 동일한 쿼리
- `background_id`: `Background.id` 참조 → `backgrounds` 테이블 쿼리

#### A-2. Association FK 방어 (P1)
- `SceneTag` INSERT (L242~243): 존재하지 않는 `tag_id` → skip + warning
- `SceneCharacterAction` INSERT (L248~255): 존재하지 않는 `character_id` → skip + warning

#### A-3. `update_storyboard_in_db()` IntegrityError catch
- `db.commit()` 시 IntegrityError → `db.rollback()` + 400 응답
- 에러 메시지: `"참조 에셋이 삭제되었습니다. 해당 씬을 재생성해주세요"`

#### A-4. 테스트
- `test_scene_builder.py`: 존재하지 않는 `tts_asset_id`/`background_id` → null 치환 확인
- `test_storyboard_crud.py`: IntegrityError catch 확인

**변경 파일**: `scene_builder.py` (1개 함수 수정), `crud.py` (IntegrityError catch 추가), 테스트 2개
**호출자**: `save_storyboard_to_db()`, `update_storyboard_in_db()` — 시그니처 변경 없음
**Enum ID 충돌**: ❌ 없음 (`crud.py` 접촉 영역이 다른 함수)
**공수**: 소

---

### Sprint B: Auto-Save 실패 알림 + 복구 강화

#### B-1. AutoRun 종료 시 강제 save
```typescript
// Before (autoSave.ts:85-89)
if (prevState.isAutoRunning && !state.isAutoRunning) {
  const { isDirty } = useStoryboardStore.getState();
  if (isDirty) scheduleSave();
}

// After — isDirty와 무관하게 씬이 있으면 save 시도
if (prevState.isAutoRunning && !state.isAutoRunning) {
  const { scenes } = useStoryboardStore.getState();
  if (scenes.length > 0) {
    useStoryboardStore.getState().setIsDirty(true);
    scheduleSave();
  }
}
```

#### B-2. 3회 실패 후 UI 알림 (현재: console.warn만)
- `useUIStore`에 `autoSaveFailed: boolean` 상태 추가
- `consecutiveFailures >= MAX_FAILURES` 시 `autoSaveFailed: true` 설정
- Studio 헤더에 경고 배너: "자동 저장에 실패했습니다. 수동으로 저장해주세요" + 저장 버튼
- 성공 시 또는 사용자 새 변경 시 배너 해제

#### B-3. Autopilot isDirty 보장 (현행 확인 결과 — 이미 안전)
- Autopilot persist 실패 → `throw` → `isDirty` 변경 없음 (true 유지) ✅
- finally에서 `isAutoRunning: false` → autoSave 구독 발동 ✅
- **추가 작업 불필요** (기존 설계가 올바름)

**변경 파일**: `autoSave.ts`, `useUIStore.ts` (상태 1개 추가), Studio 배너 컴포넌트 1개
**Enum ID 충돌**: ❌ 없음
**공수**: 소

---

### Sprint C: localStorage 오염 방어

#### C-1. `:new` 키 생명주기 관리 (LEAK-2 해결)
- `persistStoryboard()` POST 성공 후 `:new` 키 명시적 삭제

```typescript
// storyboardActions.ts — POST 성공 분기 (L212~219)
syncUrlAfterCreate(newId);
// 추가: :new 키 정리
localStorage.removeItem("shorts-producer:storyboard:v1::new");
localStorage.removeItem("shorts-producer:render:v1::new");
```

#### C-2. 스토리보드 전환 시 StoryboardStore reset (LEAK-3 해결)
- `useStudioInitialization`의 `?id=X` 경로에서 DB 로드 전에 현재 StoryboardStore reset
- DB 데이터 도착 후 `setScenes()` → rehydration 경합 제거

#### C-3. 고아 localStorage 키 GC (LEAK-1 해결)
- `resetAllStores()`에 GC 로직 추가: `shorts-producer:storyboard:v1:sb_*` 패턴 전체 스캔
- 현재 활성 `storyboardId` 외의 키 삭제 (ChatStore는 자체 LRU로 이미 관리됨)

#### C-4. `resetTransientStores()` localStorage 정리 (LEAK-4 해결)
- 현재 활성 키에 대한 `localStorage.removeItem()` 추가

#### C-5. DB 로드 경로 isDirty 억제 (LEAK-5 개선)
- `setScenes(scenes, { fromDb: true })` 옵션 추가 → isDirty 설정 억제
- 불필요한 autoSave 트리거 제거

**변경 파일**: `storyboardActions.ts`, `resetAllStores.ts`, `useStudioInitialization.ts`, `useStoryboardStore.ts`
**Enum ID 충돌**: ❌ 없음 (Enum ID는 `constants/index.ts`, `config.py`, `helpers.py` 등 enum 관련 파일만 접촉)
**공수**: 중

---

## 영향받는 파일 전체 목록

### Sprint A (Backend)

| 파일 | 변경 유형 | 비고 |
|------|----------|------|
| `services/storyboard/scene_builder.py` | 수정 | `_build_scene_kwargs` _exclude 추가 + 검증 로직 |
| `services/storyboard/crud.py` | 수정 | IntegrityError catch (L361~524 영역) |
| `tests/test_scene_builder.py` | 신규/수정 | FK null 치환 테스트 |
| `tests/test_storyboard_crud.py` | 수정 | IntegrityError 테스트 |

### Sprint B (Frontend)

| 파일 | 변경 유형 | 비고 |
|------|----------|------|
| `store/effects/autoSave.ts` | 수정 | AutoRun 종료 강제 save + 실패 상태 전파 |
| `store/useUIStore.ts` | 수정 | `autoSaveFailed` 상태 추가 |
| `components/studio/AutoSaveFailBanner.tsx` | 신규 | 실패 배너 UI |
| `store/effects/__tests__/autoSave.test.ts` | 수정 | 신규 동작 테스트 |

### Sprint C (Frontend)

| 파일 | 변경 유형 | 비고 |
|------|----------|------|
| `store/actions/storyboardActions.ts` | 수정 | `:new` 키 정리 (POST 성공 후) |
| `store/resetAllStores.ts` | 수정 | 고아 키 GC 추가 |
| `hooks/useStudioInitialization.ts` | 수정 | 전환 시 StoryboardStore reset |
| `store/useStoryboardStore.ts` | 수정 | `setScenes` fromDb 옵션 |

---

## Enum ID 정규화 충돌 분석

| Enum ID 접촉 파일 | Data Integrity 접촉 | 충돌 |
|-------------------|---------------------|------|
| `config.py` (DEFAULT_STRUCTURE) | ❌ | — |
| `services/presets.py` | ❌ | — |
| `services/storyboard/helpers.py` (normalize_structure) | ❌ | — |
| `services/storyboard/crud.py:75` (structure 비교) | `crud.py:361+` (IntegrityError) | ❌ 다른 함수 |
| `services/creative_qc.py` | ❌ | — |
| `services/agent/nodes/*` | ❌ | — |
| `schemas.py` (기본값) | ❌ | — |
| `frontend/constants/index.ts` | ❌ | — |

**결론: 전 Sprint 충돌 없음. 병렬 작업 안전.**

---

## 검증 시나리오

| # | 시나리오 | Sprint | 기대 결과 |
|---|---------|--------|----------|
| 1 | PUT with invalid `tts_asset_id` | A | null 치환 + 정상 저장 (500 아님) |
| 2 | PUT with invalid `background_id` | A | null 치환 + 정상 저장 |
| 3 | IntegrityError 발생 시 | A | 400 + 사용자 친화적 메시지 |
| 4 | AutoRun 종료 시 isDirty 이미 true | B | scheduleSave() 즉시 호출 |
| 5 | 3회 연속 save 실패 | B | UI 배너 "수동 저장 필요" 표시 |
| 6 | `?new=true` 진입 → 작업 → DB 저장 성공 | C | `:new` 키 삭제됨 |
| 7 | 스토리보드 전환 (A→B→A) | C | 고아 키 없음, B 데이터 오염 없음 |
| 8 | 스토리보드 10개 순차 열기 | C | GC로 고아 키 정리, 5MB 한도 안전 |

---

## 우선순위 근거

- **데이터 유실 위험**: 사용자가 생성한 콘텐츠가 DB에 저장되지 않으면 새로고침 시 영구 소실
- **500 에러**: FK 미검증(`tts_asset_id`, `background_id`)으로 수동 저장도 실패 → 복구 수단 없음
- **Silent autoSave 중단**: 3회 실패 후 UI 알림 없이 중단 → 사용자 인지 불가
- **localStorage 5MB 한도**: 고아 키 GC 부재로 장기 사용 시 QuotaExceededError 위험
- Enum ID 정규화/ComfyUI 전환보다 선행 필수 (데이터 안전성 > 기능 개선)
