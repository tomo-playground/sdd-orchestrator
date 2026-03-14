# SD1.5 vs NoobAI-XL 비교 테스트 계획

**작성일**: 2026-03-14
**목적**: 숏폼 영상 제작에 "프롬프트 기반으로 정확한 장면을 만들 수 있는가" 검증

---

## 1. 테스트 대상

| ID | 체크포인트 | 베이스 | 해상도 | CFG 권장 | Sampler |
|----|-----------|--------|--------|---------|---------|
| A | anyloraCheckpoint (SD1.5) | SD1.5 | 512x768 | 7.0 | DPM++ 2M Karras |
| B | NoobAI-XL V-Pred | SDXL | 832x1216 | 4.0~5.5 | Euler |
| C | NoobAI-XL Epsilon | SDXL | 832x1216 | 5.0~7.0 | DPM++ 2M Karras |

---

## 2. 점수 기준 (1-5점)

| 점수 | 등급 | 정의 |
|------|------|------|
| 5 | Excellent | 의도와 완벽히 일치. 수정 불필요 |
| 4 | Good | 의도 대부분 반영. 사소한 차이만 존재 |
| 3 | Acceptable | 의도를 인식할 수 있으나 눈에 띄는 차이. 사용 가능 |
| 2 | Poor | 의도 일부만 반영. 재생성 필요 |
| 1 | Fail | 의도와 무관하거나 파손. 사용 불가 |

**합격**: 항목 평균 3.5+ (실용), 4.0+ (전환 권장)

---

## 3. 테스트 단계 (Gate 방식)

### Phase 1: 기본 호환성 (Gate — 실패 시 중단)

#### TEST 1-1: VRAM 사용량

| 조합 | A (SD1.5) | B (V-Pred) | C (Epsilon) |
|------|-----------|------------|-------------|
| txt2img only (28 steps) | __ GB | __ GB | __ GB |
| + ControlNet OpenPose | __ GB | __ GB | __ GB |
| + IP-Adapter | __ GB | __ GB | __ GB |
| + ControlNet + IP-Adapter | __ GB | __ GB | __ GB |
| OOM 발생 여부 | Y/N | Y/N | Y/N |

**Gate 조건**: VRAM 14GB 이하

#### TEST 1-2: 태그 호환성

| 카테고리 | 테스트 태그 | A | B | C |
|---------|-----------|---|---|---|
| 기본 외모 | `1girl, black_hair, blue_eyes, long_hair` | /5 | /5 | /5 |
| 표정 | `smile, closed_eyes, crying, angry` | /5 | /5 | /5 |
| 시선 | `looking_at_viewer, looking_away, looking_down` | /5 | /5 | /5 |
| 카메라 | `cowboy_shot, close-up, from_above, from_below` | /5 | /5 | /5 |
| 포즈 | `arms_crossed, hands_on_hips, sitting, running` | /5 | /5 | /5 |
| 치비 | `chibi, super_deformed, big_head, small_body` | /5 | /5 | /5 |
| 언더바 형식 | `black_hair, blue_eyes` | /5 | /5 | /5 |
| 공백 형식 | `black hair, blue eyes` | /5 | /5 | /5 |

**Gate 조건**: 주요 태그 80% 이상 반영

#### TEST 1-3: 생성 속도

| 조건 | A | B | C |
|------|---|---|---|
| 28 steps, txt2img | __ 초 | __ 초 | __ 초 |
| 28 steps + ControlNet | __ 초 | __ 초 | __ 초 |
| 28 steps + IP-Adapter | __ 초 | __ 초 | __ 초 |

**Gate 조건**: 30초 이내

---

### Phase 2: 프롬프트 품질 (Core)

#### TEST 2-1: 프롬프트 정확도 (5씬, 각 3장, seed 고정)

| 씬 | 프롬프트 | 평가 포인트 |
|----|---------|------------|
| S1 학교 고백 | `1girl, black_hair, school_uniform, blush, looking_away, cherry_blossoms, sunset, cowboy_shot` | 감정+환경 동시 |
| S2 전투 | `1boy, spiky_hair, armor, sword, fighting_stance, dynamic_pose, fire, ruins, night, full_body` | 동적 포즈+배경 |
| S3 카페 | `1girl, brown_hair, glasses, sitting, coffee_cup, cafe_interior, warm_lighting, upper_body` | 소품+조명 |
| S4 감정 | `1girl, silver_hair, crying, tears, close-up, dark_background, dramatic_lighting` | 감정 디테일 |
| S5 코믹 | `1boy, surprised, sweatdrop, exaggerated_expression, chibi, simple_background` | 과장 표현 |

**씬별 평가표**:

| 씬 | 세부 | A | B | C |
|----|------|---|---|---|
| S1 | 감정 (blush+looking_away) | /5 | /5 | /5 |
| S1 | 환경 (cherry_blossoms+sunset) | /5 | /5 | /5 |
| S2 | 동적 포즈 | /5 | /5 | /5 |
| S2 | 장비 (armor+sword) | /5 | /5 | /5 |
| S2 | 배경 (fire+ruins) | /5 | /5 | /5 |
| S3 | 소품 (glasses+coffee) | /5 | /5 | /5 |
| S3 | 분위기 (cafe+sunlight) | /5 | /5 | /5 |
| S4 | 감정 (tears) | /5 | /5 | /5 |
| S4 | 조명 (dramatic) | /5 | /5 | /5 |
| S5 | 이모트 (sweatdrop) | /5 | /5 | /5 |
| S5 | 치비/과장 | /5 | /5 | /5 |

#### TEST 2-2: 복장/소품 정확도

