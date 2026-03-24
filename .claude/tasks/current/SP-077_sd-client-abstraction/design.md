# SP-077 상세 설계: SD Client 추상화

> 작성: 2026-03-24 | 상태: design

## 현황 분석

### SD WebUI 직접 호출 지점 (서비스/라우터 — 전환 대상)

| # | 파일 | 호출 유형 | 설명 |
|---|------|----------|------|
| 1 | `services/generation.py:241` | `httpx.post(SD_TXT2IMG_URL)` | 씬 이미지 생성 (핵심) |
| 2 | `services/image_generation_core.py:42` | `httpx.get(options)` | 체크포인트 확인 |
| 3 | `services/image_generation_core.py:55` | `httpx.post(options)` | 체크포인트 전환 |
| 4 | `services/image_generation_core.py:219` | `httpx.post(SD_TXT2IMG_URL)` | Lab+Studio 통합 생성 |
| 5 | `services/controlnet.py:186` | `requests.get(controlnet/*)` | ControlNet 가용성 체크 |
| 6 | `services/controlnet.py:197` | `requests.get(controlnet/model_list)` | ControlNet 모델 목록 |
| 7 | `services/controlnet.py:369` | `requests.post(txt2img)` | ControlNet 이미지 생성 |
| 8 | `services/controlnet.py:393` | `requests.post(controlnet/detect)` | OpenPose 감지 |
| 9 | `services/controlnet.py:848` | `httpx.post(SD_TXT2IMG_URL)` | 레퍼런스 이미지 생성 |
| 10 | `services/avatar.py:123` | `httpx.post(SD_TXT2IMG_URL)` | 아바타 생성 |
| 11 | `services/sd_progress_poller.py:25` | `httpx.get(progress)` | 생성 진행률 폴링 |
| 12 | `routers/sd_models.py:190` | `httpx.get(SD_MODELS_URL)` | SD 모델 목록 |
| 13 | `routers/sd_models.py:205` | `httpx.get(SD_OPTIONS_URL)` | SD 옵션 조회 |
| 14 | `routers/sd_models.py:223` | `httpx.post(SD_OPTIONS_URL)` | SD 옵션 변경 |
| 15 | `routers/sd_models.py:241` | `httpx.get(SD_LORAS_URL)` | SD LoRA 목록 |

### 스크립트 파일 (범위 외)

7개 스크립트(`scripts/`)는 실험/유틸 용도이므로 전환하지 않는다.

### 호출 패턴 분류

**A. txt2img** — #1, #4, #7, #9, #10: payload dict -> images + info + seed
**B. Options CRUD** — #2, #3, #12, #13, #14: 체크포인트 조회/전환/모델 목록
**C. ControlNet Extension** — #5, #6, #8: 가용성/모델/감지
**D. Progress Polling** — #11: 진행률
**E. LoRA 목록** — #15: SD WebUI LoRA 목록

---

## 설계

### DoD-1: `services/sd_client/__init__.py` — SDClientBase ABC 정의

**구현 방법:**
- `SDClientBase` ABC에 9개 추상 메서드 정의 (패턴 A~E 매핑):
  - `async txt2img(payload, timeout?) -> SDTxt2ImgResult`
  - `async get_options() -> dict`
  - `async set_options(options, timeout?) -> dict`
  - `async get_models() -> list[dict]`
  - `async get_loras() -> list[dict]`
  - `async get_progress() -> SDProgressResult`
  - `async controlnet_detect(payload) -> dict`
  - `async check_controlnet() -> bool`
  - `async get_controlnet_models() -> list[str]`
- `services/sd_client/types.py`에 결과 타입:
  - `SDTxt2ImgResult`: image, images, info, seed
  - `SDProgressResult`: progress, textinfo, current_image

**동작 정의:** ABC라 직접 인스턴스화 불가. ForgeClient/ComfyUIClient가 구현.

**엣지 케이스:**
- `controlnet_detect`는 ComfyUI에서 다른 방식이므로 기본 `NotImplementedError` 가능

