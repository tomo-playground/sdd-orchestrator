---
id: SP-084
priority: P1
scope: backend
branch: feat/SP-084-comfyui-native-cleanup
created: 2026-03-26
status: pending
depends_on:
label: chore
---

## 무엇을 (What)
Forge/WebUI 호환 레이어를 제거하고 ComfyUI 단일 경로로 정리한다. SD_CLIENT_TYPE 분기, Forge 전용 페이로드, 불필요한 API 호출을 제거.

## 왜 (Why)
현재 이미지 생성 파이프라인이 Forge 형식으로 페이로드를 빌드한 뒤 ComfyUI 클라이언트가 번역하는 구조. 매 생성마다 불필요한 변환 발생, 두 경로 유지로 버그 리스크 2배, ComfyUI 네이티브 기능(Regional, 멀티스테이지) 활용 불가.

## 완료 기준 (DoD)

### Phase A: Forge 분기 제거
- [ ] `composition.py`의 `SD_CLIENT_TYPE != "comfy"` 분기 3곳 제거 — LoRA 트리거 워드 주입 로직 삭제
- [ ] `reference.py`의 `SD_CLIENT_TYPE` 분기 제거 — ComfyUI 경로만 유지
- [ ] `image_generation_core.py`의 `_ensure_correct_checkpoint()` 제거 — ComfyUI는 워크플로우에서 체크포인트 지정

### Phase B: Forge 페이로드 정리
- [ ] `generation.py`의 `override_settings`, `override_settings_restore_afterwards` 제거
- [ ] `generation.py`의 Hi-Res Fix 파라미터 (`enable_hr`, `hr_scale`, `hr_upscaler`, `hr_second_pass_steps`, `hr_additional_modules`) 제거
- [ ] `controlnet.py`의 `_resolve_model_name()` (Forge `name [hash]` 해석) 제거
- [ ] `controlnet.py`의 Forge alwayson_scripts ControlNet 파라미터 구조 정리

### Phase C: 변환 레이어 간소화
- [ ] `comfyui/__init__.py`의 weight emphasis 정규식 제거 (ComfyUI가 직접 처리)
- [ ] `config.py`의 미사용 Forge 상수 제거 (`SD_CFG_RESCALE` 등 — 사용처 확인 후)
- [ ] `SD_BASE_URL` 조건부 로깅 제거

### Phase D: ForgeClient 제거
- [ ] `services/sd_client/forge.py` 삭제
- [ ] `services/sd_client/factory.py`에서 Forge 분기 제거 — ComfyUI 직접 반환
- [ ] `SD_CLIENT_TYPE` 환경변수 제거 (ComfyUI 고정)
- [ ] `.env.example`에서 `SD_CLIENT_TYPE`, `SD_BASE_URL` 제거

### 공통
- [ ] 기존 테스트 regression 없음 (test_comfy_client.py, test_composition.py 등)
- [ ] Forge 관련 테스트 제거 또는 ComfyUI 전용으로 업데이트
- [ ] 린트 통과

## 참고
- Forge 코드는 `forge-docker/`에 Dockerfile만 보존 (rollback용)
- ComfyUI 전환 완료: PR #205, #207, #210
- PoC 결과: `memory/project_character_consistency_poc.md`
