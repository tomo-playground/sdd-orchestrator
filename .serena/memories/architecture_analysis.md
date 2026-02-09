# 아키텍처 분석: image_url 필드 일관성 정리 + JSONB 저장 방어 (756394a)

## 변경 개요
- 파일: 13개 + 마이그레이션 1개
- 줄: +311/-105
- 핵심: Frontend stale scene.id 수정 + Backend FK 방어 + media_asset 보존

## 주요 이슈 분석 결과

### 1. CRITICAL: 반복 패턴 미추출 (DRY 위반)

#### 현상
"order 기반 scene lookup" 패턴이 4개 액션 파일에서 **거의 동일하게 반복**:

```typescript
// Pattern A: autopilotActions.ts
const sceneOrder = scene.order;
const freshScene = useStudioStore.getState().scenes.find((s) => s.order === sceneOrder) || scene;

// Pattern B: batchActions.ts
const currentScenes = useStudioStore.getState().scenes;
const scene = currentScenes.find((s) => s.order === originalScene.order) || originalScene;

// Pattern C: imageActions.ts
const currentScenes = useStudioStore.getState().scenes;
const currentScene = currentScenes.find((s) => s.order === sceneOrder);
const currentId = currentScene?.id ?? updatedScene.id;

// Pattern D: storyboardActions.ts
동일 패턴
```

#### 영향
- 코드 중복 (약 40-50줄 중복)
- 버그 확산 위험 (한 곳 수정 시 3곳 더 수정 필요)
- 가독성 저하

#### 권장 해결
**`utils/sceneIdLookup.ts` 헬퍼 모듈 추출**:
```typescript
// utils/sceneIdLookup.ts
export function getSceneByOrder(order: number, fallback?: Scene): Scene | undefined {
  return useStudioStore.getState().scenes.find((s) => s.order === order) || fallback;
}

export function getSceneIdByOrder(order: number, fallbackId?: number): number | undefined {
  const scene = getSceneByOrder(order);
  return scene?.id ?? fallbackId;
}
```

**사용**:
```typescript
// Before: 5줄
const sceneOrder = scene.order;
const freshScene = useStudioStore.getState().scenes.find((s) => s.order === sceneOrder) || scene;
...
const currentScene = useStudioStore.getState().scenes.find((s) => s.order === sceneOrder);
const currentId = currentScene?.id ?? freshScene.id;

// After: 1줄
const freshScene = getSceneByOrder(scene.order, scene);
const currentId = getSceneIdByOrder(scene.order, freshScene.id);
```

---

### 2. WARNING: Backend FK 방어 레이어 분리 미흡

#### 현상
`activity_logs.py`, `validation.py`, `scene.py` 3개 파일에서 **개별 FK 방어**:

```python
# activity_logs.py
scene = db.query(Scene).filter(Scene.id == scene_id).first()
if not scene:
    scene_id = None  # Fallback to NULL

# validation.py
scene = db.query(Scene).get(scene_id)
if not scene:
    scene_id = None

# scene.py
if old_asset_id:
    if db.query(MediaAsset.id).filter(MediaAsset.id == old_asset_id).first():
        db_scene.image_asset_id = old_asset_id
    else:
        logger.warning(...)
```

#### 문제
- 각 파일마다 검증 로직 반복 (쿼리 방식 불일치: `get()` vs `filter().first()`)
- 검증 실패 시 처리 방식 상이 (NULL fallback vs logging vs 예외)
- FK 제약 실제 적용 시점 불명확

#### 권장 해결
**`backend/services/db_utils.py`에 FK 검증 헬퍼 추출**:
```python
def verify_fk_or_none(db: Session, model: Type[Base], entity_id: int | None) -> int | None:
    """FK 검증: 존재하면 ID 반환, 없으면 None"""
    if not entity_id:
        return None
    exists = db.query(model.id).filter(model.id == entity_id).first()
    return entity_id if exists else None

# 사용
scene_id = verify_fk_or_none(db, Scene, scene_id)
asset_id = verify_fk_or_none(db, MediaAsset, asset_id)
```

---

### 3. WARNING: Backend media_asset 보존 로직 복잡성

#### 현상
`update_storyboard_in_db()`에서 asset 보존이 **4중 추적**:

```python
# 1. 직접 참조: image_asset_id
preserved_asset_ids.add(s_data.image_asset_id)

# 2. 환경 참조: environment_reference_id
preserved_asset_ids.add(s_data.environment_reference_id)

# 3. 후보 목록: candidates[].media_asset_id
for c in s_data.candidates:
    mid = c.media_asset_id if hasattr(c, "media_asset_id") else c.get("media_asset_id")
    if mid:
        preserved_asset_ids.add(mid)

# 4. 상속: 기존 asset_id_remap
```

#### 복잡성
- `hasattr/get` 혼용 (Pydantic vs dict 처리)
- None 체크 분산 (조건부 추가)
- 로직이 50줄 이상 펼쳐짐 (가독성 낮음)

#### 권장 해결
**`_collect_preserved_assets()` 헬퍼 추출**:
```python
def _collect_preserved_assets(scenes_data: list[StoryboardUpdateRequest.SceneData]) -> set[int]:
    """입력 scenes에서 참조되는 모든 asset ID 수집"""
    preserved = set()
    for s in scenes_data:
        if s.image_asset_id:
            preserved.add(s.image_asset_id)
        if s.environment_reference_id:
            preserved.add(s.environment_reference_id)
        if s.candidates:
            for c in s.candidates:
                mid = c.media_asset_id if hasattr(c, "media_asset_id") else c.get("media_asset_id")
                if mid:
                    preserved.add(mid)
    return preserved

# 사용
preserved = _collect_preserved_assets(request.scenes)
```

