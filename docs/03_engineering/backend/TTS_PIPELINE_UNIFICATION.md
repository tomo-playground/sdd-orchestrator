# TTS Pipeline 일원화 설계

**목표**: TTS 오디오 생성 로직을 단일 코어 함수(`generate_tts_audio`)로 통합. 렌더링(`scene_processing.py`)에서 TTS 생성 코드를 완전 제거.

**원칙**: "TTS는 프리뷰/prebuild에서 생성 → 렌더링은 재사용만"

---

## 1. 현재 상태 (AS-IS)

### 3경로 중복

```
preview_tts.py    → _generate_scene_tts()    92줄  (프리뷰 재생)
tts_prebuild.py   → _generate_audio()        70줄  (Auto Run tts 단계)
scene_processing.py → generate_tts()         209줄 (렌더링 독자 생성 — 레거시)
```

### 경로별 기능 비교

| 기능 | preview | prebuild | render (레거시) |
|------|---------|----------|----------------|
| voice_preset 해석 | O | O | O |
| scene_emotion 반영 | O (단건만, 배치 누락) | **X** | O |
| force_regenerate | O | **X** | X |
| Gemini voice design (4-Priority) | **X** | **X** | O |
| retry (3회) | **X** | **X** | O |
| retry 시 voice_design 단순화 | **X** | **X** | O (attempt별 축약) |
| voice_design DB write-back | **X** | **X** | O |
| TTS_VOICE_CONSISTENCY_MODE | **X** | **X** | O |
| 캐시 키에 scene_emotion | O | **X (버그)** | O |
| language 소스 | req 전달 | 하드코딩 "korean" | config 상수 |
| 반환 메타데이터 | 6종 | 2종 (bytes, duration) | bool, duration |
| MinIO 저장 | is_temp=True | is_temp=False | X (로컬만) |
| DB Scene FK 업데이트 | X | O | X |

### 기존 버그

1. **캐시 키 불일치**: prebuild에 `scene_emotion` 미전달 → 프리뷰와 다른 캐시 키 → 재생성
2. **스크립트 수정 시 tts_asset_id 미무효화**: Frontend에서 script 수정해도 이전 TTS 유지
3. **배치 프리뷰에 scene_emotion 누락**: `useTTSPreview.previewAll()`에서 scene_emotion 미전달
4. **voice_design_prompt/speaker 변경 시에도 tts_asset_id 미무효화**

---

## 2. 목표 상태 (TO-BE)

```
tts_helpers.py
  └── generate_tts_audio()          ← TTS 생성 SSOT (유일한 생성 경로)
  └── resolve_voice_design()        ← 4-Priority voice design 해석 (SSOT)
  └── persist_voice_design()        ← DB write-back (이동)
       │
       ├── preview_tts.py           → generate_tts_audio(max_retries=0) + MinIO(is_temp=True) + 응답 구성
       ├── tts_prebuild.py          → generate_tts_audio(max_retries=2) + MinIO(is_temp=False) + Scene FK
       │
       └── scene_processing.py      → tts_asset_id 로드 전용 + 무음 fallback (생성 0줄)

usePublishRender.ts                 → 렌더 전 tts-prebuild 자동 호출 (수동 렌더 통합)
Store.updateScene()                 → script/speaker/voice_design_prompt 변경 시 tts_asset_id = null 자동 리셋
```

---

## 3. 핵심 설계

### 3-1. `generate_tts_audio()` — 코어 함수 (tts_helpers.py 추가)

