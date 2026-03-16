# 캐릭터 일관성 V3 — 모듈형 파이프라인 (Character Consistency V3)

**상태**: 미착수 (백로그 P1)
**우선순위**: P1 — ComfyUI 마이그레이션 완료 후 착수
**선행 관계**: ComfyUI 마이그레이션 (Phase A~C)
**관련**: [V2 명세](CHARACTER_CONSISTENCY_V2.md) (Phase 30, 완료), [ComfyUI 마이그레이션](COMFYUI_MIGRATION.md)
**최종 갱신**: 2026-03-16

---

## 요약

V2(Phase 30)에서 프롬프트+IP-Adapter+ControlNet 조합으로 캐릭터 일관성을 개선했으나,
**1회 SD 호출에 모든 도구를 동시 투입하는 구조적 한계**가 실험으로 확인됨.

V3는 이미지 생성을 **다단계 모듈 파이프라인**으로 분업화하여
캐릭터 일관성 + 포즈 다양성 + 의상 가변성을 동시 확보한다.

---

## 실험 검증 (2026-03-16, 4회 54장)

### 실험 1: 씬 컨셉 레퍼런스 vs 흰배경 레퍼런스 (12장)

| 레퍼런스 타입 | IPA 0.90 결과 |
|-------------|--------------|
| 흰배경 캐릭터 시트 | 색 날아감, 아이덴티티 붕괴 |
| **씬 컨셉 (배경 포함)** | **캐릭터 일관성 매우 높음**, 포즈 고정 |

**발견**: 레퍼런스 품질 > IP-Adapter weight 튜닝

### 실험 2: IP-Adapter + ControlNet 동시 투입 (12장)

| 설정 | 포즈 변화 | 캐릭터 일관성 |
|------|----------|-------------|
| IPA 0.90 only | 포즈 고정 (레퍼런스 포즈 전이) | 매우 높음 |
| IPA 0.90 + CN OpenPose | **CN 무력화** — IPA가 압도 | 매우 높음 |
| IPA 0.70 + CN OpenPose | 미미한 개선 | 높음 |

**발견**: 같은 생성에서 IPA와 CN을 경쟁시키면 IPA가 이김

### 실험 3: ControlNet 단독 — IPA 없음 (13장)

| 포즈 | 프롬프트만 | CN OpenPose |
|------|----------|-------------|
| 달리기 | 부분 반영 | **정확** |
| 점프 | 부분 반영 | **정확** |
| 우산 | 반영 | **정확** |
| 뒷모습 | 반영 | **정확** |
| 손흔들기 | 부분 반영 | **정확** |

**발견**: CN 단독 = 포즈 제어 완벽. 프롬프트만으로도 NoobAI-XL의 높은 충성도 확인

### 실험 4: 2-Step 파이프라인 CN→IPA (17장)

| 씬 | 1-step (IPA only) | 2-step (CN→IPA) |
|---|---|---|
| 달리기 | 카페 포즈 고정 | **포즈 정확 + 캐릭터 일관** |
| 우산 | 비슷 | **포즈 정확 + 캐릭터 일관** |
| 손흔들기 | 포즈 약함 | **포즈 정확 + 캐릭터 일관** |
| 뒷모습 | 포즈 약함 | **포즈 정확 + 캐릭터 일관** |
| 앉기 | 카페 포즈 | **포즈 정확 + 캐릭터 일관** |

**발견**: 2-Step 분리 = 포즈 다양성 + 캐릭터 일관성 동시 확보. IPA 0.90이 포즈를 잠그는 특성을 **역이용**.

### 실험 데이터 위치

```
experiments/
├── ip_adapter_consistency/  # 실험 1 (12장)
├── ip_adapter_controlnet/   # 실험 2 (12장)
├── controlnet_only/          # 실험 3 (13장)
└── 2step_pipeline/           # 실험 4 (17장)
```

---

## 핵심 원칙 (실험 기반)

1. **ControlNet과 IP-Adapter는 같은 생성에서 경쟁시키지 않는다** → 다른 단계에서 분업
2. **IP-Adapter 0.90은 포즈까지 고정한다** → 역이용: Step 1 포즈를 Step 2에서 보존
3. **레퍼런스 품질이 weight보다 중요하다** → 씬 컨셉 레퍼런스 >> 흰배경 레퍼런스
4. **CLIP IPA는 이미지 전체를 전이한다** → FaceID(얼굴만)로 전환 시 CN과 1-step 공존 가능

---

## 레벨 정의 (V2 → V3)

| 레벨 | 기술 | 상태 |
|------|------|------|
| 2 | 프롬프트 + IP-Adapter | ✅ 완료 |
| 3 | + ControlNet + FaceID + 복장 enforce | ✅ V2 완료 |
| 3.5 | + Multi-Character (V-Pred 일반 프롬프트) | ✅ V2 완료 |
| **4** | **모듈형 파이프라인 (2-Step CN→IPA)** | **V3 목표** |
| **4.5** | **FaceID + CN 1-Step (ComfyUI)** | **V3 목표** |
| **5** | **배치 4씬 + 의상 가변 + 멀티캐릭터** | **V3 확장** |

---

## 목표 아키텍처: 4-Module 파이프라인

