---
id: SP-043
priority: P1
scope: backend
branch: feat/SP-043-pipeline-model-optimization
created: 2026-03-21
status: done
depends_on:
label: enhancement
reviewer: stopper2008
assignee: stopper2008
---

## 무엇을
파이프라인 모델 최적화 — review/creative_agent Flash 전환 + thinking budget 제한

## 왜
최신 트레이스 분석 (628초, $0.268, 46 LLM calls):
- **review**: 8회 $0.08 (30%) — Pro인데 thinking 82%, output 평균 500tok
- **creative_agent**: 6회 $0.057 (21%) — Pro인데 thinking 77%, 컨셉 생성
- **thinking 전체**: 100K/419K = 24% — 거의 1/4이 thinking에 소비
- **writer PROHIBITED_CONTENT fallback**: Flash 차단 → 2.0-flash fallback 4회, input 14K를 2번씩 전송

비용 $0.268 중 Pro가 $0.158 (59%). review + creative_agent만 Flash로 바꿔도 ~40% 절감 예상.

## 트레이스 데이터 근거

```
=== 모델별 비용 ===
gemini-2.5-pro       16x  $0.1583 (59.1%)  410s
gemini-2.5-flash     26x  $0.1012 (37.8%)  362s

=== 노드별 비용 (Pro 사용, thinking 비율) ===
review           8x  $0.0805  think:82%  → Flash 검토
creative_agent   6x  $0.0571  think:77%  → Flash 검토
director         2x  $0.0208  think:72%  → Pro 유지 (통합 판단)

=== Thinking Top 소비자 ===
cinematographer agents  think: 3,500~7,100 per call (Flash인데 과다)
director_checkpoint     think: 3,000~3,800 per call (Flash인데 과다)
```

## 실패 테스트 (TDD)

구현 전 작성 → RED 확인 → 구현 → GREEN 확인 순서로 진행.

### Part A: REVIEW_MODEL 기본값
```python
# tests/test_config_pipelines.py
def test_review_model_default_is_flash():
    """REVIEW_MODEL 기본값이 gemini-2.5-flash인지 확인."""
    import importlib
    import os

    # 환경변수 없는 상태에서 모듈 재로드
    env = {k: v for k, v in os.environ.items() if k != "REVIEW_MODEL"}
    with patch.dict(os.environ, env, clear=True):
        import config_pipelines
        importlib.reload(config_pipelines)
        assert config_pipelines.REVIEW_MODEL == "gemini-2.5-flash", (
            f"기본값이 gemini-2.5-flash여야 함, 실제: {config_pipelines.REVIEW_MODEL}"
        )
```

### Part B: CREATIVE_LEADER_MODEL 기본값
```python
# tests/test_config_pipelines.py (동일 파일)
def test_creative_leader_model_default_is_flash():
    """CREATIVE_LEADER_MODEL 기본값이 gemini-2.5-flash인지 확인."""
    import importlib
    import os

    env = {k: v for k, v in os.environ.items() if k != "CREATIVE_LEADER_MODEL"}
    with patch.dict(os.environ, env, clear=True):
        import config_pipelines
        importlib.reload(config_pipelines)
        assert config_pipelines.CREATIVE_LEADER_MODEL == "gemini-2.5-flash", (
            f"기본값이 gemini-2.5-flash여야 함, 실제: {config_pipelines.CREATIVE_LEADER_MODEL}"
        )
```

### Part C: Writer safety fallback 시 sanitization 적용
```python
# tests/test_writer_safety_fallback.py
async def test_writer_fallback_applies_sanitization():
    """PROHIBITED_CONTENT fallback 시 _sanitize_for_gemini_prompt가 적용되는지 확인."""
    sanitize_calls = []

    def capture_sanitize(prompt):
        sanitize_calls.append(prompt)
        return prompt  # 원본 반환 (내용 변경 없음)

    with patch("services.agent.nodes.writer._sanitize_for_gemini_prompt", side_effect=capture_sanitize):
        with patch("services.llm.client.generate", side_effect=[
            ProhibitedContentError(),   # 1차 Flash 차단
            MagicMock(text="결과"),      # fallback 성공
        ]):
            await writer_node(mock_state_with_bts_topic, config=None)

    assert len(sanitize_calls) >= 1, "fallback 경로에서 sanitization이 적용되어야 함"
```

## 완료 기준 (DoD)