**영향 범위:** 신규 파일 — 기존 코드 무영향

**테스트 전략:**
- ABC 인스턴스화 시 `TypeError` 확인
- 추상 메서드 9개 목록 확인
- 타입 클래스 필드 검증

**Out of Scope:** ComfyUIClient (SP-022), img2img (현재 미사용)

---

### DoD-2: `services/sd_client/forge.py` — ForgeClient 구현

**구현 방법:**
- `ForgeClient(SDClientBase)` — `__init__(base_url, timeout)`
- `httpx.AsyncClient` 사용 (기존 패턴 유지)
- 각 메서드는 기존 직접 호출 코드를 래핑
- `controlnet.py`의 동기 `requests` 호출을 `httpx` async로 통일

**동작 정의:**
- Before: `httpx.post(SD_TXT2IMG_URL, json=payload)` -> raw dict
- After: `client.txt2img(payload)` -> `SDTxt2ImgResult`

**엣지 케이스:**
- 메서드별 다른 타임아웃: `timeout` 파라미터로 오버라이드 허용
- 에러: `httpx.HTTPError` 그대로 전파 (호출부의 기존 except 절 유지)

**영향 범위:**
- `controlnet.py` 동기->비동기 전환 시 호출부 변경 필요
- `_resolve_model_name()` 캐시 로직 유지 (캐시 히트 시 동기 반환)

**테스트 전략:**
- `ForgeClient` 인스턴스화 확인
- `txt2img` httpx mock -> `SDTxt2ImgResult` 변환 확인
- 타임아웃 오버라이드 확인

**Out of Scope:** 연결 풀 최적화, retry 로직

---

### DoD-3: `config.py`에 `SD_CLIENT_TYPE` 추가

**구현 방법:** `SD_CLIENT_TYPE = os.getenv("SD_CLIENT_TYPE", "forge")`

**동작 정의:** 기본 `"forge"` -> 기존 동작 100% 동일

**엣지 케이스:** `"comfy"` -> SP-022까지 `NotImplementedError`

**영향 범위:** config.py 1줄 추가

**테스트 전략:** 기본값 확인, 환경변수 오버라이드 확인

**Out of Scope:** ComfyUI용 추가 환경변수

---

### DoD-4: `services/sd_client/factory.py` — get_sd_client() 팩토리

**구현 방법:**
- 모듈 레벨 싱글턴: `_client: SDClientBase | None`
- `get_sd_client()` -> `SD_CLIENT_TYPE`에 따라 클라이언트 생성
- `reset_sd_client()` -> 테스트용 싱글턴 리셋

**동작 정의:** 첫 호출 시 생성, 이후 동일 인스턴스 반환

**엣지 케이스:**
- `"comfy"` -> `NotImplementedError("ComfyUI client: SP-022")`
- `"unknown"` -> `ValueError`

**영향 범위:** 팩토리만 추가

**테스트 전략:**
- 반환 타입 `ForgeClient` 확인
- 싱글턴 동일 인스턴스 확인
- `reset_sd_client()` 후 새 인스턴스
- 잘못된 타입 시 에러

**Out of Scope:** DI 프레임워크

---

### DoD-5: 기존 15곳 -> get_sd_client() 전환

**파일별 전환 계획:**

#### 5-1. `services/generation.py` (1곳)
- `_call_sd_api_raw()` 내 `httpx.post(SD_TXT2IMG_URL)` -> `get_sd_client().txt2img(payload)`
- 응답 파싱을 `SDTxt2ImgResult` 기반으로 간소화

#### 5-2. `services/image_generation_core.py` (3곳)
- `_ensure_correct_checkpoint()` 내 get/post options -> `get_sd_client().get_options()`/`.set_options()`
- `generate_image_with_v3()` 내 txt2img -> `get_sd_client().txt2img()`

#### 5-3. `services/controlnet.py` (5곳)
- `check_controlnet_available()` -> `await get_sd_client().check_controlnet()`
  - 동기->비동기: 스타트업 캐시 패턴 사용 (`_controlnet_available` 모듈 캐시)
