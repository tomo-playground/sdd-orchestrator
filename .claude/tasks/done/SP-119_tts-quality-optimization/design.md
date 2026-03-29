# SP-119 상세 설계: Qwen3-TTS 품질 최적화

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|----------|------|
| `backend/config.py` | 상수 수정 | NATURALNESS_SUFFIX 축약, MIN_SECS_PER_CHAR 상향, MAX_NEW_TOKENS_CAP/PER_CHAR 상향 |
| `audio/config.py` | 상수 수정 | TTS_SILENCE_MAX_MS 하향 |
| `backend/services/audio_client.py` | 로직 수정 | suffix 조건부 적용 (instruct 있으면 스킵) |
| `audio/services/tts_postprocess.py` | 상수 수정 | normalize target_dbfs 상향 |
| `backend/services/video/tts_helpers.py` | 로직 수정 | _check_truncation 짧은 텍스트 하한 추가 |
| `backend/tests/test_audio_client.py` | 테스트 수정 | suffix 조건부 적용 반영 |

---

## P0: Must

### M1. `TTS_NATURALNESS_SUFFIX` 축약 + 조건부 적용

**구현 방법**

1. `backend/config.py:915-918` — suffix 축약
   ```python
   # Before (90자)
   "with natural, human-like speech rhythm, varied intonation, and a slightly fast conversational pace"
   # After (18자)
   "natural speech pace"
   ```

2. `backend/services/audio_client.py:100-101` — instruct 있으면 suffix 스킵
   ```python
   # Before
   if TTS_NATURALNESS_SUFFIX:
       instruct = f"{instruct}, {TTS_NATURALNESS_SUFFIX}" if instruct else TTS_NATURALNESS_SUFFIX
   # After
   if TTS_NATURALNESS_SUFFIX and not instruct:
       instruct = TTS_NATURALNESS_SUFFIX
   ```

**동작 정의**
- Before: voice design "A calm female voice" → "A calm female voice, with natural, human-like..." (172자)
- After: voice design "A calm female voice" → "A calm female voice" (그대로). instruct 없을 때만 "natural speech pace" 적용

**엣지 케이스**
- instruct="" (voice design 없음): suffix만 적용 → fallback 보호 유지
- instruct=None: Python falsy → suffix 적용

**영향 범위**
- `tts_cache_key()`에 `TTS_NATURALNESS_SUFFIX` 포함 → suffix 값 변경으로 기존 캐시 자동 무효화
- 모든 TTS 호출 경로 (`synthesize_tts`, `synthesize_voice_design`) 통과

**테스트 전략**
- `test_audio_client.py::test_naturalness_suffix_appended` → instruct 있을 때 suffix 미추가 검증으로 변경
- `test_audio_client.py::test_naturalness_suffix_alone_when_no_instruct` → 기존 동작 유지 검증

**Out of Scope**: voice design 프롬프트 자체의 품질 개선

---

### M2. `TTS_MIN_SECS_PER_CHAR` 상향: 0.05 → 0.065

**구현 방법**
- `backend/config.py:938-940` — 기본값 변경 + 주석 갱신
  ```python
  TTS_MIN_SECS_PER_CHAR = float(
      os.getenv("TTS_MIN_SECS_PER_CHAR", "0.065")
  )  # Truncation guard (0.065s/char ≈ 15자/sec, 한국어 내레이션 표준)
  ```

**동작 정의**
- Before: 20자 텍스트 → 최소 1.0초 (20자/초). truncation 판정이 관대
- After: 20자 텍스트 → 최소 1.3초 (15자/초). 잘린 음성을 더 잘 잡아냄

**엣지 케이스**
- 짧은 텍스트(3자): `3 * 0.065 = 0.195초` → `_calculate_min_duration()`의 0.4초 하한에 걸려 무관
- 14자(정보 씬): `14 * 0.065 = 0.91초` → 정상 TTS는 2초+ 이므로 오탐 없음

**영향 범위**: `_check_truncation()` — 유일 참조처. quality_passed=True인데 짧으면 재시도

**테스트 전략**
- `_check_truncation(True, 0.8, "열두글자텍스트입니다")` → True (truncated)
- `_check_truncation(True, 2.0, "열두글자텍스트입니다")` → False (정상)

**Out of Scope**: `_calculate_min_duration()` 수정

---

### M3. `TTS_SILENCE_MAX_MS` 하향: 800 → 400

**구현 방법**
- `audio/config.py:31`
  ```python
  TTS_SILENCE_MAX_MS = int(os.getenv("TTS_SILENCE_MAX_MS", "400"))
  ```

**동작 정의**
- Before: TTS 내부 800ms 이하 침묵 유지
- After: 400ms 초과 침묵을 400ms로 압축

**엣지 케이스**
- 쉼표/마침표 후 자연 pause(200~300ms): 400ms 이하 → 유지
- 긴 침묵(1초+): 400ms로 압축

