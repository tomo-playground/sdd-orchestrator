# 캐릭터 일관성 실험 가이드

AI 기반 쇼츠 제작에서 **캐릭터 일관성 유지** 및 **멀티 캐릭터 장면 생성** 방법을 실험합니다.

## 🎯 실험 목표

1. **단일 캐릭터 일관성**: 다양한 포즈/배경에서 캐릭터 외모 고정
2. **멀티 캐릭터 생성**: 2인 이상 장면 (대화, 상호작용)
3. **방법 비교**: Reference-only vs IP-Adapter vs 조합

## 📋 사전 준비

### 1. SD WebUI 실행
```bash
# API 모드로 실행 필수
cd stable-diffusion-webui
./webui.sh --api

# 확인: http://localhost:7860 접속
```

### 2. ControlNet 확장 설치
SD WebUI Extensions 탭에서:
- ControlNet (필수)
- IP-Adapter models 다운로드 (선택)

필요한 모델:
- `control_v11p_sd15_openpose.pth`
- `ip-adapter-plus_sd15.safetensors` (IP-Adapter 사용 시)

### 3. LoRA 준비
`stable-diffusion-webui/models/Lora/` 폴더에 캐릭터 LoRA 배치:
- `eureka_v9.safetensors` (예시)
- 또는 사용 가능한 다른 캐릭터 LoRA

## 🧪 실험 1: 단일 캐릭터 일관성

### 목적
다양한 포즈/배경에서 캐릭터 외모(얼굴, 헤어, 의상) 일관성 유지

### 실행
```bash
cd backend
python -m tests._experimental_character_consistency
```

### 생성 파일
```
outputs/consistency_test/
├── 1_base_fullbody.png          # 기준 이미지 (전신)
├── 2_ref_standing.png           # Reference-only 결과
├── 2_ref_walking.png
├── 2_ref_sitting.png
├── 2_ref_running.png
├── 3_ip_standing.png            # IP-Adapter 결과
├── 3_ip_walking.png
├── 3_ip_sitting.png
├── 3_ip_running.png
├── 4_combo_standing.png         # 조합 (Ref + IP) 결과
├── 4_combo_walking.png
├── 4_combo_sitting.png
└── 4_combo_running.png
```

### 비교 기준
| 기준 | Reference-only | IP-Adapter | 조합 |
|------|---------------|------------|------|
| **얼굴 일관성** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **전신 스타일** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **포즈 자유도** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **실험 평가** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | (미검증) |

### 분석 포인트
1. **기준 이미지 대비 일관성**:
   - 얼굴: 눈 색상, 헤어스타일, 표정
   - 의상: 교복, 액세서리
   - 스타일: 전체적인 그림체

2. **포즈 변화 자유도**:
   - 앉기/서기/걷기/달리기 모두 자연스러운가?
   - 기준 이미지 포즈에 과도하게 고정되지 않는가?

3. **배경 적용**:
   - 프롬프트의 배경(library)이 잘 반영되는가?

## 🧪 실험 2: 멀티 캐릭터 생성

### 목적
2인 이상 장면 생성 (상호작용, 대화)

### 실행
```bash
cd backend
python -m tests._experimental_multi_character
```

### 생성 파일
```
outputs/multi_char_test/
├── 1_interaction_hug.png        # 포옹 (단일 생성)
├── 1_interaction_hands.png      # 손잡기
├── 2_dialogue_left.png          # 대화 - 왼쪽 캐릭터
├── 2_dialogue_right.png         # 오른쪽 캐릭터
├── 2_dialogue_composite.png     # 합성 결과
└── 3_lora_combo.png             # 다중 LoRA 조합
```

### 시나리오별 평가

#### Scenario 1: 상호작용 (포옹, 손잡기)
**방법**: 단일 이미지 생성 (`2girls, hug`)

**장점**:
- ✅ 자연스러운 신체 접촉
- ✅ 조명/그림자 일관성
- ✅ 빠른 생성

**단점**:
- ❌ 캐릭터별 LoRA 완전 분리 어려움
- ❌ LoRA weight 분산 → 특징 약화

**분석**:
- 2인이 명확히 구분되는가?
- 포옹/손잡기 동작이 자연스러운가?

