# V3 Experiment Results Archive

> 이 문서는 ROADMAP.md에서 분리된 실험 결과 상세 기록입니다.

---

## Phase 6-4.22: Gemini Image Editing - 실험 결과

### Gemini Nano Banana 테스트 (2026-01-27)

**테스트 환경**:
- Model: `gemini-2.5-flash-image` (Google AI Studio)
- Cost: $0.0401/edit ($0.0011 input + $0.039 output)
- Test Character: Eureka (chibi style)

### Phase 1: Pose Editing

| Test Case | Target Change | Visual Result | WD14 Evaluation | Cost |
|-----------|---------------|---------------|-----------------|------|
| Standing → Sitting | "sitting on chair with hands on lap" | Perfect | Partial (66.7%) | $0.0404 |
| Neutral → Waving | "waving with right hand raised" | Perfect | Failed (0%) | $0.0404 |

**핵심 발견**:
- 시각적 성공률: 100% (2/2) - 포즈 변경 정확, 얼굴/화풍 완벽 보존
- WD14 평가: 50% - WD14의 한계로 확인 (실제로는 성공)
- 비용: $0.0808 (2 edits) - 예상 월 비용 $2.40 (10 scenes/day x 20% failure)

### Phase 1.5: Expression & Gaze Editing

| Test Case | Category | Visual Result | WD14 Evaluation | Cost |
|-----------|----------|---------------|-----------------|------|
| Front → Looking Back | Gaze | Perfect | Success (100%) | $0.0404 |
| Smiling → Frowning | Expression | Good | Partial (33.3%) | $0.0404 |
| Neutral → Surprised | Expression | Good | Partial (50%) | $0.0404 |

**핵심 발견**:
- Gaze Editing: 완벽! WD14 평가 100%
- Expression Editing: 시각적 성공하나 WD14 한계 재확인
- 총 비용: $0.1212 (3 edits)

### Phase 1.7: 자동 제안 + 수동 승인

**구현 완료 (2026-01-27)**:
- `suggest_edit_from_prompt()` - Gemini Vision 프롬프트/이미지 비교 분석
- `/scene/suggest-edit` API - 불일치 감지 → 편집 제안 자동 생성
- Frontend "Auto Suggest" 버튼 - 제안 모달 + 승인 워크플로우

**실제 결과**:
- 자동 제안 성공: 3개 제안 정확 감지 (Expression, Pose, Hands)
- 신뢰도 표시: confidence score (90%, 100%, 100%)
- 비용: Vision API $0.0003 + Edit $0.0404 = $0.0407/edit

### Generation Log 실패 패턴 분석 (60개 케이스)

| Category | 발생 빈도 | Priority |
|----------|-----------|----------|
| Pose/Action | 34회 (57%) | Implemented |
| Expression | 17회 (28%) | High |
| Gaze Direction | ~10회 (17%) | High |
| Framing | 20회 (33%) | Medium |
| Hand Poses | ~8회 (13%) | Medium |

### 성공 지표 (KPI)

| 지표 | 현재 | Phase 1 | Phase 2 목표 | Phase 3 목표 |
|------|------|---------|--------------|--------------|
| 시각적 성공률 | 80% | 92% | 95% | 98% |
| 실패율 (< 70%) | 20% | 10% | 5% | 2% |
| 월 Gemini 비용 | $0 | $70-130 | $30-50 | $5-10 |

### 테스트 결과 파일
- `test_results/vertex_imagen/20260127_154138/`
- Test Script: `backend/scripts/test_gemini_nano_banana.py`

---

## Phase 6-4.23: Character Consistency - 실험 결과

### Single Character Consistency (90% 성공)
- Reference-only ControlNet: Weight 0.75-0.9, guidance_end 1.0
- 최적 파라미터: LoRA 0.6 + Reference 0.75
- 복장/얼굴/머리 일관성 유지 확인

### Multi-Character Consistency (90% 성공)
- 2인 상호작용: 단일 생성 방식 권장 (포옹, 손잡기)
- 대화 장면: 분리 생성 + 합성 방식
- eureka_v9 LoRA 사용 불가 판정 → Reference-only로 충분

### Character Prompt SSOT & Reference Fields (완료 2026-01-27)
- Character Edit Modal = Single Source of Truth
- DB: `reference_base_prompt`, `reference_negative_prompt` 필드 추가
- controlnet.py 하드코딩 제거 → config.py 상수 사용

### Character Tag Auto-Suggestion (완료 2026-01-27)
- `/characters/suggest-tags` API (Base Prompt → DB 태그 매칭)
- Frontend: onBlur 자동 제안 + "Add All" / "Ignore" UI
- 카테고리별 그룹핑 (identity vs clothing)

### 실험 결과 파일
- `outputs/clothing_test/` - 복장 일관성 90% 성공
- `outputs/multi_char_test/` - 멀티 캐릭터 90% 성공
- `outputs/character_presets/` - Generic 캐릭터 프리셋
