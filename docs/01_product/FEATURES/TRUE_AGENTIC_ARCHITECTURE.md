# True Agentic Architecture — DAG Workflow → Agentic AI 전환

**상태**: 설계 완료 (Ready for Implementation)
**출처**: Tech Lead 아키텍처 검토 (2026-02-18)
**관련**: [AGENTIC_PIPELINE.md](AGENTIC_PIPELINE.md), [AGENT_SPEC.md](../../03_engineering/backend/AGENT_SPEC.md)

---

## 1. 문제 진단: "Agentic AI"가 아닌 현재 구현

### 1-1. 현재 아키텍처 정확한 분류

```
단순 LLM 호출  <  Chain/Pipeline  <  DAG Workflow  <  Router Agent  <  ReAct Agent  <  Multi-Agent
                                     ^^^^^^^^^^^^
                                     [현재 위치]
```

LangGraph 프레임워크를 사용하지만, 실질 패턴은 **"State Machine 기반 DAG Workflow"**.
LLM은 구조화된 콘텐츠 생성기 역할만 하며, 제어 흐름은 하드코딩된 Python 로직이 담당.

### 1-2. Agentic AI 5대 요건 충족 여부

| # | 요건 | 현재 상태 | 판정 |
|---|------|----------|------|
| 1 | **자율적 의사결정** — LLM이 다음 행동 결정 | `routing.py`의 if/else가 모든 분기 결정 | X |
| 2 | **Tool Use** — 에이전트가 도구를 선택적 호출 | 모든 노드가 항상 같은 함수 호출. `tools=` 미사용 | X |
| 3 | **Planning** — 목표 이해 후 계획 수립/수정 | 그래프 토폴로지 = 고정된 계획. 런타임 변경 없음 | X |
| 4 | **Self-Reflection** — 자기 출력 평가 및 개선 | Review/Director는 외부 검증. 자기 반성 아님 | X |
| 5 | **에이전트 간 소통** — 자연어 메시지 교환 | 공유 state dict 단방향 전달만 존재 | X |

### 1-3. 결정적 근거: 공통 패턴의 한계

6개 Production 노드가 `run_production_step()` 단일 함수로 동작:

```
템플릿 렌더링 → Gemini 호출 → JSON 파싱 → QC 검증 → 재시도
```

이것은 **"구조화된 출력 생성기"** 패턴이며, 에이전트의 자율적 판단이 아님.

---

## 2. 목표 (To-Be)

### 2-1. 전환 후 아키텍처 위치

```
단순 LLM 호출  <  Chain/Pipeline  <  DAG Workflow  <  Router Agent  <  ReAct Agent  <  Multi-Agent
                                                                      ^^^^^^^^^^^^
                                                                      [목표 위치]
```

### 2-2. 전환 원칙

| 원칙 | 설명 |
|------|------|
| **점진적 전환** | 한 번에 Multi-Agent가 아닌, Level 1→2→3 단계적 진화 |
| **기존 장점 보존** | 예측 가능성, 비용 통제, 디버깅 용이성은 유지 |
| **선택적 Agentic** | 모든 노드가 아닌, 효과가 큰 핵심 노드부터 전환 |
| **비용 가드레일** | Tool Use 도입 시 최대 호출 횟수 제한 필수 |
| **측정 가능한 개선** | 각 Level 완료 후 품질 지표(NarrativeScore, Match Rate)로 효과 검증 |

---

## 3. 단계별 전환 계획

### Phase A: ReAct Loop + Self-Reflection (Level 1)

**목표**: 핵심 노드에 Observe→Think→Act 루프 도입. 최소 코드 변경, 최대 효과.
**공수**: 4-5일

#### A-1. Director ReAct Loop (2-3일)

**현재** (Single-shot):
```python
# director.py — 1회 LLM 호출로 즉시 decision
result = await run_production_step("director.j2", ...)
decision = result["decision"]  # "approve" | "revise_*"
```

**개선** (Observe→Think→Act):
```python
async def director_node(state: ScriptState) -> dict:
    observations = _gather_production_results(state)

    for step in range(MAX_THINKING_STEPS):  # 최대 3 스텝
        # Observe: 현재 상태 종합
        thought = await _think(observations)
        # "시각 디자인은 양호하나 TTS 감정 표현이 장면 톤과 불일치"

        # Act: 다음 행동 결정
        action = await _decide(thought, observations)

        if action.type == "approve":
            break

        # 부분 재검토 실행 후 결과를 관찰에 추가
        result = await _execute_check(action)
        observations.append({"step": step, "action": action, "result": result})

    return {
        "director_decision": action.decision,
        "director_reasoning": [obs for obs in observations],  # 사고 과정 기록
    }
```

**핵심 변경**:
- `director.py`: Single-shot → ReAct 루프 (최대 3 스텝)
- `director.j2`: 관찰→사고→행동 분리 프롬프트
- `state.py`: `director_reasoning: list[dict]` 추가

