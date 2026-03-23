# SP-064 상세 설계 (How)

## 현재 구조 요약

- **Review 통합 호출**: `_unified_evaluate()` → LangFuse `pipeline/review/unified` 프롬프트 → Gemini가 `UnifiedReviewOutput` JSON 반환
- **UnifiedReviewOutput** = `{ technical: TechnicalEvaluation, narrative: NarrativeScoreOutput, reflection: ReflectionOutput | None }`
- `TechnicalEvaluation`에는 이미 `scene_issues: list[dict]`가 존재 (기술 이슈용)
- `NarrativeScoreOutput`에는 `scene_issues` 없음 — aggregate 점수 + feedback 문자열만 존재
- **Revise `_build_feedback()`**: `narrative_score.feedback` 문자열과 차원별 0.5 미만 경고만 전달. 씬 번호 정보 없음
- **LangFuse 프롬프트 (v6)**: Narrative 섹션에 "feedback에 씬 번호와 개선 방향 포함" 지시는 있으나, 구조화된 `scene_issues` 필드 출력 지시는 없음

---

## DoD 1: NarrativeScoreOutput에 scene_issues 추가

### 구현 방법
1. `backend/services/agent/llm_models.py`의 `NarrativeScoreOutput`에 `scene_issues: list[dict] = []` 필드 추가
2. `backend/services/agent/state.py`의 `NarrativeScore` TypedDict에 `scene_issues: list[dict]` 필드 추가
3. `backend/services/agent/nodes/review.py`의 `_build_narrative_score()`에서 `parsed.scene_issues`를 `NarrativeScore`에 전달

### 동작 정의
- Gemini가 `narrative.scene_issues` 배열을 반환하면 파싱하여 `NarrativeScore["scene_issues"]`에 저장
- 각 항목 형식: `{"scene_id": int, "issue": str, "dimension": str, "severity": "error"|"warning"}`
  - `scene_id`: 1-based 씬 번호
  - `issue`: 문제 설명 (한국어)
  - `dimension`: 8개 차원 중 하나 (hook, emotional_arc, twist_payoff, speaker_tone, script_image_sync, spoken_naturalness, retention_flow, pacing_rhythm) + 신규 "transition" (전환 자연성)
  - `severity`: `"error"` (반드시 수정) 또는 `"warning"` (권장 수정)
- Gemini가 `scene_issues`를 빈 배열 또는 누락으로 반환해도 기본값 `[]`로 안전하게 처리 (Pydantic default)

### 엣지 케이스
- **Gemini가 scene_issues를 null로 반환**: Pydantic `model_validator`에서 `None` → `[]` 변환 추가 (또는 기본값으로 커버)
- **scene_id가 범위 밖** (0 또는 씬 개수 초과): 파싱 시 필터링하지 않음 — Revise에서 피드백 문자열로 변환만 하므로 무해. 로그 경고만 출력
- **dimension이 알 수 없는 값**: 허용 (strict enum 적용 안 함). Gemini 출력 유연성 보장
- **레거시 폴백 경로** (`_narrative_evaluate` → `_parse_narrative_score`): 레거시 프롬프트 `pipeline/review/narrative`에는 scene_issues 지시가 없으므로 빈 배열로 유지. 후방 호환

### 영향 범위
- `llm_models.py`: NarrativeScoreOutput 필드 추가 (기존 테스트에 `scene_issues` 없어도 기본값 `[]`이므로 호환)
- `state.py`: NarrativeScore TypedDict 필드 추가 (TypedDict `total=False`이므로 optional)
- `review.py`: `_build_narrative_score()` 수정 — scene_issues 전달 로직 1줄 추가
- 기존 테스트: `NarrativeScoreOutput` 생성 시 `scene_issues` 미지정해도 기본값 처리되므로 regression 없음

