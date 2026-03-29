---
id: SP-119
priority: P1
scope: backend+audio
branch: feat/SP-119-tts-quality-optimization
created: 2026-03-29
status: done
approved_at: 2026-03-29
depends_on:
label: enhancement
---

## 상세 설계 (How)

> [design.md](./design.md) 참조 (설계 승인 후 작성)

## 무엇을 (What)
Qwen3-TTS 파이프라인의 음성 품질 최적화 — truncation 방지, 후처리 임계값 조정, 토큰 예산 재보정.

## 왜 (Why)
1. **TTS Truncation**: 긴 voice design instruct 시 음성이 잘리는 알려진 이슈 (2026-03-16 발견)
2. **쇼츠 템포**: 800ms 내부 침묵 허용이 쇼츠 포맷에 과다
3. **NATURALNESS_SUFFIX**: 90자가 매 호출마다 추가되어 토큰 예산 소비, 효과 미검증
4. **정규화 레벨**: -23dBFS가 BGM 믹싱 시 음성이 묻힐 수 있음

## 근본 원인 분석

### C1. TTS_NATURALNESS_SUFFIX 토큰 낭비
- **위치**: `backend/config.py:915-918`, `backend/services/audio_client.py:100-101`
- **현상**: 90자 suffix가 모든 instruct에 추가 → voice design(30~80자) + suffix(90자) = 120~170자
- **영향**: instruct 토큰이 audio 토큰 예산 잠식 → 긴 텍스트에서 truncation

### C2. TTS_MIN_SECS_PER_CHAR 과도하게 관대
- **위치**: `backend/config.py:938-940`
- **현상**: 0.05초/자 = 20자/초 → 한국어 정상 속도(12~15자/초)보다 훨씬 빠른 기준
- **영향**: truncation이 발생해도 quality_passed=True 오판

### C3. 내부 침묵 허용 과다
- **위치**: `audio/config.py:31` — `TTS_SILENCE_MAX_MS=800`
- **현상**: TTS 내부 무음 800ms까지 허용
- **영향**: 쇼츠 씬당 불필요한 침묵 추가

### C4. 정규화 타겟이 낮음
- **위치**: `audio/services/tts_postprocess.py:127` — target_dbfs=-23.0
- **현상**: 라디오/팟캐스트 기준(-23dBFS)으로 설정
- **영향**: BGM(-18dB)과 믹싱 시 음성이 상대적으로 작게 들림

### C5. 토큰 예산 계산 부정확
- **위치**: `backend/services/video/tts_helpers.py:250-261`
- **현상**: `len(text) * 30` 고정 factor, instruct `// 4` 보정
- **영향**: 한글 토크나이저 실제 비율과 괴리

## 완료 기준 (DoD)

### Must (P0)
- [ ] `TTS_NATURALNESS_SUFFIX` 20자 이하로 축약 또는 조건부 적용 (voice design 있으면 스킵)
- [ ] `TTS_MIN_SECS_PER_CHAR` 상향: 0.05 → 0.065 (15자/초 기준)
- [ ] `TTS_SILENCE_MAX_MS` 하향: 800 → 400 (쇼츠 템포 적합)
- [ ] `TTS_MAX_NEW_TOKENS_CAP` 상향: 2048 → 3072 (truncation 방지)

### Should (P1)
- [ ] 정규화 타겟 상향: -23dBFS → -20dBFS (BGM 믹싱 밸런스)
- [ ] 토큰 예산 factor 재보정: PER_CHAR 30 → 40
- [ ] `_check_truncation()` 짧은 텍스트(<5자) 최소 0.3초 별도 보장

### Could (P2)
- [ ] Top_P 0.8 → 0.85 A/B 테스트
- [ ] Hallucination detection threshold 실측 데이터 기반 재보정
- [ ] Voice design이 있을 때 suffix 자동 스킵 로직

## 참조
- `audio/config.py` — TTS 서버 설정
- `audio/services/tts_postprocess.py` — 6단계 후처리 파이프라인
- `backend/config.py:900-951` — TTS 백엔드 설정
- `backend/services/video/tts_helpers.py` — TTS 생성 코어
- `backend/services/audio_client.py` — 오디오 서버 클라이언트

## 힌트
- P0은 순수 상수 변경 + 조건문 1개 — 사이드이펙트 최소
- NATURALNESS_SUFFIX 축약은 기존 TTS 캐시 키에 포함되므로 캐시 자동 무효화됨
- 정규화 타겟 변경 시 기존 캐시된 오디오와 새 오디오 간 볼륨 차이 발생 가능
- MAX_NEW_TOKENS_CAP 상향은 VRAM 사용량 증가 없음 (토큰 수만 증가)
