# SP-106 상세 설계: Shorts Tempo Tuning

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `backend/config.py` | 상수 수정 + 추가 | READING_SPEED, 패딩, 씬 듀레이션 + speed_params 상수 승격 |
| `backend/services/video/utils.py` | 로직 수정 | `calculate_speed_params()`가 config 상수 참조 |
| `backend/services/storyboard/helpers.py` | 하한값 수정 | `estimate_reading_duration()` 최소값 2.0 → 1.5 |
| `backend/tests/test_storyboard_parsing.py` | 테스트 수정 | `TestCalculateMinScenes` 기대값 갱신 |

---

## DoD 항목별 설계

### M1. `READING_SPEED["korean"]["cps"]` 상향: 4.0 → 6.0

**구현 방법**
- 파일: `backend/config.py:1032`
- `"korean": {"cps": 4.0, "unit": "chars"}` → `"korean": {"cps": 6.0, "unit": "chars"}`

**동작 정의**
- Before: 12자 한국어 → `12/4.0 + 0.5 = 3.5초`
- After: 12자 한국어 → `12/6.0 + 0.2 = 2.2초` (M2 패딩 변경 포함)

**엣지 케이스**
- 짧은 텍스트(4자): `4/6.0 + 0.2 = 0.87초` → `estimate_reading_duration()`의 `max(1.5, ...)` 하한에 걸림 (M5 연동)

**영향 범위**
- `estimate_reading_duration()` → Agent revise 노드의 씬 듀레이션 추정 → 씬 배분에 영향
- Frontend presets API (`/api/v1/presets`)에 READING_SPEED를 그대로 내려보내므로 Frontend 표시도 자동 반영

**테스트 전략**
- `estimate_reading_duration("테스트입니다열두자", "korean")` → 기대값 검증

**Out of Scope**: 일본어/영어 속도 변경은 P1(Should)

---

### M2. `READING_DURATION_PADDING` 하향: 0.5 → 0.2

**구현 방법**
- 파일: `backend/config.py:1036`
- `READING_DURATION_PADDING = 0.5` → `READING_DURATION_PADDING = 0.2`

**동작 정의**
- Before: 매 씬마다 0.5초 호흡 여백
- After: 매 씬마다 0.2초 호흡 여백 (10씬 기준 3초 절약)

**엣지 케이스**: 없음 — 단순 상수 변경

**영향 범위**: `estimate_reading_duration()` 결과값 하향 → 씬 듀레이션 감소

**테스트 전략**: M1과 통합 테스트

**Out of Scope**: 없음

---

### M3. `tts_padding` 기본값 하향: 0.8 → 0.4

**구현 방법**
- 파일: `backend/config.py` — 새 상수 추가
  ```python
  # --- Speed/Pacing Parameters (SSOT for calculate_speed_params) ---
  SPEED_TRANSITION_DUR_BASE = 0.3   # base transition duration (seconds)
  SPEED_TTS_PADDING_BASE = 0.4      # base TTS padding after speech (seconds)
  ```
- 파일: `backend/services/video/utils.py:108-123` — `calculate_speed_params()`가 config 상수 참조
  ```python
  def calculate_speed_params(speed_multiplier: float) -> tuple[float, float, float]:
      from config import SPEED_TRANSITION_DUR_BASE, SPEED_TTS_PADDING_BASE
      clamped = max(0.25, min(speed_multiplier or 1.0, 2.0))
      transition_dur = max(0.1, SPEED_TRANSITION_DUR_BASE / clamped)
      tts_padding = SPEED_TTS_PADDING_BASE / clamped
      return transition_dur, tts_padding, clamped
  ```

**동작 정의**
- Before (speed=1.0): `transition_dur=0.5, tts_padding=0.8`
- After (speed=1.0): `transition_dur=0.3, tts_padding=0.4`

**엣지 케이스**
- speed=0.25 (최저): `transition_dur=1.2, tts_padding=1.6` — 여전히 합리적
- speed=2.0 (최고): `transition_dur=0.15, tts_padding=0.2` — 최소 0.1 하한 적용됨

**영향 범위**
- `calculate_speed_params()` 호출처: `preview_validate.py`, `video/builder.py`, `video/__init__.py`
- 모든 렌더링의 패딩/트랜지션 시간이 줄어듦

**테스트 전략**
- `calculate_speed_params(1.0)` → `(0.3, 0.4, 1.0)` 검증
- `calculate_speed_params(2.0)` → `(0.15, 0.2, 2.0)` 검증
- `calculate_speed_params(0.25)` → `(1.2, 1.6, 0.25)` 검증