### 테스트 전략
- **단위 테스트**: `_build_narrative_score()`가 `scene_issues`를 올바르게 NarrativeScore에 전달하는지 검증
  - 입력: `NarrativeScoreOutput(scene_issues=[{"scene_id": 3, "issue": "Hook 약함", "dimension": "hook", "severity": "error"}], ...)`
  - 기대: 반환 NarrativeScore에 동일 scene_issues 존재
- **단위 테스트**: `scene_issues` 미지정(기본값) 시 빈 배열 반환 검증

### Out of Scope
- scene_issues에 대한 Pydantic 엄격 검증 (scene_id 범위, dimension enum). Gemini 출력 유연성 우선

---

## DoD 2: LangFuse 프롬프트 Narrative 섹션에 scene_issues 지시 추가

### 구현 방법
1. LangFuse `pipeline/review/unified` 프롬프트 v7 생성
2. Section 2 (Narrative Quality Scoring) 하단에 scene_issues 출력 지시 추가
3. Response Format의 `narrative` 객체에 `scene_issues` 필드 예시 추가

### 동작 정의
프롬프트에 추가할 지시문:

```
## Per-Scene Narrative Issues

For EACH dimension scored below 0.7, identify specific scenes causing the low score.
Output these in `narrative.scene_issues` array:
- scene_id: 1-based scene number
- issue: Concrete problem description in Korean
- dimension: Which narrative dimension this affects
- severity: "error" (score < 0.4) or "warning" (0.4 <= score < 0.7)

Focus on actionable, scene-specific feedback that Revise node can use.
```

Response Format 변경:
```json
"narrative": {
    ...existing fields...,
    "scene_issues": [
      {"scene_id": 2, "issue": "감정 전환이 너무 급격함", "dimension": "emotional_arc", "severity": "warning"},
      {"scene_id": 1, "issue": "Hook이 일반적인 서술로 시작", "dimension": "hook", "severity": "error"}
    ]
}
```

### 엣지 케이스
- **모든 차원이 0.7 이상**: scene_issues가 빈 배열. Gemini에 "If all dimensions >= 0.7, scene_issues may be empty" 명시
- **1씬짜리 스토리보드**: 전환 평가 불가. 자연스럽게 transition 관련 scene_issues 없음

### 영향 범위
- LangFuse 프롬프트만 변경. 코드 변경 없음
- Gemini 출력 토큰 소폭 증가 (scene_issues 배열 추가)

### 테스트 전략
- 통합 테스트에서 mock Gemini 응답에 scene_issues 포함하여 파싱 검증 (DoD 1 테스트와 통합)
- 실제 Gemini 호출은 수동 검증 (LangFuse 트레이싱으로 확인)

### Out of Scope
- 레거시 `pipeline/review/narrative` 프롬프트 수정. 통합 경로(unified)만 수정

---

## DoD 3: 전환 자연성 평가 지시 추가

### 구현 방법
1. DoD 2의 LangFuse 프롬프트 수정과 함께 수행
2. Section 2 하단, Per-Scene Narrative Issues 지시 직전에 전환 자연성 평가 지시 추가

### 동작 정의
프롬프트에 추가할 지시문:

```
## Scene Transition Evaluation

Evaluate naturalness of transitions between adjacent scenes (N -> N+1):
- Script tone/topic continuity
- Emotional progression coherence
- Visual context consistency (does image_prompt flow logically?)

For awkward transitions, add to `narrative.scene_issues` with:
- scene_id: The LATER scene of the pair (e.g., scene 4 if transition 3->4 is awkward)
- dimension: "transition"
- issue: "씬 N에서 N+1로의 전환이 어색함: [구체적 이유]"
- severity: "error" (completely breaks flow) or "warning" (noticeable but minor)
```

### 엣지 케이스
- **1씬 스토리보드**: 전환 평가 대상 없음. scene_issues에 transition 항목 없음
- **2씬 스토리보드**: 1개 전환만 평가
- **의도적 급전환** (반전 씬): Gemini가 twist_payoff 맥락에서 긍정 평가할 수 있음. 프롬프트에 "intentional dramatic shift는 제외" 단서 추가

