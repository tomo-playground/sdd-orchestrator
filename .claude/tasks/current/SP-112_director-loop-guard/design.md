# SP-112: Director 공회전 방지 — 상세 설계

## 변경 파일 요약

| 파일 | 변경 유형 | 설명 |
|------|-----------|------|
| `backend/config_pipelines.py` | 수정 | 새 상수 추가 (MAX_CINETEAM_CALLS, CHECKPOINT_STAGNATION_TOLERANCE) |
| `backend/services/agent/state.py` | 수정 | `cineteam_call_count`, `director_checkpoint_score_history` 필드 추가 |
| `backend/services/agent/routing.py` | 수정 | `route_after_director`에 cineteam 왕복 제한, `route_after_director_checkpoint`에 점수 정체 조기 종료 |
| `backend/services/agent/nodes/director_checkpoint.py` | 수정 | score_history 누적 + cineteam_call_count 증분 로직 추가 |
| `backend/services/agent/nodes/director.py` | 수정 | revise_cinematographer 결정 시 cineteam_call_count 증분 |
| `backend/tests/test_routing.py` | 수정 | Director loop 반복 제한 + 점수 정체 테스트 추가 |
| `backend/tests/test_director_checkpoint.py` | 수정 | score_history 누적 + cineteam_call_count 테스트 추가 |

---

## DoD 1: Director ReAct loop 전체 반복 제한

### 배경 분석

현재 흐름: `director_checkpoint → cinematographer → fan-out → join → director → (revise_cinematographer) → cinematographer → ... → director → ...`

**문제**: Director가 `revise_cinematographer`를 반복 결정하면 CineTeam(cinematographer → fan-out → join → director)이 무한 왕복.
- `LANGGRAPH_MAX_REACT_STEPS(3)`: Director 내부 ReAct 루프 (Agent 인라인 수정 포함)
- `LANGGRAPH_MAX_DIRECTOR_REVISIONS(3)`: Director→routing→다시 노드 왕복 횟수
- 최악: 3 × 3 = 9회 CineTeam 호출 가능

**목표**: CineTeam 전체 호출 횟수를 최대 3회로 제한 (초기 1회 + revise 2회).

### 구현 방법

#### 1-1. 상수 추가 (`config_pipelines.py`)

`# --- Director-as-Orchestrator ---` 섹션 아래에 추가:

```python
LANGGRAPH_MAX_CINETEAM_CALLS = int(os.getenv("LANGGRAPH_MAX_CINETEAM_CALLS", "3"))
```

`routing.py`의 기존 `config_pipelines` import 블록에 `LANGGRAPH_MAX_CINETEAM_CALLS` 추가.

#### 1-2. State 필드 추가 (`state.py`)

`ScriptState` TypedDict의 `director_revision_count` (라인 214) 아래에 추가:

```python
cineteam_call_count: int  # SP-112: CineTeam(cinematographer) 전체 호출 횟수
```

기본값 0. routing 함수에서 `state.get("cineteam_call_count", 0)`으로 접근.

#### 1-3. `director_checkpoint_node` 수정 (`director_checkpoint.py`)

cinematographer로 진행하는 경우 (`proceed` 또는 `error` decision) cineteam_call_count 증분.

**proceed/error 경로 반환 dict에 추가:**
```python
update["cineteam_call_count"] = state.get("cineteam_call_count", 0) + 1
```

적용 위치:
- 정상 경로: `decision != "revise"` 시 (proceed 또는 error) update dict에 포함
- 재시도 성공 경로: 동일
- 양쪽 실패(error) 반환 경로: 동일 (error → routing → cinematographer)

**revise 경로**: cineteam_call_count 미변경 (writer로 가므로).

#### 1-4. `director_node` 수정 (`director.py`)

result_dict 생성 후 (라인 247~253), revised_agents 처리 루프 직전에 추가:

```python
# SP-112: revise_cinematographer → cineteam_call_count 증분
if final_decision == "revise_cinematographer":
    result_dict["cineteam_call_count"] = state.get("cineteam_call_count", 0) + 1
```

#### 1-5. `route_after_director` 수정 (`routing.py`)

