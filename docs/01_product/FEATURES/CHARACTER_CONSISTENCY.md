
# IP-Adapter 캐릭터 유사도 고도화

**상태**: 미착수
**우선순위**: 미정
**관련**: Phase 8 (Multi-Style)

---

## 현재 문제 (2026-02-21)

### 1. 동남아시아 느낌 — SD1.5 체크포인트 한계
- Realistic Vision v5.1에서 `korean` 태그가 정확히 반영되지 않음
- SD1.5 모델 자체의 아시아 얼굴 표현력 부족

### 2. 씬 간 얼굴 불일치
- 각 씬이 독립 생성 (seed 다름) → 같은 캐릭터도 씬마다 다른 얼굴
- FaceID weight 0.85 + "ControlNet is more important"로도 완전 일치 어려움
- SD 생성 이미지를 레퍼런스로 사용 시 InsightFace 임베딩이 불안정

### 3. 레퍼런스 이미지 품질
- SD 생성 이미지는 매번 미묘하게 다른 얼굴 → 레퍼런스 자체가 불안정
- 얼굴 클로즈업 크롭은 오히려 품질 저하 (해상도 열화)

## 개선 방향

### A. SDXL 기반 체크포인트 전환 (권장)
- SDXL 모델은 얼굴 표현력이 SD1.5보다 월등
- 한국인/동아시아 얼굴 특화 SDXL 체크포인트 탐색
- IP-Adapter SDXL 모델 (`ip-adapter-faceid_sdxl`) 사용
- **영향 범위**: SD WebUI 설정, ControlNet 모듈/모델 매핑, 해상도 변경 (1024x1536)

### B. 실사 인물 사진 레퍼런스 (즉시 적용 가능)
- SD 생성 이미지 대신 실제 스톡 사진/AI 포트레이트를 레퍼런스로 사용
- InsightFace가 실사 사진에서 더 안정적인 얼굴 임베딩 추출
- 정면 + 측면 멀티 레퍼런스 지원 검토

### C. 추가 튜닝
- FaceID weight 범위 실험 (0.85~1.2)
- `guidance_start`/`guidance_end` 조정 (초반 강하게, 후반 약하게)
- 프롬프트에서 얼굴 관련 태그 제거 (IP-Adapter와 충돌 방지)
- 한국인 특화 체크포인트 (majicmixRealistic 등) 테스트

## 현재 구현 상태

| 항목 | 값 |
|------|-----|
| IP-Adapter 모델 | `ip-adapter-faceid-plusv2_sd15` |
| Preprocessor | `ip-adapter_face_id_plus` (InsightFace) |
| Weight | 0.85 (캐릭터 DB 설정) |
| Control Mode | `ControlNet is more important` (faceid 전용) |
| 우선순위 | 캐릭터 > 스타일프로필 > 글로벌 기본값 |
| 체크포인트 | Realistic Vision v5.1 (SD1.5) |
