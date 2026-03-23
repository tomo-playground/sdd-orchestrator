# SP-065 Rendering Quality Hardening -- Design

## DoD 1: Ken Burns Fallback

### 1-1. resolve_preset_name()에서 무효 값 반환 시 emotion 기반 fallback

**구현 방법**

현재 `resolve_preset_name()` (motion.py:235)은 입력을 검증 없이 그대로 반환한다.
`"invalid_motion"`처럼 VALID_PRESET_NAMES에 없는 값도 통과시키며, `get_preset()`에서
`PRESETS["none"]`으로 조용히 폴백되어 모션 효과가 먹통이 된다.

변경: `resolve_preset_name()`에 `VALID_PRESET_NAMES` 검증을 추가하고,
무효 값이면 `"none"`을 반환한다 (함수 시그니처 유지).

실질적인 emotion 기반 fallback은 이미 `resolve_scene_preset()` (filters.py:229)과
`validate_ken_burns_presets()` (_finalize_validators.py:178)에 구현되어 있다.
`resolve_preset_name()`은 builder 초기화 시 global preset에만 사용되므로,
여기서 무효 값을 `"none"`으로 정리하면 하위 `resolve_scene_preset()`에서
emotion 기반 또는 random 배정이 자연스럽게 작동한다.

추가로, `resolve_scene_preset()`의 per-scene override(priority 1) 경로에서도
무효 preset을 검증한다. 현재 `per_scene`이 `"none"`이 아닌 아무 문자열이면
그대로 반환하는데, VALID_PRESET_NAMES에 없으면 emotion fallback으로 넘긴다.

**동작 정의**
- `resolve_preset_name("zoom_in_center")` -> `"zoom_in_center"` (변경 없음)
- `resolve_preset_name("invalid_foo")` -> `"none"` + warning 로그 (NEW)
- `resolve_preset_name("random")` -> `"random"` (변경 없음, random은 filters에서 해석)
- `resolve_scene_preset()`에서 per-scene이 VALID 아니면 -> 다음 priority로 이동

**엣지 케이스**
- `"random"`은 VALID_PRESET_NAMES에 포함되지 않지만, resolve_preset_name에서 특별히 통과시켜야 한다 (filters.py에서 해석)
- 빈 문자열(`""`)과 `None`은 기존대로 `"none"` 반환
- 대소문자 혼용 (`"Zoom_In_Center"`) -> 소문자 변환 후 검증

**영향 범위**
- `backend/services/motion.py` -- resolve_preset_name 수정
- `backend/services/video/filters.py` -- resolve_scene_preset의 per-scene 경로 검증 추가
- 기존 동작: 유효한 preset은 변경 없음. 무효 preset만 "none"으로 정리됨

**테스트 전략**
- `test_motion.py::TestResolvePresetName` 확장: 무효 문자열 -> "none" + warning
- `test_filters_ken_burns.py` 확장: per-scene 무효 preset -> global/random fallback
- 기존 테스트 모두 통과 확인 (regression 없음)

**Out of Scope**
- Finalize 노드의 `validate_ken_burns_presets`는 이미 동일 검증을 수행 중이므로 변경하지 않음
- EMOTION_MOTION_MAP 확장 (감정 매핑은 현재 충분)


---

## DoD 2: BGM Ducking 검증

### 2-1. ducking offset이 scene_durations 합계를 초과하면 클램프

**구현 방법**

현재 `_apply_ducked_bgm()` (effects.py:301)에서 `builder._total_dur`를 사용하여
`atrim=duration={builder._total_dur}`로 BGM을 잘라낸다. ducking 자체는 sidechain
compression으로 구현되어 별도 offset이 없다 (음성이 감지되면 자동으로 BGM 볼륨 감소).

실제 문제: `_total_dur`가 `scene_durations` 합계와 불일치할 수 있다.
`_estimate_total_duration()` (builder.py:262)에서 계산하지만, `apply_transitions()`에서
다시 계산하면서 clamping이 적용되면 값이 달라질 수 있다.

변경: `apply_bgm()` 진입 시 `builder._total_dur`가 0 이하이면 `scene_durations` 합계로
재계산하는 safety clamp를 추가한다. 또한 `atrim`과 `apad` 사이에 일관성을 보장한다.

**동작 정의**
- `_total_dur > 0`: 현재 값 그대로 사용 (정상 경로)
- `_total_dur <= 0`: `sum(scene_durations)` 으로 보정 + warning 로그
- BGM atrim duration은 항상 `_total_dur` 이하로 제한

