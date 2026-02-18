# Phase 9: Agentic AI Pipeline (LangGraph Migration) - Archive

**기간**: 2026-02-13 ~ 2026-02-19
**상태**: 전체 완료 (잔여 1건 Feature Backlog 이동)

---

## 기술 스택 (결정: 2026-02-13)

| 컴포넌트 | 선택 |
|----------|------|
| 워크플로우 | LangGraph (`langgraph` + `langchain-core` 자동 포함, 풀 LangChain 불필요) |
| LLM | 기존 `google-genai` 유지 (노드에서 래핑, LangChain wrapper 전환 불필요) |
| Checkpointer | `AsyncPostgresSaver` (기존 PostgreSQL, `setup()` 자동 테이블) |
| Memory | `AsyncPostgresStore` — Phase 2에서 도입 |
| Observability | LangFuse 셀프호스팅 — Phase 2에서 도입 |
| Frontend 연동 | SSE (기존 패턴 재활용) |
| 단일 생성 | 항상 Graph 경유 (quick/full config 분기로 이원화 방지) |
| Gemini 호출 | 최대 3회 (Draft 1 + Revise 2, `MAX_REVISIONS=2`) |

## 단계별 계획

| Phase | 핵심 | 주요 작업 | 상태 |
|-------|------|----------|------|
| **0. Foundation** | 인프라 | LangGraph + AsyncPostgresSaver + psycopg v3, 2-노드 PoC, 스냅샷 10건 확보 | [x] (2026-02-13) |
| **1. 동등 전환** | 전환 | Draft→Review→Finalize 3노드, `/scripts/generate` Graph 교체, SSE 진행률, 회귀 테스트 | [x] (2026-02-15) |
| **1.5. 기능 확장** | 개선 | Full 모드 Graph 확장(Creative Debate 흡수), Revise 루프, Human Gate, Quick/Full 토글 UI | [x] (2026-02-15) |
| **2. Memory + Obs** | 학습 | AsyncPostgresStore, LangFuse Docker, Research/Learn 노드, 피드백 UI | [x] (2026-02-15) |
| **3. Creative 재평가** | 폐기(C) | Creative Lab 잔여 서비스 LangGraph 노드로 흡수. creative_utils.py 258줄 정리 | [x] (2026-02-16) |
| **4A. E2E Pipeline** | 자동화 | Post-generation CTA → persistStoryboard → Preflight → AutoRun 자동 체인 | [x] (2026-02-16) |
| **4B. Agent Spec + Director** | 아키텍처 | 에이전트 분류(AI Agent 7/Hybrid 2/System 4), Director Agent 신규. 12→13노드 | [x] (2026-02-16) |
| **4C. Pipeline 고도화** | 품질 | Director feedback→타겟 노드 주입, Production Chain 병렬화, Explain Node. 13→14노드 | [x] (2026-02-16) |
| **5A. Narrative Quality** | 서사 품질 | Hook 구조 가이드, Review 3-tier 검증, NarrativeScore | [x] (2026-02-17) |
| **5B. Concept Gate** | 컨셉 선택 | Critic 3컨셉 사용자 노출, concept_gate 노드, Creator interrupt. 14→15노드 | [x] (2026-02-17) |
| **5C. AI Transparency** | 투명성 UX | Pipeline Stepper, Agent Reasoning 패널, Narrative Score 시각화 | [x] (2026-02-17) |
| **5D. Interactive Feedback** | 피드백 | 프리셋 피드백 4종, Concept Gate 재생성/직접입력, 파라미터 피드백 | [x] (2026-02-17) |
| **5E. Research References** | 소재 분석 | URL/텍스트 소재 분석 (httpx + SSRF 방어 + Gemini 요약) | [x] (2026-02-17) |

잔여: PipelineControl 커스텀, 분산 큐 → Feature Backlog 이동

---

## 상세 변경 이력

### Phase 2: Memory + Observability (2026-02-15~16)
- AsyncPostgresStore Memory, LangFuse v3 Docker Observability
- Research/Learn 노드 구현, 피드백 수집 API+UI, Memory 관리 Settings 탭
- AsyncPostgresStore 싱글턴 버그 수정 (from_conn_string async context manager → 직접 AsyncConnection 패턴)
- LangFuse v3 Docker 인프라: docker-compose 6서비스(PG+ClickHouse+Redis+MinIO+Web+Worker), MinIO 버킷 생성, S3 Region 설정, observability.py SDK v3 API 대응
- human_gate interrupt 시 중간 결과 기록: `update_trace_on_interrupt()`

### Phase 3: Creative 재평가 (2026-02-16)
- 선택지 C(폐기) 결정: Creative Lab UI/라우터는 Phase 7-4 D에서 이미 삭제됨
- 잔여 서비스(debate_agents, creative_qc)는 LangGraph Production 노드로 흡수
- creative_utils.py V2 데드 코드 258줄 정리

