# Phase 37: Korean Script Quality (한국어 대본 품질 강화)

**상태**: 완료
**착수일**: 2026-03-18
**목표**: TTS 낭독 자연스러움 + 씬 간 맥락 연결 + 시각적 연출 다양성

---

## 배경

대본 생성 후 3가지 품질 문제:
1. **구어체 비자연 표현**: "죽었습니다" 같은 AI톤, "뭐로" 같은 어색한 조사 → TTS 낭독 부자연스러움
2. **문장 간 맥락 연결**: 씬 사이 흐름 끊김, 말줄임표(...) 9/11씬 반복
3. **시각적 연출 단조로움**: 모든 씬이 "대화하는 얼굴 클로즈업" → 카페 입장/퇴장, 오브젝트 샷 없음

## Sprint 구성

### Sprint 1: Writer 프롬프트 한국어 구어체 강화
| # | 항목 | 파일 |
|---|------|------|
| 1-1 | `build_korean_rules_block()` dead code 활성화 + TTS/맥락 규칙 | `prompt_builders_writer.py` |
| 1-2 | Writer 노드에서 `korean_rules_block` 변수 연결 | `gemini_generator.py` |
| 1-3 | LangFuse storyboard 4종에 `{{korean_rules_block}}` 삽입 | LangFuse |

### Sprint 2: Review 8차원 숏폼 품질 평가 (업계 표준 OpusClip 기반)
기존 5차원 → 8차원:

| 차원 | 가중치 | 신규 |
|------|--------|------|
| hook | 25% | |
| emotional_arc | 15% | |
| twist_payoff | 10% | |
| speaker_tone | 5% | |
| script_image_sync | 10% | |
| **spoken_naturalness** | **15%** | ✅ TTS 낭독 자연스러움, AI톤 감지 |
| **retention_flow** | **10%** | ✅ 씬→씬 호기심 연결 |
| **pacing_rhythm** | **10%** | ✅ 템포/리듬 변화, 단조로움 감지 |

변경 파일: `state.py`, `llm_models.py`, `review.py`, `revise.py`, LangFuse review 2종

### Sprint 3: Revise 피드백 루프
- `_build_feedback()`에서 낮은 점수(< 0.5) 차원별 구체적 피드백 자동 주입
- Sprint 2 코드에서 완료

### Sprint 4: 테스트
- 16개 테스트: 가중치 합계, 파싱, 클램핑, 후방 호환, overall 계산, 피드백 주입

### Sprint 5: stage_direction (시각적 지문) 도입
**문제**: Writer는 대사만, Cinematographer는 "대사하는 얼굴"만 → 시각적 다양성 없음
**해결**: Writer가 **시각적 지문(stage_direction)**을 함께 생성 → Cinematographer가 참조하여 다양한 연출

| # | 항목 | 변경 |
|---|------|------|
| 5-1 | storyboard 4종에 `stage_direction` 필드 + 예시 추가 | LangFuse storyboard 4종 |
| 5-2 | Cinematographer Rule 0에 stage_direction 참조 규칙 | LangFuse cinematographer |
| 5-3 | Finalize → Cinematographer 전달 | 자동 (json.dumps scenes) |

**stage_direction 예시**:
```json
{
  "script": "헐, 내 데이터…!",
  "speaker": "A",
  "stage_direction": "카페 문을 열고 들어서며 주문 화면의 AI 닉네임을 보고 놀란다"
}
```

→ Cinematographer: establishing shot (full_body) + object shot (close-up 주문화면)

---

## 완료 기준 (DoD)
- [x] Writer가 한국어 구어체 규칙 적용 + stage_direction 생성
- [x] Review 8차원 평가 (spoken_naturalness, retention_flow, pacing_rhythm)
- [x] Revise에서 낮은 점수 시 구체적 피드백 포함
- [x] Cinematographer가 stage_direction 기반 다양한 연출
- [x] 테스트 16개 PASS
- [x] 검증: #1121(Before) → #1123(After) 대본 품질 개선 확인
