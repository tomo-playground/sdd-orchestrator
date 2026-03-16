# ComfyUI 마이그레이션 — 모듈형 이미지 생성 파이프라인

**상태**: P1 착수 예정
**우선순위**: P1 (P2에서 승격 — 실험 검증으로 전환 필요성 확정)
**선행 관계**: 없음
**예상 범위**: Phase A~F, 총 15~18일
**최종 갱신**: 2026-03-16
**리뷰**: 6개 에이전트 크로스 리뷰 완료 + 실험 4회(54장) 검증

---

## 목표

1. **1-step 고정 파이프라인 → 모듈형 다단계 파이프라인 전환** — ControlNet/IP-Adapter 분업 구조
2. **SD WebUI 의존성을 `SDClientBase` 추상화 계층으로 격리** — Forge→ComfyUI 점진적 전환
3. **캐릭터 일관성 극대화** — 실험 검증된 2-Step(CN→IPA) + FaceID 도입
4. **배치 생성/프롬프트 스케줄링** — 4씬 일괄 처리 (ComfyUI 네이티브)

## 완료 기준 (DoD)

- [ ] `SDClientBase` 인터페이스 + `WebUIClient` + `ComfyUIClient` 구현
- [ ] 4-Module 파이프라인 동작 (Identity→Context→Refinement→Upscale)
- [ ] 2-Step 생성(CN→IPA) 또는 FaceID+CN 1-Step 생성 지원
- [ ] 배치 4씬 일괄 생성 가능
- [ ] 기존 SD WebUI 직접 호출 지점 0건 (services/, routers/)
- [ ] pytest 전체 통과 + 동일 seed 비교 테스트

---

## 배경: 실험 검증 (2026-03-16)

### 실험 요약 (4회, 54장)

| 실험 | 결과 | 경로 |
|------|------|------|
| 씬 컨셉 레퍼런스 vs 흰배경 | 씬 컨셉 압도적 우수, 흰배경+IPA 0.90은 색/아이덴티티 붕괴 | `experiments/ip_adapter_consistency/` |
| IPA+CN 동시 투입 | IPA 0.90이 CN 완전 압도 — 포즈 제어 불가 | `experiments/ip_adapter_controlnet/` |
| CN 단독 (IPA 없음) | 포즈 제어 완벽 — 달리기/점프/우산/뒷모습 정확 | `experiments/controlnet_only/` |
| 2-Step (CN→IPA) | **포즈 + 캐릭터 일관성 동시 확보** — 최적 파이프라인 확정 | `experiments/2step_pipeline/` |

### 핵심 발견

1. **ControlNet과 IP-Adapter는 같은 생성에서 경쟁시키면 안 됨** → 다른 단계에서 분업
2. **IP-Adapter 0.90은 포즈까지 고정** → 이 특성을 역이용 (Step 1 포즈를 Step 2에서 보존)
3. **프롬프트 충성도가 높음** (NoobAI-XL) → ControlNet 없이도 배경/분위기 제어 가능
4. **CLIP 기반 IPA는 이미지 전체 전이** → FaceID(얼굴만 전이)로 전환하면 CN과 1-step 공존 가능성

### 현재 한계 (AS-IS)

```
씬 이미지 요청 → 1회 SD 호출 (CN+IPA 동시 투입, 3슬롯 경쟁) → 결과
```

- IP-Adapter 0.35로 약하게 사용 (배경 전이 방지) → 캐릭터 일관성 낮음
- IP-Adapter 올리면 ControlNet 무력화 → 포즈 고정
- 고정 파이프라인 → 모듈 교체/확장 불가
- Forge API 한계 → 배치 생성, 복합 워크플로우 구현 어려움

---

## 목표 아키텍처: 4-Module 파이프라인

### TO-BE 파이프라인 설계