- `get_controlnet_models()` -> `await get_sd_client().get_controlnet_models()`
  - `_resolve_model_name()`: 기존 캐시(`_resolved_model_cache`) 유지
- `generate_with_controlnet()` -> async + `get_sd_client().txt2img()`
- `create_pose_from_image()` -> async + `get_sd_client().controlnet_detect()`
- `generate_reference_for_character()` -> `get_sd_client().txt2img()`

#### 5-4. `services/avatar.py` (1곳)
- `ensure_avatar_file()` 내 txt2img -> `get_sd_client().txt2img()`

#### 5-5. `services/sd_progress_poller.py` (1곳)
- `poll_sd_progress()` 내 get progress -> `get_sd_client().get_progress()`

#### 5-6. `routers/sd_models.py` (4곳)
- 4개 엔드포인트 모두 -> `get_sd_client()` 메서드 호출

**동기->비동기 전환 영향 (controlnet.py):**
- `check_controlnet_available()`, `get_controlnet_models()` 현재 동기
- 호출부: `services/generation_controlnet.py`의 `apply_controlnet()` (동기)
- **결정**: 모듈 레벨 캐시 + 스타트업 초기화 패턴으로 동기 호출 유지

**영향 범위:**
- `services/generation_controlnet.py` — `apply_controlnet()` 호출부
- `services/stage/background_generator.py` — `_call_sd_api_raw` 간접 사용 (변경 불필요)
- config.py URL 상수는 **유지** (ForgeClient 내부 + scripts/ 참조)

**테스트 전략:**
- 기존 테스트 전체 통과 확인
- `test_controlnet_reference.py` 검증 기준 수정 (`SD_TXT2IMG_URL` -> `get_sd_client` 참조)

**Out of Scope:** scripts/ 전환, E2E 테스트, 통합 테스트

---

### DoD-6 & DoD-7: 기존 테스트 + 린트 통과

**구현 방법:**
- `pytest backend/tests/ -x` 전체 실행
- `test_controlnet_reference.py` 검증 기준 업데이트
- `ruff format + check` 실행, unused import 정리

---

## 신규 파일 구조

```
backend/services/sd_client/
├── __init__.py     # SDClientBase ABC + 타입 re-export
├── types.py        # SDTxt2ImgResult, SDProgressResult
├── forge.py        # ForgeClient(SDClientBase)
└── factory.py      # get_sd_client(), reset_sd_client()
```

## 전환 순서 (안전한 단계)

1. **Phase A**: `sd_client/` 패키지 생성 (ABC, types, ForgeClient, factory)
2. **Phase B**: 단순한 곳 전환 (sd_progress_poller, avatar, routers/sd_models)
3. **Phase C**: 핵심 전환 (generation, image_generation_core)
4. **Phase D**: 복잡한 전환 (controlnet — 동기->비동기 포함)
5. **Phase E**: 테스트 수정 + 전체 검증

## 변경 파일 요약 (13개)

| 파일 | 유형 |
|------|------|
| `services/sd_client/__init__.py` | 신규 — ABC |
| `services/sd_client/types.py` | 신규 — 타입 |
| `services/sd_client/forge.py` | 신규 — ForgeClient |
| `services/sd_client/factory.py` | 신규 — 팩토리 |
| `config.py` | 수정 — SD_CLIENT_TYPE 1줄 |
| `services/generation.py` | 수정 — 1곳 전환 |
| `services/image_generation_core.py` | 수정 — 3곳 전환 |
| `services/controlnet.py` | 수정 — 5곳 + 동기->비동기 |
| `services/avatar.py` | 수정 — 1곳 전환 |
| `services/sd_progress_poller.py` | 수정 — 1곳 전환 |
| `routers/sd_models.py` | 수정 — 4곳 전환 |
| `tests/test_controlnet_reference.py` | 수정 — 검증 기준 변경 |
| `tests/test_sd_client.py` | 신규 — 테스트 |
