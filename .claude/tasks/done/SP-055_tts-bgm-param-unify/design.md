# SP-055 상세 설계: TTS/BGM 파라미터 통일

## 설계 원칙

이미지 생성이 `buildSceneRequest()` 단일 조립 함수로 경로 불일치를 방지한 것과 동일한 패턴을 TTS/BGM에 적용한다.

```
Before:
  autopilotActions → 직접 조립 → /scene/tts-prebuild → tts_prebuild._generate_audio() → generate_tts_audio()
  useTTSPreview    → 직접 조립 → /preview/tts        → preview_tts._generate_scene_tts() → generate_tts_audio()
  (파라미터 제각각)

After:
  autopilotActions → buildTtsRequest() → /scene/tts-prebuild → tts_core.generate_scene_tts() → generate_tts_audio()
  useTTSPreview    → buildTtsRequest() → /preview/tts        → tts_core.generate_scene_tts() → generate_tts_audio()
  (단일 조립 + 단일 래퍼)
```

---

## DoD-1: Frontend `buildTtsRequest()` 함수 추가

- **구현**: `frontend/app/utils/buildTtsRequest.ts` 신규 생성
  - `buildTtsRequest(scene: Scene, storyboardId: number | null): TtsPrebuildSceneItem`
  - Scene 객체에서 TTS 요청에 필요한 필드를 추출하는 순수 함수
  - 반환 타입은 prebuild/preview 양쪽 스키마의 공통 필드 (scene_db_id, script, speaker, voice_design_prompt, scene_emotion, image_prompt_ko, language)
- **동작**: 호출부에서 직접 `{ script: s.script, speaker: s.speaker, ... }` 조립 → `buildTtsRequest(scene, storyboardId)` 호출로 대체
- **엣지**: scene.script가 null/empty면 빈 문자열 반환 (Backend가 validation)
- **영향**: 순수 함수 추가이므로 기존 동작에 영향 없음
- **테스트**: `buildTtsRequest(mockScene, 123)` 호출 → 반환 객체의 모든 필드 검증 (image_prompt_ko, language 포함 확인)
- **OoS**: 반환 타입을 새 interface로 정의하지 않음 — 기존 스키마 재사용

## DoD-2~5: 4곳 호출부 전환

### DoD-2: `autopilotActions.ts` tts-prebuild 호출 전환
- **구현**: `autopilotActions.ts:319-327`의 인라인 매핑을 `buildTtsRequest()` 호출로 교체
  ```
  Before: ttsScenes = workingScenes.filter(...).map(s => ({ scene_db_id: s.id, script: s.script, ... }))
  After:  ttsScenes = workingScenes.filter(...).map(s => buildTtsRequest(s, storyboardId))
  ```
- **동작**: 기존과 동일한 페이로드 + `language` 필드 추가
- **엣지**: `tts_asset_id` 필드는 prebuild 전용이므로 `buildTtsRequest` 반환 후 호출부에서 spread + `tts_asset_id: s.tts_asset_id` 추가
- **영향**: 오토런 TTS에 `language` 필드가 새로 전달됨 → 캐시 키 변경으로 기존 캐시 미스 가능 (의도된 동작)
- **테스트**: 기존 오토런 E2E 테스트가 있으면 regression 확인
- **OoS**: autopilotActions의 다른 단계(images, bgm) 수정은 별도 DoD

### DoD-3: `useTTSPreview.ts` preview/tts 호출 전환
- **구현**: `useTTSPreview.ts:55-63` (previewScene), `91-98` (previewAll), `146-154` (regenerate) 3곳의 인라인 매핑을 `buildTtsRequest()` 호출로 교체
  ```
  Before: { script: scene.script, speaker: scene.speaker || "Narrator", ... image_prompt_ko 누락 }
  After:  { ...buildTtsRequest(scene, storyboardId), force_regenerate: true }  // regenerate 시
  ```
