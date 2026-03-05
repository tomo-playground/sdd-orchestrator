# Video Pre-validation (비디오 사전 검증) — Phase 29

> 상태: Sub-Phase A 진행 중
> 시작일: 2026-03-05
> 선행: Phase 28 (Pipeline Resilience)

## 1. 배경 및 문제

- 현재 7단계 일괄 파이프라인(SETUP → PROCESS_SCENES → ... → ENCODE → UPLOAD)
- TTS 품질이나 프레임 레이아웃 문제를 **최종 영상 완성 후에만** 확인 가능
- 문제 발견 시 전체 재렌더링(2~5분) 필요
- 외부 서비스 조사(10개): 9/10이 씬별 TTS 미리듣기, 10/10이 씬별 비주얼 프리뷰 제공

## 2. Sub-Phase 구성

| Sub-Phase | 기능 | 의존성 | 상태 |
|-----------|------|--------|------|
| **A** | 씬별 TTS 미리듣기 (MVP) | 독립 | 진행 중 |
| **B** | 씬별 프레임 프리뷰 | 독립 (A와 병렬 가능) | 진행 중 |
| **C** | 타임라인 시각화 | A 완료 후 | 진행 중 |
| **D** | 통합 사전검증 리포트 | A+B+C 완료 후 | 진행 중 |

## 3. API 명세

### Sub-Phase A: TTS Preview

| Endpoint | Method | 설명 |
|----------|--------|------|
| `/api/v1/preview/tts` | POST | 개별 씬 TTS 프리뷰 |
| `/api/v1/preview/tts-batch` | POST | 일괄 TTS 프리뷰 |

**핵심 설계 — 캐시 키 동일성**:
- 프리뷰에서도 렌더링과 동일한 `tts_cache_key(text, preset_id, voice_design, language)` 사용
- 생성된 WAV → `TTS_CACHE_DIR/{cache_key}.wav` 저장
- 렌더링 시 100% 캐시 히트 → TTS 단계 < 1초

### Sub-Phase B: Frame Preview

| Endpoint | Method | 설명 |
|----------|--------|------|
| `/api/v1/preview/frame` | POST | 개별 씬 프레임 합성 (Pillow) |

### Sub-Phase C: Timeline

| Endpoint | Method | 설명 |
|----------|--------|------|
| `/api/v1/preview/timeline` | POST | 타임라인 듀레이션 데이터 |

### Sub-Phase D: Validation

| Endpoint | Method | 설명 |
|----------|--------|------|
| `/api/v1/preview/validate` | POST | 렌더링 전 사전 검증 |

## 4. 파일 맵

### 신규 (7개)

| 파일 | Phase | 설명 |
|------|-------|------|
| `backend/routers/preview.py` | A | 프리뷰 API 라우터 |
| `backend/services/preview.py` | A | 프리뷰 서비스 로직 |
| `frontend/app/hooks/useTTSPreview.ts` | A | TTS 프리뷰 Hook |
| `frontend/app/hooks/useFramePreview.ts` | B | 프레임 프리뷰 Hook |
| `frontend/app/components/studio/TimelineBar.tsx` | C | 타임라인 시각화 |
| `frontend/app/components/video/PreRenderReport.tsx` | D | 검증 리포트 UI |
| `backend/tests/test_preview_tts.py` | A | TTS 프리뷰 테스트 |

### 수정 (5개)

| 파일 | Phase | 변경 |
|------|-------|------|
| `backend/schemas.py` | A~D | Preview 스키마 12개 클래스 추가 |
| `backend/routers/__init__.py` | A | `preview_svc` 라우터 등록 |
| `frontend/app/types/index.ts` | A~D | TypeScript 타입 추가 |
| Studio 씬 카드 | A+B | 미리듣기/프레임 프리뷰 버튼 |
| `RenderSidePanel.tsx` | D | 사전 검증 버튼 |

## 5. 테스트 시나리오

### Sub-Phase A
1. 캐시 키 동일성 — 프리뷰와 렌더링이 같은 키 생성
2. 캐시 히트 시나리오 — 기존 캐시 반환
3. speaker → voice_preset 해석 정확성
4. 빈 스크립트 방어
5. 배치 부분 실패 응답 구조

### Sub-Phase B
1. Post 레이아웃 합성 이미지 크기 검증
2. Full 레이아웃 자막 위치/폰트 크기
3. 얼굴 감지 시 크롭 위치

### Sub-Phase C
1. 타임라인 기본 계산
2. 속도 배율 영향
3. TTS 듀레이션 반영

### Sub-Phase D
1. 이미지 없는 씬 → error
2. 빈 스크립트 → warning
3. 60초 초과 → warning
4. TTS 캐시 존재 확인

## 6. DoD (Definition of Done)

- [ ] Backend 5개 엔드포인트 동작 확인
- [ ] Frontend hooks + UI 통합
- [ ] TTS 캐시 키 동일성 검증 (프리뷰 → 렌더링 캐시 히트)
- [ ] 테스트 45개 이상 PASS
- [ ] 문서 업데이트 (ROADMAP + FEATURES)