```python
@dataclass
class TtsAudioResult:
    """TTS 생성 결과 (DB/저장 무관한 순수 오디오 + 메타데이터)."""
    audio_bytes: bytes
    duration: float
    cache_key: str
    cached: bool
    voice_seed: int
    voice_design: str | None      # 최종 적용된 voice design (번역 후)
    was_gemini_generated: bool     # Gemini가 새로 생성했는지 (write-back 판단용)


async def generate_tts_audio(
    *,
    script: str,
    speaker: str = DEFAULT_SPEAKER,
    # voice preset — 호출측에서 resolve 완료된 값 전달
    voice_preset_id: int | None = None,
    # voice design — Priority별 분리 전달
    scene_voice_design: str | None = None,    # Priority 0: 씬별 (파이프라인 결과)
    global_voice_design: str | None = None,   # Priority 2: 글로벌 (render panel)
    scene_emotion: str = "",
    language: str = TTS_DEFAULT_LANGUAGE,
    force_regenerate: bool = False,
    max_retries: int = 0,
    # Gemini voice design용 context (prebuild에서만 사용, preview에서는 None)
    image_prompt_ko: str | None = None,
    scene_db_id: int | None = None,
    task_id: str = "default",
) -> TtsAudioResult:
    ...
```

**설계 결정 사항**:

1. **voice_preset_id 해석은 호출측 책임**: 코어 함수에 `storyboard_id`를 전달하지 않음. 호출측(preview/prebuild)에서 `get_speaker_voice_preset()`으로 미리 resolve하여 전달. → 코어 함수의 DB 의존성 최소화.

2. **voice_design은 scene/global 분리 전달**: `scene_voice_design` (Priority 0)과 `global_voice_design` (Priority 2)을 별도 파라미터로 받음. 내부에서 `resolve_voice_design()`에 위임.

3. **캐시 키에는 resolve 전 원본 사용**: `resolve_voice_design()` 호출 전에 캐시 키를 계산. Gemini의 non-deterministic 응답이 캐시 키에 영향을 주지 않도록 보장.

**내부 흐름**:
1. `clean_script_for_tts()` + `has_speakable_content()` 검증
2. `get_preset_voice_info(voice_preset_id)` → preset_voice_design, preset_seed
3. `tts_cache_key()` 계산 (scene_emotion 포함, **resolve/번역 전 원본**)
4. `force_regenerate` 시 캐시 삭제
5. 캐시 hit → 즉시 반환 (`cached=True`)
6. `resolve_voice_design()` — 4-Priority (아래 3-2 참조)
7. `translate_voice_prompt()` — 한국어→영어 번역
8. 캐시 miss → Audio Server 호출 (retry 포함, 아래 3-3 참조)
9. `_atomic_cache_write()` — 캐시 저장
10. `was_gemini_generated=True`면 호출측에서 `persist_voice_design()` 판단

### 3-2. `resolve_voice_design()` — 4-Priority 통합 (tts_helpers.py 추가)

`scene_processing._get_voice_design_for_scene()`을 `VideoBuilder` 의존성 제거하여 이동.

```python
def resolve_voice_design(
    *,
    scene_voice_design: str | None,      # Priority 0: 파이프라인 결과
    preset_voice_design: str | None,     # preset에서 로드
    global_voice_design: str | None,     # Priority 2: render panel
    scene_emotion: str | None,
    clean_script: str,
    image_prompt_ko: str | None = None,
    speaker: str = DEFAULT_SPEAKER,
    scene_idx: int = 0,
) -> tuple[str | None, bool]:
    """
    Returns: (voice_design, was_gemini_generated)

    Priority 0: scene_voice_design (파이프라인 결과 재사용)
    Priority 1: preset + Gemini 감정 적응 (TTS_VOICE_CONSISTENCY_MODE 시 Gemini 스킵)
    Priority 2: 명시적 per-scene/global prompt
    Priority 3: Gemini context-aware 자동 생성
    """
```

**호출측 매핑**:

| 호출측 | scene_voice_design | preset | global | image_prompt_ko | 활성 Priority |
|--------|-------------------|--------|--------|-----------------|--------------|
| preview | req.voice_design_prompt | from_db | None | None | 0, 2 (Gemini 미호출) |
| prebuild | item.voice_design_prompt | from_db | None | item.image_prompt_ko | 0, 1, 2, 3 (전체) |
| ~~render~~ | ~~제거~~ | — | — | — | — |

