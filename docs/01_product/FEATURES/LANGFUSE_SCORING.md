# LangFuse Scoring 시스템 도입

**상태**: Phase 38 구현 완료 (E2E 검증 대기)
**목표**: 파이프라인 품질 점수를 LangFuse에 기록하여 추적/비교/회귀감지
**리뷰**: v1 Tech Lead/PM/QA 반영 → v2 코드 분석 갭 반영 → **v3 4-Agent 리뷰 반영 (BLOCKER 4건 해결)**

---

## 배경

### 기존 계획
- `SYSTEM_OVERVIEW.md`: 아키텍처에 "LangFuse v3 (Trace/Span/Score)" 명시
- `LANGFUSE_PROMPT_OPS.md`: "LangFuse Score 연동 — 별도 명세로 분리"로 보류
- NarrativeScore, Research Score 등이 내부 로직에서만 사용, LangFuse 기록 0건

### LangFuse 공식 Evaluation Method

| 방법 | 설명 | 적합도 |
|------|------|--------|
| **SDK/API Score** | 코드에서 프로그래밍 방식으로 기록 | ✅ **1순위** |
| **LLM-as-Judge** | LLM이 출력물을 평가 | △ 참고용 (NarrativeScore) |
| **Annotation Queue** | 구조화된 리뷰 워크플로우 | ✗ 향후 (팀 확장 시) |

---

## Score 설계 원칙

### 신뢰도 기반 Tier 분류

| Tier | 소스 | 신뢰도 | 활용 |
|------|------|--------|------|
| **Tier 1** | 코드 결정론적 측정 | 높음 | 절대값 비교, 회귀 감지 |
| **Tier 2** | LLM 자기평가 | 낮음 | 추이 비교만 (절대값 무의미) |
| **Tier 3** | 실제 시청자 데이터 | 최고 | Ground truth (향후) |

> **`research_quality` 주의**: Tier 1이지만 키워드 매칭 기반 휴리스틱이므로, 대시보드 해석 시 다른 Tier 1 지표보다 신뢰도 낮음.

---

## Score 목록

### Tier 1: 객관적 지표

| Score Name | 타입 | 범위 | 소스 | 기록 시점 |
|-----------|------|------|------|----------|
| `first_pass` | BOOLEAN | true/false | Review 1차 통과 여부 | Review |
| `revision_count` | NUMERIC | 0~3 | `state["revision_count"]` (Writer→Review 루프 횟수 단독, max=`LANGGRAPH_MAX_REVISIONS`) | Finalize |
| `scene_count` | NUMERIC | 1~30 | `len(final_scenes)` (후처리 완료 후) | Finalize |
| `visual_qc_issues` | NUMERIC | 0~20 | `len(qc.get("issues", []))` | Cinematographer |
| `script_qc_issues` | NUMERIC | 0~20 | `len(script_qc.get("issues", []))` | Review |
| `research_quality` | NUMERIC | 0.0~1.0 | `state["research_score"]["overall"]` | Research |
| `director_revision_count` | NUMERIC | 0~3 | `state["director_revision_count"]` (Director가 revise 판정한 횟수) | Director |
| `pipeline_duration_sec` | NUMERIC | 0~1800 | `time.monotonic()` 경과 시간 (Generate 시에만 설정, Resume skip) | Finalize |

> **`pipeline_mode`**: Score가 아닌 trace metadata로 기록 (CATEGORICAL은 LangFuse 대시보드 활용도 낮음)

### Tier 2: LLM 자기평가

| Score Name | 타입 | 소스 | comment |
|-----------|------|------|---------|
| `narrative_overall` | NUMERIC (0~1) | NarrativeScore.overall | 8차원 세부 JSON |

comment 예시:
```json
{"hook":0.8,"emotional_arc":0.7,"twist_payoff":0.6,"speaker_tone":0.9,
 "script_image_sync":0.7,"spoken_naturalness":0.8,"retention_flow":0.7,"pacing_rhythm":0.75}
```

### Tier 3: 실제 시청자 데이터 (향후)

