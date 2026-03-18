# Phase 37: Korean Script Quality (한국어 대본 품질 강화)

**상태**: 완료
**착수일**: 2026-03-18
**목표**: TTS 낭독 자연스러움 + 문장 간 맥락 연결 강화

---

## 배경

대본 생성 후 2가지 품질 문제:
1. **구어체 비자연 표현**: "뭐라고"→"뭐로" 같은 어색한 조사/어미 → TTS 낭독 부자연스러움
2. **문장 간 맥락 연결**: 씬 사이 흐름 끊김, 감정 전환 급격

현재 Writer→Review→Revise 루프에 한국어 자연스러움 검증 **없음**.
`build_korean_rules_block()` dead code 상태.

## Sprint 구성

### Sprint 1: Writer 프롬프트 한국어 구어체 강화
| # | 항목 | 파일 |
|---|------|------|
| 1-1 | `build_korean_rules_block()` 내용 강화 (TTS 최적화, 조사/어미, 블랙리스트, 맥락 연결) | `prompt_builders_writer.py` |
| 1-2 | Writer 노드에서 한국어 규칙 변수 연결 (dead code 활성화) | `nodes/writer.py` |
| 1-3 | LangFuse storyboard 4종에 `{{korean_rules_block}}` 삽입 | LangFuse |

### Sprint 2: Review에 korean_naturalness 평가 차원 추가
| # | 항목 | 파일 |
|---|------|------|
| 2-1 | NarrativeScore에 `korean_naturalness` 필드 추가 | `state.py`, `llm_models.py` |
| 2-2 | `_NARRATIVE_WEIGHTS` 한국어/기본 조건부 재배분 | `nodes/review.py` |
| 2-3 | 규칙 기반 한국어 검증 함수 추가 | `nodes/_review_validators.py` |
| 2-4 | LangFuse review 2종에 korean_naturalness 평가 기준 추가 | LangFuse |

### Sprint 3: Revise 한국어 피드백 루프
| # | 항목 | 파일 |
|---|------|------|
| 3-1 | `_build_feedback()` 한국어 자연스러움 피드백 주입 | `nodes/revise.py` |
| 3-2 | Tier 3 재생성 시 한국어 피드백 포함 | `nodes/revise.py` |

### Sprint 4: 테스트
| # | 항목 |
|---|------|
| 4-1 | `_NARRATIVE_WEIGHTS` 합계 1.0 검증 (한국어/기본) |
| 4-2 | `_validate_korean_naturalness()` 단위 테스트 |
| 4-3 | `_build_feedback()` 한국어 피드백 포함 검증 |
| 4-4 | `_build_narrative_score()` 한국어/비한국어 분기 검증 |

---

## 완료 기준 (DoD)
- [ ] Writer가 한국어 구어체 규칙을 적용하여 대본 생성
- [ ] Review에서 korean_naturalness 점수 산출 (한국어일 때)
- [ ] Revise에서 낮은 korean_naturalness 시 구체적 피드백 포함
- [ ] 테스트 전체 PASS