**엣지 케이스**
- scene_durations가 빈 리스트 -> BGM 적용 자체를 건너뜀 (기존 동작)
- 단일 씬 영상 -> transition 없으므로 `_total_dur == scene_durations[0]`

**영향 범위**
- `backend/services/video/effects.py` -- `apply_bgm()` 진입부에 safety check 추가

**테스트 전략**
- `test_effects_ai_bgm.py` 확장: `_total_dur=0` 일 때 scene_durations 합계로 보정 확인
- atrim duration이 _total_dur와 일치하는지 filter string 검증

**Out of Scope**
- sidechain compression 파라미터 튜닝 (threshold, ratio 등)
- ducking이 "정확히 어느 타이밍에 작동하는가"는 FFmpeg sidechain 동작에 의존하므로 unit test 범위 외

### 2-2. BGM 길이가 전체 영상보다 짧으면 루핑 또는 fade-out 적용

**구현 방법**

이미 `_build_bgm_loop_filters()` (effects.py:254)에서 aloop 기반 루핑이 구현되어 있다.
BGM이 영상보다 짧으면 자동으로 aloop 필터가 추가된다.

확인 포인트:
1. aloop 이후 `atrim`으로 정확히 `_total_dur`만큼 자름 -> 구현됨 (line 306-309)
2. fade-out 2초 적용 -> 구현됨 (`afade=t=out:st={max(0, _total_dur - 2)}:d=2`)
3. `apad=whole_dur={_total_dur}` -> 루핑이 부족할 때 무음 패딩 -> 구현됨

결론: 이미 정상 구현되어 있다. 테스트로 확인만 추가한다.

**동작 정의**
- BGM 30s, 영상 45s -> aloop=1 (2배) + atrim=45s + fade-out 마지막 2초
- BGM 10s, 영상 45s -> aloop=4 (5배) + atrim=45s + fade-out
- BGM 60s, 영상 45s -> 루핑 없음 + atrim=45s + fade-out

**엣지 케이스**
- BGM 0s (ffprobe 실패) -> fallback 루프 3회 + apad로 안전
- BGM 영상보다 1초 이내 짧음 -> margin 내이므로 루핑 없음 (기존 동작)

**영향 범위**
- 코드 변경 없음 (기존 구현이 충분)
- 테스트만 추가

**테스트 전략**
- 기존 `test_effects_ai_bgm.py::TestBuildBgmLoopFilters` 테스트가 이미 커버
- 추가: fade-out이 filter string에 포함되는지 검증하는 테스트 (`_apply_ducked_bgm`, `_apply_simple_bgm`)

**Out of Scope**
- BGM crossfade 루핑 (aloop이 아닌 asplit+acrossfade 방식) -- 현재 aloop으로 충분


### 2-3. ducking 타이밍 정확도 테스트

**구현 방법**

ducking은 FFmpeg sidechain compression으로 구현되어 실시간으로 음성 감지 시 BGM을
자동 감소시킨다. "타이밍 정확도"를 unit test하는 것은 FFmpeg 실행 없이는 불가능하다.

대안: filter chain이 올바르게 구성되는지 검증한다.
- `asplit=2[narr_out][narr_key]` -- 나레이션 분기
- `sidechaincompress=threshold=...` -- 올바른 파라미터
- `amix=inputs=2` -- 최종 합성

**동작 정의**
- `audio_ducking=True`: 4개 filter (asplit, bgm_vol, sidechaincompress, amix) 생성
- `audio_ducking=False`: 2개 filter (bgm_vol, amix) 생성
- ducking threshold는 `builder.request.ducking_threshold` 값 사용

**테스트 전략**
- mock builder로 `_apply_ducked_bgm()` 호출 후 filter string 검증
- threshold 값이 filter에 정확히 반영되는지 확인
- `_apply_simple_bgm()`과 비교하여 filter 수 차이 검증


---

## DoD 3: Voice Pacing 적용 확인

### 3-1. head_padding / tail_padding 적용 경로 확인

**구현 방법**

코드 탐색 결과, pacing은 이미 적용되고 있다:

1. **Finalize 노드** (finalize.py:921-934): `tts_design.pacing.head_padding/tail_padding`을 scene dict로 분해
2. **DB 저장**: `Scene` 모델에 `head_padding`, `tail_padding` 컬럼 존재 (models/scene.py:49-50)
3. **VideoScene 스키마** (schemas.py:565-566): `head_padding: float = 0.0`, `tail_padding: float = 0.0`
4. **Duration 계산** (utils.py:155-162): `h_pad + tts_duration + t_pad + tts_padding` 공식에 반영
5. **Audio filter** (filters.py:276-277): `adelay = (transition_dur + h_pad) * 1000`ms로 오디오 시작 지연

