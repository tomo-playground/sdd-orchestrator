---
id: SP-054
priority: P1
scope: fullstack
branch: feat/SP-054-autorun-sse-unify
created: 2026-03-22
status: approved
approved_at: 2026-03-22
depends_on:
label: feat
---

## 무엇을 (What)
오토런(AutoRun) 이미지 생성에서 배치 API(`/scene/generate-batch`)를 제거하고, 개별 SSE 생성(`/scene/generate` + SSE)으로 통일한다.

## 왜 (Why)
- 오토런 중 `/scene/generate-batch` 호출 시 500 에러 발생 (SD WebUI 과부하 또는 응답 직렬화 실패)
- 배치 실패 → 개별 fallback 이중 구조가 복잡도만 증가시킴
- 배치 API는 실시간 프로그레스, WD14 인라인 검증, 백엔드 자동 저장 등 SSE의 이점을 활용하지 못함
- 개별 SSE는 씬별 독립 에러 격리, 실시간 진행 표시, 이미 검증된 안정적 경로

## 완료 기준 (DoD)
> AI가 이 목록으로 실패 테스트를 작성(RED)하고, 구현(GREEN)한다.

- [ ] `autopilotActions.ts`의 `runAutoRunFromStep`에서 `generateBatchImages` 호출을 제거하고, 모든 씬을 개별 SSE(`generateSceneImageFor`)로 생성
- [ ] 개별 SSE 생성 시 서버 과부하 방지를 위해 동시 실행 수를 제한 (최대 2-3개 병렬 또는 순차)
- [ ] `batchActions.ts` 파일 삭제 (더 이상 사용처 없음)
- [ ] Backend `/scene/generate-batch` 엔드포인트 및 관련 스키마(`BatchSceneRequest`, `BatchSceneResult`, `BatchSceneResponse`) 삭제
- [ ] 오토런 실행 시 씬별 프로그레스가 UI에 표시됨 (기존 SSE 프로그레스 재활용)
- [ ] 개별 씬 실패 시 해당 씬만 failedSceneOrders에 추가, 나머지 씬은 정상 진행
- [ ] 기존 테스트 regression 없음
- [ ] 린트 통과

## 영향 분석
- 관련 함수/파일:
  - `frontend/app/store/actions/autopilotActions.ts` (runAutoRunFromStep: 238행)
  - `frontend/app/store/actions/batchActions.ts` (삭제 대상)
  - `frontend/app/store/actions/imageGeneration.ts` (generateSceneImageFor: 기존 활용)
  - `backend/routers/scene.py` (generate_batch_images: 81행)
  - `backend/schemas.py` (BatchSceneRequest/Result/Response)
  - `backend/config.py` (SD_BATCH_CONCURRENCY)
- 테스트 파일:
  - `frontend/app/store/actions/__tests__/batchActions.test.ts` (삭제)
  - `frontend/app/store/actions/__tests__/autopilotActions.test.ts` (mock 수정)

## 제약 (Boundaries)
- 변경 파일 10개 이하 목표
- 건드리면 안 되는 것: 개별 SSE 생성 로직 (`generateSceneImageFor`, `generateWithProgress`)
- 의존성 추가 금지

## 힌트
- 관련 파일: `.cp-images/pasted-image-2026-03-22T04-59-43-820Z.png` (에러 스크린샷)
- 오토런의 candidateGen 씬은 이미 개별 SSE 사용 중 — singleGen 씬만 배치→SSE 전환 필요