**비용 가드레일**: `MAX_THINKING_STEPS=3` (최대 Gemini 3회 추가)

#### A-2. Review Self-Reflection (1-2일)

**현재** (외부 검증만):
```python
# review.py — 규칙 실패 → 에러 리스트 전달 → revise가 재생성
errors = _validate_scenes(scenes, ...)
if errors:
    return {"review_result": {"passed": False, "errors": errors}}
```

**개선** (실패 원인 분석 + 수정 전략 수립):
```python
async def review_node(state: ScriptState) -> dict:
    errors = _validate_scenes(scenes, ...)

    if errors:
        # Self-Reflection: "왜 실패했는지" + "어떻게 수정할지" 분석
        reflection = await _reflect_on_failure(
            scenes=scenes,
            errors=errors,
            previous_feedback=state.get("revision_feedback"),
        )
        # reflection = {
        #   "root_cause": "Hook이 약함 — 첫 씬이 설명적",
        #   "strategy": "질문형 Hook으로 교체, 3초 내 긴장감 생성",
        #   "specific_fixes": [{"scene": 0, "issue": "...", "suggestion": "..."}]
        # }

        return {
            "review_result": {
                "passed": False,
                "errors": errors,
                "reflection": reflection,  # 수정 전략 포함
            }
        }
```

**핵심 변경**:
- `review.py`: 실패 시 `_reflect_on_failure()` 추가 (Gemini 1회)
- `revise.py`: `reflection.strategy`를 활용한 타겟 수정
- `templates/review_reflection.j2`: 신규 Reflection 프롬프트

**효과**: revise 노드가 "무작정 재생성"이 아닌 "전략적 수정" 수행

#### A-3. Writer Planning Step (1일)

**현재** (즉시 생성):
```python
# writer.py — 바로 generate_script() 호출
request = StoryboardRequest(topic=..., description=desc, ...)
result = await generate_script(request, db)
```

**개선** (계획 → 생성 2-step):
```python
async def writer_node(state: ScriptState) -> dict:
    # Step 1: 계획 수립
    plan = await _create_writing_plan(state)
    # plan = {
    #   "hook_strategy": "충격 통계로 시작",
    #   "emotional_arc": "호기심 → 공감 → 감동 → 행동 촉구",
    #   "scene_allocation": {"hook": 2, "rising": 4, "climax": 2, "resolution": 2},
    #   "key_message": "혼자여도 괜찮다는 위로"
    # }

    # Step 2: 계획 기반 생성
    desc_with_plan = f"{desc}\n\n[작성 계획]\n{json.dumps(plan, ensure_ascii=False)}"
    result = await generate_script(request_with_plan, db)

    return {
        "draft_scenes": result["scenes"],
        "writing_plan": plan,  # 계획도 state에 기록
    }
```

**핵심 변경**:
- `writer.py`: `_create_writing_plan()` 추가 (Gemini 1회)
- `templates/writing_plan.j2`: 신규 계획 프롬프트
- `state.py`: `writing_plan: dict | None` 추가

---

### Phase B: Tool-Calling Agent (Level 2)

**목표**: 핵심 노드에 Gemini Function Calling 도입. LLM이 필요한 도구를 선택적으로 호출.
**선행**: Phase A 완료
**공수**: 5-7일

#### B-1. Gemini Function Calling 인프라 (2일)

**구현**:
- `services/agent/tools/` 패키지 신규 생성
- Tool 정의 표준 인터페이스: `@agent_tool` 데코레이터
- Gemini `tools=` 파라미터 통합 유틸: `call_with_tools()`
- 최대 호출 횟수 가드레일: `MAX_TOOL_CALLS_PER_NODE=5`
- Tool 실행 로그: LangFuse span으로 자동 기록

```python
# services/agent/tools/base.py
from google.genai import types

def define_tool(name: str, description: str, parameters: dict) -> types.Tool:
    """Gemini Function Calling용 도구 정의"""
    ...

async def call_with_tools(
    prompt: str,
    tools: list[types.Tool],
    max_calls: int = MAX_TOOL_CALLS_PER_NODE,
) -> tuple[str, list[ToolCallLog]]:
    """도구 호출 루프: LLM 응답 → tool_call 감지 → 실행 → 결과 주입 → 반복"""
    ...
```

#### B-2. Research Agent Tool-Calling (2-3일)

**현재**: 고정 4개 네임스페이스 순회 + 조건부 소재 분석

**개선**: LLM이 필요한 정보원을 판단하여 선택적 호출