**preview에서 Gemini를 호출하지 않는 이유**: 프리뷰는 즉시 응답이 필요하고 (사용자가 재생 버튼 클릭), 현재도 Gemini 없이 동작합니다. Prebuild에서 Gemini가 결정한 voice_design이 DB에 write-back되면, 이후 프리뷰에서는 Priority 0으로 재사용됩니다.

**preview의 scene_emotion 처리**: 현재 preview에서 emotion을 voice_design에 단순 append하는 로직(`f"{voice_design}, {scene_emotion}"`)은 `resolve_voice_design()` Priority 1의 fallback 분기와 동일. 코어 함수 내부에서 통합 처리.

### 3-3. Retry 전략

| 호출측 | max_retries | 근거 |
|--------|-------------|------|
| preview (단건/배치) | 0 | 즉시 응답 필수. 실패 시 사용자가 재생성 클릭 |
| prebuild | 2 (총 3회) | 렌더 전 품질 보증. Auto Run 시간 여유 있음 |

**retry 시 voice_design 단순화 전략** (기존 scene_processing 로직 이식):
- attempt 0: 원본 voice_design
- attempt 1: voice_design의 첫 번째 쉼표 앞 부분만 사용 (단순화)
- attempt 2: preset_voice_design 원본 (Gemini 적응 제거)

### 3-4. `scene_processing.py` generate_tts() 축소

```python
async def generate_tts(builder, i, clean_script, tts_path) -> tuple[bool, float]:
    """tts_asset_id로 사전 생성된 TTS를 로드한다. 생성 로직 없음."""
    if not clean_script.strip():
        return False, 0.0

    scene_req = builder.request.scenes[i]
    tts_asset_id = scene_req.tts_asset_id

    if tts_asset_id is not None:
        # 기존 asset 로드 + is_temp 승격 로직 유지 (337-378줄)
        ...
        return True, tts_duration

    # tts_asset_id 없음 → 무음 처리 + 경고
    logger.warning("Scene %d: tts_asset_id 없음 — 무음 처리", i)
    return False, 0.0
```

**제거 대상** (약 260줄):
- `_resolve_voice_preset_id()` — tts_helpers로 이동
- `_get_voice_design_for_scene()` — `resolve_voice_design()`으로 통합
- `_persist_voice_design()` — `tts_helpers.py`로 이동
- `_calculate_max_new_tokens()` — `generate_tts_audio()`로 흡수
- `_atomic_cache_write()` — `tts_helpers.py`로 이동
- retry 루프 (461-517줄) — `generate_tts_audio()`로 흡수
- 캐시 조회 (387-401줄) — `generate_tts_audio()`로 흡수

**유지 대상** (약 50줄):
- tts_asset_id 로드 + is_temp 승격 브릿지 (337-378줄)
- `_audio_scene_success/failure` circuit breaker 호출

### 3-5. 세마포어 통합

현재 preview와 prebuild에 독립 세마포어 2개 → 동시 최대 6건 Audio Server 요청 가능.

```python
# tts_helpers.py에 공용 세마포어 정의
TTS_CONCURRENCY_SEMAPHORE = asyncio.Semaphore(TTS_MAX_CONCURRENCY)  # config.py에서 관리
```

- `generate_tts_audio()` 내부에는 세마포어를 넣지 않음 (코어 함수는 순수)
- 호출측(preview batch, prebuild)에서 공용 세마포어를 사용
- 기존 `_TTS_BATCH_SEMAPHORE`, `_PREBUILD_SEMAPHORE` 제거

### 3-6. `_wav_duration()` 통합

`preview_tts.py:179`와 `tts_prebuild.py:103`에 중복. `generate_tts_audio()` 내부에서 duration을 계산하여 `TtsAudioResult.duration`으로 반환하므로, 호출측에서 별도 계산 불필요. 중복 함수 제거.

### 3-7. 파일 크기 관리

현재 `tts_helpers.py`는 287줄. 코어 함수 추가 시 약 407줄 예상 (가이드라인 400줄 최대 경계).