| Score Name | 타입 | 소스 |
|-----------|------|------|
| `youtube_retention_rate` | NUMERIC | YouTube Analytics API (게시 후 7일) |
| `youtube_like_ratio` | NUMERIC | 좋아요/조회수 비율 |

> PM 리뷰: 1인 개발 환경에서 자기 평가 별점은 Tier 2와 동급. YouTube 실제 데이터가 진정한 Ground truth.

---

## Score Config (코드 SSOT + LangFuse UI 등록)

```python
# config_pipelines.py — SSOT (max 값은 코드 상수 참조)
LANGFUSE_SCORE_CONFIGS = {
    "first_pass": {"data_type": "BOOLEAN"},
    "revision_count": {"data_type": "NUMERIC", "min": 0, "max": LANGGRAPH_MAX_REVISIONS},  # 3
    "scene_count": {"data_type": "NUMERIC", "min": 1, "max": 30},
    "visual_qc_issues": {"data_type": "NUMERIC", "min": 0, "max": 20},
    "script_qc_issues": {"data_type": "NUMERIC", "min": 0, "max": 20},
    "research_quality": {"data_type": "NUMERIC", "min": 0, "max": 1},
    "director_revision_count": {"data_type": "NUMERIC", "min": 0, "max": LANGGRAPH_MAX_DIRECTOR_REVISIONS},  # 3
    "pipeline_duration_sec": {"data_type": "NUMERIC", "min": 0, "max": 1800},
    "narrative_overall": {"data_type": "NUMERIC", "min": 0, "max": 1},
}
```

코드가 SSOT. max 값은 하드코딩이 아닌 상수 참조로 동기화 보장. LangFuse UI에도 동일하게 등록.

### Observation-Level Score 전략

LangFuse는 observation-level 평가를 권장 (trace-level은 Legacy). SDK Score도 `observation_id`를 지정하여 **특정 노드의 span/generation에 부착**한다.

| 레벨 | 용도 | 예시 |
|------|------|------|
| **observation-level** | 노드별 Score → 노드 성능 개별 추적 | `first_pass` → Review generation |
| **trace-level** | 파이프라인 전체 Score → 종합 지표 | `pipeline_duration_sec`, `scene_count` |

**observation_id 획득**: `trace_llm_call()` context manager의 `LLMCallResult.generation.id`에서 획득.

```python
# 노드 내부 (예: review.py)
async with trace_llm_call("review.evaluate", model=model) as llm:
    llm.record(response)
    obs_id = llm.generation.id if llm.generation else None

# Score 기록 시 observation에 부착
record_score("first_pass", result["passed"], observation_id=obs_id)
```

**Finalize 노드 예외**: `revision_count`, `scene_count`, `pipeline_duration_sec`는 특정 LLM 호출에 종속되지 않으므로 **trace-level**로 기록 (`observation_id=None`).

### LangFuse SDK v3 `create_score()` 시그니처

```python
def create_score(
    self, *, name: str, value: float | str,
    trace_id: str | None = None, observation_id: str | None = None,
    data_type: Literal["NUMERIC", "BOOLEAN", "CATEGORICAL"] | None = None,
    comment: str | None = None, config_id: str | None = None,
    metadata: Any | None = None, score_id: str | None = None,
    session_id: str | None = None, timestamp: datetime | None = None,
) -> None:
```

> **BOOLEAN 주의**: `value`는 Python `bool`이 아닌 **`1` 또는 `0`** (float). `record_score()`에서 `bool → int` 변환 필수.

---

## Sprint 구성

