# SP-054 상세 설계 (How)

## 설계 결정 요약

| 항목 | 결정 |
|------|------|
| 동시성 제어 | Frontend 2개 병렬 (Promise concurrency pool) |
| 멀티젠 범위 | 변경 없음 (기존 순차 유지), 싱글젠만 전환 |
| SD_BATCH_CONCURRENCY | 삭제 (Frontend `AUTORUN_CONCURRENCY = 2` 대체) |

---

## DoD 1: autopilotActions.ts — generateBatchImages 제거 + 개별 SSE 전환

### 구현 방법
- `autopilotActions.ts`의 `runAutoRunFromStep` 함수 내 "images" 스텝에서:
  - `generateBatchImages()` 호출 (라인 236-248) 제거
  - 배치 실패 후 개별 재시도 로직 (라인 250-272) 제거
  - 대신 `singleGenScenes`를 2개 병렬 concurrency pool로 `generateSceneImageFor()` 호출
- `batchActions` import 제거

### 동작 정의
- **Before**: singleGenScenes → `generateBatchImages()` → 배치 실패 시 개별 `generateSceneImageFor()` fallback
- **After**: singleGenScenes → 2개씩 병렬 `generateSceneImageFor()` (concurrency pool)

### Concurrency Pool 구현
```typescript
// autopilotActions.ts 내 인라인 구현 (헬퍼 추출 불필요 — 1회 사용)
const AUTORUN_CONCURRENCY = 2;
const queue = [...singleGenScenes];
const running = new Set<Promise<void>>();

while (queue.length > 0 || running.size > 0) {
  if (abortController.signal.aborted) break;

  while (running.size < AUTORUN_CONCURRENCY && queue.length > 0) {
    const scene = queue.shift()!;
    const p = (async () => {
      const result = await generateSceneImageFor(scene, true);
      if (!result?.image_url) {
        failedSceneOrders.push(scene.scene_order);
      }
    })();
    running.add(p);
    p.finally(() => running.delete(p));
  }

  await Promise.race(running);
}
```

### 엣지 케이스
- AbortSignal 발동 시: while 루프 탈출, 실행 중인 요청은 `generateSceneImageFor` 내부에서 처리
- 빈 singleGenScenes: while 조건 불충족으로 스킵 (정상)
- 모든 씬 실패: failedSceneOrders에 전부 추가, autorun은 다음 스텝으로 진행

### 영향 범위
- `autopilotActions.ts`만 수정
- 멀티젠 경로 변경 없음 (독립적)
- `generateSceneImageFor` 시그니처 변경 없음

### 테스트 전략
- RED: `runAutoRunFromStep` images 스텝에서 `generateSceneImageFor`가 씬 수만큼 호출되는지 검증
- RED: 2개 이상 씬이 있을 때 동시 실행이 2개로 제한되는지 검증 (호출 타이밍)
- RED: 1개 씬 실패 시 failedSceneOrders에 추가되고 나머지는 성공하는지 검증

### Out of Scope
- 멀티젠 경로 변경
- `generateSceneImageFor` 내부 수정
- SSE 프로그레스 UI 변경

---

## DoD 2: 동시 실행 제한 (최대 2개 병렬)

DoD 1에 통합. `AUTORUN_CONCURRENCY = 2` 상수 + concurrency pool 패턴으로 해결.

---

## DoD 3: batchActions.ts 삭제

### 구현 방법
- `frontend/app/store/actions/batchActions.ts` 파일 삭제
- `frontend/app/store/actions/__tests__/batchActions.test.ts` 파일 삭제

### 동작 정의
- **Before**: `autopilotActions.ts`에서 `generateBatchImages` import + 호출
- **After**: import/호출 모두 제거, 파일 삭제

### 엣지 케이스
- 다른 파일에서 import하는 곳이 없는지 확인 필요 (탐색 결과: autopilotActions.ts만 사용)

### 영향 범위
- `autopilotActions.ts`의 import문 1개 제거
- 다른 import 없음 확인됨

### 테스트 전략
- 빌드(tsc + next build) 통과 검증
- 기존 autopilotActions 테스트가 batchActions mock 없이 동작하는지 확인

### Out of Scope
- `buildSceneRequest`는 `imageGeneration.ts`에 정의 — 삭제 대상 아님

---

## DoD 4: Backend 배치 엔드포인트 + 스키마 삭제

