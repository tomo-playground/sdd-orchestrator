---
id: SP-022
priority: P1
scope: backend
branch: feat/SP-022-comfyui-migration
created: 2026-03-24
status: pending
depends_on: SP-077
label: feat
---

## 무엇을 (What)
ForgeUI → ComfyUI 점진적 전환. SD Client 추상화 + ComfyUI 워크플로우 기반 이미지 생성.

## 왜 (Why)
- ForgeUI: 1-step 고정 파이프라인, 2P 멀티캐릭터 품질 한계, 배치 생성 불가
- ComfyUI: 모듈형 워크플로우, Regional Prompting, 영역별 IP-Adapter, 배치 처리
- 2026-03-24 테스트 완료: DynamicThresholding 적용 시 5캐릭터 레퍼런스 정상 생성 확인

## 완료 기준 (DoD)

### Phase A: SD Client 추상화
- [ ] `services/sd_client/base.py` — `SDClientBase` 인터페이스 (txt2img, img2img, get_models)
- [ ] `services/sd_client/forge.py` — 기존 ForgeUI 호출을 `ForgeClient`로 래핑
- [ ] `services/sd_client/comfy.py` — `ComfyUIClient` 구현 (workflow_runner.py 기반)
- [ ] 기존 SD WebUI 직접 호출 지점을 Client 인터페이스로 전환
- [ ] `config.py`에 `SD_CLIENT_TYPE = "forge" | "comfy"` 스위치

### Phase B: 워크플로우 관리
- [ ] `comfyui/workflows/` 디렉토리에 용도별 워크플로우 JSON
  - `reference.json` — 캐릭터 레퍼런스 (DynamicThresholding 포함, 검증 완료)
  - `scene_single.json` — 1인 씬 이미지
  - `scene_multi.json` — 2인 씬 (Regional Prompting)
- [ ] `comfyui/workflow_runner.py` — 변수 치환 + API 실행 (구현 완료)

### Phase C: 레퍼런스 생성 전환
- [ ] 캐릭터 레퍼런스 생성을 ComfyUI로 전환 (ForgeUI 코드 유지, 스위치로 선택)
- [ ] 기존 레퍼런스 품질 대비 동등 이상 확인

### Phase D: 씬 이미지 전환
- [ ] 1인 씬 이미지를 ComfyUI로 전환
- [ ] ControlNet + LoRA 워크플로우 검증
- [ ] IP-Adapter 워크플로우 검증

### Phase E: 정리
- [ ] ForgeUI 의존성 제거 (config 스위치로 유지 → 안정화 후 제거)
- [ ] 기존 테스트 통과
- [ ] 린트 통과

## 제약
- 2P 멀티캐릭터(Regional Prompting)는 SP-023에서
- ForgeUI는 당분간 fallback으로 유지
- ComfyUI 커스텀 노드: `sd-dynamic-thresholding` 필수

## 힌트
- ComfyUI 설치 완료: `/home/tomo/ComfyUI` (포트 8188)
- 모델 공유: `/home/tomo/sd-models/`
- 안정 설정: Euler/normal/CFG7.0 + DynamicThresholding(mimic_scale=5.0)
- `comfyui/workflow_runner.py` + `comfyui/generate_reference.py` 이미 구현
- [명세](../../docs/01_product/FEATURES/COMFYUI_MIGRATION.md) 참조
