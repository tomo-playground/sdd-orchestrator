# 캐릭터 렌더링 실험 리포트

> 실험일: 2025-01-24
> 목적: 쇼츠 영상의 다중 캐릭터 장면 생성 및 일관성 유지 방법 검증

## 1. 실험 배경

쇼츠 콘텐츠(특히 "썰" 형태)에서 두 명 이상의 캐릭터가 대화하거나 상호작용하는 장면이 필요함. 이를 위한 최적의 렌더링 파이프라인을 검증.

### 핵심 요구사항
- 다중 캐릭터 장면 생성
- 캐릭터별 LoRA 적용
- 장면 간 캐릭터 일관성 유지
- 상호작용 (포옹, 손잡기 등) 자연스러움

---

## 2. 실험 환경

| 항목 | 값 |
|------|-----|
| SD WebUI | AUTOMATIC1111 |
| 기본 모델 | anythingV3_fp16.safetensors |
| ControlNet | v1.1 (7개 모델) |
| 테스트 LoRA | eureka_v9, mha_midoriya-10, chibi-laugh |

---

## 3. 실험 1: 대화 장면 (분리 합성)

### 방법
1. 캐릭터 A 개별 생성 (seed 고정)
2. 캐릭터 B 개별 생성
3. rembg로 배경 제거
4. PIL로 좌우 합성
5. 화자 강조 효과 (밝기 차이)

### 결과
```
outputs/dialogue_test/
├── char_happy.png / char_surprised.png (캐릭터 A 표정 변화)
├── char_B_happy.png (캐릭터 B)
├── dialogue_speaker_A.png (A 화자 강조)
└── dialogue_speaker_B.png (B 화자 강조)
```

### 평가
| 항목 | 결과 |
|------|------|
| 캐릭터 일관성 | ✅ seed 고정으로 유지 |
| 배경 제거 품질 | ✅ rembg 양호 |
| 화자 구분 | ✅ 밝기 효과 적용 |
| 적용 장면 | 대화, 리액션 (비접촉) |

---

## 4. 실험 2: 상호작용 장면 (포옹)

### 방법 비교

| 방법 | 설명 | 결과 |
|------|------|------|
| **단일 생성** | SD에서 "2girls, hug" 직접 생성 | ✅ 자연스러움 |
| **분리 합성** | 개별 생성 후 레이어 합성 | ❌ 신체 접촉 부자연스러움 |

### 베스트 결과: 단일 생성
```
outputs/hug_test/eureka_lora_hug.png
outputs/hug_test/eureka_couple_hug.png (남녀)
```

### 결론
- **상호작용 장면 (포옹, 손잡기)** → 단일 이미지 생성
- 조명/그림자 일관성, 신체 접촉 자연스러움

---

## 5. 실험 3: 캐릭터별 LoRA 적용 (손잡고 걷기)

### 목표
- 남자: mha_midoriya LoRA
- 여자: eureka LoRA
- 배경: 비 오는 거리

### 방법 비교

| 방법 | LoRA 분리 | 손잡기 | 평가 |
|------|----------|--------|------|
| **분리 합성** | ✅ 개별 적용 | ❌ 연결 안됨 | ⭐⭐ |
| **단일 + 다중 LoRA** | ⚠️ 혼합 | ✅ 자연스러움 | ⭐⭐⭐⭐ |
| **ControlNet** | ⚠️ 혼합 | ✅ 자연스러움 | ⭐⭐⭐⭐ |
| **Regional Prompt** | ⚠️ 혼합 | ✅ 자연스러움 | ⭐⭐⭐⭐ |
| **img2img 보정 (0.7)** | ❌ 손실 | ✅ 재해석 | ⭐⭐⭐⭐ |

### 결과 파일
```
outputs/hug_test/comparison/
├── method1_controlnet.png
├── method2_regional.png
├── method3_img2img_low.png (denoising 0.3)
├── method3_img2img_mid.png (denoising 0.5)
└── method3_img2img_high.png (denoising 0.7)
```

### 결론
- 상호작용 장면에서 캐릭터별 LoRA 완전 분리는 어려움
- **ControlNet 단일 생성**이 가장 실용적

