# Phase 32: Auto Run Pipeline Hardening

**상태**: 완료
**우선순위**: P0 (핵심 사용자 워크플로우 안정성)
**예상 범위**: Sprint A~E + B-2 (15개 파일 수정, 신규 6개 파일, 테스트 30개)

---

## 배경 및 목적

Auto Run(Autopilot) 기능은 "주제 입력 → Stage → Images → Render" 전 과정을 멈춤 없이 처리하는 핵심 DoD 항목이다. 심층 코드 분석 결과 다음 카테고리의 결함이 확인됐다:

- **P0 — 루프 버그**: 환경 태그 없는 씬이 있으면 stage 단계가 매번 재실행됨
- **P0 — TTS 누락**: Auto Run에 TTS 사전 생성 단계가 없어 render 내부에서 생성 → 실패 시 복구 불가
- **P0 — GC 손실**: TTS preview asset이 24시간 후 자동 삭제 → 다음날 render 시 무음 처리
- **P1 — Resume 미연결**: `ResumeConfirmModal` 컴포넌트가 완성돼 있으나 `studio/page.tsx`에 연결 안됨
- **P1 — 진행률 미표시**: `autoRunProgress` 계산됐으나 `AutoRunStatus`에 전달 안됨
- **P2 — SSOT 위반**: `tts_engine: "qwen"` 하드코딩 2곳, `_BG_QUALITY_OVERRIDES` ID 하드코딩

- **P0 — voice_design 손실**: Auto Run render 페이로드에 `scene_db_id` 누락 → Gemini 생성 voice_design이 DB에 write-back 안됨
- **P0 — render 페이로드 중복**: `autopilotActions.ts`와 `usePublishRender.ts`가 동일한 render 페이로드를 Whitelist 방식으로 각각 구성 → 필드 누락의 근본 원인
- **P1 — stepsToRun 일관성**: `onResume`/`onRestart`/`pendingAutoRun` 3곳 모두 `stepsToRun` 없이 실행 → 완료 단계 재실행
- **P1 — Checkpoint 미영속화**: `getCheckpoint()`이 메모리 전용 → localStorage 저장 없음 → `ResumeConfirmModal`이 dead code인 근본 원인
- **P1 — data URL 가드 없음**: Auto Run render에 `data:` URL 체크 없음 → `storeSceneImage` 실패 시 base64로 render 시도

**핵심 원칙**: "의도하지 않은 결과물의 변화는 허용하지 않는다." Auto Run은 재실행 시 이미 처리된 단계를 건너뛰어야 하며, TTS는 렌더 시점에 항상 유효해야 한다.

---

## Sprint A: Stage 루프 버그 수정 (P0)

**목표**: 환경 태그 없는 씬으로 인한 stage 무한 재실행 차단

### A-1: `checkStageStep` 환경 태그 없는 씬 예외 처리

**왜**: `checkStageStep`은 `background_id == null`인 씬 개수를 기준으로 `needed: true`를 반환한다. 그러나 `background_generator.py:extract_locations_from_scenes`는 `context_tags.environment`가 비어있는 씬을 location 추출에서 제외하므로 해당 씬에는 절대 `background_id`가 할당되지 않는다. 결과적으로 stage를 완료해도 `checkStageStep`은 계속 `needed: true`를 반환해 매번 재실행된다.

**수정 대상**: `frontend/app/utils/preflight-steps.ts`

```
checkStageStep() 내부:
  현재: withoutBg = scenes.filter((s) => !s.background_id)
  변경: withoutBg = scenes.filter((s) => !s.background_id && hasEnvironmentTags(s))

헬퍼 추가:
  function hasEnvironmentTags(scene): boolean {
    const env = scene.context_tags?.environment
    return Array.isArray(env) && env.length > 0
  }
```

**완료 기준**:
- [ ] 환경 태그 없는 씬만 있는 스토리보드에서 stage `needed: false` 반환
- [ ] 환경 태그 있는 씬 일부에 `background_id` 없으면 여전히 `needed: true` 반환
- [ ] 단위 테스트 3개 추가

### A-2: stage 부분 실패 경고 로그

