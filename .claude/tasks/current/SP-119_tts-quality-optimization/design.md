# SP-119 상세 설계: Qwen3-TTS 품질 최적화

## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `backend/config.py` | 상수 5개 변경 |
| `backend/services/audio_client.py` | suffix 조건부 스킵 (1줄) |
| `audio/config.py` | 상수 1개 변경 |
| `audio/services/tts_postprocess.py` | 정규화 기본값 변경 |

---

## P0: Must

### DoD 1: TTS_NATURALNESS_SUFFIX 축약 + 조건부 적용

#### 구현 방법
- `backend/config.py:915-918`: suffix 20자 이하로 축약
- `backend/services/audio_client.py:100-101`: voice design이 있으면 suffix 스킵

#### 동작 정의
```python
# before (config.py)
TTS_NATURALNESS_SUFFIX = "with natural, human-like speech rhythm, varied intonation, and a slightly fast conversational pace"  # 90자

# after
TTS_NATURALNESS_SUFFIX = "natural conversational tone"  # 26자

# before (audio_client.py)
if TTS_NATURALNESS_SUFFIX:
    instruct = f"{instruct}, {TTS_NATURALNESS_SUFFIX}" if instruct else TTS_NATURALNESS_SUFFIX

# after — voice_design이 이미 있으면 suffix 스킵 (토큰 절약)
if TTS_NATURALNESS_SUFFIX and not instruct:
    instruct = TTS_NATURALNESS_SUFFIX
```

#### 엣지 케이스
- instruct가 빈 문자열("")인 경우 → suffix 적용 (기존 동작 유지)
- instruct가 None인 경우 → suffix 적용

#### 영향 범위
- TTS 캐시 키에 suffix가 포함되므로 캐시 자동 무효화
- voice_design 있는 캐릭터: suffix 미적용으로 토큰 절약 → truncation 감소

#### 테스트 전략
- instruct 없을 때 suffix 적용 확인
- instruct 있을 때 suffix 미적용 확인

#### Out of Scope
- 캐시 수동 클리어

---

### DoD 2: TTS_MIN_SECS_PER_CHAR 상향

#### 구현 방법
- `backend/config.py:938-940`: 0.05 → 0.065

#### 동작 정의
```python
# before
TTS_MIN_SECS_PER_CHAR = 0.05  # 20자/sec

# after
TTS_MIN_SECS_PER_CHAR = 0.065  # ~15자/sec (한국어 정상 속도)
```

#### 영향 범위
- truncation 감지가 더 엄격해짐 → 잘린 음성을 재시도할 확률 증가
- 정상 음성이 오탐될 가능성 낮음 (15자/sec는 빠른 편)

---

### DoD 3: TTS_SILENCE_MAX_MS 하향

#### 구현 방법
- `audio/config.py:31`: 800 → 400

#### 동작 정의
```python
# before
TTS_SILENCE_MAX_MS = 800  # 0.8초 침묵 허용

# after
TTS_SILENCE_MAX_MS = 400  # 0.4초 침묵 허용 (쇼츠 템포)
```

#### 영향 범위
- 후처리에서 400ms 초과 침묵이 압축됨
- 기존 캐시된 오디오에는 영향 없음 (새 생성분부터 적용)

---

### DoD 4: TTS_MAX_NEW_TOKENS_CAP 상향

#### 구현 방법
- `backend/config.py:933`: 2048 → 3072

#### 동작 정의
```python
# before
TTS_MAX_NEW_TOKENS_CAP = 2048

# after
TTS_MAX_NEW_TOKENS_CAP = 3072
```

#### 영향 범위
- VRAM 증가 없음 (토큰 수 제한만, 모델 크기 동일)
- 긴 텍스트에서 truncation 방지

---

## P1: Should

### DoD 5: 정규화 타겟 상향

#### 구현 방법
- `audio/services/tts_postprocess.py:127`: 기본값 -23.0 → -20.0

#### 동작 정의
```python
# before
def normalize_audio(wav, target_dbfs: float = -23.0, ...) -> np.ndarray:

# after
def normalize_audio(wav, target_dbfs: float = -20.0, ...) -> np.ndarray:
```

#### 영향 범위
- 새로 생성되는 TTS가 3dB 더 크게 정규화
- 기존 캐시 오디오와 볼륨 차이 발생 가능

---

### DoD 6: 토큰 예산 factor 재보정

#### 구현 방법
- `backend/config.py:932`: PER_CHAR 30 → 40

#### 동작 정의
```python
# before
TTS_MAX_NEW_TOKENS_PER_CHAR = 30

# after
TTS_MAX_NEW_TOKENS_PER_CHAR = 40
```

#### 영향 범위
- _calculate_max_new_tokens() 결과 증가 → 토큰 여유 확보
- CAP(3072)으로 상한 제한되므로 무한 증가 없음

---

### DoD 7: 짧은 텍스트 최소 보장

#### 구현 방법
- `backend/services/video/tts_helpers.py`의 `_check_truncation()` 또는 호출부에서 짧은 텍스트(<5자) 최소 0.3초 보장

#### 테스트 전략
- 2자 텍스트("응!") → 최소 0.3초 보장 확인

---

## Out of Scope (전체)
- Top_P A/B 테스트 (P2)
- Hallucination detection 재보정 (P2)
- 오디오 서버(audio/) 아키텍처 변경
- TTS 캐시 수동 클리어