**대응**: `generate_context_aware_voice_prompt()` (약 70줄)이 `resolve_voice_design()` 내부에서만 호출되므로, 두 함수를 합산해도 기존 코드 이동이지 순증가는 아님. 400줄 초과 시 `tts_voice_design.py`로 voice design 관련 함수만 분리 검토.

---

## 4. Frontend 변경

### 4-1. 수동 렌더에 prebuild 자동 삽입 (usePublishRender.ts)

```typescript
// handleRender() 시작 시:
const missingTts = renderScenes.filter(s => s.script?.trim() && !s.tts_asset_id);
if (missingTts.length > 0) {
  // "TTS 준비 중" 진행률 표시 — renderProgress에 phase 추가
  setRenderProgress({ phase: "tts-preparing", percent: 0 });

  const prebuildRes = await api.post(`${API_BASE}/scene/tts-prebuild`, {
    storyboard_id,
    scenes: missingTts.map(s => ({
      scene_db_id: s.id,
      script: s.script,
      speaker: s.speaker,
      voice_design_prompt: s.voice_design_prompt ?? undefined,
      scene_emotion: s.context_tags?.emotion ?? undefined,
      image_prompt_ko: s.image_prompt_ko ?? undefined,
    })),
  });

  // 결과의 tts_asset_id를 Store에 반영
  for (const r of prebuildRes.data.results) {
    if (r.tts_asset_id) {
      const matched = renderScenes.find(s => s.id === r.scene_db_id);
      if (matched) updateScene(matched.client_id, { tts_asset_id: r.tts_asset_id });
    }
  }

  // ★ prebuild 반영 후 renderScenes를 재조회 (stale 방지)
  const freshScenes = useStoryboardStore.getState().scenes;
  renderScenes = freshScenes.filter(/* 기존 필터 조건 */);
}
// 이후 기존 렌더 로직 실행 (renderScenes에 tts_asset_id 반영됨)
```

**진행률 표시**: `useRenderStore`의 `renderProgress`에 `phase` 필드를 추가. UI에서 `phase === "tts-preparing"` 시 "TTS 준비 중..." 텍스트 표시.

### 4-2. tts_asset_id 자동 무효화 (useStoryboardStore.ts)

**트리거 필드**: `script`, `speaker`, `voice_design_prompt` 3개 변경 시 리셋.

```typescript
updateScene(clientId, updates) {
  const existing = scenes.find(s => s.client_id === clientId);
  if (existing) {
    const ttsInvalidatingFields = ['script', 'speaker', 'voice_design_prompt'] as const;
    const needsReset = ttsInvalidatingFields.some(
      field => field in updates && updates[field] !== existing[field]
    );
    if (needsReset) {
      updates.tts_asset_id = null;
    }
  }
  // ... 기존 머지 로직
}
```

### 4-3. autopilotActions.ts — scene_emotion/image_prompt_ko 전달 추가

```typescript
scenes: workingScenes.map(s => ({
  scene_db_id: s.id,
  script: s.script,
  speaker: s.speaker,
  voice_design_prompt: s.voice_design_prompt ?? undefined,
  tts_asset_id: s.tts_asset_id ?? undefined,
  scene_emotion: s.context_tags?.emotion ?? undefined,       // 추가
  image_prompt_ko: s.image_prompt_ko ?? undefined,           // 추가
})),
```

### 4-4. useTTSPreview.ts — 배치에 scene_emotion 추가

```typescript
// previewAll() 배치 호출에 scene_emotion 추가
scenes: scenes.map((s) => ({
  script: s.script,
  speaker: s.speaker || "Narrator",
  storyboard_id: storyboardId,
  voice_design_prompt: s.voice_design_prompt || null,
  scene_emotion: s.context_tags?.emotion ?? undefined,  // 추가
  language: "korean",
})),
```

---

## 5. Backend 스키마 변경

### TtsPrebuildSceneItem 확장