```python
# services/agent/tools/research_tools.py
RESEARCH_TOOLS = [
    define_tool(
        name="search_topic_history",
        description="과거 동일/유사 주제 생성 이력 검색",
        parameters={"topic": "str", "limit": "int"}
    ),
    define_tool(
        name="search_character_history",
        description="캐릭터별 과거 생성 이력 및 성공 패턴",
        parameters={"character_id": "int"}
    ),
    define_tool(
        name="fetch_url_content",
        description="URL에서 콘텐츠를 가져와 요약",
        parameters={"url": "str"}
    ),
    define_tool(
        name="analyze_trending",
        description="해당 주제의 트렌딩 키워드 및 인기 패턴 분석",
        parameters={"topic": "str", "language": "str"}
    ),
    define_tool(
        name="get_group_dna",
        description="채널/시리즈의 톤, 세계관, 가이드라인 조회",
        parameters={"group_id": "int"}
    ),
]

async def research_node(state: ScriptState) -> dict:
    prompt = f"""당신은 쇼츠 리서치 에이전트입니다.
주제: {state['topic']}
설명: {state.get('description', '')}

목표: 이 주제에 대한 최적의 대본 작성을 위해 필요한 정보를 수집하세요.
사용 가능한 도구를 활용하여 필요한 정보만 선택적으로 수집합니다."""

    response, tool_logs = await call_with_tools(prompt, RESEARCH_TOOLS)
    return {"research_brief": response, "research_tool_logs": tool_logs}
```

**효과**:
- "오늘 하루 있었던 일" → 히스토리만 검색 (URL fetch 불필요)
- References URL 제공 시 → URL fetch + 트렌딩 분석 자동 선택
- 새 캐릭터 → 캐릭터 히스토리 스킵 (데이터 없으므로)

#### B-3. Cinematographer Agent Tool-Calling (2일)

**현재**: 고정 템플릿 → Gemini → JSON → QC

**개선**: LLM이 태그 검증/레퍼런스 검색 도구를 선택적 호출

```python
CINEMATOGRAPHER_TOOLS = [
    define_tool(
        name="validate_danbooru_tag",
        description="Danbooru에 존재하는 유효한 태그인지 검증",
        parameters={"tag": "str"}
    ),
    define_tool(
        name="search_similar_compositions",
        description="유사한 구도/분위기의 레퍼런스 이미지 태그 조합 검색",
        parameters={"mood": "str", "scene_type": "str"}
    ),
    define_tool(
        name="get_character_visual_tags",
        description="캐릭터의 비주얼 태그(identity, costume, LoRA) 조회",
        parameters={"character_id": "int"}
    ),
    define_tool(
        name="check_tag_compatibility",
        description="두 태그의 호환성 검증 (충돌 규칙 확인)",
        parameters={"tag_a": "str", "tag_b": "str"}
    ),
]
```

**효과**:
- 생성한 태그가 유효한지 스스로 검증
- 충돌하는 태그 조합을 사전에 감지
- 캐릭터 비주얼과 씬 분위기의 정합성 확인

---

### Phase C: Agent Communication (Level 3)

**목표**: 핵심 에이전트 간 자연어 메시지 기반 협업 도입.
**선행**: Phase B 완료
**공수**: 7-10일

#### C-1. Agent Message Protocol (2-3일)

**구현**: 에이전트 간 구조화된 메시지 교환 프로토콜

```python
# services/agent/messages.py
class AgentMessage(TypedDict):
    sender: str          # 발신 에이전트명
    recipient: str       # 수신 에이전트명
    content: str         # 자연어 메시지
    message_type: str    # "feedback" | "request" | "suggestion" | "approval"
    metadata: dict       # 구조화된 추가 데이터

# State 확장
class ScriptState(TypedDict, total=False):
    ...
    agent_messages: list[AgentMessage]  # 에이전트 간 메시지 로그
```

#### C-2. Director ↔ Production Agent 양방향 소통 (3-4일)

**현재**: Director → state["director_feedback"] → routing → 타겟 노드가 읽음

**개선**: Director가 타겟 에이전트에 직접 피드백 메시지 전송, 에이전트가 응답

```python
async def director_node(state: ScriptState) -> dict:
    results = _gather_production_results(state)
    messages = []

    for step in range(MAX_THINKING_STEPS):
        assessment = await _assess(results, messages)

        if assessment.decision == "approve":
            break

        # Director → Cinematographer: "씬 3의 카메라 앵글을 변경해주세요"
        feedback_msg = AgentMessage(
            sender="director",
            recipient=assessment.target_agent,
            content=assessment.feedback,
            message_type="feedback",
        )
        messages.append(feedback_msg)

        # 타겟 에이전트 실행 → 응답 메시지
        response = await _run_agent_with_message(
            assessment.target_agent, state, feedback_msg
        )
        messages.append(response)

        # 응답을 관찰에 추가하여 다음 판단에 반영
        results[assessment.target_agent] = response.metadata.get("result")

    return {
        "director_decision": assessment.decision,
        "agent_messages": messages,  # 전체 대화 기록
    }
```

#### C-3. Critic 에이전트 실시간 토론 (2-3일)