### 영향 범위
- LangFuse 프롬프트만 변경. 코드 변경 없음
- dimension 값으로 "transition" 추가되지만, `_NARRATIVE_WEIGHTS`에는 포함하지 않음 (점수 계산 대상 아님, 피드백용)

### 테스트 전략
- mock 응답에 `dimension: "transition"` 항목 포함하여 파싱 및 Revise 피드백 전달 검증

### Out of Scope
- transition을 별도 가중치 차원으로 추가. 피드백 전달 목적만

---

## DoD 4: Revise _build_feedback()에서 scene_issues 파싱

### 구현 방법
1. `backend/services/agent/nodes/revise.py`의 `_build_feedback()` 함수 수정
2. `review_result.narrative_score.scene_issues`를 읽어 "[씬별 서사 이슈]" 섹션 생성
3. 기존 narrative_score.feedback 문자열 피드백과 병렬 배치 (대체가 아닌 보강)

### 동작 정의
`_build_feedback()` 변경:

```python
# 기존 코드 (유지)
if ns := review.get("narrative_score"):
    if ns_fb := ns.get("feedback"):
        parts.append(f"[서사 품질 피드백] {ns_fb}")
    # ... 기존 low_dims 로직 유지 ...

# 신규 추가: per-scene narrative issues
if scene_issues := ns.get("scene_issues"):
    issue_lines = []
    for si in scene_issues:
        sid = si.get("scene_id", "?")
        issue = si.get("issue", "")
        dim = si.get("dimension", "")
        sev = si.get("severity", "warning")
        marker = "[ERROR]" if sev == "error" else "[WARN]"
        issue_lines.append(f"- 씬 {sid} ({dim}) {marker}: {issue}")
    if issue_lines:
        parts.append("[씬별 서사 이슈]\n" + "\n".join(issue_lines))
```

생성되는 피드백 예시:
```
[씬별 서사 이슈]
- 씬 1 (hook) [ERROR]: Hook이 일반적인 서술로 시작하여 주의를 끌지 못함
- 씬 3 (transition) [WARN]: 씬 2에서 씬 3으로의 전환이 어색함 — 감정 톤 급변
- 씬 5 (spoken_naturalness) [WARN]: "~하는 것이었습니다" AI 톤 표현
```

### 엣지 케이스
- **scene_issues 빈 배열**: "[씬별 서사 이슈]" 섹션 미출력. 기존 동작과 동일
- **scene_issues 없음 (레거시 폴백)**: `ns.get("scene_issues")` → None → 미출력
- **scene_issues 항목에 필드 누락**: `.get()` 기본값으로 안전 처리 (`"?"`, `""`, `"warning"`)

### 영향 범위
- `revise.py` `_build_feedback()` 수정 (10줄 이내 추가)
- Tier 3 재생성 시 `pipeline_context["revision_feedback"]`에 씬 번호가 포함된 피드백 자동 전달 (기존 흐름 활용)

### 테스트 전략
- **단위 테스트**: `_build_feedback()`에 scene_issues 포함된 state 전달 → 출력에 "씬 N" 형태 피드백 포함 검증
  - 케이스 1: scene_issues에 error + warning 혼합 → 양쪽 모두 출력
  - 케이스 2: scene_issues 빈 배열 → "[씬별 서사 이슈]" 미출력
  - 케이스 3: scene_issues 없음 (레거시) → 기존 동작 동일
- **단위 테스트**: `_build_feedback()`의 기존 테스트 (`test_revise_includes_reflection_in_feedback`) 회귀 없음 확인

### Out of Scope
- Revise Tier 1/2에서 scene_issues 기반 선택적 수정. Tier 3 재생성 피드백 전달만

---

## DoD 5: Revise Tier 3 pipeline_context에 씬 번호 포함 피드백 전달