### Sprint A: 인프라 + 테스트
| # | 항목 | 파일 | 상세 |
|---|------|------|------|
| A-1 | `record_score()` 헬퍼 | `observability.py` | **observation_id 지원**, value None 가드, data_type 자동 추론, bool→int, graceful skip, try/except — ✅ 구현 완료 |
| A-5 | `LANGFUSE_SCORE_CONFIGS` 상수 | `config_pipelines.py` | L58 뒤 LangFuse 섹션에 추가. max 값은 코드 상수 참조 |
| A-6a | `pipeline_mode` metadata 기록 | `observability.py` | `create_langfuse_handler()`에 `pipeline_mode` 파라미터 추가 → `_patch_trace()` body에 포함 |
| A-6b | `pipeline_mode` 전달 | `scripts.py` | `is_fast_track` → `"fasttrack"` / `"full"` 문자열 변환 후 전달 |
| A-6c | `_pipeline_start_time` contextvar | `observability.py` | Generate 시에만 `time.monotonic()` 설정 (Resume skip) + `get_pipeline_elapsed_sec()` 공개 함수 |
| A-7 | LangFuse UI Score Config 등록 | LangFuse UI | 9개 수동 등록 |
| A-8 | `record_score` 단위 테스트 | `test_observability_unit.py` | 성공/미연결/trace_id 없음/value None skip/bool True→1,False→0/exception 안전성/data_type 자동 추론/pipeline_elapsed_sec 미설정→None/**observation_id 전달 검증**/observation_id=None→trace-level |

### Sprint B: Tier 1 + Tier 2 Score 기록 + 테스트
| # | 항목 | 파일 | 상세 |
|---|------|------|------|
| B-1 | Review → `first_pass` + `script_qc_issues` | `nodes/review.py` | **return dict 구성 직전**. `record_score("first_pass", result["passed"], observation_id=obs_id)`. `obs_id`는 `trace_llm_call()` generation.id. errors만 카운트 |
| B-2 | Review → `narrative_overall` | `nodes/review.py` | `record_score("narrative_overall", ns.get("overall"), observation_id=obs_id, comment=json.dumps(ns))`. 동일 obs_id 사용 |
| B-3 | Finalize → `revision_count` + `scene_count` + `pipeline_duration_sec` | `nodes/finalize.py` | **return 직전** 3개. **trace-level** (`observation_id=None`) — 특정 LLM 호출에 종속되지 않음 |
| B-4 | Cinematographer → `visual_qc_issues` | `nodes/cinematographer.py` | Competition + 단일 모드 **양쪽**. `record_score(..., observation_id=obs_id)`. 실패 경로 미기록 |
| B-5 | Research → `research_quality` | `nodes/research.py` | `record_score("research_quality", score.get("overall"), observation_id=obs_id)`. 스킵/실패 시 None → 중앙 가드 |
| B-6 | Director → `director_revision_count` | `nodes/director.py` | `record_score("director_revision_count", new_count, observation_id=obs_id)`. approve 시 0 기록 |
| B-7 | conftest.py autouse mock | `tests/conftest.py` | `_reset_langfuse_state` fixture: `obs._initialized=False`, `obs._langfuse_client=None` 리셋 (테스트 간 상태 격리) |
| B-8 | 노드별 mock 호출 검증 + FastTrack | `tests/test_langfuse_scoring.py` | Full 경로: 9개 Score 호출 검증. FastTrack 경로: 최소 3개(revision_count, scene_count, pipeline_duration_sec) + 미기록 Score 미호출 검증 |

---

## 예외 처리 정책 (Sprint A-3, A-4)

```python
def record_score(name: str, value: float | bool | None, *,
                 observation_id: str | None = None,
                 comment: str = "") -> None:
    """현재 trace(또는 observation)에 score를 기록한다. 실패 시 파이프라인 미중단."""
    if value is None:
        return  # None 가드 — 노드 스킵/실패 시 안전하게 무시
    if not _ensure_initialized() or _langfuse_client is None:
        return  # LangFuse 비활성
    trace_id = _current_trace_id.get()
    if not trace_id:
        return  # trace context 밖에서 호출
    cfg = LANGFUSE_SCORE_CONFIGS.get(name, {})
    data_type = cfg.get("data_type", "NUMERIC")
    safe_value: float = int(value) if isinstance(value, bool) else value
    try:
        _langfuse_client.create_score(
            trace_id=trace_id,
            observation_id=observation_id,  # None이면 trace-level
            name=name,
            value=safe_value,
            data_type=data_type,
            comment=comment or None,
        )
        target = f"obs={observation_id[:16]}" if observation_id else f"trace={trace_id[:16]}"
        logger.debug("[LangFuse] Score 기록: %s=%s (%s)", name, value, target)
    except Exception as e:
        logger.warning("[LangFuse] Score 기록 실패 (non-fatal): %s=%s, %r", name, value, e)
```