**현재**: Architects(3인) → Devil's Advocate → Director 순차 파이프라인

**개선**: 3인 Architect가 서로의 컨셉을 읽고 비평하는 실시간 토론

```python
async def critic_node(state: ScriptState) -> dict:
    context = _build_debate_context(state)

    # Round 1: 각 Architect 독립 컨셉 생성
    concepts = await asyncio.gather(
        _architect_propose(1, context),
        _architect_propose(2, context),
        _architect_propose(3, context),
    )

    messages = []

    # Round 2: 상호 비평 (각 Architect가 다른 2인의 컨셉을 비평)
    for round in range(MAX_DEBATE_ROUNDS):
        critiques = await asyncio.gather(*[
            _architect_critique(i, concepts, messages)
            for i in range(3)
        ])
        messages.extend(critiques)

        # KPI 기반 수렴 판단 (§6-1 리스크 대응)
        if await _check_convergence(concepts, messages, state):
            break

        # 비평 반영하여 컨셉 개선
        concepts = await asyncio.gather(*[
            _architect_refine(i, concepts[i], critiques)
            for i in range(3)
        ])

    # Director 최종 평가
    selected = await _director_evaluate(concepts, messages)

    return {
        "critic_result": {
            "selected_concept": selected,
            "candidates": concepts,
            "debate_log": messages,  # 토론 과정 기록
        }
    }
```

---

## 4. State 확장 설계

### Phase A 추가 필드

```python
class ScriptState(TypedDict, total=False):
    # ... 기존 필드 유지 ...

    # Phase A: ReAct + Reflection
    writing_plan: dict | None           # Writer 작성 계획
    director_reasoning: list[dict]      # Director 사고 과정 기록
    review_reflection: dict | None      # Review 실패 원인 분석 + 수정 전략
```

### Phase B 추가 필드

```python
    # Phase B: Tool-Calling
    research_tool_logs: list[dict]      # Research 도구 호출 이력
    cinematographer_tool_logs: list[dict]  # Cinematographer 도구 호출 이력
```

### Phase C 추가 필드

```python
    # Phase C: Agent Communication
    agent_messages: list[AgentMessage]  # 에이전트 간 메시지 로그
    debate_log: list[dict]             # Critic 토론 기록
```

---

## 5. 비용 가드레일

| 단계 | 현재 Gemini 호출 | 추가 호출 | 가드레일 |
|------|-----------------|----------|----------|
| Phase A: Director ReAct | 1회 | +2회 | `MAX_THINKING_STEPS=3` |
| Phase A: Review Reflection | 0~2회 | +1회 | 실패 시에만 |
| Phase A: Writer Planning | 1회 | +1회 | 항상 1회 |
| Phase B: Research Tools | 1회 | +3회 | `MAX_TOOL_CALLS=5` |
| Phase B: Cinematographer Tools | 1회 | +3회 | `MAX_TOOL_CALLS=5` |
| Phase C: Director 양방향 | 1회 | +4회 | `MAX_THINKING_STEPS=3` |
| Phase C: Critic 토론 | 3+회 | +6회 | `MAX_DEBATE_ROUNDS=2` |

**Quick 모드**: Phase A~C 모두 스킵 (비용 변동 없음)
**Full 모드 최대 추가 비용**: ~20 Gemini 호출 (기존 대비 약 2배)

---

## 6. 리스크 대응 (Gemini 크로스 리뷰 반영)

### 6-1. 예측 불가능성 (Unpredictability) — 자율성의 함정

**리스크**: 에이전트에게 의사결정권을 넘기면 결과의 일관성(Consistency) 위협. Critic 토론이 "산으로 갈" 위험, 집단 사고(Groupthink), 무한 루프.

**대응**:

| 가드레일 | 구현 |
|----------|------|
| **KPI 기반 수렴 판단** | `_check_convergence()`를 단순 유사도가 아닌 비즈니스 KPI로 판단: NarrativeScore ≥ 0.7, Hook 강도 ≥ 0.6 |
| **다양성 강제** | 3 Architect에 `diversity_constraint` 주입 — 동일 방향 2개 이상 시 강제 대안 생성 |
| **Hard Timeout** | `MAX_DEBATE_ROUNDS=2` + 전체 토론 `DEBATE_TIMEOUT_SEC=60` (시간 초과 시 현재 최선 선택) |
| **Fallback 경로** | 토론 실패/수렴 불가 시 기존 단순 파이프라인(Single-shot)으로 즉시 fallback |
| **A/B 일관성 검증** | Phase별 도입 후 동일 입력 10회 실행 → 출력 분산도 측정. 기존 대비 분산 20% 이상 증가 시 롤백 |