**그러나 tail_padding이 audio filter에는 미적용**:
- `calculate_scene_durations()`에서 `t_pad`이 scene duration에 반영되어 영상 길이는 충분하지만,
- `build_audio_filters()` (filters.py:269-283)에서는 `h_pad`만 사용하고 `t_pad`는 직접 처리하지 않는다.
- tail_padding은 "TTS 끝나고 N초 후까지 씬을 유지"하는 효과인데, scene duration이 이미 충분히
  길어져 있으므로 자연스럽게 달성된다 (TTS가 끝나면 무음이 t_pad + tts_padding 만큼 이어짐).

결론: **tail_padding은 duration 확보 방식으로 간접 적용되어 있으며, 이것이 올바른 설계이다.**
adelay로 head를 지연시키고, duration을 충분히 확보하여 tail silence를 보장하는 구조.

**변경**: 코드 변경 없음. 경로 확인 결과를 테스트로 문서화한다.

**동작 정의**
- `head_padding=0.3`: TTS 오디오 시작이 0.3초 추가 지연 (transition_dur + 0.3)
- `tail_padding=0.5`: scene duration이 0.5초 추가 확보 -> TTS 후 무음 구간 확대
- 둘 다 0.0: 기존 동작 (tts_padding만 적용)

**엣지 케이스**
- head_padding/tail_padding이 None (DB 기본값) -> `or 0.0`으로 방어됨
- 매우 큰 padding (5.0초) -> scene duration이 그만큼 늘어남 (문제 없음)
- TTS 없는 씬 -> padding 무시 (기존 동작)

**영향 범위**
- 코드 변경 없음
- 테스트 추가로 경로 검증

**테스트 전략**
- `test_scene_durations_xfade.py` 기존 테스트가 이미 head/tail padding 커버
- 추가: `build_audio_filters()` 호출 후 adelay에 h_pad이 반영되는지 filter string 검증
- 추가: tail_padding이 있을 때 scene duration이 충분한지 종합 검증 (duration - adelay > tts + t_pad + tts_padding)

**Out of Scope**
- TTS 오디오 자체에 silence를 prepend/append하는 방식 (현재 FFmpeg filter 방식이 더 유연)
- pacing 값의 타당성 검증 (creative_qc.py에서 이미 수행)


---

## DoD 4: Transition Effect / Ken Burns Direction Conflict Prevention

### 4-1. resolve_scene_transition()에서 방향 충돌 감지 및 대체

**구현 방법**

`resolve_scene_transition()` (effects.py:24)이 전환 효과를 결정한 후,
해당 씬의 `ken_burns_preset`과 방향이 겹치는지 검증한다.

방향 충돌 매핑:
| Transition | Ken Burns | 충돌 이유 |
|------------|-----------|-----------|
| `slideleft` | `pan_left`, `zoom_pan_left` | 같은 왼쪽 이동 |
| `slideright` | `pan_right`, `zoom_pan_right` | 같은 오른쪽 이동 |
| `wipeleft` | `pan_left`, `zoom_pan_left` | 같은 왼쪽 방향 |
| `wiperight` | `pan_right`, `zoom_pan_right` | 같은 오른쪽 방향 |
| `slideup` | `pan_up`, `pan_up_vertical`, `pan_zoom_up` | 같은 위쪽 이동 |
| `slidedown` | `pan_down`, `pan_down_vertical`, `pan_zoom_down` | 같은 아래쪽 이동 |
| `wipeup` | `pan_up`, `pan_up_vertical`, `pan_zoom_up` | 같은 위쪽 방향 |
| `wipedown` | `pan_down`, `pan_down_vertical`, `pan_zoom_down` | 같은 아래쪽 방향 |

구현:
1. `DIRECTION_CONFLICT_MAP: dict[str, set[str]]`를 effects.py에 상수로 정의
2. `resolve_scene_transition()` 반환 전, 해당 씬의 ken_burns_preset과 대조
3. 충돌 시 `"fade"`로 대체 (가장 안전한 방향 무관 전환)
4. 충돌 대체 시 info 로그 기록

Ken Burns preset 참조 방법:
- `resolve_scene_transition()`은 `scene_idx`를 받으므로 `builder.request.scenes[scene_idx]`에서
  `ken_burns_preset`을 가져올 수 있다.