| 테스트 | 프롬프트 핵심 | A | B | C |
|--------|-------------|---|---|---|
| 교복 | `serafuku, pleated_skirt, knee_highs` | /5 | /5 | /5 |
| 갑옷 | `plate_armor, gauntlets, cape` | /5 | /5 | /5 |
| 캐주얼 | `hoodie, jeans, sneakers, backpack` | /5 | /5 | /5 |
| 색상 지정 | `red_dress, white_gloves, black_boots` | /5 | /5 | /5 |

#### TEST 2-3: 배경/환경

| 환경 | 핵심 | A | B | C |
|------|------|---|---|---|
| 도시 야경 | 네온+빗물 반사 | /5 | /5 | /5 |
| 자연 | 숲+강+하늘 공존 | /5 | /5 | /5 |
| 실내 | 가구 배치 자연스러움 | /5 | /5 | /5 |
| 판타지 | 비현실 요소 | /5 | /5 | /5 |

#### TEST 2-4: 멀티캐릭터

| 시나리오 | 핵심 | A | B | C |
|---------|------|---|---|---|
| 대화 (2girls) | 2인 분리, 시선 | /5 | /5 | /5 |
| 대립 (1boy+1girl) | 성별 구분, 포즈 | /5 | /5 | /5 |
| 외모 차이 | 개별 외모 적용 | /5 | /5 | /5 |

---

### Phase 3: 캐릭터 파이프라인 (Integration)

#### TEST 3-1: ControlNet 포즈

| 포즈 | A | B | C |
|------|---|---|---|
| standing_neutral | /5 | /5 | /5 |
| arms_crossed | /5 | /5 | /5 |
| sitting | /5 | /5 | /5 |
| waving | /5 | /5 | /5 |
| from_behind | /5 | /5 | /5 |

#### TEST 3-2: IP-Adapter 반영도

| 시나리오 | A | B | C |
|---------|---|---|---|
| 얼굴 유사도 | /5 | /5 | /5 |
| 프롬프트 vs 레퍼런스 우선순위 | /5 | /5 | /5 |
| 포즈 변경 시 얼굴 유지 | /5 | /5 | /5 |
| weight 민감도 (0.3/0.5/0.7) | /5 | /5 | /5 |

#### TEST 3-3: 캐릭터 일관성 (LoRA 없는 상황)

| 시나리오 | A (LoRA+IPA) | B (IPA only) | C (IPA only) |
|---------|-------------|-------------|-------------|
| 동일 프롬프트 5장 동일인 | /5 | /5 | /5 |
| 포즈 변경 시 동일인 | /5 | /5 | /5 |
| 의상 변경 시 동일인 | /5 | /5 | /5 |
| 표정 변경 시 동일인 | /5 | /5 | /5 |

---

### Phase 4: 종합 E2E (5씬 스토리보드 시뮬레이션)

**시나리오**: "학교 일상" — 1캐릭터, 5씬

| 씬 | 설정 | ControlNet |
|----|------|-----------|
| 1. 등교 | walking, school_gate, morning | standing |
| 2. 수업 | sitting, classroom, bored | sitting |
| 3. 점심 | eating, cafeteria, smile | sitting |
| 4. 방과후 | standing, rooftop, sunset, wind | standing |
| 5. 귀가 | walking, from_behind, evening | from_behind |

| 평가 | A | B | C |
|------|---|---|---|
| 5씬 캐릭터 일관성 | /5 | /5 | /5 |
| 의상 일관성 | /5 | /5 | /5 |
| 배경 다양성 | /5 | /5 | /5 |
| 프롬프트-장면 일치도 | /5 | /5 | /5 |
| 숏폼 사용 적합성 | /5 | /5 | /5 |

---

## 4. 가중치 및 의사결정

| 항목 | 가중치 |
|------|--------|
| 프롬프트 정확도 | 25% |
| 캐릭터 일관성 | 20% |
| ControlNet 포즈 | 15% |
| IP-Adapter 반영도 | 10% |
| VRAM 사용량 | 10% |
| 생성 속도 | 5% |
| 태그 호환성 | 5% |
| 복장/소품 | 5% |
| 배경/환경 | 3% |
| 멀티캐릭터 | 2% |

### 의사결정

| 결과 | 결론 |
|------|------|
| NoobXL >= 4.0 AND SD1.5 < 3.5 | **즉시 전환** |
| NoobXL >= 3.5 AND 비슷 | LoRA 훈련 후 재평가 |
| NoobXL < 3.5 | SD1.5 유지 |

---

## 5. 필요 리소스

### 다운로드
- [ ] NoobAI-XL V-Pred (Civitai 833294, ~6.6GB)
- [ ] NoobAI-XL Epsilon (Civitai 833294, ~6.6GB)
- [ ] ControlNet OpenPose SDXL (`thibaud/controlnet-openpose-sdxl-1.0`)
- [ ] IP-Adapter Plus Face SDXL (`ip-adapter-plus-face_sdxl_vit-h`)

### A1111 설정
- [ ] V-Pred용 yaml config
- [ ] `--medvram-sdxl` 플래그 추가
- [ ] ControlNet/IP-Adapter 확장 SDXL 호환 확인

### 테스트 데이터
- [ ] 레퍼런스 이미지 3장
- [ ] 포즈 에셋 5종
- [ ] 고정 시드: 42, 1234, 5678, 9999, 31415

---

## 6. 전환 시 코드 영향도

| 파일 | 변경 내용 |
|------|----------|
| `config.py` | 해상도, CFG, sampler 기본값 |
| `generation.py` | Hi-Res 비활성화 |
| `controlnet.py` | SDXL용 모델명 매핑 |
| `style_context.py` | V-Pred/Epsilon 분기 |
| StyleProfile DB | 체크포인트, 임베딩, 파라미터 |
| LoRA DB | 12명 SDXL용 재학습 |