**설계 결정**:
- `observation_id` → 지정 시 observation-level Score, None이면 trace-level (LangFuse 권장 패턴)
- `value=None` → 즉시 return (노드 스킵/실패 시 중앙 방어)
- `data_type` → `LANGFUSE_SCORE_CONFIGS`에서 자동 추론
- `bool → int` 변환 → SDK 요구사항 캡슐화

| 시나리오 | 동작 |
|----------|------|
| value=None | 즉시 return (노드 스킵/실패 시) |
| LangFuse 비활성 | `_ensure_initialized()` False → 즉시 return |
| trace_id=None | contextvar None → 즉시 return |
| 네트워크 장애 | try/except → warning 로그 + 계속 |
| 범위 초과 | LangFuse 서버측 처리 (거부 시 warning) |
| SDK rate limit | 동일 — warning + 계속 |
| SDK 배치 전송 | `create_score()`는 내부 큐에 넣고 즉시 반환, `flush_langfuse()`에서 최종 전송 |

---

## 활용 시나리오

### 1. 프롬프트 변경 효과 측정
```
Phase 37 적용 전: first_pass rate=60%, revision_count 평균=2.1
Phase 37 적용 후: first_pass rate=80%, revision_count 평균=1.3
→ 한국어 구어체 강화 효과 정량 입증
```

### 2. 회귀 감지
```
프롬프트 v5 배포 → visual_qc_issues 급증 (0.5 → 2.3)
→ 대시보드에서 즉시 감지 → 롤백 판단
```

### 3. 모드별 품질 비교
```
pipeline_mode=full: first_pass 85%, narrative_overall 0.81
pipeline_mode=fasttrack: first_pass 65%, narrative_overall 0.72
→ FastTrack 품질 트레이드오프 정량화
```

### 4. ComfyUI 전환 검증 (향후)
```
Forge 베이스라인: visual_qc_issues 평균 1.2
ComfyUI Phase A 후: visual_qc_issues 평균 0.8
→ 이미지 품질 개선 정량 입증
```
> PM 리뷰: 지금 도입하면 ComfyUI 전환 전 베이스라인이 자동 축적됨

---

## 완료 기준 (DoD)
- [x] `record_score` 헬퍼 구현 (observation_id + value None 가드 + data_type 자동 추론 + bool→int + graceful skip)
- [x] Tier 1 Score 8개 + Tier 2 Score 1개 = 9개 기록
- [ ] Generate 파이프라인 1회 실행 후 LangFuse Score 탭에 최소 9개 Score 표시
- [ ] Resume 파이프라인 실행 시에도 해당 노드 Score 정상 기록
- [ ] FastTrack 모드에서도 `scene_count` + `revision_count` + `pipeline_duration_sec` 최소 3개 기록
- [ ] Score Config 9개 LangFuse UI에 등록
- [x] 기존 Backend 테스트 전체 PASS (3,725 passed, 0 failed)
- [x] 신규 테스트 전체 PASS (35개)

## 모니터링
- 성공: `logger.debug("[LangFuse] Score 기록: %s=%s")`
- 실패: `logger.warning("[LangFuse] Score 기록 실패 (non-fatal): ...")`
- 점검: LangFuse UI Score 탭 → 최근 trace에 Score 존재 여부

## 의존성
- LangFuse v3 SDK `create_score` API — 설치됨 (`langfuse>=3.0.0`)
- `observability.py`의 `_current_trace_id` contextvar — 구현됨 (L33)
- Phase 37 NarrativeScore 8차원 — 완료
- `LANGGRAPH_MAX_REVISIONS` (=3) — `revision_count` max 동기화
- `LANGGRAPH_MAX_DIRECTOR_REVISIONS` (=3) — `director_revision_count` max 동기화