**왜**: `assign-backgrounds` API는 일부 씬에 background 할당에 실패해도 HTTP 200 + 빈 `assignments` 배열을 반환한다. `autopilotActions.ts:131`은 결과 확인 없이 `stageStatus: "staged"`로 설정한다. 사용자는 stage가 성공했다고 인지하지만 일부 씬은 배경 없이 이미지 생성으로 진행된다.

**수정 대상**: `frontend/app/store/actions/autopilotActions.ts`

```
assign 결과 처리 후:
  const totalScenesWithEnv = workingScenes.filter(hasEnvironmentTags).length
  const assignedCount = assignments.length
  if (assignedCount < totalScenesWithEnv) {
    pushAutoRunLog(
      `Stage warning: ${totalScenesWithEnv - assignedCount} scene(s) without background assigned`
    )
  }
```

**완료 기준**:
- [ ] 부분 할당 시 경고 로그 pushAutoRunLog에 기록
- [ ] 경고여도 stage 단계는 계속 진행 (throw 하지 않음)

---

## Sprint B: TTS 단계 추가 및 Asset 보호 (P0)

**목표**: Auto Run 파이프라인에 TTS 사전 생성 단계 추가 + GC로 인한 무음 렌더 방지

### B-1: `AUTO_RUN_STEPS`에 tts 단계 추가

**왜**: 현재 파이프라인은 `stage → images → render`이며 TTS는 render 내부에서 온디맨드 생성된다. render 중 TTS 서버 오류 시 해당 씬은 무음 처리되고 전체 render가 실패한다. TTS를 별도 단계로 분리하면 실패한 씬만 재시도할 수 있다.

**수정 대상**: `frontend/app/constants/index.ts`, `frontend/app/store/actions/autopilotActions.ts`, `frontend/app/utils/preflight.ts`, `frontend/app/utils/preflight-steps.ts`

```
constants/index.ts:
  AUTO_RUN_STEPS = [
    { id: "stage", label: "Stage" },
    { id: "images", label: "Images" },
    { id: "tts", label: "TTS" },      // 신규
    { id: "render", label: "Render" },
  ]

autopilotActions.ts: tts 단계 구현
  - API: POST /api/v1/storyboards/{id}/tts/prebuild
  - 씬별 tts_asset_id를 store에 업데이트
  - 실패한 씬은 경고 로그 후 계속 진행 (render에서 fallback 생성)

preflight-steps.ts: checkTtsStep() 함수 추가
  - tts_asset_id 없는 씬 개수 기준으로 needed 결정

preflight.ts: steps.tts 추가
  - PreflightResult.steps 타입에 tts 추가
```

**Backend 신규 엔드포인트**: `backend/routers/tts.py` (또는 storyboard 라우터에 추가)

```
POST /api/v1/storyboards/{storyboard_id}/tts/prebuild
- 모든 씬의 TTS 일괄 생성 (tts_asset_id 없는 씬만)
- 씬별 결과 반환: [{scene_id, tts_asset_id, duration, status}]
- 실패한 씬도 결과에 포함 (전체 실패 아님)
```

**완료 기준**:
- [ ] `AUTO_RUN_STEPS`에 "tts" 항목 추가
- [ ] `AutoRunStatus` 컴포넌트에 4단계 표시
- [ ] TTS prebuild API 구현 (backend)
- [ ] 씬별 tts_asset_id store 업데이트
- [ ] 단위 테스트 4개 추가

### B-2: render 완료 후 TTS asset promote (is_temp=False)

**왜**: `preview_tts.py`는 TTS asset을 `is_temp=True`로 저장한다. `media_gc.py`의 GC는 24시간 후 삭제한다. render 완료 후 실제 사용된 TTS asset은 `is_temp=False`로 변환해야 영구 보존된다. `voice_presets.py:163`과 `music_presets.py:163`에 동일 패턴이 이미 구현돼 있다.

**수정 대상**: `backend/services/video/scene_processing.py` 또는 render 완료 훅

```
render 완료 시점에:
  사용된 scene.tts_asset_id 목록 수집
  → MediaAsset.is_temp = False 업데이트 (bulk UPDATE)
  → logger.info("[TTS Promote] %d assets promoted", count)
```