- **동작**: 기존과 동일 + `image_prompt_ko` 필드 추가 전달
- **엣지**: `force_regenerate`, `voice_preset_id`는 preview 전용 파라미터 — `buildTtsRequest` 반환 후 호출부에서 추가
- **영향**: 수동 TTS에 `image_prompt_ko`가 새로 전달됨 → Gemini voice_design 생성 시 이미지 컨텍스트 활용
- **테스트**: useTTSPreview 단위 테스트에서 요청 페이로드에 image_prompt_ko 포함 검증
- **OoS**: `voice_preset_id` resolve 로직 변경 금지 (기존 유지)

### DoD-4: `ScenesTab.tsx` tts-prebuild 호출 전환
- **구현**: `ScenesTab.tsx:144-151`의 인라인 매핑을 `buildTtsRequest()` 호출로 교체
- **동작**: DoD-2와 동일 패턴
- **엣지**: 동일
- **영향**: 동일
- **테스트**: 기존 컴포넌트 테스트 regression 확인
- **OoS**: ScenesTab UI 변경 금지

### DoD-5: `usePublishRender.ts` tts-prebuild 호출 전환
- **구현**: `usePublishRender.ts:144-151`의 인라인 매핑을 `buildTtsRequest()` 호출로 교체
- **동작**: DoD-2와 동일 패턴
- **엣지**: 동일
- **영향**: 동일
- **테스트**: 기존 렌더 테스트 regression 확인
- **OoS**: usePublishRender의 렌더링 로직 변경 금지

---

## DoD-6: Backend `SceneTTSPreviewRequest` 스키마에 `image_prompt_ko` 추가

- **구현**: `backend/schemas.py` `SceneTTSPreviewRequest` 클래스에 필드 추가
  ```python
  image_prompt_ko: str | None = None  # Gemini voice_design 컨텍스트용
  ```
- **동작**: Before: preview 요청에 image_prompt_ko 전달 불가. After: 전달 가능 (optional, 기존 호출 호환)
- **엣지**: 기존 클라이언트가 image_prompt_ko를 보내지 않아도 None으로 동작 (후방 호환)
- **영향**: 없음 (optional 필드 추가)
- **테스트**: SceneTTSPreviewRequest 파싱 테스트 — image_prompt_ko 포함/미포함 양쪽 검증
- **OoS**: TtsPrebuildSceneItem 스키마 변경 금지 (이미 image_prompt_ko 있음)

---

## DoD-7: Backend `tts_core.generate_scene_tts()` 통합 래퍼

- **구현**: `backend/services/tts_core.py` 신규 생성
  ```python
  async def generate_scene_tts(
      *,
      script: str,
      speaker: str,
      storyboard_id: int | None,
      scene_db_id: int | None = None,
      voice_design_prompt: str | None = None,
      scene_emotion: str | None = None,
      image_prompt_ko: str | None = None,
      language: str | None = None,
      force_regenerate: bool = False,
  ) -> TtsAudioResult:
  ```
  내부:
  1. `get_speaker_voice_preset(storyboard_id, speaker)` → voice_preset_id resolve
  2. `generate_tts_audio(...)` 호출 — `max_retries=TTS_MAX_RETRIES` (config.py SSOT)
  3. `result.was_gemini_generated and scene_db_id` → `persist_voice_design()` write-back
  4. `TtsAudioResult` 반환
- **동작**: Before: 2개 래퍼가 제각각 파라미터 조립. After: 단일 래퍼가 동일 파라미터 보장
- **엣지**: `storyboard_id=None`이면 `voice_preset_id=None` → generate_tts_audio가 preset 없이 동작 (기존 동작)
- **영향**: 기존 generate_tts_audio() 시그니처 변경 없음. 호출 체인에 중간 레이어 추가만.
- **테스트**:
  - `generate_scene_tts(script="안녕", speaker="A", storyboard_id=1)` → generate_tts_audio가 `max_retries=TTS_MAX_RETRIES`, `language=language`, `image_prompt_ko=image_prompt_ko`로 호출되었는지 mock 검증
  - `was_gemini_generated=True, scene_db_id=5` → `persist_voice_design` 호출 검증
  - `was_gemini_generated=True, scene_db_id=None` → `persist_voice_design` 미호출 검증