```
[Module 1] Identity & Pose (뼈대와 영혼)
┌──────────────────────────────────────────┐
│  Option A: FaceID 0.7 + CN OpenPose      │  ← 1-step (ComfyUI)
│  Option B: CN OpenPose only → IPA 0.90   │  ← 2-step (폴백)
│  + 캐릭터 프롬프트 (외형 태그)              │
│                                           │
│  FaceID = 얼굴 임베딩만 → 포즈/배경 무간섭  │
│  CLIP IPA = 이미지 전체 전이 → 분리 필수    │
└──────────────┬────────────────────────────┘
               ▼
[Module 2] Context Injection (복장/배경 변주)
┌──────────────────────────────────────────┐
│  고정: 캐릭터 외형 + Style LoRA             │
│  가변: 의상 + 배경 + 분위기 + 액션           │
│                                           │
│  씬별 프롬프트 스케줄링 → 4씬 배치 일괄      │
│  의상 변경 시 이 Module만 교체              │
└──────────────┬────────────────────────────┘
               ▼
[Module 3] Refinement (디테일 교정)
┌──────────────────────────────────────────┐
│  ADetailer: 얼굴 inpaint 재렌더링          │
│  Hand Refiner: 손가락 교정                 │
│  기존 코드 재활용                           │
└──────────────┬────────────────────────────┘
               ▼
[Module 4] Upscale (최종 출력)
┌──────────────────────────────────────────┐
│  Hi-Res Fix 2x (1080×1920)               │
│  Denoising 0.3~0.4                       │
│  기존 코드 재활용                           │
└───────────────────────────────────────────┘
```

### 운영 모드

| 모드 | 조건 | Module 1 구성 | 장점 |
|------|------|-------------|------|
| **FaceID + CN** | ComfyUI + FaceID 모델 | 1-step 동시 투입 | 빠름, 의상 자유 |
| **2-Step CN→IPA** | CLIP IPA 사용 시 | Step1 CN → Step2 IPA 0.90 | 검증 완료, 폴백 |

---

## 완료 기준 (DoD)

### Phase 1: 2-Step 파이프라인 프로덕션 (ComfyUI 전환 직후)

- [ ] ComfyUI 워크플로우: CN OpenPose → IPA 0.90 2-Step 동작
- [ ] 기존 ControlNet 포즈 28종 호환
- [ ] 씬 생성 API에서 2-Step 모드 자동 선택
- [ ] 생성 시간 측정 (목표: 씬당 20초 이내)
- [ ] V2 대비 캐릭터 일관성 A/B 테스트

### Phase 2: FaceID 도입

- [ ] IP-Adapter FaceID PlusV2 ComfyUI 노드 설치
- [ ] 기존 캐릭터 레퍼런스 → FaceID 임베딩 변환
- [ ] FaceID 0.7 + CN OpenPose 1-step 워크플로우
- [ ] CLIP IPA vs FaceID A/B 테스트 (캐릭터 일관성 + 의상 자유도)
- [ ] 캐릭터 DB에 `ip_adapter_model` = `"faceid"` 옵션 추가

### Phase 3: 배치 생성 + 의상 가변

- [ ] 프롬프트 스케줄링으로 4씬 일괄 생성
- [ ] 씬별 의상 변경 (Module 2만 교체, Module 1 재사용)
- [ ] 스토리보드 전체 이미지 일괄 생성 API

### Phase 4: 멀티캐릭터 확장

- [ ] FaceID 복수 주입 (캐릭터 A + B)
- [ ] Regional Prompting 노드 (ComfyUI 네이티브)
- [ ] 2인 대화 씬 일관성 테스트

---

## V2 → V3 변경 매트릭스

| 항목 | V2 (현재) | V3 (목표) |
|------|---------|---------|
| 생성 구조 | 1-step (CN+IPA 동시) | 다단계 모듈 파이프라인 |
| IPA 모델 | CLIP (NOOB-IPA-MARK1) | FaceID PlusV2 (+ CLIP 폴백) |
| IPA weight | 0.35~0.50 (배경 전이 방지) | FaceID 0.7 또는 CLIP 0.90 (2-step) |
| ControlNet | IPA와 경쟁 (무력화됨) | 별도 단계에서 독립 제어 |
| 레퍼런스 | 흰배경 캐릭터 시트 1장 | 씬 컨셉 레퍼런스 or FaceID 임베딩 |
| 배치 생성 | 씬별 순차 호출 | 4씬 프롬프트 스케줄링 |
| 의상 변경 | 전체 재생성 | Module 2만 교체 |
| 멀티캐릭터 | V-Pred 일반 프롬프트 | FaceID 복수 + Regional Prompting |
| SD 백엔드 | Forge API | ComfyUI 노드 그래프 |

---

## 리스크 및 완화

| 리스크 | 심각도 | 완화 |
|--------|--------|------|
| FaceID 모델 애니메이션 품질 불확실 | **높** | CLIP IPA 2-Step 폴백 유지 |
| 생성 시간 증가 (2-Step ~17초) | 중 | ComfyUI VRAM 유지 + Step1 steps 축소 |
| 기존 캐릭터 레퍼런스 호환 | 중 | FaceID 임베딩 자동 변환 스크립트 |
| ComfyUI 선행 의존 | — | ComfyUI 마이그레이션 Phase A~C 완료 필수 |

---

## 참고

- 실험 스크립트: `backend/scripts/experiment_*.py` (4개)
- 실험 데이터: `experiments/` (54장 + report.json)
- V2 명세: [CHARACTER_CONSISTENCY_V2.md](CHARACTER_CONSISTENCY_V2.md)
- ComfyUI 전환: [COMFYUI_MIGRATION.md](COMFYUI_MIGRATION.md)
- SD Client 추상화: [SD_CLIENT_ABSTRACTION.md](../../03_engineering/backend/SD_CLIENT_ABSTRACTION.md)