**완료 기준**:
- [ ] render 완료 후 사용된 tts_asset의 is_temp=False 확인
- [ ] GC 실행 후에도 promote된 asset이 존재
- [ ] 단위 테스트 2개 추가

### B-3: `SCENE_TRANSIENT_FIELDS`와 `buildScenesPayload` 의미론적 정합성

**왜**: `tts_asset_id`가 `SCENE_TRANSIENT_FIELDS`에 등록돼 있으면서 `buildScenesPayload`의 `...rest` 스프레드에도 포함돼 실제로 API 페이로드에 전달된다. "transient"라는 네이밍이 모순이다. `tts_asset_id`는 실제로 저장해야 하는 값이므로 transient 목록에서 제거하거나 명시적으로 포함 의도를 주석으로 문서화한다.

**수정 대상**: `frontend/app/utils/buildScenesPayload.ts` (또는 관련 상수 파일)

**완료 기준**:
- [ ] `tts_asset_id` 처리 의도가 코드에 명시적으로 표현됨
- [ ] `buildScenesPayload` 페이로드에 tts_asset_id 포함 유지

---

## Sprint B-2: Render 페이로드 통합 (P0)

**목표**: `autopilotActions.ts`와 `usePublishRender.ts`의 중복 render 페이로드 구성을 단일 함수로 통합

### B2-1: `scene_db_id` Auto Run render 페이로드 누락 수정

**왜**: `usePublishRender.ts:134`에는 `scene_db_id: s.id || undefined`가 있지만 `autopilotActions.ts:297-311`에는 없다. Backend의 `_persist_voice_design()` 함수는 `scene_db_id`가 없으면 no-op하므로, Auto Run render 시 Gemini가 생성한 `voice_design_prompt`가 DB에 write-back되지 않는다. 다음 render 시 voice_design을 처음부터 다시 생성해야 하므로 음성 일관성이 깨진다.

**즉시 수정**: `autopilotActions.ts` 씬 페이로드에 `scene_db_id` 추가
```
scenes: renderScenes.map((s, i) => ({
  ...existing fields,
  scene_db_id: s.id || undefined,  // ← 추가
}))
```

### B2-2: render 씬 페이로드 구성 함수 추출

**왜**: `autopilotActions.ts`와 `usePublishRender.ts`가 거의 동일한 씬 페이로드를 Whitelist 방식으로 각각 구성한다. CLAUDE.md "Code Modularization Principles (중복 로직 금지)" 위반이며, `scene_db_id` 누락 같은 버그의 근본 원인이다.

**수정 대상**: 신규 `frontend/app/utils/buildRenderPayload.ts`

```ts
// 공통 render 씬 페이로드 빌더
export function buildRenderScenePayload(scene: Scene, order: number) {
  return {
    image_url: scene.image_url,
    script: scene.script,
    speaker: scene.speaker,
    duration: scene.duration,
    order,
    scene_db_id: scene.id || undefined,
    image_prompt: scene.image_prompt ?? undefined,
    voice_design_prompt: scene.voice_design_prompt ?? undefined,
    head_padding: scene.head_padding ?? undefined,
    tail_padding: scene.tail_padding ?? undefined,
    background_id: scene.background_id ?? undefined,
    ken_burns_preset: scene.ken_burns_preset ?? undefined,
    scene_emotion: scene.context_tags?.emotion ?? scene.context_tags?.mood?.[0] ?? undefined,
    image_prompt_ko: scene.image_prompt_ko ?? undefined,
    tts_asset_id: scene.tts_asset_id ?? undefined,
  };
}

// 공통 render 전체 페이로드 빌더
export function buildRenderPayload(options: RenderPayloadOptions) { ... }
```

**완료 기준**:
- [ ] `buildRenderScenePayload` 함수 추출
- [ ] `autopilotActions.ts`와 `usePublishRender.ts` 모두 공통 함수 사용
- [ ] 필드 누락 불가능 구조 (단일 변경점)
- [ ] 단위 테스트 2개 추가

### B2-3: Auto Run render data URL 가드