- **OoS**: `generate_tts_audio()` (tts_helpers.py) 시그니처/내부 로직 변경 금지

## DoD-8: `tts_prebuild._generate_audio()` 전환

- **구현**: `backend/services/tts_prebuild.py`의 `_generate_audio()` 함수 본문을 `tts_core.generate_scene_tts()` 호출로 교체
  ```python
  async def _generate_audio(...) -> tuple[bytes, float]:
      from services.tts_core import generate_scene_tts
      result = await generate_scene_tts(
          script=script, speaker=speaker, storyboard_id=storyboard_id,
          scene_db_id=scene_db_id, voice_design_prompt=voice_design_prompt,
          scene_emotion=scene_emotion, image_prompt_ko=image_prompt_ko,
          language=language,
      )
      return result.audio_bytes, result.duration
  ```
- **동작**: Before: 직접 generate_tts_audio 호출 + persist_voice_design. After: tts_core 경유 (동일 결과)
- **엣지**: `language` 파라미터가 새로 추가됨 — TtsPrebuildSceneItem에 `language` 필드 추가 필요 (optional, default None)
- **영향**: prebuild 캐시 키가 language를 포함하므로, language 값 변경 시 캐시 미스 (의도된 동작)
- **테스트**: 기존 test_tts_prebuild.py regression 확인 + language 전달 검증
- **OoS**: _save_tts_asset(), _update_scene_tts_asset() 등 저장 로직 변경 금지

## DoD-9: `preview_tts._generate_scene_tts()` 전환

- **구현**: `backend/services/preview_tts.py`의 `_generate_scene_tts()` 함수 본문을 `tts_core.generate_scene_tts()` 호출로 교체
  ```python
  async def _generate_scene_tts(req: SceneTTSPreviewRequest) -> _TtsGenResult:
      from services.tts_core import generate_scene_tts
      result = await generate_scene_tts(
          script=req.script.strip(), speaker=req.speaker,
          storyboard_id=req.storyboard_id, scene_db_id=req.scene_db_id,
          voice_design_prompt=req.voice_design_prompt,
          scene_emotion=req.scene_emotion, image_prompt_ko=req.image_prompt_ko,
          language=req.language, force_regenerate=req.force_regenerate,
      )
      return _TtsGenResult(
          audio_bytes=result.audio_bytes, duration=result.duration,
          cache_key=result.cache_key, cached=result.cached,
          voice_seed=result.voice_seed, voice_design=result.voice_design,
      )
  ```
- **동작**: Before: 직접 generate_tts_audio 호출 (image_prompt_ko 누락, max_retries=1). After: tts_core 경유 (image_prompt_ko 전달, max_retries 통일)
- **엣지**: `has_speakable_content` 검증은 tts_core가 아닌 기존 위치 유지 (preview 전용 UX: 빈 스크립트면 즉시 ValueError)
- **영향**: max_retries가 1→2(config 값)로 변경 — 수동 TTS가 더 견고해짐, 응답 시간 약간 증가 가능
- **테스트**: preview_tts 단위 테스트에서 tts_core.generate_scene_tts 호출 mock 검증
- **OoS**: _save_audio_asset(), preview_scene_tts()의 저장/영구전환 로직 변경 금지

## DoD-10: `max_retries` config SSOT