```python
async def _check_convergence(concepts: list, messages: list, state: ScriptState) -> bool:
    """비즈니스 KPI 기반 수렴 판단"""
    # 1) NarrativeScore 기반 품질 임계값
    best_score = max(c.get("estimated_score", 0) for c in concepts)
    if best_score >= CONVERGENCE_SCORE_THRESHOLD:  # 0.7
        return True

    # 2) 다양성 붕괴 감지 (Groupthink 방지)
    if _concepts_too_similar(concepts, threshold=0.85):
        logger.warning("Groupthink detected — forcing divergence")
        return False  # 추가 라운드에서 다양성 강제

    # 3) Hard round limit
    return len(messages) >= MAX_DEBATE_ROUNDS * 3
```

### 6-2. 비용 ROI — "비싸졌는데 좋아졌나?" 증명

**리스크**: Gemini 호출 2배 증가에 비례하는 품질 향상이 없으면 비용 낭비.

**대응**: Phase별 **정량적 A/B 테스트** 필수

| Phase | 비교 대상 | 측정 지표 | 최소 기대 효과 | 미달 시 |
|-------|----------|----------|---------------|---------|
| A | 기존 vs ReAct+Reflection | NarrativeScore 평균 | +10% (0.65→0.72) | 롤백 검토 |
| B | 기존 vs Tool-Calling | 유효 태그 비율 (Match Rate) | +15% | 롤백 검토 |
| C | 기존 vs Agent Communication | NarrativeScore + 사용자 만족도 | +20% (복합) | Phase C 중단 |

```python
# config_pipelines.py — Phase별 비용 추적
AGENTIC_COST_TRACKING = True  # LangFuse에 Phase별 Gemini 호출 수/토큰 기록
AGENTIC_AB_TEST_ENABLED = False  # 활성화 시 50% 트래픽을 기존 파이프라인으로
```

**원칙**: "에이전트가 생각하니까 더 좋아졌겠지"는 금지. **데이터로 증명**해야 다음 Phase 진행.

### 6-3. 레이턴시 UX — Speculative Execution

**리스크**: Phase C까지 적용 시 생성 시간 기존 대비 수 배 증가. 사용자에게 긴 로딩 경험.

**대응**:

| 전략 | 구현 | Phase |
|------|------|-------|
| **Speculative Execution** | Critic 토론 중 가장 높은 확률의 컨셉으로 Writer 미리 실행. 확정 후 결과 재활용 또는 폐기 | C |
| **Progressive Rendering** | 토론 중간 결과를 SSE로 실시간 전달 → 사용자가 과정을 "볼" 수 있음 | A~C |
| **ETA 표시** | 각 Phase별 예상 소요 시간 SSE 전달 (기존 PipelineStepper 확장) | A |
| **Quick 모드 유지** | Quick 모드는 모든 Agentic 기능 스킵 — 기존 속도 보장 | - |

```python
# Phase C: Speculative Execution 패턴
async def critic_with_speculation(state: ScriptState) -> dict:
    # 병렬 실행: 토론 + 추측 생성
    debate_task = asyncio.create_task(_run_debate(state))
    speculative_task = asyncio.create_task(
        _speculative_write(state, state.get("critic_result", {}).get("candidates", [{}])[0])
    )

    debate_result = await debate_task
    selected_concept = debate_result["selected_concept"]

    # 추측이 맞으면 재활용, 틀리면 폐기
    speculative_draft = await speculative_task
    if _concept_matches(selected_concept, speculative_draft):
        return {**debate_result, "speculative_draft": speculative_draft}
    else:
        return debate_result  # 폐기, Writer가 새로 생성
```

### 6-4. State 비대화 + 컨텍스트 오염

**리스크**: `agent_messages`가 무제한 쌓이면 뒤쪽 에이전트의 Instruction Following 저하. LLM 컨텍스트 윈도우 낭비.

**대응**: **State Condensation (상태 압축)** 프로세스

| 전략 | 구현 |
|------|------|
| **노드별 압축** | 각 노드 완료 시 `_condense_messages()` → 핵심 결론만 추출 |
| **슬라이딩 윈도우** | `agent_messages`는 최근 `MAX_MESSAGE_WINDOW=10`건만 유지 |
| **요약 필드 분리** | `agent_messages` (원본, 디버그용) vs `agent_summary` (압축본, 다음 노드 입력) |
| **토큰 예산** | 노드별 컨텍스트 주입 시 `MAX_CONTEXT_TOKENS=2000` 제한 |

```python
def _condense_messages(messages: list[AgentMessage]) -> str:
    """에이전트 메시지 로그를 핵심 결론으로 압축"""
    if len(messages) <= MAX_MESSAGE_WINDOW:
        return _format_messages(messages)

    # 오래된 메시지는 요약으로 대체
    old_messages = messages[:-MAX_MESSAGE_WINDOW]
    recent_messages = messages[-MAX_MESSAGE_WINDOW:]

    summary = _summarize_decisions(old_messages)  # 핵심 결정사항만 추출
    return f"[이전 논의 요약] {summary}\n\n" + _format_messages(recent_messages)
```