**왜**: `usePublishRender.ts:94`에 `data:` URL 체크가 있지만 `autopilotActions.ts`에는 없다. `storeSceneImage` 실패 시 data URL(base64)이 scene에 남아있을 수 있고, 이 상태로 render 요청 시 거대한 base64 문자열이 HTTP payload에 포함된다.

**수정**: `buildRenderPayload` 또는 render 단계 시작 시 data URL 씬 감지 + 경고

**완료 기준**:
- [ ] data URL 씬이 있으면 해당 씬 제외 + 경고 로그
- [ ] 또는 render 전 `persistStoryboard()` 재실행으로 data URL → stored URL 전환

---

## Sprint C: Preflight 정확성 개선 (P0)

**목표**: Preflight 모달의 모순된 경고 제거 + pendingAutoRun 경로 일관성 확보

### C-1: `checkBgm()`에 bgmMode 파라미터 추가

**왜**: `checkBgm(bgmFile)`은 `bgmFile == null`이면 무조건 "BGM 없음 (무음)" 경고를 낸다. 그러나 `bgmMode === "auto"`인 경우 bgmFile이 null이어도 AI가 자동 생성하므로 경고가 불필요하다. 같은 PreflightModal에서 stage 카테고리는 bgmMode를 구분하는데 BGM 설정 체크는 구분하지 않아 모순이 발생한다.

**수정 대상**: `frontend/app/utils/preflight.ts`

```
function checkBgm(bgmMode: "manual" | "auto", bgmFile: string | null, musicPresetId: number | null): SettingsCheck

bgmMode === "auto":
  return { valid: true, value: "Auto (AI 생성)", required: false }  // 경고 없음

bgmMode === "manual":
  if (!bgmFile && !musicPresetId) → 경고 유지
  if (musicPresetId) → { valid: true, value: "프리셋 선택됨" }
  if (bgmFile) → { valid: true, value: filename }
```

**완료 기준**:
- [ ] bgmMode="auto"일 때 BGM 경고 없음
- [ ] bgmMode="manual"이고 bgmFile=null, musicPresetId=null일 때 경고 유지
- [ ] `buildPreflightInput()`에서 bgmMode 파라미터 전달
- [ ] 단위 테스트 3개 추가

### C-2: `stepsToRun` 누락 — 3곳 일괄 수정

**왜**: `runAutoRunFromStep(step, autopilot)` 호출 시 `stepsToRun` 없이 실행하는 경로가 **3곳** 있다. `stepsToRun`이 없으면 `allowedSteps = AUTO_RUN_STEPS 전체`가 되어 이미 완료된 단계도 재실행될 수 있다.

**영향받는 3곳**:
1. `studio/page.tsx:115-128` — `pendingAutoRun` 핸들러
2. `studio/page.tsx:259` — `onResume={(step) => runAutoRunFromStep(step, autopilot)}`
3. `studio/page.tsx:260-264` — `onRestart` 핸들러

PreflightModal 경로만 `stepsToRun`을 전달해 올바르게 동작.

**수정 대상**: `frontend/app/(service)/studio/page.tsx`

```
모든 runAutoRunFromStep 호출을 래퍼 함수로 통일:

function executeAutoRun(startStep: AutoRunStepId) {
  const preflight = runPreflight(buildPreflightInput())
  const stepsToRun = getStepsToExecute(preflight)
  const filtered = stepsToRun.filter(
    s => AUTO_RUN_STEPS.findIndex(x => x.id === s) >= AUTO_RUN_STEPS.findIndex(x => x.id === startStep)
  )
  runAutoRunFromStep(filtered[0] ?? startStep, autopilot, filtered)
}

onResume → executeAutoRun(step)
onRestart → executeAutoRun(needsStage ? "stage" : "images")
pendingAutoRun → executeAutoRun(startStep)
```

**완료 기준**:
- [ ] 3곳 모두 `stepsToRun` 포함 호출로 통일
- [ ] 이미 완료된 단계는 skip 로그와 함께 건너뜀
- [ ] 단위 테스트 2개 추가

---

## Sprint D: P1 버그 수정 (Resume + 이미지 생성)

**목표**: Resume 기능 연결 + seed 무시 + silent failure 수정 + 진행률 표시

### D-1: Checkpoint localStorage 영속화 + `ResumeConfirmModal` 연결