```python
class TtsPrebuildSceneItem(BaseModel):
    scene_db_id: int
    script: str
    speaker: str = DEFAULT_SPEAKER
    voice_design_prompt: str | None = None
    tts_asset_id: int | None = None
    scene_emotion: str | None = None       # 추가
    image_prompt_ko: str | None = None     # 추가 (Gemini voice design용)
```

---

## 6. 마이그레이션 순서

안전한 점진적 전환. **Frontend를 Backend 축소보다 먼저 적용**하여 수동 렌더 회귀 방지.

### Sprint A: 코어 추출 (Backend)

| # | 작업 | 파일 |
|---|------|------|
| A-1 | `TtsAudioResult` dataclass + `generate_tts_audio()` 코어 함수 추가 | tts_helpers.py |
| A-2 | `resolve_voice_design()` 추가 (`_get_voice_design_for_scene` 이동 + VideoBuilder 제거 + `TTS_VOICE_CONSISTENCY_MODE` 포함) | tts_helpers.py |
| A-3 | `persist_voice_design()` + `_atomic_cache_write()` + `_calculate_max_new_tokens()` 이동 | tts_helpers.py |
| A-4 | 공용 세마포어 `TTS_CONCURRENCY_SEMAPHORE` 정의 | tts_helpers.py |
| A-5 | 단위 테스트 — generate_tts_audio 캐시 hit/miss, resolve_voice_design 4-Priority, consistency mode, retry 단순화 | tests/ |

### Sprint B: 기존 경로 전환 (Backend)

| # | 작업 | 파일 |
|---|------|------|
| B-1 | `preview_tts._generate_scene_tts()` → `generate_tts_audio()` 호출로 교체 + `_wav_duration` 제거 | preview_tts.py |
| B-2 | `tts_prebuild._generate_audio()` → `generate_tts_audio()` 호출로 교체 + `_wav_duration` 제거 | tts_prebuild.py |
| B-3 | 기존 세마포어 → 공용 `TTS_CONCURRENCY_SEMAPHORE`로 교체 | preview_tts.py, tts_prebuild.py |
| B-4 | `TtsPrebuildSceneItem` 스키마에 `scene_emotion`, `image_prompt_ko` 추가 | schemas.py |
| B-5 | 캐시 키 동일성 golden test — 전환 전후 동일 입력에 동일 캐시 키 보장 | tests/ |

### Sprint C: Frontend 통합 (★ Backend 축소보다 먼저)

| # | 작업 | 파일 |
|---|------|------|
| C-1 | `usePublishRender.ts` — 렌더 전 tts-prebuild 자동 호출 + "TTS 준비 중" phase + renderScenes 재조회 | usePublishRender.ts |
| C-2 | `autopilotActions.ts` — scene_emotion, image_prompt_ko 전달 추가 | autopilotActions.ts |
| C-3 | `useStoryboardStore.updateScene()` — script/speaker/voice_design_prompt 변경 시 tts_asset_id null 리셋 | useStoryboardStore.ts |
| C-4 | `useTTSPreview.ts` — 배치에 scene_emotion 추가 | useTTSPreview.ts |
| C-5 | `useRenderStore` — renderProgress에 `phase` 필드 추가 | useRenderStore.ts |

### Sprint D: 렌더링 축소 (Backend — Frontend 완료 후)

| # | 작업 | 파일 |
|---|------|------|
| D-1 | `scene_processing.generate_tts()` — 독자 생성 로직 완전 제거, tts_asset_id 로드 + 무음 fallback만 유지 | scene_processing.py |
| D-2 | `_get_voice_design_for_scene()`, `_persist_voice_design()`, `_resolve_voice_preset_id()`, `_calculate_max_new_tokens()`, `_atomic_cache_write()` 제거 | scene_processing.py |
| D-3 | 기존 렌더링 TTS 테스트 갱신 | tests/ |

---

## 7. 리스크 & 대응