기존 코드 구조(라인 204~210)에서, `target = _DIRECTOR_DECISION_MAP.get(decision)` 조회 후, `target is None` 체크 후, `return target` 직전에 cineteam 가드레일 삽입:

```python
target = _DIRECTOR_DECISION_MAP.get(decision)
if target is None:
    logger.warning("[LangGraph] Director 미등록 decision '%s', finalize로 fallback", decision)
    return "finalize"

# SP-112: CineTeam 호출 상한 체크
if target == "cinematographer":
    cine_count = state.get("cineteam_call_count", 0)
    if cine_count >= LANGGRAPH_MAX_CINETEAM_CALLS:
        logger.warning(
            "[LangGraph] CineTeam 호출 상한(%d) 도달 (count=%d), 강제 finalize",
            LANGGRAPH_MAX_CINETEAM_CALLS, cine_count,
        )
        return "finalize"

logger.debug("[LangGraph:Route] director -> %s (decision=%s)", target, decision)
return target
```

### 동작 정의

| 시나리오 | cineteam_call_count 변화 | 결과 |
|----------|------------------------|------|
| checkpoint → proceed → cinematographer (1회차) | 0 → 1 (checkpoint에서) | 정상 진행 |
| director → revise_cinematographer (2회차) | 1 → 2 (director에서) | routing 통과, cinematographer 진행 |
| director → revise_cinematographer (3회차) | 2 → 3 (director에서) | routing에서 3 ≥ MAX(3) → **강제 finalize** |

총 CineTeam 호출: 최대 3회 (초기 1 + revise 2). ✅ 스펙 충족.

### 엣지 케이스

1. **director가 revise_tts/revise_sound 결정**: cineteam_call_count 미증분. 해당 가드레일 미적용. ✅
2. **director가 revise_script 결정 후 다시 checkpoint → cinematographer**: checkpoint에서 cineteam_call_count 추가 증분. 전체 파이프라인 비용 누적 제한. ✅
3. **fast_track 모드**: 기존 `max_dir_rev=1` 가드레일이 먼저 작동. cineteam 가드레일은 추가 안전망.
4. **글로벌 리비전 상한 도달**: `LANGGRAPH_MAX_GLOBAL_REVISIONS` 체크가 cineteam 체크보다 먼저 발동 가능. 두 가드레일 독립 동작.
5. **checkpoint → error → cinematographer**: cineteam_call_count 증분됨 (1-3에서 처리). ✅

---

## DoD 2: director_checkpoint 점수 정체 조기 종료

### 배경 분석

`director_checkpoint`가 `revise` → writer → review → `director_checkpoint` 루프에서 점수가 개선되지 않고 동일 점수를 반복하면 비용 낭비.

현재 `director_checkpoint_score`는 단일 float. 이전 점수 이력이 없어 정체 감지 불가.

### 구현 방법

#### 2-1. State 필드 추가 (`state.py`)

`director_checkpoint_score` (라인 208) 아래에 추가:

```python
director_checkpoint_score_history: list[float]  # SP-112: checkpoint 점수 이력 (정체 감지용)
```

기본값 빈 리스트.

#### 2-2. 상수 추가 (`config_pipelines.py`)

`LANGGRAPH_MAX_CINETEAM_CALLS` 아래에 추가:

```python
LANGGRAPH_CHECKPOINT_STAGNATION_TOLERANCE = float(
    os.getenv("LANGGRAPH_CHECKPOINT_STAGNATION_TOLERANCE", "0.05")
)
```

#### 2-3. `director_checkpoint_node` 수정 (`director_checkpoint.py`)

LLM 호출 성공 후, update dict에 score_history 누적 추가:

```python
score_history = list(state.get("director_checkpoint_score_history") or [])
score_history.append(cp.score)
update["director_checkpoint_score_history"] = score_history
```

**모든 성공 경로에 적용**: 정상 경로 + 재시도 성공 경로. 양쪽 실패(error) 경로는 cp.score 없으므로 미적용.

#### 2-4. `route_after_director_checkpoint` 수정 (`routing.py`)

`decision != "proceed"` 분기 내부에서, 글로벌 리비전 상한 체크(라인 236~243) 직후, revise 횟수 체크(라인 245~251) **직전**에 삽입:

```python
# SP-112: 점수 정체 감지 — 연속 2회 동일 점수(±tolerance) → 강제 cinematographer 진행
score_history = state.get("director_checkpoint_score_history") or []
if len(score_history) >= 2:
    prev, curr = score_history[-2], score_history[-1]
    if abs(prev - curr) <= LANGGRAPH_CHECKPOINT_STAGNATION_TOLERANCE:
        logger.warning(
            "[LangGraph] Checkpoint 점수 정체 감지 (%.2f → %.2f, tol=%.2f), "
            "강제 cinematographer 진행",
            prev, curr, LANGGRAPH_CHECKPOINT_STAGNATION_TOLERANCE,
        )
        return "cinematographer"
```

**import 추가**: `routing.py` 상단 import에 `LANGGRAPH_CHECKPOINT_STAGNATION_TOLERANCE`, `LANGGRAPH_MAX_CINETEAM_CALLS` 추가.

### 동작 정의

| score_history | revise 결정 시 | 결과 |
|---------------|---------------|------|
| `[]` (첫 checkpoint) | 이력 부족 | revise 정상 진행 |
| `[0.5]` (1회 revise 후 재진입) | 이력 1개 | revise 정상 진행 |
| `[0.5, 0.52]` (차이 0.02 ≤ 0.05) | 정체 감지 | **강제 cinematographer** |
| `[0.5, 0.60]` (차이 0.10 > 0.05) | 개선 중 | revise 정상 진행 |
| `[0.3, 0.5, 0.52]` (3회째) | 마지막 2개 비교 | **강제 cinematographer** |
| `[0.5, 0.48]` (하락, 차이 0.02 ≤ 0.05) | 정체 감지 | **강제 cinematographer** |

### 엣지 케이스

1. **score_history 미설정 (기존 파이프라인 호환)**: `state.get(...) or []` → 빈 리스트 → 정체 감지 스킵. ✅
2. **proceed 결정 시**: revise 분기 미진입. 정체 체크 안 함. ✅
3. **score override (proceed→revise)**: cp.score로 history 기록. override 후 decision이 revise면 routing에서 정체 체크 적용. ✅
4. **음수 score**: error decision으로 변환 → cinematographer 라우팅. revise 분기 미진입. ✅
5. **연속 0.00 score**: |0.0 - 0.0| = 0.0 ≤ 0.05 → 정체 감지. 무의미한 재시도 방지. ✅

---

## DoD 3: 테스트

### `backend/tests/test_routing.py` — 추가 7개

```python
# -- SP-112: CineTeam 호출 상한 테스트 --

def test_route_after_director_cineteam_limit_blocks():
    """cineteam_call_count >= MAX → revise_cinematographer 시 finalize."""
    state = {
        "director_decision": "revise_cinematographer",
        "director_revision_count": 0,
        "cineteam_call_count": 3,
    }
    assert route_after_director(state) == "finalize"

def test_route_after_director_cineteam_under_limit_passes():
    """cineteam_call_count < MAX → revise_cinematographer 정상 진행."""
    state = {
        "director_decision": "revise_cinematographer",
        "director_revision_count": 0,
        "cineteam_call_count": 2,
    }
    assert route_after_director(state) == "cinematographer"

def test_route_after_director_cineteam_limit_other_revise_unaffected():
    """cineteam_call_count >= MAX이지만 revise_tts → tts_designer (미영향)."""
    state = {
        "director_decision": "revise_tts",
        "director_revision_count": 0,
        "cineteam_call_count": 5,
    }
    assert route_after_director(state) == "tts_designer"

# -- SP-112: Checkpoint 점수 정체 테스트 --

def test_route_checkpoint_score_stagnation_forces_proceed():
    """연속 2회 동일 점수(±0.05) → 강제 cinematographer."""
    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_score": 0.52,
        "director_checkpoint_revision_count": 1,
        "director_checkpoint_score_history": [0.5, 0.52],
    }
    assert route_after_director_checkpoint(state) == "cinematographer"

def test_route_checkpoint_score_improving_continues_revise():
    """점수 개선 중 → 정상 revise."""
    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_score": 0.60,
        "director_checkpoint_revision_count": 1,
        "director_checkpoint_score_history": [0.5, 0.60],
    }
    assert route_after_director_checkpoint(state) == "writer"

def test_route_checkpoint_score_stagnation_insufficient_history():
    """이력 1개 → 정체 감지 불가, 정상 revise."""
    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_revision_count": 0,
        "director_checkpoint_score_history": [0.5],
    }
    assert route_after_director_checkpoint(state) == "writer"

def test_route_checkpoint_score_stagnation_empty_history():
    """이력 없음 → 정상 revise."""
    state = {
        "director_checkpoint_decision": "revise",
        "director_checkpoint_revision_count": 0,
    }
    assert route_after_director_checkpoint(state) == "writer"
```