**왜**: `ResumeConfirmModal` 컴포넌트, `getCheckpoint()`, `initializeFromCheckpoint()` 함수가 모두 구현돼 있으나 **2가지 근본 원인**으로 작동하지 않는다:

1. **Checkpoint가 메모리 전용**: `getCheckpoint()`은 현재 React state에서 checkpoint를 반환하지만 localStorage에 저장하는 코드가 없다. 페이지 새로고침 시 state 초기화 → checkpoint 소실.
2. **`studio/page.tsx`에 모달 연결 없음**: 컴포넌트 import도, 렌더링도 없다.

**수정 순서**:

Step 1: Checkpoint persistence (`useAutopilot.ts`)
```ts
// setStep, setError 시 localStorage에 checkpoint 자동 저장
const CHECKPOINT_KEY = `autopilot_checkpoint_${storyboardId}`;

function persistCheckpoint(step: AutoRunStepId) {
  localStorage.setItem(CHECKPOINT_KEY, JSON.stringify({
    step, timestamp: Date.now(), storyboardId, interrupted: true,
  }));
}

// setDone / reset 시 localStorage에서 삭제
function clearCheckpoint() {
  localStorage.removeItem(CHECKPOINT_KEY);
}
```

Step 2: Page mount 시 복구 (`studio/page.tsx`)
```ts
useEffect(() => {
  const saved = localStorage.getItem(CHECKPOINT_KEY);
  if (saved) {
    const cp = JSON.parse(saved);
    if (cp.storyboardId === storyboardId && Date.now() - cp.timestamp < 24 * 3600 * 1000) {
      setResumeCheckpoint(cp);  // → ResumeConfirmModal 표시
    }
  }
}, [storyboardId]);
```

**완료 기준**:
- [ ] Auto Run 진행 중 checkpoint가 localStorage에 저장됨
- [ ] 페이지 새로고침 시 ResumeConfirmModal 표시
- [ ] Resume 선택 시 중단된 단계부터 재개
- [ ] 24시간 이상 된 checkpoint는 무시
- [ ] Auto Run 완료/리셋 시 checkpoint 삭제
- [ ] E2E 테스트 1개 추가

### D-2: Resume 시 완료된 단계 클릭 불가 처리

**왜**: `AutoRunStatus.tsx`의 에러 상태에서는 `isError`이면 모든 단계 버튼이 활성화된다 (isDone 단계 포함). 완료된 단계를 클릭하면 해당 단계부터 재실행돼 이미 생성된 이미지가 덮어씌워질 수 있다.

**수정 대상**: `frontend/app/components/storyboard/AutoRunStatus.tsx`

```
isError 상태의 버튼 렌더링:
  현재: isError이면 모든 step이 button
  변경: isError && !isDone 인 step만 button
         isDone step은 span (클릭 불가) + 완료 스타일 유지
```

**완료 기준**:
- [ ] 에러 상태에서 완료된 단계는 버튼이 아닌 span으로 렌더링
- [ ] 완료 단계는 hover 스타일 없음
- [ ] 단위 테스트 2개 추가

### D-3: `batchActions.ts` seed 강제 -1 제거

**왜**: `generateBatchImages`에서 `buildSceneRequest` 결과에 `seed: -1`을 강제 오버라이드한다. 씬에 고정 seed가 설정돼 있어도 batch 경로(Auto Run)에서만 무시된다. 개별 생성 경로는 씬 설정을 따른다. Zero Variance 원칙 위반.

**수정 대상**: `frontend/app/store/actions/batchActions.ts`

```
현재:
  const sceneRequests = targetScenes.map((scene) => ({
    ...buildSceneRequest(scene, sbState, storyboardId || null),
    seed: -1,  // 제거
  }))

변경:
  const sceneRequests = targetScenes.map((scene) =>
    buildSceneRequest(scene, sbState, storyboardId || null)
  )
```

**완료 기준**:
- [ ] batch 경로에서 씬의 seed 설정 존중
- [ ] seed가 없는 씬은 -1 (랜덤) 동작 유지 (`buildSceneRequest` 내부 처리)
- [ ] 단위 테스트 1개 추가