- **구현**: `config.py`의 `TTS_MAX_RETRIES` (현재 이미 존재, 기본값 2)를 유일한 소스로 사용. `tts_core.py`에서 import하여 사용.
  - `tts_prebuild.py:49`의 `max_retries=2` 하드코딩 제거
  - `preview_tts.py:68`의 `max_retries=1` 하드코딩 제거
  - 양쪽 모두 `tts_core.generate_scene_tts()` 경유하므로 자동 통일
- **동작**: Before: prebuild=2, preview=1. After: 양쪽 모두 TTS_MAX_RETRIES(기본 2)
- **엣지**: 환경 변수 `TTS_MAX_RETRIES`로 런타임 조정 가능 (기존 동작)
- **영향**: 수동 프리뷰 응답 시간이 재시도 1회분 증가 가능 (worst case ~3초)
- **테스트**: DoD-7 테스트에서 max_retries=TTS_MAX_RETRIES 검증
- **OoS**: TTS_MAX_RETRIES 기본값 변경 금지

## DoD-11: `language` 파라미터 통일

- **구현**:
  - `TtsPrebuildSceneItem` 스키마에 `language: str | None = None` 필드 추가
  - Frontend `buildTtsRequest()`에서 `language: "korean"` 포함
  - `tts_prebuild.py`의 `_generate_audio()`에 `language` 파라미터 추가 → `tts_core`로 전달
  - `_prebuild_one()`에 `language` 파라미터 추가
  - `prebuild_tts_for_scenes()`에서 `item.language` 전달
- **동작**: Before: prebuild는 language=None(→TTS_DEFAULT_LANGUAGE fallback), preview는 req.language. After: 양쪽 모두 Frontend에서 전달한 language 사용
- **엣지**: Frontend가 language를 안 보내면 None → Backend에서 TTS_DEFAULT_LANGUAGE fallback (후방 호환)
- **영향**: prebuild 캐시 키에 language가 반영됨 → 기존 None 기반 캐시와 키가 달라져 캐시 미스 (1회성)
- **테스트**: prebuild 요청에 language="korean" 전달 → generate_tts_audio에 language="korean" 도달 검증
- **OoS**: TTS_DEFAULT_LANGUAGE 값 변경 금지

## DoD-12: `voice_design` write-back 통일

- **구현**: `tts_core.generate_scene_tts()` 내부에서 처리 (DoD-7에 포함). 기존 `tts_prebuild.py:54-56`의 write-back 코드 제거.
- **동작**: Before: prebuild만 write-back, preview는 안 함. After: 양쪽 모두 tts_core에서 write-back (scene_db_id가 있을 때)
- **엣지**: preview에서 scene_db_id=None이면 write-back 안 함 (기존 동작 유지)
- **영향**: 수동 프리뷰 시에도 Gemini 생성 voice_design이 DB에 저장됨 → 이후 렌더링에서 일관된 음성 보장
- **테스트**: DoD-7 테스트에 포함
- **OoS**: persist_voice_design() 내부 로직 변경 금지

---

## DoD-13: `BgmPrebuildRequest`에 `total_duration` 추가

- **구현**: `backend/schemas.py` `BgmPrebuildRequest`에 필드 추가
  ```python
  total_duration: float | None = None  # 씬 duration 합계 (BGM 길이 결정)
  ```
- **동작**: Before: 필드 없음. After: optional 필드 추가 (후방 호환)
- **엣지**: None이면 기존 30초 기본값 유지
- **영향**: 없음 (optional 필드 추가)
- **테스트**: BgmPrebuildRequest 파싱 테스트 — total_duration 포함/미포함
- **OoS**: BgmPrebuildResponse 변경 금지

## DoD-14: `bgm_prebuild.prebuild_bgm()` duration 계산 통일

- **구현**: `backend/services/bgm_prebuild.py`
  - `prebuild_bgm()` 시그니처에 `total_duration: float | None = None` 추가
  - `_generate_bgm()` 시그니처에 `duration: float` 추가 (기존 내부 30초 하드코딩 제거)
  - duration 계산: `min(max(30.0, total_duration or 30.0), MUSICGEN_MAX_DURATION)`
  - `routers/stage.py`의 `bgm_prebuild()` 핸들러에서 `body.total_duration` 전달