---

## 코드 분석 결과 (2026-03-18)

### 인프라 현황

| 항목 | 위치 | 상태 |
|------|------|------|
| `_current_trace_id` contextvar | `observability.py:33` | ✅ 구현됨 |
| `_ensure_initialized()` | `observability.py:45-65` | ✅ lazy init + graceful degradation |
| `_langfuse_client` 전역 | `observability.py:26` | ✅ `Langfuse()` 인스턴스 |
| `_patch_trace()` Ingestion API | `observability.py:164-189` | ✅ httpx 직접 호출 |
| LangFuse 상수 | `config_pipelines.py:54-58` | ✅ ENABLED/KEY/URL |
| `record_score()` 헬퍼 | — | ❌ **Sprint A-1에서 구현** |
| `LANGFUSE_SCORE_CONFIGS` | — | ❌ **Sprint A-5에서 추가** (L58 뒤) |

### Score 소스 데이터 매핑 (코드 검증 완료)

| Score | 소스 코드 위치 | 접근 방식 |
|-------|---------------|----------|
| `first_pass` | `review.py` → `ReviewResult["passed"]` (bool) | `record_score("first_pass", result["passed"], data_type="BOOLEAN")` |
| `script_qc_issues` | `review.py` → `ReviewResult["errors"]` (list[str]) | `record_score("script_qc_issues", len(result.get("errors", [])))` — **errors만** 카운트 (warnings 제외, passed 결정 기준이 errors이므로) |
| `narrative_overall` | `review.py:187-194` → `_build_narrative_score()` → `.overall` | comment에 8차원 JSON (`{hook, emotional_arc, ...}`) |
| `visual_qc_issues` | `cinematographer.py:340-348` → `visual_qc_result["issues"]` (list[str]) | `record_score("visual_qc_issues", len(qc.get("issues", [])))` |
| `research_quality` | `research.py:361-363` → `calculate_research_score()` → `.overall` | float 0.0~1.0 |
| `director_revision_count` | `director.py:60,241` → `state["director_revision_count"]` | int, 증가 조건: revise 스텝 발생 또는 error |
| `revision_count` | `state["revision_count"]` (Writer→Review 루프) | Finalize에서 state 읽기 |
| `scene_count` | `finalize.py` → `len(scenes)` (후처리 완료 후) | Finalize return 직전 |
| `pipeline_duration_sec` | **ScriptState에 없음** → contextvar로 해결 | 아래 Gap #1 참조 |

### 발견된 Gap 3건 + 해결 방안

#### Gap #1: `pipeline_duration_sec` — ScriptState에 `pipeline_start_time` 없음

**문제**: Finalize에서 파이프라인 경과 시간을 계산하려면 시작 시각이 필요하나, ScriptState에 해당 필드 없음.

**해결**: `observability.py`에 `_pipeline_start_time` contextvar 추가. ScriptState 수정 불필요.

```python
_pipeline_start_time: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "langfuse_pipeline_start", default=None
)

# create_langfuse_handler()에서 설정 (Generate 시에만, Resume skip):
if _pipeline_start_time.get() is None:
    _pipeline_start_time.set(time.monotonic())

# Finalize에서 읽기:
def get_pipeline_elapsed_sec() -> float | None:
    start = _pipeline_start_time.get()
    return round(time.monotonic() - start, 1) if start else None
```

**Resume 시 동작**: `_pipeline_start_time.get()`이 이미 설정되어 있으면 skip → Generate 시작~최종 Finalize까지의 **총 AI 처리 시간**을 측정. Human Gate 대기 시간은 포함됨 (실 벽시계 시간). Resume trace에서도 동일 start 기준으로 duration 기록.

#### Gap #2: `pipeline_mode` metadata — 두 가지 결정 경로

