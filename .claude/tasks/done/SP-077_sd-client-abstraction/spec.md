---
id: SP-077
priority: P1
scope: backend
branch: feat/SP-077-sd-client-abstraction
created: 2026-03-24
status: done
approved_at: 2026-03-24
depends_on:
label: refactor
---

## 무엇을 (What)
SD WebUI 직접 호출 24곳을 `SDClient` 추상화 계층으로 통합. ComfyUI 전환(SP-022) 선행 작업.

## 왜 (Why)
현재 `services/`, `routers/`에서 SD WebUI API를 직접 호출(requests.post, sd_api 등)하고 있어서, ComfyUI로 전환하려면 24곳을 전부 수정해야 함. 추상화 계층을 만들면 Client만 교체하면 됨.

## 완료 기준 (DoD)

- [x] `services/sd_client/__init__.py` — `SDClientBase` ABC 정의 (txt2img, img2img, get_models, get_options, set_options)
- [x] `services/sd_client/forge.py` — `ForgeClient` 구현 (기존 SD WebUI 호출 래핑)
- [x] `config.py`에 `SD_CLIENT_TYPE` 환경변수 추가 (`forge` | `comfy`)
- [x] `services/sd_client/factory.py` — `get_sd_client() -> SDClientBase` 팩토리
- [x] 기존 SD WebUI 직접 호출 24곳 → `get_sd_client().txt2img(...)` 등으로 전환
- [x] 기존 테스트 통과
- [x] 린트 통과

## 제약
- ComfyUIClient 구현은 SP-022에서
- 기존 동작 변경 없음 (ForgeClient가 동일하게 동작)
- 인터페이스 시그니처는 ForgeUI/ComfyUI 양쪽을 수용할 수 있게 설계

## 힌트
- `grep -rn "sd_api\|sdapi\|txt2img\|img2img\|SD_BASE_URL" backend/services/ backend/routers/` 로 호출 지점 확인
- `backend/services/image_generation_core.py`가 핵심 진입점
- `backend/services/controlnet.py`에 ControlNet/IP-Adapter 관련 호출 집중
