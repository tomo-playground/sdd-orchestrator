# True Agentic Architecture — DAG Workflow → Agentic AI 전환

**상태**: 완료 (2026-02-18, Phase 10 ARCHIVED)
**출처**: Tech Lead 아키텍처 검토 (2026-02-18)
**관련**: [AGENTIC_PIPELINE.md](AGENTIC_PIPELINE.md), [AGENT_SPEC.md](../../03_engineering/backend/AGENT_SPEC.md)

---

## 1. 문제 진단: "Agentic AI"가 아닌 현재 구현

### 1-1. 현재 아키텍처 정확한 분류

```
단순 LLM 호출  <  Chain/Pipeline  <  DAG Workflow  <  Router Agent  <  ReAct Agent  <  Multi-Agent
                                     ^^^^^^^^^^^^
                                     [전환 전 위치]
```

LangGraph 프레임워크를 사용하지만, 실질 패턴은 **"State Machine 기반 DAG Workflow"**.
LLM은 구조화된 콘텐츠 생성기 역할만 하며, 제어 흐름은 하드코딩된 Python 로직이 담당.

### 1-2. Agentic AI 5대 요건 충족 여부 (전환 전→후)

| # | 요건 | 전환 전 | 전환 후 (Phase 10 완료) |
|---|------|--------|----------------------|
| 1 | **자율적 의사결정** | `routing.py`의 if/else가 모든 분기 결정 | Director ReAct Loop (Observe→Think→Act) |
| 2 | **Tool Use** | 모든 노드가 항상 같은 함수 호출 | Gemini Function Calling (Research 5도구, Cinematographer 4도구) |
| 3 | **Planning** | 그래프 토폴로지 = 고정된 계획 | Writer Planning Step (계획→생성 2-step) |
| 4 | **Self-Reflection** | Review/Director는 외부 검증만 | Review Self-Reflection (실패 원인 분석 + 수정 전략) |
| 5 | **에이전트 간 소통** | 공유 state dict 단방향 전달 | Agent Message Protocol + Director↔Production 양방향 + Critic 토론 |

---

## 2. 목표 (달성)

### 2-1. 전환 후 아키텍처 위치

```
단순 LLM 호출  <  Chain/Pipeline  <  DAG Workflow  <  Router Agent  <  ReAct Agent  <  Multi-Agent
                                                                      ^^^^^^^^^^^^
                                                                      [달성]
```

### 2-2. 전환 원칙

| 원칙 | 설명 |
|------|------|
| **점진적 전환** | Level 1(ReAct)→2(Tool-Calling)→3(Communication) 단계적 진화 |
| **기존 장점 보존** | 예측 가능성, 비용 통제, 디버깅 용이성 유지 |
| **선택적 Agentic** | 효과가 큰 핵심 노드(Director, Research, Cinematographer)부터 전환 |
| **비용 가드레일** | MAX_TOOL_CALLS=5, MAX_THINKING_STEPS=3, MAX_DEBATE_ROUNDS=2 |
| **측정 가능한 개선** | 벤치마크 10건 + TDD 18개 테스트로 효과 검증 |

---

## 3. 완료 요약

### Phase A: ReAct Loop + Self-Reflection (완료 2026-02-18)

| 항목 | 구현 내용 |
|------|----------|
| Director ReAct Loop | Observe→Think→Act 3-step, `MAX_THINKING_STEPS=3` |
| Review Self-Reflection | 실패 원인 분석 + 수정 전략 수립 → revise에 전달 |
| Writer Planning Step | 계획 수립 → 계획 기반 생성 2-step |
| 테스트 | 27개 신규 |

### Phase B: Tool-Calling Agent (완료 2026-02-18)

| 항목 | 구현 내용 |
|------|----------|
| Gemini Function Calling 인프라 | `services/agent/tools/` 패키지, `@agent_tool` |
| Research Agent | 5개 도구 (topic_history, character_history, fetch_url, trending, group_dna) |
| Cinematographer Agent | 4개 도구 (validate_tag, search_compositions, character_visual, tag_compatibility) |
| 테스트 | 36개 신규 |

### Phase C: Agent Communication (완료 2026-02-18)

| 항목 | 구현 내용 |
|------|----------|
| Agent Message Protocol | AgentMessage TypedDict, format/condense/truncate, MAX_MESSAGE_WINDOW=10 |
| Director ↔ Production 양방향 | 4개 Production Agent 응답 메시지, SSE 전달 |
| Critic 실시간 토론 | 3인 Architect 토론, KPI 기반 수렴, Groupthink 감지, DEBATE_TIMEOUT_SEC=60 |
| State Condensation | MAX_CONTEXT_TOKENS=2000, agent_summary 압축 |
| 테스트 | 31개 신규 (C-1: 13 + C-2: 6 + C-3: 12) |

**총 94개 테스트 추가** (Phase A 27 + Phase B 36 + Phase C 31)

### 리스크 대응 (구현 완료)

| 리스크 | 대응 |
|--------|------|
| 예측 불가능성 | KPI 기반 수렴, Groupthink 감지, Hard Timeout, Fallback 경로 |
| 비용 ROI | Phase별 A/B 벤치마크 (10건 × 10회) |
| 레이턴시 | Quick 모드 스킵, Progressive SSE, ETA 표시 |
| State 비대화 | Sliding Window 10건, State Condensation, 토큰 예산 2000 |

---

## 4. 참고

- 상세 설계 (설계 원본): [아카이브](../../99_archive/features/TRUE_AGENTIC_ARCHITECTURE_DETAIL.md)
- Phase 10 실행 기록: [Phase 10 아카이브](../../99_archive/archive/ROADMAP_PHASE_10.md)
- 에이전트 스펙: [AGENT_SPEC.md](../../03_engineering/backend/AGENT_SPEC.md)
- [Gemini Function Calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [LangGraph ReAct Agent](https://langchain-ai.github.io/langgraph/how-tos/create-react-agent/)
- [ReAct: Synergizing Reasoning and Acting (Yao et al., 2022)](https://arxiv.org/abs/2210.03629)
