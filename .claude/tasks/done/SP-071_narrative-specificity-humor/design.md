## 상세 설계 (How)

### DoD-A: `_NARRATIVE_WEIGHTS`에 `situational_specificity` 차원 추가

**구현방법**:
`backend/services/agent/nodes/review.py`의 `_NARRATIVE_WEIGHTS` dict에 `situational_specificity: 0.10` 추가.
기존 `twist_payoff`를 0.10→0.05, `pacing_rhythm`을 0.10→0.05로 조정하여 합계 1.0 유지.

```python
_NARRATIVE_WEIGHTS = {
    "hook": 0.25,
    "emotional_arc": 0.15,
    "twist_payoff": 0.05,          # 0.10 → 0.05
    "speaker_tone": 0.05,
    "script_image_sync": 0.10,
    "spoken_naturalness": 0.15,
    "retention_flow": 0.10,
    "pacing_rhythm": 0.05,          # 0.10 → 0.05
    "situational_specificity": 0.10, # 신규
}
```

**동작 정의**:
- before: 8차원 가중 평균으로 overall 계산
- after: 9차원 가중 평균으로 overall 계산. `_build_narrative_score()`는 `_NARRATIVE_WEIGHTS` 키를 순회하므로 자동 반영됨

**엣지 케이스**:
- Gemini가 `situational_specificity` 필드를 누락하면 `NarrativeScoreOutput`의 기본값 0.0이 적용 → overall 하락 → revise 트리거 (의도된 동작)
- threshold(0.6) 조정 불필요 — 기존 차원 감소분과 신규 차원이 상쇄

**영향 범위**:
- `_build_narrative_score()`: `_NARRATIVE_WEIGHTS` 키 순회 → 자동 반영
- `test_narrative_review.py`: 가중치 합계 검증 테스트 + `_all_dimensions()` 헬퍼에 필드 추가 필요

**테스트 전략**:
- `sum(_NARRATIVE_WEIGHTS.values()) == 1.0` 검증
- 9차원 모두 1.0 → overall 1.0 검증
- `situational_specificity` 0.0이고 나머지 1.0 → overall 0.90 검증

**Out of Scope**: threshold(0.6) 변경, 기존 점수 마이그레이션

---

### DoD-B: `NarrativeScoreOutput`에 `situational_specificity` 필드 추가

**구현방법**:
1. `backend/services/agent/llm_models.py`의 `NarrativeScoreOutput`에 `situational_specificity: float = 0.0` 추가
2. `_clamp_scores()`의 `score_keys` 튜플에 `"situational_specificity"` 추가
3. `backend/services/agent/state.py`의 `NarrativeScore` TypedDict에 `situational_specificity: float` 추가

**동작 정의**:
- before: Gemini 응답에서 8개 float 필드 파싱
- after: 9개 float 필드 파싱. 누락 시 0.0 기본값

**엣지 케이스**:
- Gemini가 1.0 초과 반환 → `_clamp()` 자동 보정 (기존 로직)

**영향 범위**: `_parse_narrative_score()` → `model_validate()` → 자동 반영

**테스트 전략**:
- `NarrativeScoreOutput(situational_specificity=0.8)` 파싱 검증
- `_clamp` 범위 검증 (1.5 → 1.0)

**Out of Scope**: UnifiedReviewOutput 구조 변경 (SP-064 scope)

---

### DoD-C: LangFuse `pipeline/review/unified` 프롬프트 수정

**구현방법**:
LangFuse 웹 UI에서 `pipeline/review/unified` 프롬프트의 Narrative 평가 섹션에 추가:

```
- situational_specificity (0.0-1.0): 각 씬의 대사가 구체적 상황/행동/대상을 포함하는지 평가.
  - 1.0: 모든 씬이 구체적 상황을 묘사 ("짝짝이 구두 신고 왔잖아!")
  - 0.5: 일부 씬만 구체적, 나머지는 리액션만 ("내 발... 뭐지?")
  - 0.0: 대부분 감탄사/리액션만으로 구성, 상황 맥락 전무
```

JSON 응답 스키마의 narrative 섹션에 `"situational_specificity": float` 필드 추가.

**동작 정의**:
- before: Gemini가 8차원 점수 반환
- after: Gemini가 9차원 점수 반환 (situational_specificity 포함)

**엣지 케이스**: 프롬프트 업데이트 전 캐시된 버전 사용 → LangFuse 버전 발행 필요

**영향 범위**: Gemini 응답 토큰 소폭 증가 (~10 토큰)

**테스트 전략**: 수동 — 파이프라인 실행 후 LangFuse 트레이스에서 `situational_specificity` 필드 존재 확인

**Out of Scope**: 프롬프트 기존 차원 설명 수정

---

### DoD-D: LangFuse `creative/writer` 프롬프트 규칙 추가

**구현방법**:
LangFuse 웹 UI에서 `creative/writer` 프롬프트에 규칙 추가:

```
## 대사 구체성 규칙
- 대사는 반드시 구체적 상황, 행동, 대상을 포함해야 한다
- 감탄사/리액션만으로 구성된 대사 금지
- Bad: "내 발... 뭐지?" / "모니터엔... 헐!" / "에라 모르겠다!"
- Good: "짝짝이 구두 신고 왔잖아!" / "모니터에 어제 몰래 본 쇼핑몰이 떡!" / "버튼 10개 중에 아무거나 눌러봤다!"
```

**동작 정의**:
- before: Writer가 리액션만 나열한 대사 생성 가능
- after: Writer가 구체적 상황 포함 대사 생성 유도

**엣지 케이스**: 의도적으로 짧은 감탄사가 효과적인 씬(클라이맥스 등) → "연속 2씬 이상 감탄사만으로 구성 금지"로 완화

**영향 범위**: Writer 출력 품질 변화 → Review에서 자연스럽게 검증됨

**테스트 전략**: 수동 — 파이프라인 실행 후 생성된 대사에 구체적 상황 포함 여부 확인

**Out of Scope**: Writer Planning Step 로직 변경, Critic 프롬프트 변경

---

## 변경 파일 요약

| 파일 | 변경 내용 |
|------|----------|
| `backend/services/agent/nodes/review.py` | `_NARRATIVE_WEIGHTS` 가중치 재분배 + 신규 키 |
| `backend/services/agent/llm_models.py` | `NarrativeScoreOutput`에 필드 + `_clamp_scores` 키 추가 |
| `backend/services/agent/state.py` | `NarrativeScore` TypedDict에 필드 추가 |
| `backend/tests/test_narrative_review.py` | 가중치 합계 + 9차원 테스트 갱신 |
| LangFuse `pipeline/review/unified` | Narrative 평가 기준 추가 (코드 외) |
| LangFuse `creative/writer` | 대사 구체성 규칙 추가 (코드 외) |

변경 코드 파일 4개 (제약 충족).