### Part A: review 모델 분리 (최대 효과)
- [ ] **실패 테스트 → GREEN**: `test_review_model_default_is_flash` 통과
- [ ] `config_pipelines.py`에 `REVIEW_MODEL` 기본값을 `gemini-2.5-flash`로 변경
  - 현재: `gemini-2.5-pro` (config_pipelines.py L30)
  - review는 "기준 대조 채점" 역할 — quality_criteria, narrative_score 등 명시된 기준으로 평가
  - director_checkpoint(이미 Flash)와 동일한 역할 복잡도
- [ ] review 결과 품질 regression 없음 확인 (narrative_score 범위, passed/failed 판정)

### Part B: creative_agent 모델 분리
- [ ] **실패 테스트 → GREEN**: `test_creative_leader_model_default_is_flash` 통과
- [ ] `config_pipelines.py`에 `CREATIVE_LEADER_MODEL` 기본값을 `gemini-2.5-flash`로 변경
  - 현재: `gemini-2.5-pro` (config_pipelines.py L28)
  - 3인 Architect 컨셉 생성 — 창의적이지만 구조화된 JSON 출력
  - Critic 토론이므로 다양성이 더 중요, 개별 품질은 Flash로 충분
- [ ] creative_agent 컨셉 품질 regression 없음 확인

### Part C: Writer PROHIBITED_CONTENT fallback 비용 절감
- [ ] **실패 테스트 → GREEN**: `test_writer_fallback_applies_sanitization` 통과
- [ ] 트레이스 확인: writer GENERATION에서 Flash output 0 → 2.0-flash fallback 4회 반복
  - input 14K 토큰을 2번씩 전송 (Flash 차단 + fallback 재전송)
  - writer.py L48-55: `_SAFETY_HINT` 주입으로 대응 중이지만 효과 불충분
- [ ] 원인 분석: BTS 등 실존 아티스트 주제에서 Flash 안전 필터 과민 반응
- [ ] 개선 방안 검토:
  - sanitization 강화 (`_sanitize_for_gemini_prompt` 확장)
  - 또는 Writer도 2.0-flash를 1차 모델로 사용 (Flash 차단 자체 회피)
  - 또는 fallback 없이 2.5-flash에 safety_settings 조정

### Part D: thinking budget 제한 검토
- [ ] Gemini 2.5 Flash의 thinking budget 파라미터 조사
  - `thinking_config` / `max_thinking_tokens` 등
- [ ] cinematographer agents (think 5,000~7,000)에 budget 적용 테스트
- [ ] director_checkpoint (think 3,000~3,800)에 budget 적용 테스트
- [ ] budget 제한 시 output 품질 영향 평가

### Part E: 검증
- [ ] pytest 통과
- [ ] 린트 통과
- [ ] 실제 파이프라인 실행 후 비용 비교:
  - 목표: $0.268 → $0.15 이하 (40%+ 절감)
  - review 시간: 25초 → ~10초
  - 전체 파이프라인 시간: 628초 → 400초 이하

## 제약
- `config_pipelines.py` + 필요 시 `review.py`, `creative_agents.py` = 최대 5개 파일
- `director_plan`, `director` 노드의 `DIRECTOR_MODEL`은 Pro 유지 (통합 판단 역할)
- thinking budget은 조사 후 적용 — Gemini API가 지원하지 않으면 스킵
- 품질 regression 발견 시 즉시 롤백 가능하도록 환경변수 오버라이드 유지

## 힌트

### Part A: REVIEW_MODEL 변경 (1줄)
```python
# AS-IS
REVIEW_MODEL = os.getenv("REVIEW_MODEL", "gemini-2.5-pro")
# TO-BE
REVIEW_MODEL = os.getenv("REVIEW_MODEL", "gemini-2.5-flash")
```
환경변수로 언제든 Pro 복귀 가능.

### Part B: CREATIVE_LEADER_MODEL 변경 (1줄)
```python
# AS-IS
CREATIVE_LEADER_MODEL = os.getenv("CREATIVE_LEADER_MODEL", "gemini-2.5-pro")
# TO-BE
CREATIVE_LEADER_MODEL = os.getenv("CREATIVE_LEADER_MODEL", "gemini-2.5-flash")
```

### 예상 비용 절감
| 노드 | 현재 (Pro) | 변경 후 (Flash) | 절감 |
|------|-----------|----------------|------|
| review 8x | $0.080 | ~$0.020 | -$0.060 |
| creative_agent 6x | $0.057 | ~$0.015 | -$0.042 |
| **합계** | $0.137 | ~$0.035 | **-$0.102 (74%)** |

파이프라인 전체: $0.268 → ~$0.166 (38% 절감)