```python
# State 확장 (Phase C 수정)
class ScriptState(TypedDict, total=False):
    # Phase C: Agent Communication
    agent_messages: list[AgentMessage]  # 원본 전체 (디버그/UI용)
    agent_summary: str | None           # 압축본 (다음 노드 컨텍스트)
    debate_log: list[dict]              # Critic 토론 기록
```

---

## 7. 전환 후 Agentic 요건 충족도 (섹션 6 리스크 대응 포함)

| # | 요건 | Phase A 후 | Phase B 후 | Phase C 후 |
|---|------|-----------|-----------|-----------|
| 1 | 자율적 의사결정 | **부분** (Director ReAct) | **부분** (Research/Cinematographer) | **충족** |
| 2 | Tool Use | X | **충족** (Function Calling) | **충족** |
| 3 | Planning | **부분** (Writer Plan) | **부분** | **충족** |
| 4 | Self-Reflection | **충족** (Review Reflection) | **충족** | **충족** |
| 5 | 에이전트 간 소통 | X | X | **충족** (Message Protocol) |

---

## 8. 테스트 전략

### Phase A 테스트

| 대상 | 테스트 내용 | 예상 건수 |
|------|-----------|----------|
| Director ReAct | 사고 루프 1~3 스텝, approve/revise 분기 | 8개 |
| Review Reflection | 실패 원인 분석 정확도, 전략 생성 | 6개 |
| Writer Planning | 계획 구조 검증, 계획→생성 연계 | 5개 |
| 회귀 테스트 | 기존 1,916개 전량 통과 | - |

### Phase B 테스트

| 대상 | 테스트 내용 | 예상 건수 |
|------|-----------|----------|
| Tool 인프라 | call_with_tools 루프, 가드레일, 로그 | 8개 |
| Research Tools | 도구 선택 분기, SSRF 방어 유지 | 10개 |
| Cinematographer Tools | 태그 검증, 호환성 체크 | 8개 |

### Phase C 테스트

| 대상 | 테스트 내용 | 예상 건수 |
|------|-----------|----------|
| Message Protocol | 메시지 생성/전달/로깅 | 6개 |
| Director 양방향 | 피드백→응답→재판단 루프 | 8개 |
| Critic 토론 | 비평→수렴→선정 | 8개 |

---

## 9. 영향 범위

### Phase A

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `services/agent/nodes/director.py` | Single-shot → ReAct 루프 |
| `services/agent/nodes/review.py` | Self-Reflection 추가 |
| `services/agent/nodes/writer.py` | Planning Step 추가 |
| `templates/director_react.j2` (신규) | 관찰→사고→행동 프롬프트 |
| `templates/review_reflection.j2` (신규) | 실패 분석 프롬프트 |
| `templates/writing_plan.j2` (신규) | 작성 계획 프롬프트 |
| `services/agent/state.py` | 3개 필드 추가 |
| `config_pipelines.py` | `MAX_THINKING_STEPS` 상수 |

### Phase B

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `services/agent/tools/` (신규 패키지) | base.py, research_tools.py, cinematographer_tools.py |
| `services/agent/nodes/research.py` | 고정 순회 → Tool-Calling |
| `services/agent/nodes/cinematographer.py` | 고정 템플릿 → Tool-Calling |
| `config_pipelines.py` | `MAX_TOOL_CALLS_PER_NODE` 상수 |

### Phase C

| 파일/모듈 | 변경 내용 |
|-----------|----------|
| `services/agent/messages.py` (신규) | AgentMessage 프로토콜 |
| `services/agent/nodes/director.py` | 양방향 메시지 소통 |
| `services/agent/nodes/critic.py` | 상호 비평 토론 |
| `services/agent/state.py` | agent_messages, debate_log 필드 |

---

## 10. 성공 기준 (DoD)

### Phase A DoD
- Director가 1회 이상 "사고→판단" 루프를 실행하는 케이스 확인
- Review 실패 시 구체적 수정 전략이 revise에 전달되어 타겟 수정 수행
- Writer가 생성 전 계획을 세우고, 계획 기반으로 대본 구조 결정
- 기존 테스트 전량 통과 + 신규 19개 테스트
- **A/B 검증**: 동일 입력 10회 → NarrativeScore 평균 +10% 이상 확인
- **일관성 검증**: 출력 분산도가 기존 대비 20% 이상 증가하지 않음

### Phase B DoD
- Research 노드가 주제에 따라 다른 도구를 선택적으로 호출 (로그로 확인)
- Cinematographer가 생성한 태그를 스스로 검증하고 부적절한 태그 교체
- Tool 호출 이력이 LangFuse에 span으로 기록
- `MAX_TOOL_CALLS` 가드레일 동작 확인
- **A/B 검증**: 유효 태그 비율 (Match Rate) +15% 이상 확인
- **비용 추적**: LangFuse에서 Phase별 Gemini 호출 수/토큰 집계 가능