---

## 6. 실험 4: 캐릭터 일관성 유지

### 문제
- 장면마다 캐릭터가 재해석되어 일관성 상실

### 테스트한 방법

| 방법 | 일관성 | 애니메이션 적합 | 추천도 |
|------|--------|----------------|--------|
| Seed 고정 | ⚠️ 포즈 바꾸면 무너짐 | ⚠️ | ⭐⭐ |
| IP-Adapter FaceID | ❌ 실사용 | ❌ | ⭐ |
| **Reference-only** | ✅ 스타일 유지 | ✅ | ⭐⭐⭐⭐⭐ |

### Reference-only 최적 설정
```python
{
    "module": "reference_only",
    "model": "None",
    "weight": 0.5,           # 낮춰서 포즈 자유도 확보
    "guidance_end": 0.8,     # 후반부는 프롬프트 우선
}
```

### 결과
```
outputs/hug_test/consistency/
├── base_character.png (기준)
├── reference_only_walk.png (포즈 변경)
```

---

## 7. 실험 5: 치비 스타일 포즈 변화

### 목표
- chibi-laugh LoRA로 기준 캐릭터 생성
- Reference-only로 4가지 포즈 (서다/걷기/앉기/달리기)

### 결과
```
outputs/hug_test/chibi_poses_v2/
├── chibi_base_fullbody.png (기준 - 전신)
├── chibi_standing.png
├── chibi_walking.png
├── chibi_sitting.png
└── chibi_running.png
```

### 일관성 평가
| 항목 | 유지 여부 |
|------|----------|
| 머리색 (갈색) | ✅ |
| 눈 색상 (파란눈) | ✅ |
| 교복 (세일러복) | ✅ |
| 치비 스타일 | ✅ |
| 볼터치 | ✅ |

### 핵심 발견
- **기준 이미지를 전신으로** 생성해야 포즈 변경이 자연스러움
- 얼굴 클로즈업 기준 → 결과도 클로즈업 됨

---

## 8. 최종 권장 파이프라인

### 장면 유형별 전략

```
┌─────────────────────────────────────────────────────────┐
│                    장면 유형 판단                        │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
   [상호작용 장면]                    [대화 장면]
   포옹, 손잡기 등                    좌우 배치, 리액션
          │                               │
          ▼                               ▼
   ControlNet +                      분리 생성 +
   단일 이미지 생성                   레이어 합성
          │                               │
          └───────────────┬───────────────┘
                          ▼
              [Reference-only로 일관성 유지]
```

### 캐릭터 일관성 파이프라인

```python
# 1. 캐릭터 기준 이미지 생성 (최초 1회)
base_image = generate(
    prompt="<lora:character_lora:0.8>, 1girl, full body, standing...",
    seed=12345
)

# 2. 이후 장면은 Reference-only 참조
scene_image = generate(
    prompt="<lora:character_lora:0.8>, 1girl, walking, rainy day...",
    controlnet={
        "module": "reference_only",
        "weight": 0.5,
        "guidance_end": 0.8,
        "image": base_image
    }
)
```

---

## 9. 한계점 및 향후 과제

### 현재 한계
1. **캐릭터별 LoRA 완전 분리**: 상호작용 장면에서 어려움
2. **포즈 정밀 제어**: OpenPose 참조 이미지 필요
3. **표정 세밀 제어**: 프롬프트 의존도 높음

### 향후 과제
- [ ] OpenPose + Reference-only 조합 테스트
- [ ] 캐릭터 전용 LoRA 학습 검토
- [ ] Regional Prompter 확장 설치 및 테스트
- [ ] 장면 유형 자동 판단 로직 구현

---

## 10. 참고 파일 위치

```
backend/tests/
├── test_dialogue_composite.py    # 대화 장면 테스트
└── test_hug_composite.py         # 포옹/상호작용 테스트

backend/outputs/
├── dialogue_test/                # 대화 장면 결과
├── hug_test/                     # 포옹 장면 결과
│   ├── comparison/               # 3가지 방법 비교
│   ├── consistency/              # 일관성 테스트
│   └── chibi_poses_v2/           # 치비 포즈 테스트
```