**Out of Scope**: speed_multiplier 기본값 변경 (P2)

---

### M4. `SCENE_DURATION_RANGE` 조정: (2.0, 3.5) → (1.5, 2.5)

**구현 방법**
- 파일: `backend/config.py:1007`
- `SCENE_DURATION_RANGE = (2.0, 3.5)` → `SCENE_DURATION_RANGE = (1.5, 2.5)`

**동작 정의**
- `calculate_min_scenes()` 변경: `ceil(duration / 2.5)` (was `ceil(duration / 3.5)`)
  - 15초: 5 → 6
  - 30초: 9 → 12
  - 45초: 13 → 18
  - 60초: 18 → 24

**엣지 케이스**: 없음 — `calculate_max_scenes()`는 `duration / 2`로 SCENE_DURATION_RANGE를 사용하지 않아 영향 없음

**영향 범위**
- `calculate_min_scenes()` — Agent가 생성하는 최소 씬 수 증가
- `trim_scenes_to_duration()` — max_scenes는 미변경

**테스트 수정 필요**
- `test_storyboard_parsing.py::TestCalculateMinScenes` — 4개 테스트 기대값 갱신:
  - `test_15s_min_5_scenes` → `test_15s_min_6_scenes` (5→6)
  - `test_30s_min_9_scenes` → `test_30s_min_12_scenes` (9→12)
  - `test_45s_min_13_scenes` → `test_45s_min_18_scenes` (13→18)
  - `test_60s_min_18_scenes` → `test_60s_min_24_scenes` (18→24)

**Out of Scope**: `calculate_max_scenes()` 수정

---

### M5. `SCENE_DEFAULT_DURATION` 하향: 3.0 → 2.0

**구현 방법**
- 파일: `backend/config.py:1008`
- `SCENE_DEFAULT_DURATION = 3.0` → `SCENE_DEFAULT_DURATION = 2.0`

**동작 정의**
- revise 노드에서 invalid scene의 fallback duration이 2.0초로 단축

**엣지 케이스**: 없음

**영향 범위**
- `services/agent/nodes/revise.py:67` — 이미 config 상수 참조 중이므로 자동 반영

**추가 수정**: `estimate_reading_duration()` 최소 하한
- 파일: `backend/services/storyboard/helpers.py:94`
- `max(2.0, min(...))` → `max(1.5, min(...))`
- 이유: SCENE_DURATION_RANGE 하한이 1.5이므로 동기화

**테스트 전략**: revise 노드의 fallback 동작은 기존 테스트 커버리지로 충분

**Out of Scope**: 없음

---

### M6. 기존 영상 재렌더링 체감 확인

**구현 방법**: 수동 검증 — 기존 스토리보드를 재렌더링하여 체감 비교

**테스트 전략**: 자동 테스트 불가. DoD에서 제외하고 수동 검증으로 대체.

**Out of Scope**: 자동화된 템포 벤치마크

---

## P1 (Should) 항목

### S1. `transition_dur` 기본값 하향: 0.5 → 0.3

M3에서 `SPEED_TRANSITION_DUR_BASE = 0.3`으로 이미 포함. M3와 동시 해결.

### S2. 일본어 읽기 속도: 5.0 → 7.0

- 파일: `backend/config.py:1033`
- `"japanese": {"cps": 5.0, "unit": "chars"}` → `"japanese": {"cps": 7.0, "unit": "chars"}`

### S3. 영어 읽기 속도: 2.5 → 3.0

- 파일: `backend/config.py:1034`
- `"english": {"wps": 2.5, "unit": "words"}` → `"english": {"wps": 3.0, "unit": "words"}`

---

## 변경 요약

```
config.py:
  SCENE_DURATION_RANGE        (2.0, 3.5) → (1.5, 2.5)
  SCENE_DEFAULT_DURATION      3.0 → 2.0
  READING_SPEED.korean.cps    4.0 → 6.0
  READING_SPEED.japanese.cps  5.0 → 7.0        [P1]
  READING_SPEED.english.wps   2.5 → 3.0        [P1]
  READING_DURATION_PADDING    0.5 → 0.2
  + SPEED_TRANSITION_DUR_BASE = 0.3             [신규]
  + SPEED_TTS_PADDING_BASE    = 0.4             [신규]

services/video/utils.py:
  calculate_speed_params()    하드코딩 0.5/0.8 → config 상수 참조

services/storyboard/helpers.py:
  estimate_reading_duration() max(2.0, ...) → max(1.5, ...)

tests/test_storyboard_parsing.py:
  TestCalculateMinScenes      기대값 4개 갱신
```