| 리스크 | 심각도 | 대응 |
|--------|--------|------|
| **캐시 키 변경으로 기존 캐시 전부 miss** | 높 | Sprint B-5에서 캐시 키 golden test 필수. 캐시 키 입력은 반드시 resolve/번역 전 원본 사용 |
| Sprint D를 Sprint C 전에 적용 시 수동 렌더 TTS 전부 무음 | 높 | **Sprint C(Frontend)를 D(Backend)보다 먼저 적용** — 마이그레이션 순서로 방지 |
| prebuild에 Gemini 호출 추가 → TTS 단계 실행 시간 증가 | 중 | Gemini 실패 시 preset fallback. 사용자 체감은 동일 (렌더 내부 → prebuild로 이동) |
| 수동 렌더 시 prebuild 추가 대기 시간 | 중 | 프리뷰/Auto Run에서 이미 생성된 씬은 캐시 hit로 즉시 통과. "TTS 준비 중" 진행률 표시 |
| prebuild 후 renderScenes가 stale 데이터 참조 | 중 | prebuild 완료 후 `getState().scenes`로 재조회 (Sprint C-1) |
| script/speaker/voice_design 변경 시 tts_asset_id null 리셋 → 빈번한 재생성 | 저 | 캐시 키가 입력 기반이므로 캐시 hit 가능. MinIO 재저장만 발생 |
| Audio Server 다운 시 렌더 불가 | 중 | scene_processing에 무음 fallback 유지 (기존과 동일) |
| tts_helpers.py 400줄 초과 | 저 | 초과 시 `tts_voice_design.py`로 voice design 관련 함수 분리 |

---

## 8. 테스트 계획

### 단위 테스트 (Sprint A-5, B-5)

| 테스트 | 검증 내용 |
|--------|----------|
| `generate_tts_audio` 캐시 hit | 캐시 파일 존재 시 Audio Server 호출 없이 반환 |
| `generate_tts_audio` 캐시 miss | Audio Server 호출 + 캐시 저장 + 메타데이터 반환 |
| `generate_tts_audio` force_regenerate | 캐시 삭제 후 재생성 |
| `generate_tts_audio` retry 단순화 | attempt별 voice_design 축약 동작 |
| `resolve_voice_design` Priority 0 | scene_voice_design 있으면 즉시 반환 |
| `resolve_voice_design` Priority 1 | preset + Gemini 감정 적응 |
| `resolve_voice_design` Priority 1 consistency mode | `TTS_VOICE_CONSISTENCY_MODE=True` 시 Gemini 스킵 |
| `resolve_voice_design` Priority 2 | global fallback |
| `resolve_voice_design` Priority 3 | Gemini 자동 생성 |
| 캐시 키 golden test | 전환 전후 동일 입력 → 동일 캐시 키 |

### 통합 테스트 (Sprint C, D)

| 테스트 | 검증 내용 |
|--------|----------|
| preview → prebuild 캐시 재사용 | 프리뷰 후 prebuild 시 캐시 hit |
| updateScene script 변경 → tts_asset_id null | script 수정 시 자동 리셋, 동일 script 시 유지 |
| 수동 렌더 prebuild 자동 삽입 | tts_asset_id 없는 씬에 대해 prebuild 호출 후 렌더 |
| Audio Server 다운 → 무음 fallback | prebuild 실패 → 렌더 시 무음 처리 |

---

## 9. 예상 코드 변화량

| 파일 | 추가 | 삭제 | 순변화 |
|------|------|------|--------|
| tts_helpers.py | +130 | 0 | +130 |
| preview_tts.py | +10 | -70 | -60 |
| tts_prebuild.py | +15 | -60 | -45 |
| scene_processing.py | +5 | -260 | -255 |
| schemas.py | +2 | 0 | +2 |
| usePublishRender.ts | +30 | 0 | +30 |
| autopilotActions.ts | +2 | 0 | +2 |
| useStoryboardStore.ts | +8 | 0 | +8 |
| useTTSPreview.ts | +1 | 0 | +1 |
| useRenderStore.ts | +3 | 0 | +3 |
| tests/ | +80 | -30 | +50 |
| **합계** | **+286** | **-420** | **-134** |