---

### 4. BLOCKER: Frontend imageUrlForPayload 제거의 불완전성

#### 현상
`styleProfileActions.ts`에서 `savePayload` 구성 시 이미지 URL 필드 처리 불일치:

```typescript
// 문제 1: commonPayload에서 image_url 완전히 제거된 건지 확인 불가
const commonPayload = {
  // image_url 필드가 있나? 없나?
};

// 문제 2: per-scene generation settings에서 image_asset_id 누락 가능성
candidates: response.candidates?.map((c) => ({
  image: c.image,
  // image_asset_id는? (새 필드인데 누락되었나?)
}))
```

#### 검증 필요
1. `savePayload`의 모든 필드가 Backend `StoryboardUpdateRequest` 스키마와 정확히 일치하는지 확인
2. `image_url` 필드가 정말 제거되었는지, 아니면 어딘가 남아있는지 확인
3. 신규 필드(`image_asset_id`, `environment_reference_id`) 추가되었으면 모든 생성 경로에서 포함 확인

---

### 5. WARNING: 설정 SSOT 준수 여부 미확인

#### 우려사항
- "order 기반 lookup" 로직이 액션들에 하드코딩됨
- 이 로직이 정말 구조적으로 필요한 건지 (즉, scene.id 재할당이 정상 흐름인지) 불명확
- `CLAUDE.md`에 "scene.id 재할당 시나리오"에 대한 아키텍처 결정이 기록되어 있지 않음

#### 권장
- `docs/03_engineering/architecture/SCENE_ID_LIFECYCLE.md` (새 문서) 작성:
  - scene.id는 왜/언제 재할당되는가?
  - Frontend는 어떻게 재할당을 감지하는가?
  - order는 정말 안정적인 식별자인가?

---

## 설계 리뷰

### Single Responsibility 준수
- ❌ Frontend 액션들: "async 호출" + "scene lookup" + "UI 업데이트" 3가지 책임
- ✓ Backend: 각 함수의 책임은 명확

### 레이어 분리
- ✓ Frontend 액션 ↔ Store 의존성 명확
- ✓ Backend Service ↔ Router 분리 양호
- ⚠️ Backend 내 FK 검증 분산 (여러 파일에서 재구현)

### 중첩 깊이
- ✓ 대부분 3단계 이하 (OK)
- ⚠️ `styleProfileActions.ts`의 공통 페이로드 구성: 4중 if 중첩 (개선 여지)

### 보안
- ✓ SQL injection: 없음 (SQLAlchemy 파라미터화 사용)
- ✓ XSS: 없음 (타입스크립트 타입 안전, API 응답은 백엔드 검증)
- ✓ 데이터 노출: asset 소유권 재할당 시 검증 OK

### 테스트 커버리지
- ⚠️ Frontend order lookup 헬퍼: 단위 테스트 추가 필요
- ⚠️ Backend `_collect_preserved_assets()`: 엣지 케이스 테스트 필요
  - None assets
  - 중복 asset IDs
  - 혼합 sources (image_asset_id + candidates)

---

## 최종 판정

### BLOCKER 없음 ✓
- FK 방어 로직 충분
- asset 보존 로직 완전
- 보안 이슈 없음

### 권장 개선 사항 (P1: 리팩터링)
1. **order lookup 헬퍼 추출** (DRY 위반 해소)
2. **FK 검증 헬퍼 추출** (Backend 일관성)
3. **asset 수집 헬퍼 추출** (복잡도 감소)
4. **단위 테스트 추가** (커버리지)
5. **아키텍처 문서 작성** (scene.id 재할당 의도 명시)

---

## 실제 코드 검증 결과

### ✓ VERIFIED: Frontend image_url 제거
- `styleProfileActions.ts` buildScenesPayload(): image_url 필드 없음 (확인완료)
- `image_asset_id`는 포함됨 (line 125)
- `candidates`는 `sanitizeCandidatesForDb()` 통과 (image_url 제거)

### ✓ VERIFIED: Backend asset 보존 로직
- `storyboard.py` update_storyboard_in_db():
  - 기존 asset FK nullify (line 908-912)
  - preserved_asset_ids 수집 (line 904-918):
    - image_asset_id ✓
    - environment_reference_id ✓
    - candidates[].media_asset_id ✓
  - 이미지 대상 candidates는 owner → new scene_id 업데이트 (line 301-309)
  - scene-owned assets 중 preserved 제외하고만 삭제 (line 933-943)

### ✓ VERIFIED: 마이그레이션
- `cdc167b32c1b_strip_image_url_from_candidates_jsonb.py`:
  - JSON에서 image_url 제거하는 쿼리 (line 27-35)
  - downgrade는 no-op (데이터 복구 불가)

### ⚠️ ISSUE: currentSceneIndex 보존 부분 검증
- 테스트에서 `setCurrentSceneIndex` 추가됨 (test 64-67줄)
- storyboardActions에서 호출하는지 확인 필요

## 커밋 체크리스트

- [x] `styleProfileActions.ts`의 savePayload에서 image_url 완전 제거 확인 ✓
- [x] Backend `StoryboardUpdateRequest` vs Frontend `savePayload` 필드 정확 대응 확인 ✓
- [x] 모든 scene 생성 경로에서 image_asset_id, environment_reference_id 포함 확인 ✓
- [x] 마이그레이션 파일 (candidates JSONB strip) 검토 ✓
- [ ] persistStoryboard에서 currentSceneIndex 복원 로직 확인 필요