### 구현 방법
- `backend/routers/scene.py`: `generate_batch_images` 함수 (라인 81-109) 삭제
- `backend/schemas.py`: `BatchSceneRequest`, `BatchSceneResult`, `BatchSceneResponse` 3개 클래스 삭제
- `backend/config.py`: `SD_BATCH_CONCURRENCY` 상수 삭제
- `backend/routers/scene.py`의 import에서 `BatchSceneRequest`, `BatchSceneResponse` 제거

### 동작 정의
- **Before**: `POST /api/v1/scene/generate-batch` 사용 가능
- **After**: 엔드포인트 존재하지 않음 (404)

### 엣지 케이스
- 다른 Backend 코드에서 배치 스키마를 참조하는 곳이 없는지 확인 (탐색 결과: scene.py만 사용)
- Frontend가 배치 API를 직접 호출하는 곳이 없는지 확인 (batchActions.ts만 — 함께 삭제)

### 영향 범위
- REST API 명세 업데이트 필요 (`docs/03_engineering/api/REST_API.md`)
- OpenAPI 스키마에서 자동 제거됨

### 테스트 전략
- 기존 Backend 테스트에 배치 엔드포인트 테스트가 있으면 삭제
- `pytest` 전체 회귀 없음 확인

### Out of Scope
- 개별 `POST /scene/generate` 엔드포인트 수정
- SSE 엔드포인트 수정

---

## DoD 5: 씬별 프로그레스 UI 표시

### 구현 방법
- 변경 불필요. `generateSceneImageFor` 내부에서 이미 `imageGenProgress` store에 씬별 프로그레스 저장
- 2개 병렬 실행 시 각 씬의 `client_id`가 다르므로 독립적으로 표시됨

### 동작 정의
- **Before**: 배치 API는 프로그레스 없이 완료 후 일괄 반영
- **After**: 각 씬 SSE 스트림에서 실시간 프로그레스 (기존 동작 그대로)

### 테스트 전략
- 수동 검증: 오토런 실행 시 2개 씬의 프로그레스 바가 동시에 표시되는지 확인

### Out of Scope
- 프로그레스 UI 컴포넌트 수정

---

## DoD 6: 개별 씬 실패 격리

### 구현 방법
- DoD 1의 concurrency pool에서 `generateSceneImageFor` 결과 확인
- `result`가 null이거나 `image_url` 없으면 `failedSceneOrders.push(scene.scene_order)`
- 나머지 씬은 계속 진행 (pool이 자동으로 다음 씬 실행)

### 동작 정의
- **Before**: 배치 전체 실패 → 개별 재시도 fallback (이중 구조)
- **After**: 개별 실패 → failedSceneOrders 추가, 나머지 계속 (단일 구조)

### 엣지 케이스
- 전체 씬 실패: failedSceneOrders에 모든 씬 추가, 다음 스텝(tts 등)은 성공한 씬만 대상
- SD WebUI 다운: 모든 SSE 실패 → 전체 failedSceneOrders → 사용자에게 표시

### 테스트 전략
- RED: 5개 씬 중 2개 실패 시 failedSceneOrders에 2개만 추가되는지 검증

### Out of Scope
- failedSceneOrders의 UI 표시 방식 변경

---

## DoD 7-8: 기존 테스트 regression + 린트

### 구현 방법
- `pytest` 전체 실행
- `ruff check` + `npx prettier --check`
- batchActions 관련 mock을 사용하는 테스트 수정 (autopilotActions.test.ts)

### 테스트 전략
- CI 파이프라인 전체 통과

---

## 변경 파일 목록 (예상 8개)

| 파일 | 동작 |
|------|------|
| `frontend/app/store/actions/autopilotActions.ts` | 수정 (배치→개별 SSE) |
| `frontend/app/store/actions/batchActions.ts` | 삭제 |
| `frontend/app/store/actions/__tests__/batchActions.test.ts` | 삭제 |
| `frontend/app/store/actions/__tests__/autopilotActions.test.ts` | 수정 (mock 변경) |
| `backend/routers/scene.py` | 수정 (배치 엔드포인트 삭제) |
| `backend/schemas.py` | 수정 (배치 스키마 삭제) |
| `backend/config.py` | 수정 (SD_BATCH_CONCURRENCY 삭제) |
| `docs/03_engineering/api/REST_API.md` | 수정 (배치 API 제거) |