#### Scenario 2: 대화 (좌우 배치)
**방법**: 분리 생성 + 합성

**장점**:
- ✅ 캐릭터별 LoRA 완전 분리
- ✅ 각 캐릭터 seed 고정 가능

**단점**:
- ❌ 합성 경계 부자연스러움 가능
- ❌ 배경 제거(rembg) 필요
- ❌ 후처리 복잡

**분석**:
- 합성 경계가 눈에 띄는가?
- 배경 일관성이 유지되는가?

#### Scenario 3: LoRA 조합
**방법**: 2개 LoRA 동시 사용

**제약**:
- 같은 LoRA 2번 사용 시 효과 없음
- 다른 LoRA 필요 (예: `eureka_v9` + `mha_midoriya-10`)

**분석**:
- 각 캐릭터 특징이 혼합되는가?
- 두 캐릭터가 구분 가능한가?

## 📊 실험 결과 정리

### 실험 완료 체크리스트
- [ ] 단일 캐릭터: Reference-only 결과 확인
- [ ] 단일 캐릭터: IP-Adapter 결과 확인
- [ ] 단일 캐릭터: 조합 결과 확인
- [ ] 멀티 캐릭터: 상호작용 장면 확인
- [ ] 멀티 캐릭터: 대화 장면 합성 확인
- [ ] 멀티 캐릭터: LoRA 조합 확인

### 결과 기록 템플릿

```markdown
## 실험 결과

### 환경
- SD WebUI 버전:
- ControlNet 버전:
- LoRA:
- 실행 시간:

### 단일 캐릭터
**Reference-only**:
- 얼굴 일관성: ⭐⭐⭐⭐⭐ (5점 만점)
- 전신 스타일: ⭐⭐⭐⭐⭐
- 포즈 자유도: ⭐⭐⭐⭐
- 코멘트:

**IP-Adapter**:
- 얼굴 일관성:
- 전신 스타일:
- 포즈 자유도:
- 코멘트:

**조합**:
- 얼굴 일관성:
- 전신 스타일:
- 포즈 자유도:
- 코멘트:

**최종 판단**: (어떤 방법이 가장 좋았는가?)

### 멀티 캐릭터
**상호작용 장면**:
- 자연스러움: ⭐⭐⭐⭐⭐
- 캐릭터 구분:
- 코멘트:

**대화 장면**:
- 합성 품질:
- 배경 일관성:
- 코멘트:

**LoRA 조합**:
- 특징 보존:
- 코멘트:

**최종 판단**: (어떤 방법을 프로덕션에 사용할 것인가?)
```

## 🚀 다음 단계

### 실험 성공 시
1. **프로덕션 통합**:
   - `services/generation.py`에 Reference-only 추가
   - Frontend UI에 옵션 추가
   - API 엔드포인트 확장

2. **자동화**:
   - 캐릭터 기준 이미지 자동 생성
   - 장면 유형 자동 판단 (상호작용 vs 대화)
   - 최적 방법 자동 선택

3. **고도화**:
   - OpenPose 참조 이미지 추출
   - rembg 통합 (배경 제거)
   - Regional Prompter 테스트

### 실험 실패 시
**문제 진단**:
- [ ] SD WebUI API 미실행
- [ ] ControlNet 확장 미설치
- [ ] LoRA 파일 없음
- [ ] Reference 이미지 품질 문제

**해결 방법**:
1. SD WebUI 로그 확인 (`terminal에서 확인`)
2. ControlNet 모델 다운로드 상태 확인
3. LoRA 경로 및 파일명 확인
4. 기준 이미지 수동 생성 및 교체

## 📚 참고 문서

- `docs/reports/CHARACTER_RENDERING_REPORT.md`: 기존 실험 리포트
- `docs/PRD.md`: 제품 요구사항 (v2.x Backlog)
- `backend/services/controlnet.py`: ControlNet 함수 정의
- `backend/config.py`: 캐릭터 프리셋 설정

## 💬 피드백

실험 결과를 공유하고 다음 단계를 논의하세요:
1. 어떤 방법이 가장 효과적이었나요?
2. 프로덕션에 바로 적용 가능한가요?
3. 추가 실험이 필요한 부분은?