**문제**: pipeline_mode는 두 경로로 결정됨:
- (a) API 명시 FastTrack: `scripts.py:48` `is_fast_track = len(skip) > 0` — Trace 생성 시점에 알 수 있음
- (b) Director Plan 자율 결정: `director_plan_node()` 실행 후 — Trace 이미 생성된 뒤

**해결**: 2단계 기록

```python
# Step 1: create_langfuse_handler()에 pipeline_mode 파라미터 추가
#   - API 명시 FastTrack → "fasttrack"
#   - Director Plan 경유 → "full" (초기값)
# Step 2: director_plan_node() 완료 후 _patch_trace()로 metadata 업데이트
#   - skip_stages 자율 결정 결과 추가 (예: "full_skip_research")
```

`create_langfuse_handler()` 시그니처 변경:
```python
def create_langfuse_handler(
    *, trace_id=None, session_id=None, action="generate",
    pipeline_mode: str = "full",  # ← 신규 파라미터
) -> Any:
```

`scripts.py`에서 호출:
```python
handler = create_langfuse_handler(
    trace_id=trace_id, session_id=session_id, action=action,
    pipeline_mode="fasttrack" if is_fast_track else "full",
)
```

#### Gap #3: BOOLEAN 값 변환

**문제**: LangFuse SDK `create_score(data_type="BOOLEAN")`는 Python `bool`이 아닌 `float(0/1)` 요구.

**해결**: `record_score()` 내부에서 `bool → int` 변환:
```python
safe_value: float = int(value) if isinstance(value, bool) else value
```

### FastTrack Score 기록 범위

FastTrack에서는 Research/Cinematographer/Director 노드를 건너뛸 수 있으므로:

| Score | Full | FastTrack | 비고 |
|-------|------|-----------|------|
| `first_pass` | ✅ | ✅ | Review는 항상 실행 |
| `script_qc_issues` | ✅ | ✅ | Review는 항상 실행 |
| `narrative_overall` | ✅ | ❌ | Full 모드에서만 Unified Evaluate 실행 (FastTrack은 narrative_score=None) |
| `visual_qc_issues` | ✅ | ❌ | Cinematographer 스킵 시 미기록 |
| `research_quality` | ✅ | ❌ | Research 스킵 시 미기록 |
| `director_revision_count` | ✅ | ❌ | Director 스킵 시 미기록 |
| `revision_count` | ✅ | ✅ | Finalize에서 state 읽기 |
| `scene_count` | ✅ | ✅ | Finalize에서 계산 |
| `pipeline_duration_sec` | ✅ | ✅ | contextvar 기반 |

**DoD 검증**: FastTrack 최소 3개 → `revision_count` + `scene_count` + `pipeline_duration_sec` ✅

## 리뷰 반영 이력

### v1 리뷰 (초안)
| 리뷰어 | 핵심 피드백 | 반영 |
|--------|-----------|------|
| Tech Lead | `director_revisions` 정의 모호 (BLOCKER) | → `director_revision_count` (실제 수정 횟수)로 명확화 |
| Tech Lead | `pipeline_mode`는 trace metadata로 | → Score 목록에서 제거, A-6에서 metadata 기록 |
| Tech Lead | `pipeline_duration_sec`, `script_qc_issues` 추가 | → Tier 1에 추가 |
| Tech Lead | Sprint D를 B에 통합 | → 2-Sprint 구조로 변경 |
| PM | DoD 정량적 검증 기준 부재 | → "최소 9개 Score" + "FastTrack 최소 3개" 추가 |
| PM | `revision_count` 정의 명확화 | → "state.revision_count 단독 (Writer→Review 루프)" 명시 |
| PM | Tier 3 대안: YouTube Analytics | → Tier 3을 YouTube 데이터로 변경 |
| PM | 시나리오 4 축소 | → ComfyUI 전환 검증으로 변경 (현실적) |
| QA | Sprint D 테스트 3개→11개 | → Sprint B에 통합, 노드별 mock 검증 + 통합 테스트 |
| QA | 엣지 케이스 8개 미정의 | → 예외 처리 정책 섹션 신설 |
| QA | `scene_count` Config 누락 | → Config 목록에 추가 |
| QA | 기존 테스트 영향 (~120개) | → B-7에 conftest.py autouse fixture 명시 |
| QA | Config를 코드 SSOT로 | → `LANGFUSE_SCORE_CONFIGS` 상수 정의 (A-5) |
| QA | 모니터링 방법 부재 | → 모니터링 섹션 신설 |