### Phase C DoD
- Director↔Production Agent 양방향 대화 로그가 SSE로 Frontend에 전달
- Critic 3인이 최소 1라운드 상호 비평 후 수렴 (KPI 기반 판단)
- 에이전트 메시지 기록이 AgentReasoningPanel에 표시
- State Condensation 동작 — `agent_summary` 압축본이 다음 노드에 전달
- Full 모드 E2E 파이프라인 정상 동작
- **레이턴시**: Full 모드 전체 소요 시간 120초 이내 (Speculative Execution 포함)
- **A/B 검증**: NarrativeScore + 사용자 만족도 복합 +20% 이상
- **Fallback 동작**: 토론 수렴 실패 시 기존 Single-shot으로 정상 fallback

---

## 11. A/B 벤치마크 테스트 샘플

Phase별 Gate 검증을 위한 **고정 벤치마크 입력 세트**. 동일 입력으로 기존(Baseline) vs 신규(Agentic) 각 10회 실행하여 NarrativeScore, Match Rate, 레이턴시를 비교한다.

### 11-1. 샘플 설계 원칙

| 원칙 | 설명 |
|------|------|
| **난이도 분포** | 쉬움(일상) / 보통(감정) / 어려움(복합 서사) 균등 배분 |
| **구조 커버리지** | Monologue 4건, Dialogue 3건, Narrated Dialogue 3건 |
| **언어 커버리지** | Korean 6건, English 2건, Japanese 2건 |
| **기능 타겟** | 각 샘플이 특정 Agentic 기능의 효과를 검증하도록 설계 |
| **재현성** | 입력 고정, 캐릭터 ID 고정, random seed 없음 → 분산도 측정 가능 |

### 11-2. 벤치마크 샘플 10건

#### BM-01: 일상 독백 (쉬움, Baseline)

```json
{
  "id": "BM-01",
  "topic": "오늘 하루 있었던 일",
  "structure": "Monologue",
  "language": "Korean",
  "duration": 30,
  "preset": "full_auto",
  "target": "Phase A — Writer Planning이 Hook 구조를 개선하는지 검증"
}
```
**검증 포인트**: 단순 주제에서도 Planning이 Hook/Climax 배분을 개선하는가?

#### BM-02: 감정 곡선 독백 (보통, Reflection 타겟)

```json
{
  "id": "BM-02",
  "topic": "처음 요리를 해본 날",
  "description": "실패를 겪고 결국 성공하는 감정 곡선. 코믹하면서도 따뜻한 톤",
  "structure": "Monologue",
  "language": "Korean",
  "duration": 30,
  "preset": "full_auto",
  "target": "Phase A — Review Reflection이 감정 곡선 피드백을 정확히 주는지 검증"
}
```
**검증 포인트**: Reflection이 "감정 변화 부족" 등 구체적 수정 전략을 제시하는가?

#### BM-03: 복합 서사 독백 (어려움, Planning + ReAct 타겟)

```json
{
  "id": "BM-03",
  "topic": "10년간 키운 반려동물과의 이별",
  "description": "슬프지만 감사한 마음. 반전: 새로운 만남의 암시",
  "structure": "Monologue",
  "language": "Korean",
  "duration": 45,
  "preset": "full_auto",
  "target": "Phase A — Director ReAct가 감정 톤 일관성을 다각도로 검증하는지"
}
```
**검증 포인트**: Director가 2스텝 이상 사고하여 톤 불일치를 잡아내는가?

#### BM-04: Reference 분석 독백 (Tool-Calling 타겟)

```json
{
  "id": "BM-04",
  "topic": "한국의 카페 문화가 세계적으로 주목받는 이유",
  "references": [
    "한국 카페 시장 규모 15조원 돌파, 1인당 커피 소비량 세계 4위",
    "스타벅스 매장 수 세계 3위, 개인 카페 비중 65%"
  ],
  "structure": "Monologue",
  "language": "Korean",
  "duration": 30,
  "preset": "full_auto",
  "target": "Phase B — Research Agent가 참고 소재를 분석하여 대본에 반영하는지"
}
```
**검증 포인트**: Tool-Calling Research가 소재 텍스트에서 핵심 통계를 추출하여 Hook에 활용하는가?

#### BM-05: 어색한 첫 대화 (Dialogue, 보통)

```json
{
  "id": "BM-05",
  "topic": "첫 만남에서 어색한 대화",
  "structure": "Dialogue",
  "language": "Korean",
  "duration": 30,
  "preset": "full_auto",
  "target": "Phase A — Planning이 Speaker A/B 캐릭터성을 사전 설계하는지"
}
```
**검증 포인트**: Writer Plan에 화자별 성격/말투 설계가 포함되고, 대사에 반영되는가?

#### BM-06: 영어 대화 (Dialogue, 언어 커버리지)