- **동작**: Before: 항상 30초. After: total_duration 기반 (없으면 30초 fallback)
- **엣지**: total_duration=0 or 음수 → max(30, ...) 로직으로 최소 30초 보장
- **영향**: builder.py의 `_prepare_auto_bgm()`과 동일한 duration 계산 로직
- **테스트**: prebuild_bgm(total_duration=60) → _generate_bgm이 duration=60으로 호출 검증
- **OoS**: builder.py의 `_prepare_auto_bgm()` 변경 금지 (이미 올바름)

## DoD-15: Frontend bgm-prebuild 호출 시 total_duration 전달

- **구현**: `frontend/app/store/actions/autopilotActions.ts:162-164`
  ```typescript
  const totalDur = workingScenes.reduce((sum, s) => sum + (s.duration || 3), 0);
  await axios.post(`${API_BASE}/storyboards/${storyboardId}/stage/bgm-prebuild`, {
    bgm_prompt: bgmPrompt,
    total_duration: totalDur,
  });
  ```
- **동작**: Before: bgm_prompt만 전달. After: total_duration 추가 전달
- **엣지**: workingScenes가 비어있으면 totalDur=0 → Backend에서 max(30, 0)=30초 (안전)
- **영향**: BGM prebuild 결과가 영상 길이에 맞게 생성됨
- **테스트**: autopilotActions의 BGM prebuild 호출 시 total_duration 포함 검증
- **OoS**: usePublishRender의 BGM 로직은 건드리지 않음 (렌더 시 builder.py가 처리)

---

## DoD-16~18: 품질 게이트

### DoD-16: 기존 테스트 regression 없음
- `pytest backend/tests/` 전체 통과

### DoD-17: 린트 통과
- `ruff check backend/` + `prettier --check frontend/`

### DoD-18: TTS 통합 래퍼 단위 테스트 추가
- **파일**: `backend/tests/services/test_tts_core.py` 신규
- **케이스**:
  1. 정상 호출 → generate_tts_audio에 올바른 파라미터 전달 검증 (max_retries, language, image_prompt_ko)
  2. was_gemini_generated=True + scene_db_id → persist_voice_design 호출
  3. was_gemini_generated=True + scene_db_id=None → persist_voice_design 미호출
  4. storyboard_id=None → voice_preset_id=None으로 호출

---

## 변경 파일 목록

| 파일 | 변경 | 유형 |
|------|------|------|
| `frontend/app/utils/buildTtsRequest.ts` | 신규 | Frontend |
| `frontend/app/store/actions/autopilotActions.ts` | TTS/BGM 호출부 수정 | Frontend |
| `frontend/app/hooks/useTTSPreview.ts` | 3곳 호출부 수정 | Frontend |
| `frontend/app/components/studio/ScenesTab.tsx` | 1곳 호출부 수정 | Frontend |
| `frontend/app/hooks/usePublishRender.ts` | 1곳 호출부 수정 | Frontend |
| `backend/services/tts_core.py` | 신규 (통합 래퍼) | Backend |
| `backend/services/tts_prebuild.py` | tts_core 경유로 전환 | Backend |
| `backend/services/preview_tts.py` | tts_core 경유로 전환 | Backend |
| `backend/services/bgm_prebuild.py` | total_duration 파라미터 추가 | Backend |
| `backend/routers/stage.py` | total_duration 전달 | Backend |
| `backend/schemas.py` | 2개 스키마 필드 추가 | Backend |
| `backend/tests/services/test_tts_core.py` | 신규 (단위 테스트) | Test |

**총 12개 파일** (신규 2, 수정 8, 테스트 신규 2) — 제약 10개 초과하나, 신규+테스트 제외 시 변경 8개.