### v3 리뷰 (4-Agent 통합, 2026-03-18)

**BLOCKER 4건 해결:**
| 출처 | 이슈 | 해결 |
|------|------|------|
| QA+TechLead | `revision_count` max=6 vs 실제 max=3 | → max=`LANGGRAPH_MAX_REVISIONS`(3) 상수 참조로 변경 |
| QA+Backend | Resume 시 `_pipeline_start_time` 리셋 → duration 왜곡 | → Generate 시에만 설정, Resume skip (`if get() is None:` 가드) |
| Backend+QA | narrative/research/visual None 가드 누락 | → `record_score()`에 `value is None → return` 중앙 가드 추가 |
| TechLead | `time.time()` vs `time.monotonic()` 표기 불일치 | → `time.monotonic()`으로 통일 |

**WARNING 반영 (주요):**
| 출처 | 이슈 | 해결 |
|------|------|------|
| TechLead | `narrative_overall` FastTrack = △(조건부) | → ❌(미기록)으로 정정 |
| QA | `pipeline_duration_sec` max=600 초과 가능 | → max=1800으로 상향 |
| Backend | `data_type` 매번 명시 필요 | → `LANGFUSE_SCORE_CONFIGS`에서 자동 추론 |
| Backend | Score 삽입 위치 모호 | → 각 노드 return dict 구성 직전으로 명시 |
| Backend | Cinematographer 양쪽 경로 삽입 필요 | → Competition + 단일 모드 양쪽 명시 |
| TechLead | conftest mock 구현 방식 미명시 | → `_reset_langfuse_state` fixture 구체화 |
| QA | B-8에 FastTrack 전용 테스트 누락 | → FastTrack 경로 검증 추가 |
| PM | Resume 경로 DoD 부재 | → DoD에 Resume 검증 항목 추가 |
| PM | LANGFUSE_GUIDE.md 상태 동기화 | → Sprint A 착수 시 함께 업데이트 |

**SUGGESTION 채택:**
- ~~`observation_id` 파라미터 예약 → 향후 확장 시 추가~~ → ✅ **구현 완료** (2026-03-18)
- Tier 3 `trace_id` 영구 저장 → 향후 검토 (현재 범위 밖)
- 회귀 감지 자동화 → 향후 임계치 기반 알림 검토

---

## LLM-as-a-Judge 평가자 (Observation-Level)

LangFuse UI에 등록된 자동 평가자. 파이프라인 GENERATION observation마다 LLM이 자동 채점.

| 평가자 | 평가 대상 | Tier | Runs on |
|--------|----------|------|---------|
| `pacing_rhythm` | 페이싱 리듬 | Tier 2 | observations (GENERATION) |
| `retention_flow` | 몰입 흐름 | Tier 2 | observations (GENERATION) |
| `spoken_naturalness` | 구어체 자연스러움 | Tier 2 | observations (GENERATION) |

> **Legacy → Observation 전환 완료** (2026-03-18). trace-level(Legacy) → observation-level(GENERATION 필터).

### 유지보수 시 업데이트 필요한 경우

| 변경 사항 | 필요 작업 |
|-----------|----------|
| LangFuse 프롬프트 평가 기준 변경 | LangFuse UI에서 Referenced Evaluator 프롬프트 수정 |
| 노드 이름/구조 변경 | LangFuse UI Filter의 observation name 업데이트 |
| 평가 차원 추가 (예: `visual_coherence`) | LangFuse UI에서 새 evaluator 생성 |
| SDK Score와 중복 시 | LLM-as-Judge 비활성화 검토 (SDK Score가 SSOT) |