```json
{
  "id": "BM-06",
  "topic": "A job interview gone hilariously wrong",
  "description": "Comedy tone. Interviewer is serious, candidate is nervous and funny",
  "structure": "Dialogue",
  "language": "English",
  "duration": 30,
  "preset": "full_auto",
  "target": "Phase A — 영어에서도 Planning/Reflection이 정상 동작하는지"
}
```
**검증 포인트**: 영어 대본에서도 NarrativeScore 개선이 유의미한가?

#### BM-07: 일본어 대화 (Dialogue, 언어 커버리지)

```json
{
  "id": "BM-07",
  "topic": "桜の下で再会した二人",
  "description": "春の雰囲気、穏やかだけど切ない再会",
  "structure": "Dialogue",
  "language": "Japanese",
  "duration": 30,
  "preset": "full_auto",
  "target": "Phase A — 일본어에서도 Planning/Reflection이 정상 동작하는지"
}
```
**검증 포인트**: 일본어 대본의 감정 표현과 톤 일관성이 개선되는가?

#### BM-08: 내레이션 대화 — 드라마틱 (어려움, Critic 토론 타겟)

```json
{
  "id": "BM-08",
  "topic": "퇴사 전날 사수와의 대화",
  "description": "표면적으로 담담하지만 속마음은 복잡. 마지막에 서로의 진심이 드러남",
  "structure": "Narrated Dialogue",
  "language": "Korean",
  "duration": 45,
  "preset": "full_auto",
  "target": "Phase C — Critic 토론이 서사 깊이를 향상시키는지"
}
```
**검증 포인트**: 에이전트 간 토론을 거친 컨셉이 감정 복합성(겉과 속의 괴리)을 잘 표현하는가?

#### BM-09: 내레이션 대화 — 반전 (어려움, Director ReAct 타겟)

```json
{
  "id": "BM-09",
  "topic": "면접관이 알아본 지원자의 비밀",
  "structure": "Narrated Dialogue",
  "language": "Korean",
  "duration": 45,
  "preset": "creator",
  "target": "Phase A+C — Director가 반전 타이밍/임팩트를 다각도로 검증하는지"
}
```
**검증 포인트**: Director ReAct 2+ 스텝에서 "반전이 약함" 등 구체적 피드백을 생성하는가?

#### BM-10: 영어 내레이션 + References (복합, 전체 파이프라인 타겟)

```json
{
  "id": "BM-10",
  "topic": "Why Gen-Z is quitting social media",
  "description": "Documentary style. Data-driven but emotional personal stories",
  "references": [
    "40% of Gen-Z have taken a social media break in 2025",
    "Average screen time decreased from 7h to 5h among 18-24 year olds"
  ],
  "structure": "Narrated Dialogue",
  "language": "English",
  "duration": 45,
  "preset": "full_auto",
  "target": "Phase A+B+C 전체 — 복합 시나리오에서 Agentic 파이프라인의 종합 효과"
}
```
**검증 포인트**: Research Tool-Calling(소재 분석) + Planning(다큐 구조) + Critic 토론(관점 다양성) + Director ReAct(전체 조화)가 모두 작동하는가?

### 11-3. 벤치마크 실행 프로토콜

```
1. Baseline 수집 (기존 파이프라인)
   - BM-01~10 각 10회 실행 (총 100회)
   - NarrativeScore, 유효 태그 비율, 소요 시간 기록
   - LangFuse에 "baseline" 태그로 트레이스 저장

2. Phase A 검증
   - BM-01~10 각 10회 실행 (총 100회)
   - LangFuse에 "phase_a" 태그
   - 비교: NarrativeScore 평균, 분산도, 소요 시간

3. Phase B 검증
   - BM-04, BM-10 중심 + 나머지 샘플링
   - 추가 측정: Tool 호출 횟수, 선택된 도구 분포
   - 비교: 유효 태그 비율 (Match Rate)

4. Phase C 검증
   - BM-08~10 중심 (복합 서사)
   - 추가 측정: 토론 라운드 수, 수렴 시간, State 크기
   - 비교: NarrativeScore + 레이턴시
```

### 11-4. 벤치마크 자동화 스크립트 (구현 예정)

```
scripts/benchmark/
├── run_benchmark.py      # BM-01~10 자동 실행
├── benchmark_samples.json # 10건 입력 데이터
├── compare_results.py    # Baseline vs Phase X 비교 리포트
└── README.md             # 실행 가이드
```

---

## 12. 참고 자료

- [Gemini Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [LangGraph ReAct Agent](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/)
- [ReAct: Synergizing Reasoning and Acting (Yao et al., 2022)](https://arxiv.org/abs/2210.03629)
- [LangGraph Tool Calling](https://langchain-ai.github.io/langgraph/how-tos/tool-calling/)
- [Multi-Agent Collaboration Patterns](https://langchain-ai.github.io/langgraph/concepts/multi_agent/)