**영향 범위**: `_compress_internal_silence()` — 유일 참조. 오디오 서버 재시작 필요

**테스트 전략**: 오디오 서버 단위 — 1초 침묵 WAV → 후처리 후 400ms 압축 확인

**Out of Scope**: trim_top_db, fade_ms 변경

---

### M4. `TTS_MAX_NEW_TOKENS_CAP` 상향: 2048 → 3072

**구현 방법**
- `backend/config.py:933`
  ```python
  TTS_MAX_NEW_TOKENS_CAP = int(os.getenv("TTS_MAX_NEW_TOKENS_CAP", "3072"))
  ```

**동작 정의**
- Before: 동적 계산 max = 2048. 긴 텍스트+instruct → cap에 걸려 truncation
- After: cap 3072. 50자+200자 instruct = `50*30 + 200/4 = 1550` → 여유

**엣지 케이스**
- 극단적 긴 텍스트(100자): `100*30 + 50/4 = 3012` → cap 근접하지만 여유
- VRAM 영향 없음: max_new_tokens는 생성 토큰 수 상한, 모델 크기 동일

**영향 범위**: `_calculate_max_new_tokens()` — min(..., CAP) 상한

**테스트 전략**
- `_calculate_max_new_tokens("a"*100, "b"*200)` → 3050 (cap 미달)
- `_calculate_max_new_tokens("a"*120, "b"*200)` → 3072 (cap 적용)

**Out of Scope**: BASE(1024) 변경

---

## P1: Should

### S1. 정규화 타겟 상향: -23dBFS → -20dBFS

**구현 방법**
- `audio/services/tts_postprocess.py:127` — 기본값 변경
  ```python
  def normalize_audio(wav, target_dbfs: float = -20.0, peak_limit_db: float = -1.0):
  ```

**동작 정의**
- 3dB 상향 ≈ 체감 볼륨 1.4배. BGM 대비 음성 prominence 확보

**엣지 케이스**: peak_limit_db=-1dB 유지 → 클리핑 방지

**영향 범위**: 새 생성분부터 적용. 기존 캐시 오디오와 볼륨 차이 가능

**Out of Scope**: BGM 볼륨/ducking 조정

---

### S2. 토큰 예산 factor 재보정: PER_CHAR 30 → 40

**구현 방법**
- `backend/config.py:932`
  ```python
  TTS_MAX_NEW_TOKENS_PER_CHAR = int(os.getenv("TTS_MAX_NEW_TOKENS_PER_CHAR", "40"))
  ```

**동작 정의**: 20자 → `800` 토큰 (기존 600). M4(cap 3072)와 결합하여 여유 확보

**엣지 케이스**: 짧은 텍스트(5자) → `200` → `max(200, 1024) = 1024` (BASE 하한)

**Out of Scope**: instruct_overhead 계산식(`// 4`) 변경

---

### S3. `_check_truncation()` 짧은 텍스트 최소 0.3초 보장

**구현 방법**
- `backend/services/video/tts_helpers.py:553`
  ```python
  # Before
  min_expected = len(cleaned) * TTS_MIN_SECS_PER_CHAR
  # After
  min_expected = max(len(cleaned) * TTS_MIN_SECS_PER_CHAR, 0.3)
  ```

**동작 정의**
- 3자 텍스트: `max(0.195, 0.3) = 0.3초` 최소 → 극단적으로 짧은 TTS 감지

**테스트 전략**
- `_check_truncation(True, 0.2, "네")` → True (잘림)
- `_check_truncation(True, 0.4, "네")` → False (정상)

**Out of Scope**: `_calculate_min_duration()` 수정

---

## 변경 요약

```
backend/config.py:
  TTS_NATURALNESS_SUFFIX          90자 → 18자 ("natural speech pace")
  TTS_MIN_SECS_PER_CHAR           0.05 → 0.065
  TTS_MAX_NEW_TOKENS_CAP          2048 → 3072
  TTS_MAX_NEW_TOKENS_PER_CHAR     30 → 40                    [P1]

audio/config.py:
  TTS_SILENCE_MAX_MS              800 → 400

backend/services/audio_client.py:
  synthesize_voice_design()       suffix 무조건 추가 → instruct 없을 때만

audio/services/tts_postprocess.py:
  normalize_audio()               target_dbfs -23.0 → -20.0  [P1]

backend/services/video/tts_helpers.py:
  _check_truncation()             min_expected 하한 0.3초     [P1]

backend/tests/test_audio_client.py:
  test_naturalness_suffix_appended  → suffix 미추가 검증으로 변경
```

## Out of Scope (전체)
- Top_P A/B 테스트 (P2)
- Hallucination detection 재보정 (P2)
- Voice design 프롬프트 품질 개선
- 오디오 서버 아키텍처 변경
- TTS 캐시 수동 클리어