### Phase 4B: Agent Spec + Director (2026-02-16)
- Agentic AI 기준 분류 체계(AI Agent 7 / Hybrid 2 / System 4)
- 네이밍 통일(debate→critic, draft→writer)
- Director Agent 신규(Production chain 통합 검증 + revision 루프)
- `_DIRECTOR_DECISION_MAP` 명시적 라우팅, AGENT_SPEC.md 엔지니어링 스펙

### Phase 4C: Pipeline 고도화 (2026-02-16)
- Director feedback→타겟 노드 주입(cinematographer/tts/sound/copyright/revise)
- Production Chain 병렬화(LangGraph fan-out: tts/sound/copyright 동시 실행)
- Explain Node(Full 모드 창작 결정 설명), fallback 패턴(병렬 안전)

### Phase 5 설계 (2026-02-17)
- 4-Agent 크로스 분석 합의: Multi-draft(3x) 반대, Concept Gate 방식 채택
- 5A 서사 품질 평가(Hook 40%+감정 25%+반전 20%+톤 10%+정합성 5%)
- 5B Concept Gate(Critic 3컨셉 사용자 선택)
- 5C AI 투명성 UX(Pipeline Stepper+Reasoning 패널+Score 시각화)
- 5D 프리셋 피드백 버튼

### Phase 5A: Narrative Quality (2026-02-17)
- `create_storyboard.j2`에 Hook/Rising/Climax/Resolution 구조 가이드 추가
- Review 노드 3-tier 검증(규칙→Gemini 피드백→서사 품질 평가)
- `NarrativeScore` TypedDict, `narrative_review.j2` 템플릿, `LANGGRAPH_NARRATIVE_THRESHOLD=0.6`
- Quick 모드 스킵, Gemini 에러 시 graceful degradation. 10개 테스트

### Phase 5B: Concept Gate (2026-02-17)
- concept_gate 노드 삽입(critic↔writer 사이), Creator 모드 interrupt()로 3컨셉 사용자 선택
- SSE 일반화(_read_interrupt_state → tuple[str, dict] 반환, 동적 interrupt 노드명)
- ConceptSelectionPanel UI(AI 추천 뱃지, 카드 선택). 14→15노드. 10개 테스트

### Phase 5C: AI Transparency UX (2026-02-17)
- Backend `_extract_node_result()` 매핑으로 reasoning 데이터 SSE 전달
- `pipelineSteps.ts` 순수 함수(15노드→7/3 논리 스텝 매핑)
- `PipelineStepper` 수평 멀티스텝 인디케이터, `NarrativeScoreChart` 5메트릭 바 차트
- `AgentReasoningPanel` 아코디언. 10개 테스트

### Phase 5D: Interactive Feedback (2026-02-17)
- FEEDBACK_PRESETS 4종, concept_gate 3-action 분기, MAX_CONCEPT_REGEN=2 제한
- FeedbackPresetButtons UI, ConceptSelectionPanel 재생성/직접입력 폼
- _update_user_preferences → services/agent/feedback.py 추출. 10개 테스트

### Phase 5E: Research References (2026-02-17)
- Research 노드에 사용자 소재(URL/텍스트) 분석 기능
- URL fetch: httpx + SSRF 방어(private IP 차단), HTML strip → Gemini 분석
- 테스트 22개(URL 판별, SSRF 12케이스, HTML→text, Gemini mock, fallback)

---

## 관련 버그 수정 및 안정화

### Langfuse Trace 통합 (2026-02-17)
- interrupt/resume 별도 trace → 동일 trace 통합
- 요청별 `CallbackHandler` 생성(싱글턴→per-request)으로 동시성 안전
- Per-node trace 확장: 모든 Gemini LLM 호출에 `trace_llm_call` 래핑
- v3 SDK 마이그레이션: `CallbackHandler(trace_context={"trace_id":})` 전환

### Langfuse 연동 정상화 (2026-02-18)
- langfuse + langchain 패키지 설치로 CallbackHandler 생성 실패 해소
- 전체 파이프라인 trace 기록 확인 (19 observations/trace)
- Langfuse 트레이스 검수 (trace `9095a193`): DB 세션 버그 발견/수정, 서사 품질 개선점 도출

### 안정성 수정 (2026-02-16~19)
- Script 탭 unmount 시 scenes 소실 수정 (save() 후 useStoryboardStore 동기화)
- Edit→Script 탭 전환 시 대본 소실 수정 (CSS hidden으로 ScriptTab 상태 유지)
- Character Preset 동기화 수정 (syncToGlobalStore 전파)
- 빠른 수정 대본 미반영 수정 (human_gate revision_count 리셋)
- Tool-Calling DB 세션 버그 수정 (get_db_session() fallback)
- Writer ↔ Critic 컨셉 연결 강화 (selected_concept 별도 필드)
- Agent Graceful Degradation 강화 (error → None 반환)
- useScriptEditor 페이지 이탈 시 대본 소실 수정 (isDirty + syncToGlobalStore)

---

## 테스트

Backend 1,805 + Frontend 339 = **총 2,144개**

## 전체 문서 동기화 (2026-02-18)

9개 에이전트 병렬 작업으로 **45개 파일** 소스 기준 최신화 (+2,262줄/-3,422줄).