```
[Module 1] Identity & Pose Setup (뼈대와 영혼)
┌──────────────────────────────────────────────┐
│  IP-Adapter FaceID 0.7 (얼굴 임베딩만 고정)    │
│  + ControlNet OpenPose (포즈 정밀 제어)        │
│  + 캐릭터 프롬프트 (외형 태그)                  │
│                                               │
│  FaceID는 얼굴만 추출 → 포즈/배경 간섭 없음     │
│  → CN과 같은 생성에서 공존 가능                  │
└──────────────┬────────────────────────────────┘
               ▼
[Module 2] Context Injection (복장/배경 변주)
┌──────────────────────────────────────────────┐
│  씬별 가변 프롬프트:                             │
│    고정: 캐릭터 외형 + 스타일 LoRA               │
│    가변: 의상 + 배경 + 분위기 + 액션              │
│                                               │
│  ComfyUI 프롬프트 스케줄링 → 4씬 배치 일괄 생성  │
└──────────────┬────────────────────────────────┘
               ▼
[Module 3] Iterative Refinement (디테일 교정)
┌──────────────────────────────────────────────┐
│  ADetailer: 얼굴 inpaint 재렌더링              │
│  Hand Refiner: 손가락 교정                     │
│                                               │
│  현재 ADetailer 코드 재활용                     │
└──────────────┬────────────────────────────────┘
               ▼
[Module 4] Master Upscaling (최종 출력)
┌──────────────────────────────────────────────┐
│  Hi-Res Fix 2x 또는 Ultimate SD Upscale       │
│  Denoising 0.3~0.4                            │
│  최종 1080×1920 출력                            │
└───────────────────────────────────────────────┘
```

### 2가지 운영 모드

| 모드 | 사용 시점 | Module 1 구성 |
|------|---------|---------------|
| **FaceID + CN (1-step)** | FaceID 모델 사용 가능 시 | FaceID 0.7 + OpenPose 동시 |
| **2-Step (CN→IPA)** | CLIP IPA만 사용 가능 시 | Step1: CN only → Step2: IPA 0.90 |

### Forge vs ComfyUI 비교

| 항목 | Forge (AS-IS) | ComfyUI (TO-BE) |
|------|--------------|-----------------|
| 4-Module 파이프라인 | 4번 API 호출, 중간 base64 변환 | 노드 연결, VRAM 유지 |
| 배치 4씬 | 순차 호출 | 프롬프트 스케줄링 1회 |
| Module 교체 | Python 코드 수정 | 노드 그래프 교체 |
| FaceID/InstantID | 제한적 지원 | 네이티브 노드 |
| 중간 결과 디버깅 | base64 로그 | 노드별 프리뷰 |
| VRAM 효율 | Step 간 해제/재로드 | 텐서 유지 |
| 커뮤니티 | 축소 추세 | 활발 (Comfy.org 기업화) |

---

## 전환 전략: 3-Phase 접근

### Phase A: SD Client 추상화 (Sprint A~E, 10~13일)

**목표**: 현재 Forge 코드를 추상화하여 ComfyUI 전환 준비. 기능 변경 없이 구조만 변경.

> 상세 Sprint 계획은 아래 "SD Client 추상화 Sprint 계획" 섹션 참조.
> 기술 설계 상세: [SD_CLIENT_ABSTRACTION.md](../../03_engineering/backend/SD_CLIENT_ABSTRACTION.md)

```
services/sd_client/
├── base.py           # SDClientBase(ABC)
├── models.py         # GenerationParams, GenerationResult DTO
└── webui/            # WebUIClient 구현
    ├── payload.py    # Forge 페이로드 빌더
    ├── controlnet.py # CN/IPA 빌더 (3슬롯 패딩 등)
    └── progress.py   # 진행률 폴링
```

### Phase B: ComfyUI 클라이언트 + 워크플로우 (5~7일)

**목표**: ComfyUI 클라이언트 구현 + 4-Module 워크플로우 JSON 설계

```
services/sd_client/
└── comfyui/
    ├── __init__.py    # ComfyUIClient(SDClientBase)
    ├── workflow.py    # GenerationParams → 노드 그래프 JSON
    ├── nodes.py       # CN/IPA/ADetailer 노드 빌더
    └── websocket.py   # WebSocket 진행률 수신
```

**워크플로우 설계 항목**:
1. 기본 txt2img 워크플로우 (Module 2+3+4)
2. 2-Step CN→IPA 워크플로우 (Module 1+2+3+4)
3. FaceID+CN 1-Step 워크플로우 (Module 1 통합)
4. 배치 4씬 프롬프트 스케줄링 워크플로우

### Phase C: 프로덕션 전환 + FaceID 도입 (3~5일)

1. ComfyUI Custom Node 설치 (ControlNet, IP-Adapter Plus, Impact Pack, InstantID)
2. FaceID vs CLIP A/B 테스트 (동일 캐릭터, 동일 프롬프트)
3. 기존 캐릭터 레퍼런스 → FaceID 임베딩 마이그레이션
4. `config.py` → `IMAGE_BACKEND_MODE = "comfyui"` 전환
5. Forge 제거

