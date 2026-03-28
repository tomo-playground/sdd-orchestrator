---
id: SP-113
title: ComfyUI IP-Adapter 워크플로우 노드 통합 — 캐릭터 일관성 복원
priority: P0
scope: backend
branch: feat/SP-113-comfyui-ip-adapter
created: 2026-03-28
status: done
label: bug
---

## 배경

PR #225 (Forge 제거) 이후 IP-Adapter/Reference Only가 ComfyUI에 적용되지 않음.
ControlNet 코드가 SD WebUI 형식(`alwayson_scripts`)으로만 남아있고, ComfyUI 워크플로우 노드로 전환되지 않음.
결과: 레퍼런스 이미지가 무시되어 캐릭터 일관성 완전 상실.

## DoD (Definition of Done)

### 1. scene_single.json에 IP-Adapter 노드 추가
- `IPAdapterApply` 또는 `IPAdapterAdvanced` 노드를 워크플로우에 추가
- `{{ip_adapter_image}}`, `{{ip_adapter_weight}}`, `{{ip_adapter_model}}` placeholder
- IP-Adapter 미사용 시 bypass (weight=0 또는 노드 비활성화)

### 2. ComfyUI 클라이언트에서 IP-Adapter 변수 주입
- `_payload_to_variables` 또는 `txt2img`에서 IP-Adapter 관련 변수 워크플로우에 주입
- 레퍼런스 이미지 base64 → ComfyUI `/upload/image` → 파일명 변수 주입
- `generation_controlnet.py`의 `_apply_ip_adapter` 결과를 ComfyUI 노드로 변환

### 3. Reference Only (AdaIN) 노드 통합
- `ReferenceOnlySimple` 또는 동등 ComfyUI 커스텀 노드 적용
- environment_reference (배경 레퍼런스)도 동일 경로

### 4. scene_2p.json에도 동일 적용

### 5. 테스트
- IP-Adapter 활성화 시 레퍼런스 이미지 반영 확인
- IP-Adapter 비활성화 시 정상 생성 확인
- 기존 테스트 통과

## 참조

- `backend/services/sd_client/comfyui/__init__.py` — `txt2img()`
- `backend/services/generation_controlnet.py` — `_apply_ip_adapter()`, `_apply_reference_only()`
- `backend/services/sd_client/comfyui/workflows/scene_single.json`
- ComfyUI 커스텀 노드: `ComfyUI_IPAdapter_plus` (설치 확인됨)
- 트러블슈팅: `docs/04_operations/TROUBLESHOOTING_WHITE_IMAGE.md`