### D-4: `generateBatchImages`의 `canStore=false` silent failure 방지

**왜**: `canStore = projectId && groupId && ctxStoryboardId`가 null이면 SD 이미지 생성에 성공해도 결과를 조용히 버린다 (`updateScene({isGenerating: false})` 만 실행). `storyboardId` race condition이 원인이며 사용자는 이미지가 생성됐으나 저장이 안 됐다는 것을 알 수 없다.

**수정 대상**: `frontend/app/store/actions/batchActions.ts`

```
canStore 체크 실패 시:
  현재: else { updateScene({ isGenerating: false }) }  // 조용히 버림
  변경:
    if (!canStore) {
      console.error("[Batch] canStore=false: projectId/groupId/storyboardId 중 null 있음")
      // 개별 재시도로 fallback (autopilotActions의 retry 로직이 처리)
    }
```

**완료 기준**:
- [ ] canStore=false 시 error 로그 출력
- [ ] autopilotActions의 retry 로직이 이를 감지해 개별 재시도
- [ ] 단위 테스트 1개 추가

### D-5: `autoRunProgress` progress bar 연결

**왜**: `useAutopilot.ts`에서 `autoRunProgress` (0~100)가 계산되고 `AutoRunStatus` props에는 정의돼 있지 않아 progress bar가 없다. 이미지 생성 수분간 "33%" (Images 단계)가 고정 표시되는 UX 문제가 있다.

**수정 대상**: `frontend/app/components/storyboard/AutoRunStatus.tsx`, 사용처

```
AutoRunStatus props에 추가:
  progress?: number  // 0~100

컴포넌트 내부:
  progress !== undefined 이면 progress bar 렌더링
  <div className="h-1 rounded-full bg-zinc-200">
    <div className="h-1 rounded-full bg-zinc-900 transition-all" style={{ width: `${progress}%` }} />
  </div>
```

**완료 기준**:
- [ ] AutoRunStatus에 progress bar 표시
- [ ] 단계 전환 시 진행률 업데이트 (0 → 33 → 67 → 100)
- [ ] done 상태에서 100% 표시

---

## Sprint E: P2 코드 품질 개선 (SSOT 정비)

**목표**: 하드코딩 제거, 중복 로직 통합, 미사용 필드 정리

### E-1: `tts_engine` SSOT 통합

**왜**: `autopilotActions.ts:326`과 `usePublishRender.ts:152`에 `tts_engine: "qwen"`이 각각 하드코딩돼 있다. CLAUDE.md의 "Configuration Principles (SSOT)" 원칙 위반.

**수정 대상**: `frontend/app/constants/index.ts`, `frontend/app/store/actions/autopilotActions.ts`, `frontend/app/hooks/usePublishRender.ts`

```
constants/index.ts에 추가:
  export const TTS_ENGINE = "qwen" as const

각 사용처:
  tts_engine: TTS_ENGINE
```

**완료 기준**:
- [ ] TTS_ENGINE 상수 1곳에서 관리
- [ ] 2개 사용처 모두 상수 참조로 변경

### E-2: `_BG_QUALITY_OVERRIDES` StyleProfile ID DB 이동

**왜**: `background_generator.py:33`의 `_BG_QUALITY_OVERRIDES: dict[int, str]`는 StyleProfile ID를 코드에 하드코딩한다. StyleProfile이 추가/삭제되면 코드 수정이 필요하며 CLAUDE.md "태그 규칙: 코드 하드코딩 금지" 원칙 위반이다.

**수정 방향**: `StyleProfile` 테이블에 `bg_quality_override: str | None` 컬럼 추가 또는 `config.py`의 StyleProfile 이름 기반 조회로 대체. DBA 리뷰 필요.

**완료 기준**:
- [ ] StyleProfile ID 코드 하드코딩 제거
- [ ] DB 또는 config.py 기반으로 quality override 관리
- [ ] 기존 동작 동일

### E-3: location key 계산 로직 통합

**왜**: `extract_locations_from_scenes`와 `assign_backgrounds_to_scenes`에서 location key 계산 로직 (`_filter_location_tags` → `_resolve_location_aliases` → `"_".join(sorted(set()))`) 이 중복된다. `assign_backgrounds_to_scenes`에 주석도 있다: "Use same location-only key logic as extract_locations_from_scenes". 함수 추출 필요.