### 구현 방법
별도 코드 변경 불필요. DoD 4에서 `_build_feedback()`가 씬 번호 포함 피드백을 생성하면, 기존 Tier 3 로직이 이를 자동으로 `pipeline_context["revision_feedback"]`에 전달한다.

### 동작 정의
기존 흐름 확인:
```python
# revise.py Tier 3 (line 299-305)
feedback = _build_feedback(state)  # ← DoD 4에서 scene_issues 포함
pipeline_ctx: dict[str, str] = {}
if current_script:
    pipeline_ctx["current_script_summary"] = current_script
if feedback:
    pipeline_ctx["revision_feedback"] = feedback  # ← 자동 전달
```

즉, `_build_feedback()`의 출력이 바뀌면 `pipeline_context["revision_feedback"]`도 자동으로 씬 번호 포함 피드백이 된다. 추가 코드 변경 없음.

### 테스트 전략
- **통합 테스트**: review_result에 narrative scene_issues가 있는 state로 `revise_node()` 호출 (Tier 3 경로) → `generate_script()`에 전달된 `pipeline_context["revision_feedback"]`에 "씬 N" 패턴 포함 검증
  - mock: `generate_script`를 AsyncMock으로 패치하여 `pipeline_context` 인자 캡처

### Out of Scope
- Writer가 씬 번호 피드백을 실제로 활용하는지 검증 (Writer 프롬프트 변경은 별도 태스크)

---

## DoD 6: 기존 테스트 regression 없음 + 린트 통과

### 구현 방법
1. `pytest backend/tests/test_review_reflection.py backend/tests/test_review_empty_script.py` 실행하여 기존 테스트 통과 확인
2. `ruff check backend/services/agent/llm_models.py backend/services/agent/nodes/review.py backend/services/agent/nodes/revise.py backend/services/agent/state.py` 린트 통과 확인

### 동작 정의
- 기존 테스트의 mock 데이터에 `scene_issues` 필드가 없어도 기본값 `[]`로 처리되어 regression 없음
- `_make_unified_json()` 헬퍼의 narrative에 scene_issues가 없어도 파싱 성공

### 테스트 전략
- 전체 기존 테스트 실행: `pytest backend/tests/ -x`
- ruff lint 통과

---

## 변경 파일 목록 (5개 이하)

| 파일 | 변경 내용 |
|------|----------|
| `backend/services/agent/llm_models.py` | `NarrativeScoreOutput`에 `scene_issues` 필드 추가 |
| `backend/services/agent/state.py` | `NarrativeScore` TypedDict에 `scene_issues` 필드 추가 |
| `backend/services/agent/nodes/review.py` | `_build_narrative_score()`에서 scene_issues 전달 |
| `backend/services/agent/nodes/revise.py` | `_build_feedback()`에서 scene_issues → 씬별 피드백 생성 |
| LangFuse `pipeline/review/unified` v7 | Narrative scene_issues + 전환 자연성 평가 지시 추가 |

## 전체 테스트 계획

| 테스트 | 유형 | 검증 내용 |
|--------|------|----------|
| `test_build_narrative_score_includes_scene_issues` | 단위 | scene_issues가 NarrativeScore에 전달 |
| `test_build_narrative_score_default_empty_scene_issues` | 단위 | scene_issues 미지정 시 빈 배열 |
| `test_build_feedback_with_scene_issues` | 단위 | scene_issues → "씬 N" 피드백 포맷 |
| `test_build_feedback_empty_scene_issues` | 단위 | 빈 scene_issues → 섹션 미출력 |
| `test_build_feedback_no_scene_issues_legacy` | 단위 | scene_issues 없는 state → 기존 동작 |
| `test_unified_narrative_scene_issues_parsed` | 통합 | 통합 호출 mock 응답의 scene_issues 파싱 |
| `test_revise_tier3_passes_scene_feedback` | 통합 | Tier 3에서 pipeline_context에 씬 번호 피드백 포함 |
| 기존 test_review_reflection.py 전체 | 회귀 | 기존 테스트 regression 없음 |