### `backend/tests/test_director_checkpoint.py` — 추가 2개

```python
@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_node_accumulates_score_history(mock_run):
    """checkpoint 노드가 score_history를 누적한다."""
    mock_run.return_value = {"decision": "proceed", "score": 0.8, "reasoning": "좋음"}
    state = {
        "topic": "테스트", "skip_stages": [], "duration": 30,
        "director_checkpoint_revision_count": 0,
        "director_checkpoint_score_history": [0.5],
    }
    result = await director_checkpoint_node(state)
    assert result["director_checkpoint_score_history"] == [0.5, 0.8]

@pytest.mark.asyncio
@patch("services.agent.nodes.director_checkpoint.run_production_step", new_callable=AsyncMock)
async def test_checkpoint_node_starts_empty_history(mock_run):
    """score_history 미설정 시 새 리스트 시작."""
    mock_run.return_value = {"decision": "proceed", "score": 0.7, "reasoning": "ok"}
    state = {"topic": "테스트", "duration": 30, "director_checkpoint_revision_count": 0}
    result = await director_checkpoint_node(state)
    assert result["director_checkpoint_score_history"] == [0.7]
```

### 기존 테스트 호환성

- `cineteam_call_count` 미설정 state → `state.get("cineteam_call_count", 0)` = 0 → 기존 테스트 모두 통과
- `director_checkpoint_score_history` 미설정 → `state.get(...) or []` = [] → 정체 감지 스킵 → 기존 테스트 모두 통과
- 기존 `test_route_after_director_revise_cinematographer` (`cineteam_call_count` 없음 = 0 < 3) → 기존 동작 유지 ✅
- 기존 `test_route_checkpoint_revise` (`score_history` 없음) → 정체 감지 스킵 → 기존 동작 유지 ✅

---

## 영향 범위

| 파일 | 영향 |
|------|------|
| `backend/config_pipelines.py` | 상수 2개 추가 (기존 코드 무영향) |
| `backend/services/agent/state.py` | TypedDict 필드 2개 추가 (기존 코드 무영향) |
| `backend/services/agent/routing.py` | 2개 함수 수정 (가드레일 추가, 기존 경로 유지) |
| `backend/services/agent/nodes/director_checkpoint.py` | 반환값 확장 (score_history + cineteam_call_count) |
| `backend/services/agent/nodes/director.py` | 반환값 조건부 확장 (cineteam_call_count) |
| `backend/tests/test_routing.py` | 테스트 7개 추가 |
| `backend/tests/test_director_checkpoint.py` | 테스트 2개 추가 |

**DB 영향**: 없음 (LangGraph State는 메모리/체크포인터 기반)
**Frontend 영향**: 없음
**프롬프트 영향**: 없음 (LangFuse 프롬프트 변경 불필요)

---

## Out of Scope

- Director ReAct Loop 내부 스텝 수 (`LANGGRAPH_MAX_REACT_STEPS`) 변경 — 이미 3으로 적절
- `LANGGRAPH_MAX_DIRECTOR_REVISIONS` 기본값 변경 — 기존 가드레일 유지, cineteam 전용 가드 추가
- Director 프롬프트 수정 — v7에서 이미 수정됨, 코드 가드레일만 추가
- 비용 추적/로깅 추가 — 별도 태스크로 분리
- `LANGGRAPH_MAX_GLOBAL_REVISIONS` 변경 — 기존 값(6) 유지

---

## BLOCKER 없음

- DB 스키마 변경 없음
- 외부 의존성 추가 없음
- 아키텍처 변경 없음