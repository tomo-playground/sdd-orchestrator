---
id: SP-045
priority: P0
scope: fullstack
branch: fix/SP-045-autosave-image-overwrite
created: 2026-03-22
status: done
depends_on:
label: bug
reviewer: stopper2008
assignee: stopper2008
---

## 무엇을
autoSave가 프론트엔드 stale 데이터로 DB 씬을 덮어써서 이미지가 사라지는 버그 수정

## 왜
서버 재시작 → 프론트엔드 재연결 → autoSave가 Zustand 메모리의 씬(image_asset_id 없음)으로
DB 씬(image_asset_id 있음)을 교체 → 이미지 유실.

로그 근거:
```
22:31:13 - Storyboard Update id=1167  ← 이미지 있는 씬(29039~29050)
23:29:30 - Storyboard Update id=1167  ← 서버 재시작 후 autoSave → 새 씬(29057~29062, 이미지 없음)
```

SP-039 (Draft 부활 버그)와 같은 계열 — autoSave가 stale 데이터를 DB에 덮어쓰는 근본 문제.

## 실패 테스트 (TDD)

```python
# backend/tests/test_autosave_image_preservation.py

def test_autosave_preserves_image_asset_id():
    """autoSave(PUT /storyboards/{id}) 시 scene에 image_asset_id가 없으면
    기존 DB의 image_asset_id를 보존해야 한다."""
    # 1. DB에 image_asset_id가 있는 씬 생성
    # 2. image_asset_id 없는 payload로 PUT 호출
    # 3. DB에서 image_asset_id가 보존되었는지 확인
    pass

def test_autosave_does_not_replace_scenes_when_no_change():
    """씬 내용(script, order)이 동일하면 씬을 교체하지 않아야 한다."""
    # 1. DB에 씬 6개 존재 (이미지 포함)
    # 2. 동일 내용으로 PUT 호출
    # 3. scene ID가 변경되지 않았는지 확인
    pass

def test_autosave_preserves_tts_asset_id():
    """autoSave 시 tts_asset_id도 보존되어야 한다."""
    pass
```

```typescript
// frontend/tests/store/autosave-preservation.test.ts

test("buildScenesPayload에 image_asset_id가 포함되어야 한다", () => {
  const scene = { id: 1, script: "test", image_asset_id: 8160 };
  const payload = buildScenesPayload([scene]);
  expect(payload[0].image_asset_id).toBe(8160);
});

test("autoSave payload에서 image_asset_id가 누락되지 않아야 한다", () => {
  // Zustand store에 image_asset_id가 있는 씬을 설정
  // persistStoryboard() 호출 시 payload에 image_asset_id 포함 확인
});
```

## 완료 기준 (DoD)
- [ ] 실패 테스트 → GREEN
- [ ] autoSave(PUT) 시 image_asset_id, tts_asset_id가 보존됨
- [ ] 서버 재시작 후 autoSave가 이미지를 덮어쓰지 않음
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 원인 분석 방향

### 가능한 원인 1: Frontend → Backend payload에 image_asset_id 누락
- `buildScenesPayload()`가 `image_asset_id`를 exclude하는지 확인
- Spread passthrough 패턴이 적용되어 있으면 자동 포함되어야 함

### 가능한 원인 2: Backend scene 교체 로직이 기존 asset을 무시
- `scene_builder.py`의 `create_scenes()`가 기존 씬을 hard delete 후 새로 생성
- 새 씬에 image_asset_id를 복사하지 않음

### 가능한 원인 3: 씬 변경 감지 없이 무조건 교체
- 씬 내용이 동일해도 전체 교체 → 불필요한 데이터 유실

## 제약
- `buildScenesPayload.ts` + `scene_builder.py` + 관련 테스트 = 최대 6개 파일
- autoSave 로직 자체를 제거하면 안 됨 — 보존 로직 추가
- Spread passthrough 패턴 준수 (CLAUDE.md)

## 힌트
- `frontend/app/utils/buildScenesPayload.ts` — Frontend payload 구성
- `backend/services/storyboard/scene_builder.py` — Backend 씬 교체 로직
- `frontend/app/store/effects/autoSave.ts` — autoSave 트리거
- `frontend/app/store/actions/storyboardActions.ts` — persistStoryboard()
