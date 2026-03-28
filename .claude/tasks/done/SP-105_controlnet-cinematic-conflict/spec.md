---
id: SP-105
priority: P1
scope: backend
branch: feat/SP-105-controlnet-cinematic-conflict
created: 2026-03-27
status: done
approved_at: 2026-03-28
depends_on:
label: fix
---

## 상세 설계 (How)

> [design.md](./design.md) 참조

## 무엇을 (What)
ControlNet Reference AdaIN 활성 시 시네마틱 태그 충돌로 이미지가 깨지는 문제 근본 수정.

## 왜 (Why)
Storyboard #1199에서 확인: 12개 씬 중 Scene 4, 6이 형체 붕괴, Scene 5, 10은 극단적 레드톤 색감 왜곡.
원인: Atmosphere Agent가 생성한 시네마틱 태그(`bokeh`, `depth_of_field`, `sidelighting`, `lens_flare`)가 배경 ControlNet Reference AdaIN과 충돌.
현재 파이프라인에 ControlNet 존재 여부에 따른 시네마틱 태그 필터링이 전혀 없음.

## 참조
- 문제 이미지: Storyboard #1199, Scene 4(3만원 어치나), Scene 6(블라우스는 또 왜 뒤집혀)
- Atmosphere Agent: `backend/services/agent/nodes/_cine_atmosphere.py`
- Compositor: `backend/services/agent/nodes/_cine_compositor.py`
- ControlNet 적용: `backend/services/generation_controlnet.py`
- 프롬프트 준비: `backend/services/generation_prompt.py`
- AdaIN 가중치: `backend/config.py` (REFERENCE_ADAIN_WEIGHT_*)

## 근본 원인 5건

### P1. Atmosphere Agent에 ControlNet 정보 미전달
- **위치**: `_cine_atmosphere.py:78-109` — `_build_prompt()`
- **현상**: 배경 ControlNet 존재 여부를 모르고 시네마틱 태그 생성
- **영향**: `bokeh + depth_of_field + Reference AdaIN` 조합 시 피사체 blur/형체 붕괴

### P2. 생성 파이프라인에 시네마틱 태그 필터링 부재
- **위치**: `generation_prompt.py`, `generation_controlnet.py`
- **현상**: ControlNet Reference AdaIN 활성 시에도 시네마틱 태그가 그대로 SD에 전달
- **영향**: 모든 위험 태그 조합이 필터 없이 생성에 투입

### P3. ControlNet 충돌 감지가 environment 레이어만 검사
- **위치**: `generation_controlnet.py:240-255` — `_check_tag_conflict()`
- **현상**: `LAYER_ENVIRONMENT` 태그만 비교, `LAYER_ATMOSPHERE`(시네마틱) 미검사
- **영향**: 시네마틱 vs Reference AdaIN 충돌이 감지 자체가 안 됨

### P4. Indoor Reference AdaIN 가중치 과도
- **위치**: `config.py:729` — `REFERENCE_ADAIN_WEIGHT_INDOOR = 0.40`
- **현상**: 시네마틱 태그와 결합 시 배경 색감이 이미지를 지배
- **영향**: Scene 5, 10의 극단적 레드톤 왜곡

### P5. 시네마틱 태그가 image_prompt에 Bake-in되어 분리 불가
- **위치**: `_cine_compositor.py` → `image_prompt` 평문에 직접 합침
- **현상**: `generation_prompt.py:42-53`의 `_collect_context_tags()`가 `cinematic` 키 미수집
- **영향**: 생성 시점에서 시네마틱 태그만 선택적으로 제거/조정할 경로 없음

## 완료 기준 (DoD)

### Must (P0)
- [ ] Reference AdaIN 활성 시 위험 시네마틱 태그 자동 억제 (생성 직전 필터)
  - 대상: `depth_of_field`, `bokeh`, `blurry_background`, `sidelighting`, `lens_flare`, `chromatic_aberration`
  - Reference AdaIN 비활성 시에는 필터 미적용 (기존 동작 유지)
- [ ] 억제된 태그는 warning 로그 + `debug_payload.warnings`에 기록
- [ ] Storyboard #1199 Scene 4, 6 재생성 시 형체 붕괴 해소 확인

### Should (P1)
- [ ] Atmosphere Agent에 배경 ControlNet 힌트 전달
  - `_build_prompt()`에 `has_environment_reference: bool` 정보 추가
  - LLM 프롬프트에 "Reference AdaIN 사용 중이므로 depth blur 계열 태그 자제" 규칙 추가
- [ ] Indoor Reference AdaIN 가중치 하향: 0.40 → 0.30

### Could (P2)
- [ ] `_check_tag_conflict()`에 atmosphere 레이어 충돌 감지 추가
- [ ] `context_tags.cinematic`을 `_collect_context_tags()`에서 별도 수집 → 생성 시 분리 처리 경로 확보

## 힌트
- 가장 효과적인 1차 수정: `generation_prompt.py` 또는 `generation_controlnet.py`에서 Reference AdaIN 활성 감지 → 프롬프트에서 위험 태그 strip
- `context_tags.cinematic`에 이미 태그 목록이 보존되어 있으므로, 이를 기반으로 `image_prompt`에서 해당 태그를 제거하면 됨
- Atmosphere Agent 힌트는 LLM 의존적이라 100% 보장 불가 → 반드시 생성 시점 필터와 병행