**수정 대상**: `backend/services/stage/background_generator.py`

```
헬퍼 함수 추출:
  def _compute_location_key(env_tags: list[str], db: Session) -> str | None:
    loc_tags = _filter_location_tags(env_tags, db)
    if not loc_tags:
      loc_tags = env_tags[:1]
    if not loc_tags:
      return None
    loc_tags = _resolve_location_aliases(loc_tags)
    return "_".join(sorted(set(loc_tags)))

두 함수 모두 _compute_location_key 호출로 교체
```

**완료 기준**:
- [ ] location key 계산 로직 1곳으로 통합
- [ ] 기존 테스트 모두 통과

### E-4: `renderWithProgress` polling 폴백 signal 전달

**왜**: `renderWithProgress`의 polling 폴백 경로에서 `abortController.signal`이 전달되지 않는다. Auto Run 취소 시 SSE는 중단되지만 polling은 계속된다.

**수정 대상**: `frontend/app/utils/renderWithProgress.ts`

**완료 기준**:
- [ ] polling 폴백에도 AbortSignal 전달
- [ ] Auto Run 취소 시 polling도 즉시 중단

### E-5: PreflightModal 단계 의존성 체크

**왜**: 사용자가 `stage=false`로 토글하고 `images=true`로 실행할 수 있다. stage가 필요한 씬에 배경 없이 이미지 생성이 진행된다. stage가 needed인데 disable하면 images/tts 단계도 강제 disable 또는 경고 표시해야 한다.

**수정 대상**: `frontend/app/components/common/PreflightModal.tsx`

**완료 기준**:
- [ ] stage needed인데 disable 시 images/tts에 warning 표시
- [ ] 또는 stage disable 시 의존 단계도 자동 disable

### E-6: `lastRenderHash` 미사용 필드 제거

**왜**: `PreflightInput`의 `lastRenderHash` 필드가 정의돼 있으나 `runPreflight()`에서 참조하지 않는다. 사용 계획이 없으면 제거해 타입 혼란을 방지한다.

**수정 대상**: `frontend/app/utils/preflight.ts`

**완료 기준**:
- [ ] `lastRenderHash` 필드 제거 (또는 TODO 주석으로 용도 명시)

### E-7: Stage location 생성 병렬화

**왜**: `background_generator.py`의 location별 이미지 생성이 순차 처리된다. 각 location은 독립적이므로 `asyncio.gather`로 병렬화 가능. 5개 location 기준 5x → 1x 시간으로 단축.

**수정 대상**: `backend/services/stage/background_generator.py`

**완료 기준**:
- [ ] `asyncio.gather`로 location 병렬 생성
- [ ] 개별 location 실패 시 나머지 계속 진행 (기존 동작 유지)
- [ ] 단위 테스트 통과

---

## 테스트 계획

### 신규 테스트 (예상 총 33개)

| Sprint | 테스트 유형 | 항목 | 개수 |
|--------|------------|------|------|
| A | 단위 | checkStageStep 환경 태그 예외 | 3 |
| B | 단위 | checkTtsStep + TTS prebuild API | 4 |
| B | 단위 | is_temp promote 검증 | 2 |
| B-2 | 단위 | buildRenderScenePayload 함수 (scene_db_id 포함) | 2 |
| B-2 | 단위 | data URL 가드 | 1 |
| C | 단위 | checkBgm bgmMode 파라미터 | 3 |
| C | 단위 | stepsToRun 일관성 (3곳 통일) | 2 |
| D | 단위 | Checkpoint localStorage 영속화 | 3 |
| D | 단위 | AutoRunStatus 완료 단계 버튼 비활성 | 2 |
| D | 단위 | batch seed 존중 | 1 |
| D | 단위 | canStore=false 에러 로그 | 1 |
| D | E2E | Resume 전체 플로우 | 1 |
| E | 단위 | location key 통합 함수 | 3 |
| E | 단위 | 단계 의존성 체크 | 2 |
| **합계** | — | — | **30** |

### DoD 검증 체크리스트