---

## SD Client 추상화 Sprint 계획 (Phase A 상세)

### Sprint A: DTO + 인터페이스 + Safety Net (1.5일)

- `GenerationParams` / `GenerationResult` DTO (Pydantic)
- `SDClientBase` 추상 인터페이스
- `get_sd_client()` 팩토리 + `IMAGE_BACKEND_MODE` config
- 기존 테스트 Safety Net 확인

### Sprint B: WebUIClient 추출 (3일)

- B-1: txt2img 7곳 통합 → `client.txt2img()`
- B-2: 모델 관리 통합 → `client.switch_model()` 등
- B-3: ControlNet 빌더 통합 → DTO 기반 + async 전환
- B-4: 진행률 폴링 + 캐시 키 DTO 전환
- B-5: avatar.py, lora_calibration.py 통합

### Sprint C: LoRA 주입 분리 (2일)

- PromptBuilder에서 `<lora:>` 태그 → `LoRAConfig` 리스트 분리
- `compose_scene_with_style()` 반환값 3-tuple → 4-tuple
- WebUIClient가 프롬프트에 LoRA 재주입

### Sprint D: Sampler/Config 정리 (1일)

- Forge 특화 유틸 함수 → WebUIClient 내부 이동
- 상수는 config.py 유지 (SSOT)

### Sprint E: 테스트 + 통합 검증 (2.5일)

- 기존 ~100개 테스트 마이그레이션
- 신규 26개 테스트
- 동일 seed 비교 E2E
- 수동 검증 (씬 생성, 레퍼런스, CN+IPA, 아바타, LoRA 칼리브레이션)

> Sprint 각 단계별 상세(수정 대상 파일, 코드 변환 예시, DoD)는
> [SD_CLIENT_ABSTRACTION.md](../../03_engineering/backend/SD_CLIENT_ABSTRACTION.md) 참조

---

## 리스크 및 완화

| 리스크 | 심각도 | 완화 |
|--------|--------|------|
| Phase A 추상화 시 동작 변경 | **높** | 동일 seed 비교 E2E, Sprint별 테스트 동시 수정 |
| LoRA 주입 분리 미묘한 차이 | **높** | LoRA 순서/중복/capping 단위 테스트 5개 |
| ComfyUI 워크플로우 복잡도 | 중 | 기본 워크플로우 템플릿 4종 사전 설계 |
| FaceID 모델 품질 불확실 | 중 | CLIP IPA 2-Step 폴백 유지 |
| 생성 시간 증가 (2-Step: ~17초/씬) | 중 | ComfyUI VRAM 유지로 개선 + Step1 steps 축소 |
| Forge→ComfyUI 전환 기간 이중 유지보수 | 낮 | SDClientBase 추상화로 양쪽 동시 지원 |

---

## 비변경 영역

Phase A~C에서 **건드리지 않는** 순수 비즈니스 로직:

| 영역 | 파일 | 이유 |
|------|------|------|
| 12-Layer 프롬프트 엔진 | `prompt/composition.py` | 구조 유지 (LoRA 분리만 변경) |
| 파라미터 최적화 | `generation.py` `_adjust_parameters()` | SD 무관 |
| ControlNet 적용 판단 | `generation_controlnet.py` 오케스트레이션 | DTO 생성만, 포맷 변환은 Client |
| 포즈 감지/분류 | `controlnet.py` 순수 로직 6개 | SD 무관 |
| Gemini Agent 파이프라인 | `services/agent/` | 이미지 생성과 독립 |
| 렌더링 파이프라인 | `services/video/` | FFmpeg 기반, SD 무관 |
| Frontend | `frontend/` | API 인터페이스 유지 |

---

## 향후 확장 (Phase C 이후)

| 기능 | ComfyUI 기반 구현 |
|------|------------------|
| 의상 변경 | Module 2만 교체 (Module 1 재사용) |
| 멀티캐릭터 | FaceID 복수 주입 + Regional Prompting 노드 |
| 영상 생성 | AnimateDiff/SVD 노드 추가 |
| 실시간 프리뷰 | WebSocket 중간 결과 스트리밍 |
| A/B 테스트 | 워크플로우 2개 병렬 실행 |