- 그런데 per-scene override가 아닌 global/random 경우 이 시점에서는 아직 실제 preset을
  모른다 (build_video_filters에서 결정됨). 따라서 충돌 검사는 per-scene override가 있는 경우에만
  수행하고, global/random은 건너뛴다 (이미 다양하게 배정되므로 확률적으로 충돌이 분산됨).

**동작 정의**
- per-scene `ken_burns_preset="pan_left"` + transition `"slideleft"` -> `"fade"`로 대체
- per-scene `ken_burns_preset="zoom_in_center"` + transition `"slideleft"` -> 충돌 아님, 유지
- per-scene `ken_burns_preset=None` (global) -> 충돌 검사 건너뜀
- `transition_type="fade"` -> 방향 없으므로 항상 안전

**엣지 케이스**
- `transition_type="auto"` 모드에서 location change -> slideleft/slideright 중 충돌 발생 가능 -> fade로 대체
- `transition_type="random"` 모드 -> random 결과가 충돌하면 대체
- scene_idx=0 (첫 씬) -> 전환 없음, 호출되지 않음 (apply_transitions는 i=1부터)

**영향 범위**
- `backend/services/video/effects.py` -- `resolve_scene_transition()` 수정 + 상수 추가
- 기존 동작: 충돌 없는 경우 변경 없음

**테스트 전략**
- 새 테스트: 충돌 케이스별 (slideleft+pan_left, slideright+pan_right 등) fade 대체 확인
- 새 테스트: 비충돌 케이스 (slideleft+pan_up) 유지 확인
- 새 테스트: per-scene override 없을 때 충돌 검사 건너뜀 확인

**Out of Scope**
- Ken Burns preset 자체를 전환 방향에 맞춰 변경하는 것 (전환이 양보하는 것이 더 안전)
- 수직 전환(slideup/slidedown)과 수직 Ken Burns(pan_up_vertical) 충돌 -- 포함함 (수직도 방향 겹침)


---

## DoD 5: 통합

### 5-1. 기존 테스트 regression 없음

**구현 방법**
- 모든 변경 후 `pytest backend/tests/ -x --timeout=30` 실행
- 특히 `test_motion.py`, `test_filters_ken_burns.py`, `test_effects_ai_bgm.py`,
  `test_scene_durations_xfade.py` 전체 통과 확인

### 5-2. 린트 통과

**구현 방법**
- `ruff check backend/` + `ruff format backend/` 실행
- PostToolUse hook이 자동 린트하므로 별도 작업 불필요


---

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| `backend/services/motion.py` | `resolve_preset_name()` 무효값 검증 추가 |
| `backend/services/video/filters.py` | `resolve_scene_preset()` per-scene 무효 검증 |
| `backend/services/video/effects.py` | `apply_bgm()` safety clamp + `resolve_scene_transition()` 방향 충돌 검사 + `DIRECTION_CONFLICT_MAP` 상수 |
| `backend/tests/test_motion.py` | 무효 preset fallback 테스트 |
| `backend/tests/test_effects_bgm_ducking.py` | (NEW) ducking filter chain + fade-out + safety clamp 테스트 |
| `backend/tests/test_transition_conflict.py` | (NEW) 방향 충돌 감지/대체 테스트 |

**총 변경 파일: 6개** (제약 조건 충족)


---

## 소크라테스식 확인 질문

1. `resolve_preset_name()`에서 `"random"`을 특별 취급(통과)해야 하는데, 이를 `VALID_PRESET_NAMES | {"random"}`으로 처리하는 것이 맞는지, 아니면 별도 분기가 나은지?
   -> **제안: 별도 분기.** `"random"`은 meta-value이지 실제 preset이 아니므로 `if ken_burns_preset == "random": return "random"` 후 VALID 검증.

2. 전환-Ken Burns 충돌 시 fade 대신 "반대 방향 전환"으로 바꾸는 것이 더 나은지?
   (예: slideleft+pan_left -> slideright)
   -> **제안: fade.** 반대 방향도 시각적으로 부자연스러울 수 있고, fade가 가장 무난.

3. tail_padding이 "코드 변경 없이 이미 동작한다"는 결론이 맞는지 한번 더 확인 필요 -- duration 확보 방식이 실제로 무음 구간을 만드는지?
   -> 테스트에서 `clip_dur - adelay - tts_duration >= t_pad + tts_padding` 부등식으로 검증.