Phase 32 완료 후 `PRD.md §4` 기준으로 다음을 검증한다:

- [ ] **Autopilot**: 환경 태그 없는 씬 포함 스토리보드에서 Auto Run 시 stage 1회만 실행 확인
- [ ] **Autopilot**: `stage → images → tts → render` 4단계 멈춤 없이 진행 확인
- [ ] **Consistency**: Auto Run 완료 다음날 render 시 TTS 음성 정상 출력 (is_temp promote 검증)
- [ ] **Rendering**: TTS prebuild 실패 씬에서 render fallback으로 TTS 생성 후 정상 영상 출력
- [ ] **Voice Design**: Auto Run render 후 `voice_design_prompt`가 DB에 write-back 확인 (scene_db_id)
- [ ] **UI Resilience**: Auto Run 중 새로고침 후 ResumeConfirmModal 표시 + Resume 정상 동작
- [ ] **Data Integrity**: render 페이로드에 data URL 씬이 포함되지 않음 확인

---

## 의존성 순서

```
Sprint A (stage 루프) → Sprint C-2 (stepsToRun 통일)
Sprint B-2 (render 페이로드 통합) ← 먼저: scene_db_id 즉시 수정
Sprint B (TTS 단계 추가) → Sprint D-1 (Resume: 4단계 기준 checkpoint)
Sprint C-1 (checkBgm) 독립 실행 가능
Sprint D 나머지 독립 실행 가능
Sprint E 모두 독립 실행 가능 (단, E-2는 DBA 리뷰 필요)
```

권장 실행 순서: **B2-1(즉시) → A → C-2 → B2-2 → B → D-1 → D-2 → D-3~5 병렬 → C-1 → E**

> **B2-1이 최우선**: `scene_db_id` 1줄 추가로 voice_design write-back 복구. 가장 적은 비용으로 가장 큰 효과.

---

## 완료 체크리스트

### Sprint A
- [ ] A-1: checkStageStep 환경 태그 예외 처리 (preflight-steps.ts)
- [ ] A-2: stage 부분 실패 경고 로그 (autopilotActions.ts)

### Sprint B
- [ ] B-1: AUTO_RUN_STEPS에 tts 단계 추가 (constants, autopilotActions, preflight)
- [ ] B-1: TTS prebuild API 구현 (backend)
- [ ] B-2: render 완료 후 tts_asset is_temp=False promote
- [ ] B-3: SCENE_TRANSIENT_FIELDS / tts_asset_id 의미론 정합성

### Sprint B-2
- [ ] B2-1: autopilotActions.ts render 페이로드에 scene_db_id 추가 (**최우선**)
- [ ] B2-2: buildRenderScenePayload / buildRenderPayload 공통 함수 추출
- [ ] B2-3: Auto Run render data URL 가드

### Sprint C
- [ ] C-1: checkBgm bgmMode 파라미터 추가 (preflight.ts)
- [ ] C-2: stepsToRun 누락 3곳 일괄 수정 (studio/page.tsx)

### Sprint D
- [ ] D-1: Checkpoint localStorage 영속화 + ResumeConfirmModal 연결
- [ ] D-2: AutoRunStatus 완료 단계 버튼 비활성 (AutoRunStatus.tsx)
- [ ] D-3: batchActions.ts seed 강제 -1 제거
- [ ] D-4: generateBatchImages canStore=false 에러 로그
- [ ] D-5: autoRunProgress progress bar 연결 (AutoRunStatus.tsx)

### Sprint E
- [ ] E-1: TTS_ENGINE 상수 SSOT 통합
- [ ] E-2: _BG_QUALITY_OVERRIDES StyleProfile ID 하드코딩 제거 (DBA 리뷰 필요)
- [ ] E-3: location key 계산 로직 통합 (background_generator.py)
- [ ] E-4: renderWithProgress polling AbortSignal 전달
- [ ] E-5: PreflightModal 단계 의존성 체크
- [ ] E-6: lastRenderHash 미사용 필드 처리
- [ ] E-7: Stage location 생성 asyncio.gather 병렬화

### 문서
- [ ] ROADMAP.md Phase 32 항목 추가
- [ ] REST_API.md TTS prebuild 엔드포인트 추가
